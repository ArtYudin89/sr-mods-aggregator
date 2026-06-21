#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Отправка Telegram-уведомления о тяжёлых manual-юнитах, требующих локального прогона.
Текст хранится здесь (UTF-8), чтобы кодировка раннера не калечила кириллицу.
Читает env: TG_BOT_TOKEN, TG_CHAT_ID, NOTIFY_TEST; файл state/manual_pending.json.
Код выхода 0 — отправлено/нечего слать; 1 — ошибка доставки."""
import os, json, sys, urllib.request, urllib.parse

tok = os.environ.get('TG_BOT_TOKEN', '')
chat = os.environ.get('TG_CHAT_ID', '').strip()
if not tok or not chat:
    print('TG_BOT_TOKEN/TG_CHAT_ID не заданы — уведомление пропущено')
    sys.exit(0)

if os.environ.get('NOTIFY_TEST') == 'true':
    pending = ['ТЕСТ (redux_base_installer)']
else:
    try:
        d = json.load(open('state/manual_pending.json', encoding='utf-8'))
        pending = [m['name'] for m in d.get('pending', [])]
    except Exception:
        pending = []

if not pending:
    print('Тяжёлых юнитов к обновлению нет — не шлём.')
    sys.exit(0)

msg = ('🛰 SR Mods: тяжёлый юнит обновился на GDrive и требует ЛОКАЛЬНОГО прогона:\n'
       + ', '.join(pending)
       + '\n\nЗапусти update_base.bat в репозитории и дождись завершения.')

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
    print('Telegram доставлено:', ', '.join(pending))
    sys.exit(0)
print('Telegram НЕ доставлено:', json.dumps(resp, ensure_ascii=False))
sys.exit(1)
