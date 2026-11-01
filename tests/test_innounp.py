# -*- coding: utf-8 -*-
"""innounp: закреплённая версия скачивается и сверяется по sha256; установщик Inno
незнакомой версии и ненулевой код возврата — понятная ошибка, а не «неизвестный формат»
и не молча урезанная распаковка (SR-4).

Сам innounp здесь не запускается: subprocess.run и скачивание подменены, тексты вывода
взяты из innounp.dpr 2.71.3.

Запускать: python -m unittest discover -s tests -t .
"""
import hashlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import aggregate  # noqa: E402

EXE = b'MZ fake innounp'


def _zip_with(name, data):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr(name, data)
    return buf.getvalue()


def _sha(b):
    return hashlib.sha256(b).hexdigest()


class _TmpDir(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.tmp = Path(d.name)


class FindInnounpTests(_TmpDir):
    def setUp(self):
        super().setUp()
        self.zip = _zip_with('innounp.exe', EXE)
        for name, value in (('REPO', self.tmp), ('INNOUNP_DIR', self.tmp / 'tools' / 'innounp'),
                            ('INNOUNP_ZIP_SHA256', _sha(self.zip)),
                            ('INNOUNP_EXE_SHA256', _sha(EXE))):
            p = patch.object(aggregate, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.calls = 0

    def _fake_download(self, payload):
        def dl(url, dest, token=None, timeout=300):
            self.calls += 1
            Path(dest).write_bytes(payload)
            return dest
        return patch.object(aggregate, 'download_url', side_effect=dl)

    def _find(self):
        with redirect_stdout(io.StringIO()):
            return aggregate._find_innounp()

    def test_downloads_once_then_uses_local_copy(self):
        with self._fake_download(self.zip):
            p = Path(self._find())
            self.assertEqual(p.read_bytes(), EXE)
            self.assertEqual(Path(self._find()), p)
        self.assertEqual(self.calls, 1)
        self.assertFalse((aggregate.INNOUNP_DIR / 'innounp.zip').exists())

    def test_stale_local_copy_is_replaced(self):
        aggregate.INNOUNP_DIR.mkdir(parents=True)
        (aggregate.INNOUNP_DIR / 'innounp.exe').write_bytes(b'MZ innounp 2.67.9')
        with self._fake_download(self.zip):
            self.assertEqual(Path(self._find()).read_bytes(), EXE)
        self.assertEqual(self.calls, 1)

    def test_wrong_archive_sum_fails_and_leaves_nothing(self):
        with self._fake_download(_zip_with('innounp.exe', b'MZ something else')):
            with self.assertRaisesRegex(RuntimeError, 'sha256 архива'):
                self._find()
        self.assertEqual(list(aggregate.INNOUNP_DIR.iterdir()), [])

    def test_download_error_is_explained(self):
        with patch.object(aggregate, 'download_url', side_effect=OSError('reset by peer')):
            with self.assertRaisesRegex(RuntimeError, 'не скачался.*reset by peer'):
                self._find()


def _run_returning(stdout, rc, write_into=None):
    """Подмена subprocess.run: вернуть заданный вывод; для -x — положить файл в -d<dir>."""
    calls = []

    def run(args, **kw):
        calls.append(args)
        if write_into is not None and '-x' in args:
            d = Path(next(a[2:] for a in args if a.startswith('-d')))
            (d / '{app}').mkdir(parents=True, exist_ok=True)
            (d / '{app}' / 'Rangers.exe').write_bytes(b'x')
        return subprocess.CompletedProcess(args, rc, stdout=stdout, stderr='')
    return patch.object(aggregate.subprocess, 'run', side_effect=run), calls


class InnoDetectTests(_TmpDir):
    def setUp(self):
        super().setUp()
        p = patch.object(aggregate, '_find_innounp', return_value='innounp.exe')
        self.find = p.start()
        self.addCleanup(p.stop)
        self.exe = self.tmp / 'Space_Rangers_Universe_18.09.26.exe'
        self.exe.write_bytes(b'MZ')

    def test_unknown_inno_version_is_a_clear_error(self):
        out = ('=> Signature detected:  Inno Setup Setup Data (7.0.0.3) (u)\n'
               ' *** This is not a supported version\n')
        p, _ = _run_returning(out, 3)
        with p, self.assertRaisesRegex(RuntimeError, r'незнакомой версии.*7\.0\.0\.3.*новый innounp'):
            aggregate._inno_exes(self.exe)

    def test_known_version_is_detected(self):
        p, calls = _run_returning('Inno Setup version detected: 7.0.0.3 (Unicode)\n', 0)
        with p:
            self.assertEqual(aggregate._inno_exes(self.exe), [self.exe])
        self.assertIn('-b', calls[0])

    def test_not_inno_is_skipped(self):
        out = ('The setup files are corrupted or made by incompatible version (Address: 0040)\n'
               "Maybe it's not an Inno Setup installation at all!\n")
        p, _ = _run_returning(out, 2)
        with p:
            self.assertEqual(aggregate._inno_exes(self.exe), [])

    def test_folder_without_candidates_does_not_need_innounp(self):
        d = self.tmp / 'folder'
        d.mkdir()
        (d / 'mods.zip').write_bytes(b'PK')
        self.assertEqual(aggregate._inno_exes(d), [])
        self.find.assert_not_called()


class InnoExtractTests(_TmpDir):
    def setUp(self):
        super().setUp()
        p = patch.object(aggregate, '_find_innounp', return_value='innounp.exe')
        p.start()
        self.addCleanup(p.stop)
        self.exe = self.tmp / 'setup.exe'
        self.exe.write_bytes(b'MZ')
        self.dest = self.tmp / 'out'

    def test_nonzero_exit_fails_even_if_files_appeared(self):
        p, calls = _run_returning('Setup files are corrupted (Address: 0040)\n', 2, write_into=True)
        with p, self.assertRaisesRegex(RuntimeError, 'повреждён.*код 2.*corrupted'):
            aggregate._innounp_extract(self.exe, self.dest)
        self.assertIn('-b', calls[0])

    def test_success(self):
        p, _ = _run_returning('', 0, write_into=True)
        with p:
            aggregate._innounp_extract(self.exe, self.dest)
        self.assertTrue((self.dest / '{app}' / 'Rangers.exe').exists())

    def test_zero_exit_but_nothing_extracted(self):
        p, _ = _run_returning('', 0)
        with p, self.assertRaisesRegex(RuntimeError, 'ничего не извлёк'):
            aggregate._innounp_extract(self.exe, self.dest)


if __name__ == '__main__':
    unittest.main()
