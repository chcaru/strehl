"""Read-only independent RAW decode, Sony group tags, and PC receipt verification."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import rawpy
from deploy import OUT


def main():
    sets=[]
    for label in ['complete-group','three-planes-pause','final-build-group']:
        run=json.loads((OUT/(label+'.json')).read_text())
        sets.append((label,Path(run['final']['storage']['receipt']['path']).parent))
    ui=json.loads((OUT/'ui-verification.json').read_text())['stopped_run']
    folder=Path(ui['folder']) if 'folder' in ui else Path(ui['storage']['receipt']['path']).parent
    sets.append(('browser-stop',folder))
    result=[]
    for label,folder in sets:
        files=sorted(folder.glob('*.ARW'))
        expected=12 if label=='three-planes-pause' else 4
        assert len(files)==expected
        receipts={Path(r['path']).name:r for r in map(json.loads,(folder/'transfer-receipts.jsonl').read_text().splitlines())}
        events=list(map(json.loads,(folder/'events.jsonl').read_text().splitlines()))
        groups=[r for r in events if r['event']=='capture_buffered']
        assert len(groups)==expected//4
        metadata=subprocess.run(['exiftool','-json','-Model','-ImageWidth','-ImageHeight','-Compression',
            '-Sony:PixelShiftInfo','-ExposureTime','-FNumber','-ISO',*[str(p) for p in files]],capture_output=True,text=True)
        assert metadata.returncode==0,metadata.stderr
        tags=json.loads(metadata.stdout);rows=[];group_ids=[]
        for i,(path,tag) in enumerate(zip(files,tags)):
            sha=hashlib.sha256(path.read_bytes()).hexdigest()
            receipt=receipts[path.name]
            assert receipt['durable'] and receipt['sha256']==sha and receipt['bytes']==path.stat().st_size
            assert receipt['encoding']=='strehl-raw-v1'
            assert tag['Model']=='ILCE-7CR' and tag['Compression']=='Uncompressed'
            match=re.search(r'Group (\d+), Shot (\d+)/4',tag['PixelShiftInfo'])
            assert match and int(match[2])==i%4+1
            if i%4==0:group_ids.append(match[1])
            else:assert match[1]==group_ids[-1]
            binding=groups[i//4]['data']['response']['files'][i%4]
            assert binding['name']==path.name and binding['sha256']==sha and binding['plane']==i//4+1
            assert binding['member_index']==i%4+1 and binding['members']==4
            with rawpy.imread(str(path)) as raw:
                plane=raw.raw_image_visible.copy()
                cfa=raw.raw_pattern.tolist()
            assert plane.shape==(6376,9564) and str(plane.dtype)=='uint16'
            rows.append({'name':path.name,'bytes':path.stat().st_size,'wire_bytes':receipt['wire_bytes'],
                         'sha256':sha,'visible':[6376,9564],'dtype':'uint16','cfa':cfa,
                         'exif':{k:v for k,v in tag.items() if k!='SourceFile'}})
        assert len(set(group_ids))==len(group_ids)
        original=sum(r['bytes'] for r in rows);wire=sum(r['wire_bytes'] for r in rows)
        result.append({'label':label,'folder':str(folder),'raw_count':len(rows),
            'planes':[{'focus':e['data']['target'],'camera_seconds':e['data']['response']['camera_seconds'],
                       'group_id':e['data']['response']['camera_reply']['group_id'],
                       'member_ready_seconds':[f['seconds'] for f in e['data']['response']['camera_reply']['files']]} for e in groups],
            'bytes':original,'wire_bytes':wire,'saved_percent':100*(1-wire/original),'files':rows})
    (OUT/'raw-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{k:v for k,v in r.items() if k!='files'} for r in result]))


if __name__=='__main__': main()
