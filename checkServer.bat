@echo off
setlocal

set "EXE=C:\accserver\server\accServer.exe"
set "PROC=accServer.exe"
set "WD=C:\accserver\server"

tasklist /FI "IMAGENAME eq %PROC%" | find /I "%PROC%" >NUL
if %ERRORLEVEL%==0 exit /b 0

pushd "%WD%"
start "" "%EXE%"
popd