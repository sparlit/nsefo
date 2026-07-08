use ta::indicators::AverageTrueRange;
use ta::{Next, High, Low, Close};

struct Bar {
    h: f64,
    l: f64,
    c: f64,
}

impl High for Bar {
    fn high(&self) -> f64 { self.h }
}
impl Low for Bar {
    fn low(&self) -> f64 { self.l }
}
impl Close for Bar {
    fn close(&self) -> f64 { self.c }
}

pub fn calculate_atr(high: &[f64], low: &[f64], close: &[f64], period: usize) -> Vec<f64> {
    let mut atr = AverageTrueRange::new(period).unwrap();
    let mut results = Vec::new();
    for i in 0..high.len() {
        let bar = Bar { h: high[i], l: low[i], c: close[i] };
        results.push(atr.next(&bar));
    }
    results
}

pub fn supertrend(high: &[f64], low: &[f64], close: &[f64], period: usize, multiplier: f64) -> (Vec<f64>, Vec<i8>) {
    let atr_values = calculate_atr(high, low, close, period);
    let mut trend = vec![1; high.len()];
    let mut supertrend = vec![0.0; high.len()];

    for i in 1..high.len() {
        let hl2 = (high[i] + low[i]) / 2.0;
        let upper_band = hl2 + (multiplier * atr_values[i]);
        let lower_band = hl2 - (multiplier * atr_values[i]);

        if close[i] > supertrend[i-1] {
            trend[i] = 1;
        } else if close[i] < supertrend[i-1] {
            trend[i] = -1;
        } else {
            trend[i] = trend[i-1];
        }

        if trend[i] == 1 {
            supertrend[i] = if lower_band > supertrend[i-1] { lower_band } else { supertrend[i-1] };
        } else {
            supertrend[i] = if upper_band < supertrend[i-1] { upper_band } else { supertrend[i-1] };
        }
    }
    (supertrend, trend)
}
