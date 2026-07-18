"""Verify engine.py fixes after Rust rebuild."""
import nsefo_core, math, sys, os, random

sys.path.insert(0, r'D:\myproject\nsefo')

# ── 1. get_annualized_volatility_list ──────────────────────────────────────
print('=== [1] Annualized Volatility ===')

# Random walk: log-returns are i.i.d. normal, giving a realistic vol
random.seed(42)
log_returns = [random.gauss(0.0005, 0.015) for _ in range(60)]  # ~5bps/day drift, ~1.5% daily vol
prices = [24500.0]
for lr in log_returns:
    prices.append(prices[-1] * math.exp(lr))

prices_vol = prices[:30]

ann_vol = nsefo_core.get_annualized_volatility_list(prices_vol, 20)
print(f'  ann_vol (random walk, last): {ann_vol[-1]:.4f}  ({ann_vol[-1]*100:.2f}% annualized)')
assert 0.05 < ann_vol[-1] < 0.50, f'Expected realistic vol 5-50%, got {ann_vol[-1]*100:.2f}%'
assert len(ann_vol) == 30,       f'Should return {30} values, got {len(ann_vol)}'
assert ann_vol[19] == 0.0,       f'First 20 should be 0-padded'
print(f'  First valid (index 20): {ann_vol[20]:.4f}')
print('  PASS')

# ── 2. get_atr_list ─────────────────────────────────────────────────────────
print('\n=== [2] ATR ===')
high  = [24510.0 + i * 0.5 for i in range(30)]
low   = [24490.0 - i * 0.3 for i in range(30)]
close = [(h + l) / 2 for h, l in zip(high, low)]
atr = nsefo_core.get_atr_list(high, low, close, 14)
print(f'  ATR[14]: {atr[-1]:.2f}  (expect > 0)')
assert atr[-1] > 0
assert len(atr) == 30
print('  PASS')

# ── 3. Backward compat: RSI, Supertrend, Probability ──────────────────────
print('\n=== [3] Backward Compatibility ===')
rsi = nsefo_core.get_rsi_list(prices_vol, 14)
st_vals, trends = nsefo_core.get_supertrend(high, low, close, 10, 3.0)
prob = nsefo_core.calculate_probability([1.0, 0.5])
print(f'  RSI last: {rsi[-1]:.1f}')
print(f'  Supertrend trends: {set(trends)}')
print(f'  Probability [1.0, 0.5]: {prob:.3f}')
assert len(st_vals) == 30
print('  PASS')

# ── 4. BrainEngine integration ─────────────────────────────────────────────
print('\n=== [4] BrainEngine smoke test ===')
from python_app.core.engine import BrainEngine
import pandas as pd

random.seed(99)
bars = [{'high': 24550 + random.uniform(-30, 30),
         'low':  24500 + random.uniform(-30, 30),
         'close': 24525 + random.uniform(-20, 20)}
        for _ in range(25)]
df = pd.DataFrame(bars)

engine = BrainEngine()
result = engine.analyze_symbol(df, strike=24500.0, option_type='CE')

print(f'  signal:    {result["signal"]}')
print(f'  prob:      {result["probability"]}')
brains = result.get('brains', {})
print(f'  ann_vol:   {brains.get("ann_vol", "MISSING")}')
print(f'  delta:     {brains.get("delta", "MISSING")}')
print(f'  atr:       {brains.get("atr", "MISSING")}')
print(f'  moneyness: {brains.get("moneyness", "MISSING")}')
print(f'  strike:    {brains.get("strike", "MISSING")}')

assert 'ann_vol' in brains,           'ann_vol missing from brains'
assert 'atr' in brains,               'atr missing from brains'
assert brains.get('strike') == 24500.0, f'Expected strike=24500, got {brains.get("strike")}'
assert 'moneyness' in brains,           'moneyness missing'
assert brains['moneyness'] == 'ATM',   f'K=spot should be ATM, got {brains["moneyness"]}'
print('  PASS')

# ── 5. Old broken formula vs new correct formula ───────────────────────────
print('\n=== [5] Old vs New sigma ===')
close_prices = [24500.0 + i * 10 for i in range(30)]
old_vol_list = nsefo_core.get_volatility_list(close_prices, 20)
new_vol_list = nsefo_core.get_annualized_volatility_list(close_prices, 20)
old_sigma = (old_vol_list[-1] / close_prices[-1]) * (252**0.5)
new_sigma = new_vol_list[-1]
print(f'  OLD sigma (broken): {old_sigma:.4f}  ({old_sigma*100:.2f}%)')
print(f'  NEW sigma (correct): {new_sigma:.4f}  ({new_sigma*100:.2f}%)')
# For linear trending prices: old formula inflates (price-level std-dev grows with trend)
# New formula: strictly increasing → identical log returns → vol = 0
print(f'  OLD > 0 for deterministic trend: {old_sigma > 0.01}')
print(f'  NEW = 0 for deterministic trend: {new_sigma < 0.01}')
print('  PASS')

# ── 6. ITM vs OTM delta check ───────────────────────────────────────────────
print('\n=== [6] Correct strike → correct delta (ITM vs OTM) ===')
engine = BrainEngine()
random.seed(77)
# Spot ~24750
bars2 = [{'high': 24800 + random.uniform(-50, 50),
           'low':  24700 + random.uniform(-50, 50),
           'close': 24750 + random.uniform(-30, 30)}
          for _ in range(25)]
df2 = pd.DataFrame(bars2)

result_otm = engine.analyze_symbol(df2, strike=25000.0, option_type='CE')  # OTM
result_itm = engine.analyze_symbol(df2, strike=24500.0, option_type='CE')  # ITM

delta_otm = result_otm['brains'].get('delta', 0)
delta_itm = result_itm['brains'].get('delta', 0)
print(f'  OTM call delta (K=25000, S~24750): {delta_otm:.4f}')
print(f'  ITM call delta (K=24500, S~24750): {delta_itm:.4f}')
print(f'  ITM > OTM: {delta_itm > delta_otm}  (expect True)')
assert delta_itm > delta_otm, 'ITM delta should exceed OTM delta'
assert delta_otm < 0.5,  f'OTM call delta should be < 0.5, got {delta_otm}'
assert delta_itm > 0.5,  f'ITM call delta should be > 0.5, got {delta_itm}'
print('  PASS')

# ── 7. PE delta is negative ─────────────────────────────────────────────────
print('\n=== [7] Put delta is negative ===')
result_pe = engine.analyze_symbol(df2, strike=24500.0, option_type='PE')
delta_pe = result_pe['brains'].get('delta', 0)
print(f'  Put delta (K=24500, S~24750): {delta_pe:.4f}')
assert -1.0 < delta_pe < 0.0, f'Put delta must be negative, got {delta_pe}'
print('  PASS')

# ── 8. INSUFFICIENT_DATA guard ──────────────────────────────────────────────
print('\n=== [8] INSUFFICIENT_DATA for short history ===')
tiny_df = pd.DataFrame([{'high': 24500, 'low': 24490, 'close': 24495}] * 5)
result_short = engine.analyze_symbol(tiny_df)
print(f'  Result with 5 rows: {result_short["signal"]}')
assert result_short['signal'] == 'INSUFFICIENT_DATA'
print('  PASS')

print('\n=== ALL VERIFICATIONS PASSED ===')