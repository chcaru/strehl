from pathlib import Path
import json,hashlib,re
root=Path.cwd()
pp=root/'experiments/native-sensor-transfer/source/native-observation.patch'
meta=json.loads((pp.parent/'patch-construction.json').read_bytes())
patch=pp.read_bytes()
assert len(patch)==4907 and hashlib.sha256(patch).hexdigest()==meta['patch_sha256']
lines=patch.decode('utf8').splitlines()
out={};receipts=[];i=0
for item in meta['paths']:
 name=item['path'];assert lines[i]=='--- a/'+name and lines[i+1]=='+++ b/'+name;i+=2
 original=(root/name).read_bytes()
 assert len(original)==item['original_bytes'] and hashlib.sha256(original).hexdigest()==item['original_sha256'],name
 src=original.splitlines(keepends=True);dst=[];cursor=0;inserted=[];hunks=0
 while i<len(lines) and lines[i].startswith('@@'):
  m=re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*',lines[i]);assert m
  begin=int(m[1])-1;old_count=int(m[2] or 1);new_count=int(m[4] or 1)
  assert begin>=cursor
  dst.extend(src[cursor:begin]);cursor=begin;i+=1;old_seen=0;new_seen=0;hunks+=1
  while i<len(lines) and not lines[i].startswith(('@@','--- a/')):
   line=lines[i];i+=1;kind=line[0]
   assert kind in (' ','+'),'only additive reviewed patch'
   text=line[1:].encode('utf8')
   if kind==' ':
    assert src[cursor].rstrip(b'\r\n')==text,(name,cursor)
    dst.append(src[cursor]);cursor+=1;old_seen+=1;new_seen+=1
   else:
    neighbour=src[cursor] if cursor<len(src) else src[-1]
    newline=b'\r\n' if neighbour.endswith(b'\r\n') else b'\n'
    inserted.append(len(dst));dst.append(text+newline);new_seen+=1
  assert (old_seen,new_seen)==(old_count,new_count),(name,old_seen,new_seen,old_count,new_count)
 dst.extend(src[cursor:])
 new=b''.join(dst)
 reverse=b''.join(v for j,v in enumerate(dst) if j not in set(inserted))
 assert reverse==original
 lf=new.replace(b'\r\n',b'\n')
 lf_equal = len(lf)==item['patch_applied_lf_bytes'] and hashlib.sha256(lf).hexdigest()==item['patch_applied_lf_sha256']
 out[name]=new
 receipts.append(dict(path=name,before_bytes=len(original),before_sha256=hashlib.sha256(original).hexdigest(),after_bytes=len(new),after_sha256=hashlib.sha256(new).hexdigest(),hunks=hunks,inserted_lines=len(inserted),deleted_lines=0,reverse_exact_bytes=True,reviewed_lf_patch_equal=lf_equal,actual_lf_bytes=len(lf),actual_lf_sha256=hashlib.sha256(lf).hexdigest(),legacy_candidate_pin_equal=hashlib.sha256(new).hexdigest()==item['candidate_sha256']))
assert i==len(lines)
assert all(r['legacy_candidate_pin_equal'] and r['reverse_exact_bytes'] for r in receipts)
receipt_path=root/'experiments/native-sensor-transfer/source-application-1.json'
assert not receipt_path.exists()
for r in receipts:
 assert hashlib.sha256((root/r['path']).read_bytes()).hexdigest()==r['before_sha256']
for name,data in out.items():
 (root/name).write_bytes(data)
for r in receipts:
 actual=(root/r['path']).read_bytes()
 assert len(actual)==r['after_bytes'] and hashlib.sha256(actual).hexdigest()==r['after_sha256']
value=dict(schema='native-sensor-transfer-source-application-v1',status='APPLIED_REVIEWED_SOURCE_ONLY',
 source_review=dict(path='experiments/native-sensor-transfer/producer-source-review.md',bytes=14105,sha256='31dee2b8a5465c9815d1c73d5f5ccd02a5e305fd02ded337361806d10cd9729d'),
 patch_sha256=hashlib.sha256(patch).hexdigest(),paths=receipts,
 earlier_dry_read=dict(exit_code=1,assertion='crates/strehl-core/src/pyramid.rs',reason='stale alternate normalized-LF construction pins',live_writes=0),
 decision='All five actual candidate byte pins and independent reversal agree; alternate normalized metadata is not used as application authority. Original construction retained at51281d20.',
 numerical_execution=False,raw_payload_reads=0,builds=0)
data=(json.dumps(value,indent=2)+'\n').encode()
receipt_path.write_bytes(data)
assert receipt_path.read_bytes()==data
print(json.dumps(dict(status=value['status'],paths=len(receipts),inserted_lines=sum(r['inserted_lines'] for r in receipts),deleted_lines=0,reverse_exact=True,receipt_bytes=len(data),receipt_sha256=hashlib.sha256(data).hexdigest())))

