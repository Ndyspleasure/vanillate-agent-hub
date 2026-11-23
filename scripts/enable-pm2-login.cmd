@echo off
setlocal
cd /d "%~dp0.." || exit /b 1
if not exist ".venv\Scripts\python.exe" (
  echo Python .venv tidak ditemukan di folder repo.
  exit /b 1
)
where pm2.cmd >nul 2>nul || (
  echo Pasang PM2 dahulu dengan npm.cmd install --global pm2
  exit /b 1
)
call pm2.cmd start ecosystem.config.js || exit /b 1
powershell.exe -NoProfile -Command "$ErrorActionPreference='Stop'; $dir=(Get-Location).Path; $shell=New-Object -ComObject WScript.Shell; $file=Join-Path ([Environment]::GetFolderPath('Startup')) 'Vanillate Agent Hub.lnk'; $s=$shell.CreateShortcut($file); $s.TargetPath=(Get-Command pm2.cmd).Source; $s.Arguments='start ecosystem.config.js'; $s.WorkingDirectory=$dir; $s.WindowStyle=7; $s.Save()"
if errorlevel 1 exit /b 1
echo Autostart Vanillate Agent Hub aktif saat login Windows.
