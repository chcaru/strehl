// Test-only diagnostic; the actual full-domain consumer supplies guide and floor.
use super::*;
use serde::Deserialize;
use serde_json::{Value,json};
use sha2::{Digest,Sha256};
use std::{fs::File,io::{Read,Seek,SeekFrom,Write}};
use strehl_core::pyramid::correction_variance_diagnostic as actual;

pub(crate) const POOL_RADIUS:usize=32;
pub(crate) const PADDING:usize=48;
pub(crate) struct Fields {
    pub laplacian0:Vec<f32>,pub energy0:Vec<f32>,pub floor0:Vec<f32>,
    pub pooled_energy0:Vec<f32>,pub pooled_floor0:Vec<f32>,
}
/// Diagnostic arithmetic only. The caller must preserve the original level-zero
/// decimation phase and retain at least forty quad pixels around each sample.
/// Pool E and gate*beta[0]*variance BEFORE taking positive excess or its ratio.
pub(crate) fn measure_fields(luma:&[f32],variance:&[f32],geometry:PlaneGeometry,
    beta0:f32,gate:f32)->Result<Fields> {
    ensure!(geometry.width>=80 && geometry.height>=80 && geometry.pixels()<=512*512
        && luma.len()==geometry.pixels() && variance.len()==geometry.pixels(),"bounded field geometry");
    ensure!(luma.iter().all(|v|v.is_finite() && *v>=0.0)
        && variance.iter().all(|v|v.is_finite() && *v>=0.0)
        && beta0.is_finite() && beta0>0.0 && gate.is_finite() && gate>0.0,"invalid injected diagnostic input");
    let sizes=level_sizes(geometry.width,geometry.height,1);
    ensure!(sizes.len()==2,"diagnostic requires one complete finest Laplacian");
    let laplacian0=actual::laplacian(luma,&sizes).remove(0);
    let energy0=actual::energy(&laplacian0,sizes[0]);
    // Exact multiplication order of BandMerge::add_frame_with_gain_impl.
    let floor0=variance.iter().map(|v|gate*beta0*v.max(0.0)).collect::<Vec<_>>();
    let mut scratch=vec![0.0;geometry.pixels()];
    let mut pooled_energy0=vec![0.0;geometry.pixels()];
    let mut pooled_floor0=vec![0.0;geometry.pixels()];
    strehl_core::boxfilter::box_mean(&energy0,geometry,POOL_RADIUS,&mut scratch,&mut pooled_energy0);
    strehl_core::boxfilter::box_mean(&floor0,geometry,POOL_RADIUS,&mut scratch,&mut pooled_floor0);
    ensure!(energy0.iter().chain(&floor0).chain(&pooled_energy0).chain(&pooled_floor0)
        .all(|v|v.is_finite() && *v>=0.0),"invalid computed diagnostic energy/floor");
    Ok(Fields{laplacian0,energy0,floor0,pooled_energy0,pooled_floor0})
}

/// This is the production weight's monotone SNR term before /64 and exponent.
/// A zero excess ties at zero; floor<1 uses the same one-DN-squared denominator.
pub(crate) fn excess_ratio(energy:f32,floor:f32)->f32 {(energy-floor).max(0.0)/floor.max(1.0)}

pub(crate) fn extract(values:&[f32],full:PlaneGeometry,rect:align_cmd::CropRect)->Result<Vec<f32>> {
    ensure!(values.len()==full.pixels() && rect.width>0 && rect.height>0
        && rect.x.checked_add(rect.width).is_some_and(|v|v<=full.width)
        && rect.y.checked_add(rect.height).is_some_and(|v|v<=full.height),"diagnostic crop outside consumed guide");
    let mut out=Vec::with_capacity(rect.width*rect.height);
    for y in rect.y..rect.y+rect.height {out.extend_from_slice(&values[y*full.width+rect.x..y*full.width+rect.x+rect.width]);}
    Ok(out)
}
pub(crate) fn guide_rect(window:[usize;4])->align_cmd::CropRect {
    assert!(window.iter().all(|v|v%2==0));
    let x=(window[0]/2-PADDING)&!1;let y=(window[1]/2-PADDING)&!1;
    let right=((window[0]+window[2])/2+PADDING+1)&!1;
    let bottom=((window[1]+window[3])/2+PADDING+1)&!1;
    align_cmd::CropRect{x,y,width:right-x,height:bottom-y}
}
const WINDOWS:[(&str,[usize;4]);2]=[
    ("facet-edges",[2500,2700,384,384]),("dark-inclusion",[3050,1850,384,384]),
];
const POINTS:[(&str,usize,[usize;2]);6]=[
    ("facet-core",0,[2624,2906]),("facet-fan",0,[2602,2945]),("facet-rim",0,[2760,2998]),
    ("dark-core",1,[3080,2150]),("dark-fan",1,[3102,2203]),("nearby-structure",1,[3240,2070]),
];
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema:u32,source_dir:PathBuf,warp_map:PathBuf,warp_map_sha256:String,out_dir:PathBuf,
    expected_crop:[usize;4],expected_xyz_to_cam:[[f32;3];3],expected_wb_bits:[u32;3],tone:[f32;3],weight_trace_dir:PathBuf,
}
fn hash_file(path:&Path)->Result<String> {
    let mut f=File::open(path)?;let mut h=Sha256::new();let mut buf=vec![0u8;1<<20];
    loop{let n=f.read(&mut buf)?;if n==0{break;}h.update(&buf[..n]);}
    Ok(h.finalize().iter().map(|v|format!("{v:02x}")).collect())
}
fn save(path:&Path,value:&Value)->Result<()> {
    let mut f=std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut f,value)?;writeln!(f)?;Ok(())
}
struct Source<'a>{frame:&'a Frame,index:usize}
impl PyramidFrameSource for Source<'_> {
    fn len(&self)->usize{70}
    fn decode(&self,index:usize)->Result<Frame>{ensure!(index==self.index,"wrong source index");Ok(self.frame.clone())}
}
fn nominate(scores:&[f32])->Value {
    let max=scores.iter().copied().fold(f32::NEG_INFINITY,f32::max);
    let ties=scores.iter().enumerate().filter_map(|(i,&v)|(v==max).then_some(i)).collect::<Vec<_>>();
    json!({"max":max,"first_index":ties[0],"exact_tied_indices":ties,"all_zero":max==0.0})
}

#[test]
#[ignore="root-owned bounded seventy-frame diagnostic; no candidate merge"]
fn actual_green_fine_support()->Result<()> {
    let started=Instant::now();
    let config_path=PathBuf::from(std::env::var_os("STREHL_FINE_SUPPORT_CONFIG").context("STREHL_FINE_SUPPORT_CONFIG required")?);
    let cfg:Config=serde_json::from_slice(&std::fs::read(&config_path)?)?;
    ensure!(cfg.schema==1 && cfg.expected_crop==[28,19,3460,2306],"fixed vitamin-C crop required");
    ensure!(cfg.tone.map(f32::to_bits)==[0.090420f32,0.914606,0.55].map(f32::to_bits),"held tone differs");
    ensure!(cfg.source_dir.is_absolute() && cfg.source_dir.file_name().and_then(|v|v.to_str())==Some("crystalized-vitamin-c-cpl"),"wrong source scope");
    ensure!(align_cmd::fullres_gather_enabled() && gatefloor::enabled()
        && align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded,"actual fullres/rounded/measured-probe path required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none(),"local placement excluded");
    ensure!(hash_file(&cfg.warp_map)?==cfg.warp_map_sha256,"held map changed");
    let paths=crate::raw_paths(&cfg.source_dir,None)?;
    ensure!(paths.len()==70 && paths.iter().enumerate().all(|(i,p)|p.file_name().and_then(|v|v.to_str())==Some(format!("DSC{:05}.ARW",i+94).as_str())),"all seventy original frames required");
    let map=WarpMap::load(&cfg.warp_map)?;
    map.check_stack(&StackIdentity::from_paths("crystalized-vitamin-c-cpl",&paths)?)?;
    ensure!(map.resampler()==Resampler::CatmullRom && map.placed_count()==70,"held map coverage/resampler");
    let (map,fit)=align_cmd::cover_or_explain(map,align_cmd::CoverMode::Crop);
    let crop=fit.rect().context("missing actual crop")?;
    ensure!([crop.x,crop.y,crop.width,crop.height]==cfg.expected_crop,"actual crop changed");
    let full=map.geometry();ensure!(full==PlaneGeometry{width:3516,height:2344},"full geometry changed");
    let domain=PyramidDomain::cropped(full,crop)?;let analysis=domain.analysis();
    let first=strehl_raw::decode(&paths[0])?;
    let levels=first.levels;let wb=first.wb_coeffs;let active=first.active;
    let normalized_wb=first.wb_gains().context("invalid first-frame WB")?;
    ensure!(first.camera=="ILCE-7CM2" && first.iso==Some(100.0) && levels==Levels{black:512.0,white:15360.0}
        && first.geometry()==full && first.xyz_to_cam_rgb()==Some(cfg.expected_xyz_to_cam)
        && normalized_wb.map(f32::to_bits)==cfg.expected_wb_bits,"held first-frame metadata changed");
    let merge_cfg=MergeConfig::default();
    ensure!(merge_cfg.bands==7 && merge_cfg.gate==2.0 && merge_cfg.significance_scale==0.0
        && merge_cfg.admission==AdmissionMode::HardFloor,"diagnostic requires held default admission");
    let noise=profile::noise_model_for(&first.camera,first.iso,levels);
    let plan=phase_packed_rgb::full_stack::chunk_plan(full,first.allocated_bytes(),70,merge_cfg);
    let pool=ThreadPoolBuilder::new().num_threads(band_workers(plan.planning_bytes,70)?).build()?;
    let workspace=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize()?;
    ensure!(!cfg.out_dir.exists() && cfg.out_dir.parent().context("output parent")?.canonicalize()?.starts_with(workspace.join("experiments").canonicalize()?),"fresh workspace output directory required");
    let dims:Value=serde_json::from_slice(&std::fs::read(cfg.weight_trace_dir.join("weights-dims.json"))?)?;
    ensure!(dims["frames"]==70 && dims["bands"][0]["w"]==analysis.width && dims["bands"][0]["h"]==analysis.height,"reference weight dump dimensions changed");
    let trace_path=cfg.weight_trace_dir.join("weights-b0-arg.i32");
    ensure!(std::fs::metadata(&trace_path)?.len()==(analysis.pixels()*4) as u64,"reference arg extent");
    let trace_sha=hash_file(&trace_path)?;let mut trace=File::open(&trace_path)?;
    let mut traced=Vec::new();
    for &(_,_,[x,y]) in &POINTS {
        trace.seek(SeekFrom::Start(((y/2*analysis.width+x/2)*4) as u64))?;
        let mut bytes=[0u8;4];trace.read_exact(&mut bytes)?;traced.push(i32::from_le_bytes(bytes));
    }
    let matrix=color::camera_to_srgb(cfg.expected_xyz_to_cam).context("held matrix singular")?.with_saturation(levels,normalized_wb,1.0);
    let mut dev=image_out::OutputSpace::Srgb.develop(Some(matrix));
    dev.tone=Some(image_out::Tone{black:cfg.tone[0],white:cfg.tone[1],contrast:cfg.tone[2]});dev.exposure_gain=1.0;
    std::fs::create_dir(&cfg.out_dir)?;
    let rects=WINDOWS.map(|(_,w)|guide_rect(w));
    ensure!(rects.iter().all(|r|r.x%2==0 && r.y%2==0),"level-zero decimation phase changed");
    save(&cfg.out_dir.join("started.json"),&json!({"schema":1,"config_sha256":hash_file(&config_path)?,
        "source_dir":cfg.source_dir,"map_sha256":cfg.warp_map_sha256,"crop":cfg.expected_crop,"gate":merge_cfg.gate,
        "pool_radius_quads":POOL_RADIUS,"padding_quads":PADDING,"floor":"current actual BandWorker beta[0] * current injected variance * gate, production multiplication order",
        "guide_rectangles":rects.iter().map(|r|[r.x,r.y,r.width,r.height]).collect::<Vec<_>>(),
        "weight_trace_sha256":trace_sha,"weight_trace_centre_arg":traced,
        "interpretation":"Fine-guide diagnostic, not output RGB winners or image-quality evidence; original+pooled SNR use max(floor,1)."}))?;
    let mut worker=BandWorker::new(domain,merge_cfg);let mut first=Some(first);
    let mut frame_records=Vec::new();
    let mut scores:Vec<Vec<f32>>=(0..6).map(|_|Vec::new()).collect();
    let mut pooled_scores:Vec<Vec<f32>>=(0..6).map(|_|Vec::new()).collect();
    pool.install(||->Result<()> {
        for (index,path) in paths.iter().enumerate() {
            let before=std::fs::metadata(path)?;
            let frame=match first.take(){Some(f)=>f,None=>strehl_raw::decode(path)?};
            ensure!(frame.active==active && frame.levels==levels && frame.iso==Some(100.0) && frame.camera=="ILCE-7CM2"
                && frame.wb_gains().context("invalid frame WB")?.map(f32::to_bits)==cfg.expected_wb_bits && frame.xyz_to_cam_rgb()==Some(cfg.expected_xyz_to_cam),"metadata drift frame {index}");
            let source=Source{frame:&frame,index};
            ensure!(worker.fold(&source,index,levels,&noise,Some(&map),None)?,"actual consumer refused frame {index}");
            let beta0=*worker.beta.first().context("actual measured fine-band beta absent")?;
            let mut observations=Vec::new();
            for (window_index,rect) in rects.iter().copied().enumerate() {
                let luma=extract(&worker.luma,analysis,rect)?;
                let variance=extract(&worker.var,analysis,rect)?;
                let fields=measure_fields(&luma,&variance,rect.geometry(),beta0,merge_cfg.gate)?;
                for (point_index,&(name,wi,[x,y])) in POINTS.iter().enumerate().filter(|(_,p)|p.1==window_index) {
                    let qx=x/2;let qy=y/2;let lx=qx-rect.x;let ly=qy-rect.y;
                    ensure!(lx>=40 && ly>=40 && lx+40<rect.width && ly+40<rect.height,"point lacks complete pooled operator support");
                    let mut samples=Vec::new();
                    for dy in -1isize..=1 {for dx in -1isize..=1 {
                        let sx=(lx as isize+dx) as usize;let sy=(ly as isize+dy) as usize;let i=sy*rect.width+sx;
                        let e=fields.energy0[i];let f=fields.floor0[i];let pe=fields.pooled_energy0[i];let pf=fields.pooled_floor0[i];
                        let ratio=excess_ratio(e,f);let pooled_ratio=excess_ratio(pe,pf);
                        if dx==0 && dy==0{scores[point_index].push(ratio);pooled_scores[point_index].push(pooled_ratio);}
                        samples.push(json!({"output_quad":[rect.x+sx,rect.y+sy],"offset_quad":[dx,dy],
                            "luma_dn":luma[i],"variance_dn2":variance[i],"laplacian0_dn":fields.laplacian0[i],
                            "energy0_dn2":e,"floor0_dn2":f,"excess_snr":ratio,"denominator_clamped":f<1.0,
                            "pooled_energy0_dn2":pe,"pooled_floor0_dn2":pf,"pooled_excess_snr":pooled_ratio,"pooled_denominator_clamped":pf<1.0}));
                    }}
                    observations.push(json!({"name":name,"window":WINDOWS[wi].0,"output_native":[x,y],
                        "native_cfa_phase":[x%2,y%2],"containing_quad":[qx,qy],"samples":samples}));
                }
                if [28usize,33,52,69].contains(&index) {
                    let w=WINDOWS[window_index].1;
                    let view=align_cmd::CropRect{x:w[0]/2,y:w[1]/2,width:w[2]/2,height:w[3]/2};
                    let planes=worker.planes.iter().map(|p|extract(p,analysis,view)).collect::<Result<Vec<_>>>()?;
                    phase_packed_rgb::full_stack::write_planes(&cfg.out_dir.join(format!("{}-gathered-{index:02}.tiff",WINDOWS[window_index].0)),&planes,view,levels,wb,&dev)?;
                }
            }
            let after=std::fs::metadata(path)?;
            ensure!(before.len()==after.len() && before.modified()?==after.modified()?,"original metadata changed");
            frame_records.push(json!({"index":index,"file":path.file_name().map(|v|v.to_string_lossy()),"beta":worker.beta,"points":observations}));
            eprintln!("fine-support {}/70, {:.1}s",index+1,started.elapsed().as_secs_f64());
        }
        Ok(())
    })?;
    let nominations=POINTS.iter().enumerate().map(|(i,&(name,_,xy))| {
        let original=nominate(&scores[i]);let pooled=nominate(&pooled_scores[i]);
        json!({"name":name,"output_native":xy,"unpooled":original,"pooled":pooled,
            "actual_weight_dump_arg":traced[i],"unpooled_arg_matches_dump":original["first_index"]==traced[i],
            "caveat":"A max-SNR tie can differ from clamped exponent weight ties; mismatches require inspection, not threshold relaxation."})
    }).collect::<Vec<_>>();
    save(&cfg.out_dir.join("measurements.json"),&json!({"schema":1,"status":"DIAGNOSTIC_COMPLETE","frames":frame_records,
        "nominations":nominations,"seconds":started.elapsed().as_secs_f64(),"pool_radius_quads":POOL_RADIUS,
        "scope":"No candidate fusion or image-quality acceptance. Nearby structural points are counterexamples, not tuning targets."}))?;
    eprintln!("FINE_SUPPORT_NOMINATIONS {}",serde_json::to_string(&nominations)?);
    Ok(())
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/fine-support-guidance/independent-controls.rs"));
}
