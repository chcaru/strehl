// Read-only actual writer observer, adapted from the dormant garnet stage probe.
use super::*;
use anyhow::{bail, ensure};
use serde::{Deserialize, Serialize};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{io::{Read, Write}, path::PathBuf, sync::Mutex};

const NATIVE: [usize;2] = [6792,4528];
const TARGETS: [(&str,[usize;4]);2] = [
    ("reflection",[3628,1658,384,384]),("colour-control",[2128,2228,384,384])];

#[cfg(test)]
mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/opal-headroom/independent-stage-controls.rs"));
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema:u32, cache:PathBuf, cache_sha256:String, expected_current_tiff:PathBuf,
    expected_current_file_sha256:String, expected_shoulder_tiff:PathBuf,
    expected_shoulder_file_sha256:String, out_dir:PathBuf,
}
#[derive(Default, Serialize)]
struct Counts {
    pixels:usize, pin_pixels:usize, pin_channels:[usize;3], clip_changed:usize,
    rolloff_changed:usize, mhc_has_negative:usize, developed_nonpositive_luma:usize,
    post_tone_any_over_one:usize, post_tone_luma_ge_one:usize, post_tone_any_negative:usize,
    shoulder_changed:usize, gamut_changed:usize, gamut_exact_white:usize,
    shoulder_gamut_changed:usize, shoulder_gamut_exact_white:usize,
}
struct Pixel {
    camera:[f32;3], pin:u8, clipped:[f32;3], rolled:[f32;3], developed:[f32;3],
    toned:[f32;3], shoulder:[f32;3], gamut:[f32;3], shoulder_gamut:[f32;3],
    rgb:[u16;3], shoulder_rgb:[u16;3],
}
fn same(a:[f32;3],b:[f32;3])->bool {a.map(f32::to_bits)==b.map(f32::to_bits)}
fn observe_pixel(camera:[f32;3],dev:&Develop)->Result<Pixel> {
    let render=dev.matrix.as_ref().context("matrix absent")?;
    let tone=dev.tone.as_ref().context("tone absent")?;
    let ceiling=render.ceiling();
    let pin=u8::from(camera[0]>=ceiling[0])|(u8::from(camera[1]>=ceiling[1])<<1)|(u8::from(camera[2]>=ceiling[2])<<2);
    let clipped=render.clip_highlights(camera);
    let rolled=strehl_core::highlight::desaturate(ceiling,render.top(),render.matrix(),clipped);
    let developed=render.develop(camera);
    ensure!(same(developed,color::apply(render.matrix(),rolled)),"observed develop decomposition differs");
    let gain=tone.gain(luma709(developed))*dev.exposure_gain;
    let toned=developed.map(|v|v*gain);
    let shoulder=highlight_rendering::shoulder_rgb(toned);
    let gamut=gamut_map(toned);let shoulder_gamut=gamut_map(shoulder);
    // Both final paths are the existing actual writer helper, not a new renderer.
    let rgb=highlight_rendering::pixel(camera,dev,highlight_rendering::Arm::Current);
    let shoulder_rgb=highlight_rendering::pixel(camera,dev,highlight_rendering::Arm::Shoulder);
    let encode=|v:[f32;3]|v.map(|x|(s_curve(color::srgb_encode(x),tone.contrast)*65535.0+0.5) as u16);
    ensure!(encode(gamut)==rgb&&encode(shoulder_gamut)==shoulder_rgb,"stage chain differs from actual writer");
    ensure!(camera.into_iter().chain(clipped).chain(rolled).chain(developed).chain(toned)
        .chain(shoulder).chain(gamut).chain(shoulder_gamut).all(f32::is_finite),"nonfinite stage value");
    Ok(Pixel{camera,pin,clipped,rolled,developed,toned,shoulder,gamut,shoulder_gamut,rgb,shoulder_rgb})
}
impl Counts {
    fn add(&mut self,p:&Pixel) {
        self.pixels+=1;self.pin_pixels+=usize::from(p.pin!=0);
        for c in 0..3{self.pin_channels[c]+=usize::from(p.pin&(1<<c)!=0);}
        self.clip_changed+=usize::from(!same(p.camera,p.clipped));
        self.rolloff_changed+=usize::from(!same(p.clipped,p.rolled));
        self.mhc_has_negative+=usize::from(p.camera.iter().any(|&v|v<0.0));
        self.developed_nonpositive_luma+=usize::from(luma709(p.developed)<=0.0);
        self.post_tone_any_over_one+=usize::from(p.toned.iter().any(|&v|v>1.0));
        self.post_tone_luma_ge_one+=usize::from(luma709(p.toned)>=1.0);
        self.post_tone_any_negative+=usize::from(p.toned.iter().any(|&v|v<0.0));
        self.shoulder_changed+=usize::from(!same(p.toned,p.shoulder));
        self.gamut_changed+=usize::from(!same(p.toned,p.gamut));
        self.gamut_exact_white+=usize::from(p.gamut==[1.0;3]);
        self.shoulder_gamut_changed+=usize::from(!same(p.shoulder,p.shoulder_gamut));
        self.shoulder_gamut_exact_white+=usize::from(p.shoulder_gamut==[1.0;3]);
    }
}
#[derive(Serialize)]
struct PinSupport {output_native_xy:[usize;2],pin_channels:u8,support_index:usize,
    all_25_merged_cfa_samples_below_own_ceiling:bool,max_cfa_ceiling_fraction:f32}
struct Region {
    name:&'static str,roi:[usize;4],counts:Counts,stages:[Vec<f32>;8],pin_channels:Vec<u8>,
    rgb:Vec<u16>,shoulder_rgb:Vec<u16>,pin_support:Vec<PinSupport>,support_samples:Vec<f32>,
}
impl Region {fn new(name:&'static str,roi:[usize;4])->Self {Self{name,roi,counts:Counts::default(),
    stages:std::array::from_fn(|_|Vec::with_capacity(roi[2]*roi[3]*3)),pin_channels:vec![],
    rgb:vec![],shoulder_rgb:vec![],pin_support:vec![],support_samples:vec![]}}}
struct Trace {whole:Counts,regions:Vec<Region>,current_rgb_sha256:String,shoulder_rgb_sha256:String}
static RUN:Mutex<()>=Mutex::new(());
static STATE:Mutex<Option<Option<Trace>>>=Mutex::new(None);
struct Reset;
impl Drop for Reset{fn drop(&mut self){if let Ok(mut s)=STATE.lock(){*s=None;}}}
fn capture<T>(write:impl FnOnce()->Result<T>)->Result<(T,Trace)> {
    let _run=RUN.try_lock().map_err(|_|anyhow::anyhow!("observer busy/poisoned"))?;
    {let mut s=STATE.lock().map_err(|_|anyhow::anyhow!("observer poisoned"))?;ensure!(s.is_none(),"nested observer");*s=Some(None);}
    let _reset=Reset;let result=write()?;
    let trace=STATE.lock().map_err(|_|anyhow::anyhow!("observer poisoned"))?.take().flatten().context("observer did not run")?;
    Ok((result,trace))
}
fn support(m:&Mosaic<'_>,x:usize,y:usize,ceiling:[f32;3])->Result<([f32;25],bool,f32)> {
    ensure!(x>=2&&y>=2&&x+2<m.width&&y+2<m.height,"frozen support touches border");
    let mut values=[0.0;25];let mut below=true;let mut fraction=f32::NEG_INFINITY;
    for dy in 0..5{for dx in 0..5{
        let xx=x+dx-2;let yy=y+dy-2;let v=m.data[yy*m.width+xx];
        let channel=match (yy%2,xx%2){(0,0)=>0,(1,1)=>2,_=>1};
        ensure!(v.is_finite()&&ceiling[channel].is_finite()&&ceiling[channel]>0.0,"invalid support");
        values[dy*5+dx]=v;below&=v<ceiling[channel];fraction=fraction.max(v/ceiling[channel]);
    }}Ok((values,below,fraction))
}

/// Hook once after actual resolve_tone; inactive calls return without work.
pub(crate) fn observe_mosaic(m:&Mosaic<'_>,dev:&Develop)->Result<()> {
    let mut slot=STATE.lock().map_err(|_|anyhow::anyhow!("observer poisoned"))?;
    let Some(target)=slot.as_mut() else{return Ok(());};ensure!(target.is_none(),"observer called twice");
    ensure!([m.width,m.height]==NATIVE&&dev.srgb&&dev.wants_tone&&dev.tone.is_some(),"frozen opal writer required");
    ensure!(std::env::var_os(strehl_core::demosaic::DEMOSAIC_ENV).is_none()
        &&std::env::var_os(strehl_core::highlight::KNEE_ENV).is_none(),"default MHC and sensor knee required");
    let ceiling=dev.matrix.as_ref().context("matrix")?.ceiling();
    let mut trace=Trace{whole:Counts::default(),regions:TARGETS.into_iter().map(|(n,r)|Region::new(n,r)).collect(),
        current_rgb_sha256:String::new(),shoulder_rgb_sha256:String::new()};
    let mut current_hash=Sha256::new();let mut shoulder_hash=Sha256::new();
    let mut row=vec![0.0;3*m.width];let mut current_bytes=Vec::with_capacity(6*m.width);let mut shoulder_bytes=Vec::with_capacity(6*m.width);
    for y in 0..m.height {
        // Same actual full-context MHC function and full mosaic as the real writer.
        demosaic_row(m,y,&mut row);current_bytes.clear();shoulder_bytes.clear();
        for x in 0..m.width {
            let p=observe_pixel([row[3*x],row[3*x+1],row[3*x+2]],dev)?;trace.whole.add(&p);
            for v in p.rgb{current_bytes.extend_from_slice(&v.to_le_bytes());}
            for v in p.shoulder_rgb{shoulder_bytes.extend_from_slice(&v.to_le_bytes());}
            for region in &mut trace.regions {
                let [rx,ry,rw,rh]=region.roi;if x<rx||x>=rx+rw||y<ry||y>=ry+rh{continue;}
                region.counts.add(&p);region.pin_channels.push(p.pin);region.rgb.extend_from_slice(&p.rgb);
                region.shoulder_rgb.extend_from_slice(&p.shoulder_rgb);
                for(dst,v)in region.stages.iter_mut().zip([p.camera,p.clipped,p.rolled,p.developed,p.toned,p.shoulder,p.gamut,p.shoulder_gamut]){dst.extend_from_slice(&v);}
                if p.pin!=0 {let(values,below,fraction)=support(m,x,y,ceiling)?;
                    region.pin_support.push(PinSupport{output_native_xy:[x,y],pin_channels:p.pin,
                        support_index:region.support_samples.len()/25,all_25_merged_cfa_samples_below_own_ceiling:below,
                        max_cfa_ceiling_fraction:fraction});region.support_samples.extend_from_slice(&values);}
            }
        }
        current_hash.update(&current_bytes);shoulder_hash.update(&shoulder_bytes);
    }
    trace.current_rgb_sha256=hex(current_hash.finalize());trace.shoulder_rgb_sha256=hex(shoulder_hash.finalize());
    ensure!(trace.whole.pixels==NATIVE[0]*NATIVE[1]&&trace.regions.iter().all(|r|r.counts.pixels==r.roi[2]*r.roi[3]),"incomplete scan");
    *target=Some(trace);Ok(())
}
fn hex(bytes:impl AsRef<[u8]>)->String{bytes.as_ref().iter().map(|v|format!("{v:02x}")).collect()}
fn file_hash(path:&Path)->Result<String>{let mut input=std::io::BufReader::new(std::fs::File::open(path)?);let mut h=Sha256::new();let mut b=[0u8;65536];
    loop{let n=input.read(&mut b)?;if n==0{break;}h.update(&b[..n]);}Ok(hex(h.finalize()))}
fn f32_hash(v:&[f32])->String{let mut h=Sha256::new();for chunk in v.chunks(16384){let b:Vec<_>=chunk.iter().flat_map(|v|v.to_bits().to_le_bytes()).collect();h.update(b);}hex(h.finalize())}
fn u16_hash(v:&[u16])->String{let mut h=Sha256::new();for chunk in v.chunks(32768){let b:Vec<_>=chunk.iter().flat_map(|v|v.to_le_bytes()).collect();h.update(b);}hex(h.finalize())}
fn create(path:&Path)->Result<std::fs::File>{Ok(std::fs::OpenOptions::new().write(true).create_new(true).open(path)?)}
fn save(path:&Path,v:&serde_json::Value)->Result<()>{let mut f=create(path)?;serde_json::to_writer_pretty(&mut f,v)?;writeln!(f)?;Ok(())}
fn save_f32(path:&Path,v:&[f32])->Result<()>{let mut f=std::io::BufWriter::new(create(path)?);for chunk in v.chunks(16384){let b:Vec<_>=chunk.iter().flat_map(|v|v.to_bits().to_le_bytes()).collect();f.write_all(&b)?;}f.flush()?;Ok(())}
fn read_rgb(path:&Path)->Result<([usize;2],Vec<u16>,Vec<u8>)>{let mut d=tiff::decoder::Decoder::new(std::io::BufReader::new(std::fs::File::open(path)?))?;
    let(w,h)=d.dimensions()?;ensure!(d.colortype()?==tiff::ColorType::RGB(16),"RGB16 required");let icc=d.get_tag_u8_vec(tiff::tags::Tag::IccProfile)?;ensure!(!icc.is_empty(),"ICC absent");
    let p=match d.read_image()?{tiff::decoder::DecodingResult::U16(v)=>v,_=>bail!("u16 required")};ensure!(p.len()==w as usize*h as usize*3&&!d.more_images(),"invalid shape/pages");Ok(([w as usize,h as usize],p,icc))}
fn roi_rgb(v:&[u16],r:[usize;4])->Vec<u16>{let[x,y,w,h]=r;let mut out=Vec::with_capacity(w*h*3);for yy in y..y+h{out.extend_from_slice(&v[3*(yy*NATIVE[0]+x)..3*(yy*NATIVE[0]+x+w)]);}out}

#[test]
#[ignore="root-owned current opal stage observer; exact complete cache/factorial required"]
fn opal_cached_stage_trace()->Result<()> {
    use crate::merge_cmd::full_stack_source_prior as cache;
    let path=PathBuf::from(std::env::var_os("STREHL_OPAL_STAGE_CONFIG").context("config required")?);
    let config_bytes=std::fs::read(&path)?;let cfg:Config=serde_json::from_slice(&config_bytes)?;
    ensure!(cfg.schema==1&&[&cfg.cache,&cfg.expected_current_tiff,&cfg.expected_shoulder_tiff,&cfg.out_dir].iter().all(|p|p.is_absolute()),"absolute config required");
    ensure!(file_hash(&cfg.cache)?==cfg.cache_sha256&&file_hash(&cfg.expected_current_tiff)?==cfg.expected_current_file_sha256
        &&file_hash(&cfg.expected_shoulder_tiff)?==cfg.expected_shoulder_file_sha256,"input hash changed");
    ensure!(crate::merge_cmd::matched_source_tests::pinned_tone().is_none(),"unrelated pinned tone active");
    let(metadata,planes)=cache::read_cache(&cfg.cache)?;
    ensure!(metadata.phase=="full"&&metadata.arm=="baseline"&&metadata.frames==155&&metadata.reference==77
        &&metadata.crop==[60,40,3396,2264],"frozen current opal cache required");
    let before:Vec<_>=planes.iter().map(|p|f32_hash(p)).collect();ensure!(before==metadata.plane_sha256,"cache plane binding");
    let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize()?;
    ensure!(!cfg.out_dir.exists()&&cfg.out_dir.parent().context("parent")?.canonicalize()?.starts_with(root.join("experiments").canonicalize()?),"fresh workspace directory required");
    std::fs::create_dir(&cfg.out_dir)?;
    let off=cfg.out_dir.join("observer-off.tiff");
    let(_,off_dev)=highlight_rendering::with_arm(highlight_rendering::Arm::Current,||cache::write_current(&off,&planes,&metadata))?;
    let(dims,current,icc)=read_rgb(&off)?;let(old_dims,retained,old_icc)=read_rgb(&cfg.expected_current_tiff)?;
    ensure!(dims==NATIVE&&old_dims==dims&&current==retained&&icc==old_icc,"current cache output differs");drop(retained);
    let(shoulder_dims,shoulder,shoulder_icc)=read_rgb(&cfg.expected_shoulder_tiff)?;
    ensure!(shoulder_dims==NATIVE&&shoulder_icc==icc,"held shoulder output dimensions/ICC differ");
    let on=cfg.out_dir.join("observer-on.tiff");
    let((_,on_dev),trace)=capture(||highlight_rendering::with_arm(highlight_rendering::Arm::Current,||cache::write_current(&on,&planes,&metadata)))?;
    let output_hash=file_hash(&off)?;ensure!(output_hash==file_hash(&on)?&&off_dev==on_dev,"observer perturbed complete output/development");
    ensure!(trace.current_rgb_sha256==u16_hash(&current)&&trace.shoulder_rgb_sha256==u16_hash(&shoulder),"observed whole current/shoulder writer hashes differ");
    let mut regions=Vec::new();
    for region in trace.regions {
        ensure!(region.rgb==roi_rgb(&current,region.roi)&&region.shoulder_rgb==roi_rgb(&shoulder,region.roi),"ROI mismatch");
        let dir=cfg.out_dir.join(region.name);std::fs::create_dir(&dir)?;let mut artifacts=Vec::new();
        for(name,data)in ["mhc-camera-rgb","post-clip-camera-rgb","post-rolloff-camera-rgb","post-develop-linear-srgb",
            "post-tone-linear-srgb","post-shoulder-linear-srgb","post-gamut-linear-srgb","post-shoulder-gamut-linear-srgb"].iter().zip(&region.stages){
            let filename=format!("{name}.f32");let dest=dir.join(&filename);save_f32(&dest,data)?;
            artifacts.push(json!({"file":filename,"sha256":file_hash(&dest)?,"shape":[region.roi[3],region.roi[2],3],"dtype":"f32-le","layout":"row-major interleaved"}));}
        let pin=dir.join("pin-channels.u8");create(&pin)?.write_all(&region.pin_channels)?;
        artifacts.push(json!({"file":"pin-channels.u8","sha256":file_hash(&pin)?,"shape":[region.roi[3],region.roi[2]],"dtype":"u8","meaning":"bit0 R>=ceiling_R,bit1 G>=ceiling_G,bit2 B>=ceiling_B; actual post-MHC camera predicate"}));
        let support_path=dir.join("pin-cfa-support.f32");save_f32(&support_path,&region.support_samples)?;
        artifacts.push(json!({"file":"pin-cfa-support.f32","sha256":file_hash(&support_path)?,"shape":[region.pin_support.len(),5,5],"dtype":"f32-le","layout":"pin record order,dy=-2..2,dx=-2..2","space":"actual merged normalized full mosaic; not original RAW samples"}));
        let evidence=dir.join("pin-support.json");save(&evidence,&serde_json::to_value(&region.pin_support)?)?;
        artifacts.push(json!({"file":"pin-support.json","sha256":file_hash(&evidence)?}));
        let interpolation_pins=region.pin_support.iter().filter(|p|p.all_25_merged_cfa_samples_below_own_ceiling).count();
        regions.push(json!({"name":region.name,"output_native_xywh":region.roi,
            "full_active_native_xywh":[region.roi[0]+120,region.roi[1]+80,region.roi[2],region.roi[3]],"counts":region.counts,
            "pins_with_all_merged_cfa_support_below_own_ceiling":interpolation_pins,"artifacts":artifacts,
            "current_rgb16_sha256":u16_hash(&region.rgb),"shoulder_rgb16_sha256":u16_hash(&region.shoulder_rgb)}));
    }
    let binary=cfg.cache.parent().context("cache parent")?.join(&metadata.binary);
    ensure!(planes.iter().map(|p|f32_hash(p)).collect::<Vec<_>>()==before&&file_hash(&binary)?==metadata.binary_sha256
        &&file_hash(&cfg.cache)?==cfg.cache_sha256&&file_hash(&cfg.expected_current_tiff)?==cfg.expected_current_file_sha256
        &&file_hash(&cfg.expected_shoulder_tiff)?==cfg.expected_shoulder_file_sha256&&std::fs::read(path)?==config_bytes,"observer changed inputs");
    save(&cfg.out_dir.join("receipt.json"),&json!({"schema":1,"status":"OPAL_STAGE_TRACE_COMPLETE","raw_reads":0,
        "native_dimensions":NATIVE,"resolved_development":off_dev,"whole_counts":trace.whole,"regions":regions,
        "current_rgb16_sha256":trace.current_rgb_sha256,"shoulder_rgb16_sha256":trace.shoulder_rgb_sha256,
        "whole_current_and_shoulder_pixels_exact":true,"observer_on_off_file_exact":true,"observer_on_off_file_sha256":output_hash,
        "retained_current_pixels_and_icc_exact":true,"merged_planes_unchanged":true,"scope":"Read-only stage attribution. Counts are not quality scores or original RAW clipping estimates.","causal_verdict":null}))?;
    eprintln!("OPAL_STAGE_TRACE_COMPLETE {}",cfg.out_dir.display());Ok(())
}

#[cfg(test)]
mod controls {
    use super::*;
    fn dev(ceiling:[f32;3],white:f32)->Develop {Develop{matrix:Some(color::Render::new([[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]).with_ceiling(ceiling)),
        srgb:true,tone:Some(Tone{black:0.,white,contrast:0.55}),wants_tone:true,exposure_gain:1.}}
    #[test]
    fn actual_stage_controls_exercise_pin_rolloff_and_display_loss()->Result<()> {
        let d=dev([1.;3],1.);let mut counts=Counts::default();
        let null=observe_pixel([0.2,0.3,0.4],&d)?;counts.add(&null);
        ensure!(null.pin==0&&same(null.camera,null.clipped)&&same(null.clipped,null.rolled),"below-knee control changed");
        let pin=observe_pixel([1.1,0.2,0.1],&d)?;counts.add(&pin);
        ensure!(pin.pin==1&&!same(pin.camera,pin.clipped),"pin positive unexercised");
        let rolloff=observe_pixel([0.8,0.3,0.2],&d)?;counts.add(&rolloff);
        ensure!(rolloff.pin==0&&!same(rolloff.clipped,rolloff.rolled),"rolloff-only positive unexercised");
        let display=observe_pixel([0.7;3],&dev([1.;3],0.25))?;counts.add(&display);
        ensure!(display.pin==0&&display.gamut==[1.;3]&&display.shoulder_gamut.iter().all(|&v|v<1.),"unclipped display-loss positive unexercised");
        ensure!(counts.pixels==4&&counts.pin_pixels==1&&counts.clip_changed==1&&counts.rolloff_changed>0
            &&counts.gamut_exact_white>counts.shoulder_gamut_exact_white,"counts missed positive controls");Ok(())
    }
    #[test]
    fn mhc_can_create_a_pin_from_entirely_below_ceiling_merged_support()->Result<()> {
        let mut data=vec![0.1;81];for(x,y)in [(4,4),(3,4),(5,4),(4,3),(4,5)]{data[y*9+x]=0.95;}
        let m=Mosaic{data:&data,width:9,height:9};let mut row=vec![0.;27];demosaic_row(&m,4,&mut row);
        let p=observe_pixel([row[12],row[13],row[14]],&dev([1.;3],1.))?;
        let(values,below,fraction)=support(&m,4,4,[1.;3])?;
        ensure!(below&&fraction<1.&&values.iter().all(|&v|v<1.)&&p.pin&2!=0,"MHC-created pin positive absent");
        let flat=vec![0.4;81];let m=Mosaic{data:&flat,width:9,height:9};demosaic_row(&m,4,&mut row);
        let p=observe_pixel([row[12],row[13],row[14]],&dev([1.;3],1.))?;
        ensure!(p.pin==0&&same(p.camera,p.clipped),"flat negative pin control failed");Ok(())
    }
}
