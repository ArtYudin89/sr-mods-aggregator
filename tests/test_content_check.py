# -*- coding: utf-8 -*-
"""Проверка содержимого юнита (датники CFG) и уведомление о сбоях (SR-6).

Датники собираются настоящим srblockpar из декомпилятора (../rson_decompiler/vendor) —
тем же, которым их читает проверка; нет декомпилятора рядом — тесты проверки пропускаются.

Запускать: python -m unittest discover -s tests -t .
"""
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import aggregate  # noqa: E402
import notify  # noqa: E402

with redirect_stdout(StringIO()):
    DATFILE = aggregate.dat_reader(aggregate.REPO.parent / 'rson_decompiler' / 'run.py')


class _TmpDir(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.tmp = Path(d.name)

    def put(self, rel, data):
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)


@unittest.skipIf(DATFILE is None, 'нет ../rson_decompiler/vendor/srblockpar')
class CheckContentTests(_TmpDir):
    def pack(self, kind):
        return DATFILE.pack(b'payload of a game dat file', kind=kind)

    def test_rules(self):
        self.put('Mods/Exp/ExpPilotBridge/CFG/CacheData.dat', self.pack(DATFILE.KIND_BLOCK))
        self.put('Mods/Exp/Good/CFG/CacheData.dat', self.pack(DATFILE.KIND_DATA))
        self.put('Mods/Exp/Good/CFG/Main.dat', self.pack(DATFILE.KIND_BLOCK))
        self.put('Mods/Zea/ZeaQuestEnch/CFG/CacheData.dat', b'not a dat at all, just text')
        self.put('Mods/Zea/Other/CFG/Lang.dat', b'other .dat files are not checked')
        # движок не грузит CacheData.dat из подпапок CFG (ZeaLostPromoQuest/CFG/Rus/)
        self.put('Mods/Zea/ZeaLostPromoQuest/CFG/Rus/CacheData.dat', b'not loaded by the engine')
        found = aggregate.check_content(self.tmp, DATFILE)
        self.assertEqual([(f['file'], f['rule']) for f in found], [
            ('Mods/Exp/ExpPilotBridge/CFG/CacheData.dat', 'cache-wrong-kind'),
            ('Mods/Zea/ZeaQuestEnch/CFG/CacheData.dat', 'dat-unreadable'),
        ])

    def test_name_case_does_not_matter(self):
        self.put('Mods/A/B/CFG/cachedata.DAT', self.pack(DATFILE.KIND_BLOCK))
        self.assertEqual([f['rule'] for f in aggregate.check_content(self.tmp, DATFILE)],
                         ['cache-wrong-kind'])

    def test_report_keeps_other_units(self):
        report = self.tmp / 'state' / 'content_check.json'
        with patch.object(aggregate, 'CONTENT_REPORT', report):
            aggregate.save_content_report({'a': {'sha256': '1', 'findings': []}})
            aggregate.save_content_report({'b': {'sha256': '2', 'findings': [{'rule': 'x'}]}})
        data = json.loads(report.read_text(encoding='utf-8'))
        self.assertEqual(sorted(data), ['a', 'b'])
        self.assertEqual(data['b']['findings'], [{'rule': 'x'}])
        self.assertIn('checked_at', data['a'])


class FailureLogTests(_TmpDir):
    def test_record_and_read_back(self):
        log = self.tmp / 'state' / 'failures.log'
        with patch.object(aggregate, 'FAILURES', log), redirect_stdout(StringIO()) as out:
            aggregate.record_failure('universe_community', 'обработка', RuntimeError('неизвестный формат'))
            aggregate.record_failure('universe_community', 'обработка', RuntimeError('повтор'))
            aggregate.record_failure('solar', 'ассеты: заливка на HF', 'после ретраев')
        self.assertIn('universe_community: FAIL обработка: неизвестный формат', out.getvalue())
        got = notify.read_failures(log)
        self.assertEqual([(f['name'], f['stage']) for f in got],
                         [('universe_community', 'обработка'), ('solar', 'ассеты: заливка на HF')])

    def test_missing_log_is_empty(self):
        self.assertEqual(notify.read_failures(self.tmp / 'nope.log'), [])


class SummaryTextTests(unittest.TestCase):
    def test_nothing_to_say(self):
        self.assertIsNone(notify.summary_text({'changed': []}, [], [], 'success'))

    def test_changed_only_keeps_old_message(self):
        t = notify.summary_text({'changed': ['solar']}, [], [], 'success')
        self.assertTrue(t.startswith('✅ SR Mods: автообновление отработало — обновлено паков: 1'))
        self.assertIn('solar', t)

    def test_unit_failure_is_reported_even_without_changes(self):
        fails = [{'name': 'universe_community', 'stage': 'обработка', 'error': 'неизвестный формат'}]
        t = notify.summary_text({'changed': []}, fails, [], 'success')
        self.assertTrue(t.startswith('❌'))
        self.assertIn('universe_community (обработка): неизвестный формат', t)

    def test_content_findings(self):
        s = {'changed': ['redux_fixes'], 'content': {'redux_fixes': [
            {'file': 'Mods/Exp/ExpPilotBridge/CFG/CacheData.dat', 'rule': 'cache-wrong-kind',
             'message': 'упакован ключом Main.dat'}]}}
        t = notify.summary_text(s, [], [], 'success')
        self.assertTrue(t.startswith('⚠️'))
        self.assertIn('redux_fixes: Mods/Exp/ExpPilotBridge/CFG/CacheData.dat — cache-wrong-kind', t)
        self.assertIn('Обновлено паков: 1 — redux_fixes', t)

    def test_failed_job_and_steps(self):
        steps = notify.failed_steps('assets=failure;code=success;descriptors=')
        self.assertEqual(steps, ['ассеты на HF'])
        t = notify.summary_text({'changed': []}, [], steps, 'failure')
        self.assertIn('Прогон: failure', t)
        self.assertIn('Шаги с ошибкой: ассеты на HF', t)

    def test_long_text_fits_telegram(self):
        fails = [{'name': f'u{i}', 'stage': 'обработка', 'error': 'x' * 300} for i in range(40)]
        self.assertLessEqual(len(notify.summary_text({}, fails, [], 'success')), notify.TG_LIMIT)


if __name__ == '__main__':
    unittest.main()
