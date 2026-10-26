#!/usr/bin/env python3
"""Offline, synthetic onboarding fixture. Never deploy as a real service."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


def page(route, variant):
    seeded = variant == 'seeded'
    cta = '/pricing' if seeded else '/start'
    price = '<p id="plan-price">Contact us for pricing</p>' if seeded else '<p id="plan-price">Sandbox plan: $0, no payment required</p>'
    mobile_bug = '@media(max-width:400px){#primary-cta{display:none}}' if seeded else ''
    common = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Workspace Lab</title><style>
    body{font:16px/1.55 system-ui,sans-serif;margin:0;background:#f5f7fb;color:#17202b}main{max-width:660px;margin:5rem auto;padding:2rem;background:white;border:1px solid #e2e8ef;border-radius:18px}header{background:#182838;color:white;padding:1rem 2rem}header a{color:white;margin-right:1.5rem}h1{font-size:2.4rem;line-height:1.15}a.btn,button{display:inline-block;background:#195e99;color:white;padding:.8rem 1.2rem;border:0;border-radius:8px;font:inherit;cursor:pointer}input{display:block;width:100%;max-width:400px;box-sizing:border-box;font:inherit;padding:.6rem;margin:.5rem 0 1rem}label{font-weight:600}.muted{color:#536272}#error{color:#a82428}''' + mobile_bug + '</style></head><body><header><nav><a href="/">Home</a><a href="/pricing">Pricing</a><a href="/start">Create workspace</a></nav></header><main>'
    if route == '/':
        body = '<h1>Make your first workspace</h1><p>Organize one small project without creating a production account.</p><a id="primary-cta" class="btn" href="' + cta + '">Create free workspace</a>'
    elif route == '/pricing':
        body = '<h1>Pricing</h1><p>Understand the cost before starting.</p>' + price + '<a class="btn" id="plan-cta" href="/start">Continue to workspace</a>'
    elif route == '/start':
        guard = '' if seeded else 'if (!name) { error.textContent = "Workspace name is required"; return; }'
        dedup = '' if seeded else 'if (names.includes(name)) { render(); return; }'
        body = '''<h1>Create your workspace</h1><p class="muted">Local test data only; no account or payment.</p><form id="workspace-form"><label for="name">Workspace name</label><input id="name" autocomplete="off" placeholder="e.g. Test Project"><button id="submit" type="submit">Create workspace</button></form><p id="error" role="alert"></p><section id="result" aria-live="polite"></section><script>
        const form = document.querySelector('#workspace-form');
        const error = document.querySelector('#error');
        const result = document.querySelector('#result');
        const storageKey = 'workspace-lab-' + ''' + repr(variant) + ''';
        const getNames = () => JSON.parse(localStorage.getItem(storageKey) || '[]');
        const render = () => { const names=getNames(); result.textContent=''; if(names.length) { const p=document.createElement('p'); p.dataset.testid='workspace-ready'; p.textContent='Workspace ready: '+names[names.length-1]; result.append(p); const count=document.createElement('span'); count.dataset.testid='workspace-count'; count.textContent=String(names.length); result.append(count); }};
        form.addEventListener('submit', (ev) => { ev.preventDefault(); error.textContent=''; const name=document.querySelector('#name').value.trim(); const names=getNames();
        ''' + guard + '\n' + dedup + '''
        names.push(name); localStorage.setItem(storageKey,JSON.stringify(names)); render(); });
        </script>'''
    else:
        return None
    return (common + body + '</main></body></html>').encode('utf-8')


class Handler(BaseHTTPRequestHandler):
    variant = 'seeded'

    def do_GET(self):
        route = urlsplit(self.path).path
        data = page(route, self.variant)
        if data is None:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass


def server(variant, port):
    class LabHandler(Handler):
        pass
    LabHandler.variant = variant
    return ThreadingHTTPServer(('127.0.0.1', port), LabHandler)


def main():
    parser = argparse.ArgumentParser(description='Synthetic, localhost-only First User Audit evaluation fixture')
    parser.add_argument('--variant', choices=('seeded', 'reference'), required=True)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    with server(args.variant, args.port) as app:
        print(f'Fixture {args.variant} available at http://127.0.0.1:{app.server_port}/', flush=True)
        app.serve_forever()


if __name__ == '__main__':
    main()
