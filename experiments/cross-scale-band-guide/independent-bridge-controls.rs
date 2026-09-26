// Generated actual-consumer commissioning only; root supplies the frozen model.
use super::*;
use serde_json::Value;

mod compact {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/learned-band-guide/independent-fixtures.rs"));
    pub(super) fn hash16_for_bridge(v:&[u16])->String{hash16(v)}
    pub(super) fn input()->(Vec<Frame>,Vec<Similarity>,align_cmd::CropRect){
        let case=cases().into_iter().find(|c|c.id=="held-near-fine-far-coarse-n5").unwrap();
        let g=generate(&case);(g.frames,g.transforms,crop())
    }
}
mod large {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/cross-scale-band-guide/independent-fixtures.rs"));
    pub(super) fn input()->(Vec<Frame>,Vec<Similarity>,align_cmd::CropRect){
        let case=cases().into_iter().find(|c|c.id=="train-multiscale-gabor-v0-n5-b7").unwrap();
        // This analytic case never reads texture pixels; retain its original generator.
        let t=Textures{tiles:Vec::new(),manifest:Value::Null,sha:String::new()};
        let g=generate(&case,&t);(g.frames,g.transforms,case.crop())
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ControlConfig {out:PathBuf,bridge:BridgeConfig,predictions:PathBuf,thin_case:PathBuf,scale_case:PathBuf}
fn read_json(path:&Path)->Result<Value>{Ok(serde_json::from_slice(&std::fs::read(path)?)?)}
fn array(root:&Path,row:&Value)->Result<Vec<f32>>{
    let file=root.join(row["file"].as_str().context("array path")?);
    ensure!(row["dtype"]=="<f4"&&file_hash(&file)?==row["sha256"],"array binding differs");
    let bytes=std::fs::read(&file)?;let n=row["shape"].as_array().context("shape")?.iter().try_fold(1usize,|n,v|Ok::<_,anyhow::Error>(n*v.as_u64().context("extent")? as usize))?;
    ensure!(bytes.len()==4*n,"array byte count differs");
    let a=bytes.chunks_exact(4).map(|b|f32::from_le_bytes(b.try_into().unwrap())).collect::<Vec<_>>();
    ensure!(a.iter().all(|v|v.is_finite()),"array nonfinite");Ok(a)
}
fn max_error(a:&[f32],b:&[f32])->f32{
    assert_eq!(a.len(),b.len());assert!(a.iter().chain(b).all(|x|x.is_finite()));
    a.iter().zip(b).map(|(a,b)|(a-b).abs()).fold(0.,f32::max)
}
fn output(merge:&BandMerge,sizes:&[LevelSize],f:&Frame)->Result<(Vec<Vec<f32>>,Vec<f32>)>{
    let p=merge.finish(&mut Workspace::new(sizes));
    let rgb=phase_packed_rgb::camera_rgb(&p,sizes[0].width,sizes[0].height,f.levels,f.wb_coeffs)?;
    ensure!(p.iter().flatten().chain(&rgb).all(|v|v.is_finite()),"native output nonfinite");Ok((p,rgb))
}
fn exact4(a:&[Vec<f32>],b:&[Vec<f32>])->bool{a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|same(a,b))}
fn map_for(frames:&[Frame],transforms:&[strehl_core::align::Similarity])->WarpMap{
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes()as u64)).collect::<Vec<_>>();
    WarpMap::new(strehl_core::warpmap::Provenance{stack:StackIdentity::from_entries("bridge-generated",&entries),
        strategy:"supplied independent generated geometry".into(),heldout_px:None,cycle_floor_px:None,reference:0,note:"no RAW files".into()},
        frames[0].geometry(),Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect())
}
fn fold(worker:&mut BandWorker,frames:&[Frame],i:usize,noise:&NoiseModel,map:&WarpMap)->Result<()>{
    ensure!(worker.fold(&OneFrame{frame:&frames[i],index:i,count:frames.len()},i,frames[0].levels,noise,Some(map),None)?,"generated fold refused");Ok(())
}
fn native_case(conf:&ControlConfig,path:&Path,record:&Value,frames:Vec<Frame>,transforms:Vec<strehl_core::align::Similarity>,crop:align_cmd::CropRect,bands:usize)->Result<Value>{
    let meta=read_json(path)?;let root=path.parent().context("case directory")?;
    ensure!(record["case_sha256"]==file_hash(path)?&&meta["source_count"]==frames.len(),"case/source identity");
    let id=path.parent().unwrap().file_name().unwrap().to_string_lossy().into_owned();
    let dir=conf.out.join(&id);std::fs::create_dir(&dir)?;
    let cfg=MergeConfig{bands,..Default::default()};let n=frames.len();let first=&frames[0];
    let sizes=level_sizes(crop.width,crop.height,bands);ensure!(sizes.len()==bands+1,"complete band support");
    ensure!(meta["level_sizes"]==json!(sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>()),"level layout");
    let noise=profile::noise_model_for(&first.camera,first.iso,first.levels);let map=map_for(&frames,&transforms);
    let domain=PyramidDomain::cropped(first.geometry(),crop)?;
    let original_hashes=frames.iter().map(|f|compact::hash16_for_bridge(&f.data)).collect::<Vec<_>>();
    ensure!(meta["sources"].as_array().is_some_and(|v|v.len()==n)
        &&original_hashes.iter().enumerate().all(|(i,h)|meta["sources"][i]["source_sha256"]==*h),"original generated source/order binding differs");
    // Literal observer-off canonical consumer: no bridge and no payload helpers.
    let mut off=BandWorker::new(domain,cfg);
    for i in 0..n{fold(&mut off,&frames,i,&noise,&map)?;}
    let(off_cfa,off_rgb)=output(&off.merge,&sizes,first)?;
    ensure!(same(&off_rgb,&array(root,&meta["arrays"]["canonical-rgb"])?),"retained canonical differs");
    let mut bridge_cfg=conf.bridge.clone();bridge_cfg.out_dir=dir.clone();
    let mut bridge=Bridge::new(&bridge_cfg,&sizes,n,first.levels.range(),&(0..n).collect::<Vec<_>>())?;
    ensure!(bridge.finish_stats().is_err(),"premature context accepted");
    let mut pass1=BandWorker::new(domain,cfg);let mut saw_phase=false;let mut saw_source=false;
    let expected_coeff=(0..bands).map(|k|array(root,&meta["arrays"][format!("coeff-{k}")])).collect::<Result<Vec<_>>>()?;
    let expected_features=(0..bands).map(|k|array(root,&meta["arrays"][format!("features-{k}")])).collect::<Result<Vec<_>>>()?;
    for i in 0..n{
        fold(&mut pass1,&frames,i,&noise,&map)?;let c=coefficients(&pass1,&sizes);
        ensure!(bridge.stats(n,&c).is_err(),"out-of-order context accepted");
        for k in 0..bands{let px=sizes[k].pixels();ensure!(same(&c[k],&expected_coeff[k][i*4*px..(i+1)*4*px]),"native coefficient/channel/source payload differs");
            saw_phase|=!same(&c[k][..px],&c[k][px..2*px]);
            if i>0{saw_source|=!same(&c[k],&expected_coeff[k][..4*px]);}}
        bridge.stats(i,&c)?;
    }
    bridge.finish_stats()?;ensure!(bridge.finish().is_err(),"incomplete score accepted");
    let(p1,r1)=output(&pass1.merge,&sizes,first)?;ensure!(exact4(&p1,&off_cfa)&&same(&r1,&off_rgb),"stats observer changed canonical");
    drop(pass1);
    let prediction_root=conf.predictions.parent().unwrap();
    let expected_weights=(0..bands).map(|k|array(prediction_root,&record["arrays"][format!("weights-{k}")])).collect::<Result<Vec<_>>>()?;
    let mut pass2=BandWorker::new(domain,cfg);let mut candidate=BandMerge::new(crop.width,crop.height,4,cfg);let mut work=FrameWorkspace::new(&sizes,4);
    let mut weight_error=0.0f32;let mut weight_activity=0.0f32;
    for i in 0..n{
        fold(&mut pass2,&frames,i,&noise,&map)?;
        let mut fields=core::canonical_fields(&pass2.merge,&pass2.fws,(!pass2.beta.is_empty()).then_some(pass2.beta.as_slice()));
        let c=coefficients(&pass2,&sizes);let f=features(&pass2,&sizes,&fields,first.levels.range());
        for k in 0..bands{let px=sizes[k].pixels();ensure!(same(&c[k],&expected_coeff[k][i*4*px..(i+1)*4*px]),"pass2 source coefficients differ");
            ensure!(same(&f[k],&expected_features[k][i*10*px..i*10*px+5*px]),"native five-feature payload differs");}
        let weights=bridge.score(i,&c,&f)?;
        for k in 0..bands{let px=sizes[k].pixels();weight_error=weight_error.max(max_error(&weights[k],&expected_weights[k][i*px..(i+1)*px]));
            weight_activity=weight_activity.max(weights[k].iter().map(|v|(v-1.0).abs()).fold(0.,f32::max));fields.weights[k].copy_from_slice(&weights[k]);}
        let refs=pass2.planes.iter().map(Vec::as_slice).collect::<Vec<_>>();core::add_fields(&mut candidate,&refs,&fields,&mut work);
    }
    let server=bridge.finish()?;ensure!(weight_error<=2e-5&&weight_activity>1e-5,"actual nonzero model weights fail parity/exercise");
    let(p2,r2)=output(&pass2.merge,&sizes,first)?;ensure!(exact4(&p2,&off_cfa)&&same(&r2,&off_rgb),"score observer changed canonical");
    ensure!(held_mean_hull(&candidate,&off.merge,&sizes),"learned consumer changed mean/hull");
    let(cfa,rgb)=output(&candidate,&sizes,first)?;let flat=cfa.iter().flatten().copied().collect::<Vec<_>>();
    let ce=max_error(&flat,&array(prediction_root,&record["arrays"]["cfa"])?);let re=max_error(&rgb,&array(prediction_root,&record["arrays"]["rgb"])?);
    ensure!(ce<=0.02&&re<=5e-6,"actual native weighted consumer differs");
    ensure!(saw_phase&&saw_source,"wrong phase/source destroyers are inert");
    ensure!(original_hashes==frames.iter().map(|f|compact::hash16_for_bridge(&f.data)).collect::<Vec<_>>(),"generated original changed");
    // The compact case additionally commissions actual zero-head IPC and server-side refusal.
    let mut zero_exact=false;let mut server_refused=false;
    if bands==3{
        let zdir=dir.join("zero-head");std::fs::create_dir(&zdir)?;
        let mut model=read_json(&conf.bridge.weights)?;
        for key in ["head.weight","head.bias"]{for value in model["state"][key]["values"].as_array_mut().context("head values")?{*value=json!(0.0);}}
        let model_path=zdir.join("model.json");save(&model_path,&model)?;
        let mut zcfg=bridge_cfg.clone();zcfg.out_dir=zdir;zcfg.weights=model_path;zcfg.weights_sha256=file_hash(&zcfg.weights)?;
        let mut zb=Bridge::new(&zcfg,&sizes,n,first.levels.range(),&(0..n).collect::<Vec<_>>())?;
        for i in 0..n{zb.stats(i,&(0..bands).map(|k|{let px=sizes[k].pixels();expected_coeff[k][i*4*px..(i+1)*4*px].to_vec()}).collect::<Vec<_>>())?;}zb.finish_stats()?;
        let mut zw=BandWorker::new(domain,cfg);let mut zm=BandMerge::new(crop.width,crop.height,4,cfg);let mut zwork=FrameWorkspace::new(&sizes,4);
        for i in 0..n{fold(&mut zw,&frames,i,&noise,&map)?;let mut fields=core::canonical_fields(&zw.merge,&zw.fws,(!zw.beta.is_empty()).then_some(zw.beta.as_slice()));
            let w=zb.score(i,&coefficients(&zw,&sizes),&features(&zw,&sizes,&fields,first.levels.range()))?;
            ensure!(w.iter().flatten().all(|v|v.to_bits()==1.0f32.to_bits()),"zero head is not exact unit weights");
            for k in 0..bands{fields.weights[k].copy_from_slice(&w[k]);}let refs=zw.planes.iter().map(Vec::as_slice).collect::<Vec<_>>();core::add_fields(&mut zm,&refs,&fields,&mut zwork);
        }zb.finish()?;
        let(zp,zr)=output(&zm,&sizes,first)?;let zflat=zp.iter().flatten().copied().collect::<Vec<_>>();
        ensure!(same(&zflat,&array(root,&meta["arrays"]["uniform-cfa"])?)&&same(&zr,&array(root,&meta["arrays"]["uniform-rgb"])?),"zero-head native consumer differs from retained uniform");zero_exact=true;
        let bad=dir.join("protocol-refusal");std::fs::create_dir(&bad)?;let mut badcfg=bridge_cfg.clone();badcfg.out_dir=bad;
        let mut b=Bridge::new(&badcfg,&sizes,n,first.levels.range(),&[0])?;
        b.header(&json!({"op":"stats","index":1,"floats":4*b.pixels()}))?;
        ensure!(b.response("stats").is_err(),"server accepted wrong source order");
        ensure!(!b.child.wait()?.success(),"server refusal was not terminal");b.closed=true;server_refused=true;
    }
    Ok(json!({"case":path,"case_sha256":file_hash(path)?,"source_count":n,"bands":bands,
        "payload_exact":true,"phase_and_source_destroyers_live":true,"canonical_off_stats_score_exact":true,
        "weight_max_abs_error":weight_error,"nonzero_weight_activity":weight_activity,"cfa_max_abs_error_dn":ce,"rgb_max_abs_error":re,
        "mean_hull_exact":true,"original_u16_unchanged":true,"zero_head_uniform_exact":zero_exact,"server_order_refusal":server_refused,
        "all_boundary_pixels_included":true,"server":server}))
}

#[test]
fn independent_bridge_controls()->Result<()>{
    let p=PathBuf::from(std::env::var_os("STREHL_CROSS_SCALE_BRIDGE_CONFIG").context("explicit generated bridge config")?);
    let conf:ControlConfig=serde_json::from_slice(&std::fs::read(&p)?)?;
    ensure!(!conf.out.exists(),"fresh control output required");std::fs::create_dir_all(&conf.out)?;
    ensure!(conf.thin_case.parent().unwrap().file_name().unwrap()=="held-near-fine-far-coarse-n5"
        &&conf.scale_case.parent().unwrap().file_name().unwrap()=="train-multiscale-gabor-v0-n5-b7","fixed developer cases only");
    let predictions=read_json(&conf.predictions)?;ensure!(predictions["model_sha256"]==conf.bridge.weights_sha256
        &&predictions["generic_consumer_sha256"]==conf.bridge.generic_consumer_sha256&&predictions["truth_read"]==false,"model/reference binding differs");
    let records=predictions["records"].as_array().context("prediction records")?;ensure!(records.len()==2,"exact two mechanical references required");
    let mut reports=Vec::new();
    for (path,(frames,transforms,crop),bands) in [(&conf.thin_case,compact::input(),3),(&conf.scale_case,large::input(),7)]{
        let record=records.iter().find(|r|Path::new(r["case"].as_str().unwrap())==path).context("fixed prediction absent")?;
        reports.push(native_case(&conf,path,record,frames,transforms,crop,bands)?);
    }
    save(&conf.out.join("bridge-controls.json"),&json!({"status":"BRIDGE_CONTROLS_COMPLETE","passed":true,"cases":reports,
        "model_sha256":conf.bridge.weights_sha256,"predictions_sha256":file_hash(&conf.predictions)?,"photographic_admission":false}))?;Ok(())
}
