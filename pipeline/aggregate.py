#!/usr/bin/env python3
"""Space Rangers HD — пайплайн агрегации модов (схема units/camps).

Полный цикл на один заход:
  скачать download-units (файлы/папки Google Drive) -> распаковать ->
  классифицировать файлы код/ассет -> .scr через декомпилятор -> RSON ->
  разложить в репозиторий по лагерям -> content-addressed манифест ассетов ->
  (опц.) git commit + GitHub Release с код-треком по лагерям.

Стратегия релизов (гибрид):
  * КОД-трек  — маленькие частые релизы: .scr + .rson + мелкие CFG (per camp).
  * АССЕТ-трек — большие редкие; манифест 'путь->sha256' пишется сразу
    (дедуп между лагерями, future-ready под лаунчер). Сами байты ассетов
    в этот заход НЕ заливаются — только учитываются в манифесте.

Идемпотентность: state/lock.json по sha256 архива/папки. Не изменился — пропуск.

Примеры:
  python pipeline/aggregate.py --only drkles_mod          # один юнит
  python pipeline/aggregate.py --camp redux --no-download  # лагерь из cache/
  python pipeline/aggregate.py --commit                    # + git commit
  python pipeline/aggregate.py --release                   # + GitHub Release (код-трек)
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


def stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')


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


def human(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return f'{n:.1f}{unit}' if unit != 'B' else f'{n}B'
        n /= 1024


def gdrive_id(url):
    import re
    m = re.search(r'/d/([\w-]+)', url) or re.search(r'[?&]id=([\w-]+)', url) \
        or re.search(r'/folders/([\w-]+)', url)
    return m.group(1) if m else None


def dir_hash(d):
    """Стабильный хэш каталога по (относительный путь, размер)."""
    h = hashlib.sha256()
    for p in sorted(Path(d).rglob('*')):
        if p.is_file():
            h.update(str(p.relative_to(d)).encode('utf-8', 'replace'))
            h.update(b'\0')
            h.update(str(p.stat().st_size).encode())
            h.update(b'\n')
    return h.hexdigest()


_TOKEN_CACHE = {}


def _rclone_token(rclone_exe, remote):
    """Достать свежий OAuth access_token из rclone (для вызовов Drive API)."""
    if remote in _TOKEN_CACHE:
        return _TOKEN_CACHE[remote]
    subprocess.run([rclone_exe, 'about', f'{remote}:'], capture_output=True)  # refresh
    dump = subprocess.run([rclone_exe, 'config', 'dump'], capture_output=True,
                          text=True, encoding='utf-8', errors='replace')
    try:
        tok = json.loads(json.loads(dump.stdout)[remote]['token'])['access_token']
    except Exception:
        return None
    _TOKEN_CACHE[remote] = tok
    return tok


def _drive_file_meta(fid, rclone_exe, remote):
    import requests
    tok = _rclone_token(rclone_exe, remote)
    if not tok:
        return None
    try:
        r = requests.get('https://www.googleapis.com/drive/v3/files/' + fid,
                         params={'fields': 'size,modifiedTime,md5Checksum,sha256Checksum'},
                         headers={'Authorization': 'Bearer ' + tok}, timeout=30)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def remote_signature(unit, rclone_exe, remote):
    """Отпечаток источника GDrive БЕЗ скачивания — для skip-if-unchanged.
      * файл  -> sha256Checksum (Drive API);
      * папка -> sha256 от строк '<path>|<size>|<sha256>' всех файлов (rclone lsjson).
    Возвращает строку или None (метаданные недоступны -> откат к download-then-compare)."""
    if not rclone_exe:
        return None
    gid = gdrive_id(unit['gdrive'])
    if not gid:
        return None
    if unit.get('kind') == 'folder':
        res = subprocess.run([rclone_exe, 'lsjson', '-R', '--hash', f'{remote}:',
                              '--drive-root-folder-id', gid],
                             capture_output=True, text=True, encoding='utf-8',
                             errors='replace')
        if res.returncode != 0:
            return None
        try:
            items = json.loads(res.stdout)
        except Exception:
            return None
        parts = []
        for it in sorted((x for x in items if not x.get('IsDir')),
                         key=lambda x: x['Path']):
            hh = it.get('Hashes') or {}
            h = hh.get('sha256') or hh.get('md5') or ''
            parts.append(f"{it['Path']}|{it.get('Size')}|{h}")
        if not parts:
            return None
        return hashlib.sha256('\n'.join(parts).encode('utf-8', 'replace')).hexdigest()
    meta = _drive_file_meta(gid, rclone_exe, remote)
    if not meta:
        return None
    return meta.get('sha256Checksum') or meta.get('md5Checksum') or None


def _find_rclone():
    rc = shutil.which('rclone')
    if rc:
        return rc
    base = Path(os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Packages'))
    hits = sorted(base.glob('Rclone.Rclone*/**/rclone.exe'))
    return str(hits[0]) if hits else None


def _sniff_ext(path):
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
# Шаг 1: Скачивание (file / folder)
# ---------------------------------------------------------------------------

DL_TIMEOUT = 2400        # сек на одну загрузку файла/папки (анти-зависание)
RCLONE_TIMEOUT = 2400    # сек на rclone copy/copyid
LIST_TIMEOUT = 300       # сек на листинг/метаданные


def _gdown_file(gid, out, timeout=DL_TIMEOUT):
    """Скачать один файл gdown ЧЕРЕЗ subprocess с таймаутом (сам gdown таймаута не имеет).
    Бросает subprocess.TimeoutExpired при зависании (процесс убивается)."""
    url = f'https://drive.google.com/uc?id={gid}'
    res = subprocess.run([sys.executable, '-m', 'gdown', url, '-O', str(out)],
                         timeout=timeout, capture_output=True, text=True,
                         encoding='utf-8', errors='replace')
    return res


def _call_timeout(fn, timeout):
    """Выполнить fn() с жёстким таймаутом (фоновый поток зависшей операции
    отбрасывается — это backstop против бесконечного листинга gdown)."""
    import concurrent.futures as cf
    ex = cf.ThreadPoolExecutor(max_workers=1)
    fut = ex.submit(fn)
    try:
        return fut.result(timeout=timeout)
    finally:
        ex.shutdown(wait=False)


def download_rclone(unit, remote, no_download):
    """Скачать 'расшаренный мне' юнит через rclone (OAuth). path = файл/каталог."""
    name = unit['name']
    is_folder = unit.get('kind') == 'folder'
    gid = gdrive_id(unit['gdrive'])
    if not gid:
        raise ValueError(f'не распознан id: {unit["gdrive"]}')

    if is_folder:
        out = CACHE / f'{name}.folder'
        if no_download:
            if not out.exists():
                raise FileNotFoundError(f'--no-download, нет cache/{name}.folder')
            return out, dir_hash(out)
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        exe = _find_rclone()
        if not exe:
            raise RuntimeError('rclone не найден (winget install Rclone.Rclone)')
        res = subprocess.run([exe, 'copy', f'{remote}:', str(out),
                              '--drive-root-folder-id', gid, '--ignore-errors'],
                             capture_output=True, text=True, encoding='utf-8',
                             errors='replace', timeout=RCLONE_TIMEOUT)
        if not any(out.rglob('*')):
            raise RuntimeError(f'rclone copy папки не удался: {(res.stderr or "")[:200]}')
        return out, dir_hash(out)

    # одиночный файл
    cached = [p for p in CACHE.glob(f'{name}.*')
              if p.suffix not in ('.part', '.folder')]
    if no_download:
        if not cached:
            raise FileNotFoundError(f'--no-download, нет cache/{name}.*')
        return cached[0], sha256_file(cached[0])
    exe = _find_rclone()
    if not exe:
        raise RuntimeError('rclone не найден (winget install Rclone.Rclone)')
    tmp = CACHE / f'{name}.rclone_tmp'
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    res = subprocess.run([exe, 'backend', 'copyid', f'{remote}:', gid, str(tmp)],
                         capture_output=True, text=True, encoding='utf-8',
                         errors='replace', timeout=RCLONE_TIMEOUT)
    got = [p for p in tmp.iterdir() if p.is_file()]
    if res.returncode != 0 or not got:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(f'rclone copyid не удался: {(res.stderr or "")[:200]}')
    src = got[0]
    ext = _sniff_ext(src)
    final = CACHE / f'{name}{ext}'
    digest = sha256_file(src)
    if final.exists():
        final.unlink()
    shutil.move(str(src), str(final))
    shutil.rmtree(tmp, ignore_errors=True)
    print(f'    rclone: {final.name} ({human(final.stat().st_size)})')
    return final, digest


def download(unit, no_download, rclone_remote='gdrive'):
    """Скачать юнит в cache/. Возвращает (path, digest). path = файл или каталог.
    Папки и 'shared'-юниты — через rclone (надёжно для сотен файлов и для приватных);
    одиночные публичные файлы — через gdown."""
    name = unit['name']
    is_folder = unit.get('kind') == 'folder'
    if is_folder or unit.get('access') == 'shared':
        return download_rclone(unit, rclone_remote, no_download)

    if no_download:
        if is_folder:
            d = CACHE / f'{name}.folder'
            if not d.exists():
                raise FileNotFoundError(f'--no-download, нет cache/{name}.folder')
            return d, dir_hash(d)
        cached = [p for p in CACHE.glob(f'{name}.*')
                  if p.suffix not in ('.part', '.folder')]
        if not cached:
            raise FileNotFoundError(f'--no-download, нет cache/{name}.*')
        return cached[0], sha256_file(cached[0])

    import gdown
    CACHE.mkdir(parents=True, exist_ok=True)

    if is_folder:
        out = CACHE / f'{name}.folder'
        out.mkdir(parents=True, exist_ok=True)
        # Пофайлово: один приватный файл не должен ронять всю папку.
        files = _call_timeout(
            lambda: gdown.download_folder(url=unit['gdrive'], skip_download=True,
                                          quiet=True, use_cookies=False,
                                          remaining_ok=True),
            LIST_TIMEOUT)
        if not files:
            raise RuntimeError(f'папка {name} пуста или недоступна')
        got, skipped = 0, []
        for f in files:
            target = out / f.path
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and target.stat().st_size > 0:
                got += 1
                continue                      # уже скачан (грубая идемпотентность)
            try:
                r = _gdown_file(f.id, target)         # subprocess + таймаут
                if target.exists() and target.stat().st_size > 0:
                    got += 1
                else:
                    skipped.append(f.path)
            except Exception:
                skipped.append(f.path)
        if skipped:
            print(f'    ПРОПУЩЕНО {len(skipped)} приватных/недоступных файлов:')
            for s in skipped[:10]:
                print(f'      - {s}')
            save_json(out.parent / f'{name}.skipped.json', skipped)
        if got == 0:
            raise RuntimeError(f'из папки {name} не скачан ни один файл')
        print(f'    папка: {got} файлов скачано/в кэше')
        return out, dir_hash(out)

    gid = gdrive_id(unit['gdrive'])
    if not gid:
        raise ValueError(f'не распознан file id: {unit["gdrive"]}')
    tmp = CACHE / f'{name}.part'
    if tmp.exists():
        tmp.unlink()
    res = _gdown_file(gid, tmp)
    if not tmp.exists() or tmp.stat().st_size == 0:
        raise RuntimeError(f'gdown не скачал {name}: {(res.stderr or res.stdout or "")[:200]}')
    ext = _sniff_ext(tmp)
    final = CACHE / f'{name}{ext}'
    digest = sha256_file(tmp)
    if final.exists() and sha256_file(final) == digest:
        tmp.unlink()
        return final, digest
    if final.exists():
        final.unlink()
    tmp.rename(final)
    print(f'    скачан: {final.name} ({human(final.stat().st_size)})')
    return final, digest


# ---------------------------------------------------------------------------
# Шаг 2: Распаковка (zip с CP866-именами, rar/7z через 7-Zip)
# ---------------------------------------------------------------------------

ARCHIVE_EXT = ('.zip', '.rar', '.7z')


def _find_innounp():
    """innounp для распаковки Inno Setup (в т.ч. 6.4.x)."""
    p = REPO / 'tools' / 'innounp' / 'innounp.exe'
    if p.exists():
        return str(p)
    return shutil.which('innounp')


def _inno_exe(path):
    """Если path (файл/папка) — это Inno Setup установщик, вернуть путь к .exe.
    Иначе None. Использует innounp для распознавания версии."""
    iu = _find_innounp()
    if not iu:
        return None
    cands = []
    p = Path(path)
    if p.is_dir():
        cands = sorted(p.glob('*.exe')) + sorted(p.glob('*.[0-9]'))  # exe или setup.0
    elif p.suffix.lower() == '.exe' or _sniff_ext(p) == '.bin':
        cands = [p]
    for c in cands:
        try:
            r = subprocess.run([iu, '-v', str(c)], capture_output=True, text=True,
                               encoding='utf-8', errors='replace', timeout=LIST_TIMEOUT)
            if 'Inno Setup version detected' in (r.stdout or ''):
                return c
        except Exception:
            continue
    return None


def _innounp_extract(exe, dest):
    """Извлечь Inno-установщик через innounp в dest (создаёт dest/{app}/...)."""
    iu = _find_innounp()
    if not iu:
        raise RuntimeError('innounp не найден (tools/innounp/innounp.exe)')
    dest.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([iu, '-x', '-y', f'-d{dest}', str(exe)],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=RCLONE_TIMEOUT)
    if not any(dest.rglob('*')):
        raise RuntimeError(f'innounp ничего не извлёк: {(r.stderr or r.stdout or "")[:200]}')


def _unpack_one(arc, into):
    suf = arc.suffix.lower()
    if suf == '.zip':
        _extract_zip_cp866(arc, into)
    elif suf in ('.rar', '.7z'):
        if not Path(SEVENZIP).exists():
            raise RuntimeError(f'нужен 7-Zip для {suf}: {SEVENZIP}')
        subprocess.run([SEVENZIP, 'x', '-y', f'-o{into}', str(arc)],
                       check=True, stdout=subprocess.DEVNULL)
    else:
        raise RuntimeError(f'неизвестный формат: {arc}')


def extract(archive, dest):
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    # Inno Setup установщик (в т.ч. split .bin-слайсы, 6.4.x) -> innounp
    inno = _inno_exe(archive)
    if inno is not None:
        print(f'    Inno Setup -> innounp: {Path(inno).name}')
        _innounp_extract(inno, dest)
        return dest
    if Path(archive).is_dir():
        shutil.copytree(archive, dest, dirs_exist_ok=True)
    else:
        _unpack_one(Path(archive), dest)
    # Папки часто содержат вложенные архивы (folder-of-zips) — распаковываем
    # их на месте, повторяя пока появляются новые. arc -> arc_unpacked/, arc удаляем.
    for _ in range(6):
        nested = [p for p in dest.rglob('*')
                  if p.is_file() and p.suffix.lower() in ARCHIVE_EXT]
        if not nested:
            break
        for arc in nested:
            sub = arc.parent / (arc.stem + '_unpacked')
            try:
                _unpack_one(arc, sub)
                arc.unlink()
            except Exception as e:
                print(f'    [warn] вложенный архив не распакован: {arc.name} ({e})')
                arc.unlink(missing_ok=True)
    return dest


def _extract_zip_cp866(archive, dest):
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            name = info.filename
            if not (info.flag_bits & 0x800):
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
# Шаг 3: Декомпиляция .scr -> RSON
# ---------------------------------------------------------------------------

def decompile(extracted, out_dir, run_py, check):
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    scr = list(Path(extracted).rglob('*.scr'))
    if not scr:
        return 0
    cmd = [sys.executable, str(run_py), str(extracted), '--out-dir', str(out_dir)]
    if check:
        cmd.append('--check')
    print(f'    декомпиляция {len(scr)} .scr ...')
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                         errors='replace')
    for l in [l for l in (res.stdout or '').splitlines() if l.strip()][-2:]:
        print('      ' + l)
    if res.returncode != 0:
        print('      [decompiler err]', (res.stderr or '').strip()[:200])
    return len(list(out_dir.rglob('*.rson')))


def collect_rson(out_dir, dest):
    """Скопировать исходники (.rson + Lang.txt) в репозиторий."""
    if dest.exists():
        shutil.rmtree(dest)
    n = 0
    for sd in sorted(p for p in out_dir.iterdir() if p.is_dir()):
        td = dest / sd.name
        td.mkdir(parents=True, exist_ok=True)
        for f in sd.iterdir():
            if f.suffix == '.rson' or f.name.lower() == 'lang.txt':
                shutil.copy2(f, td / f.name)
                if f.suffix == '.rson':
                    n += 1
    return n


# ---------------------------------------------------------------------------
# Шаг 4: Классификатор код/ассет
# ---------------------------------------------------------------------------

def classify(extracted, code_dir, policy):
    """Разложить распакованное дерево:
      * код-файлы (ext в code_ext И размер<=code_max) -> копия в code_dir (verbatim);
      * остальное -> ассет: запись в манифест {relpath: {sha256, size}}.
    Возвращает (manifest, code_stats, asset_stats)."""
    code_ext = set(e.lower() for e in policy['code_ext'])
    code_max = policy['code_max_bytes']
    if code_dir.exists():
        shutil.rmtree(code_dir)
    manifest = {}
    code_n = code_b = asset_n = asset_b = 0
    base = Path(extracted)
    for p in sorted(base.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(base).as_posix()
        size = p.stat().st_size
        is_code = p.suffix.lower() in code_ext and size <= code_max
        if is_code:
            dst = code_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
            code_n += 1
            code_b += size
        else:
            manifest[rel] = {'sha256': sha256_file(p), 'size': size}
            asset_n += 1
            asset_b += size
    return manifest, (code_n, code_b), (asset_n, asset_b)


# ---------------------------------------------------------------------------
# git / release
# ---------------------------------------------------------------------------

def git(*args):
    return subprocess.run(['git', '-C', str(REPO), *args],
                          capture_output=True, text=True, encoding='utf-8',
                          errors='replace')


def git_commit(changed):
    if not (REPO / '.git').exists():
        git('init')
    if not git('config', 'user.email').stdout.strip():
        git('config', 'user.email', 'sr-mods-bot@localhost')
        git('config', 'user.name', 'SR Mods Aggregator')
        print('  git: задан локальный identity')
    git('add', '-A')
    if not git('status', '--porcelain').stdout.strip():
        print('  git: изменений нет')
        return None
    msg = 'Обновление: ' + ', '.join(changed)
    res = git('commit', '-m', msg)
    if res.returncode != 0:
        print('  git: ошибка ->', (res.stderr or res.stdout).strip()[:200])
        return None
    rev = git('rev-parse', '--short', 'HEAD').stdout.strip()
    print(f'  git: коммит {rev} — {msg}')
    return rev


def _find_gh():
    gh = shutil.which('gh')
    if gh:
        return gh
    for c in (r'C:\Program Files\GitHub CLI\gh.exe',
              os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Links\gh.exe')):
        if Path(c).exists():
            return c
    return None


def build_code_bundle(camp, units_done):
    """Собрать код-трек лагеря: zip из mods/<camp>/*/{rson,code,meta.json}."""
    DIST.mkdir(parents=True, exist_ok=True)
    zip_path = DIST / f'{camp}-code-{stamp()}.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in units_done:
            ud = MODS / camp / name
            for f in ud.rglob('*'):
                if f.is_file() and f.name != 'assets.manifest.json':
                    z.write(f, f.relative_to(MODS))
    return zip_path


CHUNK_MAX = 1900 * 1024 * 1024     # 1.9 ГБ — запас под лимит ассета GitHub (2 ГБ)
ASSET_INDEX = REPO / 'state' / 'asset_index.json'


def _cached_archive(name, kind):
    if kind == 'folder':
        d = CACHE / f'{name}.folder'
        return d if d.exists() else None
    hits = [p for p in CACHE.glob(f'{name}.*')
            if p.suffix not in ('.part', '.folder')]
    return hits[0] if hits else None


def _scan_blob_usage():
    """Сколько РАЗНЫХ юнитов использует каждый блоб (по всем манифестам в mods/).
    Возвращает (usage: sha->count, blob_unit: sha->первый_юнит)."""
    usage, blob_unit = {}, {}
    for man_path in sorted(MODS.glob('*/*/assets.manifest.json')):
        uname = man_path.parent.name
        shas = {m['sha256'] for m in load_json(man_path, {}).get('files', {}).values()}
        for sh in shas:
            usage[sh] = usage.get(sh, 0) + 1
            blob_unit.setdefault(sh, uname)
    return usage, blob_unit


def build_asset_track(cfg, units, do_upload, repo_slug):
    """Собрать недостающие блобы ассетов в чанки и (опц.) залить в Release.

    Чанки группируются для ЛОКАЛЬНОСТИ скачивания:
      * блоб, используемый >=2 юнитами  -> группа 'shared';
      * блоб уникальный для юнита        -> группа = имя юнита.
    Установка одного юнита тянет только его чанк(и) + shared-чанк(и), а не
    уникальные ассеты чужих юнитов. Дедуп сохраняется (sha256, индекс).
    Размер чанка — asset_policy.chunk_max_mb (по умолчанию 512 МБ)."""
    chunk_max = cfg.get('asset_policy', {}).get('chunk_max_mb', 512) * 1024 * 1024
    index = load_json(ASSET_INDEX, {'blobs': {}, 'chunks': {}})
    seen = set(index['blobs'])
    usage, _ = _scan_blob_usage()
    shared = {sh for sh, c in usage.items() if c >= 2}

    store = REPO / '_blobstore'
    ex_tmp = REPO / '_extract_assets'
    if store.exists():
        shutil.rmtree(store)
    store.mkdir(parents=True)

    sizes = {}                       # sha256 -> size
    group_blobs = {}                 # group -> [sha256, ...]  (group: 'shared' | имя юнита)
    collected = set()
    for unit in units:
        name, camp = unit['name'], unit['camp']
        man_path = MODS / camp / name / 'assets.manifest.json'
        if not man_path.exists():
            continue
        files = load_json(man_path, {}).get('files', {})
        need = {m['sha256'] for m in files.values()} - seen - collected
        if not need:
            print(f'  {name}: новых ассетов нет')
            continue
        arc = _cached_archive(name, unit.get('kind'))
        if not arc:
            print(f'  {name}: нет архива в cache/ — пропуск (нужно скачать)')
            continue
        ext = extract(arc, ex_tmp)
        added = 0
        for rel, m in files.items():
            sh = m['sha256']
            if sh in seen or sh in collected:
                continue
            src = ext / rel
            if not src.exists():
                continue
            shutil.copy2(src, store / sh)
            collected.add(sh)
            sizes[sh] = m['size']
            grp = 'shared' if sh in shared else name
            group_blobs.setdefault(grp, []).append(sh)
            added += 1
        shutil.rmtree(ext, ignore_errors=True)
        print(f'  {name}: +{added} новых блобов')

    if not collected:
        print('Новых ассетов нет — индекс не меняется.')
        shutil.rmtree(store, ignore_errors=True)
        return 0, []

    # Пакуем каждую группу в свои чанки <chunk_max (zip STORED — ассеты уже сжаты).
    DIST.mkdir(parents=True, exist_ok=True)
    base = stamp()
    chunks = []          # [(chunk_path, [sha256, ...])]

    def write_chunk(group, seq, shas):
        cp = DIST / f'assets-{group}-{base}-{seq:03d}.zip'
        with zipfile.ZipFile(cp, 'w', zipfile.ZIP_STORED, allowZip64=True) as z:
            for sh in shas:
                z.write(store / sh, sh)
        chunks.append((cp, list(shas)))

    for group in sorted(group_blobs):
        cur, cur_sz, seq = [], 0, 0
        for sh in sorted(group_blobs[group]):
            size = sizes[sh]
            if size > chunk_max:                 # «гигант» — отдельный чанк
                write_chunk(group, seq, [sh]); seq += 1
                if size > 2 * 1024 * 1024 * 1024:
                    print(f'  [warn] блоб {sh[:12]} = {human(size)} > 2ГБ — GitHub не примет')
                continue
            if cur_sz + size > chunk_max and cur:
                write_chunk(group, seq, cur); seq += 1
                cur, cur_sz = [], 0
            cur.append(sh); cur_sz += size
        if cur:
            write_chunk(group, seq, cur)

    by_group = {}
    for cp, shas in chunks:
        g = cp.name.split('-')[1]
        by_group[g] = by_group.get(g, 0) + 1
    print(f'Собрано чанков: {len(chunks)} (новых блобов: {len(collected)}); '
          f'по группам: {by_group}')

    release_tag = f'assets-{base}'
    if not do_upload:
        # Dry-run: чанки собраны для предпросмотра, индекс НЕ трогаем
        # (блобы ещё не залиты — записывать их как доступные нельзя).
        shutil.rmtree(store, ignore_errors=True)
        print(f'[dry-run] чанки в dist/ ({len(chunks)} шт.), индекс не изменён')
        return len(collected), chunks

    if not repo_slug:
        print('  upload: не задан github.repo — индекс не обновлён')
        shutil.rmtree(store, ignore_errors=True)
        return len(collected), chunks

    notes = f'# Ассет-блобы {now_iso()}\n\nЧанков: {len(chunks)}, блобов: {len(collected)}'
    publish_release(repo_slug, release_tag, notes, [c for c, _ in chunks])

    for cp, shas in chunks:
        g = cp.name.split('-')[1]
        index['chunks'][cp.name] = {'release_tag': release_tag, 'group': g,
                                    'blob_count': len(shas)}
        for sh in shas:
            index['blobs'][sh] = {'chunk': cp.name, 'size': sizes[sh]}
    save_json(ASSET_INDEX, index)
    shutil.rmtree(store, ignore_errors=True)
    print(f'Индекс обновлён: всего блобов {len(index["blobs"])}, чанков {len(index["chunks"])}')
    return len(collected), chunks


def publish_release(repo_slug, tag, notes_text, assets):
    gh = _find_gh()
    if not gh:
        print('  release: gh CLI не найден — пропуск')
        return
    notes = REPO / 'state' / 'last_changelog.md'
    notes.write_text(notes_text, encoding='utf-8')
    cmd = [gh, 'release', 'create', tag, '-R', repo_slug, '-t', tag, '-F', str(notes)]
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
    ap.add_argument('--no-download', action='store_true')
    ap.add_argument('--check', action='store_true', help='контрольная пересборка (медленно)')
    ap.add_argument('--commit', action='store_true')
    ap.add_argument('--release', action='store_true')
    ap.add_argument('--only', default=None, help='только юнит с этим name')
    ap.add_argument('--camp', default=None, help='только лагерь (redux/universe/shared)')
    ap.add_argument('--force', action='store_true', help='игнорировать lock')
    ap.add_argument('--assets', action='store_true',
                    help='режим ассет-трека: упаковать новые блобы в чанки <2ГБ и залить')
    ap.add_argument('--no-upload', action='store_true',
                    help='с --assets: только собрать чанки локально, без Release')
    ap.add_argument('--lean', action='store_true',
                    help='удалять скачанный архив из cache/ после обработки юнита '
                         '(экономит диск; --assets потом потребует пере-скачивания)')
    a = ap.parse_args()

    cfg = load_json(a.config, None)
    if cfg is None:
        print(f'ERROR: конфиг не найден: {a.config}', file=sys.stderr)
        sys.exit(1)

    run_py = (REPO / cfg['decompiler_run_py']).resolve()
    if not run_py.exists():
        print(f'ERROR: декомпилятор не найден: {run_py}', file=sys.stderr)
        sys.exit(1)
    policy = cfg['asset_policy']

    lock_before = load_json(LOCK, {})
    lock = dict(lock_before)
    changed_by_camp = {}
    remote = cfg.get('rclone', {}).get('remote', 'gdrive')
    rclone_exe = _find_rclone()

    if a.only:
        # явно названный юнит запускаем независимо от enabled
        units = [u for u in cfg['units'] if u['name'] == a.only]
    else:
        units = [u for u in cfg['units'] if u.get('enabled', True)]
        if a.camp:
            units = [u for u in units if u['camp'] == a.camp]
    if not units:
        print('Нет включённых юнитов под выбранные фильтры.')
        return

    if a.assets:
        print(f'=== Ассет-трек: {len(units)} юнитов ===')
        build_asset_track(cfg, units, do_upload=not a.no_upload,
                          repo_slug=cfg.get('github', {}).get('repo', ''))
        return

    for unit in units:
        name, camp = unit['name'], unit['camp']
        print(f'\n=== [{camp}] {name} — {unit.get("display_name", name)} ===')

        prev = lock_before.get(name, {})

        # Предзагрузочная проверка: спрашиваем у GDrive контрольную сумму/отпечаток
        # БЕЗ скачивания. Если совпал с локом — не качаем вообще.
        sig = None if a.no_download else remote_signature(unit, rclone_exe, remote)
        if not a.force and not a.check and sig and prev.get('remote_sig') == sig:
            print('  без изменений (метаданные GDrive) — не качаем')
            continue

        try:
            archive, digest = download(unit, a.no_download, remote)
        except Exception as e:
            print(f'  FAIL download: {e}')
            continue

        # Откат для случая, когда метаданные недоступны (sig is None): сравниваем
        # по хэшу уже скачанного файла.
        if not a.force and sig is None and prev.get('sha256') == digest and not a.check:
            print('  без изменений — пропуск')
            continue

        # Изоляция: сбой/таймаут на одном юните не должен ронять весь прогон.
        try:
            extracted = extract(archive, EXTRACT / name)

            rson_tmp = RSON_TMP / name
            decompile(extracted, rson_tmp, run_py, a.check)

            unit_dir = MODS / camp / name
            n_rson = collect_rson(rson_tmp, unit_dir / 'rson')
            manifest, (cn, cb), (an, ab) = classify(extracted, unit_dir / 'code', policy)
            save_json(unit_dir / 'assets.manifest.json',
                      {'asset_count': an, 'asset_bytes': ab, 'files': manifest})
            save_json(unit_dir / 'meta.json', {
                'name': name, 'camp': camp, 'role': unit.get('role'),
                'display_name': unit.get('display_name', name),
                'load_order': unit.get('load_order'),
                'known_version': unit.get('known_version') or None,
                'source_url': unit['gdrive'], 'kind': unit.get('kind'),
                'sha256': digest,
                'rson_count': n_rson,
                'code_files': cn, 'code_bytes': cb,
                'asset_files': an, 'asset_bytes': ab,
                'updated_at': now_iso(),
            })

            lock[name] = {'sha256': digest, 'remote_sig': sig or digest,
                          'camp': camp, 'rson_count': n_rson,
                          'code_files': cn, 'asset_files': an, 'updated_at': now_iso()}
            save_json(LOCK, lock)            # инкрементально — crash-safe прогресс
            changed_by_camp.setdefault(camp, []).append(name)
            print(f'  код: {cn} файлов / {human(cb)} (+{n_rson} .rson)  |  '
                  f'ассеты: {an} / {human(ab)} (в манифесте)')
        except Exception as e:
            print(f'  FAIL обработка {name}: {e}')
        finally:
            shutil.rmtree(EXTRACT / name, ignore_errors=True)
            shutil.rmtree(RSON_TMP / name, ignore_errors=True)
            if a.lean:                       # освободить диск: убрать скачанное
                if isinstance(archive, Path) and archive.is_dir():
                    shutil.rmtree(archive, ignore_errors=True)
                elif isinstance(archive, Path) and archive.exists():
                    archive.unlink()
                for p in CACHE.glob(f'{name}.*'):
                    if p.is_dir():
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        p.unlink()

    save_json(LOCK, lock)

    total_changed = sum(len(v) for v in changed_by_camp.values())
    print(f'\n--- Итого: изменилось {total_changed} юнитов в {len(changed_by_camp)} лагерях ---')
    for camp, names in changed_by_camp.items():
        print(f'   {camp}: {", ".join(names)}')

    if a.commit or a.release:
        all_changed = [n for names in changed_by_camp.values() for n in names]
        git_commit(all_changed)
    if a.release:
        repo_slug = cfg.get('github', {}).get('repo', '')
        if not repo_slug:
            print('  release: не задан github.repo — пропуск')
        elif not changed_by_camp:
            print('  release: нечего публиковать')
        else:
            for camp, names in changed_by_camp.items():
                bundle = build_code_bundle(camp, names)
                tag = f'{cfg["github"].get("release_tag_prefix","")}{camp}-code-{stamp()}'
                notes = f'# Код-трек {camp} {now_iso()}\n\n' + \
                        '\n'.join(f'- {n}' for n in names)
                publish_release(repo_slug, tag, notes, [bundle])


if __name__ == '__main__':
    main()
