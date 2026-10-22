"""Transport adapter checks; these do not claim browser execution."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('demo_mcp', Path(__file__).resolve().parents[1] / 'examples/first-user-demo/mcp_client.py')
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class Response(io.BytesIO):
    headers = {'Mcp-Session-Id': 'test-session'}


class ClientTests(unittest.TestCase):
    def test_sse_matches_request_id_and_preserves_session(self):
        raw = b'data: {"jsonrpc":"2.0","method":"notification"}\n\ndata: {"jsonrpc":"2.0","id":"123","result":{"ok":true}}\n\n'
        with patch.object(client.urllib.request, 'urlopen', return_value=Response(raw)) as send:
            result, session = client.request({'jsonrpc':'2.0','id':'123','method':'tools/list'}, 'previous')
        self.assertEqual(result, {'ok':True})
        self.assertEqual(session, 'test-session')
        self.assertEqual(send.call_args.args[0].get_header('Mcp-session-id'), 'previous')

    def test_sse_multiline_data_and_empty_events(self):
        raw = b'data:\n\ndata: {"jsonrpc":"2.0","id":"123",\ndata: "result":{"ok":true}}\n\n'
        with patch.object(client.urllib.request, 'urlopen', return_value=Response(raw)):
            result, _ = client.request({'id':'123'})
        self.assertEqual(result, {'ok':True})

    def test_jsonl_session_does_not_collide_with_transcript(self):
        with tempfile.TemporaryDirectory() as temp:
            session = Path(temp)/'persona.jsonl'
            session.write_text(json.dumps({'session':'fake'}))
            result = {'content':[{'type':'text','text':'ok'}]}
            with patch.object(sys, 'argv', ['client','--session',str(session),'browser_snapshot']), patch.object(client, 'request', return_value=(result, 'fake')), contextlib.redirect_stdout(io.StringIO()):
                client.main()
                self.assertEqual(json.loads(session.read_text()), {'session':'fake'})
                client.main()
            self.assertEqual(json.loads(session.read_text()), {'session':'fake'})

    def test_json_rpc_error_is_not_success(self):
        with patch.object(client.urllib.request, 'urlopen', return_value=Response(b'{"id":1,"error":{"code":-1,"message":"failed"}}')):
            with self.assertRaises(RuntimeError):
                client.request({'id':1})

    def test_http_failure_preserves_actionable_message(self):
        error = urllib.error.HTTPError(client.ENDPOINT, 403, 'Forbidden', {}, io.BytesIO(b'Expected localhost'))
        with patch.object(client.urllib.request, 'urlopen', side_effect=error):
            with self.assertRaisesRegex(RuntimeError, 'MCP HTTP 403: Expected localhost'):
                client.request({'id':1})

    def test_image_payloads_are_not_printed_or_logged(self):
        with tempfile.TemporaryDirectory() as temp:
            session = Path(temp)/'test.json'
            session.write_text(json.dumps({'session':'fake'}))
            result = {'content':[{'type':'text','text':'screenshot saved'},{'type':'image','data':'BASE64_MUST_STAY_OUT'}]}
            output = io.StringIO()
            with patch.object(sys, 'argv', ['client','--session',str(session),'browser_take_screenshot']), patch.object(client, 'request', return_value=(result, 'fake')), contextlib.redirect_stdout(output):
                client.main()
            self.assertIn('screenshot saved', output.getvalue())
            self.assertNotIn('BASE64_MUST_STAY_OUT', output.getvalue()+session.with_name(session.name + '.transcript.jsonl').read_text())


if __name__ == '__main__':
    unittest.main()
