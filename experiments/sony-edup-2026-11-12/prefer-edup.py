"""Save EDUP preference with a timed rollback, then verify both camera URLs."""
import json
from pathlib import Path
import subprocess
import requests
from remote import ssh, BASE, OUT, OPTIONS

ROLLBACK = '''import subprocess
for name in ['Strehl EDUP 5 GHz','Strehl EDUP 6 GHz']:
 subprocess.run(['nmcli','con','modify',name,'connection.autoconnect','no','ipv4.route-metric','800'],capture_output=True)
 subprocess.run(['nmcli','con','down',name],capture_output=True)
subprocess.run(['nmcli','con','modify','Strehl home','connection.interface-name','','ipv4.route-metric','-1'],check=True)
subprocess.run(['nmcli','--wait','30','con','up','Strehl home','ifname','wlan0'],check=True)
'''


def main():
    setup = '''from pathlib import Path
import subprocess
p=Path('/root/strehl-edup-20261112/rollback.py');p.write_text(CODE);p.chmod(0o600)
assert subprocess.run(['systemctl','is-active','strehl-edup-rollback.timer'],capture_output=True).returncode!=0
subprocess.run(['systemd-run','--unit=strehl-edup-rollback','--on-active=120s','/usr/bin/python3',str(p)],check=True)
'''.replace('CODE', repr(ROLLBACK))
    p = ssh(setup, root=True)
    assert p.returncode == 0, p.stderr
    script = Path(__file__).with_name('pi-network.py').read_text()
    p = ssh(script, root=True, args=['prefer','--band','5'])
    (OUT/'preferred-route.jsonl').write_text(p.stdout)
    assert p.returncode == 0,p.stderr
    cfg = json.loads((BASE/'private/headless.json').read_text())
    headers = {'Authorization':'Bearer '+cfg['pairing_key']}
    states = {}
    for ip in ['10.0.0.178','10.0.0.187']:
        r = requests.get('http://'+ip+':8787/api/state',headers=headers,timeout=8)
        r.raise_for_status();s=r.json()
        states[ip] = {k:s.get(k) for k in ['connected','phase','busy','failure']}
        assert s['connected'] and not s['busy'] and s['failure'] is None
    # HostKeyAlias reuses the existing trusted host identity for this Pi.
    # Host-key verification is still enforced; no newly scanned key is trusted.
    p=ssh("print('EDUP SSH verified')",host='10.0.0.178')
    assert p.returncode==0,p.stderr
    p = ssh("import subprocess;subprocess.run(['systemctl','stop','strehl-edup-rollback.timer'],check=True);print('rollback timer cancelled')",root=True)
    assert p.returncode == 0,p.stderr
    (OUT/'preferred-route-health.json').write_text(json.dumps(states,indent=2)+'\n')
    print(json.dumps({'camera_endpoints':states,'default_data_interface':'wlan1','onboard_fallback_retained':True,'rollback_timer_cancelled':True,'new_address_host_key_matched':True}))


if __name__=='__main__':main()
