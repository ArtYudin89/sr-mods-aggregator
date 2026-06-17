# SR HD Mods Aggregator

Пайплайн агрегации модов Space Rangers HD: скачивает бинари модов с Google Drive,
декомпилирует `.scr` в исходники RSON, складывает их в этот репозиторий и публикует
GitHub Release. Источники сгруппированы по **лагерям** (camps): `redux` и `universe`
(плюс `shared` — общее для обоих).

## Структура

```
mods.config.json         конфиг: units + camps + asset_policy (ведётся вручную)
pipeline/aggregate.py    пайплайн
pipeline/probe_access.py разведка доступности GDrive-ссылок (public/shared)
state/lock.json          идемпотентность: remote_sig каждого юнита
state/asset_index.json   карта ассетов: sha256 -> чанк -> release_tag
state/access_map.json    карта доступности источников
mods/<camp>/<unit>/
    meta.json            версия, дата, источник, sha256, счётчики
    rson/<Script>/*.rson декомпилированные исходники (+ Lang.txt)
    code/<...>           мелкие файлы verbatim (.scr, CFG, txt — по asset_policy)
    assets.manifest.json большие файлы: путь -> {sha256, size}
cache/ dist/ _extract/ _rson_tmp/ _blobstore/   рабочие каталоги (в .gitignore)
```

В git коммитятся **только мелкие исходники/конфиги** (`rson/`, `code/`, манифесты, meta).
Байты ассетов не коммитятся — они уходят в релизы (см. ниже).

## Релизы (две дорожки)

- **Код-трек** — частые лёгкие релизы на лагерь (`<camp>-code-<дата>`): zip из `rson/`+`code/`.
  Это логика модов (КБ–МБ), меняется часто.
- **Ассет-трек** — редкие тяжёлые. Ассеты адресуются по `sha256` (дедуп между лагерями:
  одинаковый файл хранится один раз), пакуются в zip-чанки **<2 ГБ** и грузятся в релиз
  `assets-<дата>`. `state/asset_index.json` = карта `sha256 → чанк → release_tag`.

**Сборка пака лаунчером (будущее):** для юнита взять `assets.manifest.json` (`путь→sha256`),
по `asset_index.json` найти чанк и его `release_tag`, скачать чанк из релиза, извлечь запись
с именем `<sha256>`, положить по `путь`. Код берётся из код-трек релиза.

## Конфиг (`mods.config.json`)

```jsonc
{
  "decompiler_run_py": "../rson_decompiler/run.py",
  "github": { "repo": "owner/repo", "release_tag_prefix": "" },
  "rclone": { "remote": "gdrive" },          // OAuth-remote для shared/метаданных
  "asset_policy": {
    "code_ext": [".scr", ".rson", ".txt", ".cfg", ".dat", ".bat", ".ini"],
    "code_max_bytes": 2097152                 // код = ext в code_ext И размер <= лимита
  },
  "camps": { "redux": {...}, "universe": {...} },
  "units": [
    {
      "name": "drkles_mod",        // слаг -> путь в репозитории (ASCII)
      "camp": "redux",             // redux | universe | shared
      "display_name": "Dr.Kles Mod",
      "role": "mod",               // pack | mod | fixes | assets
      "load_order": 50,
      "known_version": "",
      "gdrive": "https://drive.google.com/file/d/<ID>",
      "kind": "file",              // file | folder
      "enabled": true,
      "access": "shared"           // опц.: "shared" -> скачивание через rclone
    }
  ]
}
```

## Запуск

```bash
python pipeline/aggregate.py                  # полный прогон по включённым юнитам
python pipeline/aggregate.py --only drkles_mod  # один юнит (даже если enabled:false)
python pipeline/aggregate.py --camp redux     # только лагерь
python pipeline/aggregate.py --no-download    # из cache/ (без скачивания)
python pipeline/aggregate.py --check          # + контрольная пересборка (медленно)
python pipeline/aggregate.py --commit         # + git commit
python pipeline/aggregate.py --release        # + код-трек Release (нужен gh CLI)
python pipeline/aggregate.py --force          # игнорировать lock

# Ассет-трек:
python pipeline/aggregate.py --assets             # упаковать новые блобы в чанки + залить
python pipeline/aggregate.py --assets --no-upload # только собрать чанки локально (предпросмотр)

python pipeline/probe_access.py               # карта доступности GDrive-ссылок
```

## Зависимости

- Python 3.9+, `gdown` (публичный GDrive), `requests`
- `rclone` (OAuth-remote `gdrive`) — для `access:shared` и для метаданных skip-if-unchanged
- 7-Zip (`C:\Program Files\7-Zip\7z.exe`) — для `.rar`/`.7z`
- `gh` CLI — для публикации релизов

## Идемпотентность

Перед скачиванием пайплайн запрашивает у Google Drive **отпечаток источника без загрузки**
и сравнивает с `state/lock.json` (поле `remote_sig`):

- **файл** — `sha256Checksum` через Drive API (токен из настроенного rclone-remote);
- **папка** — `rclone lsjson -R --hash`: sha256 по строкам `путь|размер|sha256` всех файлов.

Не изменился — **файл не скачивается вообще** (секунды вместо сотен МБ). Работает и для
публичных, и для «расшаренных» юнитов. Если rclone недоступен — откат: скачать, затем
сравнить `sha256` загруженного архива. Ассет-трек дедуплицирует по `asset_index.json`:
повторный `--assets` не перезаливает уже загруженные блобы.
