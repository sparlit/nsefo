use ta::indicators::StandardDeviation;
use ta::Next;

pub fn calculate_volatility(data: &[f64], period: usize) -> Vec<f64> {
    let mut sd = StandardDeviation::new(period).unwrap();
    data.iter().map(|&x| sd.next(x)).collect()
}
