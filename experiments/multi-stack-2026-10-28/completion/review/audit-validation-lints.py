import argparse,collections,difflib,hashlib,json,pathlib,subprocess
parser=argparse.ArgumentParser()
parser.add_argument('--suffix', default='01')
parser.add_argument('--packages', nargs='+', choices=['core','cli','ui'], default=['core','cli'])
parser.add_argument('--out', type=pathlib.Path)
parser.add_argument('--log', type=pathlib.Path, help='Explicit single-package command log')
args=parser.parse_args()
assert args.log is None or len(args.packages)==1
suffix=args.suffix
assert suffix.isdigit()
ROOT=pathlib.Path(__file__).resolve().parents[4]
BASES=['ef655050','c149e52834fc1c86c2af0fe022713c39fa25f33c']
cache={}
def norm(path):
 p=pathlib.Path(path)
 return (p if p.is_absolute() else ROOT/p).resolve().relative_to(ROOT).as_posix()
def source(path,base):
 key=(path,base)
 if key not in cache:
  r=subprocess.run(['git','-C',str(ROOT),'--work-tree='+str(ROOT),'show',base+':'+path],capture_output=True,encoding='utf-8')
  old=r.stdout.splitlines() if r.returncode==0 else None
  raw=(ROOT/path).read_bytes();cur=raw.decode('utf-8-sig').splitlines()
  blocks=[] if old is None else ([(0,0,len(cur))] if old==cur else difflib.SequenceMatcher(None,old,cur,autojunk=False).get_matching_blocks())
  cache[key]=(old,cur,blocks,hashlib.sha256(raw).hexdigest())
 return cache[key]
reports=[]
for name in [f'{package}-strict-clippy-{suffix}' for package in args.packages]:
 log=args.log or ROOT/'outputs/multi-stack/completion'/name/'command.log';raw=log.read_bytes();records=[]
 for line in raw.decode('utf-8-sig').splitlines():
  try:r=json.loads(line)
  except ValueError:continue
  records.append(r)
 found={};count=0
 for r in records:
  if r.get('reason')!='compiler-message' or r['message']['level'] not in ('warning','error'):continue
  count+=1;m=r['message'];ss=[s for s in m['spans'] if s['is_primary']]
  key=json.dumps([m.get('code'),m['message'],[(norm(s['file_name']),s['line_start'],s['column_start'],s['line_end'],s['column_end']) for s in ss]])
  if key in found:found[key]['occurrences']+=1;continue
  entry={'code':(m.get('code')or{}).get('code'),'message':m['message'],'level':m['level'],'occurrences':1,'spans':[]}
  for s in ss:
   file=norm(s['file_name']);text=[x['text'] for x in s['text']]
   span={'file':file,'line':s['line_start'],'end':s['line_end'],'column':s['column_start'],'text':text,'evidence':{}}
   for base in BASES:
    old,cur,blocks,sha=source(file,base);locations=[i for i in range(len(cur)-len(text)+1) if cur[i:i+len(text)]==text];mapped=[]
    for location in locations:
     for a,b,n in blocks:
      if b<=location and location+len(text)<=b+n:mapped.append({'current_line':location+1,'baseline_line':a+location-b+1,'unchanged_block_lines':n})
    span['evidence'][base]={'exists':old is not None,'current_sha256':sha,'unchanged_mappings':mapped}
   entry['spans'].append(span)
  entry['classification']='new_or_changed_span'
  for base in reversed(BASES):
   if ss and all(s['evidence'][base]['unchanged_mappings'] for s in entry['spans']):
    entry['classification']='unchanged_remote_main' if base==BASES[1] else 'unchanged_prior_multistack'
    if base==BASES[1]:break
  found[key]=entry
 entries=list(found.values())
 report={'name':name,'log_sha256':hashlib.sha256(raw).hexdigest(),'raw_message_count':count,'unique_diagnostics':len(entries),'counts':dict(collections.Counter(e['classification'] for e in entries)),'build_finished':[r for r in records if r.get('reason')=='build-finished'],'diagnostics':entries}
 reports.append(report);print(name,report['counts'])
 for e in entries:
  if e['classification']=='new_or_changed_span':print(json.dumps({'code':e['code'],'message':e['message'],'spans':[(s['file'],s['line']) for s in e['spans']]}))
(args.out or ROOT/f'experiments/multi-stack-2026-10-28/completion/review/validation-lint-audit-{suffix}.json').write_text(json.dumps({'baselines':BASES,'reports':reports},indent=2)+'\n',encoding='utf-8')
