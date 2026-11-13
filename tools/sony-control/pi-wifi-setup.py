"""Local-only one-shot Wi-Fi credential entry; never prints or logs the password."""
import argparse
import hashlib
import html
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--ssid', required=True)
parser.add_argument('--port', type=int, default=0)
args = parser.parse_args()
nonce = secrets.token_hex(24)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def page(self, text, code=200):
        data = text.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.page(f'''<!doctype html><meta name="viewport" content="width=device-width"><title>Strehl · Pi Wi-Fi</title>
<style>body{{background:#111418;color:#e5e7eb;font:17px system-ui;max-width:600px;margin:8vh auto;padding:24px}}h1{{font-weight:500}}input,button{{display:block;width:100%;box-sizing:border-box;margin:12px 0 24px;padding:12px;background:#22272e;border:1px solid #464c54;border-radius:8px;color:inherit;font:inherit}}button{{background:#b9cc9c;color:#161b13}}small{{color:#a9b0ba}}</style>
<small>STREHL / PI SETUP · THIS COMPUTER ONLY</small><h1>Connect the camera host</h1>
<p>Enter the Wi-Fi password here. It stays on this computer and the Pi setup card.</p>
<form method="post"><input type="hidden" name="nonce" value="{nonce}"><label>Network name<input name="ssid" value="{html.escape(args.ssid, quote=True)}" required></label><label>Wi-Fi password<input name="password" type="password" minlength="8" maxlength="64" autocomplete="off" required></label><button>Save Wi-Fi settings</button></form>''')

    def do_POST(self):
        origin = self.headers.get('Origin', '')
        if origin != f'http://127.0.0.1:{self.server.server_port}':
            return self.page('Open the setup page on this PC.', 403)
        n = int(self.headers.get('Content-Length', '0'))
        if not 0 < n < 8192:
            return self.page('Invalid request.', 400)
        data = parse_qs(self.rfile.read(n).decode('utf-8'))
        if data.get('nonce') != [nonce]:
            return self.page('Reload the setup page.', 403)
        ssid = data.get('ssid', [''])[0]
        password = data.get('password', [''])[0]
        if not 1 <= len(ssid.encode('utf-8')) <= 32 or not 8 <= len(password) <= 63:
            return self.page('Check the network name and password length.', 400)
        psk = hashlib.pbkdf2_hmac('sha1', password.encode('utf-8'), ssid.encode('utf-8'), 4096, 32).hex()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({'ssid': ssid, 'psk': psk, 'country': 'US'}) + '\n', encoding='utf-8')
        self.page('<title>Strehl · Saved</title><h1>Wi-Fi settings saved.</h1><p>You can close this tab. The Pi image can now be prepared.</p>')


server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
print(f'Wi-Fi setup: http://127.0.0.1:{server.server_port}/', flush=True)
server.serve_forever()
