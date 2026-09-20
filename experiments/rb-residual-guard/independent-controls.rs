// Frozen prior image fixtures, no new stimulus fitting.
include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/rb-own-guide/independent-fixtures.rs"));
use super::{Arm,Comparison,compare_generated,compare_generated_with_diagnostics};
const OLD_SCREEN:&str=include_str!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/rb-own-guide/controls-1/output/screen.json"));
fn digest(bytes:&[u8])->String{Sha256::digest(bytes).iter().map(|x|format!("{x:02x}")).collect()}
fn hash_f32(v:&[f32])->String{let mut h=Sha256::new();for x in v{h.update(x.to_bits().to_le_bytes());}h.finalize().iter().map(|x|format!("{x:02x}")).collect()}
fn arms(c:&Comparison)->[(&'static str,&Arm);7]{[("canonical",&c.canonical),("matched-green",&c.matched_green),("own-rb",&c.own),
    ("canonical-identity",&c.identity),("swapped-guides",&c.swapped),("camera-green-only",&c.camera_green_only),("guarded",&c.guarded)]}
fn exact_arm(a:&Arm,b:&Arm)->bool{exact(&a.planes4,&b.planes4) && exact_slice(&a.rgb,&b.rgb)}
fn ratio(a:f64,b:f64)->f64{if b>0.0{a/b}else if a==0.0{1.0}else{f64::MAX}}
fn check(c:&Comparison,frames:&[Frame],ts:&[Similarity],before:&[String],scene:Scene)->Value{
    assert_eq!((c.native_width,c.native_height),(2*crop().width,2*crop().height));
    assert_eq!(c.level_sizes,vec![[145,125],[73,63],[37,32],[19,16],[10,8]]);
    assert_eq!(c.frames.len(),frames.len());assert!(exact_arm(&c.canonical,&c.identity));
    assert!(exact(&c.camera_green_only.planes4,&c.own.planes4));
    for(_,arm)in arms(c){assert_eq!(arm.planes4.len(),4);assert!(arm.terminal_base_exact);
        assert!(arm.rgb.iter().all(|x|x.is_finite()));for ch in [1,2]{assert!(exact_slice(&arm.planes4[ch],&c.canonical.planes4[ch]));}}
    for arm in [&c.guarded,&c.camera_green_only]{for p in 0..c.native_width*c.native_height{
        assert_eq!(arm.rgb[3*p+1].to_bits(),c.canonical.rgb[3*p+1].to_bits());}}
    for p in 0..c.native_width*c.native_height{for ch in [0,2]{assert_eq!(c.camera_green_only.rgb[3*p+ch].to_bits(),c.own.rgb[3*p+ch].to_bits());}}
    let n=crop().width*crop().height;let nb=c.level_sizes.len()-1;
    assert!(c.threshold.is_finite() && c.threshold>0.0);assert_eq!(c.source_trigger_counts_rb.len(),frames.len());
    let mut fractions=[vec![],vec![]];for colour in 0..2{
        assert_eq!(c.activation_masks_rb[colour].len(),nb);assert_eq!(c.activation_counts_rb[colour].len(),nb);
        for k in 0..nb{let mask=&c.activation_masks_rb[colour][k];let size=c.level_sizes[k];assert_eq!(mask.len(),size[0]*size[1]);
            assert!(mask.iter().all(|&v|v==0.0 || v==1.0));let count=mask.iter().filter(|&&v|v==1.0).count();
            assert_eq!(count,c.activation_counts_rb[colour][k]);fractions[colour].push(count as f64/mask.len()as f64);}
        if c.activation_counts_rb[colour].iter().all(|&v|v==0){let ch=[0,3][colour];assert!(exact_slice(&c.guarded.planes4[ch],&c.canonical.planes4[ch]));}
    }
    let mut lo=vec![vec![f32::INFINITY;n];4];let mut hi=vec![vec![f32::NEG_INFINITY;n];4];let mut focused=vec![];
    let mut seeds=std::collections::BTreeSet::new();let mut clipped=0;
    for(k,f)in frames.iter().enumerate(){let e=&c.frames[k];assert_eq!(hash(&f.data),before[k]);assert_eq!(e.source_sha256,before[k]);assert!(e.source_unchanged);
        let mut active=Vec::with_capacity(W*H);for y in 0..H{active.extend_from_slice(&f.active_row(y)[..W]);}assert_eq!(hash(&active),e.active_sha256);
        for seed in e.probe_seeds{assert!(seeds.insert(seed));}assert!(e.baseline_beta.iter().all(|v|v.is_finite() && *v>0.0));
        let known=super::super::boundary_cfa_wavelet::gather_known4(f,ts[k],crop()).unwrap();for ch in 0..4{
            assert_eq!(hash_f32(&known[ch]),e.known4_sha256[ch]);for p in 0..n{lo[ch][p]=lo[ch][p].min(known[ch][p]);hi[ch][p]=hi[ch][p].max(known[ch][p]);}}
        if matches!(scene,Scene::Offset|Scene::ColourOnly) && [1,3].contains(&k){let rgb=super::super::phase_packed_rgb::camera_rgb(&known,crop().width,crop().height,levels(),f.wb_coeffs).unwrap();
            focused.push(json!({"source":k,"score":score_json(&score(scene,&rgb,INTERIOR))}));}
        for y in 0..H{clipped+=f.active_row(y)[..W].iter().filter(|&&v|v>=16383).count();}assert_eq!(hash(&f.data),before[k]);
    }
    for(_,arm)in arms(c){for ch in 0..4{assert_eq!(arm.planes4[ch].len(),n);for p in 0..n{
        let v=arm.planes4[ch][p];assert!(v.is_finite() && v>=lo[ch][p] && v<=hi[ch][p]);}}}
    if scene==Scene::ClippedGlint{assert!(clipped>0);}else{assert_eq!(clipped,0);}
    json!({"green_cfa_exact":true,"guarded_camera_green_exact":true,"terminal_base_exact":true,"canonical_identity_exact":true,
        "original_hull":true,"clipped_original_codes":clipped,"focused_sources":focused,"probe_seed_count":seeds.len(),
        "activation_fractions_rb":fractions})
}
fn retained_old(c:&Comparison,scene:Scene,iso:f32,old:&Value)->Value{
    let record=old["cases"].as_array().unwrap().iter().find(|r|r["scene"]==scene.name() && r["iso"].as_f64()==Some(iso as f64)).unwrap();
    for(name,arm)in arms(c).into_iter().take(5){let expected=record["consumer"]["arms"].as_array().unwrap().iter().find(|a|a["name"]==name).unwrap();
        assert_eq!(hash_f32(&arm.rgb),expected["rgb_sha256"].as_str().unwrap(),"old {name} RGB changed");
        for ch in 0..4{assert_eq!(hash_f32(&arm.planes4[ch]),expected["known4_sha256"][ch].as_str().unwrap());}}
    for(k,f)in c.frames.iter().enumerate(){let r=&record["consumer"]["frames"][k];assert_eq!(f.source_sha256,r["source_sha256"].as_str().unwrap());
        assert_eq!(json!(f.probe_seeds),r["probe_seeds"]);assert_eq!(json!(f.guide_fields.iter().map(|g|&g.floor_sha256).collect::<Vec<_>>()),r["guide_floors"]);}
    json!({"all_five_prior_arms_exact":true,"source_probe_seeds_and_measured_floors_exact":true})
}
fn compact(c:&Comparison)->Value{json!({"threshold":c.threshold,"level_sizes":c.level_sizes,"activation_counts_rb":c.activation_counts_rb,
    "source_trigger_counts_rb":c.source_trigger_counts_rb,"coefficient_variance_sha256":c.coefficient_variance_sha256,
    "arms":arms(c).iter().map(|(name,a)|json!({"name":name,"rgb_sha256":hash_f32(&a.rgb),"planes4_sha256":a.planes4.iter().map(|v|hash_f32(v)).collect::<Vec<_>>()})).collect::<Vec<_>>(),
    "sources":c.frames.iter().map(|f|json!({"sha256":f.source_sha256,"active_sha256":f.active_sha256,"seeds":f.probe_seeds})).collect::<Vec<_>>()})}

#[test]
fn independent_rb_residual_guard_actual_truth_screen(){
    let out=PathBuf::from(std::env::var_os("STREHL_RB_RESIDUAL_GUARD_OUT").expect("root-owned output required"));std::fs::create_dir(&out).unwrap();
    let noise_control=super::independent_noise_controls::check_residual_guard().unwrap();let commissioned=commission();
    assert_eq!(digest(OLD_SCREEN.as_bytes()),"5bae9a282349905a2d7dc391a55ced39e19f0eda9c6d24ec75706f96c3ed7cb3");let old:Value=serde_json::from_str(OLD_SCREEN).unwrap();
    let mut cases=vec![];for iso in [100.0f32,400.0]{for n in [5,9]{cases.push((Scene::Flat,iso,n));}}
    for iso in [100.0f32,400.0]{for scene in [Scene::Offset,Scene::ColourOnly]{cases.push((scene,iso,5));}}
    for scene in [Scene::Neutral,Scene::ThinDepth,Scene::Radial,Scene::ClippedGlint]{cases.push((scene,100.0,5));}
    let mut records=vec![];let mut admission=true;let mut wrong_exercised=false;
    for(scene,iso,n)in cases{let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());assert!(noise.is_trustworthy() && noise.prnu().is_none());
        let held=transforms();let ts=(0..n).map(|k|held[k%N]).collect::<Vec<_>>();let cfg=MergeConfig::default();
        let frames=ts.iter().enumerate().map(|(k,&t)|fixture(scene,k,t,iso,&noise)).collect::<Vec<_>>();let before=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
        let c=compare_generated(&frames,&ts,crop(),&noise,cfg).unwrap();let structural=check(&c,&frames,&ts,&before,scene);
        let preservation=if n==5{retained_old(&c,scene,iso,&old)}else{Value::Null};let positive=matches!(scene,Scene::Offset|Scene::ColourOnly);
        let windows:&[Window]=match scene{Scene::ThinDepth=>&[THIN_FAR,THIN_NEAR,JUNCTION],Scene::Radial=>&[RADIAL],Scene::ClippedGlint=>&[OUTSIDE,NEAR],_=>&[INTERIOR]};
        let mut pass=true;let mut scores=vec![];for &window in windows{
            let canonical=score(scene,&c.canonical.rgb,window);let matched=score(scene,&c.matched_green.rgb,window);let guarded=score(scene,&c.guarded.rgb,window);
            let raw=score(scene,&c.own.rgb,window);let green_only=score(scene,&c.camera_green_only.rgb,window);let mut gate=true;
            for reference in [&canonical,&matched]{if scene==Scene::Flat{gate&=guarded.rgb<=1.05*reference.rgb && guarded.chroma<=1.05*reference.chroma;}
                else{gate&=guarded.rgb<=1.10*reference.rgb && guarded.green<=1.10*reference.green && guarded.chroma<=1.10*reference.chroma && recovery_pass(reference,&guarded);}
                if positive{gate&=guarded.rgb<=0.95*reference.rgb && guarded.chroma<=0.95*reference.chroma;}}
            if matches!(scene,Scene::ThinDepth|Scene::Radial) || window.name=="unsaturated-adjacent-texture"{gate&=canonical.recovery.iter().all(|v|*v>=0.5);}
            pass&=gate;scores.push(json!({"name":window.name,"pass":gate,"canonical":score_json(&canonical),"matched_green":score_json(&matched),
                "own_unguarded":score_json(&raw),"camera_green_only":score_json(&green_only),"guarded":score_json(&guarded),
                "rgb_ratios":[ratio(guarded.rgb,canonical.rgb),ratio(guarded.rgb,matched.rgb)],"chroma_ratios":[ratio(guarded.chroma,canonical.chroma),ratio(guarded.chroma,matched.chroma)]}));
        }
        let activation_budget=if scene==Scene::Flat{Some(structural["activation_fractions_rb"].as_array().unwrap().iter()
            .flat_map(|a|a.as_array().unwrap()).all(|v|v.as_f64().unwrap()<=0.01))}else{None};if let Some(ok)=activation_budget{pass&=ok;}
        let mut positive_control=Value::Null;if positive{let live=[(0,0),(1,3)].iter().all(|&(mask,ch)|c.activation_counts_rb[mask].iter().any(|&n|n>0)
                && !exact_slice(&c.guarded.planes4[ch],&c.canonical.planes4[ch]) && !exact_slice(&c.guarded.planes4[ch],&c.matched_green.planes4[ch]));
            let f=&structural["focused_sources"];let feasible=f[0]["score"]["truth_template_recovery"][0].as_f64().unwrap()>=0.5 && f[1]["score"]["truth_template_recovery"][2].as_f64().unwrap()>=0.5;
            let own=score(scene,&c.own.rgb,INTERIOR);let swapped=score(scene,&c.swapped.rgb,INTERIOR);let destroyed=swapped.rgb>1.10*own.rgb || !recovery_pass(&own,&swapped);wrong_exercised|=destroyed;
            pass&=live && feasible;positive_control=json!({"guarded_rb_live":live,"focused_source_feasible":feasible,"swapped_old_guides":score_json(&swapped),"wrong_guide_destroyer_exercised":destroyed});}
        let mut observer=Value::Null;if scene==Scene::Offset && iso==100.0{let off=compare_generated_with_diagnostics(&frames,&ts,crop(),&noise,cfg,false).unwrap();
            for((name,a),(other,b))in arms(&c).into_iter().zip(arms(&off)){assert_eq!(name,other);assert!(exact_arm(a,b),"diagnostics changed {name}");}
            assert_eq!(c.threshold.to_bits(),off.threshold.to_bits());for rb in 0..2{assert!(exact(&c.activation_masks_rb[rb],&off.activation_masks_rb[rb]));}
            for(k,f)in frames.iter().enumerate(){assert_eq!(hash(&f.data),before[k]);assert_eq!(c.frames[k].probe_seeds,off.frames[k].probe_seeds);}
            observer=json!({"seven_arms_exact":true,"masks_threshold_seeds_exact":true,"rgb_hashes_on":arms(&c).iter().map(|(_,a)|hash_f32(&a.rgb)).collect::<Vec<_>>(),
                "rgb_hashes_off":arms(&off).iter().map(|(_,a)|hash_f32(&a.rgb)).collect::<Vec<_>>()});}
        admission&=pass;records.push(json!({"scene":scene.name(),"iso":iso,"frames":n,"pass":pass,"windows":scores,"structural":structural,
            "flat_activation_budget_pass":activation_budget,"positive_control":positive_control,"prior_preservation":preservation,"observer":observer,"consumer":compact(&c)}));
    }
    admission&=wrong_exercised;write(&out.join("screen.json"),&json!({"status":"SCREEN_COMPLETE","photographic_replay_admitted":admission,
        "metric_commission":commissioned,"noise_control":noise_control,"wrong_guide_destroyer_exercised":wrong_exercised,"cases":records,
        "scope":"Fixed generated conditional-model screen. Activation-area budget is empirical, not FWER or calibrated confidence after native reconstruction."}));
    eprintln!("RB_RESIDUAL_GUARD_DECISION {}",json!({"photographic_replay_admitted":admission}));
}
