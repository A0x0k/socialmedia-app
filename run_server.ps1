if (-not $env:SECRET_KEY) {
    $env:SECRET_KEY = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 50 | ForEach-Object {[char]$_})
}
$env:DJANGO_SETTINGS_MODULE = "socialmediaproject.settings"
$env:DEBUG = "True"
$env:ALLOWED_HOSTS = "localhost,127.0.0.1"
$env:REDIS_URL = ""

Write-Host "Starting server..." -ForegroundColor Green
Start-Process -FilePath "python" -ArgumentList "manage.py","runserver","0.0.0.0:8000" -WorkingDirectory $PSScriptRoot -PassThru | Select-Object Id | ForEach-Object { Write-Host "Server PID: $($_.Id)" -ForegroundColor Yellow }

Start-Sleep -Seconds 4
Start-Process "http://127.0.0.1:8000/"
Write-Host "Browser opened at http://127.0.0.1:8000/" -ForegroundColor Green