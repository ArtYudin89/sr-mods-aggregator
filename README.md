# SR HD Mods Aggregator

Пайплайн агрегации модов Space Rangers HD: скачивает бинари модов с Google Drive,
декомпилирует `.scr` в исходники RSON, складывает их в этот репозиторий и публикует
GitHub Release с оригинальными бинарями.

## Структура

```
mods.config.json        список модов (ведётся вручную)
pipeline/aggregate.py    пайплайн
state/lock.json          идемпотентность: sha256 каждого скачанного архива
mods/<modpack>/<mod>/
    meta.json            версия, дата, ссылка-источник, sha256
    src/<Script>/*.rson  декомпилированные исходники (+ Lang.txt)
cache/  dist/  _extract/  _rson_tmp/   рабочие каталоги (в .gitignore)
```

В git коммитятся **только исходники RSON** + `meta.json`. Оригинальные бинари модов
не хранятся в репозитории — они скачиваются в `dist/` и прикладываются к GitHub Release.

## Конфиг (`mods.config.json`)

```jsonc
{
  "decompiler_run_py": "../rson_decompiler/run.py",   // путь к готовому декомпилятору
  "github": { "repo": "owner/repo", "release_tag_prefix": "build-" },
  "mods": [
    {
      "name": "DrKlesMod",          // имя -> папка в репозитории (ASCII)
      "modpack": "KlessMod",        // мод-пак (null/"" -> _standalone)
      "display_name": "Клесс мод",  // отображаемое имя (любая кодировка)
      "author": "DrKles",
      "gdrive": "https://drive.google.com/file/d/<ID>/view",
      "kind": "file",               // "file" | "folder"
      "archive": "auto",            // auto|zip|rar|7z|none
      "known_version": "",
      "enabled": true
    }
  ]
}
```

## Запуск

```bash
python pipeline/aggregate.py                 # полный прогон по конфигу
python pipeline/aggregate.py --no-download   # из cache/ (без скачивания)
python pipeline/aggregate.py --check         # + контрольная пересборка (медленно)
python pipeline/aggregate.py --commit        # + git commit изменившихся исходников
python pipeline/aggregate.py --release        # + GitHub Release (нужен gh CLI)
python pipeline/aggregate.py --only DrKlesMod # только один мод
python pipeline/aggregate.py --force          # игнорировать lock
```

## Зависимости

- Python 3.9+, `gdown` (скачивание с Google Drive), `requests`
- 7-Zip (`C:\Program Files\7-Zip\7z.exe`) — для `.rar`/`.7z`
- `gh` CLI — для публикации релизов (`winget install GitHub.cli`)

## Идемпотентность

При повторном запуске архив сравнивается по `sha256` с `state/lock.json`.
Если не изменился — распаковка, декомпиляция и укладка пропускаются.
(Скачивание с публичного Google Drive выполняется всегда — у GDrive нет надёжного
способа узнать хэш без загрузки; зато тяжёлые шаги ниже короткозамыкаются.)
