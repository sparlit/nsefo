pub mod probability;

pub struct Signal {
    pub symbol: String,
    pub price: f64,
    pub direction: String,
    pub probability: f64,
}
