"""Saved-output reporting repair only; frozen v2 science runs unchanged after root release."""
import time
START=time.perf_counter()
import argparse,ast,copy,hashlib,json,sys,traceback,types
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'experiments/m193c-output-grid/work'
SELF=Path(__file__).resolve();LEDGER=WORK/'independent-real-accounting-repair-v3-audit-ledger.json'
FROZEN=WORK/'independent-real-accounting-repair-v2-audit.py'
FROZEN_PIN=(81800,'a97d00094ec0c1442354e0401f7894e9d6ca52bca7c21324642568a696e52dc0')
FROZEN_LEDGER_PIN=(3797,'e7b3447cb4ad70f1ef42d393b738e26f7a2cdc2fbfa66cb567cf95fbcadba555')
KIB=1024
RESERVES=dict(source=24*KIB,ledger=4*KIB,source_review=8*KIB,final=128*KIB,progress=32*KIB,staging=32*KIB,stderr=8*KIB,outer=4*KIB,report=8*KIB)
FAILED_CHARGE=dict(cpu_seconds=25,wall_seconds=40)
FAILED_PINS={
'independent-real-accounting-repair-v2-audit.py':FROZEN_PIN,
'independent-real-accounting-repair-v2-outcome-read.md':(8008,'b5f764b379d1855da4fd61340a81aa427f0f7cc2824b85e058be0e0542a414cf'),
'independent-real-accounting-repair-v2-audit-ledger.json':FROZEN_LEDGER_PIN,
'independent-real-accounting-repair-v2-auditor-source-review.md':(6097,'0e1eaa7e622e4143199021d7baf9d1cc478adb78b04b4fe205775a6c04db6473'),
'independent-real-accounting-repair-v2-audit.json':(0,'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
'independent-real-accounting-repair-v2-audit-stderr.txt':(1569,'8044ee4dc477212c60265634e09f33d8dcb9255657b6609b496533e961b58697'),
'independent-real-accounting-repair-v2-audit-progress.json':(18754,'3f26ded0ba6cc780e01a48c70df32a93d4659a2dded8caea7ad813aed936b6df'),
'independent-real-accounting-repair-v2-audit-outer.json':(1155,'140cf71a59cbcb5b29d4578f38ad1f417b2d6cafa556db7fd6dcf74352e4f456')}
H=None;OWN=None;LEDGER_REF=None;INVOCATION=None

def need(ok,message):
    if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def compact(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def load_frozen():
    # Source hashes are checked before any definition executes; its main is never automatic.
    raw=FROZEN.read_bytes();need((len(raw),sha(raw))==FROZEN_PIN,'immutable exact v2 auditor')
    h=types.ModuleType('m193c_frozen_v2_output_audit');h.__file__=str(FROZEN);sys.modules[h.__name__]=h
    exec(compile(raw,str(FROZEN),'exec'),h.__dict__)
    h.source_bytes(FROZEN,FROZEN_PIN)
    return h,raw

def patched_main(h,raw):
    original=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='main')
    before=ast.dump(original,include_attributes=False)
    target=ast.parse("dict(account['subject_final_work'])",mode='eval').body
    replacement=ast.parse("carry_with_prior_failed_audit(account['subject_final_work'])",mode='eval').body
    class One(ast.NodeTransformer):
        def __init__(self,reverse=False):self.count=0;self.reverse=reverse
        def visit_Call(self,node):
            a,b=(replacement,target) if self.reverse else (target,replacement)
            if ast.dump(node,include_attributes=False)==ast.dump(a,include_attributes=False):
                self.count+=1;return ast.copy_location(copy.deepcopy(b),node)
            return self.generic_visit(node)
    forward=One();candidate=forward.visit(copy.deepcopy(original));reverse=One(True);restored=reverse.visit(copy.deepcopy(candidate))
    need(forward.count==reverse.count==1 and ast.dump(restored,include_attributes=False)==before,'exact one carry-call replacement; reverse AST equality preserves all other main checks')
    module=ast.fix_missing_locations(ast.Module(body=[candidate],type_ignores=[]))
    exec(compile(module,str(FROZEN),'exec'),h.__dict__)
    return dict(original_main_ast_sha256=sha(before.encode()),adapted_main_ast_sha256=sha(ast.dump(candidate,include_attributes=False).encode()),replacements=1,reverse_equal=True)

def carry_with_prior_failed_audit(value):
    result=dict(value)
    for key,amount in FAILED_CHARGE.items():result[key]=float(Decimal(str(result[key]))+Decimal(amount))
    return result

def phase_runtime(row):
    if row is None:return None
    # The original verified object and full final summary stay unchanged.
    return dict(record=row['record'],files=row['files'],python_modules=row['python_modules'],native_modules=row['native_modules'],complete_verified_summary_sha256=sha(H.canonical(row)),summary_scope='Exact source record and full verified summary hash retained; full summary appears only in a completed final report.')

def install(h,doc,args,projected,proof):
    original_copy=h.output_copy;original_remember=h.remember;original_family=h.audit_family
    h.START=START;h.PROGRESS=WORK/'independent-real-accounting-repair-v3-audit-progress.json'
    h.carry_with_prior_failed_audit=carry_with_prior_failed_audit
    cap,fields=h.FINAL_SECTIONS['authority'];h.FINAL_SECTIONS['authority']=(cap,fields+' reused_frozen_v2_source prior_failed_audit')
    def family(g,own,ledger_ref,old_doc):
        original_family(g,own,ledger_ref,old_doc)
        global OWN,LEDGER_REF
        OWN=g.file(SELF);LEDGER_REF=g.file(LEDGER)
        need(OWN['sha256']==args.source_sha256 and OWN['bytes']<=RESERVES['source'] and LEDGER_REF['sha256']==args.ledger_sha256 and LEDGER_REF['bytes']<=RESERVES['ledger'],'released v3 source and finite ledger')
        need(doc['schema']=='m193c-real-accounting-repair-v3-audit-family-v1' and doc['limit_bytes']==384*KIB and doc['new_reservations']==RESERVES and doc['failed_audit_charge']==FAILED_CHARGE and doc['own_audit_caps_including_tail']==h.AUDIT_CAPS and doc['own_publication_allowance']==h.TAIL,'closed v3 accounting and output reservation')
        need(set(doc['held_failed_attempt'])==set(FAILED_PINS),'complete prior failed evidence/report family')
        for name,pin in FAILED_PINS.items():
            r=g.file(WORK/name);need((r['bytes'],r['sha256'])==pin and doc['held_failed_attempt'][name]=={k:r[k] for k in ('bytes','sha256')},'all frozen failed source/output/diagnostic extents and bytes')
        total=sum(x[0] for x in FAILED_PINS.values())+sum(RESERVES.values())
        need(doc['maximum_family_bytes']==total<=384*KIB,'entire historical/new evidence family in existing nonrefundable reservation')
        failed=g.read(g.file(WORK/'independent-real-accounting-repair-v2-audit-outer.json'))
        need(failed['command']==projected and failed['exit_code']==1 and failed['stdout_bytes']==0 and failed['stderr_bytes']==1569 and 0<failed['elapsed_wall_seconds']<=40,'exact failed once-only audit command, output gap and elapsed wall')
        progress=g.read(g.file(WORK/'independent-real-accounting-repair-v2-audit-progress.json'));err=g.read(g.file(WORK/'independent-real-accounting-repair-v2-audit-stderr.txt'))
        need(progress['status']=='AUDIT_INCOMPLETE' and progress['subject_complete'] is progress['admission_allowed'] is False and progress['active_phase']=='audit-refused','old failed partial remains incomplete')
        need([r['phase'] for r in progress['visited']]==['initialization','authority-operational-controls','worker-publication-controls','saved-export-codec','actual-normalized-components','actual-science-prefix'],'old exact visited prefix, no later audit phase invented')
        last=progress['visited'][-1]['summary'];need(last['real_pairs']==23 and last['predictions']==26 and last['fits']==28 and last['unvisited']==last['trailing_saved_values']==[],'retained prior complete scientific prefix only')
        need(err['partial_publication_error'] is None and "remember('worker-scientific-outcome'" in err['error']['traceback_suffix'] and err['error']['traceback_suffix'].endswith('ValueError: declared compact phase extent\n'),'actual output-size refusal')
        need(doc['phase_shape_policy']=='REF_COUNT_HASH_ONLY_FOR_RUNTIME_IN_TWO_FRESH_PHASE_COPIES' and doc['final_section_caps_bytes']=={k:v[0] for k,v in h.FINAL_SECTIONS.items()},'only declared phase reporting seam; unchanged final section bars')
        return dict(ledger=LEDGER_REF,limit_bytes=384*KIB,reservations=RESERVES,audit_caps_including_publication=h.AUDIT_CAPS,maximum_family_bytes=total)
    def remember(phase,summary=None,error=None):
        selected=summary
        if error is None and phase in ('worker-scientific-outcome','runtime-and-current-Job'):
            selected=dict(summary)
            if phase=='worker-scientific-outcome':selected['runtime']=[phase_runtime(r) for r in summary['runtime']]
            else:
                selected['parent_runtime']=phase_runtime(summary['parent_runtime'])
                selected['worker_runtime']=None if summary['worker_runtime'] is None else [phase_runtime(r) for r in summary['worker_runtime']]
            before=sha(h.canonical(summary));original_remember(phase,selected,error);need(sha(h.canonical(summary))==before,'phase copy leaves original verified summary unchanged');return
        original_remember(phase,selected,error)
    def output_copy(value):
        result=original_copy(value)
        if type(value) is dict and value.get('schema')=='m193c-real-accounting-repair-v2-audit-progress-v1':result['schema']='m193c-real-accounting-repair-v3-audit-progress-v1'
        if type(value) is dict and value.get('schema')=='m193c-saved-real-accounting-repair-v2-audit-v1':
            result['schema']='m193c-saved-real-accounting-repair-v3-audit-v1';result['status']='PASS_SAVED_REAL_ACCOUNTING_REPAIR_V3_OUTCOME_AUDIT'
            result['audit_source']=original_copy(OWN);result['reused_frozen_v2_source']=original_copy(value['audit_source'])
            result['prior_failed_audit']=dict(family_ledger=original_copy(LEDGER_REF),charge=FAILED_CHARGE,charge_scope='Full prior25CPU/40wall reservation retained; no final sampled CPU existed. File/evidence family remains inside already charged384KiB preparation.',failure='OUTPUT_PHASE_CAPACITY; scientific prefix retained, later audit unvisited',main_ast=proof,actual_v3_argv_sha256=sha(compact(INVOCATION)))
        return result
    h.audit_family=family;h.remember=remember;h.output_copy=output_copy

def main():
    global H,INVOCATION
    parser=argparse.ArgumentParser()
    for key in ('source','ledger','plan','result','outer','console','exit'):parser.add_argument('--'+key+'-sha256',required=True)
    parser.add_argument('--worker-result-sha256',required=True);args=parser.parse_args();INVOCATION=[sys.executable,'-B',*sys.argv]
    h,raw=load_frozen();H=h
    own=h.source_bytes(SELF);ledger=h.source_bytes(LEDGER)
    need(sha(own)==args.source_sha256 and len(own)<=RESERVES['source'] and sha(ledger)==args.ledger_sha256 and len(ledger)<=RESERVES['ledger'],'actual released new adapter/ledger')
    doc=h.json.loads(ledger);proof=patched_main(h,raw)
    projected=[str(h.PYTHON),'-B',str(FROZEN),'--source-sha256',FROZEN_PIN[1],'--ledger-sha256',FROZEN_LEDGER_PIN[1]]
    for key in ('plan','result','outer','console','exit','worker-result'):projected+=['--'+key+'-sha256',getattr(args,key.replace('-','_')+'_sha256')]
    install(h,doc,args,projected,proof)
    saved=sys.argv;sys.argv=projected[2:]
    try:h.main()
    finally:sys.argv=saved

if __name__=='__main__':
    try:main()
    except BaseException:
        raw=traceback.format_exc().encode();error=dict(status='INCOMPLETE_NO_ADMISSION',full_utf8_bytes=len(raw),full_utf8_sha256=sha(raw),traceback_suffix=raw[-3000:].decode('utf-8','replace'))
        while len(compact(error))>4096:error['traceback_suffix']=error['traceback_suffix'][len(error['traceback_suffix'])//2:]
        publication_error=None
        try:
            if H is not None and H.PROGRESS_OWNED:H.remember('audit-refused',error=error)
        except BaseException as exc:publication_error=dict(type=type(exc).__name__,message=repr(exc)[-512:])
        data=compact(dict(error=error,partial_publication_error=publication_error));need(len(data)<=RESERVES['stderr'],'bounded actual v3 failure publication')
        sys.stderr.write(data.decode());sys.stderr.flush();raise SystemExit(1)
