@echo off
chcp 65001 >nul
title Обновление redux_base (локально)
setlocal

REM === Простой локальный прогон тяжёлого юнита redux_base_installer ===
REM Запускать, когда облако прислало уведомление "redux_base обновился".
REM Делает: скачать с GDrive -> декомпилировать -> манифесты -> ассеты+код на HF
REM         -> дескрипторы -> индекс -> commit/push. В конце ждёт нажатия клавиши.

cd /d "%~dp0"

set "PY=%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
if not exist "%PY%" set "PY=python"
set "PATH=%LOCALAPPDATA%\Programs\Python\Python39;C:\Program Files\Git\cmd;C:\Program Files\GitHub CLI;%PATH%"
set "HF_HUB_DISABLE_XET=1"

if "%HF_TOKEN%"=="" (
  echo [!] HF_TOKEN не задан в окружении. Беру из User-переменной...
  for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('HF_TOKEN','User')"`) do set "HF_TOKEN=%%T"
)
if "%HF_TOKEN%"=="" (
  echo [X] HF_TOKEN не найден. Ассеты/код на HF не зальются. Прерываю.
  pause & exit /b 1
)

echo.
echo === [1/6] Подтянуть свежий репозиторий (rebase) ===
git pull --rebase origin master

echo.
echo === [2/6] Скачать + декомпилировать redux_base (это долго, ~12 ГБ) ===
"%PY%" pipeline\aggregate.py --only redux_base_installer --commit --lean
if errorlevel 1 ( echo [X] Ошибка на этапе скачивания/декомпиляции & pause & exit /b 1 )

echo.
echo === [3/6] Ассеты redux_base на Hugging Face ===
"%PY%" pipeline\aggregate.py --assets --only redux_base_installer --fetch --lean

echo.
echo === [4/6] Код redux_base на Hugging Face ===
"%PY%" pipeline\aggregate.py --code-track

echo.
echo === [5/6] Дескрипторы + публикация индекса ===
"%PY%" pipeline\aggregate.py --descriptors
"%PY%" pipeline\aggregate.py --publish-index

echo.
echo === [6/6] Коммит и пуш ===
git add -A
git commit -m "update redux_base (локальный прогон)"
git push origin master || ( git pull --rebase origin master && git push origin master )

echo.
echo ====================================================
echo  ГОТОВО. redux_base обновлён и выложен.
echo ====================================================
pause
endlocal
