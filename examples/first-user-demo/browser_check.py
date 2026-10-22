#!/usr/bin/env python3
"""Deterministic fixture smoke checks through MCP; NOT independent personas."""
import argparse
import json
import time

from mcp_client import request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=('baseline', 'fixed'), required=True)
    args = parser.parse_args()
    _, session = request({'jsonrpc':'2.0','id':'init','method':'initialize','params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'demo-smoke','version':'0.1.0'}}})
    request({'jsonrpc':'2.0','method':'notifications/initialized'}, session)

    def tool(name, arguments):
        result, _ = request({'jsonrpc':'2.0','id':str(time.time_ns()),'method':'tools/call','params':{'name':name,'arguments':arguments}}, session)
        text = '\n'.join(x['text'] for x in result.get('content', []) if x['type'] == 'text')
        if result.get('isError'):
            raise RuntimeError(text)
        return text

    def observe(function):
        text = tool('browser_evaluate', {'function': function})
        return json.JSONDecoder().raw_decode(text.split('### Result\n', 1)[1].lstrip())[0]

    base = 'http://127.0.0.1:4179'
    try:
        tool('browser_navigate', {'url': base})
        tool('browser_resize', {'width':375, 'height':812})
        start = observe('() => ({width:innerWidth, overflow:document.documentElement.scrollWidth>innerWidth, storage:localStorage.length, cta:document.querySelector(".button").getAttribute("href"), privacy:document.querySelector("#privacy-link").getAttribute("href")})')
        assert start['width'] == 375 and start['storage'] == 0, start
        fixed = args.variant == 'fixed'
        assert start['overflow'] is not fixed, start
        assert start['cta'] == ('/create' if fixed else '#start'), start
        tool('browser_navigate', {'url':base + start['privacy']})
        assert observe('() => document.querySelector("h1").textContent') == ('Demo privacy' if fixed else 'Error response')
        tool('browser_navigate', {'url':base + '/create'})
        tool('browser_click', {'target':'button[type=submit]'})
        invalid = observe('() => ({path:location.pathname, data:JSON.parse(localStorage.getItem("task-cabin-demo-v1")||"[]"), error:document.querySelector("#error")?.textContent})')
        if fixed:
            assert invalid['path'] == '/create' and not invalid['data'] and invalid['error'], invalid
            tool('browser_fill_form', {'fields':[{'target':'#name','name':'Workspace name','type':'textbox','value':'Smoke test workspace'}]})
            tool('browser_click', {'target':'button[type=submit]'})
            success = observe('() => ({path:location.pathname, text:document.body.textContent, data:JSON.parse(localStorage.getItem("task-cabin-demo-v1")||"[]")})')
            assert success['path'] == '/workspace' and len(success['data']) == 1 and success['data'][0]['name'] == 'Smoke test workspace' and 'Plan first release' in success['text'], success
            tool('browser_click', {'target':'#reset'})
            assert observe('() => localStorage.length') == 0
        else:
            assert invalid['path'] == '/workspace' and len(invalid['data']) == 1 and invalid['data'][0]['name'] == '', invalid
        print(f'{args.variant}: responsive layout, navigation, invalid input, storage contract checks passed' + ('; success and reset checked' if fixed else '; intentional defects reproduced'))
    finally:
        tool('browser_close', {})


if __name__ == '__main__':
    main()
