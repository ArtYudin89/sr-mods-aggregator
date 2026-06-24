#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Telegram-уведомления автообновления. Текст здесь (UTF-8), чтобы кодировка раннера
не калечила кириллицу.

Режимы (argv[1]):
  manual  — алерт: тяжёлый manual-юнит (redux_base) изменился, нужен локальный прогон.
  summary — итог обычного автообновления: какие паки обновились (если обновились).

Env: TG_BOT_TOKEN, TG_CHAT_ID, NOTIFY_TEST. Источник: state/cloud_summary.json.
Код выхода 0 — отправлено/нечего слать; 1 — ошибка доставки."""
import os, json, sys, urllib.request, urllib.parse, urllib.error

# stdout раннера = cp1252 -> кириллица в print() роняет процесс (UnicodeEncodeError).
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8')
    except Exception:
        pass

KIND = sys.argv[1] if len(sys.argv) > 1 else 'summary'
tok = os.environ.get('TG_BOT_TOKEN', '').strip()
chat = os.environ.get('TG_CHAT_ID', '').strip()
test = os.environ.get('NOTIFY_TEST') == 'true'
if not tok or not chat:
    print('TG_BOT_TOKEN/TG_CHAT_ID не заданы — уведомление пропущено')
    sys.exit(0)

try:
    s = json.load(open('state/cloud_summary.json', encoding='utf-8'))
except Exception:
    s = {'changed': [], 'manual': []}

if KIND == 'manual':
    units = ['redux_base_installer'] if test else s.get('manual', [])
    if not units:
        print('Тяжёлых юнитов к обновлению нет — не шлём.')
        sys.exit(0)
    msg = ('🛰 SR Mods: тяжёлый юнит обновился на GDrive и требует ЛОКАЛЬНОГО прогона:\n'
           + ', '.join(units)
           + '\n\nЗапусти update_base.bat в репозитории и дождись завершения.')
else:  # summary
    units = ['redux_fixes', 'universe_fixes_130325'] if test else s.get('changed', [])
    if not units:
        print('Обычных изменений нет — итог не шлём.')
        sys.exit(0)
    msg = (f'✅ SR Mods: автообновление отработало — обновлено паков: {len(units)}\n'
           + ', '.join(units)
           + '\n\nИсходники и ассеты на HF обновлены автоматически.')

data = urllib.parse.urlencode({'chat_id': chat, 'text': msg}).encode('utf-8')
url = f'https://api.telegram.org/bot{tok}/sendMessage'
try:
    with urllib.request.urlopen(url, data=data, timeout=30) as r:
        resp = json.load(r)
except urllib.error.HTTPError as e:
    resp = json.load(e)
except Exception as e:
    print('Telegram: сетевая ошибка:', e)
    sys.exit(1)

if resp.get('ok'):
    print(f'Telegram доставлено [{KIND}]:', ', '.join(units))
    sys.exit(0)
print(f'Telegram НЕ доставлено [{KIND}]:', json.dumps(resp, ensure_ascii=False))
sys.exit(1)
