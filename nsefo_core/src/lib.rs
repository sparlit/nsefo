use pyo3::prelude::*;
mod strategies;
mod analysis;

use strategies::trend::supertrend;
use strategies::mean_reversion::calculate_rsi;
use strategies::volatility::calculate_volatility;
use analysis::probability::assess_winning_probability;

#[pyfunction]
fn get_rsi_list(data: Vec<f64>, period: usize) -> PyResult<Vec<f64>> {
    Ok(calculate_rsi(&data, period))
}

#[pyfunction]
fn get_volatility_list(data: Vec<f64>, period: usize) -> PyResult<Vec<f64>> {
    Ok(calculate_volatility(&data, period))
}

#[pyfunction]
fn get_supertrend(high: Vec<f64>, low: Vec<f64>, close: Vec<f64>, period: usize, multiplier: f64) -> PyResult<(Vec<f64>, Vec<i8>)> {
    Ok(supertrend(&high, &low, &close, period, multiplier))
}

#[pyfunction]
fn calculate_probability(indicators: Vec<f64>) -> PyResult<f64> {
    Ok(assess_winning_probability(indicators))
}

#[pymodule]
fn nsefo_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_rsi_list, m)?)?;
    m.add_function(wrap_pyfunction!(get_volatility_list, m)?)?;
    m.add_function(wrap_pyfunction!(get_supertrend, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_probability, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rsi_accuracy() {
        let data = vec![100.0, 105.0, 102.0, 110.0, 108.0, 115.0, 112.0, 120.0, 118.0, 125.0, 122.0, 130.0, 128.0, 135.0, 132.0];
        let rsi = get_rsi_list(data, 14).unwrap();
        assert_eq!(rsi.len(), 15);
        assert!(rsi[14] > 50.0);
    }

    #[test]
    fn test_probability_clamp() {
        let low_prob = calculate_probability(vec![-1.0, -1.0, 0.5]).unwrap();
        assert!(low_prob >= 0.0 && low_prob <= 1.0);
        let high_prob = calculate_probability(vec![1.0, 1.0, 1.2]).unwrap();
        assert!(high_prob >= 0.0 && high_prob <= 1.0);
    }
}
