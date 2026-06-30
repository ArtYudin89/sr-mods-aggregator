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
import fnmatch
import hashlib
import re
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


def download_url(url, dest, token=None, timeout=300):
    """Скачать произвольный URL в dest (для HF public — token не нужен)."""
    import requests
    headers = {'Authorization': 'Bearer ' + token} if token else {}
    with requests.get(url, headers=headers, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(dest, 'wb') as f:
            for c in r.iter_content(1 << 20):
                f.write(c)
    return dest


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


def _inno_exes(path):
    """ВСЕ Inno Setup установщики в path (файл/папка). Папка может содержать
    несколько инсталляторов (напр. большой пак + патч) — извлекать надо ВСЕ.
    Возвращает список .exe, отсортированный по размеру УБЫВ. (база → патч поверх)."""
    iu = _find_innounp()
    if not iu:
        return []
    cands = []
    p = Path(path)
    if p.is_dir():
        cands = sorted(p.glob('*.exe')) + sorted(p.glob('*.[0-9]'))  # exe или setup.0
    elif p.suffix.lower() == '.exe' or _sniff_ext(p) == '.bin':
        cands = [p]
    inno = []
    for c in cands:
        try:
            r = subprocess.run([iu, '-v', str(c)], capture_output=True, text=True,
                               encoding='utf-8', errors='replace', timeout=LIST_TIMEOUT)
            if 'Inno Setup version detected' in (r.stdout or ''):
                inno.append(c)
        except Exception:
            continue
    inno.sort(key=lambda c: c.stat().st_size, reverse=True)
    return inno


def _inno_exe(path):
    """Первый Inno-установщик (back-compat). См. _inno_exes."""
    lst = _inno_exes(path)
    return lst[0] if lst else None


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


def extract(archive, dest, include=None):
    """include: список glob-масок по ИМЕНИ архива. Если задан и папка содержит
    несколько архивов (folder-of-zips), распаковываются ТОЛЬКО подходящие, остальные
    отбрасываются. Нужно для папок с вариантами одного пака под разные базы (напр.
    Solyanka_..._For_Redux vs _For_Original в одной GDrive-папке) — без фильтра оба
    архива слились бы в один юнит и моды одного варианта «протекали» бы в другой."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    # Inno Setup установщик(и) -> innounp. Папка может содержать несколько
    # (большой пак + патч): извлекаем ВСЕ в общий dest (база, затем патч поверх).
    innos = _inno_exes(archive)
    if innos:
        for inno in innos:
            print(f'    Inno Setup -> innounp: {inno.name} ({inno.stat().st_size // (1<<20)} МБ)')
            _innounp_extract(inno, dest)
        return dest
    if Path(archive).is_dir():
        shutil.copytree(archive, dest, dirs_exist_ok=True)
    else:
        _unpack_one(Path(archive), dest)
    # Папки часто содержат вложенные архивы (folder-of-zips) — распаковываем
    # их на месте, повторяя пока появляются новые. arc -> arc_unpacked/, arc удаляем.
    for round_i in range(6):
        nested = [p for p in dest.rglob('*')
                  if p.is_file() and p.suffix.lower() in ARCHIVE_EXT]
        if not nested:
            break
        # include применяем только на ПЕРВОМ проходе — к архивам-братьям из самой
        # папки. Глубже (внутри выбранного архива) фильтр не трогаем, чтобы случайно
        # не выкинуть нужные вложенные части по совпадению имени.
        if round_i == 0 and include:
            keep = [p for p in nested
                    if any(fnmatch.fnmatch(p.name.lower(), pat.lower()) for pat in include)]
            for p in nested:
                if p not in keep:
                    print(f'    [include] пропускаю архив {p.name} (не подходит под {include})')
                    p.unlink(missing_ok=True)
            nested = keep
            if not nested:
                print(f'    [warn] include={include}: ни один архив не подошёл')
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


def mod_key(relpath):
    """Ключ группировки ассета по МОДУ из пути.
    'Mods/<Категория>/<Имя>/DATA/...' -> 'Категория/Имя'; всё вне Mods/ -> '_base'.
    Глубина переменная: берём сегменты после последнего 'Mods' до DATA/CFG."""
    parts = relpath.replace('\\', '/').split('/')
    idxs = [i for i, p in enumerate(parts) if p.lower() == 'mods']
    if not idxs:
        return '_base'
    key = []
    for seg in parts[idxs[-1] + 1:]:
        if seg.lower() in ('data', 'cfg'):
            break
        key.append(seg)
    return '/'.join(key) if key else '_base'


def _sanitize_group(g):
    """Имя группы -> безопасный фрагмент имени файла чанка."""
    import re
    return re.sub(r'[^0-9A-Za-z._-]+', '_', g).strip('_') or 'misc'


def _drop_cache(name):
    """Удалить скачанное из cache/ (для --lean)."""
    for p in CACHE.glob(f'{name}.*'):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            p.unlink(missing_ok=True)


def build_asset_track(cfg, units, do_upload, repo_slug, fetch=False, lean=False,
                      remote='gdrive'):
    """ПОТОКОВАЯ заливка ассетов по юниту (пик диска ~ один юнит, не весь набор).

    Для каждого юнита: (опц. --fetch) скачать -> распаковать -> упаковать НОВЫЕ
    блобы (которых ещё нет в индексе) в чанки <chunk_max ПРЯМО из распаковки ->
    залить в asset_store (hf|github) -> инкрементально обновить индекс -> удалить
    распаковку (и cache при --lean). Дедуп — по индексу (блоб грузится один раз;
    общий блоб «принадлежит» первому залившему юниту). Без --upload — только отчёт."""
    chunk_max = cfg.get('asset_policy', {}).get('chunk_max_mb', 512) * 1024 * 1024
    index = load_json(ASSET_INDEX, {'blobs': {}, 'chunks': {}})
    seen = set(index['blobs'])
    store_cfg = cfg.get('asset_store', {'type': 'github'})
    stype = store_cfg.get('type', 'github')
    hf_repo = hf_token = None
    if do_upload and stype == 'hf':
        hf_repo = store_cfg.get('hf_repo')
        hf_token = os.environ.get('HF_TOKEN') or store_cfg.get('token')
        if not hf_repo or not hf_token:
            print('  upload[hf]: нет hf_repo или HF_TOKEN — выход')
            return 0

    ex_tmp = REPO / '_extract_assets'
    DIST.mkdir(parents=True, exist_ok=True)
    total_new = total_bytes = 0

    for unit in units:
        name, camp = unit['name'], unit['camp']
        man_path = MODS / camp / name / 'assets.manifest.json'
        if not man_path.exists():
            continue
        files = load_json(man_path, {}).get('files', {})
        need = {}                       # sha256 -> (relpath, size), первая встреча
        for rel, m in files.items():
            sh = m['sha256']
            if sh in seen or sh in need:
                continue
            need[sh] = (rel, m['size'])
        if not need:
            print(f'  {name}: новых ассетов нет')
            continue
        nbytes = sum(s for _, s in need.values())

        if not do_upload:               # dry-run: только отчёт, без скачивания
            print(f'  {name}: НОВЫХ {len(need)} блобов / {human(nbytes)} (dry-run)')
            total_new += len(need); total_bytes += nbytes
            continue

        arc = _cached_archive(name, unit.get('kind'))
        if not arc:
            if not fetch:
                print(f'  {name}: нет в cache/ (нужен --fetch) — пропуск')
                continue
            try:
                print(f'  {name}: скачивание ...')
                arc, _ = download(unit, False, remote)
            except Exception as e:
                print(f'  {name}: FAIL download: {e}')
                continue
        try:
            ext = extract(arc, ex_tmp)
        except Exception as e:
            print(f'  {name}: FAIL extract: {e}')
            if lean:
                _drop_cache(name)
            continue

        base = stamp()
        from collections import defaultdict
        by_mod = defaultdict(list)               # mod_key -> [sha,...]
        for sh, (rel, size) in need.items():
            if (ext / rel).exists():
                by_mod[mod_key(rel)].append(sh)
        uploaded = 0
        uchunks = REPO / '_unit_chunks'
        if uchunks.exists():
            shutil.rmtree(uchunks)
        uchunks.mkdir(parents=True)
        pending = []                              # (chunk_name, [sha,...], group)
        seq = 0

        def build(grp, cur):                      # собрать чанк ЛОКАЛЬНО (без заливки)
            nonlocal seq
            if not cur:
                return
            san = _sanitize_group(grp)
            cn = f'assets-{san}-{base}-{seq:03d}.zip'
            seq += 1
            with zipfile.ZipFile(uchunks / cn, 'w', zipfile.ZIP_STORED, allowZip64=True) as z:
                for sh in cur:
                    z.write(ext / need[sh][0], sh)
            pending.append((cn, list(cur), grp))

        try:
            for grp in sorted(by_mod):           # чанки группируются ПО МОДУ
                cur, cur_sz = [], 0
                for sh in sorted(by_mod[grp]):
                    size = need[sh][1]
                    if size > chunk_max:         # «гигант» — отдельный чанк
                        build(grp, [sh]); continue
                    if cur_sz + size > chunk_max and cur:
                        build(grp, cur); cur, cur_sz = [], 0
                    cur.append(sh); cur_sz += size
                build(grp, cur)
            # Заливка ВСЕЙ папки чанков юнита ОДНИМ коммитом (мало коммитов —
            # обходит rate-limit HF; subprocess+таймаут — не зависает; резюмируемо).
            uploaded = 0
            if pending:
                if stype == 'hf':
                    ok = _hf_put_folder(hf_repo, uchunks, hf_token)
                    if not ok:
                        print(f'  {name}: FAIL upload папки после ретраев — '
                              f'юнит переедет в следующий прогон')
                    else:
                        for cn, shas, grp in pending:
                            url = (f'https://huggingface.co/datasets/{hf_repo}/'
                                   f'resolve/main/{cn}')
                            index['chunks'][cn] = {'url': url, 'store': stype,
                                                   'group': grp, 'blob_count': len(shas)}
                            for sh in shas:
                                index['blobs'][sh] = {'chunk': cn, 'size': need[sh][1]}
                                seen.add(sh)
                            uploaded += len(shas)
                        save_json(ASSET_INDEX, index)
                else:
                    for cn, shas, grp in pending:
                        tag = f'assets-{name}-{base}'
                        publish_release(repo_slug, tag, f'assets {name}', [uchunks / cn])
                        url = (f'https://github.com/{repo_slug}/releases/'
                               f'download/{tag}/{cn}')
                        index['chunks'][cn] = {'url': url, 'store': stype, 'group': grp,
                                               'blob_count': len(shas)}
                        for sh in shas:
                            index['blobs'][sh] = {'chunk': cn, 'size': need[sh][1]}
                            seen.add(sh)
                        uploaded += len(shas)
                    save_json(ASSET_INDEX, index)
            print(f'  {name}: залито {uploaded} блобов / {human(nbytes)} '
                  f'({len(by_mod)} мод-групп, {len(pending)} чанков)')
            total_new += uploaded; total_bytes += nbytes
        except Exception as e:
            print(f'  {name}: FAIL upload: {e}')
        finally:
            shutil.rmtree(ext, ignore_errors=True)
            shutil.rmtree(uchunks, ignore_errors=True)
            if lean:
                _drop_cache(name)

    print(f'Ассет-трек: новых блобов {total_new} / {human(total_bytes)}; '
          f'в индексе {len(index["blobs"])} блобов, {len(index["chunks"])} чанков')
    return total_new


def _build_code_manifest(code_dir):
    """relpath('/') -> {'sha256','size'} для всех файлов в code/. ЕДИНЫЙ источник
    истины для code.manifest.json — используется и code_track, и build_descriptors,
    чтобы манифест не отставал от содержимого code/ (см. self-heal в build_descriptors)."""
    files = {}
    if not Path(code_dir).is_dir():
        return files
    for f in Path(code_dir).rglob('*'):
        if f.is_file():
            rel = str(f.relative_to(code_dir)).replace('\\', '/')
            files[rel] = {'sha256': sha256_file(f), 'size': f.stat().st_size}
    return files


def code_track(cfg):
    """Нарезать КОД по модам (из committed mods/<camp>/<unit>/code/) и залить на HF.
    Пишет code.manifest.json (path->sha,size) на юнит; код-блобы идут в общий
    asset_index (chunk kind='code'). Без GDrive — код уже в git."""
    from collections import defaultdict
    index = load_json(ASSET_INDEX, {'blobs': {}, 'chunks': {}})
    seen = set(index['blobs'])
    store_cfg = cfg.get('asset_store', {})
    if store_cfg.get('type') != 'hf':
        print('code-track: только asset_store type=hf'); return
    repo_id = store_cfg.get('hf_repo')
    token = os.environ.get('HF_TOKEN') or store_cfg.get('token')
    if not repo_id or not token:
        print('code-track: нет hf_repo/HF_TOKEN'); return
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    chunk_max = cfg.get('asset_policy', {}).get('chunk_max_mb', 512) * 1024 * 1024
    total = 0

    for unit_dir in sorted(MODS.glob('*/*')):
        code_dir = unit_dir / 'code'
        if not code_dir.is_dir():
            continue
        name = unit_dir.name
        # манифест кода (path -> sha,size) — единый билдер с build_descriptors
        files = _build_code_manifest(code_dir)
        if not files:
            continue
        save_json(unit_dir / 'code.manifest.json', {'files': files})

        need = {}                       # sha -> relpath (первая встреча новых)
        for rel, m in files.items():
            sh = m['sha256']
            if sh in seen or sh in need:
                continue
            need[sh] = rel
        if not need:
            print(f'  {name}: код без новых блобов')
            continue

        by_mod = defaultdict(list)
        for sh, rel in need.items():
            by_mod[mod_key(rel)].append(sh)
        uchunks = REPO / '_code_chunks'
        if uchunks.exists():
            shutil.rmtree(uchunks)
        uchunks.mkdir(parents=True)
        DIST.mkdir(parents=True, exist_ok=True)
        base = stamp()
        usan = _sanitize_group(name)
        pending = []
        seq = 0

        def build(grp, cur):
            nonlocal seq
            if not cur:
                return
            cn = f'code-{usan}-{_sanitize_group(grp)}-{base}-{seq:03d}.zip'
            seq += 1
            with zipfile.ZipFile(uchunks / cn, 'w', zipfile.ZIP_STORED, allowZip64=True) as z:
                for sh in cur:
                    z.write(code_dir / need[sh], sh)
            pending.append((cn, list(cur), grp))

        for grp in sorted(by_mod):
            cur, cur_sz = [], 0
            for sh in sorted(by_mod[grp]):
                sz = files[need[sh]]['size']
                if sz > chunk_max:
                    build(grp, [sh]); continue
                if cur_sz + sz > chunk_max and cur:
                    build(grp, cur); cur, cur_sz = [], 0
                cur.append(sh); cur_sz += sz
            build(grp, cur)

        if _hf_put_folder(repo_id, uchunks, token):
            for cn, shas, grp in pending:
                url = f'https://huggingface.co/datasets/{repo_id}/resolve/main/{cn}'
                index['chunks'][cn] = {'url': url, 'store': 'hf', 'group': grp,
                                       'kind': 'code', 'blob_count': len(shas)}
                for sh in shas:
                    index['blobs'][sh] = {'chunk': cn, 'size': files[need[sh]]['size']}
                    seen.add(sh)
            save_json(ASSET_INDEX, index)
            total += sum(len(s) for _, s, _ in pending)
            print(f'  {name}: код залит — {len(need)} блобов, {len(pending)} чанков '
                  f'({len(by_mod)} мод-групп)')
        else:
            print(f'  {name}: FAIL заливка кода после ретраев')
        shutil.rmtree(uchunks, ignore_errors=True)

    print(f'Код-трек: новых код-блобов {total}; в индексе {len(index["blobs"])} блобов, '
          f'{len(index["chunks"])} чанков')


def fill_missing(cfg, dry=False):
    """Долить на HF блобы, на которые ССЫЛАЮТСЯ committed-манифесты, но которых НЕТ
    в asset_index — восстановить инвариант «каждый sha манифеста есть в индексе».
    Манифесты могут уйти вперёд HF (--descriptors самовосстанавливает code.manifest
    из git, а заливка не переобрабатывает неизменившиеся юниты). КОД восстановим из
    git (mods/<юнит>/code/<rel>, sha должен совпасть) и доливается дёшево. Ассеты
    (нет байт в git) и устаревшие код-записи (файл на диске изменился) НЕ доливаются —
    только сообщаются (нужен --assets --fetch / пересборка манифеста). dry=True —
    только посчитать, без заливки/записи индекса."""
    from collections import defaultdict
    index = load_json(ASSET_INDEX, {'blobs': {}, 'chunks': {}})
    seen = set(index['blobs'])
    store_cfg = cfg.get('asset_store', {})
    if store_cfg.get('type') != 'hf':
        print('fill-missing: только asset_store type=hf'); return
    repo_id = store_cfg.get('hf_repo')
    token = os.environ.get('HF_TOKEN') or store_cfg.get('token')
    if not (dry or (repo_id and token)):
        print('fill-missing: нет hf_repo/HF_TOKEN'); return
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    chunk_max = cfg.get('asset_policy', {}).get('chunk_max_mb', 512) * 1024 * 1024

    need = {}                       # sha -> (relpath, abspath) — код к доливу из git
    asset_units, stale_units = set(), set()
    asset_gap = stale = 0
    for unit_dir in sorted(MODS.glob('*/*')):
        cm = load_json(unit_dir / 'code.manifest.json', {}).get('files', {})
        am = load_json(unit_dir / 'assets.manifest.json', {}).get('files', {})
        code_dir = unit_dir / 'code'
        for rel, m in cm.items():
            sh = m['sha256']
            if sh in seen or sh in need:
                continue
            fp = code_dir / rel
            if fp.is_file() and sha256_file(fp) == sh:
                need[sh] = (rel, fp)
            else:
                stale += 1; stale_units.add(unit_dir.name)
        for m in am.values():
            if m['sha256'] not in seen:
                asset_gap += 1; asset_units.add(unit_dir.name)
    print(f'fill-missing: код к доливу из git {len(need)}; устаревших код-записей '
          f'{stale} ({len(stale_units)} юн.); ассет-дыр {asset_gap} ({len(asset_units)} юн.)')
    if asset_units:
        print('  ассеты долить ре-фетчем (--assets --fetch --only <юнит>): '
              + ', '.join(sorted(asset_units)))
    if stale_units:
        print('  устаревшие код-записи (нужна пересборка манифеста --code-track): '
              + ', '.join(sorted(stale_units)))
    if not need:
        print('  из git доливать нечего.'); return
    if dry:
        print(f'  [dry] залилось бы {len(need)} код-блобов.'); return

    by_mod = defaultdict(list)
    for sh in need:
        by_mod[mod_key(need[sh][0])].append(sh)
    uchunks = REPO / '_fill_chunks'
    if uchunks.exists():
        shutil.rmtree(uchunks)
    uchunks.mkdir(parents=True)
    base = stamp()
    pending = []
    seq = 0

    def build(grp, cur):
        nonlocal seq
        if not cur:
            return
        cn = f'code-fill-{_sanitize_group(grp)}-{base}-{seq:03d}.zip'
        seq += 1
        with zipfile.ZipFile(uchunks / cn, 'w', zipfile.ZIP_STORED, allowZip64=True) as z:
            for sh in cur:
                z.write(need[sh][1], sh)
        pending.append((cn, list(cur), grp))

    for grp in sorted(by_mod):
        cur, cur_sz = [], 0
        for sh in sorted(by_mod[grp]):
            sz = need[sh][1].stat().st_size
            if sz > chunk_max:
                build(grp, [sh]); continue
            if cur_sz + sz > chunk_max and cur:
                build(grp, cur); cur, cur_sz = [], 0
            cur.append(sh); cur_sz += sz
        build(grp, cur)

    if _hf_put_folder(repo_id, uchunks, token):
        for cn, shas, grp in pending:
            url = f'https://huggingface.co/datasets/{repo_id}/resolve/main/{cn}'
            index['chunks'][cn] = {'url': url, 'store': 'hf', 'group': grp,
                                   'kind': 'code', 'blob_count': len(shas)}
            for sh in shas:
                index['blobs'][sh] = {'chunk': cn, 'size': need[sh][1].stat().st_size}
        save_json(ASSET_INDEX, index)
        print(f'  залито {len(need)} код-блобов в {len(pending)} чанках; '
              f'в индексе теперь {len(index["blobs"])} блобов')
    else:
        print('  FAIL заливка после ретраев')
    shutil.rmtree(uchunks, ignore_errors=True)


# ---- Фаза 1: дескрипторы модов (мод = пакет по URL) ----

# Корень игры (НЕ моды): эти имена при роутинге уходят в папку игры, не в Mods.
# Должно совпадать с install_route в лаунчере (launcher_core.py) — иначе агрегатор
# каталогизирует не те папки, что лаунчер кладёт на диск.
_ROOT_DIRS = {'cfg', 'data', 'matrix', 'soundtrack', 'help', 'man', 'build', 'dist'}
_ROOT_FILES = {
    'rangers.exe', 'cassandra.exe', 'manualrus.exe', 'matrixgame.dll',
    'build version.txt', 'cachedata.txt', 'cfg.txt', 'cfg.dat', 'lang.txt',
    'main.txt', 'changelog_rus.txt', 'generatemergedcfg.bat',
    'install.txt', 'install_russian.txt', 'readme_ru_ru.txt',
}
_ROOT_EXTS = {'.dll'}


def _after_mods(relpath):
    """Путь мода относительно Mods/ — или None, если файл не модовый (корень игры,
    мусор инсталлятора, Inno-плейсхолдер). Зеркалит install_route() лаунчера:
    срезает обёртки '<X>_unpacked/'; пропускает .exe(не игры)/.iss; берёт всё после
    последнего 'Mods'; срезает ведущий '{app}'; корневые папки/файлы игры и одиночные
    верхнеуровневые файлы -> None; прочая папка -> это мод (путь как есть)."""
    parts = [p for p in relpath.replace('\\', '/').split('/') if p]
    if any(p.startswith('.') for p in parts):    # staging агрегатора (.temp/.tmp) — не мод
        return None
    while parts and parts[0].lower().endswith('_unpacked'):
        parts = parts[1:]
    if not parts:
        return None
    base = parts[-1].lower()
    ext = os.path.splitext(base)[1]
    if ext == '.iss' or (ext == '.exe' and base not in _ROOT_FILES):
        return None
    low = [p.lower() for p in parts]
    if 'mods' in low:
        i = max(j for j, p in enumerate(low) if p == 'mods')
        rest = parts[i + 1:]
        return '/'.join(rest) if rest else None
    if parts and parts[0] == '{app}':
        parts = parts[1:]
        low = [p.lower() for p in parts]
        if not parts:
            return None
        if 'mods' in low:
            i = max(j for j, p in enumerate(low) if p == 'mods')
            rest = parts[i + 1:]
            return '/'.join(rest) if rest else None
    topl = parts[0].lower()
    if topl.startswith('{') and topl.endswith('}'):
        return None
    if topl in _ROOT_DIRS:
        return None
    if len(parts) == 1:          # одиночный файл сверху — не мод (readme/корневой файл)
        return None
    return '/'.join(parts)


def _read_text_auto(path):
    """Прочитать ModuleInfo.txt с автоопределением кодировки (UTF-16 BOM / cp1251)."""
    b = Path(path).read_bytes()
    if b[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return b.decode('utf-16', 'replace')
    try:
        return b.decode('utf-8')
    except UnicodeDecodeError:
        return b.decode('cp1251', 'replace')


def _parse_moduleinfo(text):
    """ModuleInfo.txt 'Ключ=Значение' -> dict (повторы ключа склеиваем переводом строки)."""
    out = {}
    for line in text.splitlines():
        if '=' not in line:
            continue
        k, _, v = line.partition('=')
        k, v = k.strip(), v.strip()
        if not k:
            continue
        out[k] = (out[k] + '\n' + v) if k in out else v
    return out


def _split_modlist(val):
    """Conflict/Dependence -> список id модов (разделители , ; пробел)."""
    if not val:
        return []
    return [x for x in re.split(r'[,;\s]+', val.strip()) if x]


def _strip_color(s):
    """Убрать игровую разметку <color=...>...</color> для отображаемого имени."""
    return re.sub(r'</?color[^>]*>', '', s or '').strip()


def _norm_name(s):
    """Каноничная форма имени мода для сравнения идентичности: без цветовой
    разметки, без скобочных пометок (напр. '(нано-версия)') и без пробелов/
    подчёркиваний, в нижнем регистре. 'ShuMM'->'shumm', 'PolMM'->'polmm',
    'Dr_Kles_Mod (нано-версия)'->'drklesmod'."""
    s = re.sub(r'\([^)]*\)', '', _strip_color(s))
    return re.sub(r'[\s_]+', '', s).lower()


def _mi_localized(mi, *keys):
    """Первое непустое значение из ModuleInfo по списку ключей (рус → eng-фолбэк),
    с убранной цветовой разметкой. Для описаний в дескрипторе/каталоге."""
    for k in keys:
        v = mi.get(k)
        if v:
            return _strip_color(v)
    return ''


def build_descriptors(cfg):
    """Сгенерировать дескриптор на каждый (источник, мод) — мод = папка с ModuleInfo.txt.
    Один и тот же мод в разных паках = РАЗНЫЕ варианты (версии часто отличаются), поэтому
    путь дескриптора квалифицирован источником: descriptors/<camp>/<unit>/<modid>.json.
    catalog.json группирует по логическому id со списком вариантов и дефолтным источником.
    Дескриптор самоописываем: id/source/version, мета из ModuleInfo, отфильтрованные
    code/assets манифесты, depends/conflicts, указатель на индекс чанков."""
    from collections import defaultdict
    store_cfg = cfg.get('asset_store', {})
    repo_id = store_cfg.get('hf_repo', '')
    chunk_index_url = (f'https://huggingface.co/datasets/{repo_id}/resolve/main/asset_index.json'
                       if repo_id else 'state/asset_index.json')
    out_root = REPO / 'descriptors'
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True)

    variants = defaultdict(list)   # mod_id -> [variant catalog-entry]
    n_desc = 0
    for unit_dir in sorted(MODS.glob('*/*')):
        camp_unit = f'{unit_dir.parent.name}/{unit_dir.name}'
        code_dir = unit_dir / 'code'
        # Источник истины — сам code/ на диске. code.manifest.json мог отстать, если
        # юнит переагрегировали (новое содержимое code/), но --code-track ещё не
        # прогоняли — тогда в манифесте файлы прошлой версии, и часть ModuleInfo.txt
        # (а значит и модов-дескрипторов) теряется. Пересобираем из code/ и сохраняем.
        if code_dir.is_dir():
            code_man = _build_code_manifest(code_dir)
            save_json(unit_dir / 'code.manifest.json', {'files': code_man})
        else:
            code_man = load_json(unit_dir / 'code.manifest.json', {}).get('files', {})
        am = load_json(unit_dir / 'assets.manifest.json', {})
        asset_man = am.get('files', am) if isinstance(am, dict) else {}
        if not code_man and not asset_man:
            continue

        roots = {}  # mod_id -> relpath ModuleInfo
        for rel in code_man:
            a = _after_mods(rel)
            if a and a.lower().endswith('/moduleinfo.txt'):
                roots[a[:-len('/ModuleInfo.txt')]] = rel
        if not roots:
            continue
        sorted_roots = sorted(roots, key=len, reverse=True)

        def assign(rel):
            a = _after_mods(rel)
            if a is None:
                return None
            for root in sorted_roots:
                if a == root or a.startswith(root + '/'):
                    return root
            return None

        buckets = {r: {'code': {}, 'assets': {}} for r in roots}
        for rel, meta in code_man.items():
            r = assign(rel)
            if r:
                buckets[r]['code'][rel] = meta
        for rel, meta in asset_man.items():
            r = assign(rel)
            if r:
                buckets[r]['assets'][rel] = meta

        for root, mi_rel in roots.items():
            files = buckets[root]
            mi = _parse_moduleinfo(_read_text_auto(code_dir / mi_rel))
            allpairs = sorted([(_after_mods(k), v['sha256'])
                               for k, v in {**files['code'], **files['assets']}.items()])
            version = hashlib.sha256(
                json.dumps(allpairs, ensure_ascii=False).encode('utf-8')).hexdigest()[:16]
            raw_title = mi.get('Name', root.split('/')[-1])
            desc = {
                'schema': 'srmod/1',
                'id': root,
                'source': camp_unit,
                'name': _strip_color(raw_title) or root.split('/')[-1],
                'title': raw_title,
                'author': mi.get('Author') or mi.get('Autor', ''),
                'section': mi.get('Section', ''),
                'priority': mi.get('Priority', ''),
                'description': _mi_localized(mi, 'SmallDescription', 'SmallDescriptionEng'),
                'full_description': _mi_localized(mi, 'FullDescription', 'FullDescriptionEng'),
                'version': version,
                'depends': _split_modlist(mi.get('Dependence', '')),
                'conflicts': _split_modlist(mi.get('Conflict', '')),
                'chunk_index_url': chunk_index_url,
                'files': files,
            }
            rel_path = f'descriptors/{camp_unit}/{root}.json'
            out_f = REPO / rel_path
            out_f.parent.mkdir(parents=True, exist_ok=True)
            save_json(out_f, desc)
            variants[root].append({
                'source': camp_unit, 'version': version, 'name': desc['name'],
                'author': desc['author'], 'depends': desc['depends'],
                'conflicts': desc['conflicts'], 'code_files': len(files['code']),
                'asset_files': len(files['assets']), 'path': rel_path,
                'unit_mod_count': len(roots),
                'description': desc['description'],
                'full_description': desc['full_description'],
                'section': desc['section'],
            })
            n_desc += 1

    # каталог: группировка по id; дефолт = вариант из самого «специализированного» юнита
    # (меньше всего модов в юните), tie-break — больше файлов.
    # ВАЖНО: id (путь папки) НЕ равен идентичности мода. Некоторые источники кладут
    # РАЗНЫЕ моды в одну папку (Polus Mira: PolMM в ShusRangers/ShuMM, PolMusic в
    # ShuMusic и т.д.). Истинный идентификатор в движке — Name= из ModuleInfo (через
    # него заданы depends/conflicts). Поэтому внутри одного пути доразбиваем варианты
    # по нормализованному имени: группа, чьё имя совпадает с именем папки (или дефолт,
    # если совпадения нет), держит ключ = путь; остальные получают ключ '<путь>@<Name>',
    # чтобы чужой мод не маскировался под имя папки.
    def _emit(mid, group):
        vs_sorted = sorted(group, key=lambda v: (v['unit_mod_count'],
                                                 -(v['code_files'] + v['asset_files'])))
        default = vs_sorted[0]
        # описание/раздел — из дефолта, но если у него пусто, берём первое непустое
        # среди вариантов (фиксы часто без ModuleInfo-описания, а установщик с ним)
        def _first(field):
            return next((v[field] for v in vs_sorted if v.get(field)), '')
        catalog[mid] = {
            'name': default['name'], 'author': default['author'],
            'default_source': default['source'],
            'description': default.get('description') or _first('description'),
            'full_description': default.get('full_description') or _first('full_description'),
            'section': default.get('section') or _first('section'),
            'versions_differ': len({v['version'] for v in group}) > 1,
            'variants': [{k: v[k] for k in ('source', 'version', 'name', 'depends',
                                            'conflicts', 'code_files', 'asset_files', 'path')}
                         for v in vs_sorted],
        }

    catalog = {}
    for root, vs in variants.items():
        by_norm = defaultdict(list)
        for v in vs:
            by_norm[_norm_name(v['name'])].append(v)
        if len(by_norm) == 1:                       # обычный случай — один мод, путь = id
            _emit(root, vs)
            continue
        base_norm = _norm_name(root.split('/')[-1])
        # какая группа удержит «голый» путь как ключ: совпадение с именем папки,
        # иначе — группа с общим дефолтным вариантом
        keep = next((n for n in by_norm if n == base_norm), None)
        if keep is None:
            overall_default = sorted(
                vs, key=lambda v: (v['unit_mod_count'],
                                   -(v['code_files'] + v['asset_files'])))[0]
            keep = _norm_name(overall_default['name'])
        for n, group in by_norm.items():
            mid = root if n == keep else f"{root}@{group[0]['name']}"
            _emit(mid, group)
    save_json(out_root / 'catalog.json', {'schema': 'srmod-catalog/2', 'mods': catalog})

    # packs.json: тир каждого юнита для проверки совместимости в лаунчере (Фаза 2).
    #   base   — полноценная игра (содержит Rangers.exe); сейвы привязаны к базе.
    #   fix    — фикс-пак, ставится ТОЛЬКО на родителя (fix_parent); обновление обязательно.
    #   assets — графика/музыка; mod — обычный мод.
    FIX_PARENT = {                       # нерегулярные имена -> родитель (можно переопр. в config)
        'redux_fixes': 'redux_base_installer',
        'original_fixes': 'original_installer',
        'reflection_fixes': 'reflection_installer',
        'universe_fixes_130325': 'universe_community',
        'denmods_fix': 'denmods',
    }
    packs = {}
    for u in cfg.get('units', []):
        name, camp = u['name'], u['camp']
        unit_dir = MODS / camp / name
        cm = load_json(unit_dir / 'code.manifest.json', {}).get('files', {})
        am = load_json(unit_dir / 'assets.manifest.json', {})
        am = am.get('files', am) if isinstance(am, dict) else {}
        contains_exe = any(k.lower().endswith('rangers.exe') for k in {**cm, **am})
        # размер юнита (байты на диске после установки) — для показа в лаунчере
        code_bytes = sum(int(v.get('size', 0)) for v in cm.values())
        asset_bytes = sum(int(v.get('size', 0)) for v in am.values())
        role = u.get('role')
        if role == 'pack' and contains_exe:
            tier = 'base'
        elif role == 'fixes':
            tier = 'fix'
        elif role == 'assets':
            tier = 'assets'
        else:
            tier = 'mod'
        packs[f'{camp}/{name}'] = {
            'name': name, 'camp': camp, 'role': role, 'tier': tier,
            'contains_exe': contains_exe,
            'fix_parent': u.get('fix_parent') or (FIX_PARENT.get(name) if tier == 'fix' else None),
            'load_order': u.get('load_order'),
            'update_required': tier in ('base', 'fix'),  # критично: обновление обязательно
            'display_name': u.get('display_name', name),
            'code_bytes': code_bytes,
            'asset_bytes': asset_bytes,
            'bytes': code_bytes + asset_bytes,
        }
    save_json(REPO / 'state' / 'packs.json', {'schema': 'srmod-packs/1', 'packs': packs})
    n_base = sum(1 for p in packs.values() if p['tier'] == 'base')
    n_fix = sum(1 for p in packs.values() if p['tier'] == 'fix')
    print(f'  packs.json: {len(packs)} юнитов (base {n_base}, fix {n_fix})')

    multi = sum(1 for v in catalog.values() if len(v['variants']) > 1)
    differ = sum(1 for v in catalog.values() if v['versions_differ'])
    with_dep = sum(1 for v in variants.values() for x in v if x['depends'])
    with_con = sum(1 for v in variants.values() for x in v if x['conflicts'])
    print(f'Дескрипторы: {n_desc} вариантов / {len(catalog)} уник. модов '
          f'(в неск. источниках {multi}, версии различаются {differ}); '
          f'записей с depends {with_dep}, с conflicts {with_con}; '
          f'каталог descriptors/catalog.json')


def regroup_assets(cfg):
    """Перегруппировать уже залитые на HF ассеты ПО МОДАМ (без GDrive).
    Скачивает блобы из текущих HF-чанков -> локальный store -> переупаковывает
    по mod_key (mod-unique -> 'Категория/Имя', cross-mod -> 'shared', вне Mods -> '_base')
    -> заливает новые чанки -> удаляет старые с HF. Индекс перезаписывается."""
    from collections import defaultdict
    index = load_json(ASSET_INDEX, {'blobs': {}, 'chunks': {}})
    store_cfg = cfg.get('asset_store', {})
    if store_cfg.get('type') != 'hf':
        print('regroup: поддержан только asset_store type=hf'); return
    repo_id = store_cfg.get('hf_repo')
    token = os.environ.get('HF_TOKEN') or store_cfg.get('token')
    if not repo_id or not token:
        print('regroup: нет hf_repo/HF_TOKEN'); return
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    chunk_max = cfg.get('asset_policy', {}).get('chunk_max_mb', 512) * 1024 * 1024
    from huggingface_hub import HfApi
    api = HfApi(token=token)

    # 1. sha -> множество mod_key (по всем манифестам)
    sha_keys = defaultdict(set)
    for man in MODS.rglob('assets.manifest.json'):
        for rel, m in load_json(man, {}).get('files', {}).items():
            sha_keys[m['sha256']].add(mod_key(rel))

    def group_of(sha):
        nb = {k for k in sha_keys.get(sha, ()) if k != '_base'}
        if not nb:
            return '_base'
        return next(iter(nb)) if len(nb) == 1 else 'shared'

    # 2. материализуем все блобы из текущих HF-чанков
    store = REPO / '_regroup_store'
    if store.exists():
        shutil.rmtree(store)
    store.mkdir(parents=True)
    old_chunks = list(index['chunks'].items())
    tmpz = REPO / '_regroup_tmp.zip'
    print(f'Скачиваю {len(old_chunks)} старых чанков с HF -> store ...')
    for ci, (cname, cmeta) in enumerate(old_chunks, 1):
        url = cmeta.get('url')
        if not url:
            continue
        try:
            download_url(url, tmpz)
            with zipfile.ZipFile(tmpz) as z:
                for sh in z.namelist():
                    tgt = store / sh
                    if not tgt.exists():
                        with z.open(sh) as s, open(tgt, 'wb') as o:
                            shutil.copyfileobj(s, o)
        except Exception as e:
            print(f'  [warn] чанк {cname}: {e}')
        finally:
            tmpz.unlink(missing_ok=True)
        if ci % 10 == 0:
            print(f'  ...{ci}/{len(old_chunks)} чанков')
    have = [p.name for p in store.iterdir() if p.is_file()]
    print(f'материализовано блобов: {len(have)}')

    # 3. группируем по модам, СОБИРАЕМ все чанки локально (без заливки)
    groups = defaultdict(list)
    for sh in have:
        groups[group_of(sh)].append(sh)
    print(f'групп: {len(groups)} (примеры: {sorted(groups)[:5]})')
    new_index = {'blobs': {}, 'chunks': {}}
    base = stamp()
    out = REPO / '_regroup_out'
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    counter = {'seq': 0}

    def build_chunk(grp, shas):
        san = _sanitize_group(grp)
        name = f'assets-{san}-{base}-{counter["seq"]:03d}.zip'
        counter['seq'] += 1
        with zipfile.ZipFile(out / name, 'w', zipfile.ZIP_STORED, allowZip64=True) as z:
            for sh in shas:
                z.write(store / sh, sh)
        new_index['chunks'][name] = {
            'url': f'https://huggingface.co/datasets/{repo_id}/resolve/main/{name}',
            'store': 'hf', 'group': grp, 'blob_count': len(shas)}
        for sh in shas:
            new_index['blobs'][sh] = {'chunk': name, 'size': (store / sh).stat().st_size}

    for grp in sorted(groups):
        cur, cur_sz = [], 0
        for sh in sorted(groups[grp]):
            sz = (store / sh).stat().st_size
            if sz > chunk_max:
                build_chunk(grp, [sh]); continue
            if cur_sz + sz > chunk_max and cur:
                build_chunk(grp, cur); cur, cur_sz = [], 0
            cur.append(sh); cur_sz += sz
        if cur:
            build_chunk(grp, cur)
    nchunks = len(new_index['chunks'])
    print(f'собрано {nchunks} чанков локально, заливаю одним upload_folder ...')

    # 4. батч-заливка всех чанков ОДНОЙ операцией (не коммит-на-чанк)
    api.upload_folder(folder_path=str(out), repo_id=repo_id, repo_type='dataset',
                      commit_message=f'regroup по модам: {nchunks} чанков, {len(groups)} групп')
    save_json(ASSET_INDEX, new_index)

    # ПРЕДОХРАНИТЕЛЬ: не удаляем старое, если новых блобов подозрительно мало
    if len(new_index['blobs']) < len(index['blobs']) * 0.9:
        print(f'SAFETY: новых блобов {len(new_index["blobs"])} << старых {len(index["blobs"])}'
              f' — НЕ удаляю старые чанки и НЕ перезаписываю индекс. Разберись вручную.')
        shutil.rmtree(store, ignore_errors=True)
        shutil.rmtree(out, ignore_errors=True)
        return

    # 5. удалить старые чанки с HF (имена новые -> старые не пересекаются)
    print('удаляю старые чанки с HF ...')
    new_names = set(new_index['chunks'])
    for cname, _ in old_chunks:
        if cname in new_names:
            continue
        try:
            api.delete_file(path_in_repo=cname, repo_id=repo_id, repo_type='dataset')
        except Exception as e:
            print(f'  del {cname}: {e}')
    shutil.rmtree(store, ignore_errors=True)
    shutil.rmtree(out, ignore_errors=True)
    print(f'REGROUP готово: блобов {len(new_index["blobs"])}, '
          f'чанков {nchunks}, групп {len(groups)}')


def _hf_put(repo_id, path, token, timeout=600, retries=4):
    """Залить ОДИН файл в HF dataset через subprocess с таймаутом+ретраями.
    upload из РФ иногда виснет навсегда (нет таймаута) — subprocess убивается по
    таймауту и попытка повторяется. Возвращает True при успехе."""
    path = Path(path)
    code = ('import sys,os;'
            'os.environ["HF_HUB_DISABLE_XET"]="1";'
            'from huggingface_hub import HfApi;'
            'HfApi(token=os.environ["HF_TOKEN"]).upload_file('
            'path_or_fileobj=sys.argv[2],path_in_repo=os.path.basename(sys.argv[2]),'
            'repo_id=sys.argv[1],repo_type="dataset")')
    env = dict(os.environ, HF_TOKEN=token, HF_HUB_DISABLE_XET='1')
    for attempt in range(1, retries + 1):
        try:
            r = subprocess.run([sys.executable, '-c', code, repo_id, str(path)],
                               env=env, capture_output=True, text=True,
                               encoding='utf-8', errors='replace', timeout=timeout)
            if r.returncode == 0:
                return True
            _lines = (r.stderr or r.stdout or '').strip().splitlines()
            err = (_lines[-1] if _lines else '')[:240]   # последняя строка = сам exception
        except subprocess.TimeoutExpired:
            err = f'timeout {timeout}s'
        print(f'    [upload retry {attempt}/{retries}] {path.name}: {err}')
    return False


def _hf_put_folder(repo_id, folder, token, timeout=420, retries=8):
    """Залить ВСЮ папку чанков ОДНИМ коммитом (upload_folder) в subprocess с
    таймаутом+ретраями. Мало коммитов (обходит rate-limit HF) + не зависает
    (subprocess убивается по таймауту). upload_folder резюмируемый — пропускает
    уже залитое, поэтому ретрай продолжает с места. Возвращает True при успехе."""
    folder = Path(folder)
    code = ('import sys,os;'
            'os.environ["HF_HUB_DISABLE_XET"]="1";'
            'from huggingface_hub import HfApi;'
            'HfApi(token=os.environ["HF_TOKEN"]).upload_folder('
            'folder_path=sys.argv[1],repo_id=sys.argv[2],repo_type="dataset",'
            'commit_message="assets batch")')
    env = dict(os.environ, HF_TOKEN=token, HF_HUB_DISABLE_XET='1')
    for attempt in range(1, retries + 1):
        try:
            r = subprocess.run([sys.executable, '-c', code, str(folder), repo_id],
                               env=env, capture_output=True, text=True,
                               encoding='utf-8', errors='replace', timeout=timeout)
            if r.returncode == 0:
                return True
            _lines = (r.stderr or r.stdout or '').strip().splitlines()
            err = (_lines[-1] if _lines else '')[:240]   # последняя строка = сам exception
        except subprocess.TimeoutExpired:
            err = f'timeout {timeout}s (резюмируемо, повтор)'
        print(f'    [folder upload retry {attempt}/{retries}]: {err}')
    return False


def _hf_upload(repo_id, paths, token, public):
    """Залить чанки в HF dataset-репозиторий. Возвращает {имя_чанка: resolve-URL}."""
    # Xet-бэкенд (cas-bridge.xethub.hf.co) недоступен из РФ (403) и вешает аплоад —
    # форсим классический LFS-путь.
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    from huggingface_hub import HfApi
    api = HfApi(token=token)
    api.create_repo(repo_id, repo_type='dataset', private=not public, exist_ok=True)
    urls = {}
    for p in paths:
        print(f'  hf upload: {p.name} ({human(p.stat().st_size)}) ...')
        api.upload_file(path_or_fileobj=str(p), path_in_repo=p.name,
                        repo_id=repo_id, repo_type='dataset',
                        commit_message=f'add {p.name}')
        urls[p.name] = (f'https://huggingface.co/datasets/{repo_id}/'
                        f'resolve/main/{p.name}')
    return urls


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
    ap.add_argument('--camp', default=None, help='только лагерь (original/redux/universe/shared)')
    ap.add_argument('--force', action='store_true', help='игнорировать lock')
    ap.add_argument('--assets', action='store_true',
                    help='режим ассет-трека: упаковать новые блобы в чанки <2ГБ и залить')
    ap.add_argument('--no-upload', action='store_true',
                    help='с --assets: только собрать чанки локально, без Release')
    ap.add_argument('--lean', action='store_true',
                    help='удалять скачанный архив из cache/ после обработки юнита '
                         '(экономит диск; --assets потом потребует пере-скачивания)')
    ap.add_argument('--code-release', action='store_true',
                    help='перегенерировать код-трек релизы по ВСЕМ юнитам в mods/ '
                         '(не только изменившимся) и опубликовать')
    ap.add_argument('--fetch', action='store_true',
                    help='с --assets: докачивать юнит, если его нет в cache/')
    ap.add_argument('--regroup', action='store_true',
                    help='перегруппировать уже залитые на HF ассеты ПО МОДАМ '
                         '(скачать с HF -> переупаковать -> залить -> удалить старые)')
    ap.add_argument('--code-track', action='store_true',
                    help='нарезать КОД по модам (из mods/<юнит>/code/) и залить на HF '
                         '+ code.manifest.json (без GDrive)')
    ap.add_argument('--descriptors', action='store_true',
                    help='сгенерировать дескрипторы модов (descriptors/<id>.json + catalog.json) '
                         'из ModuleInfo.txt + манифестов (Фаза 1)')
    ap.add_argument('--publish-index', action='store_true',
                    help='залить state/asset_index.json на HF (chunk_index_url для дескрипторов)')
    ap.add_argument('--fill-missing', action='store_true',
                    help='долить на HF код-блобы, на которые ссылаются манифесты, но '
                         'которых нет в asset_index (из git); ассет-дыры сообщить. '
                         'С --no-upload — только посчитать (dry-run)')
    ap.add_argument('--cloud', action='store_true',
                    help='облачный режим: manual-юниты (тяжёлые, manual:true) НЕ обрабатывать, '
                         'только детектить изменения -> state/manual_pending.json (для уведомления)')
    a = ap.parse_args()

    cfg = load_json(a.config, None)
    if cfg is None:
        print(f'ERROR: конфиг не найден: {a.config}', file=sys.stderr)
        sys.exit(1)

    # Автономные подкоманды (НЕ требуют декомпилятора/GDrive/юнитов) — диспатчим первыми,
    # чтобы они работали и в облаке (workflow без репо декомпилятора).
    if a.regroup:
        print('=== Перегруппировка ассетов по модам (из HF) ===')
        regroup_assets(cfg)
        return

    if a.code_track:
        print('=== Код-трек по модам (на HF) ===')
        code_track(cfg)
        return

    if a.fill_missing:
        print('=== Долив недостающих блобов (verify-and-fill) ===')
        fill_missing(cfg, dry=a.no_upload)
        return

    if a.descriptors:
        print('=== Генерация дескрипторов модов (Фаза 1) ===')
        build_descriptors(cfg)
        return

    if a.publish_index:
        store_cfg = cfg.get('asset_store', {})
        repo_id = store_cfg.get('hf_repo')
        token = os.environ.get('HF_TOKEN') or store_cfg.get('token')
        if not repo_id or not token:
            print('publish-index: нет hf_repo/HF_TOKEN'); return
        ok = _hf_put(repo_id, str(ASSET_INDEX), token)
        print(f'asset_index.json -> HF ({repo_id}): {"OK" if ok else "FAIL"}')
        return

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

    if a.code_release:
        repo_slug = cfg.get('github', {}).get('repo', '')
        camps = {}
        for ud in sorted(MODS.glob('*/*')):
            if (ud / 'meta.json').exists():
                camps.setdefault(ud.parent.name, []).append(ud.name)
        print(f'=== Код-трек релизы по всем юнитам: {sum(len(v) for v in camps.values())} в {len(camps)} лагерях ===')
        for camp, names in camps.items():
            bundle = build_code_bundle(camp, names)
            tag = f'{cfg["github"].get("release_tag_prefix","")}{camp}-code-{stamp()}'
            notes = f'# Код-трек {camp} (все {len(names)} юнитов) {now_iso()}\n\n' + \
                    '\n'.join(f'- {n}' for n in names)
            print(f'  {camp}: {len(names)} юнитов -> {bundle.name} ({human(bundle.stat().st_size)})')
            publish_release(repo_slug, tag, notes, [bundle])
        return

    if a.assets:
        print(f'=== Ассет-трек: {len(units)} юнитов ===')
        build_asset_track(cfg, units, do_upload=not a.no_upload,
                          repo_slug=cfg.get('github', {}).get('repo', ''),
                          fetch=a.fetch, lean=a.lean, remote=remote)
        return

    manual_pending = []
    for unit in units:
        name, camp = unit['name'], unit['camp']
        print(f'\n=== [{camp}] {name} — {unit.get("display_name", name)} ===')

        prev = lock_before.get(name, {})

        # Предзагрузочная проверка: спрашиваем у GDrive контрольную сумму/отпечаток
        # БЕЗ скачивания. Если совпал с локом — не качаем вообще.
        sig = None if a.no_download else remote_signature(unit, rclone_exe, remote)

        # Облако: тяжёлые manual-юниты НЕ обрабатываем — только детектим изменение
        # (lock не трогаем, останется pending до локального прогона).
        if a.cloud and unit.get('manual'):
            if a.force or (sig and prev.get('remote_sig') != sig):
                manual_pending.append({'name': name, 'camp': camp,
                                       'display_name': unit.get('display_name', name)})
                print(f'  [MANUAL-CHANGED] {name}: изменился на GDrive — нужен локальный прогон')
            else:
                print('  manual-юнит без изменений (облако пропускает)')
            continue

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
            extracted = extract(archive, EXTRACT / name, unit.get('include'))

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

    # Облако: сводка прогона для Telegram-уведомлений (changed = обработанные авто-юниты,
    # manual = тяжёлые, требующие локального прогона).
    if a.cloud:
        changed_names = [n for names in changed_by_camp.values() for n in names]
        save_json(REPO / 'state' / 'manual_pending.json',
                  {'pending': manual_pending, 'checked_at': now_iso()})
        save_json(REPO / 'state' / 'cloud_summary.json',
                  {'changed': changed_names,
                   'manual': [m['name'] for m in manual_pending],
                   'checked_at': now_iso()})
        if manual_pending:
            names = ', '.join(m['name'] for m in manual_pending)
            print(f'\n[MANUAL-PENDING] требуют локального прогона: {names}')

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
