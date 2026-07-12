//! HTTP client module.
//!
//! Re-exports `http_post` and `http_get` pyfunctions.

mod client;  // declares src/http/client.rs as submodule of http

pub use client::{http_post, http_get};