"""Independent saved rejection-trace audit; source preparation only.
No images, detector/matcher calls, numerical-subject imports or new hypotheses.
Only reported selected seeds and actually visited refinements are reconstructed.
Global hypothesis optimality is NOT independently re-enumerated. Exact source
loop/key coverage and off/on/placebo return evidence provide partial assurance.
"""
import argparse
import ast
from decimal import Decimal as D
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics
import sys
import time
import types

ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'experiments/m193c-output-grid'
OUT=HERE/'refusal-trace-1'
Q=1<<32
XY=256
R2=(2*XY*Q)**2
HELPER=(42893,'4b4736b8a95ef7d347dd2ad98cc66ac4460e1d77d7f735e68f016e8e26912e30')
REAL_AUDIT=(78821,'7920f885e0cea2bcfbe2ac4f9af9ffc519212495274798cee23b79aa2e179ccc')
RUNNER=(34853,'05162ef398426ea7ec9ac434ec3ab637bc2cd7e02331ef93f9534357ffd50268')
SPEC=(16062,'756d46b8e2bbe2ab6513b56335c142a3fa22b2569b67ac010d6caaf1d3c7191d')


def need(ok,why):
    if not ok:raise ValueError(why)


def integer(x):return type(x) is int


def rounded_ratio(n,d):
    # Signed floor/remainder handles negative half ties without floating point.
    need(integer(n) and integer(d) and d>0,'positive exact ratio denominator')
    q,r=divmod(n,d)
    return q+int(2*r>d or (2*r==d and q%2!=0))


def coords(row):
    r,s=row['reference_q8'],row['source_q8']
    need(type(r) is list and type(s) is list and len(r)==len(s)==2 and all(integer(v) for v in r+s),'literal Q8 row')
    return r[0],r[1],s[0],s[1]


def retained_seed(first,second):
    rx,ry,sx,sy=coords(first);rx1,ry1,sx1,sy1=coords(second)
    dx,dy,du,dv=sx1-sx,sy1-sy,rx1-rx,ry1-ry
    den=dx*dx+dy*dy;refden=du*du+dv*dv
    if min(den,refden)<(32*XY)**2:return None
    # The squared scale is refden/den, giving exact inclusive [1/2,2].
    if 4*refden<den or refden>4*den:return None
    an=dx*du+dy*dv;bn=dx*dv-dy*du
    return dict(a=rounded_ratio(an*Q,den),b=rounded_ratio(bn*Q,den),
        tx=rounded_ratio((rx*den-an*sx+bn*sy)*Q,XY*den),
        ty=rounded_ratio((ry*den-bn*sx-an*sy)*Q,XY*den))


def retained_refinement(rows):
    # Pair-difference identities differ from the subject's centred sums. This
    # checks a visited fit only; it is never called on an unvisited candidate.
    need(len(rows)>=2,'visited least-squares subset has at least two rows')
    points=[coords(r) for r in rows];den=an=bn=0
    for (rx,ry,sx,sy),(rx1,ry1,sx1,sy1) in itertools.combinations(points,2):
        dx,dy,du,dv=sx1-sx,sy1-sy,rx1-rx,ry1-ry
        den+=dx*dx+dy*dy;an+=dx*du+dy*dv;bn+=dx*dv-dy*du
    if den==0:return None
    rx,ry,sx,sy=(sum(p[k] for p in points) for k in range(4));n=len(rows)
    return dict(a=rounded_ratio(an*Q,den),b=rounded_ratio(bn*Q,den),
        tx=rounded_ratio((rx*den-an*sx+bn*sy)*Q,n*XY*den),
        ty=rounded_ratio((ry*den-bn*sx-an*sy)*Q,n*XY*den))


def all_residuals(rows,t):
    need(type(t) is dict and set(t)=={'a','b','tx','ty'} and all(integer(v) for v in t.values()),'saved Q32 candidate')
    values=[]
    for row in rows:
        rx,ry,sx,sy=coords(row)
        ex=t['a']*sx-t['b']*sy+t['tx']*XY-rx*Q
        ey=t['b']*sx+t['a']*sy+t['ty']*XY-ry*Q
        values.append(ex*ex+ey*ey)
    return values


def split_summary(values,indices):
    # Re-choose the complete split, including its non-inliers. This distribution
    # has no independent real truth and cannot identify a physical cause.
    selected=[values[i] for i in indices];inside=[x for x in selected if x<=R2]
    need(selected and all(integer(x) and x>=0 for x in selected),'nonempty complete residual population')
    return dict(count=len(selected),within_two_native_pixels=len(inside),
        minimum_twelve_pass=len(inside)>=12,majority_pass=2*len(inside)>=len(selected),
        all_rows_rms_native_pixels=math.sqrt(sum(selected)/len(selected))/(XY*Q),
        all_rows_median_native_pixels=statistics.median(math.sqrt(x)/(XY*Q) for x in selected),
        all_rows_max_native_pixels=math.sqrt(max(selected))/(XY*Q),
        inlier_rows_rms_native_pixels=None if not inside else math.sqrt(sum(inside)/len(inside))/(XY*Q),
        inlier_rms_at_most_one_native=None if not inside else sum(inside)<=len(inside)*(XY*Q)**2)


def commissioning():
    need([rounded_ratio(x,2) for x in (-5,-3,-1,1,3,5)]==[-2,-2,0,0,2,2],'signed ties-to-even')
    def row(sx,sy,rx,ry):return dict(source_q8=[sx*XY,sy*XY],reference_q8=[rx*XY,ry*XY])
    identity=dict(a=Q,b=0,tx=0,ty=0)
    need(retained_seed(row(0,0,0,0),row(31,0,31,0)) is None,'short baseline rejects')
    need(retained_seed(row(0,0,0,0),row(32,0,32,0))==identity,'inclusive 32-native baseline')
    need(retained_seed(row(0,0,0,0),row(64,0,32,0))==dict(a=Q//2,b=0,tx=0,ty=0),'inclusive half scale')
    need(retained_seed(row(0,0,0,0),row(32,0,64,0))==dict(a=2*Q,b=0,tx=0,ty=0),'inclusive double scale')
    need(retained_seed(row(0,0,0,0),row(32,0,65,0)) is None,'too-large scale rejects')
    plant=[row(x,y,3071-y,x) for x,y in ((0,0),(100,0),(0,100),(75,201))]
    truth=dict(a=0,b=Q,tx=3071*Q,ty=0)
    need(retained_seed(plant[0],plant[1])==retained_refinement(plant)==truth and all_residuals(plant,truth)==[0]*4,'known rotation with independent endpoints')
    need(retained_refinement([plant[0],plant[0]]) is None,'singular visited subset')
    shifted=all_residuals(plant,dict(truth,tx=truth['tx']+2*Q))
    need(shifted==[R2]*4 and split_summary(shifted,range(4))['within_two_native_pixels']==4,'inclusive two-native residual boundary')
    mixture=[0]*12+[(4*XY*Q)**2]*13
    summary=split_summary(mixture,range(25))
    need(summary['minimum_twelve_pass'] is True and summary['majority_pass'] is False and summary['inlier_rows_rms_native_pixels']==0 and summary['all_rows_rms_native_pixels']>2,'minimum versus majority and non-inlier choice have power')
    return ['signed_half_ties','short_baseline','inclusive_baseline','inclusive_half_scale','inclusive_double_scale','scale_destroyer','rotation_seed_and_refinement','singular_subset','inclusive_residual_boundary','minimum_vs_majority_and_all_split']


def helpers():
    path=HERE/'work/independent-factor-eight-1-audit.py';raw=path.read_bytes()
    need((len(raw),hashlib.sha256(raw).hexdigest())==HELPER,'held independent standard-library helper')
    a=types.ModuleType('independent_refusal_trace_helpers');a.__file__=str(path)
    sys.modules[a.__name__]=a;exec(compile(raw,str(path),'exec'),a.__dict__);a.OUT=OUT
    return a,path


def real_baseline(a,plan):
    refs=plan['real_baseline'];need(set(refs)==set('plan result outer console exit audit'.split()),'six actual real FileRefs')
    old,parent,outer,audit=(a.read(refs[k]) for k in ('plan','result','outer','audit'))
    for k in ('console','exit'):a.file(a.path(refs[k]),refs[k])
    need((refs['audit']['bytes'],refs['audit']['sha256'])==REAL_AUDIT and audit['schema']=='m193c-saved-real-precise-audit-v1' and audit['status']=='PASS_SAVED_REAL_PRECISE_OUTCOME_AUDIT' and audit['subject_complete'] is True and audit['refused_control'] is None and audit['cpu_accounting_complete'] is True,'pinned complete real audit authority')
    for k in ('plan','result','outer','console','exit'):need(a.same(refs[k],audit['external'][k]),'real audit actual external association')
    need(old['schema']=='m193c-real-precise-plan-v1' and len(old['source_bindings'])==197 and all(plan['source_bindings'].get(k)==v for k,v in old['source_bindings'].items()),'whole exercised real source closure')
    worker=a.read(parent['worker_result']);need(a.same(parent['worker_result'],audit['worker_result']) and a.same(parent['plan'],refs['plan']),'cached actual real parent/worker')
    need(parent['status']==worker['status']=='COMPLETE_FACTOR_EIGHT_SUPPORT_ONLY' and parent['implementation_version']==worker['implementation_version']=='m193c-real-precise-v1' and parent['source_bindings']==worker['source_bindings']==old['source_bindings'],'exact completed real implementation')
    need(parent['sources_unchanged'] is worker['sources_unchanged'] is True and parent['error'] is worker['error'] is None and parent['finalization_errors']==worker['finalization_errors']==[],'real final source/error checks')
    final=a.strict(a.path(refs['console']).read_bytes().splitlines()[-1])
    need(final['status']==parent['status'] and final['error'] is None and final['finalization_errors']==[] and final['cpu_accounting_complete'] is True and final['work_through_final_checks']==audit['actual_final_work'],'real final work authority')
    need(type(outer['exit_code']) is int and outer['exit_code']==0 and outer['admissible_parent_exit'] is True and a.path(refs['exit']).read_bytes().strip()==b'0' and outer['command']==parent['command'] and outer['plan_sha256']==refs['plan']['sha256'],'actual real outer/exit')
    need(D(str(parent['prior_work']['wall_seconds']))+D(str(outer['elapsed_wall_seconds']))==D(audit['next_wall_seconds']),'conservative real wall carry')
    need(worker['real_decode_attempts']==worker['real_decodes_completed']==9 and len(worker['features'])==9 and len(worker['pairs'])==23 and worker['unvisited']==[] and [x['id'] for x in worker['controls']]==a.ALL_IDS and all(x['passed'] is True for x in worker['controls']),'complete cached 14/9/23 population')
    schedule=a.planned();pairs=[];reasons=[]
    for i,index in enumerate(worker['pairs']):
        record=a.read(index['record']);need(index['pair']==record['pair']==schedule[i] and index['status']==record['outcome']['status']=='REGISTRATION_REFUSED','all original ordered scientific refusals')
        need(a.path(index['record'])==HERE/'real-precise-1/worker'/(schedule[i]['id']+'.json'),'literal real record path')
        pairs.append(dict(ref=index['record'],record=record));reasons.append(record['outcome']['error']['message'])
    expected=[a.CODE+': no majority landmark consensus']*23
    expected[7]=a.CODE+': held-out residual RMS 1.035343942 px exceeds 1.0';expected[11]=a.CODE+': held-out landmarks lack a majority consensus'
    need(reasons==expected,'exact prior 21 calibration/one RMS/one held-out refusal messages')
    pp=a.read(old['private_baseline']['result']);pw=a.read(pp['worker_result']);need(pp['status']==pw['status']=='COMPLETE_PRIVATE_PRECISE_UPSCALE_CONTROL_ONLY' and len(pw['arms'])==3,'complete cached private fixture comparison')
    arms=[dict(ref=r,record=a.read(r)) for r in pw['arms'][:2]]
    need([x['record']['name'] for x in arms]==['explicit-false','precise-true'] and [x['record']['enable_precise_upscale'] for x in arms]==[False,True] and all(x['record']['outcome']['status']=='RETURNED' and x['record']['error'] is None for x in arms),'actual false/true known private arms')
    need(not a.corner_pass(arms[0]['record']['outcome']['transform']) and a.corner_pass(arms[1]['record']['outcome']['transform']),'private retained-map truth counterexample and positive')
    return audit,pairs,arms


QUALIFICATION=dict(status='NONADMISSIBLE_DIAGNOSTIC_CANDIDATES',coordinate_gauge='native pixel centres; source to reference',coordinate_lattice_step_q8=8,inherited_quantization_guard_q8=1,guard_status='UNQUALIFIED_FOR_COARSE_LATTICE',consumer='saved registrar rejection path; no support, overlap, graph solve, placement, merge or quality admission',limitation='Residual severity does not identify bad correspondence versus localization or model error without real truth; lattice quantum does not bound detector localization.')
CDF=((1,4),(1,2),(1,1),(2,1),(4,1),(8,1),(16,1),(32,1))
QUANTILES=((0,1),(1,2),(9,10),(19,20),(1,1))


def census(rows,indices):
    from collections import Counter
    selected=[rows[i] for i in indices];groups=Counter(tuple(r['reference_q8']+r['source_q8']) for r in selected);ends={}
    for side in ('reference','source'):
        points=[tuple(r[side+'_q8']) for r in selected]
        ends[side]=dict(unique_sites=len(set(points)),bbox_q8=None if not points else [min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)])
    return dict(rows=len(selected),unique_joint_groups=len(groups),joint_multiplicity_histogram=[list(x) for x in sorted(Counter(groups.values()).items())],endpoints=ends)


def candidate(got,rows,label,expected_map=None,calibration_input=None):
    need(got['label']==label and got['qualification']==QUALIFICATION,'candidate label/nonadmission')
    t=got['transform_q32'];need(expected_map is None or t==expected_map,'independent retained-map coefficients')
    values=all_residuals(rows,t);expected=[]
    for i,row in enumerate(rows):
        rx,ry,sx,sy=coords(row);dx=t['a']*sx-t['b']*sy+t['tx']*XY-rx*Q;dy=t['b']*sx+t['a']*sy+t['ty']*XY-ry*Q
        expected.append([i,dx,dy,values[i],values[i]<=R2])
    need(got['residuals']==expected and all(type(r) is list and len(r)==5 and all(integer(x) for x in r[:4]) and type(r[4]) is bool for r in got['residuals']),'every signed/squared residual and typed inlier flag')
    need(got['calibration_input_ordinals']==calibration_input and got['calibration_update_ordinals']==[i for i in range(0,len(rows),2) if values[i]<=R2],'actual calibration input/update population')
    need(got['residual_columns']==['ordinal','predicted_minus_reference_x_numerator','predicted_minus_reference_y_numerator','squared_numerator','within_two_native'] and got['residual_coordinate_denominator']==XY*Q and got['residual_squared_denominator']==(XY*Q)**2,'literal native coordinate denominators')
    summaries=got['summaries'];need(set(summaries)=={'all','calibration','holdout'},'complete split summaries')
    for split,indices in (('all',list(range(len(rows)))),('calibration',list(range(0,len(rows),2))),('holdout',list(range(1,len(rows),2)))):
        s=summaries[split];values_sorted=sorted(values[i] for i in indices);count=len(indices)
        inside=[i for i in indices if values[i]<=R2]
        need(integer(s['count']) and integer(s['within_two_native']) and s['count']==count and s['within_two_native']==len(inside),'all split and inlier population counts')
        expected_cdf=[dict(radius_native=str(n) if d==1 else str(n)+'/'+str(d),count=sum(v*d*d<=(XY*Q*n)**2 for v in values_sorted)) for n,d in CDF]
        need(s['cdf']==expected_cdf,'independent integer CDF counts; no new gate')
        need(len(s['quantiles_nearest_rank'])==len(QUANTILES),'complete fixed quantile population')
        for q,(n,d) in zip(s['quantiles_nearest_rank'],QUANTILES):
            index=max(0,(n*count+d-1)//d-1);num=values_sorted[index]
            need(q['fraction']==(str(n) if d==1 else str(n)+'/'+str(d)) and q['squared_residual_numerator']==num and integer(q['squared_residual_numerator']) and math.isclose(q['native_px'],math.sqrt(num)/(XY*Q),rel_tol=1e-12,abs_tol=1e-12),'whole-split nearest-rank quantile')
        need(s['all_rows']==census(rows,indices) and s['within_two_rows']==census(rows,inside),'independently regroup complete versus fitted subset locations')
    return dict(label=label,transform_q32=t,calibration_input_count=None if calibration_input is None else len(calibration_input),calibration=split_summary(values,range(0,len(rows),2)),holdout=split_summary(values,range(1,len(rows),2))),values


CODE='UNMEASURED_INPUT_REGISTRATION_INADEQUATE'
REF_LINES=None


def signature(outcome):
    e=outcome['error']
    return dict(status=outcome['status'],transform=outcome['transform'],metrics=outcome['metrics'],guard=outcome['guard'],error=None if e is None else dict(code=e['code'],message=e['message']))


def refusal(message):
    return dict(status='REGISTRATION_REFUSED',transform=None,metrics=None,guard=None,error=dict(code=CODE,message=CODE+': '+message))


def gate(message,passed,**extra):return dict(message=message,code=CODE,passed=passed,**extra)


def trace_check(a,t,rows,cached=None):
    need(24<=len(rows)<=256 and all(r['split']==('holdout' if i%2 else 'calibration') for i,r in enumerate(rows)),'fixed saved row population/split')
    need(t['qualification']==QUALIFICATION and t['helpers_restored'] is True and t['callback_calls']==1,'saved callback/restoration and scope')
    cal=list(range(0,len(rows),2));held=list(range(1,len(rows),2));counts=t['seed_counts'];seed=t['seed'];steps=t['refinement'];summaries=[]
    need(set(counts)=={'total','separation_rejected','scale_rejected','eligible'} and all(integer(v) and v>=0 for v in counts.values()) and counts['total']==len(cal)*(len(cal)-1)//2==sum(counts[k] for k in ('separation_rejected','scale_rejected','eligible')),'reported exhaustive count arithmetic, not independent winner enumeration')
    need((seed is not None)==(counts['eligible']>0),'retained seed existence')
    current=[]
    if seed is not None:
        ix=seed['seed_calibration_ordinals'];need(type(ix) is list and len(ix)==2 and all(integer(v) for v in ix) and 0<=ix[0]<ix[1]<len(cal),'selected seed calibration endpoints')
        full=[cal[i] for i in ix];need(seed['seed_full_ordinals']==full,'selected full-row endpoints')
        expected=retained_seed(rows[full[0]],rows[full[1]]);need(expected is not None,'reported seed is eligible')
        summary,values=candidate(seed,rows,'selected-calibration-seed',expected)
        current=[i for i in cal if values[i]<=R2]
        need(seed['selection_key']==[-len(current),sum(values[i] for i in current),*ix],'selected seed own ordering key arithmetic')
        expected_baselines={side:sum((rows[full[1]][side+'_q8'][k]-rows[full[0]][side+'_q8'][k])**2 for k in (0,1)) for side in ('source','reference')}
        need(seed['seed_baseline_squared_q8']==expected_baselines,'actual seed baseline lengths')
        summaries.append(summary)
    cg=dict(candidate_exists=seed is not None,minimum_12=len(current)>=12,at_least_half=2*len(current)>=len(cal),selected_count=len(current),calibration_count=len(cal))
    need(t['calibration_gate']==cg,'independent minimum versus half-support calibration gates')
    gates=[gate('too few total mutual landmarks',True),gate('too few calibration landmarks',True),gate('no majority landmark consensus',all(cg[k] for k in ('candidate_exists','minimum_12','at_least_half')))]
    expected_return=None;fit_failure=None;visited=0;finish=None;last_map=None
    def fit_once(ids,iteration,seen_count,coordinate_signature,line):
        nonlocal visited,last_map,fit_failure
        need(visited<len(steps),'missing actually visited fit attempt');step=steps[visited];ordinal=visited;visited+=1
        need(step['calibration_input_ordinals']==ids and step['original_caller_state']==dict(callsite_line=line,loop_index=iteration,seen_signature_count=seen_count,current_coordinate_signature=[list(x) for x in coordinate_signature]),'visited fit input and original loop state')
        predicted=None if len(ids)<2 else retained_refinement([rows[i] for i in ids])
        if predicted is None:
            message='similarity fit needs at least two landmarks' if len(ids)<2 else 'landmark geometry is singular'
            expected_error=dict(type='ContractError',code=CODE,message=CODE+': '+message)
            need(step['status']=='FAILED' and step['candidate'] is None and step['error']==expected_error,'failed visited fit retained without map')
            fit_failure=message;return None
        need(step['status']=='RETURNED' and step['error'] is None,'successful visited fit')
        summary,values=candidate(step['candidate'],rows,'visited-refinement-'+str(ordinal),predicted,ids)
        summaries.append(summary);last_map=predicted
        return [i for i in cal if values[i]<=R2]
    if not gates[-1]['passed']:
        need(steps==[] and t['final'] is None,'failed seed gate has no visited refinement/final')
        expected_return=refusal('no majority landmark consensus');finish='CALIBRATION_GATE_REFUSED'
    else:
        seen=set();stable=False;coordinate_signature=();iteration=None
        for iteration in range(8):
            coordinate_signature=tuple(coords(rows[i]) for i in current)
            if coordinate_signature in seen:
                finish='COORDINATE_SIGNATURE_CYCLE';break
            seen.add(coordinate_signature)
            updated=fit_once(current,iteration,len(seen),coordinate_signature,REF_LINES[0])
            if fit_failure:break
            row_key=lambda i:(*coords(rows[i]),rows[i]['digest'])
            if list(map(row_key,updated))==list(map(row_key,current)):
                stable=True;finish='STABLE_REFINEMENT';break
            current=updated
        if not stable and not fit_failure:
            if finish is None:finish='EIGHT_ITERATIONS_THEN_FINAL_FIT'
            fit_once(current,iteration,len(seen),coordinate_signature,REF_LINES[1])
        need(visited==len(steps)<=9,'exact original visited-fit prefix, no unvisited fits')
        if fit_failure:
            need(t['final'] is None,'failed fit has no choose return')
            expected_return=refusal(fit_failure);finish='VISITED_FIT_REFUSED'
        else:
            need(t['final'] is not None,'actual choose return retained')
            summary,values=candidate(t['final'],rows,'actually-returned-by-choose',last_map,current);summaries.append(summary)
            inside=[i for i in held if values[i]<=R2];minimum=len(inside)>=12;half=2*len(inside)>=len(held)
            gates.append(gate('held-out landmarks lack a majority consensus',minimum and half,minimum_12=minimum,at_least_half=half,selected_count=len(inside),holdout_count=len(held)))
            if not gates[-1]['passed']:expected_return=refusal(gates[-1]['message'])
            else:
                total=sum(values[i] for i in inside);rms=math.sqrt(total/len(inside))/(XY*Q);message=f'held-out residual RMS {rms:.9f} px exceeds 1.0'
                rms_ok=total<=len(inside)*(XY*Q)**2;gates.append(gate(message,rms_ok))
                if not rms_ok:expected_return=refusal(message)
                else:
                    det=last_map['a']**2+last_map['b']**2;need(det>0,'returned private map nonsingular');maximum=max(values[i] for i in inside);ceiling=math.isqrt(maximum//det)
                    if ceiling*ceiling*det<maximum:ceiling+=1
                    metrics=dict(mutual_match_count=len(rows),calibration_count=len(cal),calibration_inlier_count=len(current),holdout_count=len(held),holdout_inlier_count=len(inside),heldout_rms_reference_px=f'{rms:.9f}',heldout_max_source_px_ceil_q8=ceiling,coordinate_quantization_guard_q8=1,valid_support_continuous_margin_q8=128+ceiling+1)
                    expected_return=dict(status='RETURNED',transform=last_map,metrics=metrics,guard=ceiling+1,error=None)
    need(t['gates']==gates and all(type(g['passed']) is bool for g in t['gates']),'every actually visited gate and exact predicate')
    need(t['signature']==expected_return,'exact retained-path return/refusal reconstructed')
    if cached is not None:need(expected_return==signature(cached),'unchanged current actual return/refusal cache')
    return dict(seed_counts=counts,calibration_gate=cg,visited_refinement_count=len(steps),refinement_stop=finish,gates=gates,signature=expected_return,candidates=summaries,global_seed_optimality_independently_reenumerated=False)


IDS=['private-false-counterexample','private-true-known-map','within-split-association-destroyer','restored-private-true']
COMPARISON_METHOD='entire registrar return/refusal or trace; exact canonical bytes'


def blob_digest(a,value):
    raw=a.canonical(value);return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def comparison(a,got,label,left,right=None):
    need(set(got)=={'label','equal','left','right','method'} and got['label']==label and got['method']==COMPARISON_METHOD and type(got['equal']) is bool,'typed actual observer comparison')
    need(got['left']==blob_digest(a,left),'on/retained operand complete canonical digest')
    if right is not None:need(got['right']==blob_digest(a,right),'independent complete actual/cache operand')
    else:
        need(set(got['right'])=={'bytes','sha256'} and integer(got['right']['bytes']) and got['right']['bytes']>0,'off/placebo opaque actual operand extent');a.hv(got['right']['sha256'])
    need(got['equal'] is (got['left']==got['right']),'reported byte equality agrees with saved hashes/extents')
    return got['equal']


def triplet(a,checks,on,cached):
    need(len(checks)==3,'both observer comparisons and actual cache comparison')
    return [comparison(a,checks[0],'on-vs-off',on),comparison(a,checks[1],'on-vs-placebo',on),comparison(a,checks[2],'on-vs-actual-cache',on,signature(cached))]


def literal_check(a,got,rows,returned=None,permuted=False):
    truth=dict(a=0,b=Q,tx=3071*Q,ty=0);label='literal-truth-on-permuted-pairings' if permuted else 'independent-literal-rotation-truth'
    summary,values=candidate(got,rows,label,truth)
    summary['all_rows_literal_truth']=a.true_rotation_landmarks(rows)
    if returned is not None:
        corners=[]
        for c in a.corners(returned['transform']):
            # The helper reduces its rational; the producer saves Q32**2.
            scale=(Q*Q)//c['squared_error_denominator'];num=c['squared_error_numerator']*scale
            corners.append(dict(source_native=c['source'],squared_numerator=num,squared_denominator=Q*Q,within_one_native=num<=Q*Q))
        need(got['returned_map_known_corners']==corners,'literal integer corners against returned private map')
        summary['returned_map_known_corners']=corners
    return summary,values


def controls_and_pairs(a,w,pairs,arms):
    indexes=w['controls'];need([x['id'] for x in indexes]==IDS[:len(indexes)] and 0<len(indexes)<=4,'fixed private control prefix')
    controls=[];summaries=[];true_rows=true_trace=None;replays=0
    for i,index in enumerate(indexes):
        ref=index['record'];need(a.path(ref)==OUT/'worker'/(IDS[i]+'.json'),'private control record path')
        record=a.read(ref);need(record['id']==index['id'] and record['passed'] is index['passed'] and type(record['passed']) is bool,'private control index/disposition')
        if i<2:
            need(a.same(record['cached'],arms[i]['ref']),'actual private arm association');cached=arms[i]['record']['outcome'];rows=cached['landmarks']
            summary=trace_check(a,record['trace'],rows);equalities=triplet(a,record['comparisons'],record['trace']['signature'],cached);replays+=3
            returned=record['trace']['signature']['status']=='RETURNED';literal=None
            if returned:
                literal,values=literal_check(a,record['literal_truth'],rows,record['trace']['signature']);within=sum(v<=R2 for v in values);corners_ok=all(c['within_one_native'] for c in literal['returned_map_known_corners'])
            else:need(record['literal_truth'] is None,'refused private replay has no returned-map oracle');within=None;corners_ok=False
            passed=all(equalities) and returned and (corners_ok if i else not corners_ok)
            passed=passed and (within*2>=len(rows) if i else within==0)
            if i:true_rows,true_trace=rows,record['trace']
            details=dict(trace=summary,literal_truth=literal,comparisons=record['comparisons'])
        elif i==2:
            need(true_rows is not None,'private permutation follows true arm');rows=[dict(r) for r in true_rows];mapping=[]
            for parity in (0,1):
                slots=list(range(parity,len(rows),2))
                key=lambda i:hashlib.sha256(b'M193C-REFUSAL-TRACE-PERMUTE-V1'+bytes([0,parity])+i.to_bytes(4,'big')+bytes.fromhex(true_rows[i]['digest'])).digest()
                order=sorted(slots,key=key)
                for target,source in zip(slots,order):rows[target]['source_q8']=list(true_rows[source]['source_q8']);mapping.append([target,source])
            changed=sum(r['source_q8']!=z['source_q8'] for r,z in zip(true_rows,rows))
            marginal=[sorted(tuple(r['source_q8']) for r in true_rows[k::2])==sorted(tuple(r['source_q8']) for r in rows[k::2]) for k in (0,1)]
            need(record['permutation']==mapping and record['changed_pairings']==changed and record['marginals_preserved']==marginal and record['digest_semantics']=='Original row-order/split labels retained under explicit metadata fault; these are not rematched/rehashed landmark digests','exact declared within-split fault and restored marginals')
            summary=trace_check(a,record['trace'],rows);literal,values=literal_check(a,record['literal_truth'],rows,permuted=True);replays+=1
            passed=changed>0 and all(marginal) and record['trace']['signature']['status']=='REGISTRATION_REFUSED' and sum(v<=R2 for v in values)*2<len(rows)
            details=dict(trace=summary,literal_truth=literal,changed_pairings=changed,permutation_reconstructed=True,marginals_preserved=marginal)
        else:
            summary=trace_check(a,record['trace'],true_rows);checks=record['comparisons'];need(len(checks)==1,'entire restored trace predicate')
            passed=comparison(a,checks[0],'entire-restored-vs-true-trace',record['trace'],true_trace);replays+=1
            details=dict(trace=summary,comparisons=checks)
        need(record['passed'] is passed,'control predicate independently reconstructed')
        summaries.append(dict(id=IDS[i],passed=passed,record=ref,**details));controls.append(record)
        if not passed:need(i==len(indexes)-1,'no private continuation after failed control')
    all_controls=len(controls)==4 and all(r['passed'] for r in controls)
    need(all_controls or w['pairs']==[],'no real replay after private control refusal')
    real=[]
    for i,index in enumerate(w['pairs']):
        need(i<23 and index['pair']==pairs[i]['record']['pair'],'same real ordered pair prefix');ref=index['record']
        need(a.path(ref)==OUT/'worker'/(index['pair']['id']+'.json'),'real trace record path');record=a.read(ref)
        need(record['schema']=='m193c-saved-refusal-trace-record-v1' and record['pair']==index['pair'] and a.same(record['input'],pairs[i]['ref']) and record['qualification']==QUALIFICATION and record['saved_landmark_digest_semantics']=='Producer witness; descriptors absent, no digest recomputation, rematching or split change','actual real record identity and scope')
        cached=pairs[i]['record']['outcome'];summary=trace_check(a,record['trace'],cached['landmarks']);equalities=triplet(a,record['comparisons'],record['trace']['signature'],cached);replays+=3
        passed=all(equalities) and record['trace']['signature']['status']=='REGISTRATION_REFUSED'
        need(record['passed'] is index['passed'] is passed,'actual real reproduction disposition')
        real.append(dict(pair=index['pair'],record=ref,input=record['input'],passed=passed,trace=summary,comparisons=record['comparisons']))
        if not passed:need(i==len(w['pairs'])-1,'no real continuation after failed reproduction')
    need(integer(w['registrar_replay_attempts']) and replays==w['registrar_replay_attempts']<=77,'completed saved replay count; no unrecorded extra invocation')
    need(w['unvisited']==list(range(len(real),23)),'exact unvisited real suffix')
    return dict(all_four_pass=all_controls,rows=summaries,unvisited=IDS[len(indexes):]),real,replays


ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=1<<20,metadata_bytes=1<<20)
COMPLETE='COMPLETE_SAVED_REFUSAL_TRACE_ONLY'


def main():
    global REF_LINES
    cpu,wall=time.process_time(),time.perf_counter();parser=argparse.ArgumentParser()
    for key in ('plan','result','outer','console','exit'):parser.add_argument('--'+key+'-sha256',required=True)
    args=parser.parse_args();a,helper_path=helpers();commissioned=commissioning()+a.commissioning()
    paths=dict(plan=HERE/'refusal-trace-plan-1.json',result=OUT/'result.json',outer=HERE/'work/refusal-trace-1-outer.json',console=HERE/'work/refusal-trace-1-console.txt',exit=HERE/'work/refusal-trace-1-exit.txt')
    refs={}
    for key,path in paths.items():refs[key]=a.file(path);need(refs[key]['sha256']==getattr(args,key+'_sha256'),'actual external '+key)
    plan,parent,outer=(a.read(refs[k]) for k in ('plan','result','outer'));final=a.strict(a.path(refs['console']).read_bytes().splitlines()[-1]);code=int(a.path(refs['exit']).read_bytes().strip())
    need(set(plan)==set('schema source_bindings real_baseline prior_work preparation_allowance python_executable commands'.split()) and plan['schema']=='m193c-refusal-trace-plan-v1','closed saved-trace plan')
    for relative,pin in plan['source_bindings'].items():a.file(ROOT/relative,dict(path=relative,**pin))
    for name,pin in (('refusal-trace-run.py',RUNNER),('work/real-precise-refusal-diagnostic-preregister.md',SPEC)):
        r=a.file(HERE/name);need((r['bytes'],r['sha256'])==pin,'held numerical/source specification')
    reference=ROOT/'experiments/M193-cover-overlap/reference.py';rr=a.file(reference)
    need(rr['sha256']=='c08340f6f0658fae048dda92629a543b5a539462a93db196aaae29e1862ba790','immutable original registrar')
    tree=ast.parse(reference.read_bytes());choose=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='choose_similarity')
    REF_LINES=sorted(x.lineno for x in ast.walk(choose) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='exact_similarity_fit');need(len(REF_LINES)==2,'original loop/fallback callsite inventory')
    baseline,pairs,arms=real_baseline(a,plan);prior=a.read(plan['prior_work']);need(plan['preparation_allowance']==ALLOWANCE,'whole new preparation allowance')
    for key,value in ALLOWANCE.items():need(D(str(prior[key]))==D(baseline['next_wall_seconds'] if key=='wall_seconds' else str(baseline['actual_final_work'][key]))+value,'full no-refund carry')
    need(prior==dict(cpu_seconds=577.75,wall_seconds=684.0280850,file_bytes=3963171268,metadata_bytes=37970622),'literal next prior')
    py=a.file(a.path(plan['python_executable']),plan['python_executable']);base=[py['path'],'-B','-X','faulthandler','-X'];script=str(HERE/'refusal-trace-run.py')
    pc=base+['pycache_prefix='+str(OUT/'parent-cache'),script,'--plan',str(paths['plan']),'--sha256',refs['plan']['sha256'],'--output',str(OUT)]
    frozen=[refs['plan']['sha256'] if x=='ACTUAL_PLAN_SHA256' else x for x in plan['commands']['parent']]
    need(set(plan['commands'])=={'parent','worker'} and pc==frozen==parent['command']==outer['command'] and a.same(parent['plan'],refs['plan']),'independent exact actual parent argv')
    need(set(outer)==set('scope command plan_sha256 exit_code elapsed_wall_seconds admissible_parent_exit'.split()) and outer['plan_sha256']==refs['plan']['sha256'] and integer(outer['exit_code']) and outer['exit_code']==code and outer['admissible_parent_exit'] is (code==0),'actual outer/exit association')
    need(parent['schema']=='m193c-refusal-trace-run-v1' and parent['source_bindings']==plan['source_bindings'] and parent['prior_work']==prior and parent['qualification']==QUALIFICATION and parent['sources_unchanged'] is True and parent['finalization_errors']==[],'parent final source association')
    need(final['status']==parent['status'] and final['error']==parent['error'] and final['finalization_errors']==parent['finalization_errors'] and Path(final['result']).resolve()==OUT/'result.json','parent terminal publication')
    need(parent['request'] is not None and parent['worker_result'] is not None and parent['child'] is not None,'actual saved-replay worker exists')
    request=a.read(parent['request']);w=a.read(parent['worker_result']);child=parent['child']
    need(set(request)==set('schema plan prior_work pair_refs private_refs'.split()) and request['schema']=='m193c-refusal-trace-request-v1' and a.same(request['plan'],refs['plan']),'closed actual saved-metadata request')
    need(request['pair_refs']==[r['ref'] for r in pairs] and request['private_refs']==[r['ref'] for r in arms] and all(request['prior_work'][k]>=prior[k] for k in prior),'exact 23/two inputs and charged setup')
    wc=base+['pycache_prefix='+str(OUT/'worker-cache'),script,'--plan',str(paths['plan']),'--sha256',refs['plan']['sha256'],'--output',str(OUT/'worker'),'--worker','--request',str(OUT/'request.json'),'--request-sha256',parent['request']['sha256']]
    frozen=[refs['plan']['sha256'] if x=='ACTUAL_PLAN_SHA256' else parent['request']['sha256'] if x=='ACTUAL_REQUEST_SHA256' else x for x in plan['commands']['worker']]
    need(wc==frozen==child['command']==w['command'],'independent exact actual worker argv')
    need(w['schema']=='m193c-refusal-trace-worker-v1' and w['plan']==parent['plan'] and w['request']==parent['request'] and w['source_bindings']==plan['source_bindings'] and w['prior_work']==prior and w['qualification']==QUALIFICATION and w['sources_unchanged'] is True and w['finalization_errors']==[],'worker source/request/final checks')
    need(parent['removed_environment']==sorted(set(parent['removed_environment'])) and not (OUT/'parent-cache').exists() and not (OUT/'worker-cache').exists(),'saved clean environment/no bytecode output')
    need(parent['runtime']==w['runtime']==dict(python=sys.version,executable=py['path'],pointer_bits=64),'exact pinned metadata runtime')
    for obj in (parent,w):need(all(integer(obj[k]) and obj[k]==0 for k in ('image_decodes','feature_extractions','descriptor_matcher_calls')),'zero image/detector/descriptor-matcher counters')
    controls,records,replays=controls_and_pairs(a,w,pairs,arms);complete=parent['status']==COMPLETE
    if complete:
        need(controls['all_four_pass'] and len(records)==23 and all(r['passed'] for r in records) and replays==77 and w['status']==COMPLETE and parent['error'] is w['error'] is None and code==child['exit_code']==0,'complete actual 77 replay population')
        need(w['active'] is parent['active'] is None and all(parent[k]==w[k] for k in ('controls','pairs','unvisited','registrar_replay_attempts')),'complete published child results copied to parent')
    else:
        failed=records[-1]['pair']['id'] if records else controls['rows'][-1]['id']
        need(parent['status']==w['status']=='REFUSED' and code==child['exit_code']==1 and parent['error'] is not None and w['error'] is not None and w['active']==failed,'named saved control/reproduction refusal')
        need((records and records[-1]['passed'] is False) or (not records and controls['rows'][-1]['passed'] is False),'no silently complete partial prefix')
        need(parent['controls']==parent['pairs']==[] and parent['registrar_replay_attempts']==0 and parent['unvisited']==list(range(23)),'failed worker not copied as complete parent')
    need(child['error'] is None and child['cleanup_errors']==[] and child['terminal_job_accounting'] is True and child['direct_exit_observed'] is True and child['pipe_eof_observed'] is True and child['job_accounting']['active_processes']==0 and child['termination']['attempted'] is False and child['post_exit_drain']['completed'] is True,'terminal Job without kill/helper error')
    account=child['job_accounting'];need(all(integer(account[k]) for k in ('total_cpu_100ns','total_user_100ns','total_kernel_100ns','active_processes')) and account['total_cpu_100ns']==account['total_user_100ns']+account['total_kernel_100ns'],'complete CPU components')
    log=a.file(OUT/'worker.log');need(child['log_bytes']==log['bytes'] and (child.get('log') is None or a.same(child['log'],log)),'actual worker log')
    terminal=a.strict(a.path(log).read_bytes().splitlines()[-1]);need(terminal['status']==w['status'] and terminal['error']==w['error'] and terminal['finalization_errors']==w['finalization_errors'] and Path(terminal['result']).resolve()==OUT/'worker/result.json','worker terminal association')
    need(final['cpu_accounting_complete'] is True and parent['work']['cpu_accounting_complete'] is True and terminal['cpu_accounting_complete'] is True and w['work']['cpu_accounting_complete'] is True,'actual complete terminal CPU accounting')
    inventory=a.all_inventory();total=sum(r['bytes'] for r in inventory);work=final['work_through_final_checks']
    need(parent['work']['snapshot_bytes']==w['work']['snapshot_bytes']==0 and work['file_bytes']-prior['file_bytes']==work['metadata_bytes']-prior['metadata_bytes']==total,'no snapshots; exact output byte charge')
    need(parent['work']['new_extent_bytes']+refs['result']['bytes']==total,'prepublication extent plus canonical result')
    need(D(str(work['cpu_seconds']))-D(str(prior['cpu_seconds']))>=D(account['total_cpu_100ns'])/10000000,'whole Job CPU charged')
    limits=child['limits'];caps={k:D(str(work[k]))-D(str(prior[k]))<=v for k,v in dict(cpu_seconds=300,wall_seconds=480,file_bytes=8<<20,metadata_bytes=8<<20).items()}
    need(all(D(str(work[k]))>=D(str(prior[k])) for k in prior),'no refund')
    caps['global']=work['cpu_seconds']<=1200 and work['wall_seconds']<=1800 and work['file_bytes']<=4*(1<<30) and work['metadata_bytes']<=128*(1<<20)
    caps['child_cpu']=account['total_cpu_100ns']/1e7<=limits['cpu_seconds']<=300;caps['child_wall']=child['wall_seconds']<=limits['wall_seconds']<=240
    caps['child_memory']=child['job_memory']['peak_job_memory_used_bytes']<=limits['committed_bytes']==8*(1<<30);caps['child_log']=log['bytes']<=limits['log_bytes']<=1<<20
    need(child['configured_job_limits']['committed_bytes']==limits['committed_bytes'] and all(caps.values()),'actual process/local/global caps')
    helper=a.file(helper_path);need((helper['bytes'],helper['sha256'])==HELPER,'held independent helper unchanged')
    for ref in list(a.USED.values()):a.file(a.path(ref),ref)
    result=dict(schema='m193c-saved-refusal-trace-audit-v1',status='PASS_SAVED_REFUSAL_TRACE_OUTCOME_AUDIT',subject_complete=complete,subject_status=parent['status'],worker_status=w['status'],refused_control=None if complete else w['active'],external=refs,worker_result=parent['worker_result'],audit_source=a.file(__file__),pure_helper_source=helper,real_baseline=plan['real_baseline'],qualification=QUALIFICATION,controls=controls,pairs=records,registrar_replay_attempts=replays,unvisited=w['unvisited'],image_decodes=0,feature_extractions=0,descriptor_matcher_calls=0,commissioning=commissioned,actual_final_work=work,next_wall_seconds=str(D(str(prior['wall_seconds']))+D(str(outer['elapsed_wall_seconds']))),cpu_accounting_complete=True,job=child,caps=caps,inventory=inventory,inventory_total_bytes=total,unique_hashed_metadata_files=len(a.USED),subject_errors=dict(parent=parent['error'],worker=w['error']),finalization_errors=dict(parent=parent['finalization_errors'],worker=w['finalization_errors']),audit_timing=dict(cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall),scope='Saved metadata only. No image payload/stat reads, detector/matcher calls, numerical-subject imports, unvisited refinement or second exhaustive hypothesis search. Independent integer coefficients/residuals verify only selected seeds and actually visited refinements. Entire held-out populations are descriptive, not physical cause/truth. Global seed optimality is not independently reenumerated; pinned loop/key coverage, seed census and actual observer hashes provide partial assurance.')
    encoded=json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False).encode();need(len(encoded)<=120*(1<<10) and len(encoded)+Path(__file__).stat().st_size+12*(1<<10)<=196*(1<<10),'bounded entire audit reservation');print(encoded.decode())

if __name__=='__main__':main()
