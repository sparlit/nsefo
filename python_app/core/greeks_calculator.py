"""
Bare-minimum Black-Scholes Greeks calculator for NSE F&O options.
Pure Python + scipy. No IBridgePy, no interactive brokers.

Inputs:
    S       - spot price (float)
    K       - strike price (float)
    T       - time to expiry in years (float)
    r       - risk-free rate (annualised, e.g. 0.07 for 7%) (float)
    sigma   - implied volatility (annualised, e.g. 0.20 for 20%) (float)
    option_type - 'call' or 'put' (str)

Returns:
    dict with delta, gamma, theta, vega
"""

from __future__ import annotations

import math
from scipy.stats import norm


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple[float, float]:
    """Compute d1 and d2 for Black-Scholes."""
    if T <= 0 or sigma <= 0:
        raise ValueError("T must be positive and sigma must be non-zero.")
    sqrt_t = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    return d1, d2


def delta(S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call") -> float:
    """
    Black-Scholes Delta.
    Call:  N(d1)
    Put:   N(d1) - 1
    """
    d1, _ = _d1_d2(S, K, T, r, sigma)
    if option_type.lower().startswith("c"):
        return norm.cdf(d1)
    else:
        return norm.cdf(d1) - 1.0


def gamma(S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call") -> float:
    """
    Black-Scholes Gamma.
    Same formula for calls and puts: n(d1) / (S * sigma * sqrt(T))
    """
    d1, _ = _d1_d2(S, K, T, r, sigma)
    sqrt_t = math.sqrt(T)
    return norm.pdf(d1) / (S * sigma * sqrt_t)


def theta(S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call") -> float:
    """
    Black-Scholes Theta (per-share, per-year, discounted to present).
    Call:  -S * n(d1) * sigma / (2 * sqrt(T)) - r * K * exp(-rT) * N(d2)
    Put:   -S * n(d1) * sigma / (2 * sqrt(T)) + r * K * exp(-rT) * N(-d2)

    Returns theta in terms of option value change per year.
    Divide by 365 to get daily theta.
    """
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    sqrt_t = math.sqrt(T)
    term1 = -(S * norm.pdf(d1) * sigma) / (2.0 * sqrt_t)
    disc_k = K * math.exp(-r * T)
    if option_type.lower().startswith("c"):
        term2 = -r * disc_k * norm.cdf(d2)
    else:
        term2 = r * disc_k * norm.cdf(-d2)
    return term1 + term2


def vega(S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call") -> float:
    """
    Black-Scholes Vega.
    Same for calls and puts: S * sqrt(T) * n(d1)
    Returns vega — change in option price per 1.0 (i.e. 100%) move in IV.
    For vega per 1% move, divide result by 100.
    """
    d1, _ = _d1_d2(S, K, T, r, sigma)
    sqrt_t = math.sqrt(T)
    return S * sqrt_t * norm.pdf(d1)


def greeks(S: float, K: float, T: float, r: float, sigma: float,
           option_type: str = "call") -> dict[str, float]:
    """
    Convenience wrapper: compute all four Greeks at once.

    Args:
        S:          Spot price (e.g. 24500 for NIFTY)
        K:          Strike price
        T:          Time to expiry in years (e.g. 7/365 for 7 days)
        r:          Risk-free rate (e.g. 0.0695 for 6.95% — current 91-day T-bill)
        sigma:      Implied volatility (e.g. 0.18 for 18%)
        option_type: 'call' or 'put'

    Returns:
        dict: {'delta': ..., 'gamma': ..., 'theta': ..., 'vega': ...}
    """
    return {
        "delta": delta(S, K, T, r, sigma, option_type),
        "gamma": gamma(S, K, T, r, sigma, option_type),
        "theta": theta(S, K, T, r, sigma, option_type),
        "vega":  vega(S, K, T, r, sigma, option_type),
    }


# ----------------------------------------------------------------------
# Dhan API integration helpers
# ----------------------------------------------------------------------
# To fetch the data needed for Greeks from Dhan:
#
#   from dhanhq import dhanhq, DhanContext
#   dhan = dhanhq(DhanContext(client_id, access_token))
#
# Required fields from Dhan quote / option chain:
#   - S (spot):       dhan.quote_data([{'exchange_segment': 'NSE_FNO', 'security_id': '...'}])
#                     or from index quote for NIFTY/BANKNIFTY
#   - K (strike):     user-selected; NSE F&O options have fixed strike intervals
#   - T:              computed from order/chain expiry date: (expiry_date - today).days / 365.0
#   - r:              risk-free rate — use current 91-day T-bill rate (~6.95% as of 2025)
#                     or fetch from: https://www.rbi.org.in/Scripts/WSSView.aspx?page=SP1
#   - sigma (IV):     not directly returned by Dhan; requires:
#                     (a) a third-party IV feed, OR
#                     (b) historical close prices to compute realised volatility, OR
#                     (c) an IV model (e.g. Black-Scholes implied vol solver via scipy.optimize)
#
# Dhan option chain endpoint (if available):
#   dhan.get_option_chain(security_id, exchange_segment)
#   Returns: {'status': 'success', 'data': [{strike, expiry, pe_price, ce_price, lot_size, ...}, ...]}
#
# ----------------------------------------------------------------------


if __name__ == "__main__":
    # Smoke-test with NIFTY ATM call scenario
    # Spot: 24,500 | Strike: 24,500 ATM | 7 days to expiry | IV: 18% | r: 6.95%

    S = 24500.0
    K = 24500.0
    T = 7.0 / 365.0          # 7 days
    r = 0.0695               # ~6.95% 91-day T-bill
    sigma = 0.18             # 18% IV

    g = greeks(S, K, T, r, sigma, "call")

    print("=== NIFTY ATM Call Greeks (7 days to expiry) ===")
    print(f"  Spot:      {S}")
    print(f"  Strike:    {K}")
    print(f"  T:         {T:.6f} years ({7} days)")
    print(f"  r:         {r:.4f} ({r*100:.2f}%)")
    print(f"  IV:        {sigma:.4f} ({sigma*100:.1f}%)")
    print()
    print(f"  Delta:     {g['delta']:.4f}")
    print(f"  Gamma:     {g['gamma']:.6f}")
    print(f"  Theta:     {g['theta']:.4f}  (per year — divide by 365 for daily: {g['theta']/365:.4f})")
    print(f"  Vega:      {g['vega']:.4f}  (per 1.0 IV — divide by 100 for per-1% IV)")
    print()

    # Put Greeks
    g_put = greeks(S, K, T, r, sigma, "put")
    print("=== NIFTY ATM Put Greeks ===")
    print(f"  Delta:     {g_put['delta']:.4f}")
    print(f"  Gamma:     {g_put['gamma']:.6f}  (same as call)")
    print(f"  Theta:     {g_put['theta']:.4f}")
    print(f"  Vega:      {g_put['vega']:.4f}  (same as call)")