"""Telegram notifications with the HTTP client replaced."""

import io
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from pipeline import notify


class TelegramNotify(unittest.TestCase):
    def run_notify(self, kind, responses, summary='{}', **settings):
        env = {'TG_BOT_TOKEN': 'primary', 'TG_CHAT_ID': '10', **settings}
        captured = []
        responses = iter(responses)

        def fake_urlopen(url, data, timeout):
            captured.append((urlsplit(url).path, parse_qs(data.decode('utf-8'))))
            response = next(responses)
            if isinstance(response, Exception):
                raise response
            return io.BytesIO(response)

        output = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(notify.sys, 'argv', ['notify.py', kind]), \
                mock.patch.object(notify, 'open', mock.mock_open(read_data=summary), create=True), \
                mock.patch.object(notify, 'read_failures', return_value=[]), \
                mock.patch.object(notify.urllib.request, 'urlopen', side_effect=fake_urlopen), \
                redirect_stdout(output):
            status = notify.main()
        return status, captured, output.getvalue()

    def test_both_modes_send_same_text_to_all_chats(self):
        inputs = (
            ('manual', '{"manual":["example"]}', 'example'),
            ('summary', '{"changed":["example"]}', 'example'),
        )
        for kind, summary, expected_text in inputs:
            with self.subTest(kind=kind):
                status, requests, _ = self.run_notify(
                    kind, [b'{"ok":true}'] * 3, summary,
                    TG_EXTRA_CHAT_IDS=' 20, ,30,20 ', TG_EXTRA_BOT_TOKEN=' secondary ')
                self.assertEqual(status, 0)
                self.assertEqual([fields['chat_id'][0] for _, fields in requests], ['10', '20', '30'])
                self.assertEqual([path for path, _ in requests],
                                 ['/botprimary/sendMessage', '/botsecondary/sendMessage',
                                  '/botsecondary/sendMessage'])
                messages = [fields['text'][0] for _, fields in requests]
                self.assertEqual(messages, [messages[0]] * 3)
                self.assertIn(expected_text, messages[0])

    def test_notify_test_uses_extra_chat_and_primary_token_fallback(self):
        for kind in ('manual', 'summary'):
            with self.subTest(kind=kind):
                status, requests, _ = self.run_notify(
                    kind, [b'{"ok":true}'] * 2, NOTIFY_TEST='true', TG_EXTRA_CHAT_IDS='20')
                self.assertEqual(status, 0)
                self.assertEqual([path for path, _ in requests], ['/botprimary/sendMessage'] * 2)
                self.assertEqual([fields['chat_id'][0] for _, fields in requests], ['10', '20'])
                self.assertEqual(requests[0][1]['text'], requests[1][1]['text'])

    def test_extra_failure_is_logged_and_next_recipient_still_gets_message(self):
        failure = HTTPError('https://example.test/botsecondary', 403, 'secondary', {},
                            io.BytesIO(b'{"description":"secondary"}'))
        status, requests, output = self.run_notify(
            'summary', [b'{"ok":true}', failure, b'{"ok":true}'], NOTIFY_TEST='true',
            TG_EXTRA_CHAT_IDS='20,30', TG_EXTRA_BOT_TOKEN='secondary')
        self.assertEqual(status, 0)
        self.assertEqual(len(requests), 3)
        self.assertIn('HTTP 403', output)
        self.assertNotIn('secondary', output)

    def test_primary_failure_controls_exit_code_but_extras_are_attempted(self):
        status, requests, output = self.run_notify(
            'manual', [URLError('URL containing primary'), b'{"ok":true}'],
            NOTIFY_TEST='true', TG_EXTRA_CHAT_IDS='20')
        self.assertEqual(status, 1)
        self.assertEqual(len(requests), 2)
        self.assertIn('сетевая ошибка', output)
        self.assertNotIn('primary', output)

    def test_no_extra_chat_preserves_single_send(self):
        status, requests, _ = self.run_notify('summary', [b'{"ok":true}'], NOTIFY_TEST='true')
        self.assertEqual(status, 0)
        self.assertEqual(len(requests), 1)

    def test_no_updates_means_no_notifications(self):
        status, requests, _ = self.run_notify('summary', [], TG_EXTRA_CHAT_IDS='20')
        self.assertEqual(status, 0)
        self.assertEqual(requests, [])
