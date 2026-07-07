@echo off
setlocal

cd /d "%~dp0"

set "PY=%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
if not exist "%PY%" set "PY=python"
set "PATH=%LOCALAPPDATA%\Programs\Python\Python39;C:\Program Files\Git\cmd;C:\Program Files\GitHub CLI;%PATH%"
set "HF_HUB_DISABLE_XET=1"

title Force-reprocess redux_base - backfill dev dates

:: ----- Read HF_TOKEN from user environment variable if not already set -----
if "%HF_TOKEN%"=="" (
  echo [!] HF_TOKEN not set in environment. Reading from User variable...
  for /f "delims=" %%T in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('HF_TOKEN','User')"') do set "HF_TOKEN=%%T"
)
if "%HF_TOKEN%"=="" (
  echo [X] HF_TOKEN not found. Assets/code will not upload to HF. Aborting.
  pause
  exit /b 1
)

echo.
echo === [1/6] Pull fresh repo state (rebase) - fetch 27 cloud units ===
git pull --rebase origin master
if errorlevel 1 (
  echo [X] git pull --rebase failed. Resolve the conflict and re-run.
  pause
  exit /b 1
)

echo.
echo === [2/6] FORCE: download + decompile redux_base (slow, ~12 GB) ===
"%PY%" pipeline\aggregate.py --only redux_base_installer --force --lean
if errorlevel 1 (
  echo [X] Error during download/decompile
  pause
  exit /b 1
)

echo.
echo === [3/6] Assets redux_base to Hugging Face ===
"%PY%" pipeline\aggregate.py --assets --only redux_base_installer --fetch --lean
if errorlevel 1 (
  echo [X] Error uploading assets to HF
  pause
  exit /b 1
)

echo.
echo === [4/6] Code redux_base to Hugging Face ===
"%PY%" pipeline\aggregate.py --code-track
if errorlevel 1 (
  echo [X] code-track failed
  pause
  exit /b 1
)

echo.
echo === [5/6] Descriptors (rebuild catalog over all 28 units) + publish index ===
"%PY%" pipeline\aggregate.py --descriptors
if errorlevel 1 (
  echo [X] descriptor build failed
  pause
  exit /b 1
)
"%PY%" pipeline\aggregate.py --publish-index
if errorlevel 1 (
  echo [X] index publish failed
  pause
  exit /b 1
)

echo.
echo === [6/6] Commit and push ===
git add -A
git commit -m "force-reprocess: dev-mtime in manifests/catalog"
git push origin master || ( git pull --rebase origin master && git push origin master )

echo.
echo ====================================================
echo  DONE. Dev dates backfilled across the whole catalog.
echo ====================================================
pause
endlocal
