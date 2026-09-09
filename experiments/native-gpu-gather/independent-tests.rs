// Fixed independent consumer controls. Root executes; see independent-design.md.
use super::*;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use strehl_core::align::{Similarity, SimilarityParams};
use strehl_core::optics::{OpticalProfile, A7C2_FE100GM_2XTC_X4CPL};
use strehl_core::plane::QuadSource;
use strehl_native_gpu_gather::{GpuGather, Input, Output, SamplePlan, INVALID};

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

#[test]
#[ignore = "root runs the fixed 18 GPU consumer comparisons explicitly"]
fn independent_gpu_gather_controls() {
    let path=PathBuf::from(std::env::var_os("STREHL_GPU_GATHER_OUTPUT")
        .expect("STREHL_GPU_GATHER_OUTPUT required")).join("results.json");
    let mut report=json!({"schema":"native-gpu-gather-fixed-eighteen-v1","status":"STARTED",
        "expected_primary_cases":18,"rows":[],"scope":"generated codes; exact operator equivalence, no calibration/quality/timing claim"});
    save(&path,&report);
    let initialized=std::panic::catch_unwind(std::panic::AssertUnwindSafe(GpuGather::new));
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
