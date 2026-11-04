import collections,difflib,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(r'C:\Users\chris\.codex\worktrees\multi-stack\strehl')
REVIEW=ROOT/'experiments/multi-stack-2026-10-28/review'
BASE='c149e52834fc1c86c2af0fe022713c39fa25f33c'
LOG=ROOT/'outputs/multi-stack/checks/engine-fmt-1.log'
raw=LOG.read_bytes(); text=raw.decode('utf-8-sig')
headers=list(re.finditer(r'^Diff in (.+):(\d+):\r?$',text,re.M))
cache={}; results=[]
def get(file):
 if file not in cache:
  run=subprocess.run(['git','-C',str(ROOT),'--work-tree='+str(ROOT),'show',BASE+':'+file],capture_output=True,text=True,encoding="utf-8")
  base=run.stdout.splitlines() if run.returncode==0 else None
  p=ROOT/file; b=p.read_bytes(); cur=b.decode('utf-8-sig').splitlines()
  blocks=[] if base is None else difflib.SequenceMatcher(None,base,cur,autojunk=False).get_matching_blocks()
  cache[file]=(base,cur,blocks,hashlib.sha256(b).hexdigest())
 return cache[file]
def locations(lines,seq):
 return [i for i in range(len(lines)-len(seq)+1) if lines[i:i+len(seq)]==seq]
for n,h in enumerate(headers):
 path=h.group(1).removeprefix('\\\\?\\')
 file=Path(path).resolve().relative_to(ROOT).as_posix()
 base,cur,blocks,sha=get(file)
 body=text[h.end():headers[n+1].start() if n+1<len(headers) else len(text)].splitlines()
 old=[];removed=[];added=[]
 for line in body:
  if line.startswith('+'): added.append(line[1:])
  if line.startswith(' ') or line.startswith('-'):
   if line.startswith('-'): removed.append(len(old))
   old.append(line[1:])
 positions=locations(cur,old)
 baseline_positions=locations(base,old) if base else []
 entry={'file':file,'reported_line':int(h.group(2)),'current_file_sha256':sha,'input_hunk_lines':old,'removed_offsets':removed,'formatted_added_lines':added,'current_locations':[v+1 for v in positions],'baseline_locations':[v+1 for v in baseline_positions]}
 if base==cur:
  entry['classification']='inherited_entire_file'
 elif not positions:
  entry['classification']='requires_review_current_span_not_found'
 else:
  at=min(positions,key=lambda p:abs(p+1-int(h.group(2))))
  new=[];unchanged=[]
  for offset in removed:
   idx=at+offset
   hits=[(a+idx-b+1,n) for a,b,n in blocks if b<=idx<b+n]
   if hits: unchanged.append({'current_line':idx+1,'baseline_line':hits[0][0]})
   else:new.append({'current_line':idx+1,'text':cur[idx]})
  entry['new_removed_lines']=new;entry['unchanged_removed_lines']=unchanged
  if new: entry['classification']='new_or_changed_formatting'
  elif removed: entry['classification']='inherited_removed_lines_map_to_baseline'
  elif baseline_positions: entry['classification']='inherited_insert_only_hunk'
  else: entry['classification']='requires_review_insert_only_hunk'
 results.append(entry)
new_lines={line['text'] for e in results for line in e.get('new_removed_lines',[])}
for e in results:
 if e['classification']=='inherited_insert_only_hunk' and any(line in new_lines for line in e['formatted_added_lines']):
  e['classification']='new_formatting_relocation_destination'
summary={'log_sha256':hashlib.sha256(raw).hexdigest(),'baseline':BASE,'hunks':len(results),'files':len(cache),'classifications':dict(collections.Counter(e['classification'] for e in results))}
(REVIEW/'engine-format-hunk-audit.json').write_text(json.dumps({'summary':summary,'hunks':results},indent=2)+'\n')
print(json.dumps(summary,indent=2))
for e in results:
 if not e['classification'].startswith('inherited'):
  print(json.dumps({k:v for k,v in e.items() if k not in ['input_hunk_lines','unchanged_removed_lines']},indent=2))
