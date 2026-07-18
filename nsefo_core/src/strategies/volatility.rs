use ta::indicators::StandardDeviation;
use ta::Next;

pub fn calculate_volatility(data: &[f64], period: usize) -> Vec<f64> {
    let mut sd = StandardDeviation::new(period).unwrap();
    data.iter().map(|&x| sd.next(x)).collect()
}

/// Compute annualized volatility from log returns.
///
/// Step 1: log returns = ln(price[i] / price[i-1]) for i = 1..n-1
/// Step 2: std_dev of those log returns (population std dev with n-1 denominator)
/// Step 3: annualize by multiplying by sqrt(252)
///
/// Returns a list of annualized volatility values (one per complete price pair).
/// The first `period` values will be 0.0 since we need `period` prices to compute
/// the first valid return, then `period-1` returns for the std-dev.
pub fn calculate_annualized_volatility(data: &[f64], period: usize) -> Vec<f64> {
    if data.len() < period + 1 {
        return vec![0.0; data.len()];
    }

    let mut result = vec![0.0; period]; // pad start with zeros

    // Rolling window of log returns
    for window_end in period..data.len() {
        let window_start = window_end - period;
        let mut log_returns = Vec::with_capacity(period);
        for i in (window_start + 1)..=window_end {
            let r = (data[i] / data[i - 1]).ln();
            log_returns.push(r);
        }

        // Population standard deviation of log returns
        let mean = log_returns.iter().sum::<f64>() / log_returns.len() as f64;
        let variance = log_returns.iter()
            .map(|&x| {
                let d = x - mean;
                d * d
            })
            .sum::<f64>() / log_returns.len() as f64;
        let std_dev = variance.sqrt();

        // Annualize: multiply by sqrt(252) for daily data
        result.push(std_dev * (252.0_f64).sqrt());
    }

    result
}
