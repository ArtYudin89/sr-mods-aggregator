# SR HD Mods Aggregator

Пайплайн агрегации модов Space Rangers HD: скачивает бинари модов с Google Drive,
декомпилирует `.scr` в исходники RSON, складывает мелкие исходники в этот репозиторий,
а код и ассеты — content-addressed чанками на **Hugging Face**. Генерирует **дескрипторы**
модов и **каталог** для лаунчера. Может обновляться **сам в облаке** (GitHub Actions) без
включённого ПК. Источники сгруппированы по **лагерям** (camps): `redux` и `universe`
(плюс `shared`).

Связанные репозитории: декомпилятор `rson-decompiler`, лаунчер игрока `sr-mods-launcher`.

## Структура

```
mods.config.json          конфиг: units + camps + asset_policy (ведётся вручную)
pipeline/aggregate.py     пайплайн (декомпиляция, манифесты, HF, дескрипторы)
pipeline/notify.py        Telegram-уведомления автообновления (UTF-8)
update_base.bat           локальный прогон тяжёлого юнита (redux_base) по уведомлению
state/lock.json           идемпотентность: remote_sig каждого юнита
state/asset_index.json    карта блобов: sha256 -> {chunk, size}; чанк -> {url, store, kind, group}
state/packs.json          тиры юнитов: base / fix (+fix_parent) / mod / assets (для совместимости)
state/manual_pending.json  тяжёлые юниты, ждущие локального прогона
state/cloud_summary.json   сводка облачного прогона (для Telegram-итога)
descriptors/<camp>/<unit>/<modid>.json   дескриптор каждого (источник, мод)
descriptors/catalog.json  каталог: мод -> варианты (из разных паков) + дефолт
mods/<camp>/<unit>/
    meta.json             версия, дата, источник, sha256, счётчики
    rson/<Script>/*.rson  декомпилированные исходники (+ Lang.txt)
    code/<...>            мелкие файлы verbatim (.scr, CFG, txt — по asset_policy)
    code.manifest.json    код: путь -> {sha256, size}
    assets.manifest.json  большие файлы: путь -> {sha256, size}
.github/workflows/        автообновление в облаке (см. docs/CI_AUTOUPDATE.md)
cache/ dist/ _extract/ _rson_tmp/ _*chunks/   рабочие каталоги (в .gitignore)
```

В git коммитятся **только мелкие исходники/конфиги/манифесты/дескрипторы**. Байты кода и
ассетов не коммитятся — они лежат на Hugging Face (см. ниже).

## Хранение (Hugging Face, content-addressed)

И код, и ассеты адресуются по `sha256` (дедуп: одинаковый файл хранится один раз) и пакуются
в zip-чанки **по модам** (`mod_key`), которые заливаются в публичный датасет HF
(`asset_store.hf_repo`, напр. `Artyudin/sr-mods-assets`).

- `state/asset_index.json` — единая карта: `blobs[sha] = {chunk, size}`;
  `chunks[имя] = {url, store:"hf", kind:"asset"|"code", group:<mod_key>, blob_count}`.
- Заливка папки чанков юнита — **одним коммитом** через `_hf_put_folder` (subprocess + таймаут
  420с + ретраи; резюмируемо). Обязательно `HF_HUB_DISABLE_XET=1` (Xet-бэкенд из РФ = 403).
- Токен HF — только через env `HF_TOKEN` (в git/конфиг не пишется).

Лаунчер собирает мод/пак так: по `code.manifest`+`assets.manifest` берёт нужные sha, по
`asset_index` находит чанк и `url`, качает, извлекает запись `<sha256>`, кладёт по пути.

## Дескрипторы и совместимость (для лаунчера)

- `--descriptors` строит на каждый **(источник, мод)** самоописываемый `descriptors/.../<id>.json`
  (мета из `ModuleInfo.txt`, отфильтрованные манифесты, `depends`/`conflicts`, `version`=хэш,
  `chunk_index_url`) и `catalog.json` (группировка по логическому id с вариантами из разных
  паков). Заодно пишет `state/packs.json` — тир каждого юнита: **base** (пак с `Rangers.exe`),
  **fix** (+`fix_parent`), **mod**, **assets**; `update_required` для base/fix.
- Лаунчер по этим данным резолвит набор (зависимости), показывает конфликты и проверяет
  совместимость (одна база, фиксы к родителю, сейвы при смене базы).

## Автообновление в облаке (без ПК)

GitHub Actions (`.github/workflows/`, подробно — `docs/CI_AUTOUPDATE.md`):

- **`sync-descriptors`** — при пуше манифестов/индекса пересобирает дескрипторы + публикует
  индекс на HF.
- **`auto-update`** — ежедневный (cron 03:00 UTC) инкрементальный прогон: детектит изменения
  на GDrive по `remote_sig`, качает/декомпилирует только изменённые, заливает на HF,
  пересобирает дескрипторы, пушит. Шлёт **Telegram-итог** обновлённых паков.
- **Тяжёлые юниты** (`manual:true`, напр. `redux_base` ~12 ГБ — не влезает в раннер): облако их
  не качает, только детектит и шлёт **Telegram-уведомление**; обновляешь локально через
  **`update_base.bat`**.

Секреты (Settings → Secrets → Actions): `REPO_PAT`, `HF_TOKEN`, `RCLONE_CONF`,
`TG_BOT_TOKEN`, `TG_CHAT_ID`.

## Конфиг (`mods.config.json`)

```jsonc
{
  "decompiler_run_py": "../rson_decompiler/run.py",
  "github": { "repo": "owner/repo" },
  "asset_store": { "type": "hf", "hf_repo": "Artyudin/sr-mods-assets", "public": true },
  "rclone": { "remote": "gdrive" },          // OAuth-remote для shared/метаданных
  "asset_policy": {
    "code_ext": [".scr", ".rson", ".txt", ".cfg", ".dat", ".bat", ".ini"],
    "code_max_bytes": 2097152,                // код = ext в code_ext И размер <= лимита
    "chunk_max_mb": 512
  },
  "camps": { "redux": {...}, "universe": {...} },
  "units": [
    {
      "name": "redux_base_installer",  // слаг -> путь в репозитории (ASCII)
      "camp": "redux",                 // redux | universe | shared
      "display_name": "Universe Redux — установщик",
      "role": "pack",                  // pack | mod | fixes | assets
      "load_order": 10,
      "gdrive": "https://drive.google.com/file/d/<ID>",
      "kind": "file",                  // file | folder
      "enabled": true,
      "manual": true,                  // опц.: тяжёлый — в облаке только детект+уведомление
      "fix_parent": "...",             // опц. (для fixes): родительский пак
      "access": "shared"               // опц.: "shared" -> скачивание через rclone
    }
  ]
}
```

## Запуск

```bash
python pipeline/aggregate.py --commit          # прогон по включённым юнитам + git commit
python pipeline/aggregate.py --only drkles_mod # один юнит (даже если enabled:false)
python pipeline/aggregate.py --camp redux      # только лагерь
python pipeline/aggregate.py --cloud --commit  # облачный режим (manual-юниты — только детект)
python pipeline/aggregate.py --no-download     # из cache/ (без скачивания)
python pipeline/aggregate.py --force           # игнорировать lock

# Хранение на HF (нужен env HF_TOKEN):
python pipeline/aggregate.py --assets --fetch --lean   # ассеты изменённых юнитов -> HF
python pipeline/aggregate.py --code-track              # код по модам -> HF
python pipeline/aggregate.py --publish-index           # залить asset_index.json на HF
python pipeline/aggregate.py --regroup                 # перегруппировать ассеты по модам

# Дескрипторы/каталог/packs (декомпилятор не нужен — работает и в облаке):
python pipeline/aggregate.py --descriptors

python pipeline/probe_access.py                # карта доступности GDrive-ссылок
```

## Зависимости

- Python 3.9+, `gdown` (публичный GDrive), `requests`, `huggingface_hub`
- `rclone` (OAuth-remote `gdrive`) — для `access:shared` и метаданных skip-if-unchanged
- 7-Zip / `tools/innounp/innounp.exe` (вендорен) — для `.rar`/`.7z` и Inno Setup 6.4.x
- `gh` CLI — для git-операций/секретов

## Идемпотентность

Перед скачиванием пайплайн запрашивает у Google Drive **отпечаток источника без загрузки**
и сравнивает с `state/lock.json` (`remote_sig`): файл — `sha256Checksum` через Drive API;
папка — `rclone lsjson -R --hash`. Не изменился — **не скачивается вообще** (секунды вместо
сотен МБ). Откат при недоступном rclone — скачать и сравнить `sha256`. HF-заливка дедуплицирует
по `asset_index.json`: повторный прогон не перезаливает уже загруженные блобы.
