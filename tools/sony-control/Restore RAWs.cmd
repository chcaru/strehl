@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0restore-raws.ps1" -InputPath "%~1"
if errorlevel 1 pause
