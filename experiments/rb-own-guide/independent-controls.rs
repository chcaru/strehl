// Independent image-truth decisions; root alone executes.
include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/rb-own-guide/independent-fixtures.rs"));
use super::{Arm,Comparison,compare_generated,compare_generated_with_diagnostics};

fn hash_f32(v:&[f32])->String{let mut h=Sha256::new();for x in v{h.update(x.to_bits().to_le_bytes());}h.finalize().iter().map(|x|format!("{x:02x}")).collect()}
fn arms(c:&Comparison)->[(&'static str,&Arm);5]{[("canonical",&c.canonical),("matched-green",&c.matched_green),
    ("own-rb",&c.own),("canonical-identity",&c.identity),("swapped-guides",&c.swapped)]}
fn exact_arm(a:&Arm,b:&Arm)->bool{exact(&a.planes4,&b.planes4) && exact_slice(&a.rgb,&b.rgb)}
fn check(c:&Comparison,frames:&[Frame],ts:&[Similarity],before:&[String],scene:Scene)->Value{
    assert_eq!((c.native_width,c.native_height),(2*crop().width,2*crop().height));
    assert_eq!(c.level_sizes,vec![[145,125],[73,63],[37,32],[19,16],[10,8]]);
    assert_eq!(c.frames.len(),N);assert!(exact_arm(&c.canonical,&c.identity));
    for(_,arm)in arms(c){assert_eq!(arm.planes4.len(),4);assert!(arm.terminal_base_exact);
        assert!(arm.rgb.iter().all(|x|x.is_finite()));
        for green in [1,2]{assert!(exact_slice(&c.canonical.planes4[green],&arm.planes4[green]));}
    }
    let n=crop().width*crop().height;let mut lo=vec![vec![f32::INFINITY;n];4];let mut hi=vec![vec![f32::NEG_INFINITY;n];4];
    let mut focused=vec![];let mut all_seeds=std::collections::BTreeSet::new();let mut clipped=0usize;
    for(k,frame)in frames.iter().enumerate(){let e=&c.frames[k];assert_eq!(hash(&frame.data),before[k]);assert_eq!(e.source_sha256,before[k]);
        assert!(e.source_unchanged);assert!(e.baseline_beta.iter().all(|v|v.is_finite() && *v>0.0));
        let mut active=Vec::with_capacity(W*H);for y in 0..H{active.extend_from_slice(&frame.active_row(y)[..W]);}
        assert_eq!(hash(&active),e.active_sha256);
        for seed in e.probe_seeds{assert!(all_seeds.insert(seed),"independent source/draw probe seed collision");}
        for field in std::iter::once(&e.canonical_fields).chain(e.guide_fields.iter()){
            assert_eq!(field.energy_sha256.len(),c.level_sizes.len()-1);assert_eq!(field.floor_sha256.len(),field.energy_sha256.len());
            assert_eq!(field.weight_sha256.len(),field.energy_sha256.len());assert_eq!(field.positive_weight_counts.len(),field.energy_sha256.len());
        }
        // Independent current-frame re-gather: retain only extrema and small scores.
        let known=super::super::boundary_cfa_wavelet::gather_known4(frame,ts[k],crop()).unwrap();
        for ch in 0..4{assert_eq!(hash_f32(&known[ch]),e.known4_sha256[ch]);for p in 0..n{lo[ch][p]=lo[ch][p].min(known[ch][p]);hi[ch][p]=hi[ch][p].max(known[ch][p]);}}
        if matches!(scene,Scene::Offset|Scene::ColourOnly) && [1,3].contains(&k){
            let rgb=super::super::phase_packed_rgb::camera_rgb(&known,crop().width,crop().height,levels(),frames[0].wb_coeffs).unwrap();
            let s=score(scene,&rgb,INTERIOR);focused.push(json!({"source":k,"score":score_json(&s)}));
        }
        for y in 0..H{clipped+=frame.active_row(y)[..W].iter().filter(|&&v|v>=16383).count();}
        assert_eq!(hash(&frame.data),before[k]);
    }
    for(_,arm)in arms(c){for ch in 0..4{assert_eq!(arm.planes4[ch].len(),n);for p in 0..n{
        assert!(arm.planes4[ch][p].is_finite() && arm.planes4[ch][p]>=lo[ch][p] && arm.planes4[ch][p]<=hi[ch][p],"actual original input hull escaped");
    }}}
    if scene==Scene::ClippedGlint{assert!(clipped>0,"clipped-glint guard was not exercised");}else{assert_eq!(clipped,0);}
    json!({"green_cfa_exact":true,"terminal_base_exact":true,"canonical_identity_exact":true,"original_hull":true,
        "clipped_original_codes":clipped,"focused_sources":focused,"probe_seed_count":all_seeds.len()})
}
fn evidence(c:&Comparison)->Value{json!({"level_sizes":c.level_sizes,"baseline_averaged_fraction":c.baseline_averaged_fraction,
    "arms":arms(c).iter().map(|(name,arm)|json!({"name":name,"rgb_sha256":hash_f32(&arm.rgb),
        "known4_sha256":arm.planes4.iter().map(|v|hash_f32(v)).collect::<Vec<_>>(),"averaged_fraction_rb":arm.averaged_fraction_rb})).collect::<Vec<_>>(),
    "frames":c.frames.iter().map(|f|json!({"source_sha256":f.source_sha256,"active_sha256":f.active_sha256,
        "probe_seeds":f.probe_seeds,"known4_sha256":f.known4_sha256,"baseline_guide_sha256":f.baseline_guide_sha256,
        "baseline_variance_sha256":f.baseline_variance_sha256,"baseline_beta":f.baseline_beta,
        "canonical_weights":f.canonical_fields.weight_sha256,
        "guide_weights":f.guide_fields.iter().map(|g|&g.weight_sha256).collect::<Vec<_>>(),
        "guide_floors":f.guide_fields.iter().map(|g|&g.floor_sha256).collect::<Vec<_>>(),
        "guide_positive_counts":f.guide_fields.iter().map(|g|&g.positive_weight_counts).collect::<Vec<_>>()})).collect::<Vec<_>>()})}
fn relative(a:f64,b:f64)->f64{if b>0.0{a/b}else if a==0.0{1.0}else{f64::MAX}}

#[test]
fn independent_rb_own_guide_actual_truth_screen(){
    let out=PathBuf::from(std::env::var_os("STREHL_RB_OWN_GUIDE_OUT").expect("root-owned unique output required"));std::fs::create_dir(&out).unwrap();
    let noise_control=super::independent_noise_controls::check_noise_floor().unwrap();let commissioned=commission();
    let ts=transforms();let cfg=MergeConfig::default();let mut records=Vec::new();let mut admission=true;let mut wrong_exercised=false;
    for iso in [100.0f32,400.0]{let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());assert!(noise.is_trustworthy() && noise.prnu().is_none());
        let scenes:&[Scene]=if iso==100.0{&[Scene::Flat,Scene::Offset,Scene::ColourOnly,Scene::Neutral,Scene::ThinDepth,Scene::Radial,Scene::ClippedGlint]}
            else{&[Scene::Flat,Scene::Offset,Scene::ColourOnly]};
        for &scene in scenes{let frames=ts.iter().enumerate().map(|(k,&t)|fixture(scene,k,t,iso,&noise)).collect::<Vec<_>>();
            let before=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();let c=compare_generated(&frames,&ts,crop(),&noise,cfg).unwrap();
            let structural=check(&c,&frames,&ts,&before,scene);let positive=matches!(scene,Scene::Offset|Scene::ColourOnly);
            let windows:&[Window]=match scene{Scene::ThinDepth=>&[THIN_FAR,THIN_NEAR,JUNCTION],Scene::Radial=>&[RADIAL],
                Scene::ClippedGlint=>&[OUTSIDE,NEAR],_=>&[INTERIOR]};let mut pass=true;let mut scores=Vec::new();
            for &window in windows{let own=score(scene,&c.own.rgb,window);let canonical=score(scene,&c.canonical.rgb,window);let matched=score(scene,&c.matched_green.rgb,window);
                let mut gate=true;for reference in [&canonical,&matched]{
                    if scene==Scene::Flat{gate&=own.rgb<=1.25*reference.rgb && own.chroma<=1.25*reference.chroma;}
                    else{gate&=own.rgb<=1.10*reference.rgb && own.green<=1.10*reference.green && own.chroma<=1.10*reference.chroma && recovery_pass(reference,&own);}
                    if positive{gate&=own.rgb<=0.95*reference.rgb && own.chroma<=0.95*reference.chroma;}
                }
                if matches!(scene,Scene::ThinDepth|Scene::Radial) || window.name=="unsaturated-adjacent-texture"{
                    gate&=canonical.recovery.iter().all(|v|*v>=0.5); // plant must carry recoverable protected detail
                }
                pass&=gate;scores.push(json!({"name":window.name,"native_xyxy":[window.x0,window.y0,window.x1,window.y1],"pass":gate,
                    "canonical":score_json(&canonical),"matched_green":score_json(&matched),"own":score_json(&own),
                    "rgb_ratios":[relative(own.rgb,canonical.rgb),relative(own.rgb,matched.rgb)],
                    "chroma_ratios":[relative(own.chroma,canonical.chroma),relative(own.chroma,matched.chroma)]}));
            }
            let mut positive_control=Value::Null;if positive{
                let live=[(0,0),(2,3)].iter().all(|&(guide,plane)|c.frames.iter().any(|f|
                    f.guide_fields[guide].positive_weight_counts.iter().any(|&v|v>0)
                    && f.guide_fields[guide].weight_sha256!=f.guide_fields[1].weight_sha256)
                    && !exact_slice(&c.own.planes4[plane],&c.canonical.planes4[plane])
                    && !exact_slice(&c.own.planes4[plane],&c.matched_green.planes4[plane]));
                let focused=&structural["focused_sources"];
                let feasible=focused[0]["source"]==1 && focused[1]["source"]==3
                    && focused[0]["score"]["truth_template_recovery"][0].as_f64().unwrap()>=0.5
                    && focused[1]["score"]["truth_template_recovery"][2].as_f64().unwrap()>=0.5;
                let own=score(scene,&c.own.rgb,INTERIOR);let swapped=score(scene,&c.swapped.rgb,INTERIOR);
                let destroyed=swapped.rgb>1.10*own.rgb || !recovery_pass(&own,&swapped);wrong_exercised|=destroyed;
                pass&=live && feasible;positive_control=json!({"own_guides_live":live,"focused_source_feasible":feasible,
                    "swapped":score_json(&swapped),"wrong_guide_destroyer_exercised":destroyed});
            }
            let mut observer=Value::Null;if scene==Scene::Offset && iso==100.0{
                let off=compare_generated_with_diagnostics(&frames,&ts,crop(),&noise,cfg,false).unwrap();
                for((name,a),(other,b))in arms(&c).into_iter().zip(arms(&off)){assert_eq!(name,other);assert!(exact_arm(a,b),"diagnostics changed {name}");}
                for(k,f)in frames.iter().enumerate(){assert_eq!(hash(&f.data),before[k]);assert_eq!(c.frames[k].probe_seeds,off.frames[k].probe_seeds);}
                observer=json!({"all_five_arms_exact":true,"probe_seeds_exact":true,
                    "on_rgb_hashes":arms(&c).iter().map(|(_,a)|hash_f32(&a.rgb)).collect::<Vec<_>>(),
                    "off_rgb_hashes":arms(&off).iter().map(|(_,a)|hash_f32(&a.rgb)).collect::<Vec<_>>()});
            }
            admission&=pass;records.push(json!({"scene":scene.name(),"iso":iso,"pass":pass,"windows":scores,
                "structural":structural,"positive_control":positive_control,"observer":observer,"consumer":evidence(&c)}));
        }
    }
    admission&=wrong_exercised;
    write(&out.join("screen.json"),&json!({"status":"SCREEN_COMPLETE","photographic_replay_admitted":admission,
        "wrong_guide_destroyer_exercised":wrong_exercised,"metric_commission":commissioned,"noise_control":noise_control,"cases":records,
        "scope":"Actual rounded-gather generated image truth. No original RAW, camera calibration, full-photo or SOTA claim."}));
    eprintln!("RB_OWN_GUIDE_DECISION {}",json!({"photographic_replay_admitted":admission}));
}
