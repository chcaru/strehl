"""Version2 independent saved-completion audit: one asserted runtime-conjunct AST repair.
All subject, scientific, publication and accounting code remains frozen. No image,
model, normalization or registrar call. Execute only after exact root release.
"""
import time
WALL_START=time.perf_counter()
import argparse
import ast
import copy
from decimal import Decimal as D
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import traceback
import types
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/m193c-output-grid';WORK=HERE/'work'
SELF=Path(__file__).resolve();V1=WORK/'independent-sift-lightglue-saved-completion-audit.py'
V1_PIN=(59052,'7c93287992515235438912569520513eb7d2573742304a253d00104d96e044fa')
PYTHON=Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
KIB=1024
LEDGER_PATH=WORK/'independent-sift-lightglue-saved-completion-audit-v2-ledger.json'
PROGRESS=WORK/'independent-sift-lightglue-saved-completion-audit-v2-progress.json'
RESERVES=dict(final_json=112*KIB,stderr=16*KIB,outer=8*KIB,progress=32*KIB,staging=32*KIB,source_review=8*KIB,actual_report=8*KIB,ledger=8*KIB)
FAILED={
 'stdout':('independent-sift-lightglue-saved-completion-audit.json',0,'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
 'stderr':('independent-sift-lightglue-saved-completion-audit-stderr.txt',928,'a093a9917408f5f7df125cb310f81941dd1f2ca293cd0c3d15cab2b401d1ce01'),
 'outer':('independent-sift-lightglue-saved-completion-audit-outer.json',975,'5b53307aad22a3251ea4051d3718d12a5e4e5ab89568000838aad968bdc0095f'),
 'partial':('independent-sift-lightglue-saved-completion-audit-progress.json',15806,'99e45a3892926d803e8301105e5040d4994abba8e1541f9192f787b9c821ae34'),
 'report':('independent-sift-lightglue-saved-completion-audit-v1-refusal.md',5668,'d1b8bd677b39bf5e01aa43b7ba68d3919a312dd3a82462c7f97bddb6c686e6be')}
SOURCE_MODULES={
 'm193c_saved_pure_reference':'experiments/M193-cover-overlap/reference.py',
 'm193c_saved_pure_direct_pair_run':'experiments/m193c-output-grid/direct-pair-run.py',
 'm193c_saved_pure_factor_eight_prototype':'experiments/m193c-output-grid/factor-eight-prototype.py',
 'm193c_saved_pure_sift_lightglue_adapter':'experiments/m193c-output-grid/sift-lightglue-adapter.py'}
H=None;TRANSITION=None;GATE_CALLS=0;IMMUTABLE={}

def need(ok,message):
    if not ok:raise ValueError(message)
def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def strict(data):
    def pairs(items):
        out={}
        for k,v in items:need(k not in out,'duplicate metadata field');out[k]=v
        return out
    return json.loads(data,object_pairs_hook=pairs,parse_constant=lambda x:need(False,'nonfinite metadata'))
def identity(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,getattr(s,'st_file_attributes',0),s.st_nlink)
def bound(path,pin=None):
    path=Path(os.path.abspath(path));need(path.is_relative_to(WORK) and path.suffix in ('.py','.md','.json','.txt'),'only owned audit metadata/source')
    before=path.stat(follow_symlinks=False);ident=identity(before)
    need(stat.S_ISREG(before.st_mode) and not getattr(before,'st_file_attributes',0)&0x400 and before.st_nlink==1 and 0<=before.st_size<=256*KIB and path.resolve()==path,'plain bounded owned audit evidence')
    with path.open('rb') as stream:
        need(identity(os.fstat(stream.fileno()))==ident,'opened audit source identity');raw=stream.read(256*KIB+1)
        need(identity(os.fstat(stream.fileno()))==ident,'opened audit source unchanged')
    need(len(raw)==before.st_size and identity(path.stat(follow_symlinks=False))==ident,'same bounded complete audit bytes')
    ref=dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=sha(raw))
    if pin is not None:need((ref['bytes'],ref['sha256'])==pin,'root-held audit evidence pin')
    need(IMMUTABLE.setdefault(str(path),(ref,ident))==(ref,ident),'same repeated audit metadata')
    return ref,raw

def ledger():
    ref,raw=bound(LEDGER_PATH);value=strict(raw)
    need(value['schema']=='m193c-saved-completion-audit-family-v2' and value['limit_bytes']==384*KIB and value['reserved_outputs']==RESERVES,'fixed full audit family')
    held=value['held_files'];need(type(held) is list and len({r['path'] for r in held})==len(held),'unique full held family')
    for r in held:
        actual,_=bound(ROOT/r['path'],(r['bytes'],r['sha256']));need(actual==r,'canonical held reference')
    need(any((ROOT/r['path']).resolve()==SELF for r in held) and any((ROOT/r['path']).resolve()==V1 for r in held),'actual v2 and immutable v1 included')
    need(sum(r['bytes'] for r in held)+sum(RESERVES.values())==value['maximum_total_bytes']<=384*KIB,'entire held plus simultaneous reserved bytes')
    need(ref['bytes']<=RESERVES['ledger'] and value['source_preparation_reservation_bytes']==185051 and value['plan_bytes']==48518 and value['preparation_other_bound_bytes']==32*KIB,'explicit already-charged preparation population')
    need(185051+48518+32*KIB+384*KIB<1024*KIB,'even conservative double count fits existing1MiB prep')
    for r in value['reused_previously_charged_sources']:bound(ROOT/r['path'],(r['bytes'],r['sha256']))
    return ref,value

def key(h,r):
    h.ref_shape(r);return (str(h.path(r).resolve()),r['bytes'],r['sha256'])
def expand(h,snapshot,plan,registry):
    need(set(snapshot)==set('schema prior_registry entries python_modules native_module_indices empty_current_files python_version scope'.split()),'closed current snapshot metadata')
    bindings=[]
    for entry in snapshot['entries']:
        need(type(entry) is dict and len(entry)==1,'single indexed origin')
        if 'local_source' in entry:
            name=entry['local_source'];need(name in plan['source_bindings'],'declared local source');r=dict(path=name,**plan['source_bindings'][name])
        elif 'prior_runtime_index' in entry:
            i=entry['prior_runtime_index'];need(type(i) is int and 0<=i<len(registry['files']),'valid prior index');r=registry['files'][i]
        else:
            need(set(entry)=={'empty_runtime_index'},'closed empty origin');i=entry['empty_runtime_index'];need(type(i) is int and 0<=i<len(registry['empty_runtime_files']),'valid empty index');r={k:registry['empty_runtime_files'][i][k] for k in ('path','bytes','sha256')}
        bindings.append(key(h,r))
    need(len(bindings)==len(set(bindings)),'unique resolved runtime bindings')
    modules={};indices=set()
    for row in snapshot['python_modules']:
        need(type(row) is list and len(row)==2 and type(row[0]) is str and row[0] not in modules and type(row[1]) is int and 0<=row[1]<len(bindings),'closed module index row')
        modules[row[0]]=bindings[row[1]];indices.add(row[1])
    native_indices=snapshot['native_module_indices'];need(type(native_indices) is list and all(type(i) is int and 0<=i<len(bindings) for i in native_indices) and len(native_indices)==len(set(native_indices)),'closed native index list')
    need(indices|set(native_indices)==set(range(len(bindings))),'every entry used by exact module/native union')
    return dict(bindings=set(bindings),ordered=bindings,modules=modules,native={bindings[i] for i in native_indices},other={k:v for k,v in snapshot.items() if k not in ('entries','python_modules','native_module_indices')})

def transition(h,before,after,plan,registry):
    a,z=expand(h,before,plan,registry),expand(h,after,plan,registry)
    expected={name:key(h,dict(path=path,**plan['source_bindings'][path])) for name,path in SOURCE_MODULES.items()}
    future=(PYTHON.parent/'Lib/__future__.py').resolve();refs=[r for r in registry['files'] if h.path(r).resolve()==future]
    need(len(refs)==1,'one exact previously admitted future module');expected['__future__']=key(h,refs[0])
    need(not set(expected)&set(a['modules']),'expected source additions were absent before science')
    need(z['modules']==a['modules']|expected,'exact five additions with unchanged prior module identities')
    need(z['bindings']==a['bindings']|set(expected.values()) and len(z['bindings'])==len(a['bindings'])+5,'exact five added file bindings, no removals or aliases')
    need(a['native']==z['native'],'unchanged resolved native file set')
    need(a['other']==z['other'],'all other snapshot fields unchanged')
    return dict(added_modules={name:dict(path=value[0],bytes=value[1],sha256=value[2]) for name,value in sorted(expected.items())},before_file_count=len(a['bindings']),after_file_count=len(z['bindings']),before_module_count=len(a['modules']),after_module_count=len(z['modules']),native_file_count=len(a['native']),existing_module_bindings_unchanged=True,other_fields_unchanged=True,raw_snapshots_equal=before==after)

def gate(worker,plan):
    global GATE_CALLS,TRANSITION
    GATE_CALLS+=1;need(GATE_CALLS==1,'one replaced runtime conjunct invocation')
    h=H;before=h.read(worker['runtime_before']);after=h.read(worker['runtime_after']);registry=h.read(before['prior_registry'])
    before_hash=sha(canonical(before));after_hash=sha(canonical(after));summary=transition(h,before,after,plan,registry)
    # The original runtime_record verification already authenticated both snapshots and every actual file.
    shuffled=copy.deepcopy(after);n=len(shuffled['entries']);need(n>1,'index-table positive has more than one actual row')
    shuffled['entries'].reverse();shuffled['python_modules']=[[name,n-1-i] for name,i in shuffled['python_modules']];shuffled['native_module_indices']=[n-1-i for i in shuffled['native_module_indices']]
    need(shuffled!=after and transition(h,before,shuffled,plan,registry)==summary,'actual shuffled-table positive preserves all resolved identities')
    mutants=[]
    target=next(row[1] for row in after['python_modules'] if row[0]=='m193c_saved_pure_reference')
    bad=copy.deepcopy(after);existing=next(row for row in bad['python_modules'] if row[0] in {r[0] for r in before['python_modules']});existing[1]=target;mutants.append(('wrong-existing-binding',bad))
    bad=copy.deepcopy(after);bad['python_modules']=[row for row in bad['python_modules'] if row[0]!='m193c_saved_pure_reference'];mutants.append(('missing-expected-module',bad))
    bad=copy.deepcopy(after);bad['python_modules'].append(['m193c_unexpected_module',target]);mutants.append(('unexpected-extra-module',bad))
    bad=copy.deepcopy(after);need(target not in bad['native_module_indices'],'native-membership fault changes actual set');bad['native_module_indices'].append(target);mutants.append(('changed-native-binding-set',bad))
    controls=[]
    for name,mutant in mutants:
        error=None
        try:transition(h,before,mutant,plan,registry)
        except ValueError as exc:error=str(exc)
        need(error is not None,'actual runtime-policy destroyer rejected: '+name)
        controls.append(dict(id=name,rejected=True,error=error,mutant_canonical_sha256=sha(canonical(mutant))))
    need(sha(canonical(before))==before_hash and sha(canonical(after))==after_hash,'actual input snapshot metadata unchanged after controls')
    need(transition(h,before,after,plan,registry)==summary,'restored original runtime transition')
    TRANSITION=dict(before=worker['runtime_before'],after=worker['runtime_after'],summary=summary,shuffled_index_positive=dict(passed=True,canonical_sha256=sha(canonical(shuffled))),destroyers=controls,restored=True,comparison_scope='Exact source-predicted stage additions; every original file verification remains enforced. No altered record is returned to frozen readers.')
    h.remember('exact-source-predicted-runtime-transition',TRANSITION)
    return True

class LimitedCapture(io.StringIO):
    def write(self,value):
        need(len(self.getvalue().encode())+len(value.encode())<=96*KIB,'frozen final JSON capture remains bounded96KiB')
        return super().write(value)

def install_main(h,source):
    tree=ast.parse(source,str(V1));nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main'];need(len(nodes)==1,'one frozen main declaration');original=nodes[0]
    old=ast.parse("read(worker['runtime_before'])==read(worker['runtime_after'])",mode='eval').body
    old_dump=ast.dump(old,include_attributes=False);old_main=ast.dump(original,include_attributes=False)
    class OneCompare(ast.NodeTransformer):
        count=0
        def visit_Compare(self,node):
            if ast.dump(node,include_attributes=False)==old_dump:
                need(node.lineno==554,'exact frozen conjunct source location');self.count+=1
                return ast.copy_location(ast.Call(func=ast.Name(id='_runtime_transition_gate',ctx=ast.Load()),args=[ast.Name(id='worker',ctx=ast.Load()),ast.Name(id='plan',ctx=ast.Load())],keywords=[]),node)
            return self.generic_visit(node)
    transformer=OneCompare();new=transformer.visit(copy.deepcopy(original));need(transformer.count==1,'exactly one replaced AST Compare')
    class Reverse(ast.NodeTransformer):
        count=0
        def visit_Call(self,node):
            if isinstance(node.func,ast.Name) and node.func.id=='_runtime_transition_gate':self.count+=1;return copy.deepcopy(old)
            return self.generic_visit(node)
    reverse=Reverse();restored=reverse.visit(copy.deepcopy(new));need(reverse.count==1 and ast.dump(restored,include_attributes=False)==old_main,'every other AST node remains exactly frozen')
    need('_runtime_transition_gate' not in h.__dict__,'fresh explicit gate binding');h._runtime_transition_gate=gate
    module=ast.fix_missing_locations(ast.Module(body=[new],type_ignores=[]))
    exec(compile(module,str(SELF)+'::frozen_main_one_runtime_conjunct','exec'),h.__dict__)
    return dict(replaced_comparisons=1,original_line=554,original_comparison_ast_sha256=sha(old_dump.encode()),original_main_ast_sha256=sha(old_main.encode()),adapted_main_ast_sha256=sha(ast.dump(new,include_attributes=False).encode()),reversal_reproduces_every_other_node=True,scope='Only before/after raw snapshot equality is replaced. All scientific, source, command, publication, ledger and accounting gates remain original.')

def main():
    global H
    need(Path.cwd().resolve()==ROOT and Path(sys.executable).resolve()==PYTHON and sys.dont_write_bytecode,'fixed owned Python and no bytecode')
    p=argparse.ArgumentParser()
    for key_ in ('plan','result','outer','console','exit'):p.add_argument('--'+key_+'-sha256',required=True)
    args=p.parse_args();ledger_ref,ledger_value=ledger()
    own,_=bound(SELF);old_ref,source=bound(V1,V1_PIN)
    failed_refs={};failed_values={}
    for name,(filename,size,digest) in FAILED.items():
        ref,data=bound(WORK/filename,(size,digest));failed_refs[name]=ref
        if name in ('outer','partial'):failed_values[name]=strict(data)
    failed_outer=failed_values['outer'];failed_partial=failed_values['partial']
    command=[str(PYTHON),'-B',str(V1)]
    for k in ('plan','result','outer','console','exit'):command.extend(['--'+k+'-sha256',getattr(args,k+'_sha256')])
    need(failed_outer['command']==command and failed_outer['exit_code']==1 and failed_outer['stdout_bytes']==0 and failed_outer['stderr_bytes']==928 and failed_outer['launcher_error'] is None and failed_outer['elapsed_wall_seconds']==0.7889838000010059,'exact first failed audit launch and full costs')
    need(failed_partial['status']=='AUDIT_INCOMPLETE' and failed_partial['admission_allowed'] is False and 'line 554' in failed_partial['error'] and 'exact parent counters and stable worker runtime' in failed_partial['error'],'exact retained failed-conjunct partial')
    h=types.ModuleType('immutable_saved_completion_audit_v1');h.__file__=str(V1);sys.modules[h.__name__]=h
    exec(compile(source,str(V1),'exec'),h.__dict__);H=h
    # Keep h.SELF=V1 so the frozen main validates the original subject's unchanged251-source plan.
    need(h.SELF==V1 and h.FAMILY_RESERVES['progress']==48*KIB,'unchanged original source identity and declared old progress reservation')
    h.PROGRESS=PROGRESS;h.FAMILY_RESERVES=dict(h.FAMILY_RESERVES,progress=64*KIB)
    adaptation=install_main(h,source);capture=LimitedCapture();stdout=sys.stdout
    try:
        sys.stdout=capture;h.main()
    finally:sys.stdout=stdout
    need(GATE_CALLS==1 and TRANSITION is not None,'replacement gate actually exercised')
    result=h.strict(capture.getvalue().encode())
    need(result['schema']=='m193c-saved-sift-lightglue-saved-completion-audit-v1' and result['status']=='PASS_SAVED_PRIVATE_LIGHTGLUE_COMPLETION_OUTCOME_AUDIT' and h.same(result['audit_source'],old_ref),'unchanged frozen-main result before explicit versioned augmentation')
    for path,(ref,ident) in IMMUTABLE.items():need(identity(Path(path).stat(follow_symlinks=False))==ident,'all v2 source and failed-attempt identities unchanged')
    current_cpu=time.process_time();current_wall=time.perf_counter()-WALL_START
    base=dict(result['accounting']['subject_final_work']);h.typed_work(base)
    failed_cpu=D(str(failed_outer['elapsed_wall_seconds']))+D('.25');failed_wall=D(str(failed_outer['elapsed_wall_seconds']))+D('.5')
    carry=dict(base,cpu_seconds=float(D(str(base['cpu_seconds']))+failed_cpu+D(str(current_cpu))+D('.25')),wall_seconds=float(D(str(base['wall_seconds']))+failed_wall+D(str(current_wall))+D('.5')))
    need(carry['cpu_seconds']<=1200 and carry['wall_seconds']<=1800 and carry['file_bytes']<=4<<30 and carry['metadata_bytes']<=128*(1<<20),'global conservative carry including preserved failure and complete current audit cost')
    result.update(schema='m193c-saved-sift-lightglue-saved-completion-audit-v2',audit_version='v2-one-runtime-conjunct',audit_source=own,reused_v1_source=old_ref,adaptation=adaptation,runtime_transition=TRANSITION,previous_failed_audit=dict(refs=failed_refs,cpu_charge_seconds=str(failed_cpu),wall_charge_seconds=str(failed_wall),scope='Full failed outer used as conservative single-thread CPU bound plus.25/.5 tails; prior partial remains incomplete.'),actual_final_work=carry,next_wall_seconds=str(D(str(carry['wall_seconds']))),audit_timing=dict(cpu_seconds=current_cpu,wall_seconds=current_wall),audit_publication_allowance=dict(cpu_seconds=.25,wall_seconds=.5),audit_family=dict(ledger=ledger_ref,limit_bytes=384*KIB,maximum_total_bytes=ledger_value['maximum_total_bytes'],reserved_outputs=RESERVES,reused_previously_charged_sources=ledger_value['reused_previously_charged_sources']),scope=result['scope']+' V2 changes only the one stage-runtime comparison; root must verify exact v2 source/ledger/outer/output pins and actual current publication tail before continuation.')
    output=json.dumps(result,sort_keys=True,allow_nan=False,separators=(',',':')).encode()
    need(len(output)+1<=RESERVES['final_json'],'actual v2 final112KiB including newline');print(output.decode())

if __name__=='__main__':
    try:main()
    except BaseException:
        if H is not None and H.PROGRESS_OWNED:
            try:H.remember('audit-v2-refused',error=traceback.format_exc())
            except BaseException as exc:print('V2 phase preservation failed: '+repr(exc),file=sys.stderr)
        raise
