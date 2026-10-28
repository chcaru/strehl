"""No-fit audit of the complete saved original-CFA reconstruction."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import struct
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RUN=ROOT/"outputs/raw-quality-2026-10-27/direct-cfa-streamed-full-photograph-1/output"
PINS={HERE/"full-photograph.py":"9c69386259c2b508c059e867af7ec1bc45c88803476b85e9f45451a62cf90458",
      RUN/"fit/result.json":"e3a3a79fd1e81ef962de899990b4a7f00d7dc8c55167d06f16d9fa30225d11f3",
      RUN/"constructor.json":"dd445d04244b7c1b1f91032110bfc6ba1d8814fa207cea9c53c9c6f3ed5a0de0",
      RUN/"receipt.json":"3fcb652ca1e8d5572b0a9449994eea2d54d796ee5ff2117949c037d0559d11ea"}
LIMIT=8<<30
FORWARD_MAX,FORWARD_RMS,DOT_BAR=1e-5,2e-6,3e-6
OBJECTIVE_REL,OBJECTIVE_ABS=5e-5,1e-7
PATCHES=((0,0),(7028,0),(0,4684),(7028,4684),(3516,2344),(1988,794),(4592,2608))


def require(ok,message):
    if not ok: raise ValueError(message)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""): h.update(block)
    return h.hexdigest()


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    exec(compile(Path(path).read_bytes(),str(path),"exec"),module.__dict__)
    return module


def comparison(t,actual,expected):
    require(actual.shape==expected.shape,"comparison shape differs")
    require(bool(t.isfinite(actual).all() & t.isfinite(expected).all()),"nonfinite comparison")
    difference=actual-expected
    maximum=float(difference.abs().max())
    rms=float(t.sqrt(difference.square().mean(dtype=t.float32)))
    maxscale=max(1.,float(expected.abs().max()))
    rmsscale=max(1.,float(t.sqrt(expected.square().mean(dtype=t.float32))))
    return dict(max_abs=maximum,rms=rms,reference_max_scale=maxscale,reference_rms_scale=rmsscale,
                normalized_max=maximum/maxscale,normalized_rms=rms/rmsscale,
                passed=maximum/maxscale<=FORWARD_MAX and rms/rmsscale<=FORWARD_RMS)


def reconcile(actual,expected,absolute=OBJECTIVE_ABS):
    allowance=absolute+OBJECTIVE_REL*max(abs(expected),1e-12)
    return dict(actual=actual,expected=expected,difference=actual-expected,
                allowed_abs=allowance,passed=abs(actual-expected)<=allowance)


def haar_controls(t,np,cpu,bands,normal,codes):
    current=bands.prepare_source(t,codes,(0,0),NOISE,collect_evidence=False)
    plan=current.plan
    require(all(len(s)==8 for s in plan.sizes),"actual full7-level plan required")
    original=current.observed.cpu().contiguous()
    reference=cpu.HaarPlan((4688,7032),(0,0))
    require(reference.bands==plan.bands and reference.sizes==plan.sizes,"full Haar layouts differ")
    cpu_coefficients=reference.forward(original)
    reference_gpu=cpu_coefficients.to("cuda:0")
    parity=[]
    for b in plan.bands:
        a,z=b["start"],b["end"]
        row=dict(phase=b["phase"],level=b["level"],kind=b["kind"],shape=list(b["shape"]),
                 comparison=comparison(t,current.d[a:z],reference_gpu[a:z]))
        indices=sorted(set((a,(a+z-1)//2,z-1)))
        row["fixed_first_middle_last"]=[dict(index=i,cpu=float(cpu_coefficients[i]),
                                              gpu=float(current.d[i])) for i in indices]
        parity.append(row)
    roundtrip=comparison(t,plan.inverse(current.d),current.observed)
    # Independent coefficient vector traverses the actual transpose, not H(y).
    dual=((t.arange(plan.count,device="cuda:0",dtype=t.int32)%17).to(t.float32)-8.)/8.
    gpu_inverse=plan.inverse(dual)
    cpu_inverse=reference.inverse(dual.cpu()).to("cuda:0")
    inverse_parity=comparison(t,gpu_inverse,cpu_inverse)
    lhs=normal.stable_dot(t,current.d,dual)
    rhs=normal.stable_dot(t,current.observed,gpu_inverse)
    scale=(t.sqrt(current.d.square().sum(dtype=t.float32))*t.sqrt(dual.square().sum(dtype=t.float32))
           +t.sqrt(current.observed.square().sum(dtype=t.float32))*t.sqrt(gpu_inverse.square().sum(dtype=t.float32)))
    dot_error=float((lhs-rhs).abs()/scale.clamp_min(1))
    parseval=float((current.d.square().sum()-current.observed.square().sum()).abs()
                   /current.observed.square().sum().clamp_min(1))
    odd=[dict(phase=p,level=k,input_hw=list(hw),odd_y=bool(hw[0]&1),odd_x=bool(hw[1]&1))
         for p,sizes in enumerate(plan.sizes) for k,hw in enumerate(sizes[:-1]) if hw[0]&1 or hw[1]&1]
    result=dict(shape=[4688,7032],phase_sizes=plan.sizes,odd_carry_levels=odd,
                coefficient_parity=parity,roundtrip=roundtrip,transpose_parity=inverse_parity,
                dot=dict(lhs=float(lhs),rhs=float(rhs),normalized_error=dot_error,bar=DOT_BAR,passed=dot_error<=DOT_BAR),
                parseval=dict(relative_error=parseval,bar=DOT_BAR,passed=parseval<=DOT_BAR))
    result["passed"]=(roundtrip["passed"] and inverse_parity["passed"] and dot_error<=DOT_BAR
                       and parseval<=DOT_BAR and all(r["comparison"]["passed"] for r in parity))
    del current,reference_gpu,dual,gpu_inverse,cpu_inverse,cpu_coefficients,original
    return result


def sparse_controls(t,np,cpu,measurement_module,measurement,x,latent_cpu,geometry,field_hw):
    # Invoke frozen _matrix once per source. It allocates a sparse transpose CSR
    # row pointer (~800MB), immediately discarded; no dense CPU operator exists.
    yy,xx=np.mgrid[:4,:4]
    xy=np.concatenate([np.stack((xx+ox,yy+oy),axis=-1).reshape(-1,2) for ox,oy in PATCHES]).astype(np.int32)
    axis=np.asarray([-math.sqrt(3/5)/2,0,math.sqrt(3/5)/2],dtype=np.float64)
    offsets=np.asarray([(a,b) for b in axis for a in axis],dtype=np.float64)
    one=np.asarray([5/18,4/9,5/18],dtype=np.float64)
    weights=np.outer(one,one).reshape(9).astype(np.float32)
    phase=((xy[:,1]&1)*2+(xy[:,0]&1)).astype(np.uint8)
    channels=np.asarray([0,1,1,2],dtype=np.int64)[phase]
    wrong=measurement_module.MeasurementGpu(t,field_hw,device_limit_bytes=LIMIT,
                                            diagnostic_channel_map=(2,1,1,0))
    # Fixed full-field sentinel commissions both foils even where saved X is flat.
    sy=t.arange(field_hw[0],device="cuda:0",dtype=t.float32)[:,None]
    sx=t.arange(field_hw[1],device="cuda:0",dtype=t.float32)[None,:]
    sentinel=t.empty_like(x)
    sentinel[...,0]=2000+sx/4+sy/8
    sentinel[...,1]=4000-sx/8+sy/4
    sentinel[...,2]=1000+sx/2-sy/8
    sentinel_cpu=sentinel.cpu().contiguous()
    latent_tensor=t.from_numpy(latent_cpu)
    rows=[]
    for source_id in (0,149):
        affine=np.asarray(geometry["maps"][source_id]["source_to_latent_2x3"],dtype=np.float64)
        nodes=(xy[:,None,:].astype(np.float64)+offsets[None,:,:])@affine[:,:2].T+affine[:,2]
        matrix,transpose=cpu._matrix(nodes,weights,channels,field_hw)
        del transpose
        reference=t.sparse.mm(matrix,latent_tensor.reshape(-1,1))[:,0]
        reference_sentinel=t.sparse.mm(matrix,sentinel_cpu.reshape(-1,1))[:,0]
        actual=[];sent=[];wrong_phase=[];wrong_origin=[]
        moved=affine.copy();moved[:,2]+=affine[:,0] # +1 original x, phase held fixed.
        for patch_index,(ox,oy) in enumerate(PATCHES):
            rect=(ox,oy,4,4)
            actual.append(measurement.forward(x,rect,affine).reshape(-1))
            sent.append(measurement.forward(sentinel,rect,affine).reshape(-1))
            wrong_phase.append(wrong.forward(sentinel,rect,affine).reshape(-1))
            if patch_index>=4:
                wrong_origin.append(measurement.forward(sentinel,rect,moved).reshape(-1))
        actual=t.cat(actual).cpu();sent=t.cat(sent).cpu()
        p=comparison(t,actual,reference);s=comparison(t,sent,reference_sentinel)
        phase_foil=comparison(t,t.cat(wrong_phase).cpu(),reference_sentinel)
        origin_foil=comparison(t,t.cat(wrong_origin).cpu(),reference_sentinel[4*16:])
        rows.append(dict(source_id=source_id,xy=xy.tolist(),physical_phase=phase.tolist(),
                         saved_X_actual=actual.tolist(),saved_X_cpu=reference.tolist(),saved_X=p,
                         sentinel=s,wrong_phase=phase_foil,shifted_origin=origin_foil,
                         shifted_origin_indices=list(range(4*16,len(xy))),
                         passed=p["passed"] and s["passed"] and not phase_foil["passed"] and not origin_foil["passed"]))
        del matrix,reference,reference_sentinel
    runtime=wrong.metadata(strict=True)
    del sentinel,sentinel_cpu,latent_tensor,wrong
    return dict(rows=rows,passed=all(r["passed"] for r in rows),foil_runtime=runtime,
                sparse_pixels_per_source=len(xy),no_cropped_or_rebased_latent=True)


SUM_FIELDS=("sum_q","observed_energy","predicted_energy","observed_predicted_cross",
            "raw_error_energy","variance_normalized_error_energy","weighted_error_energy",
            "initial_predicted_energy","initial_raw_error_energy","initial_variance_normalized_error_energy",
            "initial_weighted_error_energy","T_energy","T_rhs_cross","partial_support_sum_q",
            "partial_support_T_energy","boundary_admission_sum_q","boundary_admission_T_energy")


def source_budget(t,bands,current,predicted,initial,dc,factor):
    plan=current.plan
    d=current.d
    pred=plan.forward(predicted);base=plan.forward(initial);dc_coeff=plan.forward(dc)
    weighted_rhs=factor*d
    residual=weighted_rhs-factor*pred
    initial_residual=weighted_rhs-factor*base
    column=factor*dc_coeff
    scalars=[];identities=[]
    for band in plan.bands:
        a,z=band["start"],band["end"]
        valid=current.valid_coeff[a:z]
        support=current.support_coeff[a:z]
        q=current.metric[a:z]
        actual=d[a:z];fitted=pred[a:z];start=base[a:z]
        variance=current.variance[a:z]
        error=actual-fitted;initial_error=actual-start
        mask=valid.to(t.float32)
        zero=t.zeros((),dtype=t.float32,device="cuda:0")
        qmin=t.where(valid,q,t.full_like(q,float("inf"))).min()
        # Nominal support boundaries include all earlier odd carries; actual
        # coefficient geometry is retained, not rebased to a small test image.
        s=1<<((band["level"]+1) if band["kind"]!="LL" else band["level"])
        h,w=plan.sizes[band["phase"]][0]
        bh,bw=band["shape"]
        partial=((t.arange(bh,device="cuda:0")[:,None]+1)*s>h)|((t.arange(bw,device="cuda:0")[None,:]+1)*s>w)
        risk=(~bands.window_all(t,~partial)) if band["kind"]!="LL" else partial
        partial=partial.reshape(-1).to(t.float32);risk=risk.reshape(-1).to(t.float32)
        sums=[q.sum(),(mask*actual.square()).sum(),(mask*fitted.square()).sum(),(mask*actual*fitted).sum(),
              (mask*error.square()).sum(),(mask*error.square()/variance).sum(),residual[a:z].square().sum(),
              (mask*start.square()).sum(),(mask*initial_error.square()).sum(),
              (mask*initial_error.square()/variance).sum(),initial_residual[a:z].square().sum(),
              column[a:z].square().sum(),(column[a:z]*weighted_rhs[a:z]).sum(),
              (partial*q).sum(),(partial*column[a:z].square()).sum(),
              (risk*q).sum(),(risk*column[a:z].square()).sum()]
        scalars.append(t.stack([valid.sum(dtype=t.float32),support.sum(dtype=t.float32),qmin,q.max(),*sums]))
        identities.append(dict(phase=band["phase"],level=band["level"],kind=band["kind"],
                               shape=list(band["shape"]),count=z-a,nominal_native_support=2*s))
    table=t.stack(scalars).cpu().tolist()
    rows=[]
    for identity,values in zip(identities,table):
        n,support=int(values[0]),int(values[1])
        row=dict(**identity,valid_count=n,support_invalid=identity["count"]-support,
                 omitted=identity["count"]-n,q_min=values[2] if n else None,q_max=values[3])
        row.update(zip(SUM_FIELDS,values[4:]));rows.append(row)
    return rows,residual,initial_residual


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    require(out.is_relative_to(ROOT/"outputs") and not out.exists(),"fresh workspace output required")
    out.mkdir(parents=True)
    for path,sha in PINS.items():require(digest(path)==sha,"bound prior source/result changed: "+str(path))
    worker=load(HERE/"full-photograph.py","budget_frozen_full_worker")
    save,read,record,stat=worker.save,worker.read,worker.record,worker.stat
    telemetry=worker.Telemetry(out/"telemetry.ndjson")
    started=time.perf_counter();source_count=0
    state=dict(status="STARTED_SAVED_X_BAND_BUDGET",complete=False,fit_calls=0,adjoint_calls=0,RAW_reads=0,
               quality_claim=False,photographic_admission=False)
    rows_file=(out/"per-source.ndjson").open("x",encoding="utf-8",newline="\n")
    try:
        fit,constructor,full=[read(RUN/n) for n in ("fit/result.json","constructor.json","receipt.json")]
        require(full["complete"] and full["status"]=="COMPLETE_DIRECT_CFA_FULL_PHOTOGRAPH"
                and full["source_count"]==299 and fit["iterations"]==64 and not fit["converged"],"actual refused full result required")
        evidence=fit["evidence"]
        require(evidence["source_count"]==299 and evidence["original_sensel_count"]==9856838784
                and evidence["metric_scale_f32"]==73572098048.0,"frozen factor authority differs")
        latent_path=worker.bind(full["latent"])
        require(fit["latent"]["sha256"]==full["latent"]["sha256"] and fit["latent"]["shape"]==[4743,7109,3],"latent joins differ")
        export,geometry,input_order=read(worker.CACHE),read(worker.GEOMETRY),read(worker.BASE/"input-order.json")
        worker.validate_export(export,geometry,input_order)
        paths=list(dict.fromkeys([*worker.PINNED,*PINS,Path(__file__),HERE/"band-budget-notes.md",latent_path,
                                 HERE.parent/"dual-tree-cfa-gpu/ordered-fir.py"]))
        bindings=[record(p) for p in paths];stats=[stat(p) for p in paths]
        for p,r in zip(paths,bindings):
            expected=PINS.get(p,worker.PINNED.get(p))
            require(expected is None or r["sha256"]==expected,"frozen source differs: "+str(p))
        save(out/"bindings-before.json",bindings)
        caches=[];cache_stats=[]
        for row in export["records"]:
            item={k:row["cache"][k] for k in ("path","sha256","bytes")}
            path=worker.bind(item)
            with path.open("rb") as f:require(struct.unpack("<4I",f.read(16))==(0,0,4688,7032),"cache header differs")
            caches.append(item);cache_stats.append(stat(path))
        save(out/"cache-bindings-before.json",caches)
        import numpy as np
        import torch as t
        t.set_num_threads(4);t.set_num_interop_threads(1);t.set_default_dtype(t.float32)
        t.backends.cuda.matmul.allow_tf32=False;t.backends.cudnn.allow_tf32=False
        require(t.cuda.is_available(),"CUDA required");t.cuda.set_device(0)
        properties=t.cuda.get_device_properties(0)
        t.cuda.set_per_process_memory_fraction(LIMIT/properties.total_memory,0);t.cuda.reset_peak_memory_stats(0)
        normal=load(HERE/"normal-operator.py","budget_frozen_normal")
        bands=normal.bands
        cpu=load(normal.CPU_PATH,"budget_frozen_cpu")
        paired=load(HERE/"measurement-paired.py","budget_frozen_paired")
        original_measurement=load(normal.MEASUREMENT_PATH,"budget_frozen_measurement")
        noise=export["noise"]
        global NOISE
        NOISE=bands.Noise(tuple(worker.f32(v) for v in noise["gain_bits4"]),
                          tuple(worker.f32(v) for v in noise["read_variance_bits4"]),
                          tuple(noise["black4"]),noise["white"])
        require(evidence["supplied_noise"]==dict(shot4=list(NOISE.shot4),read_variance_dn2_4=list(NOISE.read4),
                                                black4=list(NOISE.black4),saturation=NOISE.saturation),"noise authority mismatch")
        def codes(i):return np.memmap(caches[i]["path"],mode="r",dtype="<u2",offset=16,shape=(4688,7032))
        latent_cpu=np.memmap(latent_path,mode="r",dtype="<f4",shape=(*worker.FIELD_HW,3))
        x=t.from_numpy(latent_cpu).to(device="cuda:0",copy=True)
        require(bool(t.isfinite(x).all()),"saved X nonfinite")
        with t.inference_mode(),t.autocast(device_type="cuda",enabled=False):
            telemetry.emit("full-shape-Haar-start")
            h=haar_controls(t,np,cpu,bands,normal,codes(149));save(out/"haar-controls.json",h)
            require(h["passed"],"full-shape Haar fidelity failed")
            measurement=paired.PairedMeasurementGpu(t,worker.FIELD_HW,device_limit_bytes=LIMIT)
            telemetry.emit("sparse-full-field-measurement-start")
            m=sparse_controls(t,np,cpu,original_measurement,measurement,x,latent_cpu,geometry,worker.FIELD_HW)
            save(out/"measurement-controls.json",m);require(m["passed"],"full-field measurement fidelity/foil failed")
            constants=t.tensor(evidence["constant_initial_f32"],device="cuda:0",dtype=t.float32)
            constant_x=t.empty_like(x);constant_x.copy_(constants.reshape(1,1,3))
            final_total=normal.norm_pair(t,t.zeros(1,device="cuda:0"))
            initial_total=normal.norm_pair(t,t.zeros(1,device="cuda:0"))
            aggregates=None;max_q=0.;reductions=[]
            for i in range(299):
                tick=time.perf_counter()
                current=bands.prepare_source(t,codes(i),(0,0),NOISE,collect_evidence=False)
                factor=current.factors(evidence["metric_scale_f32"],evidence["original_sensel_count"])
                predicted=t.empty_like(current.observed);dc=t.empty_like(predicted);initial=t.empty_like(predicted)
                affine=geometry["maps"][i]["source_to_latent_2x3"]
                for y in range(0,4688,1048576//7032):
                    height=min(1048576//7032,4688-y);rect=(0,y,7032,height)
                    a,c=measurement.forward_with_dc(x,rect,affine)
                    predicted[y:y+height].copy_(a);dc[y:y+height].copy_(c)
                    initial[y:y+height].copy_(measurement.forward(constant_x,rect,affine))
                rows,residual,initial_residual=source_budget(t,bands,current,predicted,initial,dc,factor)
                expected=evidence["sources"][i]
                require(expected["source_id"]==i and len(rows)==len(expected["bands"]),"source/band census differs")
                for row,b in zip(rows,expected["bands"]):
                    require(all(row[k]==b[k] for k in ("phase","level","kind","support_invalid","omitted")),"support census differs")
                final_source=normal.norm_pair(t,residual);initial_source=normal.norm_pair(t,initial_residual)
                final_total=final_total.add(final_source);initial_total=initial_total.add(initial_source)
                checks=dict(final=reconcile(sum(r["weighted_error_energy"] for r in rows),final_source.receipt()["value_f32"]),
                            initial=reconcile(sum(r["initial_weighted_error_energy"] for r in rows),initial_source.receipt()["value_f32"]))
                require(all(v["passed"] for v in checks.values()),"perband/fullvector reduction mismatch")
                reductions.append(dict(source_id=i,**checks))
                max_q=max(max_q,max(r["q_max"] for r in rows))
                if aggregates is None:
                    aggregates=[dict(phase=r["phase"],level=r["level"],kind=r["kind"],nominal_native_support=r["nominal_native_support"],
                                     count=0,valid_count=0,support_invalid=0,omitted=0,q_min=None,q_max=0.,**{k:0. for k in SUM_FIELDS}) for r in rows]
                for aggregate,row in zip(aggregates,rows):
                    for k in ("count","valid_count","support_invalid","omitted"):aggregate[k]+=row[k]
                    for k in SUM_FIELDS:aggregate[k]+=row[k]
                    if row["q_min"] is not None:aggregate["q_min"]=row["q_min"] if aggregate["q_min"] is None else min(aggregate["q_min"],row["q_min"])
                    aggregate["q_max"]=max(aggregate["q_max"],row["q_max"])
                rows_file.write(json.dumps(dict(source_id=i,bands=rows,fullvector_final=final_source.receipt(),
                                               fullvector_initial=initial_source.receipt()),separators=(",",":"),allow_nan=False)+"\n")
                rows_file.flush();source_count=i+1
                del current,factor,predicted,dc,initial,residual,initial_residual,a,c
                telemetry.emit("source-complete",source_id=i,seconds=time.perf_counter()-tick)
            require(max_q==evidence["metric_scale_f32"],"actual all-source qmax differs")
            final_value=final_total.receipt()["value_f32"];initial_value=initial_total.receipt()["value_f32"]
            objective_checks=dict(final_saved=reconcile(final_value,evidence["restored_objective_scaled"]["value_f32"]),
                                  initial_saved=reconcile(initial_value,evidence["constant_initial_objective_scaled"]["value_f32"]),
                                  final_bands=reconcile(sum(r["weighted_error_energy"] for r in aggregates),final_value),
                                  initial_bands=reconcile(sum(r["initial_weighted_error_energy"] for r in aggregates),initial_value))
            gram=[sum(r["T_energy"] for r in aggregates if bands.PHASE_CHANNEL[r["phase"]]==c) for c in range(3)]
            tb=[sum(r["T_rhs_cross"] for r in aggregates if bands.PHASE_CHANNEL[r["phase"]]==c) for c in range(3)]
            gram_checks=[reconcile(v,e,absolute=1e-13) for v,e in zip(gram,evidence["color_gram_f32"])]
            tb_checks=[reconcile(v,e,absolute=1e-13) for v,e in zip(tb,evidence["T_b_f32"])]
            save(out/"budget.json",dict(source_count=source_count,bands=aggregates,objective_checks=objective_checks,
                 final_objective=final_total.receipt(),initial_objective=initial_total.receipt(),per_source_reduction_checks=reductions,
                 color_gram=gram,T_b=tb,gram_checks=gram_checks,T_b_checks=tb_checks,
                 count=evidence["original_sensel_count"],metric_scale=evidence["metric_scale_f32"],
                 scalar_aggregate_precision="Python float sums of producing f32 reductions; authoritative objective uses frozen f32 norm_pair.add",
                 raw_band_errors="unweighted over admitted original coefficient support; squared DN",
                 sigma_units="injected marginal temporal DN variance; neither spatial scene variance nor independent Haar-band likelihood",
                 spectral_nullspace_claim=False,conditioning_proven=False,quality_claim=False))
            require(all(r["passed"] for r in objective_checks.values()) and all(r["passed"] for r in gram_checks+tb_checks),"saved objective/constant-column reconciliation failed")
            runtime=measurement.metadata(strict=True)
        rows_file.close()
        for item,previous in zip(caches,cache_stats):
            require(record(item["path"])==item and stat(item["path"])==previous,"original cache changed")
        require([record(p) for p in paths]==bindings and [stat(p) for p in paths]==stats,"bound source/result changed")
        require(max(t.cuda.max_memory_allocated(0),t.cuda.max_memory_reserved(0))<=LIMIT,"GPU budget exceeded")
        save(out/"bindings-after.json",bindings);save(out/"cache-bindings-after.json",caches)
        state.update(status="COMPLETE_FULL299_BAND_BUDGET",complete=True,source_count=source_count,
                     mechanical_pass=True,controls_pass=True,
                     source_bindings_unchanged=True,cache_bytes_and_metadata_unchanged=True,
                     original_ARW_opened=False,old_solver_refusal_retained=True,budget=record(out/"budget.json"),
                     per_source=record(out/"per-source.ndjson"),measurement=runtime,
                     elapsed_seconds=time.perf_counter()-started,peak_allocated_bytes=t.cuda.max_memory_allocated(0),
                     peak_reserved_bytes=t.cuda.max_memory_reserved(0),device_limit_bytes=LIMIT,
                     torch=t.__version__,numpy=np.__version__,python=sys.version,device=properties.name,
                     workers=4,interop_workers=1,TF32=False,autocast=False)
        save(out/"receipt.json",state);telemetry.emit("complete",source_count=source_count)
    except BaseException as error:
        state.update(status="INCOMPLETE_SAVED_X_BAND_BUDGET",complete=False,source_count=source_count,
                     error=repr(error),traceback=traceback.format_exc(),elapsed_seconds=time.perf_counter()-started)
        save(out/"receipt.json",state);telemetry.emit("failed",error=repr(error));raise
    finally:
        rows_file.close();telemetry.close()


if __name__=="__main__": main()
