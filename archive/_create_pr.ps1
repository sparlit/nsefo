$headers = @{
    "Authorization" = "token YOUR_GITHUB_TOKEN_HERE"
    "Content-Type" = "application/json"
}
$body = @{
    title = "fix(dashboard): correct static path doubling dashboards/dashboards/web/static"
    body = @"
## Summary
- Fixed `_STATIC_DIR` in `dashboards/web/app.py` to resolve to `_BASE_DIR / 'web' / 'static'` instead of `_BASE_DIR / 'dashboards' / 'web' / 'static'`
- The old path caused `RuntimeError: Directory 'dashboards/dashboards/web/static' does not exist` at startup

## Verification
- Dashboard starts and serves on http://localhost:9099
- Homepage: HTTP 200, 31,006 bytes of HTML
- Config endpoint: HTTP 200
"@
    head = "main"
    base = "main"
} | ConvertTo-Json -Depth 10

$r = Invoke-RestMethod -Uri "https://api.github.com/repos/sparlit/nsefo/pulls" -Method Post -Headers $headers -Body $body
Write-Host "PR:" $r.html_url