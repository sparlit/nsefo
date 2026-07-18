use pyo3::prelude::*;
mod strategies;
mod analysis;
mod http;

use http::{http_post, http_get};
use strategies::trend::supertrend;
use strategies::mean_reversion::calculate_rsi;
use strategies::volatility::{calculate_volatility, calculate_annualized_volatility};
use analysis::probability::assess_winning_probability;

#[pyfunction]
fn get_rsi_list(data: Vec<f64>, period: usize) -> PyResult<Vec<f64>> {
    Ok(calculate_rsi(&data, period))
}

#[pyfunction]
fn get_volatility_list(data: Vec<f64>, period: usize) -> PyResult<Vec<f64>> {
    Ok(calculate_volatility(&data, period))
}

/// Annualized volatility from log-return standard deviation.
/// Returns the same length as input, with the first `period` values set to 0.0
/// until enough prices accumulate to compute a valid log-return window.
#[pyfunction]
fn get_annualized_volatility_list(data: Vec<f64>, period: usize) -> PyResult<Vec<f64>> {
    Ok(calculate_annualized_volatility(&data, period))
}

/// Average True Range — exposed so Python can use ATR for stop-loss sizing
/// without having to duplicate the High/Low/Close Bar construction.
#[pyfunction]
fn get_atr_list(high: Vec<f64>, low: Vec<f64>, close: Vec<f64>, period: usize) -> PyResult<Vec<f64>> {
    Ok(strategies::trend::calculate_atr(&high, &low, &close, period))
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
fn nsefo_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_rsi_list, m)?)?;
    m.add_function(wrap_pyfunction!(get_volatility_list, m)?)?;
    m.add_function(wrap_pyfunction!(get_annualized_volatility_list, m)?)?;
    m.add_function(wrap_pyfunction!(get_atr_list, m)?)?;
    m.add_function(wrap_pyfunction!(get_supertrend, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_probability, m)?)?;
    m.add_function(wrap_pyfunction!(http_post, m)?)?;
    m.add_function(wrap_pyfunction!(http_get, m)?)?;
    Ok(())
}