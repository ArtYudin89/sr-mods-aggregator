# Код-трек по модам: нарезать code/ по модам и залить на HF + code.manifest.json.
# Токен наследуется из $env:HF_TOKEN (User scope).
$ErrorActionPreference = 'Continue'
$repo = 'C:\claude_sandbox\sr-mods-aggregator'
Set-Location $repo
$env:Path = "$env:LOCALAPPDATA\Programs\Python\Python39;" +
            "C:\Program Files\Git\cmd;C:\Program Files\GitHub CLI;" + $env:Path
$env:HF_HUB_DISABLE_XET = '1'
if (-not $env:HF_TOKEN) {
    $env:HF_TOKEN = [Environment]::GetEnvironmentVariable('HF_TOKEN','User')
}
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "$env:LOCALAPPDATA\Programs\Python\Python39\python.exe" }
$ts  = Get-Date -Format 'yyyyMMdd_HHmmss'
$log = Join-Path $repo "state\code_track_$ts.log"
"=== START $(Get-Date) ===" | Out-File $log -Encoding utf8
if (-not $env:HF_TOKEN) { "ОШИБКА: нет HF_TOKEN" | Out-File $log -Append; exit 1 }

& $py pipeline\aggregate.py --code-track *>> $log

& git add state/asset_index.json "mods/*/*/code.manifest.json" *>> $log
& git commit -m "code-track: код по модам на HF + code.manifest.json" *>> $log
& git push origin master *>> $log
"=== DONE $(Get-Date) ===" | Out-File $log -Append -Encoding utf8
