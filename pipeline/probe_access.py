#!/usr/bin/env python3
"""Разведка доступности GDrive-ссылок без скачивания тел файлов.

Для каждого юнита определяет: PUBLIC (качается анонимно) / RESTRICTED
(нужен доступ) / EMPTY/ERROR. Тела не качаются — читается только метадата
и первые байты ответа. Результат — карта в stdout + access_map.json.
"""
import json
import sys
from pathlib import Path

import gdown
import requests

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = Path(__file__).resolve().parent.parent
RESTRICT = 'Only the owner and editors can download'


def probe_file(fid, sess):
    """Вернуть 'public' / 'restricted' / 'error', не качая тело."""
    try:
        r = sess.get('https://drive.google.com/uc',
                     params={'id': fid, 'export': 'download'},
                     stream=True, timeout=30)
        cd = r.headers.get('content-disposition', '')
        head = next(r.iter_content(8192), b'') or b''
        r.close()
        text = head.decode('utf-8', 'replace')
        if cd or r.headers.get('content-type', '').startswith('application/'):
            return 'public'          # сразу отдаёт файл
        if RESTRICT in text:
            return 'restricted'
        if 'confirm=' in text or 'download_warning' in text or 'uc-download-link' in text:
            return 'public'          # confirm-страница большого файла
        if RESTRICT in text:
            return 'restricted'
        return 'public' if cd else 'unknown'
    except Exception as e:
        return f'error:{str(e)[:60]}'


def main():
    cfg = json.loads((REPO / 'mods.config.json').read_text(encoding='utf-8'))
    sess = requests.Session()
    sess.headers['User-Agent'] = 'Mozilla/5.0'
    rows = []
    for u in cfg['units']:
        name, kind = u['name'], u.get('kind')
        url = u['gdrive']
        status, detail = '?', ''
        try:
            if kind == 'folder':
                files = gdown.download_folder(url=url, skip_download=True,
                                              quiet=True, use_cookies=False,
                                              remaining_ok=True)
                if not files:
                    status = 'empty'
                else:
                    # классифицируем по первому файлу (доступ обычно на уровне папки)
                    status = probe_file(files[0].id, sess)
                    detail = f'{len(files)} файлов'
            else:
                import re
                m = re.search(r'/d/([\w-]+)', url) or re.search(r'[?&]id=([\w-]+)', url)
                status = probe_file(m.group(1), sess) if m else 'no-id'
        except Exception as e:
            status = f'error:{str(e)[:60]}'
        rows.append({'name': name, 'camp': u['camp'], 'kind': kind,
                     'status': status, 'detail': detail})
        print(f'  {status:<12} [{u["camp"]:<8}] {name:<24} {kind:<7} {detail}')

    (REPO / 'state' / 'access_map.json').write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    pub = sum(1 for r in rows if r['status'] == 'public')
    res = sum(1 for r in rows if r['status'] == 'restricted')
    print(f'\nИтого: public={pub}  restricted={res}  прочее={len(rows)-pub-res}  из {len(rows)}')


if __name__ == '__main__':
    main()
