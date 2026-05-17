$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "RealEnglish" -ForegroundColor Green

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command", "cd '$root\backend'; Write-Host 'Backend (port 8000)...' -ForegroundColor Cyan; ..\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
)

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command", "cd '$root\frontend'; Write-Host 'Frontend (port 5173)...' -ForegroundColor Cyan; npm run dev"
)
