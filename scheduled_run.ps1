# Полный прогон агрегатора (для планировщика).
# Включает ВСЕ юниты -> скачивание/декомпиляция/укладка -> код-трек релизы -> git push.
# НЕ заливает ассет-байты (--assets ~20ГБ) — это тяжёлое внешнее действие, запускается вручную.
$ErrorActionPreference = 'Continue'
$repo = 'C:\claude_sandbox\sr-mods-aggregator'
Set-Location $repo

# окружение (планировщик может стартовать с урезанным PATH)
$env:Path = "$env:LOCALAPPDATA\Programs\Python\Python39;" +
            "C:\Program Files\Git\cmd;C:\Program Files\GitHub CLI;" + $env:Path
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "$env:LOCALAPPDATA\Programs\Python\Python39\python.exe" }

$ts  = Get-Date -Format 'yyyyMMdd_HHmmss'
$log = Join-Path $repo "state\scheduled_run_$ts.log"
"=== START $(Get-Date) ===" | Out-File $log -Encoding utf8

# 1) включить все юниты
& $py -c "import json; p='mods.config.json'; c=json.load(open(p,encoding='utf-8')); [u.__setitem__('enabled',True) for u in c['units']]; json.dump(c,open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=2); print('enabled', sum(1 for u in c['units'] if u.get('enabled')))" *>> $log

# 2) полный прогон + код-трек релизы (commit внутри pipeline)
& $py pipeline\aggregate.py --release *>> $log

# 3) push
& git push origin master *>> $log

"=== DONE $(Get-Date) ===" | Out-File $log -Append -Encoding utf8
