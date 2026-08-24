@echo off
setlocal enabledelayedexpansion
for /L %%i in (1,1,%1) do @echo line %%i marker
exit /b 1
