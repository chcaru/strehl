"""Metadata-only census of actual saved runtime entries; no runtime payload reads."""
from pathlib import Path
import base64,hashlib,json,os,stat,subprocess,zlib
ROOT=Path(__file__).resolve().parents[3];H=ROOT/'experiments/m193c-output-grid'
SOURCE=Path(__file__);OUT=H/'work/independent-sift-lightglue-runtime-link-census-v2.json'
def ref(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def canonical(v):return (json.dumps(v,sort_keys=True,separators=(',',':'))+'\n').encode()
def ident(s):return [s.st_dev,s.st_ino,s.st_nlink,getattr(s,'st_file_attributes',0),s.st_size,s.st_mtime_ns,stat.S_ISREG(s.st_mode),bool(getattr(s,'st_file_attributes',0)&0x400)]
inputs=[];snapshots=[]
for name in ('runtime-before.json','runtime-after.json'):
 p=H/'sift-lightglue-commission-1/worker'/name;r=ref(p);assert (r['bytes'],r['sha256'])==(870631,'17e19d0b91e66a14268527757a371af4fa9f68d6205b4d5f75e83c79cc6f6ab4');inputs.append(r);snapshots.append(json.loads(p.read_bytes()))
assert snapshots[0]==snapshots[1]
v=snapshots[0];source_rows=[('files',i,r) for i,r in enumerate(v['files'])]+[('empty_runtime_files',i,r) for i,r in enumerate(v['empty_runtime_files'])]
records=[];exceptions=[];multis=[];aliases=[]
for kind,i,r in source_rows:
 p=Path(r['path']);assert p.suffix.lower() not in ('.tif','.tiff','.arw','.dng','.png','.jpg','.jpeg')
 a=p.stat(follow_symlinks=False);data=ident(a);records.append([kind,i,*data]);cap=(2<<30) if kind=='files' else 0
 checks=dict(positive_link_count=a.st_nlink>0,single_link=a.st_nlink==1,regular=data[-2],non_reparse=not data[-1],extent_matches=a.st_size==r['bytes'],within_kind_extent=(0<a.st_size<=cap) if kind=='files' else a.st_size==0)
 if not all(checks.values()):exceptions.append(dict(kind=kind,ordinal=i,path=str(p),properties=data,checks=checks,expected_bytes=r['bytes'],expected_sha256=r['sha256']))
 if a.st_nlink>1:
  multis.append(len(records)-1)
  observed=subprocess.run(['fsutil','hardlink','list',str(p)],capture_output=True,text=True,timeout=5)
  assert len(observed.stdout)+len(observed.stderr)<=8192
  names=[x.strip() for x in observed.stdout.splitlines() if x.strip()]
  aliases.append(dict(kind=kind,ordinal=i,path=str(p),exit_code=observed.returncode,link_names=names,error=observed.stderr.strip(),contains_component_store_alias=any('\\winsxs\\' in x.lower() for x in names)))
 assert ident(p.stat(follow_symlinks=False))==data
raw=canonical(records);encoded=base64.b64encode(zlib.compress(raw,9)).decode();assert len(raw)<=1024*1024
value=dict(schema='m193c-saved-runtime-link-metadata-census-v1',status='COMPLETE_METADATA_CENSUS_ONLY',source=ref(SOURCE),inputs=inputs,snapshots_byte_identical=True,nonempty_entries=len(v['files']),empty_entries=len(v['empty_runtime_files']),record_count=len(records),record_layout=['saved_collection','ordinal','device','file_id','link_count','attributes','bytes','mtime_ns','regular','reparse'],records_encoding='zlib compressed UTF8 JSON, base64; reference path/hash come from exact input collection+ordinal',records_uncompressed_bytes=len(raw),records_sha256=hashlib.sha256(raw).hexdigest(),records_zlib_base64=encoded,exceptions=exceptions,hardlink_alias_observations=aliases,summary=dict(single_link_rejections=sum(not x['checks']['single_link'] for x in exceptions),other_property_rejections=sum(not all(v for k,v in x['checks'].items() if k!='single_link') for x in exceptions),multilink_entries=len(multis),alias_queries=len(aliases),successful_alias_queries=sum(x['exit_code']==0 for x in aliases),component_store_aliases=sum(x['contains_component_store_alias'] for x in aliases)),scope='Every saved nonempty/empty runtime entry statted without following a final symlink; complete compact identity/link/extent census retained. fsutil hardlink list is metadata only. No runtime DLL/source/checkpoint/image payload read, model, numerical audit or registrar call. Saved SHA values are reference authority, not independently rehashed by this census.')
full=canonical(value);container=dict(schema='m193c-saved-runtime-link-metadata-census-v2',status=value['status'],source=value['source'],inputs=inputs,summary=value['summary'],record_count=len(records),full_census_encoding='zlib compressed UTF8 JSON, base64; complete version1 metadata record including every identity and alias query',full_census_uncompressed_bytes=len(full),full_census_sha256=hashlib.sha256(full).hexdigest(),full_census_zlib_base64=base64.b64encode(zlib.compress(full,9)).decode(),scope=value['scope']);b=canonical(container);assert len(full)<=1024*1024 and len(b)<=64*1024 and not OUT.exists()
with OUT.open('xb') as stream:assert stream.write(b)==len(b)
print(json.dumps(dict(result=ref(OUT),source=ref(SOURCE),summary=value['summary'],record_count=len(records))))
