import collections,difflib,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(r'C:\Users\chris\.codex\worktrees\multi-stack\strehl')
BASE='c149e52834fc1c86c2af0fe022713c39fa25f33c'; REVIEW=ROOT/'experiments/multi-stack-2026-10-28/review'
reports=json.loads((REVIEW/'lint-span-audit.json').read_text()); cache={}
def get(path):
 if path not in cache:
  p=subprocess.run(['git','-C',str(ROOT),'--work-tree='+str(ROOT),'show',BASE+':'+path],capture_output=True,encoding='utf-8')
  base=p.stdout.splitlines() if p.returncode==0 else None
  raw=(ROOT/path).read_bytes(); cur=raw.decode('utf-8').splitlines()
  cache[path]=(base,cur,hashlib.sha256(raw).hexdigest(), [] if base is None or base==cur else difflib.SequenceMatcher(None,base,cur,autojunk=False).get_matching_blocks())
 return cache[path]
for report in reports:
 for item in report['diagnostics']:
  for span in item['spans']:
   base,cur,sha,blocks=get(span['file']); span['current_file_sha256']=sha
   if base==cur: span['diff_evidence']={'kind':'entire_file_equals_baseline'}
   else:
    evidence=[]
    for location in span['current_locations']:
     for a,b,n in blocks:
      if b<=location-1 and location-1+len(span['text'])<=b+n:
       evidence.append({'current_start':location,'baseline_start':a+(location-1-b)+1,'unchanged_block_lines':n})
    span['diff_evidence']={'kind':'unchanged_diff_block' if evidence else 'changed_or_new_span','mappings':evidence}
  if item['code']=='clippy::large_enum_variant' and item['spans'][0]['file']=='crates/strehl-cli/src/lib.rs':
   base,cur,sha,blocks=get('crates/strehl-cli/src/lib.rs')
   def variant(lines):
    a=lines.index('    Stack {'); b=lines.index('    },',a); return lines[a:b+1]
   old_align=get('crates/strehl-cli/src/align_cmd.rs')[0]; new_align=get('crates/strehl-cli/src/align_cmd.rs')[1]
   assert variant(base)==variant(cur) and '    Align(align_cmd::AlignArgs),' in base and old_align==new_align
   item['classification']='inherited_variant_size_cause'
   item['manual_evidence']='Largest Stack fields exactly equal baseline; second-largest Align variant and entire align_cmd.rs defining AlignArgs equal baseline. Added Session is neither size cause in this diagnostic.'
 report['classification_counts']=dict(collections.Counter(e['classification'] for e in report['diagnostics']))
 report['by_source_group']=dict(collections.Counter('experiment_include' if e['spans'] and e['spans'][0]['file'].startswith('experiments/') else 'crate_source' for e in report['diagnostics']))
 print(pathlib.Path(report['input']).name,report['unique_diagnostics'],report['classification_counts'],report['by_source_group'])
 for e in report['diagnostics']:
  if e['classification']=='baseline_exact_span' and any(s['diff_evidence']['kind']=='changed_or_new_span' for s in e['spans']):print('REVIEW MAPPING',json.dumps(e))
(REVIEW/'lint-span-audit.json').write_text(json.dumps(reports,indent=2)+'\n',encoding='utf-8')
