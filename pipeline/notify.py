#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Telegram-уведомления автообновления. Текст здесь (UTF-8), чтобы кодировка раннера
не калечила кириллицу.

Режимы (argv[1]):
  manual  — алерт: тяжёлый manual-юнит (redux_base) изменился, нужен локальный прогон.
  summary — итог прогона: какие паки обновились, какие юниты и шаги упали, что нашла
            проверка содержимого модов. Нечего сказать — не шлём.

Env: TG_BOT_TOKEN, TG_CHAT_ID, NOTIFY_TEST; для summary ещё JOB_STATUS (job.status) и
STEP_OUTCOMES («id=outcome;…» шагов с continue-on-error — их провал иначе не виден).
Источники: state/cloud_summary.json, state/failures.log.
Код выхода 0 — отправлено/нечего слать; 1 — ошибка доставки."""
import os, json, sys, urllib.request, urllib.parse, urllib.error

TG_LIMIT = 4000          # у Telegram предел 4096 символов на сообщение
STEP_NAMES = {'assets': 'ассеты на HF', 'code': 'код на HF', 'descriptors': 'дескрипторы и индекс'}


def read_failures(path):
    """Сбои юнитов из state/failures.log (JSON на строку), без повторов, по порядку."""
    out, seen = [], set()
    try:
        with open(path, encoding='utf-8') as fh:
            lines = fh.read().splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            f = json.loads(line)
        except ValueError:
            continue
        key = (f.get('name'), f.get('stage'))
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def failed_steps(outcomes):
    """'assets=failure;code=success' -> ['ассеты на HF']."""
    names = []
    for part in (outcomes or '').split(';'):
        name, _, outcome = part.rpartition('=')
        if name.strip() and outcome.strip() == 'failure':
            names.append(STEP_NAMES.get(name.strip(), name.strip()))
    return names


def summary_text(summary, failures, steps, job_status):
    """Текст итога прогона или None, если сообщать нечего."""
    changed = summary.get('changed', [])
    content = summary.get('content', {})
    job_failed = job_status not in ('', None, 'success')
    if not (changed or failures or steps or content or job_failed):
        return None
    bad = failures or steps or job_failed
    parts = ['❌ SR Mods: автообновление с ошибками' if bad
             else '⚠️ SR Mods: в обновлённых модах ошибки' if content
             else f'✅ SR Mods: автообновление отработало — обновлено паков: {len(changed)}']
    if job_failed:
        parts.append(f'Прогон: {job_status} — см. журнал GitHub Actions '
                     '(в т.ч. не прошёл ли push в master).')
    if steps:
        parts.append('Шаги с ошибкой: ' + ', '.join(steps))
    if failures:
        parts.append('Юниты со сбоем:\n' + '\n'.join(
            f'• {f.get("name")} ({f.get("stage")}): {f.get("error")}' for f in failures))
    if content:
        lines = [f'• {unit}: {f["file"]} — {f["rule"]}: {f["message"]}'
                 for unit, found in content.items() for f in found]
        parts.append('Проверка содержимого (файлы авторов, мы их не правим):\n' + '\n'.join(lines))
    if changed and (bad or content):
        parts.append(f'Обновлено паков: {len(changed)} — ' + ', '.join(changed))
    elif changed:
        parts.append(', '.join(changed) + '\n\nИсходники и ассеты на HF обновлены автоматически.')
    text = '\n\n'.join(parts)
    return text if len(text) <= TG_LIMIT else text[:TG_LIMIT - 1] + '…'


def main():
    # stdout раннера = cp1252 -> кириллица в print() роняет процесс (UnicodeEncodeError).
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding='utf-8')
        except Exception:
            pass

    kind = sys.argv[1] if len(sys.argv) > 1 else 'summary'
    tok = os.environ.get('TG_BOT_TOKEN', '').strip()
    chat = os.environ.get('TG_CHAT_ID', '').strip()
    test = os.environ.get('NOTIFY_TEST') == 'true'
    if not tok or not chat:
        print('TG_BOT_TOKEN/TG_CHAT_ID не заданы — уведомление пропущено')
        return 0

    try:
        s = json.load(open('state/cloud_summary.json', encoding='utf-8'))
    except Exception:
        s = {'changed': [], 'manual': []}

    if kind == 'manual':
        units = ['redux_base_installer'] if test else s.get('manual', [])
        if not units:
            print('Тяжёлых юнитов к обновлению нет — не шлём.')
            return 0
        msg = ('🛰 SR Mods: тяжёлый юнит обновился на GDrive и требует ЛОКАЛЬНОГО прогона:\n'
               + ', '.join(units)
               + '\n\nЗапусти update_base.bat в репозитории и дождись завершения.')
    else:  # summary
        if test:
            s = {'changed': ['redux_fixes', 'universe_fixes_130325']}
        msg = summary_text(s, [] if test else read_failures('state/failures.log'),
                           failed_steps(os.environ.get('STEP_OUTCOMES')),
                           os.environ.get('JOB_STATUS', ''))
        if not msg:
            print('Изменений и ошибок нет — итог не шлём.')
            return 0
        units = s.get('changed', [])

    data = urllib.parse.urlencode({'chat_id': chat, 'text': msg}).encode('utf-8')
    url = f'https://api.telegram.org/bot{tok}/sendMessage'
    try:
        with urllib.request.urlopen(url, data=data, timeout=30) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        resp = json.load(e)
    except Exception as e:
        print('Telegram: сетевая ошибка:', e)
        return 1

    if resp.get('ok'):
        print(f'Telegram доставлено [{kind}]:', ', '.join(units) or msg.splitlines()[0])
        return 0
    print(f'Telegram НЕ доставлено [{kind}]:', json.dumps(resp, ensure_ascii=False))
    return 1


if __name__ == '__main__':
    sys.exit(main())
