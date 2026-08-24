@echo off
rem Emits many lines, then exits with the code passed as %1.
rem Volume matters: early termination can only be observed if the producer is
rem still running when the consumer stops reading.
for /L %%i in (1,1,20000) do @echo line%%i
exit /b %1
