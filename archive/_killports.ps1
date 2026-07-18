$conn = Get-NetTCPConnection -LocalPort 8899 -ErrorAction SilentlyContinue
if ($conn) {
    $conn | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force; Write-Host "Killed PID $($_.OwningProcess)" }
} else {
    Write-Host "Port 8899 is free"
}
$conn8888 = Get-NetTCPConnection -LocalPort 8888 -ErrorAction SilentlyContinue
if ($conn8888) {
    $conn8888 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force; Write-Host "Killed PID $($_.OwningProcess) on 8888" }
} else {
    Write-Host "Port 8888 is free"
}