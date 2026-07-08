pub fn calculate_rsi(data: &[f64], period: usize) -> Vec<f64> {
    use ta::indicators::RelativeStrengthIndex;
    use ta::Next;
    let mut rsi = RelativeStrengthIndex::new(period).unwrap();
    data.iter().map(|&x| rsi.next(x)).collect()
}
