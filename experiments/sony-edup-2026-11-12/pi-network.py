"""Run on the Pi as root. Credentials stay inside NetworkManager/root backup."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

NAMES = {'5': 'Strehl EDUP 5 GHz', '6': 'Strehl EDUP 6 GHz'}
MAC = 'E8:4E:06:AF:DB:70'
BSSID = {'5': 'AE:4C:A5:BE:57:FE', '6': 'AC:4C:A5:C5:57:FF'}


def run(args, check=True, timeout=55):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    print(json.dumps({'command': args, 'exit': p.returncode,
                      'stdout': p.stdout, 'stderr': p.stderr}), flush=True)
    if check and p.returncode:
        raise RuntimeError('Network command failed')
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('op', choices=['setup', 'connect', 'status', 'prefer'])
    ap.add_argument('--band', choices=['5', '6'], default='5')
    a = ap.parse_args()
    assert Path('/sys/class/net/wlan1/address').read_text().strip().upper() == MAC
    if a.op == 'setup':
        backup = Path('/root/strehl-edup-20261112')
        backup.mkdir(mode=0o700, exist_ok=True)
        if not (backup/'network-before').exists():
            shutil.copytree('/etc/NetworkManager/system-connections', backup/'network-before')
        names = subprocess.run(['nmcli', '-g', 'NAME', 'connection', 'show'],
                               capture_output=True, text=True, check=True).stdout.splitlines()
        for band, name in NAMES.items():
            if name not in names:
                run(['nmcli', 'connection', 'clone', 'Strehl home', name])
            options = ['connection.interface-name', 'wlan1', 'connection.autoconnect', 'no',
                       '802-11-wireless.mac-address', MAC,
                       '802-11-wireless.cloned-mac-address', 'permanent',
                       '802-11-wireless.bssid', BSSID[band], '802-11-wireless.band', '',
                       '802-11-wireless.powersave', '2', 'ipv4.route-metric', '800']
            if band == '6':
                options += ['802-11-wireless-security.key-mgmt', 'sae',
                            '802-11-wireless-security.pmf', '3']
            run(['nmcli', 'connection', 'modify', name, *options])
        return
    if a.op == 'connect':
        run(['nmcli', '--wait', '50', 'connection', 'up', NAMES[a.band], 'ifname', 'wlan1'])
    if a.op == 'prefer':
        # Call only after connectivity and a separate rollback have been armed.
        run(['nmcli', 'connection', 'modify', 'Strehl home',
             'connection.interface-name', 'wlan0', 'ipv4.route-metric', '600'])
        run(['nmcli', 'connection', 'modify', NAMES[a.band], 'connection.autoconnect', 'yes',
             'connection.autoconnect-priority', '100', 'ipv4.route-metric', '100'])
        run(['nmcli', 'device', 'reapply', 'wlan1'])
    for c in [['iw', 'dev', 'wlan1', 'link'], ['ip', '-j', 'address', 'show', 'wlan1'],
              ['ip', '-j', 'route'], ['cat', '/proc/loadavg']]:
        run(c)


if __name__ == '__main__':
    main()
