"""SOURCE-ONLY until root release: exact budget callback comparison, no model."""
import time
WALL_START=time.monotonic()
CPU_START=0.0  # process_time includes interpreter/bootstrap CPU
import argparse, ast, copy, hashlib, json, math, os, stat, sys, types
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/"experiments/m193c-output-grid";WORK=HERE/"work";MIB=1<<20
OLD=HERE/"sift-lightglue-real-run.py";READER=HERE/"native-derivative-run.py"
PINS={OLD:(51374,"038a7d649932553891e16018efe1a5d6b6ad313a8073471c4dc8b6a19ce3a420"),
      READER:(44451,"94fe31fbd80854fac80114e0b16b150d9d70ed8899ced727dd8c052b74d0244a")}
MANIFEST=HERE/"sift-lightglue-commission-1/worker/runtime-before.json"
MANIFEST_PIN=(870631,"17e19d0b91e66a14268527757a371af4fa9f68d6205b4d5f75e83c79cc6f6ab4")
FILE_INDEX=72;FILE_PIN=(28437,"a53b1db774f19c6b1e4320c2bc64058c49e3fba58b20b9c1158e5a8d02069890")
NAMES=("need","closed","integer","number","hash_form","strict","json_bytes","relative","repo_path",
       "plain_file","metadata","file_digest","Budget","Files")
OLD_NAMES=("need","budget_for","MIB","KIB","CAPS","FAMILIES","META")
def need(ok,message):
    if not ok:raise ValueError(message)
def encoded(value):return (json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def bound(path,pin,cap=MIB):
    with Path(path).open("rb") as f:raw=f.read(cap+1)
    need((len(raw),sha(raw))==pin,"held metadata/source identity")
    return raw
def guard():
    need(time.process_time()-CPU_START<=9.5 and time.monotonic()-WALL_START<=19,
         "comparison ordinary CPU/wall reserve")
class Clock:
    def __init__(self):self.cpu=0.;self.wall=0.
    def process_time(self):return self.cpu
    def monotonic(self):return self.wall
def select(raw,names):
    source=ast.parse(raw);nodes=[]
    for name in names:
        selected=[x for x in source.body if
                  isinstance(x,(ast.FunctionDef,ast.ClassDef)) and x.name==name or
                  isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in x.targets)]
        need(len(selected)==1,"closed AST name "+name);nodes+=selected
    return ast.Module(body=nodes,type_ignores=[])
def digest_ast(tree):return sha(ast.dump(tree,include_attributes=False).encode())
def optimized(tree):
    answer=copy.deepcopy(tree)
    factory=next(x for x in answer.body if isinstance(x,ast.FunctionDef) and x.name=="budget_for")
    klass=next(x for x in factory.body if isinstance(x,ast.ClassDef))
    check=next(x for x in klass.body if isinstance(x,ast.FunctionDef) and x.name=="check")
    matches=[]
    for i,node in enumerate(check.body):
        if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and ast.unparse(node.value.func)=="need":
            if len(node.value.args)>1 and isinstance(node.value.args[1],ast.Constant) and node.value.args[1].value=="reserved family cap":
                matches.append((i,node))
    need(len(matches)==1,"one exact family-cap statement")
    index,node=matches[0]
    old=ast.parse('need(all(self.totals()[k]<=value for k,value in FAMILIES.items()),"reserved family cap")').body[0]
    need(ast.dump(node,include_attributes=False)==ast.dump(old,include_attributes=False),"unchanged old nine-total predicate")
    check.body[index:index+1]=ast.parse('totals=self.totals()\nneed(all(totals[k]<=value for k,value in FAMILIES.items()),"reserved family cap")').body
    class Lazy(ast.NodeTransformer):
        def __init__(self):self.changed=0
        def visit_Call(self,node):
            node=self.generic_visit(node)
            if ast.unparse(node.func)=="self.overrides.get" and len(node.args)==2:
                need(ast.unparse(node.args[1])=="self.family("+ast.unparse(node.args[0])+")" and not node.keywords,"only exact fallback call")
                key=node.args[0];self.changed+=1
                return ast.IfExp(test=ast.Compare(left=copy.deepcopy(key),ops=[ast.In()],comparators=[ast.parse("self.overrides",mode="eval").body]),
                       body=ast.Subscript(value=ast.parse("self.overrides",mode="eval").body,slice=copy.deepcopy(key),ctx=ast.Load()),
                       orelse=node.args[1])
            return node
    change=Lazy();answer=change.visit(answer)
    need(change.changed==2,"exactly totals and prewrite metadata fallback sites")
    return ast.fix_missing_locations(answer)
def instantiate(tree,clock,name):
    namespace=dict(Path=Path,PurePosixPath=PurePosixPath,ROOT=ROOT,MIB=MIB,
                   math=math,os=os,stat=stat,sys=sys,hashlib=hashlib,json=json,
                   datetime=datetime,timezone=timezone,time=clock,contextmanager=contextmanager,START=0.,re=__import__("re"))
    exec(compile(ast.fix_missing_locations(copy.deepcopy(tree)),name,"exec"),namespace)
    return types.SimpleNamespace(**namespace)
def observed_budget(factory,n,clock,output,kind):
    prior=dict(cpu_seconds=0.,wall_seconds=0.,file_bytes=0,metadata_bytes=0)
    b=factory(n,output,prior,kind!="joint-parent-child")
    families=list(factory.__globals__["FAMILIES"])
    # Deliberately reserved bookkeeping fixture, not a reconstruction of the lost ledger.
    for i in range(64):
        family=families[i%len(families)]
        p=str(output/family/("entry-"+str(i)+".bin"))
        b.extents[p]=16
        if i%2==0:b.overrides[p]=families[(i+1)%len(families)]
    stats=dict(checks=0,totals=0,family=0,scans=0)
    for name in ("totals","family","scan","check"):
        original=getattr(b,name);counter={"scan":"scans","check":"checks"}.get(name,name)
        def wrapper(*args,_fn=original,_key=counter,**kw):
            stats[_key]+=1;return _fn(*args,**kw)
        setattr(b,name,wrapper)
    if kind=="local-cpu":clock.cpu=101.
    if kind=="global-cpu":clock.cpu=1201.
    if kind=="publication-cpu":clock.cpu=99.
    if kind=="local-wall":clock.wall=181.
    if kind=="global-wall":clock.wall=1801.
    if kind=="publication-wall":clock.wall=178.
    if kind=="worker-soft-wall":clock.wall=148.
    if kind=="family":
        b.extents[str(output/"runtime"/"too-large.bin")]=factory.__globals__["FAMILIES"]["runtime"]+1
    if kind=="joint-parent-child":
        # Earlier parent=1 leaves exactly95 child allowance after4 CPU reserve.
        clock.cpu=1.;limits=b.limits();need(limits["cpu_seconds"]==95.,"actual child allowance")
        clock.cpu=6.;b.child_cpu=95.
        b.joint=dict(parent_before=1,child_allowed=95,child_terminal=95,parent_final=6,combined=101)
    for key in stats:stats[key]=0
    return b,stats
def exercise(factory,n,clock,output,kind,runtime_ref):
    b,stats=observed_budget(factory,n,clock,output,kind)
    value=None;error=None;scans=[]
    try:
        if kind=="hash":
            value=n.Files(b).bind(runtime_ref["path"],MIB,True)
        elif kind=="cadence":
            for t in (0.,.1,.21):
                clock.wall=t;before=stats["scans"];b.check();scans.append(stats["scans"]-before)
        elif kind=="prewrite-family":
            b.reserve(output/"runtime"/"new.bin",factory.__globals__["FAMILIES"]["runtime"]+1,"runtime",False)
        elif kind=="prewrite-metadata":
            b.reserve(output/"metadata"/"controller"/"new.json",factory.__globals__["META"]["controller"]+1,"metadata",False)
        else:b.check()
    except Exception as e:error=dict(type=type(e).__name__,message=str(e))
    counters=dict(stats)
    intrinsic=dict(error=error,value=value,extents=sorted(b.extents.items()),
                   overrides=sorted(b.overrides.items()),work=b.work(),last_scan=b.last_scan,
                   cadence=scans,joint=getattr(b,"joint",None))
    # Infinity occurs only on an early global refusal, before no actual scan? scan runs first.
    need(math.isfinite(intrinsic["last_scan"]),"actual scan timestamp")
    return dict(intrinsic=intrinsic,counters=counters,
                extent_count=len(b.extents),fallback_count=sum(p not in b.overrides for p in b.extents))
def publish(path,value):
    raw=encoded(value);need(len(raw)<=10240,"fixed comparison result capacity")
    raw+=b" "*(10240-len(raw))
    with path.open("wb") as f:
        need(f.write(raw)==len(raw),"complete reserved result");f.flush();os.fsync(f.fileno())
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True,type=Path);args=parser.parse_args()
    output=args.output.resolve()
    need(output.parent==WORK and output.name=="accounting-callback-comparison-1" and not output.exists(),"fresh exact owned probe directory")
    retained=[Path(__file__),WORK/"accounting-callback-preregister.md",
              WORK/"independent-accounting-callback-source-review.md"]
    need(all(p.is_file() for p in retained) and sum(p.stat().st_size for p in retained)+10240+16+1536<=32768,
         "whole source/protocol/review/result/seed/outer family maximum")
    output.mkdir();ledger=output/"ledger";ledger.mkdir()
    (ledger/"actual-observed.bin").write_bytes(b"BOUND_SCAN_SEED\n")
    result=dict(schema="m193c-accounting-callback-comparison-v1",status="REFUSED",cases=[],error=None,
                scientific_calls=0,original_attempt_cpu_cause="UNMEASURED",
                joint_cpu_publication_issue="REPRODUCED_BOOKKEEPING_CASE_ONLY; no production publication repair")
    destination=output/"result.json";publish(destination,result)
    try:
        source={p:bound(p,expected) for p,expected in PINS.items()}
        manifest=json.loads(bound(MANIFEST,MANIFEST_PIN))
        runtime_ref=manifest["files"][FILE_INDEX]
        need(Path(runtime_ref["path"]).name=="contextlib.py" and
             (runtime_ref["bytes"],runtime_ref["sha256"])==FILE_PIN,"fixed manifest-bound ordinary runtime file")
        tree=select(source[OLD],OLD_NAMES);candidate=optimized(tree);ntree=select(source[READER],NAMES)
        result["source_bindings"]=[dict(path=str(p),bytes=len(raw),sha256=sha(raw)) for p,raw in source.items()]
        result["owned_source_bindings"]=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in retained]
        result["runtime_manifest"]=dict(path=str(MANIFEST),bytes=MANIFEST_PIN[0],sha256=MANIFEST_PIN[1])
        result["runtime_file"]=runtime_ref;result["runtime_file_index"]=FILE_INDEX
        result["old_ast"]=digest_ast(tree);result["candidate_ast"]=digest_ast(candidate)
        expected={"hash":None,"cadence":None,"local-cpu":"local cap","global-cpu":"complete real CPU bound",
                  "publication-cpu":"publication CPU reserve","local-wall":"local cap","global-wall":"complete real wall bound",
                  "publication-wall":"publication wall reserve","worker-soft-wall":"worker soft wall",
                  "family":"reserved family cap","prewrite-family":"prewrite family capacity",
                  "prewrite-metadata":"metadata subfamily capacity","joint-parent-child":"local cap"}
        for ordinal,(kind,wanted) in enumerate(expected.items()):
            guard();row=dict(id=kind,passed=False);result["cases"].append(row);pair={}
            order=("old","candidate") if ordinal%2==0 else ("candidate","old")
            for mode in order:
                clock=Clock();n=instantiate(ntree,clock,"held-reader")
                module=instantiate(tree if mode=="old" else candidate,clock,mode+"-budget")
                pair[mode]=exercise(module.budget_for,n,clock,ledger,kind,runtime_ref)
            a,z=pair["old"],pair["candidate"]
            raw_a=encoded(a["intrinsic"]);raw_z=encoded(z["intrinsic"])
            row.update(order=order,whole_intrinsic_equal=raw_a==raw_z,
                       old_sha256=sha(raw_a),candidate_sha256=sha(raw_z),
                       error=a["intrinsic"]["error"],old_counts=a["counters"],candidate_counts=z["counters"])
            need(raw_a==raw_z,"entire bookkeeping outcome differs")
            actual=None if row["error"] is None else row["error"]["message"]
            need(actual==wanted,"fixed meaningful refusal/pass result")
            if kind=="hash":
                need(a["intrinsic"]["value"]==runtime_ref,"full actual Files.bind digest")
                need(a["counters"]["checks"]==z["counters"]["checks"]==1 and
                     a["counters"]["totals"]==9 and z["counters"]["totals"]==1,
                     "actual one-block hash callback nine-to-one totals")
                need(a["extent_count"]==65 and z["fallback_count"]==33 and
                     a["counters"]["family"]==9*65 and z["counters"]["family"]==33,
                     "actual overridden and fallback paths exercised")
            if kind=="cadence":need(a["intrinsic"]["cadence"]==[1,0,1],"unchanged actual scan cadence")
            if kind=="joint-parent-child":row["actual_bookkeeping_case"]=a["intrinsic"]["joint"]
            row["passed"]=True;publish(destination,result)
        guard()
        for p,expected in PINS.items():bound(p,expected)
        for ref in result["owned_source_bindings"]:
            bound(ref["path"],(ref["bytes"],ref["sha256"]))
        result["sources_unchanged"]=True
        result["status"]="PASS_CALLBACK_EQUIVALENCE_AND_POWER_ONLY"
    except BaseException as exc:result["error"]=dict(type=type(exc).__name__,message=str(exc))
    result["actual_controller_work"]=dict(cpu_seconds=time.process_time()-CPU_START,wall_seconds=time.monotonic()-WALL_START)
    publish(destination,result)
    if time.process_time()-CPU_START>10 or time.monotonic()-WALL_START>20:
        result["status"]="REFUSED";result["error"]={"message":"whole comparison cap including publication"}
        publish(destination,result)
    print(json.dumps(dict(status=result["status"],path=str(destination),sha256=sha(destination.read_bytes()))))
    return 0 if result["status"].startswith("PASS_") else 1
if __name__=="__main__":raise SystemExit(main())
