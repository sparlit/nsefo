pub fn assess_winning_probability(indicators: Vec<f64>) -> f64 {
    if indicators.is_empty() { return 0.5; }
    if indicators.len() < 2 { return 0.5; }

    // Weighting Scheme:
    // indicators[0]: Trend Alignment (Weight 0.5)
    // indicators[1]: Momentum/RSI Alignment (Weight 0.3)
    // indicators[2]: Volatility Factor (Multiplier for base score)

    let trend = indicators[0];
    let momentum = indicators[1];
    let vol_factor = if indicators.len() > 2 { indicators[2] } else { 1.0 };

    let base_score = (trend * 0.5) + (momentum * 0.3);

    // Convert -0.8 to 0.8 range into a 0.0 to 1.0 probability
    // (score + 0.8) / 1.6
    let normalized = (base_score + 0.8) / 1.6;

    let final_prob = normalized * vol_factor;

    final_prob.clamp(0.0, 1.0)
}
