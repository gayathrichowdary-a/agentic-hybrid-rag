@echo off
cd /d "%~dp0frontend"
if not exist .env.local echo NEXT_PUBLIC_API_URL=http://localhost:8000> .env.local
call npm install
echo.
echo Website starting at http://localhost:3000
call npm run dev
pause
