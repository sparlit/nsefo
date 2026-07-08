pub fn assess_winning_probability(indicators: Vec<f64>) -> f64 {
    // Weighted scoring of multiple indicators
    // indicators[0]: Trend Alignment (1.0 or -1.0)
    // indicators[1]: RSI Oversold/Overbought status
    // indicators[2]: Volume surge

    let score: f64 = indicators.iter().sum();
    let normalized = (score + indicators.len() as f64) / (2.0 * indicators.len() as f64);

    // Return a probability between 0 and 1
    normalized.clamp(0.0, 1.0)
}
