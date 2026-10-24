# -*- coding: utf-8 -*-
"""Условия сторонних компонентов, которые едут в паках (third_party/notices.json).

Загрузчик XenoNative из Xenomorphchyma/XenoMods раздаётся в паке shared/solar под
PolyForm Noncommercial 1.0.0. Раздел Notices требует, чтобы каждый получатель получил
текст условий (или их URL) и строки «Required Notice:» (находка аудита F1024-crit-2-1).
Тесты читают только файлы репозитория: без сети и без импорта aggregate.

Запускать: python -m unittest discover -s tests -t .
"""
import glob
import hashlib
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTICES = os.path.join(ROOT, 'third_party', 'notices.json')
MANIFESTS = ('code.manifest.json', 'assets.manifest.json')


def _components():
    with open(NOTICES, encoding='utf-8') as f:
        return json.load(f)


def _read_bytes(rel):
    with open(os.path.join(ROOT, *rel.split('/')), 'rb') as f:
        return f.read()


def _norm(text):
    return ' '.join(text.split())


def _notice_paragraphs(text):
    """Абзацы текста условий, которые начинаются с «Required Notice:»."""
    text = text.replace('\r\n', '\n')
    return [p.strip('\n') for p in re.split(r'\n[ \t]*\n', text)
            if p.startswith('Required Notice:')]


def _manifest_paths(unit_dir):
    paths = set()
    for name in MANIFESTS:
        path = os.path.join(unit_dir, name)
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as f:
                paths.update(json.load(f).get('files', {}))
    return paths


class RegistryTests(unittest.TestCase):
    def test_license_file_is_verbatim_copy(self):
        for c in _components():
            data = _read_bytes(c['license_file'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), c['license_sha256'], c['id'])

    def test_required_notices_are_verbatim_from_license(self):
        for c in _components():
            text = _read_bytes(c['license_file']).decode('utf-8')
            self.assertEqual(_notice_paragraphs(text), c['required_notices'], c['id'])
            self.assertIn(c['license_url'], text, c['id'])


class DistributionTests(unittest.TestCase):
    def test_readme_has_required_notices(self):
        with open(os.path.join(ROOT, 'README.md'), encoding='utf-8') as f:
            readme = f.read()
        flat = _norm(readme)
        missing = []
        for c in _components():
            missing += ['%s: %s...' % (c['id'], _norm(n)[:60]) for n in c['required_notices']
                        if _norm(n) not in flat]
            missing += ['%s: link to %s' % (c['id'], url)
                        for url in (c['license_url'], c['license_file'])
                        if '](%s)' % url not in readme]
        self.assertEqual(missing, [])

    # Пак shared/solar пока раздаётся без файла условий: хука, который кладёт его в паки
    # с загрузчиком, и разового файла в mods/shared/solar/code/ ещё нет (вариант 1 аудита
    # F1024-crit-2-1 ждёт решения). Когда они появятся и ночной --code-track пересоберёт
    # code.manifest.json, тест пройдёт, unittest засчитает неожиданный успех и прогон
    # упадёт — тогда снять декоратор.
    @unittest.expectedFailure
    def test_repo_units_carry_notices(self):
        missing = []
        for unit_dir in sorted(glob.glob(os.path.join(ROOT, 'mods', '*', '*'))):
            paths = _manifest_paths(unit_dir)
            lowered = {p.lower() for p in paths}
            unit = os.path.relpath(unit_dir, ROOT).replace(os.sep, '/')
            for c in _components():
                markers = {m.lower() for m in c['markers']}
                folders = {p.rpartition('/')[0] for p in paths
                           if p.rpartition('/')[2].lower() in markers}
                for folder in sorted(folders):
                    want = (folder + '/' if folder else '') + c['install_as']
                    lic_dir = want.rpartition('/')[0].lower() + '/'
                    if not any(p.startswith(lic_dir) and '/' not in p[len(lic_dir):]
                               and p[len(lic_dir):].startswith('licen') for p in lowered):
                        missing.append('%s: %s' % (unit, want))
        self.assertEqual(missing, [])


if __name__ == '__main__':
    unittest.main()
