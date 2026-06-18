# Полная потоковая заливка ассетов в Hugging Face.
# Токен НЕ хранится здесь — наследуется из $env:HF_TOKEN запускающего процесса.
# --assets --fetch --lean: по юниту скачать -> чанки -> залить в HF -> удалить cache.
$ErrorActionPreference = 'Continue'
$repo = 'C:\claude_sandbox\sr-mods-aggregator'
Set-Location $repo
$env:Path = "$env:LOCALAPPDATA\Programs\Python\Python39;" +
            "C:\Program Files\Git\cmd;C:\Program Files\GitHub CLI;" + $env:Path
$env:HF_HUB_DISABLE_XET = '1'      # Xet из РФ = 403, форсим LFS
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "$env:LOCALAPPDATA\Programs\Python\Python39\python.exe" }

$ts  = Get-Date -Format 'yyyyMMdd_HHmmss'
$log = Join-Path $repo "state\asset_upload_$ts.log"
"=== START $(Get-Date) ===" | Out-File $log -Encoding utf8
if (-not $env:HF_TOKEN) { "ОШИБКА: нет HF_TOKEN в окружении" | Out-File $log -Append; exit 1 }

# заливка
& $py pipeline\aggregate.py --assets --fetch --lean *>> $log

# зафиксировать индекс (URL чанков) в репозитории
& git add state/asset_index.json *>> $log
& git commit -m "asset-track: заливка ассетов в HF (обновление asset_index)" *>> $log
& git push origin master *>> $log

"=== DONE $(Get-Date) ===" | Out-File $log -Append -Encoding utf8
