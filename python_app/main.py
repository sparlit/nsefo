import pandas as pd
import json
import logging
import time
import sys
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List
from python_app.nlp.parser import CommandParser
from python_app.core.risk_manager import RiskManager
from python_app.core.engine import BrainEngine, RSI_PERIOD, VOLATILITY_PERIOD
from python_app.core.coordinator import Coordinator
from python_app.broker.session_manager import SessionManager
from python_app.core.utils import auto_confirm_trade
from python_app.core.state import global_state

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [ENGINE] - %(levelname)s - %(message)s')

# Per-symbol lot sizes — NIFTY=50, FINNIFTY=25, BANKNIFTY=25 (as of 2023)
LOT_SIZES = {"NIFTY": 50, "BANKNIFTY": 25, "FINNIFTY": 25}

# Minimum historical rows needed for a valid analysis
_MIN_HISTORY_ROWS = max(RSI_PERIOD + 1, VOLATILITY_PERIOD + 1)  # 21


def compute_delta_adjusted_quantity(
    symbol: str,
    delta: float,
    fixed_lots: int = 1,
    win_rate: float = 0.55,
    ann_vol: float = 0.20,
) -> int:
    """
    Compute position size using delta × Kelly fraction × lot_size.

    Delta: |d| gives the equivalent underlying exposure per option contract.
    Kelly fraction: f = (W - (1-W)/R) where W=win_rate, R=reward/risk (≈1 for option play).
    Resulting quantity is clipped to at least 1 lot.

    Args:
        symbol:      Trading symbol (e.g. "NIFTY", "BANKNIFTY")
        delta:       BrainEngine delta (0.0 to 1.0, absolute value used)
        fixed_lots:  Number of option lots before delta scaling
        win_rate:    Historical win rate (0.0 to 1.0). Defaults to 0.55 (conservative).
        ann_vol:     Annualized volatility from BrainEngine. Used in Kelly denominator.
    Returns:
        Integer quantity (number of shares/contracts to trade)
    """
    lot_size = LOT_SIZES.get(symbol, 50)
    d = abs(delta)

    # Kelly fraction: f = W - (1-W)/R  (simplified, R ≈ 1 for short-duration options)
    # Lower Kelly to 50% of full Kelly for risk management (half-Kelly)
    R_approx = 1.0
    kelly_full = max(0.0, win_rate - (1.0 - win_rate) / R_approx)
    kelly_fraction = kelly_full * 0.5  # Half-Kelly: reduces volatility of outcomes

    # Delta × Kelly × base_qty
    base_qty = fixed_lots * lot_size
    raw_qty = d * kelly_fraction * base_qty

    # Clip to at least 1 lot, at most 10× the base (cap on extreme delta scenarios)
    qty = max(lot_size, min(base_qty * 10, round(raw_qty / lot_size) * lot_size))
    return qty

class TradingApp:
    def __init__(self):
        self.session = SessionManager()
        self.parser = CommandParser()

        cfg = self.session.config
        if not cfg or 'risk' not in cfg:
            raise RuntimeError(
                "config.json is missing the required 'risk' section. "
                "Run: python install.py or python run.py --setup"
            )

        self.risk_manager = RiskManager(
            capital=cfg['risk']['capital'],
            max_risk_per_trade=cfg['risk'].get('max_risk_per_trade_percent', 1.0) / 100.0,
        )
        self.engine = BrainEngine()
        self.broker = self.session.get_broker()
        self.coordinator = Coordinator(self.broker, risk_manager=self.risk_manager)
        self.logger = logging.getLogger("TradingApp")
        self.running = False
        self.watch_list = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
        self.symbol_map = {"NIFTY": "13", "BANKNIFTY": "25", "FINNIFTY": "27"}

        global_state.update_summary(
            capital=self.session.config['risk']['capital'],
            mode=self.session.config['mode']
        )
        global_state.set_scanning(self.watch_list)

    def handle_manual_suggestion(self, command: str):
        self.logger.info(f"Analyzing Instruction: {command}")
        global_state.add_log(f"Manual Input: {command}")
        parsed = self.parser.interpret(command)
        if parsed["status"] == "error": return parsed

        data = parsed["data"]
        sid = self.symbol_map.get(data['symbol'], "13")
        symbol_info = {'security_id': sid, 'exchange_segment': 'NSE_EQ'}

        market_data = self.broker.get_market_data([symbol_info])
        last_price = self._extract_ltp(market_data, sid)

        if last_price <= 0.0:
            self.logger.error("Live price unavailable. Aborting analysis.")
            return {"status": "error", "message": "Live price unavailable"}

        df_context = self._get_context_data(symbol_info, last_price)
        if df_context.empty or len(df_context) < _MIN_HISTORY_ROWS:
            self.logger.error(f"Market context unavailable (need {_MIN_HISTORY_ROWS}+ rows, got {len(df_context)}).")
            return {"status": "error", "message": "Market context unavailable"}

        # Pass strike and option_type so BrainEngine computes the CORRECT delta
        analysis = self.engine.analyze_symbol(
            df_context,
            strike=data.get('strike'),
            option_type=data.get('option_type', 'CE'),
        )
        prob = analysis['probability']
        signal = analysis.get("signal", "NEUTRAL")
        brains = analysis.get('brains', {})

        # Reject crashed-brain output explicitly — don't rely on prob≈0 accidental gate
        if signal == "SYSTEM_ERROR":
            self.logger.error("Brain returned SYSTEM_ERROR — rejecting analysis")
            return {"status": "error", "message": "Brain system error", "signal": signal}

        symbol = data['symbol']
        delta = brains.get('delta', 0.5)  # default to ATM-ish if absent
        ann_vol = brains.get('ann_vol', 0.20)
        fixed_lots = int(self.session.config['risk'].get('fixed_lots', 1))
        lot_size = LOT_SIZES.get(symbol, 50)
        quantity = compute_delta_adjusted_quantity(
            symbol=symbol,
            delta=delta,
            fixed_lots=fixed_lots,
            ann_vol=ann_vol,
        )

        # ATR-based stop-loss: 1.5 × ATR below entry for BUY, above for SELL
        # Previously used hardcoded 1.5% (0.985/1.015 multiplier) — ATR adapts to
        # actual market volatility instead of a fixed percentage.
        curr_atr = brains.get('atr', last_price * 0.015)  # fallback to ~1.5% if no ATR
        if data['action'] == 'BUY':
            sl_val = round(last_price - 1.5 * curr_atr, 2)
            # Target: 2:1 reward-to-risk ratio
            target_val = round(last_price + 3.0 * curr_atr, 2)
        else:
            sl_val = round(last_price + 1.5 * curr_atr, 2)
            # Target: 2:1 reward-to-risk ratio
            target_val = round(last_price - 3.0 * curr_atr, 2)

        risk_report = self.risk_manager.assess_trade(last_price, sl_val, quantity)

        report = {
            "symbol": symbol,
            "action": data['action'],
            "strike": data.get('strike'),
            "option_type": data.get('option_type'),
            "last_price": last_price,
            "probability": prob,
            "fixed_lots": fixed_lots,
            "lot_size": lot_size,
            "quantity": quantity,
            "entry_price": last_price,
            "sl_price": sl_val,
            "atr_1_5x": round(curr_atr, 2),
            "brains": brains,
            "risk": risk_report,
            "decision": (
                "EXECUTE"
                if (
                    analysis["signal"] in ("BUY", "SELL")
                    and prob > 0.8
                    and risk_report["is_safe"]
                )
                else "REJECT"
            )
        }

        # Circuit breaker gates assess_trade — check returned state
        if risk_report.get("circuit_broken"):
            report["reason"] = risk_report.get("recommendation", "CIRCUIT_BREAKER_TRIPPED")
            report["decision"] = "REJECT"
            print("\n" + "#"*60 + "\nCIRCUIT BREAKER TRIPPED — AUTO-STOP\n" + "#"*60)
            print(json.dumps(report, indent=2))
            return report

        print("\n" + "#"*60 + "\nMASTER PRO EXPERT ANALYSIS\n" + "#"*60)
        print(json.dumps(report, indent=2))

        if report['decision'] == "EXECUTE":
            # Verify broker margin BEFORE placing order (margin check is cheap and fast)
            margin_check = self.risk_manager.check_margin_requirement(
                broker=self.broker,
                side=data['action'],
                price=last_price,
                quantity=quantity,
                option_type=data.get('option_type', 'CE'),
            )
            if not margin_check["sufficient"]:
                print(f"MARGIN CHECK FAILED: {margin_check['recommendation']}")
                global_state.add_log(f"Margin check FAIL: {margin_check['recommendation']}")
                report["decision"] = "REJECT"
                report["reason"] = margin_check["recommendation"]
                return report

            if auto_confirm_trade(data, recommend_action="YES"):
                proposal = {
                    'security_id': sid, 'exchange_segment': 'NSE_FNO',
                    'symbol': symbol, 'side': data['action'],
                    'quantity': quantity, 'price': last_price, 
                    'stop_loss': sl_val, 'target': target_val,
                    'tag': 'NSEFO_EXPERT'
                }
                try:
                    order_id = self.coordinator.execute_confirmed_trade(proposal)
                    if order_id:
                        global_state.add_log(f"Order Success: {order_id}")
                except Exception as e:
                    global_state.add_log(f"Order failed: {e}")
                    self.logger.error(f"Order execution failed: {e}")

        return report

    def _extract_ltp(self, market_data, sid):
        """Extracts LTP from real Dhan/Fenix data structures."""
        try:
            if market_data and 'data' in market_data:
                d = market_data['data']
                if isinstance(d, dict):
                    # Dhan quote_data format
                    return float(d.get(sid, {}).get('last_price', 0.0))
                elif isinstance(d, list) and len(d) > 0:
                    return float(d[0].get('last_price', 0.0))
        except Exception as e:
            self.logger.debug(f"LTP extraction failed: {e}")
        return 0.0

    def _get_context_data(self, symbol_info, last_price):
        """
        Fetches real historical OHLC for brain processing.
        Needs at least 21 rows for annualized volatility (VOLATILITY_PERIOD=20).
        """
        now = datetime.now()
        # Fetch enough to cover the worst case: period + some buffer
        lookback_minutes = max(
            max(RSI_PERIOD, VOLATILITY_PERIOD) * 5 + 30,  # per-bar * period + buffer
            120,  # but at least 2 hours of 1-min bars
        )
        try:
            hist_data = self.broker.get_historical_data(
                symbol_info, "1",
                (now - timedelta(minutes=lookback_minutes)).strftime("%Y-%m-%d %H:%M:%S"),
                now.strftime("%Y-%m-%d %H:%M:%S")
            )
            if hist_data and isinstance(hist_data, list) and len(hist_data) >= _MIN_HISTORY_ROWS:
                return pd.DataFrame(hist_data)
        except Exception as e:
            self.logger.error(f"Historical fetch failed: {e}")
        return pd.DataFrame()

    def run_market_cycle(self):
        self.running = True
        self.logger.info("Neural Scanning Cycle Started.")
        while self.running:
            try:
                current_prices = {}
                active_list = []
                # kanban["ACTIVE"] is a List[Dict], not a Dict — iterate directly
                for trade in global_state.kanban["ACTIVE"]:
                    sid = self.symbol_map.get(trade['symbol'], "13")
                    quote = self.broker.get_market_data([{'security_id': sid, 'exchange_segment': 'NSE_EQ'}])
                    lp = self._extract_ltp(quote, sid)
                    if lp > 0:
                        current_prices[trade['symbol']] = lp
                        active_list.append({"symbol": trade['symbol'], "side": trade['side'], "price": trade['price'], "ltp": lp, "quantity": trade['quantity']})

                self.coordinator.track_trades(lambda sym: current_prices.get(sym, 0))
                global_state.update_active_trades(active_list)

                for symbol in self.watch_list:
                    sid = self.symbol_map.get(symbol)
                    info = {'security_id': sid, 'exchange_segment': 'NSE_EQ'}
                    quote = self.broker.get_market_data([info])
                    lp = self._extract_ltp(quote, sid)
                    if lp > 0:
                        df = self._get_context_data(info, lp)
                        # Need _MIN_HISTORY_ROWS for valid annualized vol and RSI
                        if len(df) >= _MIN_HISTORY_ROWS:
                            analysis = self.engine.analyze_symbol(df)
                            if analysis['probability'] > 0.90:
                                global_state.add_signal({"symbol": symbol, "side": analysis['signal'], "prob": analysis['probability'], "price": lp, "brains": analysis['brains']})
            except Exception as e:
                self.logger.error(f"Cycle Exception: {e}")
            time.sleep(1)

    def start(self):
        self.logger.info("Activating Master Pro Core Loop...")
        self.run_market_cycle()

if __name__ == "__main__":
    app = TradingApp()
    if len(sys.argv) > 1:
        app.handle_manual_suggestion(" ".join(sys.argv[1:]))
    else:
        app.start()
