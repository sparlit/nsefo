//! HTTP client for broker API calls.
//!
//! Uses reqwest (blocking) with rustls TLS. Returns JSON-serializable responses.
//! Exposed as `nsefo_core.http_post()` and `nsefo_core.http_get()`.

use pyo3::prelude::*;
use reqwest::header::{HeaderMap, HeaderName, HeaderValue};
use std::net::{IpAddr, ToSocketAddrs};
use std::str::FromStr;
use std::time::Duration;
use url::Url;

fn _validate_url(url: &Url) -> PyResult<()> {
    // Reject non-HTTP(S) schemes — prevents file://, gopher://, dict:// etc.
    match url.scheme() {
        "http" | "https" => {}
        _ => {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "unsupported URL scheme '{}' — only http/https allowed",
                url.scheme()
            )));
        }
    }

    // Resolve host and reject loopback / private / link-local addresses.
    // This prevents SSRF against internal services (metadata, admin panels, localhost).
    if let Some(host_str) = url.host_str() {
        // Try to parse as IP address directly
        if let Ok(ip) = IpAddr::from_str(host_str) {
            if ip.is_loopback() || ip.is_private() || ip.is_link_local() {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "SSRF blocked: cannot connect to private/reserved IP addresses",
                ));
            }
        } else {
            // It's a hostname — try to resolve it and check the resulting IPs.
            // If resolution fails, allow the request (DNS may be down — let it fail naturally).
            if let Ok(addrs) = (host_str, 80u16).to_socket_addrs() {
                for addr in addrs {
                    if addr.ip().is_loopback() || addr.ip().is_private() || addr.ip().is_link_local() {
                        return Err(pyo3::exceptions::PyValueError::new_err(
                            "SSRF blocked: hostname resolves to a private/reserved IP",
                        ));
                    }
                }
            }
        }
    }

    Ok(())
}

// ─── PyO3 module-level functions ────────────────────────────────────────────

/// Perform an HTTP POST with a JSON body.
///
/// url: str — full URL
/// body_json: str — JSON request body
/// headers_json: Optional[str] — extra headers as JSON string "{\"Key\": \"value\"}"
/// timeout_secs: f64 — request timeout (default 30s)
#[pyfunction]
#[pyo3(signature = (url, body_json, headers_json = None, timeout_secs = 30.0))]
pub fn http_post(
    url: &str,
    body_json: &str,
    headers_json: Option<&str>,
    timeout_secs: f64,
) -> PyResult<String> {
    let parsed = Url::parse(url).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("invalid URL: {}", e))
    })?;

    // SSRF protection: reject private/loopback IPs and non-HTTP schemes
    _validate_url(&parsed)?;

    let mut builder = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs_f64(timeout_secs))
        .connect_timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("reqwest build failed: {}", e)))?
        .post(parsed)
        .header(reqwest::header::CONTENT_TYPE, "application/json")
        .body(body_json.to_string());

    // Apply optional extra headers
    if let Some(h) = headers_json {
        let extra: Vec<(String, String)> = serde_json::from_str(h)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("headers parse error: {}", e)))?;
        let mut header_map = HeaderMap::new();
        for (k, v) in extra {
            if let (Ok(name), Ok(val)) = (HeaderName::from_str(&k), HeaderValue::from_str(&v)) {
                header_map.insert(name, val);
            }
        }
        builder = builder.headers(header_map);
    }

    let resp = builder.send().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("request failed: {}", e))
    })?;

    let status = resp.status();
    let body = resp.text().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("read body failed: {}", e))
    })?;

    if status.is_success() {
        Ok(body)
    } else {
        Err(pyo3::exceptions::PyRuntimeError::new_err(format!(
            "HTTP {}: <{} bytes>",
            status.as_u16(),
            body.len(),
        )))
    }
}

/// Perform an HTTP GET request.
///
/// url: str — full URL
/// headers_json: Optional[str] — extra headers as JSON string "{\"Key\": \"value\"}"
/// timeout_secs: f64 — request timeout (default 30s)
#[pyfunction]
#[pyo3(signature = (url, headers_json = None, timeout_secs = 30.0))]
pub fn http_get(
    url: &str,
    headers_json: Option<&str>,
    timeout_secs: f64,
) -> PyResult<String> {
    let parsed = Url::parse(url).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("invalid URL: {}", e))
    })?;

    // SSRF protection: reject private/loopback IPs and non-HTTP schemes
    _validate_url(&parsed)?;

    let mut builder = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs_f64(timeout_secs))
        .connect_timeout(Duration::from_secs(10))
        .default_headers({
            let mut m = HeaderMap::new();
            m.insert(
                reqwest::header::USER_AGENT,
                HeaderValue::from_static(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
                     (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
            );
            m.insert(
                reqwest::header::ACCEPT,
                HeaderValue::from_static("application/json, text/plain, */*"),
            );
            m.insert(
                reqwest::header::ACCEPT_ENCODING,
                HeaderValue::from_static("gzip, deflate, zstd"),
            );
            m
        })
        .build()
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("reqwest build failed: {}", e)))?
        .get(parsed);

    if let Some(h) = headers_json {
        let extra: Vec<(String, String)> = serde_json::from_str(h)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("headers parse error: {}", e)))?;
        let mut header_map = HeaderMap::new();
        for (k, v) in extra {
            if let (Ok(name), Ok(val)) = (HeaderName::from_str(&k), HeaderValue::from_str(&v)) {
                header_map.insert(name, val);
            }
        }
        builder = builder.headers(header_map);
    }

    let resp = builder.send().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("request failed: {}", e))
    })?;

    let status = resp.status();
    let body = resp.text().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("read body failed: {}", e))
    })?;

    if status.is_success() {
        Ok(body)
    } else {
        Err(pyo3::exceptions::PyRuntimeError::new_err(format!(
            "HTTP {}: <{} bytes>",
            status.as_u16(),
            body.len(),
        )))
    }
}