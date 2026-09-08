"""Saved AREA4 diagnostic metadata audit. No subject imports or image payload/stat reads.
Held before outcome audit; actual run requires root-supplied terminal digests.
Falsifiers: omitted pair/refusal, wrong true flag, unrestored factory, altered
entire private cache record, wrong native lift, duplicate sites called support,
false graph bridge/cycle, detached source/argv/accounting or uncharged bytes.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import types
from decimal import Decimal as D, ROUND_CEILING

ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'experiments/m193c-output-grid'
OUT=HERE/'area-four-1'
HELPER=(42893,'4b4736b8a95ef7d347dd2ad98cc66ac4460e1d77d7f735e68f016e8e26912e30')
RUNNER_PIN=(27409, '2fda937bbf9e37f16bd3bc2fa8de5d5348d0d253432e22fa9366dbf9f798a7d6')
SPEC_PIN=(14404, '2e908273a5c7b21c25aed0568b5c87901ac95997f223714fb055e09753e23282')
PROTOTYPE_PIN=(2438, '136e35bc25f05cc94ecde67a179a755cbe6cf168596ecae97c97b486d4351308')
TRACE_AUDIT=(118456,'eed8b4949d7f1ec4def3defccb7cad24f8ef971e34e027b5247b618273c15428')
REAL_AUDIT=(78821,'7920f885e0cea2bcfbe2ac4f9af9ffc519212495274798cee23b79aa2e179ccc')
PRIVATE_AUDIT='471c68d50e1cca2804eec32e38756d06b3e0d8db79716de1450fb038ff197b5e'
VERSION='m193c-area-four-diagnostic-v1'
COMPLETE='COMPLETE_AREA_FOUR_DIAGNOSTIC_ONLY'
METHOD='entire registrar return/refusal or trace; exact canonical bytes'
BUDGET=dict(cpu_seconds=20,wall_seconds=30,file_bytes=1<<20,metadata_bytes=1<<20)
KWARGS=dict(nfeatures=2048,nOctaveLayers=3,contrastThreshold=0.01,edgeThreshold=12,sigma=1.6,enable_precise_upscale=True)
PRIVATE_CACHE=None


def helpers():
    p=HERE/'work/independent-factor-eight-1-audit.py';raw=p.read_bytes()
    if (len(raw),hashlib.sha256(raw).hexdigest())!=HELPER:raise ValueError('held independent helper')
    # Only our own standard-library helper executes; its main is guarded.
    a=types.ModuleType('independent_real_precise_helpers');a.__file__=str(p)
    sys.modules[a.__name__]=a;exec(compile(raw,str(p),'exec'),a.__dict__);a.OUT=OUT
    names=('need integer sha canonical strict path file read actual same saved planned components topology controls landmarks hv signature coordinate_rows corners corner_pass check_corners near_components residual true_rotation_landmarks commissioning all_inventory USED GAPS TIFF_STAT QUAL CODE ORIGINAL ALL_IDS NATIVE_AUDIT Q').split()
    for name in names:globals()[name]=getattr(a,name)
    globals()['QUAL']=dict(coordinate_gauge='native pixel centres; q_native=4*q_coarse+384',coordinate_lattice_step_q8=4,inherited_quantization_guard_q8=1,guard_status='UNQUALIFIED_FOR_COARSE_LATTICE',scope='Diagnostic direct fit only; no support, overlap, placement or quality admission')
    globals()['ALL_IDS']=[s.replace('area8-','area4-') for s in a.ALL_IDS]
    return a,p


def comparison(got,label,left,right):
    l,r=canonical(left),canonical(right)
    expected=dict(label=label,method=METHOD,equal=l==r,left=dict(bytes=len(l),sha256=sha(l)),right=dict(bytes=len(r),sha256=sha(r)))
    need(got==expected,'entire canonical predicate: '+label)
    return l==r


def witness(w,scope,ordinal,complete=False):
    keys=set('scope ordinal requested_true calls restored error'.split())
    if scope=='real':keys.add('original_index')
    need(set(w)==keys and w['scope']==scope and integer(w['ordinal']) and w['ordinal']==ordinal and w['requested_true'] is True,'fixed scoped factory attempt')
    if scope=='real':need(w['original_index']==ORIGINAL[ordinal],'factory actual original index')
    need(type(w['calls']) is list and len(w['calls'])<=1 and w['restored'] is True,'one call ceiling and final restoration')
    for call in w['calls']:need(call==KWARGS and all(type(call[k]) is type(v) for k,v in KWARGS.items()),'only explicit true constructor flag')
    need(w['error'] is None or (type(w['error']) is str and 'Traceback' in w['error']),'retained factory error')
    if complete:need(len(w['calls'])==1 and w['error'] is None,'completed extraction actual factory')


def private_native_baseline(plan):
    global PRIVATE_CACHE
    refs=plan['private_baseline'];need(set(refs)==set('plan result outer console exit audit'.split()),'six private baseline FileRefs')
    historical={k:read(r) if k in ('plan','result','outer','audit') else file(path(r),r) for k,r in refs.items()}
    old,audit,parent=historical['plan'],historical['audit'],historical['result'];worker=read(parent['worker_result'])
    need(refs['audit']['sha256']==PRIVATE_AUDIT and audit['schema']=='m193c-saved-precise-upscale-canonical-audit-v1' and audit['status']=='PASS_SAVED_PRECISE_UPSCALE_CANONICAL_OUTCOME_AUDIT' and audit['subject_complete'] is True and audit['refused_control'] is None and audit['cpu_accounting_complete'] is True,'held completed canonical private authority')
    need(old['schema']=='m193c-precise-upscale-canonical-plan-v1' and all(plan['source_bindings'].get(k)==v for k,v in old['source_bindings'].items()),'whole exercised private source closure')
    for k in ('plan','result','outer','console','exit'):need(same(refs[k],audit['external'][k]),'private audit external association')
    need(same(parent['worker_result'],audit['worker_result']) and same(parent['plan'],refs['plan']) and parent['status']==worker['status']=='COMPLETE_PRIVATE_PRECISE_UPSCALE_CONTROL_ONLY' and parent['implementation_version']==worker['implementation_version']=='m193c-precise-upscale-canonical-v1','actual audited complete private worker')
    need(parent['sources_unchanged'] is worker['sources_unchanged'] is True and parent['error'] is worker['error'] is None and parent['finalization_errors']==worker['finalization_errors']==[],'historical terminal/source checks')
    final=strict(path(refs['console']).read_bytes().splitlines()[-1]);outer=historical['outer']
    need(final['work_through_final_checks']==audit['actual_final_work'] and final['cpu_accounting_complete'] is True and final['status']==parent['status'] and final['error'] is None and final['finalization_errors']==[],'canonical final accounting association')
    need(outer['exit_code']==0 and type(outer['exit_code']) is int and outer['admissible_parent_exit'] is True and path(refs['exit']).read_bytes().strip()==b'0' and outer['command']==parent['command'] and outer['plan_sha256']==refs['plan']['sha256'],'canonical actual outer/exit')
    need(D(str(parent['prior_work']['wall_seconds']))+D(str(outer['elapsed_wall_seconds']))==D(audit['next_wall_seconds']),'canonical conservative wall')
    need(len(worker['controls'])==7 and all(r['passed'] is True for r in worker['controls']) and [(r['id'],r['passed']) for r in worker['comparison_controls']]==[('whole-record-comparator',True)] and worker['counters']==dict(private_decode_attempts=1,feature_extraction_attempts=6,factory_calls=6,matcher_calls=5) and len(worker['arms'])==3,'cached complete private population')
    ar=worker['arms'][1];arm=read(ar);fr=arm['feature_record'];f=read(fr)
    need(arm['name']=='precise-true' and arm['enable_precise_upscale'] is True and arm['factory_restored'] is True and arm['constructor_calls']==[KWARGS]*2 and arm['error'] is None and arm['outcome']['status']=='RETURNED' and corner_pass(arm['outcome']['transform']),'audited actual true arm')
    need(path(ar)==HERE/'precise-upscale-canonical-1/worker/precise-true-arm.json' and path(fr)==HERE/'precise-upscale-canonical-1/worker/precise-true-features.json','literal private cache paths')
    PRIVATE_CACHE=dict(arm_ref=ar,features_ref=fr,features=f,outcome=arm['outcome'])
    # The pinned complete private audit owns its earlier failure chain. Recover
    # the original real9/native23 authority without inventing a new population.
    previous=read(old['failed_attempt']['plan']);factor=read(previous['factor_eight_baseline']['plan']);native_refs=factor['native_baseline']
    native={k:read(r) if k in ('plan','result','outer','audit') else file(path(r),r) for k,r in native_refs.items()}
    nold,na=native['plan'],native['audit'];np=native['result'];nw=read(np['worker_result']);nr=read(np['request'])
    need(native_refs['audit']['sha256']==NATIVE_AUDIT and na['status']=='PASS_SAVED_DIRECT_PAIR_OUTCOME_AUDIT' and na['subject_complete'] is True and len(nold['source_bindings'])==170 and all(plan['source_bindings'].get(k)==v for k,v in nold['source_bindings'].items()),'old 170-source closure and complete native audit')
    for k in ('plan','result','outer','console','exit'):need(same(native_refs[k],na['external'][k]),'native external authority')
    need(same(np['worker_result'],na['worker_result']) and np['status']==nw['status']=='COMPLETE_DIRECT_PAIR_SUPPORT_ONLY' and np['sources_unchanged'] is nw['sources_unchanged'] is True and np['error'] is nw['error'] is None and np['finalization_errors']==nw['finalization_errors']==[],'cached complete native outcome')
    need([r['pair'] for r in nw['pairs']]==planned() and all(r['outcome']['status']=='REGISTRATION_REFUSED' for r in nw['pairs']),'all 23 native refusals retained')
    return audit,native_refs,nw,nr


def graph_commission():
    def score(edges):
        groups=components(edges);bridges=[e for i,e in enumerate(edges) if len(components(edges[:i]+edges[i+1:]))>len(groups)]
        return len(groups),len(edges)-9+len(groups),bridges
    need(score([[0,1],[1,2]])==(7,0,[[0,1],[1,2]]),'graph tree is two bridges and zero cycles')
    need(score([[0,1],[1,2],[2,0]])==(7,1,[]),'graph ring positive has one cycle and no bridges')
    need(score([])==(9,0,[]),'graph empty retains all nodes')
    return ['tree_bridges','ring_cycle','empty_nine_nodes']


def site_check(o):
    marks=o['landmarks'];reported=o['site_evidence'];need(set(reported)==set('scope descriptor_match_count exact_joint_groups sides repeated_joint_groups'.split()),'compact site receipt');joint={};sides={}
    for i,m in enumerate(marks):joint.setdefault(tuple(m['reference_q8']+m['source_q8']),[]).append(i)
    for side in ('reference_q8','source_q8'):
        points=sorted({tuple(m[side]) for m in marks});cal={tuple(m[side]) for m in marks if m['split']=='calibration'};held={tuple(m[side]) for m in marks if m['split']=='holdout'}
        e=dict(unique_total=len(points),calibration_unique=len(cal),holdout_unique=len(held),exact_locations_shared_between_splits=[list(p) for p in sorted(cal&held)],bbox_q8=None if not points else [min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)])
        need(reported['sides'][side]==e,'exact site extent/intersection')
        sides[side]=dict(exact_sites=len(points),exact_shared_sites=len(cal&held),radius_one=near_components(marks,side))
    repeated=[dict(reference_q8=list(k[:2]),source_q8=list(k[2:]),ordinals=ids,split_membership=sorted({marks[i]['split'] for i in ids})) for k,ids in sorted(joint.items()) if len(ids)>1]
    need(reported['descriptor_match_count']==len(marks) and reported['exact_joint_groups']==len(joint) and reported['repeated_joint_groups']==repeated,'joint groups')
    need(reported['scope']=='descriptive exact coordinate groups; no independence or coverage acceptance claim','site scope')
    return dict(descriptor_rows=len(marks),exact_joint_groups=len(joint),exact_joint_mixed=sum(len(g['split_membership'])>1 for g in repeated),radius_one_joint=near_components(marks,'joint'),sides=sides)

def observed(o,ref_coords,src_coords,*,missing=False,captured=True):
    q=dict(QUAL)
    if missing:q.update(coordinate_gauge='active faulty coordinates; q_fault=4*q_coarse+0',expected_ordinary_coordinate_gauge=QUAL['coordinate_gauge'],active_defect='omitted +384 Q8 on both endpoints')
    need(o['qualification']==q,'coarse lattice qualification');marks=o['landmarks'];need(len(marks)<=256,'bounded matches')
    if captured:
        landmarks(o,[dict(coordinates_q8=ref_coords),dict(coordinates_q8=src_coords)],dict(reference=0,source=1))
        if o['status']=='RETURNED':
            held=[]
            for i,m in enumerate(marks):
                e=residual(m,o['transform']);need(m['inlier'] is (e<=(2*256*Q)**2),'retained-map inlier flags')
                if i%2 and m['inlier']:held.append(e)
            cal=sum(m['inlier'] for m in marks if m['split']=='calibration')
            need(cal==o['metrics']['calibration_inlier_count'] and cal>=12 and cal*2>=(len(marks)+1)//2,'all retained calibration flags/count/half')
            need(len(held)>=12 and len(held)*2>=len(marks)//2,'held support minimum')
            total=sum(held);need(total<=len(held)*(256*Q)**2,'one native pixel held RMS')
            rms=math.sqrt(total/len(held))/(256*Q);need(o['metrics']['heldout_rms_reference_px']==f'{rms:.9f}','held RMS')
            det=o['transform']['a']**2+o['transform']['b']**2;need(det>0,'map determinant');mx=max(held);ceiling=math.isqrt(mx//det)
            if ceiling*ceiling*det<mx:ceiling+=1
            need(o['metrics']['heldout_max_source_px_ceil_q8']==ceiling and o['guard']==ceiling+1 and o['metrics']['coordinate_quantization_guard_q8']==1 and o['metrics']['valid_support_continuous_margin_q8']==128+o['guard'],'frozen unqualified guard arithmetic')
    else:need(marks==[] and o['heldout_bbox_q8'] is None and o['status']=='RETURNED' and o['error'] is None,'off/placebo signature only')
    result=site_check(o)
    if captured and o['status']=='RETURNED':
        from statistics import median
        result['returned_map_all_rows']={}
        for split in ('calibration','holdout'):
            selected=[m for m in marks if m['split']==split];squares=[residual(m,o['transform']) for m in selected];den=256*Q
            result['returned_map_all_rows'][split]=dict(count=len(selected),within_two_native_pixels=sum(v<=(2*den)**2 for v in squares),rms_native_reference_pixels=math.sqrt(sum(squares)/len(squares))/den,conventional_median_native_reference_pixels=median(math.sqrt(v)/den for v in squares),max_native_reference_pixels=math.sqrt(max(squares))/den)
    return result

def representation(r,shape):
    need(r['method']=='m193c-area4-native-centres-v1' and r['factor']==4 and r['centre_q8']==384 and r['key_coordinate_gauge']=='coarse Q8; unchanged detector keys' and r['native_shape']==shape and r['coarse_shape']==[shape[0]//4,shape[1]//4,3],'fixed AREA4')
    hv(r['coarse_rgb_sha256_u16_le'])

def lifted_arrays(coarse,native,count):
    coordinate_rows(coarse);coordinate_rows(native)
    need(integer(count) and 0<count<=1024 and len(coarse)==len(native)==count,'actual feature count')
    need(all(n==[4*x+384 for x in c] for c,n in zip(coarse,native)),'actual coordinate lift')

def private_features(ref,fixtures):
    r=read(ref);need(path(ref)==OUT/'worker/rotation-feature-record.json','private feature path')
    need(r['schema']=='m193c-area-four-private-diagnostic-features-v1' and r['qualification']==QUAL,'private schema')
    need(any(same(r['fixture'],f) for f in fixtures),'private fixture association')
    known=actual(ROOT/'experiments/M193-cover-overlap/fixtures.json')['synthetic_overlap']['sources'][0]
    need(r['fixture']['sha256']==known['source_sha256'],'literal first fixture')
    for name,shape in (('reference',[2304,3072,3]),('source',[3072,2304,3])):
        f=r[name];representation(f['representation'],shape);lifted_arrays(f['coarse_coordinates_q8'],f['native_coordinates_q8'],f['count']);hv(f['descriptors_sha256']);hv(f['keys_sha256'])
    return r

def baseline(plan):
    refs=plan['trace_baseline'];need(set(refs)==set('plan result outer console exit audit'.split()),'six trace references')
    old,parent,outer,audit=(read(refs[k]) for k in ('plan','result','outer','audit'))
    for k in ('console','exit'):file(path(refs[k]),refs[k])
    need((refs['audit']['bytes'],refs['audit']['sha256'])==TRACE_AUDIT and audit['schema']=='m193c-saved-refusal-trace-audit-v1' and audit['status']=='PASS_SAVED_REFUSAL_TRACE_OUTCOME_AUDIT' and audit['subject_complete'] is True and audit['refused_control'] is None and audit['cpu_accounting_complete'] is True,'held trace audit')
    need(old['schema']=='m193c-refusal-trace-plan-v1' and len(old['source_bindings'])==203 and all(plan['source_bindings'].get(k)==v for k,v in old['source_bindings'].items()),'whole 203 trace source closure')
    for k in ('plan','result','outer','console','exit'):need(same(refs[k],audit['external'][k]),'trace audit binding')
    worker=read(parent['worker_result']);need(same(parent['worker_result'],audit['worker_result']) and same(parent['plan'],refs['plan']),'trace worker and plan association')
    need(parent['status']==worker['status']==audit['worker_status']=='COMPLETE_SAVED_REFUSAL_TRACE_ONLY' and parent['sources_unchanged'] is worker['sources_unchanged'] is True and parent['error'] is worker['error'] is None and parent['finalization_errors']==worker['finalization_errors']==[],'trace successful finalization')
    need(parent['source_bindings']==worker['source_bindings']==old['source_bindings'] and len(worker['pairs'])==23 and len(worker['controls'])==4 and worker['registrar_replay_attempts']==77 and worker['unvisited']==[] and all(r['passed'] for r in worker['pairs']+worker['controls']),'actual complete trace population')
    final=strict(path(refs['console']).read_bytes().splitlines()[-1]);need(final['work_through_final_checks']==audit['actual_final_work'] and final['status']==parent['status'] and final['error'] is None and final['finalization_errors']==[] and final['cpu_accounting_complete'] is True,'trace final receipt')
    need(integer(outer['exit_code']) and outer['exit_code']==0 and outer['admissible_parent_exit'] is True and path(refs['exit']).read_bytes().strip()==b'0' and outer['command']==parent['command'] and outer['plan_sha256']==refs['plan']['sha256'],'trace actual exit/argv')
    need(D(str(parent['prior_work']['wall_seconds']))+D(str(outer['elapsed_wall_seconds']))==D(audit['next_wall_seconds']),'trace conservative wall')
    rr=old['real_baseline'];need(set(rr)==set('plan result outer console exit audit'.split()),'six actual AREA8 baseline refs')
    rp,ra,rparent,rout=(read(rr[k]) for k in ('plan','audit','result','outer'));rw=read(rparent['worker_result']);rq=read(rparent['request'])
    for k in ('console','exit'):file(path(rr[k]),rr[k])
    need((rr['audit']['bytes'],rr['audit']['sha256'])==REAL_AUDIT and ra['schema']=='m193c-saved-real-precise-audit-v1' and ra['status']=='PASS_SAVED_REAL_PRECISE_OUTCOME_AUDIT' and ra['subject_complete'] is True and ra['cpu_accounting_complete'] is True and ra['refused_control'] is None,'complete held AREA8 audit')
    for k in ('plan','result','outer','console','exit'):need(same(rr[k],ra['external'][k]),'AREA8 actual association')
    need(same(rparent['worker_result'],ra['worker_result']) and rparent['source_bindings']==rw['source_bindings']==rp['source_bindings'] and all(plan['source_bindings'].get(k)==v for k,v in rp['source_bindings'].items()),'AREA8 source/worker closure')
    need(rparent['status']==rw['status']=='COMPLETE_FACTOR_EIGHT_SUPPORT_ONLY' and rw['implementation_version']=='m193c-real-precise-v1' and len(rw['features'])==9 and len(rw['pairs'])==23 and len(rw['controls'])==14 and all(c['passed'] for c in rw['controls']) and rw['unvisited']==[],'whole AREA8 population')
    need(rparent['sources_unchanged'] is rw['sources_unchanged'] is True and rparent['error'] is rw['error'] is None and rparent['finalization_errors']==rw['finalization_errors']==[],'AREA8 complete finalization')
    need(rq['schema']=='m193c-factor-eight-request-v1' and same(rq['plan'],rr['plan']) and rq['pairs']==planned(),'cached real request authority')
    _,nr,nw,nq=private_native_baseline(rp)
    need(rq['rows']==nq['rows'] and rq['fixtures']==nq['fixtures'],'unchanged authenticated nine-image/five-fixture population')
    real_pairs=[];real_features=[]
    for i,row in enumerate(rw['pairs']):
        record=read(row['record']);need(row['pair']==record['pair']==planned()[i] and record['outcome']['status']=='REGISTRATION_REFUSED' and row['status']=='REGISTRATION_REFUSED','all 23 AREA8 refusals retained')
        trace=read(worker['pairs'][i]['record']);need(same(trace['input'],row['record']) and trace['pair']==record['pair'] and trace['passed'] is True,'trace exact AREA8 input')
        need(same(record['native_baseline'],rq['native_pairs'][i]) and read(record['native_baseline'])==nw['pairs'][i],'same direct native comparison')
        real_pairs.append(record)
    for i,ref in enumerate(rw['features']):
        f=read(ref);need(f['original_index']==ORIGINAL[i] and same(f['tiff'],rq['rows'][i]['tiff']) and f['status']=='RETURNED','AREA8 complete real feature cache');real_features.append(f)
    errors=[p['outcome']['error']['message'] for p in real_pairs]
    need(sum(s.endswith('no majority landmark consensus') for s in errors)==21 and '1.035343942' in errors[7] and errors[11].endswith('held-out landmarks lack a majority consensus'),'exact prior 21/1/1 paths')
    return audit,nr,nw,nq,rr,rw,rq,real_pairs,real_features


def control_audit(rows,fixtures):
    need([r['id'] for r in rows]==ALL_IDS[:len(rows)] and 7<=len(rows)<=14,'fixed control prefix')
    for r in rows:need(type(r['passed']) is bool,'typed control outcome')
    controls(rows[:7])
    for r in rows:saved(OUT/'worker'/('control-'+r['id']+'.json'),r,True)
    e={r['id']:r['evidence'] for r in rows};private=None;positive=None;audit=[]
    for row in rows[7:]:
        name=row['id'];v=row['evidence'];site_summary=None;truth_summary=None;comparisons=None
        if set(v)=={'exception'}:
            need(row is rows[-1] and row['passed'] is False and type(v['exception']) is str and 'Traceback' in v['exception'],'retained private exception')
            audit.append(dict(id=name,passed=False,exception=True));break
        if name=='area4-half-ties':
            sums=[7,8,9,23,24,25,16*65535];expected=[[[round(s/16)]*3 for s in sums]]
            need(v['input_channel_sums']==sums and v['expected']==expected,'independent ties-even truth');ok=v['actual']==expected
        elif name=='repeated-block-null':
            need(any(same(v['fixture'],f) for f in fixtures),'repeated fixture ref')
            representation(v['reference'],[2304,3072,3]);representation(v['source'],[3072,2304,3]);hs=v['actual_sha256']
            need(set(hs)=={'expected_reference','coarse_reference','expected_rotation','coarse_source'},'null hash keys')
            for h in hs.values():hv(h)
            need(hs['coarse_reference']==v['reference']['coarse_rgb_sha256_u16_le'] and hs['coarse_source']==v['source']['coarse_rgb_sha256_u16_le'],'representation hash association')
            ok=v['native_repeat_factor']==8 and v['expected_coarse_repeat_factor']==2 and hs['expected_reference']==hs['coarse_reference'] and hs['expected_rotation']==hs['coarse_source']
        elif name=='native-rotation-positive':
            private=private_features(v['features'],fixtures);positive=v['outcome']
            site_summary=observed(positive,private['reference']['native_coordinates_q8'],private['source']['native_coordinates_q8'])
            check_corners(v['corner_errors'],positive['transform'])
            need(v['literal_truth_q32']==dict(a=0,b=Q,tx=3071*Q,ty=0),'independent rotation truth')
            need(len(v['precise_factories'])==2,'two completed private true factories')
            for i,w in enumerate(v['precise_factories']):witness(w,'private',i,True)
            ok=positive['status']=='RETURNED' and len(positive['landmarks'])>=24 and corner_pass(positive['transform'])
            if positive['landmarks']:
                truth_summary=true_rotation_landmarks(positive['landmarks'])
                truth_summary['same_fixture_area8_true']=true_rotation_landmarks(PRIVATE_CACHE['outcome']['landmarks'])
                need(same(private['fixture'],PRIVATE_CACHE['features']['fixture']),'same physical fixture across representations')
        elif name=='native-two-pixel-map-destroyer':
            need(positive is not None and v['baseline']==positive['transform'] and v['qualification']==QUAL and v['added_native_px']==2,'two-pixel baseline')
            need(v['mutated']==dict(positive['transform'],tx=positive['transform']['tx']+2*Q),'tx mutation only')
            check_corners(v['corner_errors'],v['mutated']);ok=not corner_pass(v['mutated'])
        elif name=='centre-offset-destroyer':
            need(private is not None and same(v['features'],e['native-rotation-positive']['features']) and v['active_omission_q8']==384,'same private features')
            o=v['outcome'];site_summary=observed(o,[[4*x for x in p] for p in private['reference']['coarse_coordinates_q8']],[[4*x for x in p] for p in private['source']['coarse_coordinates_q8']],missing=True)
            check_corners(v['corner_errors'],o['transform']);ok=o['status']=='RETURNED' and not corner_pass(o['transform'])
        elif name=='native-rotation-restored':
            o=v['outcome'];site_summary=observed(o,private['reference']['native_coordinates_q8'],private['source']['native_coordinates_q8']);check_corners(v['corner_errors'],o['transform'])
            comparisons=v['canonical_comparisons'];need(len(comparisons)==2,'both complete restored outcomes')
            # The left full restored feature value was not separately saved; validate its execution hash witness against the saved positive.
            equalities=[comparison(comparisons[0],'entire-restored-private-features',private,private),comparison(comparisons[1],'entire-restored-outcome',o,positive)]
            ok=signature(o)==signature(positive) and v['corner_errors']==e['native-rotation-positive']['corner_errors'] and o['status']=='RETURNED' and corner_pass(o['transform']) and all(equalities)
        elif name=='rotation-observer-null':
            for mode in ('off','count','placebo'):observed(v[mode],private['reference']['native_coordinates_q8'],private['source']['native_coordinates_q8'],captured=mode=='count')
            need(v['count']==e['native-rotation-restored']['outcome'],'count reuses restored call')
            expected={k:sha(canonical(signature(v[k]))) for k in ('off','count','placebo')}
            comparisons=v['canonical_comparisons'];need(len(comparisons)==2,'two observer predicates')
            equalities=[comparison(comparisons[i],'observer-count-vs-'+mode,signature(v['count']),signature(v[mode])) for i,mode in enumerate(('off','placebo'))]
            ok=all(equalities) and len(set(expected.values()))==1 and len(v['count']['landmarks'])>=24
        need(row['passed'] is ok,'saved boolean versus independent predicate: '+name)
        audit.append(dict(id=name,passed=ok,corner_errors=v.get('corner_errors'),captured_landmarks=len(v.get('outcome',{}).get('landmarks',[])),site_summary=site_summary,literal_truth_all_landmarks=truth_summary,canonical_comparisons=comparisons))
        if not ok:need(row is rows[-1],'no continuing after failed control')
    all_pass=len(rows)==14 and all(r['passed'] for r in rows)
    if all_pass:saved(OUT/'worker/controls.json',rows,True)
    else:need(not (OUT/'worker/controls.json').exists(),'no complete control record after failure')
    if private is None and (OUT/'worker/rotation-feature-record.json').exists():private=private_features(file(OUT/'worker/rotation-feature-record.json'),fixtures)
    return dict(all_fourteen_pass=all_pass,rows=[dict(id=r['id'],passed=r['passed']) for r in rows],additive_checks=audit,private_features_present=private is not None,private_counts=None if private is None else {k:private[k]['count'] for k in ('reference','source')},unvisited=ALL_IDS[len(rows):])


def main():
    cpu,wall=time.process_time(),time.perf_counter();parser=argparse.ArgumentParser()
    for k in ('plan','result','outer','console','exit'):parser.add_argument('--'+k+'-sha256',required=True)
    args=parser.parse_args();helper,hpath=helpers();commissioned=commissioning()+graph_commission();refs={}
    names=dict(plan=HERE/'area-four-plan-1.json',result=OUT/'result.json',outer=HERE/'work/area-four-1-outer.json',console=HERE/'work/area-four-1-console.txt',exit=HERE/'work/area-four-1-exit.txt')
    for k,p in names.items():refs[k]=file(p);need(refs[k]['sha256']==getattr(args,k+'_sha256'),'external actual '+k)
    plan,parent,outer=(read(refs[k]) for k in ('plan','result','outer'))
    console=strict(path(refs['console']).read_bytes().splitlines()[-1]);exit_code=int(path(refs['exit']).read_bytes().strip())
    need(set(plan)==set('schema source_bindings trace_baseline prior_work preparation_allowance python_executable commands'.split()) and plan['schema']=='m193c-area-four-plan-v1','closed new plan')
    need(set(plan['trace_baseline'])==set('plan result outer console exit audit'.split()),'six baseline references')
    need(set(outer)==set('scope command plan_sha256 exit_code elapsed_wall_seconds admissible_parent_exit'.split()) and outer['plan_sha256']==refs['plan']['sha256'],'closed actual outer')
    for relative,binding in plan['source_bindings'].items():file(ROOT/relative,dict(path=relative,**binding))
    for relative,pin in (('area-four-run.py',RUNNER_PIN),('area-four-preregister.md',SPEC_PIN),('area-four-prototype.py',PROTOTYPE_PIN)):
        r=file(HERE/relative);need((r['bytes'],r['sha256'])==pin,'held executed '+relative)
    py=file(path(plan['python_executable']),plan['python_executable'])
    audit,native_refs,native_worker,native_request,real_refs,real_worker,real_request,real_pairs,real_features=baseline(plan)
    schedule=planned()
    prior=read(plan['prior_work']);need(plan['preparation_allowance']==BUDGET,'whole preparation allowance')
    for k,extra in BUDGET.items():need(D(str(prior[k]))==(D(audit['next_wall_seconds']).quantize(D('0.000001'),rounding=ROUND_CEILING) if k=='wall_seconds' else D(str(audit['actual_final_work'][k])))+extra,'exact no-refund carry')
    need(prior==dict(cpu_seconds=611.234375,wall_seconds=727.575086,file_bytes=3966142483,metadata_bytes=40941837),'literal new carry')
    need(set(plan['commands'])=={'parent','worker'},'two exact commands');base=[py['path'],'-B','-X','faulthandler','-X']
    pc=base+['pycache_prefix='+str(OUT/'parent-cache'),str(HERE/'area-four-run.py'),'--plan',str(names['plan']),'--sha256',refs['plan']['sha256'],'--output',str(OUT)]
    command=[refs['plan']['sha256'] if x=='ACTUAL_PLAN_SHA256' else x for x in plan['commands']['parent']]
    need(pc==command==parent['command']==outer['command'] and same(parent['plan'],refs['plan']),'independent parent argv')
    need(integer(outer['exit_code']) and outer['exit_code']==exit_code and outer['admissible_parent_exit'] is (exit_code==0),'actual parent exit')
    need(parent['schema']=='m193c-area-four-diagnostic-run-v1' and parent['source_bindings']==plan['source_bindings'] and parent['prior_work']==prior and parent['qualification']==QUAL,'parent association')
    need(parent['sources_unchanged'] is True and parent['finalization_errors']==[],'parent final checks')
    need(console['status']==parent['status'] and Path(console['result']).resolve()==OUT/'result.json' and console['error']==parent['error'] and console['finalization_errors']==parent['finalization_errors'],'terminal publication')
    need(parent['request'] is not None and parent['worker_result'] is not None and parent['child'] is not None,'audited branch has worker')
    request=read(parent['request']);worker=read(parent['worker_result'])
    need(set(request)==set('schema plan pairs rows fixtures area8_pair_refs prior_work'.split()) and request['schema']=='m193c-area-four-diagnostic-request-v1','closed request')
    need(same(request['plan'],refs['plan']) and request['pairs']==schedule and request['rows']==real_request['rows'] and request['fixtures']==real_request['fixtures'],'same requested population')
    need([(r['ordinal'],r['original_index']) for r in request['rows']]==list(enumerate(ORIGINAL)) and len(request['fixtures'])==5,'literal nine/five population')
    for r in [row['tiff'] for row in request['rows']]+request['fixtures']:
        need(set(r)=={'path','bytes','sha256'} and integer(r['bytes']) and r['bytes']>0,'opaque authenticated image reference');hv(r['sha256'])
    need(len(request['area8_pair_refs'])==23,'cached AREA8 FileRef count')
    for i,r in enumerate(request['area8_pair_refs']):need(path(r)==HERE/'real-precise-1/worker'/(schedule[i]['id']+'.json') and read(r)==real_pairs[i],'exact cached pair FileRef')
    need(all(request['prior_work'][k]>=prior[k] for k in prior),'setup carry into request')
    pair_plan=dict(rows=request['rows'],pairs=schedule,area8_pair_refs=request['area8_pair_refs'])
    need(not (OUT/'pair-plan.json').exists(),'parent does not duplicate pair plan');saved(OUT/'worker/pair-plan.json',pair_plan,True)
    need(worker['schema']=='m193c-area-four-diagnostic-worker-v1' and worker['request']==parent['request'] and worker['plan']==parent['plan'] and worker['source_bindings']==plan['source_bindings'] and worker['prior_work']==prior and worker['qualification']==QUAL and worker['sources_unchanged'] is True and worker['finalization_errors']==[],'worker final/associations')
    wc=base+['pycache_prefix='+str(OUT/'worker-cache'),str(HERE/'area-four-run.py'),'--plan',str(names['plan']),'--sha256',refs['plan']['sha256'],'--output',str(OUT/'worker'),'--worker','--request',str(OUT/'request.json'),'--request-sha256',parent['request']['sha256']]
    expected=[refs['plan']['sha256'] if x=='ACTUAL_PLAN_SHA256' else parent['request']['sha256'] if x=='ACTUAL_REQUEST_SHA256' else x for x in plan['commands']['worker']]
    child=parent['child'];need(wc==expected==child['command']==worker['command'],'independent worker argv')
    need(parent['environment']==dict.fromkeys(('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'),'2') and parent['removed_environment']==sorted(set(parent['removed_environment'])),'bounded saved environment')
    need(not (OUT/'parent-cache').exists() and not (OUT/'worker-cache').exists(),'no bytecode/cache artifacts')
    need(parent['implementation_version']==worker['implementation_version']==VERSION,'actual precise implementation tags')
    obs=worker['precise_factory_observations']
    need(set(obs)=={'private','real'} and len(obs['private'])<=2 and len(obs['real'])<=9,'factory scope/population')
    for scope in ('private','real'):
        for i,w in enumerate(obs[scope]):witness(w,scope,i)
    ctrl=control_audit(worker['controls'],request['fixtures']);complete=parent['status']==COMPLETE
    for row in worker['controls']:
        if row['id']=='native-rotation-positive' and 'precise_factories' in row['evidence']:
            need(row['evidence']['precise_factories']==obs['private'],'control/publication actual private witnesses')
    features=[];fs=[];pairs=[];records=[];graph=None
    if ctrl['all_fourteen_pass']:
        need(len(obs['private'])==2 and len(obs['real'])==9,'complete explicit true extraction population')
        for i,w in enumerate(obs['private']):witness(w,'private',i,True)
        need(complete and worker['status']==parent['status'] and worker['error'] is parent['error'] is None and worker['real_decode_attempts']==worker['real_decodes_completed']==9 and len(worker['features'])==9 and len(worker['pairs'])==23,'complete real phase')
        for i,ref in enumerate(worker['features']):
            need(path(ref)==OUT/'worker'/f'feature-{i}.json','feature FileRef path');f=read(ref);features.append(f)
            need(f['schema']=='m193c-area-four-diagnostic-feature-v1' and f['qualification']==QUAL and f['original_index']==ORIGINAL[i] and same(f['tiff'],request['rows'][i]['tiff']),'real feature association')
            if f['representation'] is not None:
                representation(f['representation'],[4688,7032,3])
                need(f['representation']['precise_factory']==obs['real'][i],'feature receipt actual factory witness')
            if f['status']=='RETURNED':
                need(f['error'] is None and f['representation'] is not None,'returned feature receipt');witness(obs['real'][i],'real',i,True);r=f['representation'];lifted_arrays(r['coarse_coordinates_q8'],r['native_coordinates_q8'],f['count'])
                need(f['coordinates_q8']==r['native_coordinates_q8'],'emitted native coordinates');hv(f['descriptors_sha256']);hv(f['keys_sha256'])
            else:need(f['status']=='FEATURE_UNAVAILABLE' and f['error']['code']==CODE and obs['real'][i]['error'] is not None,'feature scientific refusal retained through factory')
            fs.append(dict(original_index=ORIGINAL[i],status=f['status'],count=f.get('count'),representation=f['representation'] is not None,area8_count=real_features[i]['count'],keys_sha256=f.get('keys_sha256'),descriptors_sha256=f.get('descriptors_sha256'),record=ref,precise_factory=obs['real'][i],error=f.get('error')))
        for i,index in enumerate(worker['pairs']):
            need(index['pair']==schedule[i] and path(index['record'])==OUT/'worker'/(schedule[i]['id']+'.json'),'ordered pair FileRef')
            record=read(index['record']);records.append(record);o=record['outcome'];p=record['pair']
            need(record['schema']=='m193c-area-four-diagnostic-pair-v1' and p==schedule[i] and same(record['area8_precise_baseline'],request['area8_pair_refs'][i]) and index['status']==o['status'],'pair cached association')
            a,z=p['reference'],p['source'];missing=[j for j in (a,z) if features[j]['status']!='RETURNED'];sites=None
            if missing:need(o==dict(status='FEATURE_UNAVAILABLE',unavailable=missing,qualification=QUAL),'unavailable propagation')
            else:sites=observed(o,features[a]['coordinates_q8'],features[z]['coordinates_q8'])
            err=o.get('error');pairs.append(dict(id=p['id'],source=z,reference=a,source_original=ORIGINAL[z],reference_original=ORIGINAL[a],record=index['record'],area8_precise_baseline=record['area8_precise_baseline'],area8_baseline_status='REGISTRATION_REFUSED',area8_matches=len(real_pairs[i]['outcome']['landmarks']),area8_site_summary=helper.site_check(real_pairs[i]['outcome']),area8_error={k:real_pairs[i]['outcome']['error'][k] for k in ('code','message')},status=o['status'],matches=len(o.get('landmarks',[])),transform=o.get('transform'),metrics=o.get('metrics'),error=None if err is None else {k:err[k] for k in ('code','message')},site_summary=sites))
        need(worker['unvisited']==parent['unvisited']==[] and worker['graph']==parent['graph'] and worker['graph']['qualification']==QUAL,'complete topology')
        graph=topology(records,worker['graph']);graph.update(anchor_local=4,anchor_original=52,reference_local=5,reference_original=65,anchor_component=next(c for c in graph['components'] if 4 in c),reference_component=next(c for c in graph['components'] if 5 in c));need(exit_code==child['exit_code']==0,'complete exits')
    else:
        need(not complete and parent['status']==worker['status']=='REFUSED' and exit_code==child['exit_code']==1 and parent['error'] is not None and worker['error'] is not None,'failed control remains refusal')
        need(worker['controls'][-1]['passed'] is False and len(worker['controls'])>=8,'named additive failed control')
        need(obs['real']==[] and worker['real_decode_attempts']==worker['real_decodes_completed']==0 and worker['features']==worker['pairs']==[] and worker['unvisited']==parent['unvisited']==list(range(23)) and worker['graph'] is parent['graph'] is None,'zero real phase after failed control')
        need(not list((OUT/'worker').glob('feature-*.json')) and not list((OUT/'worker').glob('pair-[0-9]*.json')),'no real records after failed control')
    if complete:
        need(parent['controls']==[dict(id=r['id'],passed=r['passed'],record=f) for r,f in zip(worker['controls'],worker['control_records'],strict=True)],'compact parent control associations')
        for k in ('control_records','features','pairs','unvisited','graph','development_outcome','real_decode_attempts','real_decodes_completed','runtime_before','runtime_after','precise_factory_observations'):need(parent[k]==worker[k],'parent complete copy: '+k)
        expected_development='ZERO_RETURNED_EDGES_AT_FIXED_AREA4' if not graph['edges'] else 'RETURNED_EDGES_REQUIRE_INDEPENDENT_GEOMETRY_AND_CONSUMER_QUALIFICATION'
        need(worker['development_outcome']==expected_development,'fixed arm decision')
    else:need(parent['features']==parent['pairs']==parent['controls']==parent['control_records']==[] and parent['precise_factory_observations']==dict(private=[],real=[]) and parent['real_decode_attempts']==parent['real_decodes_completed']==0,'failed parent has no copied scientific results')
    need(len(worker['control_records'])==len(worker['controls']),'individual control count')
    for r,f in zip(worker['controls'],worker['control_records'],strict=True):need(read(f)==r and path(f)==OUT/'worker'/('control-'+r['id']+'.json'),'complete individual control records')
    fixed=dict(legacy_feature_extractions=5,private_precise_extractions=2,real_precise_extractions=9,legacy_matcher_calls=6,private_matcher_calls=5,real_matcher_calls=23)
    need(parent['fixed_maximum_calls']==worker['fixed_maximum_calls']==fixed,'source fixed maximum calls')
    runtime=actual(ROOT/'experiments/M193-cover-overlap/contract-v1.json')['reference_environment']
    need(worker['runtime_before']==runtime and worker['runtime_after']==(runtime if complete else None),'runtime branch')
    need(child['error'] is None and child['cleanup_errors']==[] and child['terminal_job_accounting'] is True and child['direct_exit_observed'] is True and child['pipe_eof_observed'] is True and child['job_accounting']['active_processes']==0 and child['termination']['attempted'] is False and child['post_exit_drain']['completed'] is True,'terminal Job no kill/error')
    account=child['job_accounting'];need(all(integer(account[k]) for k in ('total_cpu_100ns','total_user_100ns','total_kernel_100ns','active_processes')) and account['total_cpu_100ns']==account['total_user_100ns']+account['total_kernel_100ns'],'CPU components')
    log=file(OUT/'worker.log');need(child['log_bytes']==log['bytes'] and (child.get('log') is None or same(child['log'],log)),'actual worker log')
    terminal=strict(path(log).read_bytes().splitlines()[-1]);need(terminal['status']==worker['status'] and terminal['error']==worker['error'] and terminal['finalization_errors']==worker['finalization_errors'] and Path(terminal['result']).resolve()==OUT/'worker/result.json','worker terminal publication')
    need(console['cpu_accounting_complete'] is True and parent['work']['cpu_accounting_complete'] is True and terminal['cpu_accounting_complete'] is True and worker['work']['cpu_accounting_complete'] is True,'complete CPU accounting even on refusal')
    inventory=all_inventory();total=sum(r['bytes'] for r in inventory);work=console['work_through_final_checks']
    need(parent['work']['snapshot_bytes']==worker['work']['snapshot_bytes']==0,'no snapshots')
    need(work['file_bytes']-prior['file_bytes']==work['metadata_bytes']-prior['metadata_bytes']==total,'all actual metadata charged once')
    need(parent['work']['new_extent_bytes']+refs['result']['bytes']==total,'prepublication extent plus result')
    need(D(str(work['cpu_seconds']))-D(str(prior['cpu_seconds']))>=D(account['total_cpu_100ns'])/10000000,'whole terminal Job CPU charged')
    limits=child['limits'];caps={k:D(str(work[k]))-D(str(prior[k]))<=v for k,v in dict(cpu_seconds=300,wall_seconds=480,file_bytes=8<<20,metadata_bytes=8<<20).items()}
    need(all(D(str(work[k]))>=D(str(prior[k])) for k in prior),'no refund')
    caps['global']=work['cpu_seconds']<=1200 and work['wall_seconds']<=1800 and work['file_bytes']<=4*(1<<30) and work['metadata_bytes']<=128*(1<<20)
    caps['child_cpu']=account['total_cpu_100ns']/1e7<=limits['cpu_seconds']<=300;caps['child_wall']=child['wall_seconds']<=limits['wall_seconds']<=240
    caps['child_memory']=child['job_memory']['peak_job_memory_used_bytes']<=limits['committed_bytes']==8*(1<<30);caps['child_log']=log['bytes']<=limits['log_bytes']==1<<20
    need(child['configured_job_limits']['committed_bytes']==limits['committed_bytes'] and all(caps.values()),'actual owned caps')
    helper_ref=file(hpath);need((helper_ref['bytes'],helper_ref['sha256'])==HELPER,'executed independent helper stable')
    for ref in list(USED.values()):file(path(ref),ref)
    need(TIFF_STAT==[],'no image stat read')
    result=dict(schema='m193c-saved-area-four-audit-v1',development_outcome=worker['development_outcome'],fixed_maximum_calls=worker['fixed_maximum_calls'],status='PASS_SAVED_AREA_FOUR_OUTCOME_AUDIT',subject_complete=complete,subject_status=parent['status'],worker_status=worker['status'],subject_errors=dict(parent=parent['error'],worker=worker['error']),finalization_errors=dict(parent=parent['finalization_errors'],worker=worker['finalization_errors']),sources_unchanged=dict(parent=parent['sources_unchanged'],worker=worker['sources_unchanged']),subject_branch='COMPLETE_DIAGNOSTIC_POPULATION' if complete else 'NAMED_CONTROL_FAILED_ZERO_REAL_DECODES',refused_control=None if complete else worker['controls'][-1]['id'],external=refs,audit_source=file(__file__),pure_helper_source=helper_ref,commissioning=commissioned,trace_baseline=plan['trace_baseline'],area8_precise_baseline=real_refs,native_baseline=native_refs,area8_features=[dict(record=real_worker['features'][i],original_index=ORIGINAL[i],count=f['count'],status=f['status']) for i,f in enumerate(real_features)],precise_factory_observations=obs,worker_result=parent['worker_result'],controls=ctrl,features=fs,pairs=pairs,graph=graph,qualification=QUAL,unvisited=worker['unvisited'],real_decode_attempts=worker['real_decode_attempts'],real_decodes_completed=worker['real_decodes_completed'],actual_final_work=work,next_wall_seconds=str(D(str(prior['wall_seconds']))+D(str(outer['elapsed_wall_seconds']))),job=child,caps=caps,cpu_accounting_complete=True,inventory=inventory,inventory_total_bytes=total,image_payload_and_stat_reads=0,unique_hashed_metadata_files=len(USED),retention_gaps=GAPS,audit_timing=dict(cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall),scope='Saved JSON/metadata only; no TIFF/RAW stat, payload hash, decode, feature extraction, matching, fit or subject import. AREA8true is the fixed paired comparator, not physical truth. Private restored feature equality is an actual hash witness; its second whole value was not saved. Coarse image/descriptor/key hashes and factory restoration are producer witnesses. Exact and radius-one site groups describe repeated coordinates; connected groups may chain beyond one pixel and do not establish independence. Returned fit residuals can favor biased maps and are only consistency checks. Graph components/cycle rank/bridges are descriptive, not physical geometry, support, overlap, per-frame placement or quality admission.')
    raw=json.dumps(result,sort_keys=True,allow_nan=False,separators=(',',':')).encode();need(len(raw)<=120*(1<<10),'bounded audit result');need(len(raw)+Path(__file__).stat().st_size+12*(1<<10)<=196*(1<<10),'196 KiB audit source/result/report reservation');print(raw.decode())

if __name__=='__main__':main()
