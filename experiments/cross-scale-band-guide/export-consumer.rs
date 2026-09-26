// Scoped dynamic-level copy of learned-band-guide native exporter.
// Original gather/fields/coefficient/terminal/hull/MHC arithmetic retained.
// No model evaluation; root separately commissions nonzero predictor replay.
use super::*;
use serde_json::{json,Value};
use std::io::Write;
use strehl_core::align::Similarity;
use strehl_core::pyramid::{Pyramid,LevelSize,rb_own_guide_diagnostic as core};
use super::shared_source_field::{hash16,hash32};

const FEATURES:usize=10;
pub(crate) struct Arm {pub planes4:Vec<Vec<f32>>,pub rgb:Vec<f32>}
struct Collected {
    sizes:Vec<LevelSize>,features:Vec<Vec<f32>>,coeff:Vec<Vec<f32>>,canonical_weights:Vec<Vec<f32>>,
    base:Vec<Vec<f32>>,lower:Vec<Vec<f32>>,upper:Vec<Vec<f32>>,canonical:Arm,sources:Value,
}
fn same(a:&[f32],b:&[f32])->bool{a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())}
fn same4(a:&[Vec<f32>],b:&[Vec<f32>])->bool{a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|same(a,b))}
fn arm(merge:&BandMerge,sizes:&[LevelSize],levels:Levels,wb:[f32;4])->Result<Arm>{
    let planes4=merge.finish(&mut Workspace::new(sizes));let rgb=phase_packed_rgb::camera_rgb(&planes4,sizes[0].width,sizes[0].height,levels,wb)?;
    ensure!(planes4.iter().flatten().chain(&rgb).all(|v|v.is_finite()),"nonfinite final image");Ok(Arm{planes4,rgb})
}
struct Source<'a>(&'a[Frame]);impl PyramidFrameSource for Source<'_>{fn len(&self)->usize{self.0.len()}fn decode(&self,i:usize)->Result<Frame>{Ok(self.0[i].clone())}}
fn setup(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,noise:&NoiseModel,cfg:MergeConfig)->Result<(WarpMap,Vec<LevelSize>)>{
    ensure!((2..=65).contains(&frames.len())&&frames.len()==transforms.len()
        &&((crop.width==80&&crop.height==72&&cfg.bands==3)||(cfg.bands==7&&[(1024,1024),(1031,1029)].contains(&(crop.width,crop.height)))),
        "declared compact/high-N/seven-band generated scope required");let first=&frames[0];let full=first.geometry();
    ensure!(first.active.width<=2110&&first.active.height<=2110&&noise.is_trustworthy()&&noise.prnu().is_none(),"tiny injected model scope");
    ensure!(gatefloor::enabled()&&strehl_core::pyramid::fine_support_candidate::environment_mode()==strehl_core::pyramid::fine_support_candidate::Mode::Off,
        "held canonical noise/no competing treatment required");
    for (i,f) in frames.iter().enumerate(){ensure!(!f.path.exists()&&f.geometry()==full&&f.active==first.active&&f.stride==first.stride
        &&f.buffer_height==first.buffer_height&&f.levels==first.levels&&f.camera==first.camera&&f.iso==first.iso&&f.wb_coeffs[..3]==first.wb_coeffs[..3],"generated metadata mismatch");
        validate_pyramid_frame(f,full,i)?;let id=strehl_raw::identity(&f.path);
        ensure!(strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?.is_none(),"noCA generated scope");
        ensure!(phase_packed_rgb::full_stack::full_source_supported(transforms[i],full,crop,None),"source footprint incomplete");}
    for p in [CfaPlane::R,CfaPlane::G1,CfaPlane::G2,CfaPlane::B]{ensure!(noise.plane(p).levels==first.levels,"injected levels mismatch");}
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes()as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance{stack:StackIdentity::from_entries("cross-scale-band-guide-generated",&entries),
        strategy:"independent supplied transforms".into(),heldout_px:None,cycle_floor_px:None,reference:0,note:"bounded independent generated export".into()},
        full,Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect());
    let sizes=level_sizes(crop.width,crop.height,cfg.bands);ensure!(sizes.len()==cfg.bands+1,"requested completeAC plusbase required");Ok((map,sizes))
}
fn collect(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,noise:&NoiseModel,cfg:MergeConfig)->Result<Collected>{
    let(map,sizes)=setup(frames,transforms,crop,noise,cfg)?;let n=frames.len();let first=&frames[0];let source=Source(frames);
    let mut worker=BandWorker::new(PyramidDomain::cropped(first.geometry(),crop)?,cfg);
    let mut features=sizes[..cfg.bands].iter().map(|s|vec![0.0;n*FEATURES*s.pixels()]).collect::<Vec<_>>();
    let mut coeff=sizes[..cfg.bands].iter().map(|s|vec![0.0;n*4*s.pixels()]).collect::<Vec<_>>();
    let mut canonical_weights=sizes[..cfg.bands].iter().map(|s|vec![0.0;n*s.pixels()]).collect::<Vec<_>>();
    let mut lower=vec![vec![f32::INFINITY;crop.width*crop.height];4];let mut upper=vec![vec![f32::NEG_INFINITY;crop.width*crop.height];4];let mut receipts=Vec::new();
    for(i,f)in frames.iter().enumerate(){let before=hash16(&f.data);ensure!(worker.fold(&source,i,first.levels,noise,Some(&map),None)?,"source refused");
        let fields=core::canonical_fields(&worker.merge,&worker.fws,(!worker.beta.is_empty()).then_some(worker.beta.as_slice()));
        let mut gaussian:Vec<Pyramid>=(0..3).map(|_|Pyramid::zeros(&sizes)).collect();
        let guides=[worker.luma.clone(),worker.planes[0].iter().zip(&worker.luma).map(|(r,g)|r-g).collect(),worker.planes[3].iter().zip(&worker.luma).map(|(b,g)|b-g).collect()];
        for(p,v)in gaussian.iter_mut().zip(&guides){p.build_gaussian(v,&mut Workspace::new(&sizes));}
        for k in 0..cfg.bands{let px=sizes[k].pixels();canonical_weights[k][i*px..(i+1)*px].copy_from_slice(&fields.weights[k]);
            for j in 0..px{let vals=[(fields.energy[k][j]/fields.floor[k][j].max(1.0)).ln_1p(),fields.floor[k][j].ln_1p(),
                gaussian[0].level(k)[j]/first.levels.range(),gaussian[1].level(k)[j]/first.levels.range(),gaussian[2].level(k)[j]/first.levels.range()];
                for f in 0..5{features[k][(i*FEATURES+f)*px+j]=vals[f];}}}
        for c in 0..4{let mut p=Pyramid::zeros(&sizes);p.build(&worker.planes[c],&mut Workspace::new(&sizes));for k in 0..cfg.bands{let px=sizes[k].pixels();coeff[k][(i*4+c)*px..(i*4+c+1)*px].copy_from_slice(p.level(k));}
            for j in 0..lower[c].len(){lower[c][j]=lower[c][j].min(worker.planes[c][j]);upper[c][j]=upper[c][j].max(worker.planes[c][j]);}}
        ensure!(before==hash16(&f.data),"original changed");receipts.push(json!({"source_sha256":before,"known4_sha256":worker.planes.iter().map(|p|hash32(p)).collect::<Vec<_>>(),
            "guide_sha256":hash32(&worker.luma),"variance_sha256":hash32(&worker.var),"beta":worker.beta}));
    }
    for k in 0..cfg.bands{let px=sizes[k].pixels();for f in 0..5{for j in 0..px{let mut sum=0.0;for i in 0..n{sum+=features[k][(i*FEATURES+f)*px+j];}let mean=sum/n as f32;
        for i in 0..n{features[k][(i*FEATURES+f+5)*px+j]=mean;}}}}
    ensure!(features.iter().flatten().chain(coeff.iter().flatten()).all(|v|v.is_finite()),"nonfinite exported data");
    let base=core::terminal_means(&worker.merge);let canonical=arm(&worker.merge,&sizes,first.levels,first.wb_coeffs)?;
    Ok(Collected{sizes,features,coeff,canonical_weights,base,lower,upper,canonical,sources:json!(receipts)})
}
fn prescribed(sizes:&[LevelSize],n:usize)->Vec<Vec<f32>>{sizes[..sizes.len()-1].iter().map(|sz|(0..n).flat_map(|s|(0..sz.height).flat_map(move|y|(0..sz.width).map(move|x|1.0+0.25*((s+3*x+5*y)%5)as f32))).collect()).collect()}
fn render(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,noise:&NoiseModel,cfg:MergeConfig,data:&Collected,
    sets:&[Vec<Vec<f32>>])->Result<Vec<Arm>>{
    let(map,sizes)=setup(frames,transforms,crop,noise,cfg)?;let first=&frames[0];let source=Source(frames);
    ensure!(sets.iter().all(|s|s.len()==cfg.bands&&s.iter().enumerate().all(|(k,w)|w.len()==frames.len()*sizes[k].pixels()&&w.iter().all(|v|v.is_finite()&&*v>=0.0))),"weight shape/values");
    let mut worker=BandWorker::new(PyramidDomain::cropped(first.geometry(),crop)?,cfg);
    let mut merges=sets.iter().map(|_|BandMerge::new(crop.width,crop.height,4,cfg)).collect::<Vec<_>>();let mut work=sets.iter().map(|_|FrameWorkspace::new(&sizes,4)).collect::<Vec<_>>();
    for i in 0..frames.len(){ensure!(worker.fold(&source,i,first.levels,noise,Some(&map),None)?,"replay refused");
        let got=worker.planes.iter().map(|p|hash32(p)).collect::<Vec<_>>();ensure!(json!(got)==data.sources[i]["known4_sha256"],"replay gather differs");
        let mut fields=core::canonical_fields(&worker.merge,&worker.fws,(!worker.beta.is_empty()).then_some(worker.beta.as_slice()));
        let refs=worker.planes.iter().map(Vec::as_slice).collect::<Vec<_>>();
        for a in 0..sets.len(){for k in 0..cfg.bands{let px=sizes[k].pixels();fields.weights[k].copy_from_slice(&sets[a][k][i*px..(i+1)*px]);}
            core::add_fields(&mut merges[a],&refs,&fields,&mut work[a]);}}
    let check=arm(&worker.merge,&sizes,first.levels,first.wb_coeffs)?;ensure!(same4(&check.planes4,&data.canonical.planes4)&&same(&check.rgb,&data.canonical.rgb),"canonical replay differs");
    for m in &merges{ensure!(same4(&core::terminal_means(m),&data.base),"terminal mean changed");}
    merges.iter().map(|m|arm(m,&sizes,first.levels,first.wb_coeffs)).collect()
}
fn blob(out:&Path,name:&str,values:&[f32],shape:&[usize])->Result<Value>{ensure!(shape.iter().product::<usize>()==values.len()&&values.iter().all(|v|v.is_finite()),"blob shape/values");
    let path=out.join(name);let file=std::fs::OpenOptions::new().write(true).create_new(true).open(&path)?;
    let mut file=std::io::BufWriter::with_capacity(1<<20,file);for v in values{file.write_all(&v.to_le_bytes())?;}file.flush()?;
    Ok(json!({"file":name,"shape":shape,"dtype":"<f4","sha256":hash32(values)}))}
fn flat(v:&[Vec<f32>])->Vec<f32>{v.iter().flatten().copied().collect()}
pub(crate) fn export_case(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,noise:&NoiseModel,cfg:MergeConfig,truth_rgb:&[f32],out:&Path)->Result<Value>{
    ensure!(!out.exists(),"fresh export directory required");ensure!(truth_rgb.len()==4*crop.width*crop.height*3&&truth_rgb.iter().all(|v|v.is_finite()),"truth RGB shape/values");
    let data=collect(frames,transforms,crop,noise,cfg)?;let n=frames.len();let uniform=data.sizes[..cfg.bands].iter().map(|s|vec![1.0;n*s.pixels()]).collect::<Vec<_>>();
    // Literal zero-score prediction has unit weights. Nonzero model is commissioned separately.
    let zeros=uniform.clone();let prescribed=prescribed(&data.sizes,n);
    let mut arms=render(frames,transforms,crop,noise,cfg,&data,&[uniform,zeros,prescribed.clone()])?;let check=arms.pop().unwrap();let zero_arm=arms.pop().unwrap();let uniform=arms.pop().unwrap();
    ensure!(same4(&uniform.planes4,&zero_arm.planes4)&&same(&uniform.rgb,&zero_arm.rgb),"uniform/zero identity");std::fs::create_dir(out)?;let mut arrays=serde_json::Map::new();
    for k in 0..cfg.bands{let s=data.sizes[k];for(label,values,shape)in [
        ("coeff",&data.coeff[k],vec![n,4,s.height,s.width]),("features",&data.features[k],vec![n,10,s.height,s.width]),
        ("canonical-weights",&data.canonical_weights[k],vec![n,s.height,s.width]),("prescribed-weights",&prescribed[k],vec![n,s.height,s.width])]{
        arrays.insert(format!("{label}-{k}"),blob(out,&format!("{label}-{k}.f32"),values,&shape)?);}}
    let b=data.sizes[cfg.bands];arrays.insert("base".into(),blob(out,"base.f32",&flat(&data.base),&[4,b.height,b.width])?);
    for(label,v)in [("lower",&data.lower),("upper",&data.upper),("uniform-cfa",&uniform.planes4),("prescribed-cfa",&check.planes4)]{
        arrays.insert(label.into(),blob(out,&format!("{label}.f32"),&flat(v),&[4,crop.height,crop.width])?);}
    for(label,v)in [("canonical-rgb",data.canonical.rgb.as_slice()),("uniform-rgb",uniform.rgb.as_slice()),("zero-network-rgb",zero_arm.rgb.as_slice()),("prescribed-rgb",check.rgb.as_slice()),("truth-rgb",truth_rgb)]{
        arrays.insert(label.into(),blob(out,&format!("{label}.f32"),v,&[2*crop.height,2*crop.width,3])?);}
    let receipt=json!({"schema":1,"sources":data.sources,"source_count":n,"level_sizes":data.sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),
        "wb":[frames[0].wb_coeffs[0]/frames[0].wb_coeffs[1],1.0,frames[0].wb_coeffs[2]/frames[0].wb_coeffs[1]],"range":frames[0].levels.range(),
        "arrays":arrays,"original_linear_reconstruction":true,"zero_network_uniform_exact":true,"zero_network_scope":"literal zero-score unit weights; new predictor inference commissioned separately","terminal_mean_exact":true});
    let path=out.join("case.json");serde_json::to_writer_pretty(std::fs::OpenOptions::new().write(true).create_new(true).open(path)?,&receipt)?;Ok(receipt)
}
