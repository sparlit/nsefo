use ta::indicators::AverageTrueRange;
use ta::{Next, High, Low, Close};

struct Bar { h: f64, l: f64, c: f64 }
impl High for Bar { fn high(&self) -> f64 { self.h } }
impl Low for Bar { fn low(&self) -> f64 { self.l } }
impl Close for Bar { fn close(&self) -> f64 { self.c } }

pub fn calculate_atr(high: &[f64], low: &[f64], close: &[f64], period: usize) -> Vec<f64> {
    let mut atr = AverageTrueRange::new(period).unwrap();
    high.iter().enumerate().map(|(i, _)| {
        atr.next(&Bar { h: high[i], l: low[i], c: close[i] })
    }).collect()
}

pub fn supertrend(high: &[f64], low: &[f64], close: &[f64], period: usize, multiplier: f64) -> (Vec<f64>, Vec<i8>) {
    let atr_values = calculate_atr(high, low, close, period);
    let mut trend = vec![1; high.len()];
    let mut supertrend = vec![0.0; high.len()];
    for i in 1..high.len() {
        let hl2 = (high[i] + low[i]) / 2.0;
        let up = hl2 + (multiplier * atr_values[i]);
        let dn = hl2 - (multiplier * atr_values[i]);
        if close[i] > supertrend[i-1] { trend[i] = 1; }
        else if close[i] < supertrend[i-1] { trend[i] = -1; }
        else { trend[i] = trend[i-1]; }
        supertrend[i] = if trend[i] == 1 { if dn > supertrend[i-1] { dn } else { supertrend[i-1] } }
                        else { if up < supertrend[i-1] { up } else { supertrend[i-1] } };
    }
    (supertrend, trend)
}
