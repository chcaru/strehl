// Test-only original-CFA consumer; root executes, author does not.
use super::*;
use super::super::*;
use strehl_core::pyramid::correction_variance_diagnostic as kernel;
use strehl_core::warpmap::Provenance as WarpProvenance;
use sha2::{Digest, Sha256};

struct Source(Frame);
impl PyramidFrameSource for Source {
    fn len(&self) -> usize { 1 }
    fn decode(&self, index: usize) -> Result<Frame> {
        assert_eq!(index, 0);
        Ok(self.0.clone())
    }
}
fn fixture() -> Frame { super::m194c_independent_tests::green_fixture(274,190,1,1) }
fn domain(frame: &Frame) -> PyramidDomain {
    PyramidDomain::cropped(frame.geometry(), super::m194c_independent_tests::variance_crop()).unwrap()
}
fn warpmap(frame: &Frame, t: Similarity) -> WarpMap {
    let path = frame.path.to_string_lossy();
    WarpMap::new(WarpProvenance {
        stack: StackIdentity::from_entries("correction variance original-CFA fixture", &[(path,frame.allocated_bytes() as u64)]),
        strategy: "fixed existing M194c warp".into(), heldout_px: None, cycle_floor_px: None,
        reference: 0, note: "test-only transfer; no alignment truth claim".into(),
    }, frame.geometry(), Resampler::CatmullRom, vec![FrameWarp::Placed(t)])
}
fn prepare(frame: &Frame, t: Similarity, defect: Option<&crate::stack::DefectPlan>, measure: bool)
    -> (Vec<Vec<f32>>, Vec<f32>, Vec<f32>) {
    let domain = domain(frame);
    let n = domain.analysis().pixels();
    let mut planes = vec![vec![0.0; n]; 4];
    let mut luma = vec![0.0; n];
    let mut probe = Probe::new(domain,3);
    let tally = crate::stack::DefectTally::default();
    assert!(load_frame(&Source(frame.clone()),0,domain,frame.levels,Some(&warpmap(frame,t)),
        defect.map(|p| (p,&tally)),&mut WarpScratch::new(domain.full),measure.then_some(&mut probe),
        &mut planes,&mut luma).unwrap());
    (planes,luma,probe.last().to_vec())
}
fn hash(values: &[f32]) -> String {
    let mut digest = Sha256::new();
    for value in values { digest.update(value.to_bits().to_le_bytes()); }
    digest.finalize().iter().map(|v| format!("{v:02x}")).collect()
}
#[test]
#[ignore = "root-owned bounded source-transfer diagnostic"]
fn correction_variance_smoke() {
    let frame = fixture();
    assert!(!frame.path.exists());
    let sizes = level_sizes(domain(&frame).analysis().width,domain(&frame).analysis().height,3);
    for t in [Similarity::IDENTITY,super::m194c_independent_tests::variance_warp()] {
        let (planes,luma,beta) = prepare(&frame,t,None,true);
        assert_eq!(planes.len(),4);
        assert!(beta.len() >= 2 && beta[..2].iter().all(|v| v.is_finite()));
        let bands = kernel::laplacian(&luma,&sizes);
        let energy = kernel::energy(&bands[0],sizes[0]);
        assert_eq!(energy.len(),luma.len());
        println!("CORRECTION_VARIANCE_SMOKE luma={} energy={} beta={:?}",hash(&luma),hash(&energy),beta);
    }
}

use serde_json::{json, Value};
use strehl_core::align::PlaneRef;
use strehl_core::defect_map::{Correction, DefectMap, DustQuad, HotFloor};
use strehl_core::noise::{PlaneNoise, Provenance as NoiseProvenance};

const N: usize = 64;
const CENTRE: (f64,f64) = (137.0,95.0);
const PEAK: f32 = 1.0584;

fn noise_model(frame: &Frame, read: bool) -> NoiseModel {
    NoiseModel::new([PlaneNoise { gain_dn_per_e: 0.25, read_noise_e: if read {64.0} else {0.0},
        levels: frame.levels };4],160.0,NoiseProvenance::Fallback)
}
fn correction(frame: &Frame, unity: bool) -> (crate::stack::DefectPlan, Vec<f32>) {
    let geom = frame.geometry();
    let mut map = DefectMap::empty(frame.active.width,frame.active.height,&frame.camera);
    let mut gains = vec![1.0;geom.pixels()];
    let amplitude = 1.0-1.0/PEAK;
    for y in 0..geom.height { for x in 0..geom.width {
        let radius = ((2*x) as f32+0.5-CENTRE.0 as f32).hypot((2*y) as f32+0.5-CENTRE.1 as f32);
        if radius < 32.0 {
            let phi = (std::f32::consts::PI*radius/64.0).cos().powi(2);
            let gain = if unity {1.0} else {1.0/(1.0-amplitude*phi)};
            gains[y*geom.width+x] = gain;
            map.dust.push(DustQuad { px:x as u32, py:y as u32,gain });
        }
    }}
    assert!(!map.dust.is_empty());
    if !unity {
        let max = gains.iter().copied().fold(1.0f32,f32::max);
        assert!(max>1.05 && max<=PEAK);
        assert!(gains.iter().any(|v| *v>1.0 && *v<max));
    }
    (crate::stack::DefectPlan { map,correction:Correction::DUST,floor:HotFloor(8.0),gain_dn_per_e:0.25 },gains)
}
fn seed(j: usize, read: bool) -> usize {
    let seed = 0x6a09e667u64.wrapping_add(0x9e3779b9u64.wrapping_mul(j as u64));
    (seed ^ if read {0xd1b54a32d192ed03} else {0x94d049bb133111eb}) as usize
}
fn noisy(frame: &Frame, j: usize, read: bool) -> Frame {
    // Exact existing Gaussian generator; the standardized u16 draw has1/4096 resolution.
    let geom = frame.geometry();
    let mut normals = frame.clone();
    fill_probe_noise(&mut normals,geom,32768.0,4096.0,seed(j,read)).unwrap();
    let mut output = frame.clone();
    for y in 0..frame.active.height { for x in 0..frame.active.width {
        let i = (frame.active.y+y)*frame.stride+frame.active.x+x;
        let code = normals.data[i];
        assert!(code > 0 && code < u16::MAX,"standardized generator clipping");
        let z = (code as f32-32768.0)/4096.0;
        let signal = frame.data[i] as f32-frame.levels.black;
        let sigma = if read {16.0} else {(0.25*signal).sqrt()};
        let value = (frame.data[i] as f32+sigma*z).round();
        assert!(value > frame.levels.black+512.0 && value < frame.levels.white-512.0,"source clamp margin");
        output.data[i] = value as u16;
    }}
    output
}
fn component_variance(luma: &[f32], frame: &Frame, read: bool) -> Vec<f32> {
    let mut shot = vec![0.0;luma.len()];
    luma_variance(luma,&noise_model(frame,false),&mut shot);
    if !read { return shot; }
    let mut full = vec![0.0;luma.len()];
    luma_variance(luma,&noise_model(frame,true),&mut full);
    full.iter().zip(shot).map(|(a,b)| a-b).collect()
}
fn mapped_gains(frame: &Frame, t: Similarity, gains: &[f32]) -> Vec<[f32;2]> {
    let full = frame.geometry();
    let domain = domain(frame);
    let source = PlaneRef::from_geometry(gains,full).unwrap();
    let ident = strehl_raw::identity(&frame.path);
    let ca = strehl_core::optics::profile_for_capture_env(ident.model.as_deref(),ident.lens_type3).unwrap();
    assert!(ca.is_none(),"fixed software fixture has no identified CA profile; no forced CA arm");
    let mut output = Vec::with_capacity(domain.analysis().pixels());
    for y in 0..domain.rect.height { for x in 0..domain.rect.width {
        let mut pair = [0.0;2];
        for (slot,(dx,dy)) in [(1usize,0usize),(0,1)].into_iter().enumerate() {
            let channel = strehl_core::optics::cfa_site_channel(dx,dy);
            let site = strehl_core::optics::OpticalProfile::compose(ca,channel,t);
            let (sx,sy) = site.apply_at((domain.rect.x+x) as f64+dx as f64*0.5,
                (domain.rect.y+y) as f64+dy as f64*0.5,full.width as f64*0.5,full.height as f64*0.5);
            pair[slot] = Resampler::Bilinear.sample_checked(source,sx-dx as f64*0.5,sy-dy as f64*0.5).unwrap();
            assert!(pair[slot] >= 1.0 && pair[slot] <= PEAK);
        }
        output.push(pair);
    }}
    output
}
fn local_variance(base: &[f32], planes: &[Vec<f32>], gains: &[[f32;2]], read: bool, wrong: bool) -> Vec<f32> {
    base.iter().enumerate().map(|(i,v)| {
        let delta: f32 = (0..2).map(|g| {
            let d = gains[i][g];
            if read {
                (if wrong {d-1.0} else {d*d-1.0})*256.0
            } else {
                (if wrong {d*d-1.0} else {d-1.0})*0.25*planes[g+1][i]
            }
        }).sum();
        v+0.25*delta
    }).collect()
}
fn regions(frame: &Frame, t: Similarity, size: LevelSize, band: usize) -> [Vec<usize>;2] {
    let domain = domain(frame);
    let full = frame.geometry();
    let mut roi = [Vec::new(),Vec::new()];
    for y in 0..size.height { for x in 0..size.width {
        let qx = (domain.rect.x+(x<<band)) as f64;
        let qy = (domain.rect.y+(y<<band)) as f64;
        let a = t.apply_at(qx+0.5,qy,full.width as f64*0.5,full.height as f64*0.5);
        let b = t.apply_at(qx,qy+0.5,full.width as f64*0.5,full.height as f64*0.5);
        let radius = (a.0+b.0-CENTRE.0).hypot(a.1+b.1-CENTRE.1);
        let which = if radius <= 16.0 {Some(0)} else if radius > 32.0 && radius <= 48.0 {Some(1)} else {None};
        if let Some(r) = which {
            assert!(x >= 2 && y >= 2 && x+2 < size.width && y+2 < size.height,"ROI smoothing support inside crop");
            roi[r].push(y*size.width+x);
        }
    }}
    assert!(roi.iter().all(|r| !r.is_empty()));
    roi
}
fn predicted_roi(values: &[f32], indices: &[usize], beta: f32) -> f64 {
    indices.iter().map(|i| (values[*i]*beta) as f64).sum::<f64>()/indices.len() as f64
}
fn roi_mean(values: &[f32], indices: &[usize]) -> f64 {
    indices.iter().map(|i| values[*i] as f64).sum::<f64>()/indices.len() as f64
}
struct Samples {
    size: LevelSize, indices: Vec<usize>, rois: [Vec<usize>;2],
    off: Vec<Vec<f32>>, on: Vec<Vec<f32>>,
}
impl Samples {
    fn new(size: LevelSize, rois: [Vec<usize>;2]) -> Self {
        let mut needed = vec![false;size.pixels()];
        for roi in &rois { for &i in roi {
            let (x,y) = (i%size.width,i/size.width);
            for yy in y-2..=y+2 { for xx in x-2..=x+2 { needed[yy*size.width+xx] = true; }}
        }}
        Self {size,indices:needed.iter().enumerate().filter_map(|(i,v)| v.then_some(i)).collect(),rois,
            off:Vec::with_capacity(N),on:Vec::with_capacity(N)}
    }
    fn push(&mut self, off: &[f32], on: &[f32]) {
        self.off.push(self.indices.iter().map(|i| off[*i]).collect());
        self.on.push(self.indices.iter().map(|i| on[*i]).collect());
    }
}
struct Moments { variance: Vec<f32>, mean_square: Vec<f32>, second_moment: Vec<f32> }
fn moments(samples: &[Vec<f32>], indices: &[usize], size: LevelSize, omit: Option<usize>) -> Moments {
    let n = samples.len()-usize::from(omit.is_some());
    let mut variance = vec![0.0;size.pixels()];
    let mut mean_square = variance.clone();
    let mut second_moment = variance.clone();
    for (j,&i) in indices.iter().enumerate() {
        // f64 statistical accumulation only; all source/gather/filter arrays remainf32.
        let mut sum = 0.0f64;
        let mut sq = 0.0f64;
        for (k,s) in samples.iter().enumerate() { if Some(k) != omit {
            sum += s[j] as f64;
            sq += (s[j] as f64).powi(2);
        }}
        variance[i] = ((sq-sum*sum/n as f64)/(n-1) as f64) as f32;
        mean_square[i] = (sum*sum/(n*n) as f64) as f32;
        second_moment[i] = (sq/n as f64) as f32;
    }
    Moments {variance,mean_square,second_moment}
}
fn temporal(off: &[Vec<f32>], on: &[Vec<f32>], indices: &[usize], size: LevelSize, rois: &[Vec<usize>]) -> Vec<Value> {
    assert!(off.len() == on.len() && off.len() >= 3);
    let n = off.len();
    let off_m = moments(off,indices,size,None);
    let on_m = moments(on,indices,size,None);
    let voff = kernel::smooth(&off_m.variance,size);
    let von = kernel::smooth(&on_m.variance,size);
    let boff = kernel::smooth(&off_m.mean_square,size);
    let bon = kernel::smooth(&on_m.mean_square,size);
    let soff = kernel::smooth(&off_m.second_moment,size);
    let son = kernel::smooth(&on_m.second_moment,size);
    let mut deleted = vec![Vec::with_capacity(n);rois.len()];
    for k in 0..n {
        let a = kernel::smooth(&moments(off,indices,size,Some(k)).variance,size);
        let b = kernel::smooth(&moments(on,indices,size,Some(k)).variance,size);
        for (r,roi) in rois.iter().enumerate() { deleted[r].push(roi_mean(&b,roi)-roi_mean(&a,roi)); }
    }
    rois.iter().enumerate().map(|(r,roi)| {
        let average = deleted[r].iter().sum::<f64>()/n as f64;
        let se = (((n-1) as f64/n as f64)*deleted[r].iter().map(|v| (v-average).powi(2)).sum::<f64>()).sqrt();
        let a = roi_mean(&voff,roi);
        let b = roi_mean(&von,roi);
        json!({"n":n,"measured_off":a,"measured_corrected":b,"delta":b-a,"se":se,
            "bias_power_off":roi_mean(&boff,roi),"bias_power_corrected":roi_mean(&bon,roi),
            "second_moment_off":roi_mean(&soff,roi),"second_moment_corrected":roi_mean(&son,roi),
            "jackknife_deltas":deleted[r],"roi_samples":roi.len()})
    }).collect()
}
fn scalar_temporal(off: &[f32], on: &[f32]) -> (f64,f64,f64,f64) {
    let a:Vec<_> = off.iter().map(|v| vec![*v]).collect();
    let b:Vec<_> = on.iter().map(|v| vec![*v]).collect();
    let rows = temporal(&a,&b,&[0],LevelSize {width:1,height:1},&[vec![0]]);
    let r = &rows[0];
    (r["measured_off"].as_f64().unwrap(),r["measured_corrected"].as_f64().unwrap(),
     r["delta"].as_f64().unwrap(),r["se"].as_f64().unwrap())
}
mod independent {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/native-correction-variance/independent-controls.rs"));
}
#[test]
#[ignore = "root-owned64seed correction variance diagnostic"]
fn correction_variance_transfer() {
    let literal = independent::literal_controls(scalar_temporal);
    assert!(align_cmd::fullres_gather_enabled(),"fixed full-resolution route");
    assert!(!std::env::var("STREHL_DEMOSAIC").unwrap_or_default().eq_ignore_ascii_case("directional"),"fixedMalvarroute");
    #[cfg(feature = "native-direct-planes")]
    assert_eq!(align_cmd::direct_plane_mode().unwrap(),align_cmd::DirectPlaneMode::Rounded);
    let mut rows = Vec::new();
    let mut cases = Vec::new();
    let mut unity = Vec::new();
    for field in ["flat","textured"] {
        let mut frame = fixture();
        if field == "flat" {
            for y in 0..frame.active.height { for x in 0..frame.active.width {
                let i=(frame.active.y+y)*frame.stride+frame.active.x+x;frame.data[i]=4012;
            }}
        }
        let (plan,gains) = correction(&frame,false);
        let (unity_plan,unity_gains) = correction(&frame,true);
        let local = domain(&frame).analysis();
        let sizes = level_sizes(local.width,local.height,3);
        for (mapping,t) in [("identity",Similarity::IDENTITY),("warp",super::m194c_independent_tests::variance_warp())] {
            let (off_planes,off_luma,beta) = prepare(&frame,t,None,true);
            let (on_planes,on_luma,_) = prepare(&frame,t,Some(&plan),false);
            let (unity_planes,unity_luma,unity_beta) = prepare(&frame,t,Some(&unity_plan),true);
            assert_eq!(off_planes,unity_planes);assert_eq!(off_luma,unity_luma);assert_eq!(beta,unity_beta);
            assert!(beta.len()>=2);
            let mapped = mapped_gains(&frame,t,&gains);
            let mapped_unity = mapped_gains(&frame,t,&unity_gains);
            let base_off_bands = kernel::laplacian(&off_luma,&sizes);
            assert_eq!(base_off_bands,kernel::laplacian(&unity_luma,&sizes));
            let base_on_bands = kernel::laplacian(&on_luma,&sizes);
            let zero_delta:Vec<_> = on_luma.iter().zip(&off_luma).map(|(a,b)| a-b).collect();
            assert!(zero_delta.iter().any(|v| *v != 0.0),"knowncorrectionmustbe live");
            for component in ["shot","read"] {
                let read = component == "read";
                let v0 = component_variance(&off_luma,&frame,read);
                let vc = component_variance(&on_luma,&frame,read);
                let proposed = local_variance(&vc,&on_planes,&mapped,read,false);
                let wrong = local_variance(&vc,&on_planes,&mapped,read,true);
                let unity_v = local_variance(&v0,&unity_planes,&mapped_unity,read,false);
                assert_eq!(v0,unity_v);
                let p0 = kernel::gaussian(&v0,&sizes);
                let pc = kernel::gaussian(&vc,&sizes);
                let pp = kernel::gaussian(&proposed,&sizes);
                let pw = kernel::gaussian(&wrong,&sizes);
                let pu = kernel::gaussian(&unity_v,&sizes);
                assert_eq!(p0,pu);
                unity.push(json!({"field":field,"mapping":mapping,"component":component,
                    "plane_hashes":off_planes.iter().map(|p|hash(p)).collect::<Vec<_>>(),
                    "luma":hash(&off_luma),"variance":hash(&v0),"bands":base_off_bands.iter().map(|v|hash(v)).collect::<Vec<_>>(),
                    "beta":beta,"variance_levels":p0.iter().map(|v|hash(v)).collect::<Vec<_>>() }));
                let mut samples: Vec<Samples> = (0..2).map(|k|Samples::new(sizes[k],regions(&frame,t,sizes[k],k))).collect();
                let mut consumed = Sha256::new();
                for j in 0..N {
                    let source = noisy(&frame,j,read);
                    let mut corrected_source = source.clone();
                    let tally = crate::stack::DefectTally::default();
                    crate::stack::apply_defects(&plan,&mut corrected_source,&tally,0).unwrap();
                    assert_eq!(tally.report().dust_clipped,0);
                    assert_eq!(tally.report().dust_outside,0);
                    for y in 0..source.active.height { for x in 0..source.active.width {
                        let i=(source.active.y+y)*source.stride+source.active.x+x;
                        let value=corrected_source.data[i] as f32;
                        assert!(value>source.levels.black+512.0 && value<source.levels.white-512.0,"correctedsourceclampmargin");
                    }}
                    assert!(tally.report().samples_changed>0);
                    let (p0,l0,_) = prepare(&source,t,None,false);
                    let (p1,l1,_) = prepare(&source,t,Some(&plan),false);
                    for v in p0.iter().chain(p1.iter()).flat_map(|p|p.iter()).chain(l0.iter()).chain(l1.iter()) {
                        consumed.update(v.to_bits().to_le_bytes());
                    }
                    let b0 = kernel::laplacian(&l0,&sizes);
                    let b1 = kernel::laplacian(&l1,&sizes);
                    for k in 0..2 {
                        let n0:Vec<_> = b0[k].iter().zip(&base_off_bands[k]).map(|(a,b)|a-b).collect();
                        let n1:Vec<_> = b1[k].iter().zip(&base_on_bands[k]).map(|(a,b)|a-b).collect();
                        samples[k].push(&n0,&n1);
                    }
                }
                for k in 0..2 {
                    let sample=&samples[k];
                    let stats=temporal(&sample.off,&sample.on,&sample.indices,sample.size,&sample.rois);
                    for (r,mut row) in stats.into_iter().enumerate() {
                        let roi=&sample.rois[r];
                        let v=row.as_object_mut().unwrap();
                        v.insert("field".into(),json!(field));v.insert("mapping".into(),json!(mapping));
                        v.insert("component".into(),json!(component));v.insert("band".into(),json!(k));
                        v.insert("region".into(),json!(if r==0 {"core"} else {"adjacent"}));
                        v.insert("beta".into(),json!(beta[k]));v.insert("gate".into(),json!(2.0));
                        v.insert("predicted_off".into(),json!(predicted_roi(&p0[k],roi,beta[k])));
                        v.insert("predicted_current_corrected".into(),json!(predicted_roi(&pc[k],roi,beta[k])));
                        v.insert("predicted_corrected".into(),json!(predicted_roi(&pp[k],roi,beta[k])));
                        v.insert("predicted_wrong".into(),json!(predicted_roi(&pw[k],roi,beta[k])));
                        rows.push(row);
                    }
                }
                let memory=samples.iter().map(|s|(s.off.len()+s.on.len())*s.indices.len()*4).sum::<usize>();
                assert!(memory<16<<20);
                cases.push(json!({"field":field,"mapping":mapping,"component":component,"source_seeds":(0..N).map(|j|seed(j,read) as u64).collect::<Vec<_>>(),
                    "retained_band_bytes":memory,"discrete_max_gain":gains.iter().copied().fold(1.0f32,f32::max),
                    "gain_sha256":hash(&gains),"consumed_sha256":consumed.finalize().iter().map(|v|format!("{v:02x}")).collect::<String>(),
                    "own_noiseless_off":hash(&off_luma),"own_noiseless_corrected":hash(&on_luma),
                    "deterministic_correction_luma":hash(&zero_delta),"base_beta":beta,
                    "probe_policy":"once perfield/map, fixedindex0, no correction-gain modulation"}));
            }
        }
    }
    assert_eq!(rows.len(),32);
    let get_unity = |mapping: &str| unity.iter().find(|v|v["field"]=="textured" && v["mapping"]==mapping && v["component"]=="shot").unwrap();
    assert_ne!(get_unity("identity")["luma"],get_unity("warp")["luma"],"nonidentitysamplewitness");
    assert_ne!(get_unity("identity")["beta"],get_unity("warp")["beta"],"nonidentitytransferwitness");
    let decision=independent::decide(&rows);
    let output=std::path::PathBuf::from(std::env::var_os("STREHL_CORRECTION_VARIANCE_OUT").expect("rootoutputpath"));
    let result=json!({"schema":"native-correction-variance-v1","literal_controls":literal,"rows":rows,"decision":decision,"cases":cases,"unity":unity,
        "source_fixture":"M194c native274x190 layout1 k1; flatraw4012",
        "crop_quad":[9,6,112,78],"centre_native":[137,95],"radius_native":32,"theoretical_peak_gain":PEAK,
        "noise":"existingGaussian fill(level32768,sigma4096), standardizedu16 draw; heteroscedasticGaussian shot, no photon/calibrationclaim",
        "ca":"softwarefixture unrecognized; no resolvedprofile; same heldCAguard foractual/probe/gainmapping",
        "predictions":"ownnoiselessluma; actualluma_variance full-minus-shot forread; beta fixed; no gate factor inreportedpower",
        "moment_policy":"samplevariance percoefficient N-1 then actualsmooth5;64paireddeleteonejackknife; smallROI+supportcoefficients only"});
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(&output).unwrap();
    serde_json::to_writer_pretty(file,&result).unwrap();
    println!("CORRECTION_VARIANCE_COMPLETE {}",output.display());
}
