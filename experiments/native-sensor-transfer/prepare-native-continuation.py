"""Metadata-only constructor for one native continuation: reuse zero, run one through eight.
Retains the original 150 sources and adds five operational sources without a new
source archive. Original payloads and copied native executables are not read.
The inherited metadata bounds remain 30 CPU/60 wall, 128 MiB read/24 MiB write.
No candidate, decoder, scanner, compiler, control or process helper is invoked.
"""
from pathlib import Path, PureWindowsPath
import argparse, hashlib, io, json, math, os, re, stat, sys, time, zipfile

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
WORK=HERE/'work'
PY=Path(sys.executable).resolve()
START=time.monotonic()
MIB=1<<20
READ=WRITE=0
PUBLISHING=False
def need(value,reason):
    if not value:raise ValueError(reason)

def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def strict(raw):
    def pairs(items):
        out={}
        for k,v in items:
            need(k not in out,'duplicate metadata key');out[k]=v
        return out
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite JSON')))

def check():
    need(time.process_time()+(0 if PUBLISHING else 1)<=30 and
         time.monotonic()-START+(0 if PUBLISHING else 2)<=60,'metadata CPU/wall allocation')
    need(READ<=128*MIB and WRITE+(0 if PUBLISHING else MIB+4096)<=24*MIB,'metadata byte allocation')

def path(value):
    need(type(value) is str and 0<len(value)<=512 and value.isascii() and '\x00' not in value,'bounded ASCII path')
    if value.startswith('\\\\?\\'):
        value=value[4:];need(re.match(r'^[A-Za-z]:[\\/]',value),'local verbatim path')
    w=PureWindowsPath(value)
    need((w.is_absolute() and re.match(r'^[A-Za-z]:[\\/]',value)) or (not w.drive and not w.root and ':' not in value),
         'local absolute or plain relative path')
    need(not value.startswith(('\\\\','//')) and all(v not in ('.','..') for v in value.replace('\\','/').split('/')),
         'local path without dot traversal')
    need(not any(':' in part for part in w.parts[1:] if part not in ('\\','/')),'path alternate stream')
    p=Path(os.path.abspath(value if w.is_absolute() else ROOT/value))
    need(p.is_relative_to(ROOT) or p==PY,'metadata repository/current-Python scope')
    return p

def source_path(key):
    need(type(key) is str and not PureWindowsPath(key).is_absolute() and '\\' not in key,'relative source spelling')
    p=path(key);need(p.is_relative_to(ROOT) and p.suffix in ('.rs','.py','.toml','.lock','.txt','.md','.json'),'source-only member')
    return p

def pin(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def pin_shape(value,empty=False,cap=4*MIB):
    need(type(value) is dict and set(value)=={'bytes','sha256'} and type(value['bytes']) is int and
         (0 if empty else 1)<=value['bytes']<=cap and type(value['sha256']) is str and
         re.fullmatch('[0-9a-f]{64}',value['sha256']) is not None,'bounded typed pin')

def ref(p,raw):
    p=path(str(p));return {'path':p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p),**pin(raw)}

def same(left,right,empty=False):
    for v in (left,right):
        need(type(v) is dict and set(v)=={'path','bytes','sha256'},'closed FileRef')
        pin_shape({k:v[k] for k in ('bytes','sha256')},empty,128*MIB)
    need(path(left['path'])==path(right['path']) and left['bytes']==right['bytes'] and left['sha256']==right['sha256'],
         'same actual role/path/bytes/hash')

def read(p,cap=4*MIB,empty=False):
    global READ
    check();p=path(str(p))
    for q in (p,*p.parents):
        s=q.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400,'plain metadata ancestry')
    before=p.stat();need(stat.S_ISREG(before.st_mode) and (0 if empty else 1)<=before.st_size<=cap,'metadata extent/type')
    need(READ+before.st_size+1<=128*MIB,'prospective metadata read');READ+=before.st_size+1
    shared=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink,getattr(s,'st_file_attributes',0))
    full=lambda s:shared(s)+(s.st_ctime_ns,)
    with p.open('rb') as f:
        opened=os.fstat(f.fileno());raw=f.read(before.st_size+1);after=os.fstat(f.fileno())
    final=p.stat()
    need(full(before)==full(final) and full(opened)==full(after) and shared(before)==shared(opened)
         and shared(final)==shared(after) and len(raw)==before.st_size,'stable path and handle source bytes')
    check();return raw

def bound_read(value,cap=4*MIB,empty=False):
    need(type(value) is dict and set(value)=={'path','bytes','sha256'},'closed read FileRef')
    pin_shape({k:value[k] for k in ('bytes','sha256')},empty,cap)
    raw=read(value['path'],cap,empty);same(ref(value['path'],raw),value,empty);return raw

def publish_raw(p,raw,cap=MIB):
    global WRITE
    check();p=path(str(p));need(type(raw) is bytes and len(raw)<=cap and not p.exists(),'bounded fresh metadata publication')
    need(WRITE+len(raw)<=24*MIB,'prospective metadata write');WRITE+=len(raw)
    with p.open('xb') as f:
        need(f.write(raw)==len(raw),'full metadata write');f.flush();os.fsync(f.fileno())
    need(read(p,cap)==raw,'actual metadata readback');return ref(p,raw)

def publish(p,value):return publish_raw(p,encoded(value))

def map_shape(value):
    need(type(value) is dict and 1<=len(value)<=512,'bounded source map')
    paths=set()
    for k,v in value.items():
        p=source_path(k);need(p not in paths,'unique source path');paths.add(p);pin_shape(v)
    need(sum(v['bytes'] for v in value.values())<=16*MIB,'source byte aggregate')


EXTRAS=("run-native-continuation.py","native-publication-scan.py","publication-race-controls.py",
        "capture-native-continuation.py","prepare-native-continuation.py")
def main():
    need(os.name=="nt" and Path.cwd().resolve()==ROOT,"fixed Windows repository")
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,"isolated metadata constructor")
    runner_raw=read(HERE/"run-native-continuation.py",64<<10)
    import ast
    nodes=ast.parse(runner_raw).body
    history=[ast.literal_eval(n.value) for n in nodes if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="HISTORY" for t in n.targets)]
    need(len(history)==1,"literal held history");history=history[0]
    failed_raw=bound_read(history["failed_result"],256<<10);failed=strict(failed_raw)
    old_raw=bound_read(failed["release"],MIB);old=strict(old_raw)
    freeze_raw=bound_read(history["freeze"],MIB);frozen=strict(freeze_raw);original=frozen["source_bindings"]
    need(len(original)==150 and old["source_bindings"]==original and failed["status"]=="REFUSED","exact original 150 and negative parent")
    current=dict(original)
    for name in EXTRAS:
        q=HERE/name;raw=read(q,128<<10);key=q.relative_to(ROOT).as_posix()
        need(key not in current,"additive source only");current[key]=pin(raw)
    map_shape(current)
    for key,value in current.items():need(pin(read(source_path(key)))==value,"unchanged exact source")
    release_path=WORK/"native-continuation-release-3.json"
    freeze_path=WORK/"native-continuation-source-freeze-3.json"
    receipt_path=WORK/"native-continuation-preparation-3.json"
    need(all(not q.exists() for q in (release_path,freeze_path,receipt_path,HERE/"native-3")),"fresh continuation metadata/output")
    need((HERE/"native-run-0").is_dir() and all(not (HERE/f"native-run-{i}").exists() for i in range(1,9)),"saved zero and fresh remainder")
    moved_raw=bound_read(history["archive"],64<<10);moved=strict(moved_raw)
    need(moved["content_hashes_preserved"] is True and moved["partial_population_excluded"] is True
         and moved["files"]==130 and moved["bytes"]==48620310
         and path(moved["from"])==HERE/"native-run-1" and path(moved["to"])==HERE/"native-attempt-1-partial","held exact relocation")
    need(old["schema"]=="native-sensor-transfer-stage-release-v1" and old["stage"]=="native"
         and len(old["children"])==9 and set(old["prerequisites"])=={"build-on","build-off","controls"},"held fixed parent release")
    for bundle in old["prerequisites"].values():
        for role,reference in bundle.items():bound_read(reference,256<<10,empty=role=="stderr")
    for role in ("result","tail","outer","stdout","stderr","exit"):bound_read(history["failed_"+role],256<<10,empty=role=="stderr")
    for key in ("child0","child1","traversal0"):bound_read(history[key],64<<10)
    need(any(path(v["path"])==PY and pin(read(PY,64*MIB))=={k:v[k] for k in ("bytes","sha256")} for v in old["inputs"]),"same metadata Python input")
    source_freeze=publish(freeze_path,dict(schema="native-sensor-transfer-continuation-source-freeze-v1",
                  original_source_freeze=history["freeze"],source_bindings=current))
    recovery=dict(failed_native={k:history["failed_"+k] for k in ("result","tail","outer","stdout","stderr","exit")},
                  relocation=history["archive"],reused0=dict(child=history["child0"],result=history["traversal0"]))
    value=dict(schema="native-sensor-transfer-continuation-release-v1",stage="native",source_bindings=current,
        inputs=old["inputs"],originals=old["originals"],binaries=old["binaries"],reader_release=None,
        prerequisites=old["prerequisites"],children=old["children"][1:],recovery=recovery,
        command=[str(PY),"-I","-S","-B",str(HERE/"run-native-continuation.py"),"--release",str(release_path),
                 "--release-sha256","ACTUAL_RELEASE_SHA256"])
    released=publish(release_path,value)
    for key,expected in current.items():need(pin(read(source_path(key)))==expected,"final unchanged source")
    check()
    receipt=publish(receipt_path,dict(schema="native-sensor-transfer-continuation-preparation-v1",
        release=released,source_freeze=source_freeze,reused_invocations=[0],new_invocations=list(range(1,9)),
        cpu_sample=time.process_time(),wall_sample=time.monotonic()-START,read_bytes_sample=READ,write_bytes_sample=WRITE,
        scope="Metadata/source only; no payload/decoder/numerical/compiler/process helper. Original full native failure costs remain separately charged. Current native retained family includes archive and both parents."))
    raw=encoded(dict(release=released,preparation=receipt,source_freeze=source_freeze))
    need(len(raw)<=8192 and sys.stdout.buffer.write(raw)==len(raw),"full bounded metadata stdout");sys.stdout.buffer.flush()
if __name__=="__main__":main()
