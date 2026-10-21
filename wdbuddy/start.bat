@echo off
setlocal
cd /d "%~dp0"

where node.exe >nul 2>&1
if errorlevel 1 (
  echo [WDBuddy] Node.js was not found. Install Node.js 20.11 or newer first.
  exit /b 1
)

where pnpm.cmd >nul 2>&1
if errorlevel 1 (
  echo [WDBuddy] pnpm was not found. Run this command in PowerShell:
  echo   npm.cmd install --global pnpm@9.12.3
  exit /b 1
)

if not exist "node_modules\.modules.yaml" (
  echo [WDBuddy] Dependencies are missing. Run:
  echo   pnpm.cmd install --frozen-lockfile
  echo   node scripts/rebuild-electron-natives.mjs
  exit /b 1
)

call pnpm.cmd dev
exit /b %errorlevel%
