use pyo3::prelude::*;
mod strategies;
mod analysis;

use strategies::trend::calculate_ema;
use analysis::probability::assess_winning_probability;

#[pyfunction]
fn get_ema_list(data: Vec<f64>, period: usize) -> PyResult<Vec<f64>> {
    Ok(calculate_ema(&data, period))
}

#[pyfunction]
fn calculate_probability(indicators: Vec<f64>) -> PyResult<f64> {
    Ok(assess_winning_probability(indicators))
}

#[pymodule]
fn nsefo_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_ema_list, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_probability, m)?)?;
    Ok(())
}
