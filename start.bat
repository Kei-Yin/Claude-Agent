@echo off
setlocal
cd /d "%~dp0"
call conda run --no-capture-output -n LLMs python -X utf8 -m src.myclaude %*
exit /b %errorlevel%
