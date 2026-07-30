# SR Mods Aggregator — правила для Claude

Public `ArtYudin89/sr-mods-aggregator`, ПРОД: ночной cron GitHub Actions 03:00 UTC (`auto-update.yml`), лаунчер читает каталог live. Ядро `pipeline/aggregate.py` (Py 3.9). Живой статус — в памяти `project-sr-mods-aggregator`.

## Регламенты (нарушение = сломанный прод)
- **Реконсиляция с ночным ботом:** `git reset --hard origin/master` → `git checkout <мой-commit> -- <файлы кода>` → regen поверх свежего контента → commit+push. Артефакты (манифесты/дескрипторы) руками НЕ мержить.
- **НЕ пушить локально собранные (Windows/CRLF) манифесты облачных юнитов** — Linux-раннер их sha не сматчит. Локально коммитить только код; данные откатывать `git checkout -- mods descriptors`.
- **Локальный реген дескрипторов:** монкипатчить `A._build_code_manifest = lambda cd, prev=None: dict(prev or {})` — строить от committed-манифестов (иначе self-heal с диска даёт CRLF-churn).
- Конфиг/данные НЕ прогонять через json.dump — точечный `str.replace` (`write_json` уже даёт round-trip).
- **НЕ удалять старое (HF/git), пока новое не проверено залитым** (инцидент −22 ГБ; предохранитель <90% есть, но правило главнее).

## Данные
- `mods.config.json`: units (1 unit = 1 раздача GDrive; name/camp/role/load_order/kind/enabled/manual/fix_parent). Мод = папка с `ModuleInfo.txt` (не mod_key).
- `redux_base` (~12 ГБ) `manual:true` → TG-алерт → локальный `update_base.bat`.
- Фолд фикс-оверлеев: `_fold_fix_overlays` вшивает файлы role=fixes в дескриптор родителя (`overlaid_fixes:true`); аудит `pipeline/_audit_fixes.py`.

## HF и секреты
- HF: public `Artyudin/sr-mods-assets`; `HF_HUB_DISABLE_XET=1` обязателен; заливать `_hf_put_folder` (upload_folder, 1 коммит/юнит), НЕ per-file. SSL-EOF флейки = DPI, лечится ретраем.
- Secrets Actions: `HF_TOKEN`, `RCLONE_CONF` — срезать BOM; TG слать из облака (`pipeline/notify.py`), из РФ api.telegram.org режется.
- Локально: `HF_TOKEN` из `[Environment]::GetEnvironmentVariable('HF_TOKEN','User')` — в вывод не печатать.

## Форс-прогон облака
`gh workflow run auto-update.yml -f force=true` (+`-f only=<unit>`). `gh run watch` транзиентно падает — проверять `--json status`; `gh workflow run` бывает 502 (ретрай). redux_base локально: `--only redux_base_installer --force --lean` → `--code-track` → `--descriptors` → `--publish-index` → push.
