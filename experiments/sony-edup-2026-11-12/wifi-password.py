"""Loopback-only password entry; send to owned Pi without retaining plaintext on PC."""
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
import shlex
import subprocess
import threading
from urllib.parse import parse_qs
from remote import BASE, OUT, OPTIONS

saved = json.loads((BASE/'private/wifi.json').read_text())
token = secrets.token_hex(24)
lock = threading.Lock()
applied = False
remote_code = '''import json,sys,subprocess
d=json.load(sys.stdin)
for name in ['Strehl EDUP 5 GHz','Strehl EDUP 6 GHz']:
 p=subprocess.run(['nmcli','connection','modify',name,'802-11-wireless-security.psk',d['password'],'802-11-wireless-security.psk-flags','0'],capture_output=True,text=True)
 if p.returncode:raise RuntimeError('Could not update EDUP credential')
p=subprocess.run(['nmcli','connection','modify','Strehl EDUP 5 GHz','802-11-wireless-security.pmf','0'],capture_output=True,text=True)
assert p.returncode==0
print('EDUP credentials applied')
'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, text, status=200):
        data = text.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Frame-Options', 'DENY')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path != '/':
            self.reply('Not found', 404);return
        if applied:
            self.reply('<h2>EDUP Wi-Fi settings saved.</h2><p>You can close this page.</p>');return
        self.reply('''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Strehl EDUP setup</title><style>body{background:#111918;color:#e8eeeb;font:18px system-ui;max-width:520px;margin:12vh auto;padding:24px}input,button{box-sizing:border-box;width:100%;padding:14px;margin-top:14px;font:inherit;border-radius:8px}button{background:#b4e1c5;border:0;color:#15231b}p{line-height:1.5;color:#c2cbc5}</style>
<h1>Connect EDUP Wi-Fi</h1><p>Enter the password for <b>Chris&amp;Ethan</b> to test WPA3 and 6 GHz. It goes directly to your Pi over SSH and is not saved as plaintext on this PC or sent into chat.</p>
<form method="post"><input type="hidden" name="csrf" value="'''+token+'''">
<label>Wi-Fi password<input type="password" name="password" required autofocus autocomplete="off"></label>
<button>Apply to EDUP</button></form>''')

    def do_POST(self):
        global applied
        host = '127.0.0.1:'+str(self.server.server_port)
        if self.path != '/' or self.headers.get('Host') != host or self.headers.get('Origin') not in (None, 'http://'+host):
            self.reply('Invalid origin', 403);return
        n = int(self.headers.get('Content-Length', '0'))
        if not 0 < n < 4096:
            self.reply('Invalid form size', 400);return
        fields = parse_qs(self.rfile.read(n).decode('utf-8'))
        if not hmac.compare_digest(fields.get('csrf', [''])[0], token):
            self.reply('Please reload the form.', 403);return
        password = fields.get('password', [''])[0]
        candidate = hashlib.pbkdf2_hmac('sha1', password.encode(), saved['ssid'].encode(), 4096, 32).hex()
        if not hmac.compare_digest(candidate, saved['psk']):
            self.reply('<h2>Password did not match.</h2><p>Go back and try the Chris&amp;Ethan Wi-Fi password again.</p>', 400);return
        with lock:
            if not applied:
                try:
                    p = subprocess.run(['ssh', *OPTIONS, 'strehl@10.0.0.187', 'sudo python3 -c '+shlex.quote(remote_code)],
                         input=json.dumps({'password':password}),capture_output=True,text=True,timeout=20,
                         creationflags=subprocess.CREATE_NO_WINDOW)
                    if p.returncode:
                        raise RuntimeError('Pi configuration failed')
                except Exception:
                    self.reply('<h2>Could not reach the Pi.</h2><p>Go back and try again. Nothing was saved on this PC.</p>', 503);return
                applied = True
                (OUT/'wifi-password-applied.json').write_text(json.dumps({'applied': True, 'plaintext_saved_on_pc': False})+'\n')
        self.reply('<h2>EDUP Wi-Fi settings saved.</h2><p>You can close this page.</p>')


if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    (OUT/'wifi-password-server.json').write_text(json.dumps({'port': server.server_port})+'\n')
    server.serve_forever()
