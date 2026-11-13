"""Negative controls against the installed authenticated HTTP receiver.

Creates a uniquely named transport-fixture stack, never operates the camera.
Credentials remain in the existing private configuration and are never logged.
"""
import hashlib
import json
from pathlib import Path
import socket
import struct
import time
import imagecodecs
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'outputs/sony-transport-2026-11-12'
CFG = json.loads((Path.home()/'AppData/Local/StrehlCaptureReceiver/receiver.json').read_text())
URL = 'http://127.0.0.1:8789'
AUTH = {'Authorization': 'Bearer '+CFG['key']}


def packet(data, method=0, width=0, decoded=None):
    packed = imagecodecs.zstd_encode(data, level=1)
    n = len(data) if decoded is None else decoded
    return b'STRHRAW1'+struct.pack('<Q', n)+struct.pack('<IIBI', n, len(packed), method, width)+packed


def main():
    run='stack-transport-controls-'+str(int(time.time()*1000))
    result=requests.post(URL+'/api/runs/'+run,headers=AUTH,timeout=8)
    result.raise_for_status();folder=Path(result.json()['folder'])
    path=folder/'frame-000001.ARW'
    data=bytes(range(256))*128
    sha=hashlib.sha256(data).hexdigest()
    good=packet(data)
    headers={**AUTH,'x-strehl-encoding':'strehl-raw-v1','x-strehl-decoded-length':str(len(data)),'x-content-sha256':sha}
    endpoint=URL+'/api/files/'+run+'/frame-000001.ARW'
    cases=[('truncated',good[:-3],{}),('trailing',good+b'x',{}),
           ('bad-checksum',good,{'x-content-sha256':'0'*64}),
           ('unknown-encoding',good,{'x-strehl-encoding':'future'}),
           ('oversized-original',good,{'x-strehl-decoded-length':str(256*1024*1024+1)}),
           ('bad-cfa-dimensions',packet(data,8,1),{}),
           ('bad-version',b'BADVERS1'+good[8:],{}),
           ('expansion-bomb',packet(b'\0'*(1024*1024),decoded=1024),{'x-strehl-decoded-length':'1024'})]
    rows=[]
    for label,body,override in cases:
        r=requests.put(endpoint,headers={**headers,**override},data=body,timeout=10)
        assert r.status_code>=400,(label,r.status_code)
        assert not path.exists() and not list(folder.glob('*.partial'))
        rows.append({'control':label,'status':r.status_code,'no_final_or_partial':True})
    # TCP is closed mid-body, distinct from a complete HTTP body with bad data.
    wire_header=('PUT /api/files/'+run+'/frame-000001.ARW HTTP/1.1\r\nHost: 127.0.0.1:8789\r\n'+
                 ''.join(k+': '+v+'\r\n' for k,v in headers.items())+
                 'Content-Length: '+str(len(good))+'\r\nConnection: close\r\n\r\n').encode()
    with socket.create_connection(('127.0.0.1',8789),timeout=8) as sock:
        sock.sendall(wire_header+good[:len(good)//2])
    time.sleep(.3)
    assert not path.exists() and not list(folder.glob('*.partial'))
    rows.append({'control':'tcp-interruption','no_final_or_partial':True})
    r=requests.put(endpoint,headers=headers,data=good,timeout=10);r.raise_for_status()
    first=r.json();assert first['durable'] and first['encoding']=='strehl-raw-v1'
    assert path.read_bytes()==data and hashlib.sha256(path.read_bytes()).hexdigest()==sha
    r=requests.put(endpoint,headers=headers,data=good,timeout=10);r.raise_for_status()
    assert r.json()['already_saved']
    r=requests.put(endpoint,headers=headers,data=good[:-1],timeout=10);assert r.status_code>=400
    other=b'changed'+data[7:]
    r=requests.put(endpoint,headers={**headers,'x-content-sha256':hashlib.sha256(other).hexdigest()},data=packet(other),timeout=10)
    assert r.status_code>=400 and path.read_bytes()==data
    result={'run':run,'fixture_is_photographic_raw':False,'negative_controls':rows,
            'exact_positive':True,'duplicate_consumed':True,'truncated_duplicate_refused':True,
            'different_overwrite_refused':True,'receipt':first}
    (OUT/'http-controls.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
