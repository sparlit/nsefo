use ta::indicators::ExponentialMovingAverage;
use ta::Next;

pub fn calculate_ema(data: &[f64], period: usize) -> Vec<f64> {
    let mut ema = ExponentialMovingAverage::new(period).unwrap();
    data.iter().map(|&x| ema.next(x)).collect()
}

pub fn check_supertrend_signal(high: &[f64], _low: &[f64], close: &[f64]) -> i8 {
    // Placeholder for actual Supertrend logic
    // Returns 1 for Buy, -1 for Sell, 0 for Neutral
    if close.last() > high.last() { 1 } else { 0 }
}
