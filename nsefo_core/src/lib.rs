use pyo3::prelude::*;
mod strategies;
mod analysis;

use strategies::trend::{supertrend};
use strategies::mean_reversion::calculate_rsi;
use analysis::probability::assess_winning_probability;

#[pyfunction]
fn get_rsi_list(data: Vec<f64>, period: usize) -> PyResult<Vec<f64>> {
    Ok(calculate_rsi(&data, period))
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
    m.add_function(wrap_pyfunction!(get_supertrend, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_probability, m)?)?;
    Ok(())
}
