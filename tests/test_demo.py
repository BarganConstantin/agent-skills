"""HTTP contract for the optional, synthetic localhost fixture."""
import importlib.util
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

spec = importlib.util.spec_from_file_location('demo', Path(__file__).resolve().parents[1] / 'examples/first-user-demo/server.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), demo.handler('fixed'))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_journey_and_policy_routes_are_local_and_uncached(self):
        for route in ('/', '/create', '/workspace', '/pricing', '/terms', '/privacy'):
            with self.subTest(route=route), urllib.request.urlopen(self.url + route) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                self.assertIn("connect-src 'self'", response.headers['Content-Security-Policy'])
                self.assertIn('Local demo', response.read().decode())

    def test_variant_and_unknown_route(self):
        with urllib.request.urlopen(self.url + '/config.js') as response:
            self.assertIn('"fixed"', response.read().decode())
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self.url + '/privacy-policy')
        self.assertEqual(ctx.exception.code, 404)

    def test_server_does_not_serve_repository_files_or_mutating_endpoints(self):
        for route in ('/../../README.md', '/LICENSE', '/reset'):
            with self.subTest(route=route), self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(self.url + route)
            self.assertEqual(ctx.exception.code, 404)
        request = urllib.request.Request(self.url + '/create', data=b'no writes')
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request)
        self.assertEqual(ctx.exception.code, 501)


if __name__ == '__main__':
    unittest.main()
