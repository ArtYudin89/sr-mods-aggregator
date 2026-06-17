#!/usr/bin/env python3
"""Space Rangers HD — пайплайн агрегации модов.

Полный цикл: скачать архивы модов с Google Drive -> распаковать ->
прогнать .scr через декомпилятор (RSON) -> разложить исходники в репозиторий ->
(опц.) закоммитить и опубликовать GitHub Release с оригинальными бинарями.

Идемпотентность: state/lock.json хранит sha256 каждого скачанного архива.
Если архив не изменился — распаковка/декомпиляция/коммит пропускаются.

Примеры:
  python pipeline/aggregate.py                      # полный прогон по конфигу
  python pipeline/aggregate.py --no-download        # использовать архивы из cache/
  python pipeline/aggregate.py --check              # с контрольной пересборкой (медленно)
  python pipeline/aggregate.py --commit             # + git commit изменившихся исходников
  python pipeline/aggregate.py --release            # + GitHub Release (нужен gh CLI)
  python pipeline/aggregate.py --only DrKlesMod     # только один мод
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / 'mods.config.json'
LOCK = REPO / 'state' / 'lock.json'
CACHE = REPO / 'cache'
EXTRACT = REPO / '_extract'
RSON_TMP = REPO / '_rson_tmp'
DIST = REPO / 'dist'
MODS = REPO / 'mods'

SEVENZIP = r'C:\Program Files\7-Zip\7z.exe'


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_json(path, default):
    if Path(path).exists():
        return json.loads(Path(path).read_text(encoding='utf-8'))
    return default


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def gdrive_id(url):
    """Достать file id из ссылки вида .../file/d/<ID>/view или ?id=<ID>."""
    import re
    m = re.search(r'/d/([\w-]+)', url) or re.search(r'[?&]id=([\w-]+)', url)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Шаг 1: Скачивание
# ---------------------------------------------------------------------------

def download(mod, no_download):
    """Скачать архив мода в cache/<name>.<ext>. Возвращает (path, sha256)."""
    name = mod['name']
    cached = sorted(CACHE.glob(f'{name}.*'))
    cached = [p for p in cached if p.suffix != '.part']

    if no_download:
        if not cached:
            raise FileNotFoundError(f'--no-download, но в cache/ нет архива для {name}')
        path = cached[0]
        print(f'    cache: {path.name}')
        return path, sha256_file(path)

    import gdown
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = CACHE / f'{name}.part'
    if tmp.exists():
        tmp.unlink()

    if mod.get('kind') == 'folder':
        out_dir = CACHE / f'{name}.folder'
        if out_dir.exists():
            shutil.rmtree(out_dir)
        gdown.download_folder(url=mod['gdrive'], output=str(out_dir), quiet=True)
        # папку упаковываем не будем — отдаём каталог как «архив»
        return out_dir, _dir_hash(out_dir)

    gid = gdrive_id(mod['gdrive'])
    if not gid:
        raise ValueError(f'не удалось распознать file id в ссылке: {mod["gdrive"]}')
    gdown.download(id=gid, output=str(tmp), quiet=True)

    ext = _sniff_ext(tmp)
    final = CACHE / f'{name}{ext}'
    digest = sha256_file(tmp)
    # сравним со старым: если совпало — оставляем старый, новый удаляем
    if final.exists() and sha256_file(final) == digest:
        tmp.unlink()
        print(f'    без изменений: {final.name}')
        return final, digest
    if final.exists():
        final.unlink()
    tmp.rename(final)
    print(f'    скачан: {final.name} ({final.stat().st_size // (1<<20)} MB)')
    return final, digest


def _dir_hash(d):
    h = hashlib.sha256()
    for p in sorted(Path(d).rglob('*')):
        if p.is_file():
            h.update(p.name.encode('utf-8', 'replace'))
            h.update(str(p.stat().st_size).encode())
    return h.hexdigest()


def _sniff_ext(path):
    """Определить расширение архива по магическим байтам."""
    with open(path, 'rb') as f:
        magic = f.read(8)
    if magic[:4] == b'PK\x03\x04':
        return '.zip'
    if magic[:4] == b'Rar!':
        return '.rar'
    if magic[:6] == b'7z\xbc\xaf\x27\x1c':
        return '.7z'
    return '.bin'


# ---------------------------------------------------------------------------
# Шаг 2: Распаковка (с учётом CP866-имён в zip)
# ---------------------------------------------------------------------------

def extract(archive, dest):
    """Распаковать архив в dest. Возвращает Path(dest)."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    if Path(archive).is_dir():           # gdrive folder — просто копируем
        shutil.copytree(archive, dest, dirs_exist_ok=True)
        return dest

    suf = Path(archive).suffix.lower()
    if suf == '.zip':
        _extract_zip_cp866(archive, dest)
    elif suf in ('.rar', '.7z'):
        if not Path(SEVENZIP).exists():
            raise RuntimeError(f'нужен 7-Zip для {suf}: {SEVENZIP} не найден')
        subprocess.run([SEVENZIP, 'x', '-y', f'-o{dest}', str(archive)],
                       check=True, stdout=subprocess.DEVNULL)
    else:
        raise RuntimeError(f'неизвестный формат архива: {archive}')
    return dest


def _extract_zip_cp866(archive, dest):
    """zip из SR-сообществ хранит имена в CP866 (DOS). zipfile читает их как
    cp437 — перекодируем обратно, иначе кириллица в путях ломается."""
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            name = info.filename
            if not (info.flag_bits & 0x800):   # нет UTF-8 флага -> cp437->cp866
                try:
                    name = name.encode('cp437').decode('cp866')
                except Exception:
                    pass
            target = dest / name
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(target, 'wb') as out:
                shutil.copyfileobj(src, out)


# ---------------------------------------------------------------------------
# Шаг 3: Декомпиляция через готовую CLI-утилиту
# ---------------------------------------------------------------------------

def decompile(extracted, out_dir, run_py, check):
    """Прогнать декомпилятор по распакованному каталогу. Возвращает кол-во .rson."""
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    scr = list(Path(extracted).rglob('*.scr'))
    if not scr:
        print('    .scr не найдены — пропуск декомпиляции')
        return 0

    cmd = [sys.executable, str(run_py), str(extracted), '--out-dir', str(out_dir)]
    if check:
        cmd.append('--check')
    print(f'    декомпиляция {len(scr)} .scr ...')
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                         errors='replace')
    # последняя строка с итогами полезна в лог
    tail = [l for l in res.stdout.splitlines() if l.strip()][-3:]
    for l in tail:
        print('      ' + l)
    if res.returncode != 0:
        print('      [decompiler stderr]', (res.stderr or '').strip()[:300])
    return len(list(out_dir.rglob('*.rson')))


def collect_sources(out_dir, src_dir):
    """Скопировать только исходники (.rson + Lang.txt) в репозиторий.
    Бинари (.scr/_check.scr/Lang.dat) в git не кладём."""
    if src_dir.exists():
        shutil.rmtree(src_dir)
    src_dir.mkdir(parents=True)
    n = 0
    for script_dir in sorted(p for p in out_dir.iterdir() if p.is_dir()):
        dest = src_dir / script_dir.name
        dest.mkdir(parents=True, exist_ok=True)
        for f in script_dir.iterdir():
            if f.suffix == '.rson' or f.name.lower() == 'lang.txt':
                shutil.copy2(f, dest / f.name)
                if f.suffix == '.rson':
                    n += 1
    return n


# ---------------------------------------------------------------------------
# Шаг 4: meta + dist + git + release
# ---------------------------------------------------------------------------

def write_meta(mod, meta_path, digest, archive_name, n_rson):
    save_json(meta_path, {
        'name': mod['name'],
        'modpack': mod.get('modpack') or None,
        'display_name': mod.get('display_name') or mod['name'],
        'author': mod.get('author') or None,
        'source_url': mod['gdrive'],
        'known_version': mod.get('known_version') or None,
        'archive': archive_name,
        'sha256': digest,
        'rson_count': n_rson,
        'updated_at': now_iso(),
    })


def stage_dist(archive, mod):
    """Положить оригинальный бинарь в dist/ для релиза."""
    DIST.mkdir(parents=True, exist_ok=True)
    if Path(archive).is_dir():
        return None
    dest = DIST / f'{mod["name"]}{Path(archive).suffix}'
    shutil.copy2(archive, dest)
    return dest


def git(*args):
    return subprocess.run(['git', '-C', str(REPO), *args],
                          capture_output=True, text=True, encoding='utf-8',
                          errors='replace')


def git_commit(changed):
    if not (REPO / '.git').exists():
        git('init')
    # локальный identity (только если не задан глобально/локально) — чтобы
    # коммит проходил «из коробки»; пользователь может переопределить.
    if not git('config', 'user.email').stdout.strip():
        git('config', 'user.email', 'sr-mods-bot@localhost')
        git('config', 'user.name', 'SR Mods Aggregator')
        print('  git: задан локальный identity (переопредели git config при желании)')
    git('add', '-A')
    status = git('status', '--porcelain').stdout.strip()
    if not status:
        print('  git: изменений нет')
        return None
    msg = 'Обновление модов: ' + ', '.join(changed)
    res = git('commit', '-m', msg)
    if res.returncode != 0:
        print('  git: ошибка коммита ->', (res.stderr or res.stdout).strip()[:300])
        return None
    rev = git('rev-parse', '--short', 'HEAD').stdout.strip()
    print(f'  git: коммит {rev} — {msg}')
    return rev


def make_changelog(changed, lock_before, lock_after):
    lines = [f'# Сборка {now_iso()}', '']
    for name in changed:
        b = lock_before.get(name, {})
        a = lock_after.get(name, {})
        old = (b.get('sha256') or '')[:8] or 'нет'
        new = (a.get('sha256') or '')[:8]
        lines.append(f'- **{name}**: {old} -> {new}')
    if not changed:
        lines.append('- изменений нет')
    return '\n'.join(lines)


def publish_release(repo_slug, tag, changelog, assets):
    gh = shutil.which('gh')
    if not gh:
        print('  release: gh CLI не найден — пропуск (установи: winget install GitHub.cli)')
        return
    notes = REPO / 'state' / 'last_changelog.md'
    notes.write_text(changelog, encoding='utf-8')
    cmd = [gh, 'release', 'create', tag, '-R', repo_slug,
           '-t', tag, '-F', str(notes)]
    cmd += [str(a) for a in assets if a]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                         errors='replace')
    if res.returncode == 0:
        print(f'  release: опубликован {tag}')
    else:
        print('  release: ошибка ->', (res.stderr or res.stdout).strip()[:300])


# ---------------------------------------------------------------------------
# Главный цикл
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description='Пайплайн агрегации модов SR HD',
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument('--config', default=str(CONFIG))
    ap.add_argument('--no-download', action='store_true', help='использовать архивы из cache/')
    ap.add_argument('--check', action='store_true', help='контрольная пересборка (медленно)')
    ap.add_argument('--commit', action='store_true', help='git commit изменившихся исходников')
    ap.add_argument('--release', action='store_true', help='опубликовать GitHub Release')
    ap.add_argument('--only', default=None, help='обработать только мод с этим name')
    ap.add_argument('--force', action='store_true', help='игнорировать lock (обработать всё заново)')
    a = ap.parse_args()

    cfg = load_json(a.config, None)
    if cfg is None:
        print(f'ERROR: конфиг не найден: {a.config}', file=sys.stderr)
        sys.exit(1)

    run_py = (REPO / cfg['decompiler_run_py']).resolve()
    if not run_py.exists():
        print(f'ERROR: декомпилятор не найден: {run_py}', file=sys.stderr)
        sys.exit(1)

    lock_before = load_json(LOCK, {})
    lock = dict(lock_before)
    changed = []
    dist_assets = {}

    mods = [m for m in cfg['mods'] if m.get('enabled', True)]
    if a.only:
        mods = [m for m in mods if m['name'] == a.only]

    for mod in mods:
        name = mod['name']
        print(f'\n=== {name} ({mod.get("display_name", name)}) ===')

        archive, digest = download(mod, a.no_download)

        prev = lock_before.get(name, {})
        if not a.force and prev.get('sha256') == digest and not a.check:
            print('  без изменений — пропуск декомпиляции/укладки')
            continue

        extracted = extract(archive, EXTRACT / name)
        rson_out = RSON_TMP / name
        n = decompile(extracted, rson_out, run_py, a.check)

        modpack = mod.get('modpack') or '_standalone'
        mod_dir = MODS / modpack / name
        n_src = collect_sources(rson_out, mod_dir / 'src')
        write_meta(mod, mod_dir / 'meta.json', digest,
                   Path(archive).name, n_src)
        asset = stage_dist(archive, mod)
        if asset:
            dist_assets[name] = asset

        lock[name] = {
            'sha256': digest,
            'archive': Path(archive).name,
            'rson_count': n_src,
            'updated_at': now_iso(),
        }
        changed.append(name)
        print(f'  готово: {n_src} .rson -> {mod_dir.relative_to(REPO)}')

        # уборка временных каталогов этого мода
        shutil.rmtree(extracted, ignore_errors=True)
        shutil.rmtree(rson_out, ignore_errors=True)

    save_json(LOCK, lock)

    print(f'\n--- Итого: изменилось {len(changed)} из {len(mods)} ---')
    if changed:
        print('   ' + ', '.join(changed))

    if a.commit or a.release:
        rev = git_commit(changed)
    if a.release:
        repo_slug = cfg.get('github', {}).get('repo', '')
        if not repo_slug:
            print('  release: не задан github.repo в конфиге — пропуск')
        else:
            tag = cfg['github'].get('release_tag_prefix', 'build-') + \
                  datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
            changelog = make_changelog(changed, lock_before, lock)
            assets = [dist_assets.get(n) for n in changed]
            publish_release(repo_slug, tag, changelog, assets)


if __name__ == '__main__':
    main()
