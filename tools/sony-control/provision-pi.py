#!/usr/bin/env python3
"""Provision an already mounted, disposable Pi OS image; never opens a physical disk."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--private',type=Path,required=True)
    args=parser.parse_args()
    root=args.root.resolve()
    assert root!=Path('/') and root.name=='strehl-pi-root'
    source=subprocess.check_output(['findmnt','-n','-o','SOURCE','--target',str(root)],text=True).strip()
    assert source.startswith('/dev/loop'), 'Only a mounted image loop device may be provisioned'
    assert (root/'etc/os-release').is_file() and (root/'boot/firmware/cmdline.txt').is_file()
    assert 'strehl:' not in (root/'etc/passwd').read_text() or 'strehl:x:1001:1001:' in (root/'etc/passwd').read_text()
    if 'strehl:' not in (root/'etc/passwd').read_text():
        subprocess.run(['useradd','--prefix',str(root),'-m','-U','-u','1001','-s','/bin/bash','-G','sudo,plugdev,netdev','strehl'],check=True)
    uid=gid=1001
    def write(name,text,mode=0o644,owner=None):
        path=root/name.lstrip('/')
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text.rstrip()+'\n')
        path.chmod(mode)
        if owner:os.chown(path,*owner)
    def link(name,target):
        path=root/name.lstrip('/');path.parent.mkdir(parents=True,exist_ok=True)
        if path.is_symlink():path.unlink()
        assert not path.exists(),f'Refusing to replace {path}'
        path.symlink_to(target)
    package=root/'opt/strehl-capture'
    shutil.copytree(args.build,package,dirs_exist_ok=True)
    for name in ('strehl-capture-headless','strehl-sony-control'):(package/name).chmod(0o755)
    state=root/'var/lib/strehl-capture';state.mkdir(parents=True,exist_ok=True);state.chmod(0o700);os.chown(state,uid,gid)
    write('/etc/strehl-capture/headless.json',(args.private/'headless.json').read_text(),0o600,(uid,gid))
    (root/'etc/strehl-capture').chmod(0o750);os.chown(root/'etc/strehl-capture',uid,gid)
    write('/home/strehl/.ssh/authorized_keys',(args.private/'pi-admin-ed25519.pub').read_text(),0o600,(uid,gid))
    ssh=root/'home/strehl/.ssh';ssh.chmod(0o700);os.chown(ssh,uid,gid)
    write('/etc/hostname','strehl')
    hosts=(root/'etc/hosts').read_text().replace('raspberrypi','strehl')
    write('/etc/hosts',hosts)
    write('/etc/sudoers.d/090-strehl','strehl ALL=(ALL) NOPASSWD: ALL',0o440)
    write('/etc/ssh/sshd_config.d/00-strehl.conf','''PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
AllowUsers strehl@10.0.0.0/24 strehl@127.0.0.1
AddressFamily inet''')
    # User is already provisioned. Skip the stock image's interactive rename prompt.
    for service in ('userconfig.service','sshswitch.service','cloud-init-local.service','cloud-init-main.service','cloud-init-network.service','cloud-config.service','cloud-final.service'):
        link('/etc/systemd/system/'+service,'/dev/null')
    write('/etc/cloud/cloud-init.disabled','Strehl offline image is already configured')
    banner=root/'etc/ssh/sshd_config.d/rename_user.conf'
    if banner.exists():banner.unlink()
    wifi=json.loads((args.private/'wifi.json').read_text())
    assert wifi['ssid']=='Chris&Ethan' and len(wifi['psk'])==64 and all(c in '0123456789abcdef' for c in wifi['psk'])
    write('/etc/NetworkManager/system-connections/strehl-home.nmconnection',f'''[connection]
id=Strehl home
type=wifi
autoconnect=true
autoconnect-retries=0

[wifi]
mode=infrastructure
ssid={wifi['ssid']}
powersave=2

[wifi-security]
key-mgmt=wpa-psk
psk={wifi['psk']}

[ipv4]
method=auto
dhcp-hostname=strehl

[ipv6]
method=disabled''',0o600)
    write('/etc/modprobe.d/strehl-wifi.conf','options cfg80211 ieee80211_regdom=US')
    write('/var/lib/NetworkManager/NetworkManager.state','''[main]
NetworkingEnabled=true
WirelessEnabled=true
WWANEnabled=true''',0o600)
    # Mask both swap generators; the image buffer itself also refuses swap.
    for generator in ('rpi-swap-generator','zram-generator'):
        link('/etc/systemd/system-generators/'+generator,'/dev/null')
    write('/etc/systemd/system/run-strehl\\x2draw.mount','''[Unit]
Description=Strehl RAW buffer in unswappable RAM
Before=strehl-capture.service

[Mount]
What=tmpfs
Where=/run/strehl-raw
Type=tmpfs
Options=size=512M,noswap,nodev,nosuid,noexec,mode=0700,uid=1001,gid=1001

[Install]
WantedBy=multi-user.target''')
    write('/etc/udev/rules.d/70-strehl-camera.rules','SUBSYSTEM=="usb", ATTR{idVendor}=="054c", MODE="0660", GROUP="plugdev"')
    write('/etc/systemd/system/strehl-radio.service','''[Unit]
Description=Enable local Wi-Fi radio for Strehl
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
ExecStart=/usr/sbin/rfkill unblock wifi
ExecStart=/usr/sbin/iw reg set US
ExecStart=/usr/bin/nmcli radio wifi on
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target''')
    write('/etc/systemd/system/strehl-capture.service','''[Unit]
Description=Strehl Capture headless LAN controller
After=network.target run-strehl\\x2draw.mount
Requires=run-strehl\\x2draw.mount
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
User=strehl
Group=strehl
SupplementaryGroups=plugdev
WorkingDirectory=/opt/strehl-capture
Environment=LD_LIBRARY_PATH=/opt/strehl-capture:/opt/strehl-capture/CrAdapter
ExecStart=/opt/strehl-capture/strehl-capture-headless --config /etc/strehl-capture/headless.json
Restart=on-failure
RestartSec=5
TimeoutStopSec=240
KillSignal=SIGINT
UMask=0077
LimitCORE=0
MemorySwapMax=0
NoNewPrivileges=yes
ProtectHome=yes
ProtectSystem=strict
ReadWritePaths=/var/lib/strehl-capture /run/strehl-raw
PrivateTmp=yes
TemporaryFileSystem=/tmp:rw,noswap,nodev,nosuid,size=128M /var/tmp:rw,noswap,nodev,nosuid,size=128M

[Install]
WantedBy=multi-user.target''')
    cmdline=(root/'boot/firmware/cmdline.txt').read_text().strip()
    if 'usbcore.usbfs_memory_mb=' not in cmdline:cmdline+=' usbcore.usbfs_memory_mb=150'
    write('/boot/firmware/cmdline.txt',cmdline)
    for service in ('ssh.service','strehl-radio.service','run-strehl\\x2draw.mount','strehl-capture.service'):
        unit_path='/etc/systemd/system/'+service
        if not (root/unit_path.lstrip('/')).is_file():unit_path='/usr/lib/systemd/system/'+service
        assert (root/unit_path.lstrip('/')).is_file()
        link('/etc/systemd/system/multi-user.target.wants/'+service,unit_path)
    subprocess.run(['sync'],check=True)
    print('Provisioned the mounted image: Wi-Fi, key-only SSH, LAN control, unswappable RAM and boot services.')

if __name__=='__main__':main()
