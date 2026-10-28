import collections, difflib, hashlib, json, pathlib, re, subprocess
ROOT=pathlib.Path(r'C:\Users\chris\.codex\worktrees\multi-stack\strehl')
BASE='c149e52834fc1c86c2af0fe022713c39fa25f33c'
REVIEW=ROOT/'experiments/multi-stack-2026-10-28/review'
cache={}
def source(path):
    if path not in cache:
        p=subprocess.run(['git','-C',str(ROOT),'--work-tree='+str(ROOT),'show',BASE+':'+path],capture_output=True,encoding='utf-8')
        baseline=p.stdout.splitlines() if p.returncode==0 else None
        current=(ROOT/path).read_text(encoding='utf-8').splitlines() if (ROOT/path).is_file() else None
        cache[path]=(baseline,current)
    return cache[path]
def locations(lines, text):
    if not lines or not text: return []
    return [i+1 for i in range(len(lines)-len(text)+1) if lines[i:i+len(text)]==text]
def norm(path):
    p=pathlib.Path(path)
    return (p if p.is_absolute() else ROOT/p).resolve().relative_to(ROOT).as_posix()
reports=[]
for name in ['frontends-clippy-3.jsonl']:
    path=ROOT/'outputs/multi-stack/checks'/name
    raw=path.read_bytes()
    records=[json.loads(line) for line in raw.decode('utf-8-sig').splitlines() if line.strip().startswith('{')]
    messages=[r for r in records if r.get('reason')=='compiler-message' and r['message']['level'] in ('warning','error')]
    found={}
    for r in messages:
        m=r['message']; spans=[s for s in m['spans'] if s['is_primary']]
        key=json.dumps([m.get('code'),m['message'],[(norm(s['file_name']),s['line_start'],s['column_start'],s['line_end'],s['column_end'],s['text']) for s in spans]],sort_keys=True)
        if key in found:
            found[key]['occurrences']+=1; continue
        item={'code':(m.get('code') or {}).get('code'),'message':m['message'],'level':m['level'],'occurrences':1,'spans':[]}
        for s in spans:
            file=norm(s['file_name']); base, current=source(file); text=[t['text'] for t in s['text']]
            item['spans'].append({'file':file,'reported_line':s['line_start'],'reported_end':s['line_end'],'column':s['column_start'],'text':text,'baseline_locations':locations(base,text),'current_locations':locations(current,text),'file_exists_in_baseline':base is not None})
        item['classification']='baseline_exact_span' if spans and all(s['baseline_locations'] for s in item['spans']) else 'unmatched_or_new'
        found[key]=item
    entries=list(found.values())
    report={'input':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest(),'baseline':BASE,'compiler_message_records':len(messages),'unique_diagnostics':len(entries),'duplicate_records':len(messages)-len(entries),'build_finished':[r for r in records if r.get('reason')=='build-finished'],'classification_counts':dict(collections.Counter(e['classification'] for e in entries)),'diagnostics':entries}
    reports.append(report)
    print(name, json.dumps({k:v for k,v in report.items() if k!='diagnostics'}))
    for e in entries:
        s=e['spans'][0] if e['spans'] else {}
        if e['classification']=='unmatched_or_new': print(json.dumps({'code':e['code'],'occurrences':e['occurrences'],'classification':e['classification'],'file':s.get('file'),'line':s.get('reported_line'),'baseline':s.get('baseline_locations'),'current':s.get('current_locations'),'message':e['message']}))
(REVIEW/'lint-span-audit-3.json').write_text(json.dumps(reports,indent=2)+'\n',encoding='utf-8')
