include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/learned-band-guide/independent-fixtures.rs"));
use super::Model;
fn config()->Value{serde_json::from_slice(&std::fs::read(std::env::var("STREHL_LEARNED_BAND_GUIDE_CONFIG").expect("bounded config")).unwrap()).unwrap()}
fn output()->PathBuf{let p=PathBuf::from(config()["out"].as_str().unwrap());std::fs::create_dir_all(&p).unwrap();p}
fn cfg()->MergeConfig{MergeConfig{bands:3,..Default::default()}}
fn file_sha(p:&Path)->String{let mut h=Sha256::new();h.update(std::fs::read(p).unwrap());h.finalize().iter().map(|x|format!("{x:02x}")).collect()}
fn load_json(p:&Path)->Value{serde_json::from_slice(&std::fs::read(p).unwrap()).unwrap()}
fn exact(a:&[f32],b:&[f32])->bool{a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())}
fn max_error(a:&[f32],b:&[f32])->f64{assert_eq!(a.len(),b.len());a.iter().zip(b).map(|(a,b)|{assert!(a.is_finite()&&b.is_finite());(f64::from(*a)-f64::from(*b)).abs()}).fold(0.0,f64::max)}
fn read_blob(dir:&Path,row:&Value)->Vec<f32>{assert_eq!(row["dtype"],"<f4");let p=dir.join(row["file"].as_str().unwrap());assert_eq!(file_sha(&p),row["sha256"].as_str().unwrap());let v=read_f32(&p);assert_eq!(v.len(),row["shape"].as_array().unwrap().iter().map(|n|n.as_u64().unwrap()as usize).product::<usize>());assert!(v.iter().all(|v|v.is_finite()));v}
struct Held{case:Case,g:Generated,canonical:Vec<f32>,uniform:Vec<f32>,case_path:PathBuf}
fn positive(f:Family)->Option<Window>{match f{Family::Curved=>Some(CURVED),Family::Thin=>Some(THIN),_=>None}}
// Absolute error rejects noise/offset/overshoot; signed projections alone can reward them.
fn judge(h:&Held,candidate:&[f32])->Value{let mut preservation=true;let mut rows=Vec::new();let mut eligible=0usize;let mut unqualified=0usize;
    for w in windows(h.case.family){let c=score(&h.g,&h.canonical,w);let u=score(&h.g,&h.uniform,w);let p=score(&h.g,candidate,w);
        for reference in [&c,&u]{for channel in 0..3{for component in 0..2{match reference.coeff[channel][component]{Some(r)if r>=0.5=>eligible+=1,Some(_)=>unqualified+=1,None=>{}}}}}
        let pass=safe(&c,&p)&&safe(&u,&p)&&retained(&c,&p)&&retained(&u,&p);preservation&=pass;
        rows.push(json!({"window":w.name,"native_xyxy":[w.x0,w.y0,w.x1,w.y1],"canonical":score_json(&c),"uniform":score_json(&u),"candidate":score_json(&p),"preservation_pass":pass}));}
    let gain=positive(h.case.family).map(|w|{let c=score(&h.g,&h.canonical,w);let u=score(&h.g,&h.uniform,w);let p=score(&h.g,candidate,w);json!({"window":w.name,"candidate_rgb_rmse":p.rgb,"better_reference_rgb_rmse":c.rgb.min(u.rgb),"pass":p.rgb<=0.95*c.rgb.min(u.rgb)})});
    let positive_pass=gain.as_ref().map_or(true,|v|v["pass"].as_bool().unwrap());
    json!({"id":h.case.id,"n":h.case.n,"iso":h.case.iso,"windows":rows,"positive":gain,"preservation_pass":preservation,"positive_pass":positive_pass,"eligible_reference_components":eligible,"unqualified_reference_components":unqualified,"pass":preservation&&positive_pass})
}
fn all_pass(rows:&[Value])->bool{rows.iter().all(|r|r["pass"]==true)}
fn witness(h:&Held,w:Window,c:usize,d:usize)->Value{let a=score(&h.g,&h.canonical,w).coeff[c][d];let b=score(&h.g,&h.uniform,w).coeff[c][d];json!({"case":h.case.id,"window":w.name,"channel":c,"component":d,"canonical":a,"uniform":b,"live":a.is_some_and(|x|x>=0.5)||b.is_some_and(|x|x>=0.5)})}
fn metadata(case:&Case,g:&Generated)->Value{json!({"id":case.id,"training":case.training,"family":case.family.name(),"variant":case.variant,"iso":case.iso,"sources":case.n,"pupil":pupil_name(case),"clipped_original_samples":g.clipped,"truth_sha256":hash_f32(&g.truth),"source_buffer_sha256":g.frames.iter().map(|f|hash16(&f.data)).collect::<Vec<_>>(),"noise_drawn_after_illumination":true,"calibration_validation":false})}
fn qualify(held:&[Held])->Value{
    let oracle=held.iter().map(|h|judge(h,&h.g.truth)).collect::<Vec<_>>();
    let mut headroom=Vec::new();for h in held.iter().filter(|h|positive(h.case.family).is_some()){let w=positive(h.case.family).unwrap();let flat=held.iter().find(|f|f.case.family==Family::Flat&&f.case.n==h.case.n).unwrap();
        let c=score(&h.g,&h.canonical,w).rgb;let u=score(&h.g,&h.uniform,w).rgb;let cf=score(&flat.g,&flat.canonical,WHOLE).rgb;let uf=score(&flat.g,&flat.uniform,WHOLE).rgb;
        let mut difference=0.0f64;for y in w.y0..w.y1{for x in w.x0..w.x1{for channel in 0..3{let j=index(x,y,channel);difference=difference.max((f64::from(h.canonical[j])-f64::from(h.uniform[j])).abs());}}}
        headroom.push(json!({"case":h.case.id,"canonical_error":c,"uniform_error":u,"canonical_flat_error":cf,"uniform_flat_error":uf,"reference_max_difference":difference,"matched_source_count":h.case.n,"same_brightness":false,"pass":c>2.0*cf&&u>2.0*uf&&difference>1e-6}));}
    let thin=held.iter().find(|h|h.case.family==Family::Thin).unwrap();let glint=held.iter().find(|h|h.case.family==Family::Glint).unwrap();let colour=held.iter().find(|h|h.case.family==Family::Colour).unwrap();
    let witnesses=vec![witness(thin,THIN,1,0),witness(thin,THIN,1,1),witness(glint,GLINT,1,1),witness(colour,COLOUR,0,0),witness(colour,COLOUR,2,0)];
    // Fixed mutations of known truth commission this same final scorer, not a separate metric.
    let half_near=thin.g.truth.iter().zip(&thin.g.near_detail).map(|(t,n)|t-0.5*n).collect::<Vec<_>>();
    let erased_near=thin.g.truth.iter().zip(&thin.g.near_detail).map(|(t,n)|t-n).collect::<Vec<_>>();
    let wrong_depth=thin.g.truth.iter().zip(&thin.g.far_detail).map(|(t,f)|t-f).collect::<Vec<_>>();
    let mut noisy=held[0].g.truth.clone();for (j,v)in noisy.iter_mut().enumerate(){*v+=0.10*random_normal((j/3)%NW,(j/3)/NW,j%3,0x97650b13);}
    let destroyers=json!({"erased_near_detail":judge(thin,&erased_near),"erased_far_depth":judge(thin,&wrong_depth),"added_noise":judge(&held[0],&noisy),"erased_image":judge(colour,&vec![0.0;NW*NH*3])});
    let destroyers_rejected=destroyers.as_object().unwrap().values().all(|r|r["pass"]==false);
    let truth_pass=all_pass(&oracle);let headroom_live=headroom.iter().all(|r|r["pass"]==true);let protected_live=witnesses.iter().all(|r|r["live"]==true);
    json!({"schema":1,"status":"PRETRAINING_COMPLETE","oracle":oracle,"headroom":headroom,"protected_witnesses":witnesses,"destroyers":destroyers,"optional_half_near_disclosure":judge(thin,&half_near),"truth_pass":truth_pass,"headroom_live":headroom_live,"protected_witnesses_live":protected_live,"destroyers_rejected":destroyers_rejected,"pretraining_qualified":truth_pass&&headroom_live&&protected_live&&destroyers_rejected,"truth_representable_by_fixed_consumer_proven":false,"photographic_replay_admitted":false})
}

#[test]
fn export_dataset(){let out=output();let all=cases();assert_eq!(all.len(),19);let(mut training,mut heldout,mut labels,mut held)=(Vec::new(),Vec::new(),Vec::new(),Vec::new());
    // Training flat cases occur first; held N5 and N9 flat precede every held detail.
    for case in all{let g=generate(&case);let folder=out.join(&case.id);let noise=profile::noise_model_for("ILCE-7CM2",Some(case.iso),levels());
        let receipt=super::export_case(&g.frames,&g.transforms,crop(),&noise,cfg(),&g.truth,&folder).unwrap();let case_path=folder.join("case.json");assert_eq!(receipt["zero_network_uniform_exact"],true);assert_eq!(receipt["terminal_mean_exact"],true);
        labels.push(metadata(&case,&g));if case.training{training.push(case_path);}else{heldout.push(case_path.clone());let canonical=read_blob(&folder,&receipt["arrays"]["canonical-rgb"]);let uniform=read_blob(&folder,&receipt["arrays"]["uniform-rgb"]);let zero=read_blob(&folder,&receipt["arrays"]["zero-network-rgb"]);assert!(exact(&uniform,&zero));assert!(exact(&g.truth,&read_blob(&folder,&receipt["arrays"]["truth-rgb"])));held.push(Held{case,g,canonical,uniform,case_path});}}
    assert_eq!((training.len(),heldout.len()),(12,7));let pre=qualify(&held);write(&out.join("dataset.json"),&json!({"schema":1,"training":training,"heldout":heldout}));write(&out.join("fixture-labels.json"),&json!({"schema":1,"cases":labels}));write(&out.join("pretraining.json"),&pre);println!("LEARNED_BAND_GUIDE_PRETRAINING {}",pre["pretraining_qualified"]);
}

fn prediction(row:&Value,label:&str)->Vec<f32>{read_blob(Path::new(""),&row["arrays"][label])}
#[test]
fn replay_dataset(){let conf=config();let out=output();let dataset_path=PathBuf::from(conf["dataset"].as_str().unwrap());let dataset=load_json(&dataset_path);let pre=load_json(&dataset_path.parent().unwrap().join("pretraining.json"));assert_eq!(pre["pretraining_qualified"],true,"unqualified baseline cannot authorize training/replay");
    let model_path=PathBuf::from(conf["weights"].as_str().unwrap());let model=Model::load(&model_path).unwrap();let inference_path=PathBuf::from(conf["inference"].as_str().unwrap());let inference=load_json(&inference_path);assert_eq!(inference["model_sha256"].as_str().unwrap(),file_sha(&model_path));assert_eq!(inference["truth_read"],false);
    let held_cases=cases().into_iter().filter(|c|!c.training).collect::<Vec<_>>();let paths=dataset["heldout"].as_array().unwrap();assert_eq!(paths.len(),7);let mut rows=Vec::new();let mut parity=Vec::new();let mut live=false;let mut shuffled=None;
    for(case,path)in held_cases.into_iter().zip(paths){let case_path=PathBuf::from(path.as_str().unwrap());assert_eq!(case_path.parent().unwrap().file_name().unwrap().to_str().unwrap(),case.id);let saved=load_json(&case_path);let g=generate(&case);let noise=profile::noise_model_for("ILCE-7CM2",Some(case.iso),levels());let result=super::replay_case(&g.frames,&g.transforms,crop(),&noise,cfg(),&model).unwrap();
        assert_eq!(result.sources,saved["sources"]);assert!(result.terminal_base_exact);assert!(exact(&g.truth,&read_blob(case_path.parent().unwrap(),&saved["arrays"]["truth-rgb"])));assert!(exact(&result.canonical.rgb,&read_blob(case_path.parent().unwrap(),&saved["arrays"]["canonical-rgb"])));assert!(exact(&result.uniform.rgb,&read_blob(case_path.parent().unwrap(),&saved["arrays"]["uniform-rgb"])));assert!(exact(&result.uniform.rgb,&result.no_learning.rgb));
        let prediction_row=inference["records"].as_array().unwrap().iter().find(|r|Path::new(r["case"].as_str().unwrap())==case_path).expect("case inference missing");assert_eq!(prediction_row["case_sha256"].as_str().unwrap(),file_sha(&case_path));
        let mut weight_error=0.0f64;for k in 0..3{weight_error=weight_error.max(max_error(&result.learned_weights[k],&prediction(prediction_row,&format!("weights-{k}"))));assert!(exact(&result.features[k],&read_blob(case_path.parent().unwrap(),&saved["arrays"][format!("features-{k}")])));}
        let cfa=result.learned.planes4.iter().flatten().copied().collect::<Vec<_>>();let cfa_error=max_error(&cfa,&prediction(prediction_row,"cfa"));let rgb_error=max_error(&result.learned.rgb,&prediction(prediction_row,"rgb"));assert!(weight_error<=2e-5&&cfa_error<=0.02&&rgb_error<=5e-6,"nonzero model Python/native mismatch {weight_error} {cfa_error} {rgb_error}");
        let delta=max_error(&result.learned.rgb,&result.uniform.rgb);live|=delta>1e-6;parity.push(json!({"id":case.id,"weights_max_abs":weight_error,"cfa_max_abs_dn":cfa_error,"rgb_max_abs":rgb_error,"uniform_rgb_max_delta":delta,"source_gather_exact":true,"baseline_exact":true,"base_exact":true}));
        let h=Held{case,g,canonical:result.canonical.rgb,uniform:result.uniform.rgb,case_path};let decision=judge(&h,&result.learned.rgb);
        if h.case.family==Family::Thin{let data=super::collect(&h.g.frames,&h.g.transforms,crop(),&noise,cfg()).unwrap();let weights=result.learned_weights.iter().enumerate().map(|(k,v)|{let px=result.level_sizes[k][0]*result.level_sizes[k][1];let mut w=vec![0.0;v.len()];for s in 0..h.case.n{w[s*px..(s+1)*px].copy_from_slice(&v[((s+2)%h.case.n)*px..((s+2)%h.case.n+1)*px]);}w}).collect::<Vec<_>>();let mut arms=super::render(&h.g.frames,&h.g.transforms,crop(),&noise,cfg(),&data,&[weights]).unwrap();let arm=arms.pop().unwrap();shuffled=Some(json!({"fixed_source_rotation":2,"rgb_max_delta":max_error(&arm.rgb,&result.learned.rgb),"judgment":judge(&h,&arm.rgb)}));}
        rows.push(decision);
    }
    let shuffled=shuffled.unwrap();let shuffle_live=shuffled["rgb_max_delta"].as_f64().unwrap()>1e-6;let shuffle_rejected=shuffled["judgment"]["pass"]==false;let scientific=all_pass(&rows);let nominated=scientific&&live&&shuffle_live&&shuffle_rejected;
    let screen=json!({"schema":1,"status":"SCREEN_COMPLETE","cases":rows,"parity":parity,"mechanical_pass":true,"scientific_pass":scientific,"learning_live":live,"shuffled_weights":shuffled,"shuffle_live":shuffle_live,"shuffle_rejected":shuffle_rejected,"candidate_nominated":nominated,"photographic_replay_admitted":false,"held_iso":100,"high_iso_validation":false,"model_sha256":file_sha(&model_path),"dataset_sha256":file_sha(&dataset_path),"inference_sha256":file_sha(&inference_path)});write(&out.join("screen.json"),&screen);println!("LEARNED_BAND_GUIDE {}",screen["candidate_nominated"]);
}

include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/learned-band-guide/independent-arithmetic.rs"));
