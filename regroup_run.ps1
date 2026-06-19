# Перегруппировка ассетов по модам (из HF). Токен наследуется из $env:HF_TOKEN.
$ErrorActionPreference = 'Continue'
$repo = 'C:\claude_sandbox\sr-mods-aggregator'
Set-Location $repo
$env:Path = "$env:LOCALAPPDATA\Programs\Python\Python39;" +
            "C:\Program Files\Git\cmd;C:\Program Files\GitHub CLI;" + $env:Path
$env:HF_HUB_DISABLE_XET = '1'
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "$env:LOCALAPPDATA\Programs\Python\Python39\python.exe" }
$ts  = Get-Date -Format 'yyyyMMdd_HHmmss'
$log = Join-Path $repo "state\regroup_$ts.log"
"=== START $(Get-Date) ===" | Out-File $log -Encoding utf8
if (-not $env:HF_TOKEN) { "ОШИБКА: нет HF_TOKEN" | Out-File $log -Append; exit 1 }

& $py pipeline\aggregate.py --regroup *>> $log

& git add state/asset_index.json *>> $log
& git commit -m "asset_index: перегруппировка ассетов по модам" *>> $log
& git push origin master *>> $log
"=== DONE $(Get-Date) ===" | Out-File $log -Append -Encoding utf8
