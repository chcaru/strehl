// Fixed independent consumer controls. Root executes; see independent-design.md.
use super::*;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use strehl_core::align::{Similarity, SimilarityParams};
use strehl_core::optics::{OpticalProfile, A7C2_FE100GM_2XTC_X4CPL};
use strehl_core::plane::QuadSource;
use strehl_native_gpu_gather::{GpuGather, Input, Output, SamplePlan, Schedule, INVALID, UNCONSUMED};

struct Case {
    id: usize,
    label: String,
    frame: Frame,
    transform: Similarity,
    ca: Option<OpticalProfile>,
    green: bool,
    boundary: Option<(f64, i32)>,
}

fn translation(x: f64, y: f64) -> Similarity {
    Similarity::from_params(SimilarityParams { ax: x, ay: y, g: 0.0, rot: 0.0 })
}

fn make_case(id: usize) -> Case {
    let main = match id { 16 => 1, 17 => 5, _ => id };
    let layout = match main { 0 | 15 => 0, 2 => 2, _ => 1 };
    let (w, h) = if main == 15 { (2, 2) } else { (70, 50) };
    let mut f = gatefloor::gpu_fixture(w, h, layout, 1);
    let mut t = if matches!(main, 1 | 2 | 3) { gatefloor::gpu_warp() }
        else { Similarity::IDENTITY };
    if !matches!(main, 1 | 2 | 3 | 15) { f.wb_coeffs = [1.0, 1.0, 1.0, f32::NAN]; }
    let mut ca = None;
    let mut boundary = None;
    let label = match main {
        0 => "identity-colour".into(), 1 => "padded-transform-colour".into(),
        2 => "odd-active-odd-stride".into(),
        3 => {
            ca = Some(OpticalProfile { eps_r: 0.012, eps_b: Some(-0.009),
                translation: (0.13, -0.09), key: "SYNTHETIC-GPU-CONTROL",
                ..A7C2_FE100GM_2XTC_X4CPL });
            "synthetic-ca".into()
        }
        4 => {
            f.levels.black = 512.25;
            t = translation(0.25, 0.0);
            for y in 0..h { for x in 0..w {
                f.data[(f.active.y+y)*f.stride+f.active.x+x] = 4096+x as u16;
            }}
            "ramp-half-ties".into()
        }
        5 => {
            f.levels.white = 65535.0;
            t = translation(0.185, -0.115);
            for y in 0..h { for x in 0..w {
                f.data[(f.active.y+y)*f.stride+f.active.x+x] = if x < 35 {0} else {65535};
            }}
            for (x,y,v) in [(16,16,65535), (52,34,0)] {
                f.data[(f.active.y+y)*f.stride+f.active.x+x] = v;
            }
            "signed-overshoot-clamp".into()
        }
        6..=14 => {
            let centre = [1.5, 4.0, 67.5][(main-6)/3];
            let direction = ((main-6)%3) as i32 - 1;
            let c = centre + f64::from(direction)*2.0f64.powi(-40);
            t = translation(c/2.0, 0.0); f.levels.black = 512.25;
            boundary = Some((centre, direction));
            format!("native-boundary-{centre}-{direction}")
        }
        15 => {
            f.levels.black = 512.25;
            f.data = vec![1000,2100,3300,4700];
            "all-uncovered-two-by-two".into()
        }
        _ => unreachable!(),
    };
    Case { id, label: if id >= 16 {format!("green-only-{label}")} else {label},
        frame:f, transform:t, ca, green:id >= 16, boundary }
}

fn channel(x: usize, y: usize) -> usize {
    match (x%2,y%2) { (0,0) => 0, (1,1) => 2, _ => 1 }
}

fn native_codes(f: &Frame) -> Vec<u16> {
    let g = f.geometry();
    (0..2*g.height).flat_map(|y| (0..2*g.width).map(move |x| f.sample(x,y))).collect()
}

fn unpack(out: &Output) -> (Vec<u16>, Vec<bool>) {
    let codes = out.packed.iter().flat_map(|v| [(*v & 65535) as u16, (*v >> 16) as u16]).collect();
    let cover = out.coverage.iter().flat_map(|v| [v & 1 != 0, v & 2 != 0]).collect();
    (codes, cover)
}

fn input<'a>(c: &'a Case, oracle: &align_cmd::GpuCpuOracle) -> Input<'a> {
    let f = &c.frame;
    Input { data:&f.data, stride:f.stride,
        active:[f.active.x,f.active.y,f.active.width,f.active.height], geom:f.geometry(),
        black:f.levels.black, gain:oracle.gain, inverse_gain:oracle.inverse_gain,
        pulls:oracle.pulls, green_only:c.green, malvar:true, resampler:Resampler::CatmullRom }
}

fn descriptor(c: &Case, oracle: &align_cmd::GpuCpuOracle, x: usize, y: usize) -> Value {
    let g = c.frame.geometry();
    let (sx,sy) = oracle.pulls[channel(x,y)].apply_at(x as f64/2.0, y as f64/2.0,
        g.width as f64/2.0,g.height as f64/2.0);
    let p = strehl_native_gpu_gather::plan_at(2*g.width,2*g.height,2.0*sx,2.0*sy);
    json!({"source_native":[2.0*sx,2.0*sy],"x0":p.x0,"y0":p.y0,
        "fx_bits":p.fx.to_bits(),"fy_bits":p.fy.to_bits()})
}

fn require(ok: bool, message: &str, errors: &mut Vec<String>) {
    if !ok { errors.push(message.into()); }
}

fn storage_hash(data:&[u16]) -> String {
    let mut hash=Sha256::new();
    for code in data {hash.update(code.to_le_bytes());}
    hash.finalize().iter().map(|b|format!("{b:02x}")).collect()
}

fn check_case(gpu: &mut GpuGather, c: &Case) -> Result<Value,String> {
    let original = c.frame.data.clone();
    let g = c.frame.geometry(); let (w,h) = (2*g.width,2*g.height); let n = w*h;
    let mut cpu = c.frame.clone();
    let oracle = align_cmd::gpu_cpu_oracle(&mut cpu,c.transform,g,c.ca,c.green)
        .map_err(|e| format!("actual CPU oracle: {e:#}"))?;
    let out = gpu.run(&input(c,&oracle))?;
    let mut errors = Vec::new();
    let mut cpu_observer_controls=Value::Null;
    if matches!(c.id,1|16) {
        let mut ordinary=c.frame.clone(); let mut scratch=WarpScratch::new(g);
        if c.green {
            align_cmd::warp_probe_greens_in_place_fullres(&mut ordinary,c.transform,g,
                Resampler::CatmullRom,&mut scratch).map_err(|e|format!("ordinary green placebo: {e:#}"))?;
        } else {
            let coverage=align_cmd::warp_frame_in_place_fullres(&mut ordinary,c.transform,g,
                Resampler::CatmullRom,&mut scratch).map_err(|e|format!("ordinary RGB placebo: {e:#}"))?;
            require(coverage.to_bits()==(oracle.covered as f64/n as f64).to_bits(),
                "CPU observer changes coverage fraction",&mut errors);
        }
        require(ordinary.data==cpu.data,"CPU observer changes complete output storage",&mut errors);
        let mut placebo=c.frame.clone();
        let placebo_trace=align_cmd::gpu_cpu_oracle_placebo(&mut placebo,c.transform,g,c.ca,c.green)
            .map_err(|e|format!("CPU fixed-sentinel placebo: {e:#}"))?;
        let sentinel_trace=placebo_trace.coverage.len()==n && placebo_trace.sensor_values.len()==n
            && placebo_trace.coverage.iter().all(|v|!*v)
            && placebo_trace.sensor_values.iter().enumerate().all(|(i,v)| {
                if c.green && channel(i%w,i/w)!=1 {v.is_nan()}
                else {v.to_bits()==(-12345.0f32).to_bits()}
            });
        require(sentinel_trace,"CPU placebo does not record the fixed sentinel trace",&mut errors);
        require(oracle.coverage.iter().any(|v|*v) && oracle.sensor_values.iter().any(|v|v.is_finite()),
            "real CPU observation did not differ from placebo trace",&mut errors);
        require(placebo.data==ordinary.data,"CPU placebo changes complete output storage",&mut errors);
        cpu_observer_controls=json!({"same_complete_storage":ordinary.data==cpu.data && placebo.data==ordinary.data,
            "fixed_sentinel_trace":sentinel_trace,"arms":[
                {"arm":"ordinary-no-observer","sha256_u16_le":storage_hash(&ordinary.data)},
                {"arm":"actual-operand-observer","sha256_u16_le":storage_hash(&cpu.data)},
                {"arm":"fixed-sentinel-observer-placebo","sha256_u16_le":storage_hash(&placebo.data)}]});
    }
    require(out.width == w && out.height == h, "GPU geometry differs", &mut errors);
    require(out.packed.len() == n/2 && out.coverage.len() == n/2,
        "GPU packed/coverage lengths differ", &mut errors);
    require(oracle.coverage.len() == n && oracle.sensor_values.len() == n,
        "CPU diagnostic lengths differ", &mut errors);
    if !errors.is_empty() { return Ok(json!({"pass":false,"errors":errors,
        "cpu_observer_controls":cpu_observer_controls})); }
    let (codes,cover) = unpack(&out); let expected = native_codes(&cpu);
    let code_mismatches = codes.iter().zip(&expected).filter(|(a,b)| a!=b).count();
    let coverage_mismatches = cover.iter().zip(&oracle.coverage).filter(|(a,b)| a!=b).count();
    require(code_mismatches == 0,"consumed u16 differs",&mut errors);
    require(coverage_mismatches == 0,"per-site coverage differs",&mut errors);
    require(out.coverage.iter().all(|b| b & !3 == 0),"coverage has high garbage bits",&mut errors);
    require(out.covered == cover.iter().filter(|v| **v).count(),"GPU coverage count differs",&mut errors);
    require(out.consumed_sites == if c.green {n/2} else {n},"consumed site denominator differs",&mut errors);
    let first = (0..n).find(|i| codes[*i]!=expected[*i] || cover[*i]!=oracle.coverage[*i]);
    let first_difference = first.map(|i| {
        let (x,y)=(i%w,i/w); let ci=channel(x,y); let sensor=oracle.sensor_values[i];
        json!({"native":[x,y],"phase":(["R","G1","G2","B"][2*(y%2)+x%2]),
            "cpu_code":expected[i],"gpu_code":codes[i],"source_code":c.frame.sample(x,y),
            "cpu_covered":oracle.coverage[i],"gpu_covered":cover[i],
            "cpu_sensor_before_round":sensor,"cpu_sensor_bits":sensor.to_bits(),
            "inverse_wb_bits":oracle.inverse_gain[ci].to_bits(),"black_bits":c.frame.levels.black.to_bits(),
            "descriptor":descriptor(c,&oracle,x,y)})
    });
    // The prototype returns compact words. This explicit test-side scatter checks
    // conversion to the real padded storage; it is not a production writer hook.
    let mut scattered = c.frame.clone();
    for y in 0..h { for x in 0..w {
        scattered.data[(scattered.active.y+y)*scattered.stride+scattered.active.x+x] = codes[y*w+x];
    }}
    let mut outside_changed = 0;
    for i in 0..original.len() {
        let (x,y)=(i%c.frame.stride,i/c.frame.stride);
        let inside = x>=c.frame.active.x && x<c.frame.active.x+w
            && y>=c.frame.active.y && y<c.frame.active.y+h;
        if !inside && (scattered.data[i]!=original[i] || cpu.data[i]!=original[i]) {outside_changed+=1;}
    }
    require(outside_changed == 0,"outside consumed storage changed",&mut errors);
    require(c.frame.data == original,"GPU call mutated original source",&mut errors);
    let mut phase_counts = [0usize;4]; let mut half_ties=0; let mut low=0; let mut high=0;
    for i in 0..n {
        let (x,y)=(i%w,i/w); let phase=2*(y%2)+x%2;
        phase_counts[phase] += usize::from(cover[i]);
        if c.green && matches!(phase,0|3) {
            require(codes[i]==c.frame.sample(x,y) && !cover[i],"green-only R/B was changed or covered",&mut errors);
        }
        if oracle.coverage[i] {
            let v=oracle.sensor_values[i];
            half_ties += usize::from(v.is_finite() && v>0.0 && v<65535.0 && v.fract()==0.5);
            low += usize::from(v<0.0 && expected[i]==0);
            high += usize::from(v>65535.0 && expected[i]==65535);
        } else if !c.green || matches!(phase,1|2) {
            require(expected[i]==c.frame.levels.black.round().clamp(0.0,65535.0) as u16,
                "CPU uncovered does not use rounded black",&mut errors);
        }
    }
    if c.id==4 { require(half_ties>0,"actual ramp half-tie witness absent",&mut errors); }
    if matches!(c.id,5|17) { require(low>0 && high>0,"actual signed overshoot/clamp witness absent",&mut errors); }
    if c.id==15 { require(out.covered==0 && codes.iter().all(|v|*v==512),"tiny all-uncovered control failed",&mut errors); }
    else if c.id<=5 || c.id>=16 { for phase in 0..4 {
        if !c.green || matches!(phase,1|2) { require(phase_counts[phase]>0,"CFA phase never covered",&mut errors); }
    }}
    if let Some((centre,direction))=c.boundary {
        let c_actual=centre+f64::from(direction)*2.0f64.powi(-40);
        let p=strehl_native_gpu_gather::plan_at(w,h,c_actual,20.0);
        let wanted_cover=!(centre==1.5 && direction<0 || centre==67.5 && direction>0);
        require(oracle.coverage[20*w]==wanted_cover,"literal CPU support direction failed",&mut errors);
        require((p.x0!=INVALID)==wanted_cover,"descriptor support direction failed",&mut errors);
        if wanted_cover {
            let wanted_floor=if centre==1.5 {1} else if centre==67.5 {67}
                else if direction<0 {3} else {4};
            require(p.x0==wanted_floor,"literal descriptor floor differs",&mut errors);
            require(p.fx.to_bits()==((c_actual-f64::from(wanted_floor)) as f32).to_bits(),
                "descriptor rounded fraction differs",&mut errors);
        }
    }
    if c.id==3 {
        let centre=(g.width as f64/2.0,g.height as f64/2.0);
        let p=(7.0,8.0); let base=c.transform.apply_at(p.0,p.1,centre.0,centre.1);
        for (ci,eps) in [(0,0.012),(2,-0.009)] {
            let actual=oracle.pulls[ci].apply_at(p.0,p.1,centre.0,centre.1);
            let expected=(centre.0+(1.0+eps)*(base.0-centre.0)+0.13,
                centre.1+(1.0+eps)*(base.1-centre.1)-0.09);
            require((actual.0-expected.0).abs()<1e-12 && (actual.1-expected.1).abs()<1e-12,
                "CA direction/translation literal differs",&mut errors);
            require((actual.0-base.0).abs()+(actual.1-base.1).abs()>0.001,
                "CA direction control lacks displacement",&mut errors);
        }
        let green=oracle.pulls[1].apply_at(p.0,p.1,centre.0,centre.1);
        require(green.0.to_bits()==base.0.to_bits() && green.1.to_bits()==base.1.to_bits(),
            "CA altered green geometry",&mut errors);
    }
    Ok(json!({"pass":errors.is_empty(),"errors":errors,"code_mismatches":code_mismatches,
        "coverage_mismatches":coverage_mismatches,"first_difference":first_difference,
        "phase_covered":phase_counts,"outside_changed":outside_changed,"half_ties":half_ties,
        "negative_clamped":low,"high_clamped":high,"width":w,"height":h,
        "cpu_observer_controls":cpu_observer_controls}))
}

fn literal_quantization(gpu: &mut GpuGather) -> Result<Value,String> {
    // Values are final sensor-DN operands; the actual shader quantizer is used.
    let mut values=vec![-100000.0,-1.5,-0.5,-0.0,0.0,65535.0,100000.0];
    for tie in [0.5f32,1.5,512.5,4096.5,65534.5,65535.5] {
        values.extend([f32::from_bits(tie.to_bits()-1),tie,f32::from_bits(tie.to_bits()+1)]);
    }
    let want:Vec<u32>=values.iter().map(|v|v.round().clamp(0.0,65535.0) as u32).collect();
    let got=gpu.quantize_for_test(&values)?;
    let first=(0..want.len().min(got.len())).find(|i|want[*i]!=got[*i]).map(|i|
        json!({"index":i,"value":values[i],"bits":values[i].to_bits(),"cpu":want[i],"gpu":got[i]}));
    let below=f32::from_bits(0.5f32.to_bits()-1);
    let premature=(below+0.5).floor() as u32;
    let destroyer_live=premature != below.round() as u32;
    Ok(json!({"pass":got==want && destroyer_live,"count":values.len(),
        "gpu_length":got.len(),"first_difference":first,"premature_add_destroyer_live":destroyer_live}))
}

fn descriptor_destroyers(gpu: &mut GpuGather) -> Result<Value,String> {
    let c=make_case(1); let g=c.frame.geometry(); let (w,h)=(2*g.width,2*g.height);
    let mut cpu=c.frame.clone();
    let oracle=align_cmd::gpu_cpu_oracle(&mut cpu,c.transform,g,c.ca,false).map_err(|e|e.to_string())?;
    let request=input(&c,&oracle);
    let baseline=gpu.run(&request)?;
    let (base_codes,base_cover)=unpack(&baseline);
    let mut rows=Vec::new();
    for kind in ["source-base-plus-one","swap-green-phase","flip-coverage"] {
        let mut mutations=0usize;
        let mut mutate=|y_start:usize, plans:&mut[SamplePlan]| {
            if kind=="swap-green-phase" {
                for ly in (0..plans.len()/w).step_by(2) { for x in (0..w).step_by(2) {
                    if ly+1<plans.len()/w {
                        let (a,b)=(ly*w+x+1,(ly+1)*w+x);
                        if plans[a].x0!=INVALID && plans[b].x0!=INVALID {plans.swap(a,b);mutations+=2;}
                    }
                }}
            } else {
                for (local,p) in plans.iter_mut().enumerate() {
                    let (x,y)=(local%w,y_start+local/w);
                    if x>=10 && x<60 && y>=10 && y<40 && p.x0!=INVALID {
                        if kind=="source-base-plus-one" && p.x0<(w-3) as u32 {p.x0+=1;mutations+=1;}
                        else if kind=="flip-coverage" {p.x0=INVALID;mutations+=1;}
                    }
                }
            }
        };
        let changed=gpu.run_with_plan_mutator(&request,&mut mutate)?;
        let (codes,cover)=unpack(&changed);
        let code_changes=codes.iter().zip(&base_codes).filter(|(a,b)|a!=b).count();
        let coverage_changes=cover.iter().zip(&base_cover).filter(|(a,b)|a!=b).count();
        let first=(0..w*h).find(|i|codes[*i]!=base_codes[*i] || cover[*i]!=base_cover[*i]);
        rows.push(json!({"kind":kind,"pass":mutations>0 && code_changes+coverage_changes>0,
            "mutations":mutations,"changed_codes":code_changes,"changed_coverage":coverage_changes,
            "first_changed_native":first.map(|i|[i%w,i/w])}));
    }
    Ok(json!({"pass":rows.iter().all(|r|r["pass"]==true),"rows":rows}))
}

fn panic_text(p: Box<dyn std::any::Any+Send>) -> String {
    if let Some(s)=p.downcast_ref::<String>() {s.clone()}
    else if let Some(s)=p.downcast_ref::<&str>() {s.to_string()} else {"non-string panic".into()}
}

fn capture(f: impl FnOnce()->Result<Value,String>) -> Value {
    match std::panic::catch_unwind(std::panic::AssertUnwindSafe(f)) {
        Ok(Ok(value))=>value, Ok(Err(e))=>json!({"pass":false,"error":e}),
        Err(p)=>json!({"pass":false,"panic":panic_text(p)}),
    }
}

fn save(path:&std::path::Path, report:&Value) {
    if let Some(parent)=path.parent() {std::fs::create_dir_all(parent).expect("create report directory");}
    std::fs::write(path,serde_json::to_vec_pretty(report).unwrap()).expect("retain independent report");
}

fn requested_gpu_schedule() -> Result<Schedule,String> {
    match std::env::var("STREHL_GPU_SCHEDULE") {
        Err(std::env::VarError::NotPresent) => Ok(Schedule::Parallel256),
        Ok(v) if v=="serial" => Ok(Schedule::Serial32),
        Ok(v) if v=="parallel" => Ok(Schedule::Parallel256),
        Ok(v) if v=="device" => Ok(Schedule::Device256),
        other => Err(format!("STREHL_GPU_SCHEDULE: expected serial, parallel, or device; {other:?}")),
    }
}

#[test]
#[ignore = "root runs the fixed 18 GPU consumer comparisons explicitly"]
fn independent_gpu_gather_controls() {
    let path=PathBuf::from(std::env::var_os("STREHL_GPU_GATHER_OUTPUT")
        .expect("STREHL_GPU_GATHER_OUTPUT required")).join("results.json");
    let mut report=json!({"schema":"native-gpu-gather-fixed-eighteen-v1","status":"STARTED",
        "expected_primary_cases":18,"rows":[],"scope":"generated codes; exact operator equivalence, no calibration/quality/timing claim"});
    save(&path,&report);
    let initialized=std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        GpuGather::new_with_schedule(requested_gpu_schedule()?)
    }));
    let mut gpu=match initialized {
        Ok(Ok(g))=>g,
        failed=>{
            report["status"]=json!("CONTROL_FAILED");
            report["initialization_error"]=json!(match failed {Ok(Err(e))=>e,Err(p)=>panic_text(p),_=>unreachable!()});
            save(&path,&report);panic!("GPU initialization failed; report retained at {}",path.display());
        }
    };
    report["adapter"]=json!(gpu.adapter);
    report["backend"]=json!(gpu.backend);
    report["device_type"]=json!(gpu.device_type);
    report["compilation"]=json!(gpu.compilation);
    report["schedule"]=json!(format!("{:?}",gpu.schedule()));
    save(&path,&report);
    report["literal_quantization"]=capture(||literal_quantization(&mut gpu));
    save(&path,&report);
    for id in 0..18 {
        // Save visitation first, including a panic before this case finishes.
        report["active_primary_case"]=json!(id);save(&path,&report);
        let c=make_case(id);
        let mut row=capture(||check_case(&mut gpu,&c));
        row["id"]=json!(id);row["label"]=json!(c.label);
        report["rows"].as_array_mut().unwrap().push(row);
        save(&path,&report);
    }
    report["descriptor_destroyers"]=capture(||descriptor_destroyers(&mut gpu));
    report["active_primary_case"]=Value::Null;
    let passed=report["rows"].as_array().unwrap().len()==18
        && report["rows"].as_array().unwrap().iter().all(|r|r["pass"]==true)
        && report["literal_quantization"]["pass"]==true && report["descriptor_destroyers"]["pass"]==true;
    // One separately reported compiler-route diagnostic, using the unchanged
    // case3 and actual CPU comparison. It does not enter the primary predicate.
    drop(gpu);
    report["undecorated_case3"]=json!({"status":"STARTED","id":3,
        "constructor":"new_undecorated_for_test","affects_primary_pass":false});
    save(&path,&report);
    let mut diagnostic=capture(|| {
        let mut undecorated=GpuGather::new_undecorated_for_test()
            .map_err(|e|format!("undecorated initialization: {e}"))?;
        let mut row=capture(||check_case(&mut undecorated,&make_case(3)));
        row["adapter"]=json!(undecorated.adapter);
        row["backend"]=json!(undecorated.backend);
        row["device_type"]=json!(undecorated.device_type);
        row["compilation"]=json!(undecorated.compilation);
        row["schedule"]=json!(format!("{:?}",undecorated.schedule()));
        Ok(row)
    });
    diagnostic["status"]=json!("RETURNED_OR_CAUGHT_ERROR");
    diagnostic["id"]=json!(3);
    diagnostic["constructor"]=json!("new_undecorated_for_test");
    diagnostic["affects_primary_pass"]=json!(false);
    report["undecorated_case3"]=diagnostic;
    report["status"]=json!(if passed {"EIGHTEEN_GPU_GATHER_CONTROLS_PASS"} else {"CONTROL_FAILED"});
    save(&path,&report);
    assert!(passed,"GPU gather exact controls failed; report retained at {}",path.display());
}

fn plan_words(p:&SamplePlan) -> [u32;4] { [p.x0,p.y0,p.fx.to_bits(),p.fy.to_bits()] }

fn cpu_source(width:usize,height:usize,pulls:&[Similarity;3],x:usize,y:usize) -> (f64,f64) {
    let (sx,sy)=pulls[channel(x,y)].apply_at(x as f64/2.0,y as f64/2.0,
        width as f64/4.0,height as f64/4.0);
    (2.0*sx,2.0*sy)
}

fn cpu_plans(width:usize,height:usize,pulls:&[Similarity;3],green:bool,start:usize,rows:usize) -> Vec<SamplePlan> {
    (start..start+rows).flat_map(|y|(0..width).map(move |x| {
        if green && channel(x,y)!=1 {SamplePlan{x0:UNCONSUMED,y0:0,fx:0.0,fy:0.0}}
        else {let (sx,sy)=cpu_source(width,height,pulls,x,y);
            strehl_native_gpu_gather::plan_at(width,height,sx,sy)}
    })).collect()
}

#[allow(clippy::too_many_arguments)]
fn compare_device_plans(gpu:&mut GpuGather,width:usize,height:usize,pulls:[Similarity;3],
    green:bool,start:usize,rows:usize) -> Result<(Value,Vec<SamplePlan>),String> {
    let expected=cpu_plans(width,height,&pulls,green,start,rows);
    let actual=gpu.device_plans_for_test(width,height,pulls,green,start,rows)?;
    let different=actual.iter().zip(&expected).filter(|(a,b)|plan_words(a)!=plan_words(b)).count();
    let first=actual.iter().zip(&expected).position(|(a,b)|plan_words(a)!=plan_words(b)).map(|i| {
        let (x,y)=(i%width,start+i/width);let (sx,sy)=cpu_source(width,height,&pulls,x,y);
        json!({"native":[x,y],"channel":channel(x,y),"source_native":[sx,sy],
            "source_f64_bits":[sx.to_bits(),sy.to_bits()],"cpu_words":plan_words(&expected[i]),
            "device_words":plan_words(&actual[i])})
    });
    let valid=actual.iter().filter(|p|p.x0!=INVALID && p.x0!=UNCONSUMED).count();
    let omitted=actual.iter().filter(|p|p.x0==UNCONSUMED).count();
    Ok((json!({"pass":actual.len()==expected.len() && different==0 && std::mem::size_of::<SamplePlan>()==16,
        "width":width,"height":height,"start":start,"rows":rows,"green_only":green,
        "expected_plans":expected.len(),"actual_plans":actual.len(),"different":different,
        "valid":valid,"unconsumed":omitted,"first_difference":first}),actual))
}

fn device_record(path:&std::path::Path,report:&mut Value,group:&str,label:&str,
    run:impl FnOnce()->Result<Value,String>) {
    report["active_case"]=json!(label);save(path,report);
    let mut row=capture(run);row["group"]=json!(group);row["label"]=json!(label);
    report["rows"].as_array_mut().unwrap().push(row);save(path,report);
}

#[allow(clippy::too_many_arguments)]
fn literal_device_row(gpu:&mut GpuGather,axis:usize,target:f64,wanted:[u32;4],
    live_f32:&mut usize,live_shift:&mut usize) -> Result<Value,String> {
    let (x,y,start,pull)=if axis==0 {(0,20,20,translation(target/2.0,0.0))}
        else {(20,0,0,translation(0.0,target/2.0))};
    let pulls=[pull;3];let (sx,sy)=cpu_source(70,50,&pulls,x,y);
    let actual_target=if axis==0 {sx} else {sy};
    let current=strehl_native_gpu_gather::plan_at(70,50,sx,sy);
    let wrong=strehl_native_gpu_gather::plan_at(70,50,(sx as f32) as f64,(sy as f32) as f64);
    let f32_destroyer=plan_words(&wrong)!=wanted;
    *live_f32+=usize::from(f32_destroyer);
    let mut shifted=current;
    let shift_live=if shifted.x0!=INVALID {shifted.x0+=1;plan_words(&shifted)!=wanted} else {false};
    *live_shift+=usize::from(shift_live);
    let (mut row,device)=compare_device_plans(gpu,70,50,pulls,false,start,1)?;
    let local=x; // nominated point is on the only returned row.
    let source_exact=actual_target.to_bits()==target.to_bits();
    let literal_cpu=plan_words(&current)==wanted;
    let literal_device=device.get(local).is_some_and(|p|plan_words(p)==wanted);
    row["pass"]=json!(row["pass"]==true && source_exact && literal_cpu && literal_device);
    row["axis"]=json!(axis);row["target"]=json!(target);row["target_f64_bits"]=json!(target.to_bits());
    row["actual_source_f64_bits"]=json!(actual_target.to_bits());row["source_target_exact"]=json!(source_exact);
    row["literal_expected_words"]=json!(wanted);row["cpu_target_words"]=json!(plan_words(&current));
    row["device_target_words"]=device.get(local).map(|p|json!(plan_words(p))).unwrap_or(Value::Null);
    row["f32_coordinate_destroyer_live"]=json!(f32_destroyer);
    row["f32_coordinate_words"]=json!(plan_words(&wrong));row["shift_base_destroyer_live"]=json!(shift_live);
    Ok(row)
}

fn descriptor_ca_pulls(base:Similarity) -> [Similarity;3] {
    let ca=make_case(3).ca.unwrap();
    [(0,0),(1,0),(1,1)].map(|(x,y)|OpticalProfile::compose(Some(&ca),
        strehl_core::optics::cfa_site_channel(x,y),base))
}

#[test]
#[ignore = "root runs device descriptor controls before the unchanged18 image cases"]
fn independent_gpu_device_descriptor_controls() {
    let path=PathBuf::from(std::env::var_os("STREHL_GPU_GATHER_OUTPUT")
        .expect("STREHL_GPU_GATHER_OUTPUT required")).join("device-descriptor-results.json");
    let mut report=json!({"schema":"native-gpu-device-descriptor-v1","status":"STARTED",
        "expected_rows":41,"expected_device_requests":37,"rows":[],
        "scope":"exact16-byte descriptors; separate from original18 image population"});
    save(&path,&report);
    let initialized=std::panic::catch_unwind(std::panic::AssertUnwindSafe(||
        GpuGather::new_with_schedule(Schedule::Device256)));
    let mut gpu=match initialized {Ok(Ok(g))=>g,other=>{
        report["status"]=json!("CONTROL_FAILED");
        report["initialization_error"]=json!(match other {Ok(Err(e))=>e,Err(p)=>panic_text(p),_=>unreachable!()});
        save(&path,&report);panic!("device-coordinate initialization refused; retained {}",path.display());
    }};
    report["adapter"]=json!(gpu.adapter);report["backend"]=json!(gpu.backend);
    report["device_type"]=json!(gpu.device_type);report["schedule"]=json!(format!("{:?}",gpu.schedule()));
    report["gather_compilation"]=json!(gpu.compilation);
    report["coordinate_compilation"]=json!(gpu.coordinate_compilation);save(&path,&report);
    let (mut f32_live,mut shift_live)=(0,0);
    for axis in 0..2 {
        let upper=if axis==0 {67.5} else {47.5};
        for centre in [1.5,4.0,upper] {for direction in [-1,0,1] {
            let target=centre+f64::from(direction)*2.0f64.powi(-40);
            let covered=!(centre==1.5 && direction<0 || centre==upper && direction>0);
            let floor=if centre==1.5 {1} else if centre==upper {if axis==0 {67} else {47}}
                else if direction<0 {3} else {4};
            let frac=if centre!=4.0 {0x3f000000} else if direction<0 {0x3f800000}
                else if direction==0 {0} else {0x2b800000};
            let want=if !covered {[INVALID,0,0,0]} else if axis==0 {[floor,20,frac,0]} else {[20,floor,0,frac]};
            device_record(&path,&mut report,"boundary",&format!("axis{axis}-at{centre}-side{direction}"),
                ||literal_device_row(&mut gpu,axis,target,want,&mut f32_live,&mut shift_live));
        }}
        for parity in 0..2 {for direction in [-1,0,1] {
            let target=4.5+(1+2*parity) as f64*2.0f64.powi(-25)+f64::from(direction)*2.0f64.powi(-40);
            let frac=if parity==0 {if direction<=0 {0x3f000000} else {0x3f000001}}
                else if direction<0 {0x3f000001} else {0x3f000002};
            let want=if axis==0 {[4,20,frac,0]} else {[20,4,0,frac]};
            device_record(&path,&mut report,"f32-half-tie",&format!("axis{axis}-parity{parity}-side{direction}"),
                ||literal_device_row(&mut gpu,axis,target,want,&mut f32_live,&mut shift_live));
        }}
    }
    let ca_base=gatefloor::gpu_warp();let ca_pulls=descriptor_ca_pulls(ca_base);
    for green in [false,true] {
        device_record(&path,&mut report,"ca-field",&format!("ca-green{green}"),|| {
            let (mut row,plans)=compare_device_plans(&mut gpu,70,50,ca_pulls,green,0,50)?;
            let mut phases=[0usize;4];
            for (i,p) in plans.iter().enumerate() {
                if p.x0!=INVALID && p.x0!=UNCONSUMED {phases[2*((i/70)%2)+i%2]+=1;}
            }
            let point=(7.0,8.0);let centre=(17.5,12.5);
            let base=ca_base.apply_at(point.0,point.1,centre.0,centre.1);
            let positions=ca_pulls.map(|t|t.apply_at(point.0,point.1,centre.0,centre.1));
            let distinct=(0..3).all(|a|(a+1..3).all(|b|
                (positions[a].0-positions[b].0).abs()+(positions[a].1-positions[b].1).abs()>0.001));
            let literal_ca=[(0,0.012),(2,-0.009)].iter().all(|&(ci,eps)| {
                let expected=(centre.0+(1.0+eps)*(base.0-centre.0)+0.13,
                    centre.1+(1.0+eps)*(base.1-centre.1)-0.09);
                (positions[ci].0-expected.0).abs()<1e-12 && (positions[ci].1-expected.1).abs()<1e-12
            }) && positions[1].0.to_bits()==base.0.to_bits() && positions[1].1.to_bits()==base.1.to_bits();
            let phase_live=(0..4).all(|p|if green && matches!(p,0|3) {phases[p]==0} else {phases[p]>0});
            row["pass"]=json!(row["pass"]==true && distinct && literal_ca && phase_live);
            row["phase_valid"]=json!(phases);row["all_three_maps_distinct"]=json!(distinct);
            row["independent_ca_literal"]=json!(literal_ca);Ok(row)
        });
    }
    let inward=Similarity::from_params(SimilarityParams{ax:0.0,ay:0.0,g:-0.02,rot:0.0});
    let batch_pulls=descriptor_ca_pulls(inward);
    for green in [false,true] {
        let mut concatenated=Vec::new();
        for (start,rows) in [(0,256),(256,2)] {
            device_record(&path,&mut report,"batch-strip",&format!("batch-green{green}-start{start}"),|| {
                let (mut row,plans)=compare_device_plans(&mut gpu,70,258,batch_pulls,green,start,rows)?;
                concatenated.extend(plans);
                if start==256 {
                    let expected=cpu_plans(70,258,&batch_pulls,green,0,258);
                    let exact=concatenated.len()==expected.len() && concatenated.iter().zip(&expected)
                        .all(|(a,b)|plan_words(a)==plan_words(b));
                    let live=row["valid"].as_u64().unwrap_or(0)>0;
                    row["concatenation_exact"]=json!(exact);row["last_strip_valid"]=json!(live);
                    row["pass"]=json!(row["pass"]==true && exact && live);
                }
                Ok(row)
            });
        }
    }
    device_record(&path,&mut report,"nonfinite","nan-infinity-overflow",|| {
        let pulls=[translation(f64::NAN,0.0),translation(0.0,f64::INFINITY),
            Similarity::from_params(SimilarityParams{ax:0.0,ay:0.0,g:f64::MAX,rot:0.0})];
        let all_nonfinite=(20..22).all(|y|(0..70).all(|x| {
            let (sx,sy)=cpu_source(70,50,&pulls,x,y);!sx.is_finite() || !sy.is_finite()
        }));
        let (mut row,plans)=compare_device_plans(&mut gpu,70,50,pulls,false,20,2)?;
        let invalid=plans.iter().all(|p|plan_words(p)==[INVALID,0,0,0]);
        row["pass"]=json!(row["pass"]==true && all_nonfinite && invalid);
        row["all_cpu_coordinates_nonfinite"]=json!(all_nonfinite);Ok(row)
    });
    for (label,w,h,start,rows) in [("odd-width",71,50,0,1),("odd-height",70,51,0,1),
        ("too-many-rows",70,258,0,257),("strip-past-end",70,50,49,2)] {
        device_record(&path,&mut report,"api-refusal",label,|| {
            match gpu.device_plans_for_test(w,h,[Similarity::IDENTITY;3],false,start,rows) {
                Err(e)=>Ok(json!({"pass":true,"refusal":e})),
                Ok(p)=>Ok(json!({"pass":false,"unexpected_plans":p.len()})),
            }
        });
    }
    report["active_case"]=Value::Null;
    report["f32_coordinate_destroyers_live"]=json!(f32_live);
    report["shift_base_destroyers_live"]=json!(shift_live);
    let rows=report["rows"].as_array().unwrap();
    let counts_match=[("boundary",18),("f32-half-tie",12),("ca-field",2),("batch-strip",4),
        ("nonfinite",1),("api-refusal",4)].iter().all(|(name,n)|rows.iter().filter(|r|r["group"]==*name).count()==*n);
    let pass=rows.len()==41 && counts_match && rows.iter().all(|r|r["pass"]==true)
        && f32_live>=6 && shift_live>0 && gpu.schedule()==Schedule::Device256
        && gpu.coordinate_compilation.is_some();
    report["status"]=json!(if pass {"DEVICE_DESCRIPTOR_CONTROLS_PASS"} else {"CONTROL_FAILED"});
    save(&path,&report);
    assert!(pass,"device descriptor controls failed; retained {}",path.display());
}

// Additional guarded-domain controls. Original descriptor/image populations above stay fixed.
fn set_guard_coefficient(pulls:&mut [Similarity;3],slot:usize,value:f64) {
    let t=&mut pulls[slot/4];
    match slot%4 {0=>t.a.re=value,1=>t.a.im=value,2=>t.b.re=value,3=>t.b.im=value,_=>unreachable!()}
}

fn guard_predicates() -> Value {
    use strehl_native_gpu_gather::{device_coordinate_eligible,MIN_DEVICE_COEFFICIENT};
    const T:u64=0x07b0000000000000;
    const NEG:u64=0x8000000000000000;
    let cases=[("positive-below",T-1,false),("positive-at",T,true),("positive-above",T+1,true),
        ("negative-below",NEG|(T-1),false),("negative-at",NEG|T,true),("negative-above",NEG|(T+1),true),
        ("positive-half",0x07a0000000000000,false),("negative-half",0x87a0000000000000,false),
        ("minimum-normal",0x0010000000000000,false),("positive-subnormal",1,false),
        ("negative-subnormal",NEG|1,false),("positive-zero",0,true),("negative-zero",NEG,true),
        ("positive-infinity",0x7ff0000000000000,true),("negative-infinity",0xfff0000000000000,true),
        ("quiet-nan",0x7ff8000000001234,true)];
    let mut rows=Vec::new();
    for slot in 0..12 {for (label,bits,expected) in cases {
        let mut pulls=descriptor_ca_pulls(gatefloor::gpu_warp());
        set_guard_coefficient(&mut pulls,slot,f64::from_bits(bits));
        let actual=device_coordinate_eligible(pulls);
        rows.push(json!({"slot":slot,"channel":slot/4,"component":(["a.re","a.im","b.re","b.im"][slot%4]),
            "label":label,"bits":bits,"expected":expected,"actual":actual,"pass":actual==expected}));
    }}
    let mut dangerous=Similarity::IDENTITY;
    dangerous.a.re=f64::from_bits(0x0010000000000001);
    dangerous.a.im=f64::from_bits(0x0010000000000000);
    dangerous.b.re=0.0;dangerous.b.im=0.0;
    let centred=strehl_core::align::Cx::new(37.0/2.0-70.0/4.0,27.0/2.0-50.0/4.0);
    let product=std::hint::black_box(dangerous.a)*std::hint::black_box(centred);
    let flushed=if product.re.is_subnormal() {0.0} else {product.re};
    let cancellation_pass=centred.re==1.0 && centred.im==1.0 && product.re.to_bits()==1
        && flushed.to_bits()!=product.re.to_bits() && !device_coordinate_eligible([dangerous;3]);
    let pass=MIN_DEVICE_COEFFICIENT.to_bits()==T && rows.len()==192
        && rows.iter().all(|r|r["pass"]==true) && cancellation_pass;
    json!({"pass":pass,"literal_threshold_bits":T,"exported_threshold_bits":MIN_DEVICE_COEFFICIENT.to_bits(),
        "expected_checks":192,"rows":rows,"underflow_witness":{"pass":cancellation_pass,
            "native":[37,27],"centred_quad":[centred.re,centred.im],"real_product_bits":product.re.to_bits(),
            "literal_expected_bits":1,"flushed_bits":flushed.to_bits(),
            "scope":"intermediate differs; final rounded image difference is not claimed"}})
}

fn word_hash(data:&[u32]) -> String {
    let mut hash=Sha256::new();for word in data {hash.update(word.to_le_bytes());}
    hash.finalize().iter().map(|b|format!("{b:02x}")).collect()
}

#[allow(clippy::too_many_arguments)]
fn guard_image_pair(device:&mut GpuGather,parallel:&mut GpuGather,c:&Case,
    oracle:&align_cmd::GpuCpuOracle,pulls:[Similarity;3],safe:bool) -> Result<Value,String> {
    let original=c.frame.data.clone();let mut source=input(c,oracle);source.pulls=pulls;
    let (w,h)=(2*source.geom.width,2*source.geom.height);let n=w*h;
    let helper=match device.device_plans_for_test(w,h,pulls,false,0,h) {
        Err(e)=>json!({"pass":!safe,"refused":true,"reason":e}),
        Ok(actual)=>{
            let expected=cpu_plans(w,h,&pulls,false,0,h);
            let first=actual.iter().zip(&expected).position(|(a,b)|plan_words(a)!=plan_words(b));
            json!({"pass":safe && actual.len()==expected.len() && first.is_none(),"refused":false,
                "actual_plans":actual.len(),"expected_plans":expected.len(),
                "first_difference":first.map(|i|json!({"native":[i%w,i/w],
                    "cpu_words":plan_words(&expected[i]),"device_words":plan_words(&actual[i])}))})
        }
    };
    let reference=parallel.run(&source)?;
    let actual=device.run(&source)?;
    let dimensions=actual.width==w && actual.height==h && reference.width==w && reference.height==h;
    let lengths=actual.packed.len()==n/2 && actual.coverage.len()==n/2
        && reference.packed.len()==n/2 && reference.coverage.len()==n/2;
    let (codes,coverage)=unpack(&actual);
    let mut phases=[0usize;4];
    for (i,covered) in coverage.iter().enumerate() {
        if *covered {phases[2*((i/w)%2)+i%2]+=1;}
    }
    let first=(0..actual.packed.len().min(reference.packed.len())
        .min(actual.coverage.len()).min(reference.coverage.len())).find(|&i|
        actual.packed[i]!=reference.packed[i] || actual.coverage[i]!=reference.coverage[i]);
    let first_difference=first.map(|i|{
        let (x,y)=(2*i%w,2*i/w);
        json!({"native_pair":[x,y],"cpu_planned_word":reference.packed[i],"actual_word":actual.packed[i],
            "cpu_planned_coverage":reference.coverage[i],"actual_coverage":actual.coverage[i],
            "source_native_pair":[cpu_source(w,h,&pulls,x,y),cpu_source(w,h,&pulls,x+1,y)]})
    });
    let source_live=native_codes(&c.frame).windows(2).any(|v|v[0]!=v[1]);
    let counts=actual.covered==reference.covered && actual.covered==coverage.iter().filter(|v|**v).count()
        && actual.consumed_sites==n && reference.consumed_sites==n && phases.iter().all(|n|*n>0)
        && actual.coverage.iter().all(|bits|bits&!3==0);
    let expected_schedule=if safe {Schedule::Device256} else {Schedule::Parallel256};
    let routing=actual.schedule==expected_schedule && reference.schedule==Schedule::Parallel256
        && reference.coordinate_fallback.is_none()
        && (if safe {actual.coordinate_fallback.is_none()}
            else {actual.coordinate_fallback.is_some_and(|s|!s.is_empty())})
        && device.schedule()==Schedule::Device256 && parallel.schedule()==Schedule::Parallel256;
    let upload_expected=if safe {96} else {(n*16) as u64};
    let uploads=actual.costs.coordinate_upload_bytes==upload_expected
        && reference.costs.coordinate_upload_bytes==(n*16) as u64;
    let exact=actual.packed==reference.packed && actual.coverage==reference.coverage;
    let pass=dimensions && lengths && counts && routing && uploads && exact && source_live
        && c.frame.data==original && helper["pass"]==true;
    Ok(json!({"pass":pass,"safe":safe,"dimensions_exact":dimensions,"lengths_exact":lengths,
        "counts_exact_and_live":counts,"covered_phase_sites":phases,"source_nonconstant":source_live,
        "original_storage_unchanged":c.frame.data==original,"requested_schedule":format!("{:?}",device.schedule()),
        "actual_schedule":format!("{:?}",actual.schedule),"reference_schedule":format!("{:?}",reference.schedule),
        "coordinate_fallback":actual.coordinate_fallback,"routing_pass":routing,"upload_route_pass":uploads,
        "actual_coordinate_upload_bytes":actual.costs.coordinate_upload_bytes,
        "reference_coordinate_upload_bytes":reference.costs.coordinate_upload_bytes,
        "exact_packed_and_coverage":exact,"first_difference":first_difference,"direct_helper":helper,
        "actual_code_sha256_u16_le":storage_hash(&codes),
        "reference_packed_sha256_u32_le":word_hash(&reference.packed),
        "actual_packed_sha256_u32_le":word_hash(&actual.packed),
        "reference_coverage_sha256_u32_le":word_hash(&reference.coverage),
        "actual_coverage_sha256_u32_le":word_hash(&actual.coverage),
        "pull_bits":pulls.map(|t|[t.a.re.to_bits(),t.a.im.to_bits(),t.b.re.to_bits(),t.b.im.to_bits()])}))
}

#[test]
#[ignore = "root runs guard controls before the unchanged descriptor and image populations"]
fn independent_gpu_device_guard_controls() {
    let path=PathBuf::from(std::env::var_os("STREHL_GPU_GATHER_OUTPUT")
        .expect("STREHL_GPU_GATHER_OUTPUT required")).join("device-guard-results.json");
    let mut report=json!({"schema":"native-gpu-device-guard-v1","status":"STARTED","expected_image_pairs":4,
        "rows":[],"scope":"guarded coordinate routing; same strict image shader in both arms"});
    save(&path,&report);
    report["predicate_controls"]=capture(||Ok(guard_predicates()));save(&path,&report);
    if report["predicate_controls"]["pass"]!=true {
        report["status"]=json!("CONTROL_FAILED");save(&path,&report);
        panic!("coefficient guard predicates failed; retained {}",path.display());
    }
    let initialized=std::panic::catch_unwind(std::panic::AssertUnwindSafe(||
        GpuGather::new_with_schedule(Schedule::Device256)));
    let mut device=match initialized {Ok(Ok(g))=>g,other=>{
        report["status"]=json!("CONTROL_FAILED");
        report["initialization_error"]=json!(match other {Ok(Err(e))=>e,Err(p)=>panic_text(p),_=>unreachable!()});
        save(&path,&report);panic!("guard device initialization refused; retained {}",path.display());
    }};
    report["adapter"]=json!(device.adapter);report["backend"]=json!(device.backend);
    report["device_type"]=json!(device.device_type);report["schedule"]=json!(format!("{:?}",device.schedule()));
    report["gather_compilation"]=json!(device.compilation);
    report["coordinate_compilation"]=json!(device.coordinate_compilation);save(&path,&report);
    let initialized=std::panic::catch_unwind(std::panic::AssertUnwindSafe(||
        GpuGather::new_with_schedule(Schedule::Parallel256)));
    let mut parallel=match initialized {Ok(Ok(g))=>g,other=>{
        report["status"]=json!("CONTROL_FAILED");
        report["reference_initialization_error"]=json!(match other {Ok(Err(e))=>e,Err(p)=>panic_text(p),_=>unreachable!()});
        save(&path,&report);panic!("guard CPU-planner context refused; retained {}",path.display());
    }};
    report["reference_context"]=json!({"adapter":parallel.adapter,"backend":parallel.backend,
        "device_type":parallel.device_type,"schedule":format!("{:?}",parallel.schedule()),
        "gather_compilation":parallel.compilation,"coordinate_compilation":parallel.coordinate_compilation});
    save(&path,&report);
    let setup=std::panic::catch_unwind(std::panic::AssertUnwindSafe(||{
        let c=make_case(1);let mut cpu=c.frame.clone();
        let oracle=align_cmd::gpu_cpu_oracle(&mut cpu,c.transform,c.frame.geometry(),c.ca,c.green)
            .map_err(|e|format!("unchanged case1 photometry: {e:#}"))?;
        Ok::<_,String>((c,oracle))
    }));
    let (c,oracle)=match setup {Ok(Ok(v))=>v,other=>{
        report["status"]=json!("CONTROL_FAILED");
        report["fixture_error"]=json!(match other {Ok(Err(e))=>e,Err(p)=>panic_text(p),_=>unreachable!()});
        save(&path,&report);panic!("guard fixture setup failed; retained {}",path.display());
    }};
    let base=descriptor_ca_pulls(gatefloor::gpu_warp());
    for id in 0..4 {
        let mut pulls=base;
        let label=match id {
            0=>{pulls[0].b.re=f64::from_bits(0x07afffffffffffff);"below-threshold-translation"},
            1=>{pulls[2].b.re=f64::from_bits(1);"subnormal-translation"},
            2=>{for t in &mut pulls {t.a.re=f64::from_bits(0x0010000000000001);
                t.a.im=f64::from_bits(0x0010000000000000);t.b.re=0.0;t.b.im=0.0;}
                "underflow-cancellation"},
            3=>{pulls[2].a.im=f64::from_bits(0x07b0000000000000);"threshold-after-fallback"},
            _=>unreachable!(),
        };
        device_record(&path,&mut report,"guard-image-pair",label,||
            guard_image_pair(&mut device,&mut parallel,&c,&oracle,pulls,id==3));
    }
    let protected=device.compilation.original_sha256=="41658a89bd9b17c73b0f452b48bde689679e4ecc50774872ebfff0171cdb6560"
        && device.compilation.submitted_sha256=="a7dce2107ce7713ac4d9cd961dd44e303bd69b37c2d2ca7029f20aa1f131de9d"
        && parallel.compilation.original_sha256==device.compilation.original_sha256
        && parallel.compilation.submitted_sha256==device.compilation.submitted_sha256;
    let rows=report["rows"].as_array().unwrap();
    let pass=rows.len()==4 && rows.iter().all(|r|r["pass"]==true) && protected
        && device.coordinate_compilation.is_some() && parallel.coordinate_compilation.is_none();
    report["active_case"]=Value::Null;report["protected_image_shader_hashes"]=json!(protected);
    report["status"]=json!(if pass {"DEVICE_GUARD_CONTROLS_PASS"} else {"CONTROL_FAILED"});
    save(&path,&report);assert!(pass,"device guard controls failed; retained {}",path.display());
}
