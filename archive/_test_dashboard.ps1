$env:PYTHONPATH = "."
$job = Start-Job -ScriptBlock {
    Set-Location 'D:\myproject\nsefo'
    python dashboards/web/app.py 2>&1 | Out-Null
} -Name 'nsefo-dashboard'
Start-Sleep -Seconds 3
try {
    $r = Invoke-WebRequest http://localhost:9099/ -TimeoutSec 5 -UseBasicParsing
    Write-Host "HOME: HTTP $($r.StatusCode) length=$($r.Content.Length)"
    Write-Host "HAS_HTML: $($r.Content.Contains('html'))"
} catch {
    Write-Host "HOME ERROR: $_"
}
try {
    $r2 = Invoke-WebRequest http://localhost:9099/config -TimeoutSec 5 -UseBasicParsing
    Write-Host "CONFIG: HTTP $($r2.StatusCode)"
    Write-Host "CONFIG_BODY: $($r2.Content.Substring(0, [Math]::Min(200, $r2.Content.Length)))"
} catch {
    Write-Host "CONFIG ERROR: $_"
}
Stop-Job -Name 'nsefo-dashboard' -ErrorAction SilentlyContinue
Remove-Job -Name 'nsefo-dashboard' -Force -ErrorAction SilentlyContinue