"""Bound each iperf stream to the tested Pi interface and verify its counters."""
import argparse
import json
import subprocess
import time
from remote import ssh, OPTIONS, OUT


def snapshot():
    code = '''import subprocess,json,pathlib
r={'load':pathlib.Path('/proc/loadavg').read_text(),'temperature_mC':int(pathlib.Path('/sys/class/thermal/thermal_zone0/temp').read_text()),'interfaces':{}}
for iface in ['wlan0','wlan1']:
 p=pathlib.Path('/sys/class/net')/iface/'statistics'
 r['interfaces'][iface]={'tx_bytes':int((p/'tx_bytes').read_text()),'rx_bytes':int((p/'rx_bytes').read_text()),'link':subprocess.run(['iw','dev',iface,'link'],capture_output=True,text=True).stdout}
print(json.dumps(r))
'''
    p = ssh(code, root=True)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def main():
    ap = argparse.ArgumentParser();ap.add_argument('--label', required=True)
    ap.add_argument('--interface', choices=['wlan0','wlan1'], required=True)
    ap.add_argument('--address', choices=['10.0.0.187','10.0.0.178'], required=True)
    ap.add_argument('--streams', type=int, choices=[1,4], default=1)
    a = ap.parse_args();assert a.label.replace('-', '').isalnum()
    before = snapshot()
    command = ['wsl','-d','Debian','-u','root','--','iperf3','-c',a.address,
               '-p','5217','-t','12','-O','2','-R','-P',str(a.streams),'-J']
    server_command = 'sudo iperf3 -s -1 -B '+a.address+' --bind-dev '+a.interface+' -p 5217 --idle-timeout 25 -J'
    with (OUT/(a.label+'-server.json')).open('wb') as log:
        server = subprocess.Popen(['ssh',*OPTIONS,'strehl@10.0.0.187',server_command],
                                  stdout=log,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            time.sleep(.6)
            client = subprocess.run(command,capture_output=True,text=True,timeout=35)
            assert client.returncode == 0, client.stderr+client.stdout
            result = json.loads(client.stdout)
            assert 'error' not in result,result.get('error')
            _, error = server.communicate(timeout=10)
            assert server.returncode == 0,error
        finally:
            if server.poll() is None:
                server.terminate();server.wait(timeout=5)
    after = snapshot()
    deltas = {i:after['interfaces'][i]['tx_bytes']-before['interfaces'][i]['tx_bytes'] for i in before['interfaces']}
    end = result['end'];received = end['sum_received']['bytes']
    assert deltas[a.interface] >= .9*received, 'Traffic did not use the intended interface'
    other = 'wlan0' if a.interface=='wlan1' else 'wlan1'
    assert deltas[other] < .1*received, 'Other interface carried significant traffic'
    row={'case':a.label,'interface':a.interface,'command':command,'server_command':server_command,
         'received_Mbps':end['sum_received']['bits_per_second']/1e6,
         'received_MBps':end['sum_received']['bits_per_second']/8e6,
         'retransmits':end['sum_sent'].get('retransmits'),'tx_deltas':deltas,
         'before':before,'after':after,'raw_result':result}
    (OUT/(a.label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps({k:v for k,v in row.items() if k not in ['before','after','raw_result']}),flush=True)


if __name__=='__main__':main()
