"""Workspace-local SSH runner. Does not print or package private identities."""
from pathlib import Path
import argparse
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'outputs/pi-capture-2026-11-11'
OUT = ROOT/'outputs/sony-edup-2026-11-12'
OPTIONS = ['-i', str(BASE/'private/pi-admin-ed25519'), '-o',
           'UserKnownHostsFile='+str(BASE/'private/pi-known-hosts'), '-o',
           'BatchMode=yes', '-o', 'ConnectTimeout=8']


def ssh(script, host='10.0.0.187', root=False, args=(), timeout=60):
    command = ('sudo ' if root else '')+'python3 -'
    # Only internally selected simple arguments are accepted for the remote shell.
    assert all(str(s).replace('-', '').isalnum() for s in args)
    command += ''.join(' '+str(s) for s in args)
    host_options=OPTIONS+(['-o','HostKeyAlias=10.0.0.187'] if host=='10.0.0.178' else [])
    return subprocess.run(['ssh', *host_options, 'strehl@'+host, command],
                          input=script, capture_output=True, text=True, timeout=timeout)


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('op', choices=['setup','connect','status','prefer'])
    p.add_argument('--band', choices=['5','6'], default='5');p.add_argument('--host', default='10.0.0.187')
    p.add_argument('--label', required=True);a = p.parse_args()
    r = ssh(Path(__file__).with_name('pi-network.py').read_text(), a.host,
            root=True, args=[a.op, '--band', a.band])
    (OUT/(a.label+'.jsonl')).write_text(r.stdout)
    print(r.stdout);print(r.stderr)
    assert r.returncode == 0, r.returncode
