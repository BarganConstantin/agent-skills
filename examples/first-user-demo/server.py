#!/usr/bin/env python3
"""Synthetic audit fixture. Loopback only, no accounts or external integrations."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

APP = Path(__file__).resolve().parent / 'app'


def handler(variant):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            route = urlsplit(self.path).path
            if route == '/config.js':
                content = f'window.DEMO_VARIANT = {json.dumps(variant)};'.encode()
                mime = 'application/javascript'
            elif route in ('/', '/create', '/workspace', '/pricing', '/terms', '/privacy'):
                content, mime = (APP / 'index.html').read_bytes(), 'text/html; charset=utf-8'
            elif route in ('/app.js', '/style.css'):
                content = (APP / route.lstrip('/')).read_bytes()
                mime = 'application/javascript' if route.endswith('.js') else 'text/css'
            else:
                self.send_error(404, 'Demo page not found')
                return
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(content)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=('baseline', 'fixed'), default='baseline')
    parser.add_argument('--port', type=int, default=4179)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler(args.variant))
    print(f'Demo {args.variant}: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
