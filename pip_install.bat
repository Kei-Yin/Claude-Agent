@echo off
setlocal
call conda run --no-capture-output -n LLMs python -m pip install -r "%~dp0requirements.txt"
exit /b %errorlevel%
