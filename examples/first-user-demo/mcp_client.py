#!/usr/bin/env python3
"""Small local MCP HTTP adapter for this demo, not an agent or audit runner."""
import argparse
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

ENDPOINT = 'http://localhost:8931/mcp'


def request(message, session=None):
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': '2025-03-26'}
    if session:
        headers['Mcp-Session-Id'] = session
    req = urllib.request.Request(ENDPOINT, data=json.dumps(message).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            raw = response.read().decode()
            session = response.headers.get('Mcp-Session-Id', session)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'MCP HTTP {exc.code}: {exc.read().decode()}') from exc
    if not raw:
        return None, session
    if raw.lstrip().startswith('{'):
        payload = json.loads(raw)
    else:
        messages, data = [], []
        for line in raw.splitlines() + ['']:
            if not line:
                joined = '\n'.join(data)
                if joined.strip():
                    messages.append(json.loads(joined))
                data = []
            elif line == 'data':
                data.append('')
            elif line.startswith('data:'):
                value = line[5:]
                data.append(value[1:] if value.startswith(' ') else value)
        matches = [item for item in messages if isinstance(item, dict) and item.get('id') == message.get('id')]
        if not matches:
            raise RuntimeError('No matching MCP JSON-RPC response')
        payload = matches[-1]
    if 'error' in payload:
        raise RuntimeError(payload['error'])
    return payload.get('result'), session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True, help='Ignored session state file; use a new path per persona')
    parser.add_argument('tool', help='MCP tool name, or tools/list')
    parser.add_argument('arguments', nargs='?', default='{}', help='JSON object with tool arguments')
    args = parser.parse_args()
    if args.session.exists():
        session = json.loads(args.session.read_text())['session']
    else:
        _, session = request({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'first-user-demo-adapter','version':'0.1.0'}}})
        request({'jsonrpc':'2.0','method':'notifications/initialized'}, session)
        args.session.parent.mkdir(parents=True, exist_ok=True)
        args.session.write_text(json.dumps({'session': session}))
    message = {'jsonrpc':'2.0','id':str(time.time_ns()),'method':'tools/list' if args.tool == 'tools/list' else 'tools/call'}
    if args.tool != 'tools/list':
        message['params'] = {'name':args.tool,'arguments':json.loads(args.arguments)}
    result, _ = request(message, session)
    if args.tool == 'tools/list':
        print(json.dumps(result, indent=2))
    else:
        # Screenshots are written by the server; never print base64 image payloads.
        text = '\n'.join(item['text'] for item in result.get('content', []) if item['type'] == 'text')
        print(text)
        log = args.session.with_name(args.session.name + '.transcript.jsonl')
        with log.open('a') as output:
            output.write(json.dumps({'tool':args.tool,'arguments':message['params']['arguments'],'text':text,'isError':result.get('isError',False)})+'\n')
        if result.get('isError'):
            raise SystemExit(1)


if __name__ == '__main__':
    main()
