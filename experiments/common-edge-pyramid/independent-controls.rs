// Independent choices and final-consumer scoring; no operator arithmetic here.
include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/learned-band-guide/independent-fixtures.rs"));
use super::{Arm, Comparison, EdgeMerge, EdgePyramid, compare_generated};
use strehl_core::plane::QuadSource;
use strehl_core::pyramid::{LevelSize,level_sizes};

fn output()->PathBuf{let p=PathBuf::from(std::env::var("STREHL_COMMON_EDGE_PYRAMID_OUT").expect("bounded output directory"));std::fs::create_dir_all(&p).unwrap();p}
fn cfg()->MergeConfig{MergeConfig{bands:3,..Default::default()}}
fn exact(a:&[f32],b:&[f32])->bool{a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())}
fn exact4(a:&[Vec<f32>],b:&[Vec<f32>])->bool{a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|exact(a,b))}
fn max_error(a:&[f32],b:&[f32])->f64{assert_eq!(a.len(),b.len());a.iter().zip(b).map(|(a,b)|{assert!(a.is_finite()&&b.is_finite());(f64::from(*a)-f64::from(*b)).abs()}).fold(0.0,f64::max)}
fn max4(a:&[Vec<f32>],b:&[Vec<f32>])->f64{assert_eq!(a.len(),b.len());a.iter().zip(b).map(|(a,b)|max_error(a,b)).fold(0.0,f64::max)}
fn hashes4(a:&[Vec<f32>])->Vec<String>{a.iter().map(|p|hash_f32(p)).collect()}
fn arm<'a>(r:&'a Comparison,name:&str)->&'a Arm{r.arms.iter().find(|a|a.name==name).unwrap()}
fn arm_hashes(a:&Arm)->Value{json!({"name":a.name,"cfa":hashes4(&a.planes4),"pre_hull":hashes4(&a.pre_hull4),"terminal":hashes4(&a.terminal4),"rgb":hash_f32(&a.rgb),"guide":hash_f32(&a.guide),"guide_levels":a.guide_level_sha256,"stencil_bytes":a.stencil_bytes})}
fn check_arm(a:&Arm){assert_eq!(a.planes4.len(),4);assert_eq!(a.pre_hull4.len(),4);assert_eq!(a.terminal4.len(),4);assert_eq!(a.rgb.len(),NW*NH*3);for p in a.planes4.iter().chain(&a.pre_hull4){assert_eq!(p.len(),NW*NH/4);assert!(p.iter().all(|x|x.is_finite()));}assert!(a.rgb.iter().chain(&a.guide).all(|x|x.is_finite()));}
fn observer_equal(a:&Arm,b:&Arm){assert_eq!(a.name,b.name);assert!(exact4(&a.planes4,&b.planes4)&&exact4(&a.pre_hull4,&b.pre_hull4)&&exact4(&a.terminal4,&b.terminal4)&&exact(&a.rgb,&b.rgb)&&exact(&a.guide,&b.guide));}
fn true_guide(g:&Generated)->Vec<f32>{(0..NH/2).flat_map(|y|(0..NW/2).map(move|x|{let mut s=0.0;for dy in 0..2{for dx in 0..2{s+=g.truth[((2*y+dy)*NW+2*x+dx)*3+1];}}s*(0.25*levels().range())})).collect()}
fn positive(f:Family)->Option<Window>{match f{Family::Curved=>Some(CURVED),Family::Thin=>Some(THIN),_=>None}}
// Ordinary one-pass canonical consumer: no new guide, field extraction,
// per-frame diagnostic hash, or second pass. This is the observer-off control.
fn ordinary_canonical(g:&Generated,noise:&NoiseModel)->(Vec<Vec<f32>>,Vec<f32>){
    let full=g.frames[0].geometry();let entries=g.frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes()as u64)).collect::<Vec<_>>();
    let map=super::WarpMap::new(strehl_core::warpmap::Provenance{stack:super::StackIdentity::from_entries("common-edge-generated",&entries),strategy:"supplied generated direct geometry".into(),heldout_px:None,cycle_floor_px:None,reference:0,note:"independent ordinary canonical control".into()},full,super::Resampler::CatmullRom,g.transforms.iter().copied().map(super::FrameWarp::Placed).collect());
    struct Source<'a>(&'a[Frame]);impl super::PyramidFrameSource for Source<'_>{fn len(&self)->usize{self.0.len()}fn decode(&self,i:usize)->anyhow::Result<Frame>{Ok(self.0[i].clone())}}
    let source=Source(&g.frames);let mut worker=super::BandWorker::new(super::PyramidDomain::cropped(full,crop()).unwrap(),cfg());
    for i in 0..g.frames.len(){assert!(worker.fold(&source,i,levels(),noise,Some(&map),None).unwrap());}
    let sizes=level_sizes(crop().width,crop().height,cfg().bands);let planes=worker.merge.finish(&mut super::Workspace::new(&sizes));
    let rgb=super::phase_packed_rgb::camera_rgb(&planes,crop().width,crop().height,levels(),g.frames[0].wb_coeffs).unwrap();(planes,rgb)
}

// RMSE can reward erased detail; signed component recovery can hide offsets or
// reward correlated artifacts. Their conjunction, not either alone, is scored.
fn judge(case:&Case,g:&Generated,canonical:&[f32],uniform:&[f32],candidate:&[f32])->Value{
    let mut pass=true;let mut rows=Vec::new();let(mut eligible,mut unqualified)=(0,0);
    for w in windows(case.family){let c=score(g,canonical,w);let u=score(g,uniform,w);let p=score(g,candidate,w);
        for channel in 0..3{for d in 0..2{match c.coeff[channel][d]{Some(r)if r>=0.5=>eligible+=1,Some(_)=>unqualified+=1,None=>{}}}}
        let error_pass=safe(&c,&p)&&(case.family!=Family::Flat||safe(&u,&p));let retention_pass=retained(&c,&p);let ok=error_pass&&retention_pass;pass&=ok;
        rows.push(json!({"window":w.name,"source_native_xyxy":[w.x0,w.y0,w.x1,w.y1],"output_native_xyxy":[w.x0-16,w.y0-16,w.x1-16,w.y1-16],"canonical":score_json(&c),"uniform":score_json(&u),"candidate":score_json(&p),"error_pass":error_pass,"retention_pass":retention_pass,"preservation_pass":ok}));
    }
    let gain=positive(case.family).map(|w|{let c=score(g,canonical,w);let p=score(g,candidate,w);json!({"window":w.name,"canonical_rgb_rmse":c.rgb,"candidate_rgb_rmse":p.rgb,"pass":p.rgb<=0.95*c.rgb})});
    let positive_pass=gain.as_ref().is_none_or(|v|v["pass"]==true);
    json!({"windows":rows,"positive":gain,"preservation_pass":pass,"positive_pass":positive_pass,"eligible_canonical_components":eligible,"unqualified_canonical_components":unqualified,"pass":pass&&positive_pass})
}
fn witness(case:&Case,g:&Generated,canonical:&[f32],w:Window,c:usize,d:usize)->Value{let s=score(g,canonical,w);let v=s.coeff[c][d];json!({"case":case.id,"window":w.name,"channel":c,"component":d,"canonical_recovery":v,"template_sd":s.template_sd[c][d],"condition":s.condition[c],"live":v.is_some_and(|r|r>=0.5)})}

#[test]
#[ignore]
fn a_independent_native_screen(){
    let ids=["held-flat-n5","held-flat-n9","train-flat-1","held-curved-bright-occlusion-n9","held-near-fine-far-coarse-n5","held-unclipped-point-glint-n5","held-clipped-point-glint-n5","held-weak-colour-dots-n5"];
    let available=cases();let mut rows=Vec::new();let mut witnesses=Vec::new();let mut destroyers=Vec::new();let mut oracle=Vec::new();let mut headroom=Vec::new();let mut flats=Vec::<(usize,f64)>::new();
    let(mut all_preserved,mut positives_pass,mut candidate_live,mut wrong_guides_live)=(true,true,false,false);
    let mut nuisance_failures=Vec::new();let mut observer_rows=Vec::new();
    for (case_index,id) in ids.iter().enumerate(){
        let case=available.iter().find(|c|c.id==*id).unwrap();assert_eq!(case.family==Family::Flat,case_index<3);
        let g=generate(case);let input_hashes=g.frames.iter().map(|f|hash16(&f.data)).collect::<Vec<_>>();let noise=profile::noise_model_for("ILCE-7CM2",Some(case.iso),levels());let truth_guide=true_guide(&g);
        let r=compare_generated(&g.frames,&g.transforms,crop(),&noise,cfg(),Some(&truth_guide),true).unwrap();
        assert_eq!((r.native_width,r.native_height),(NW,NH));assert_eq!(r.level_sizes.len(),4);assert_eq!(r.frames.len(),case.n);assert!(r.canonical_replay_exact&&r.frames.iter().all(|f|f.replay_exact));
        assert_eq!(input_hashes,g.frames.iter().map(|f|hash16(&f.data)).collect::<Vec<_>>());
        assert_eq!(r.arms.iter().map(|a|a.name.as_str()).collect::<Vec<_>>(),["common-canonical","constant","displaced","temporal-mean","true"]);
        for a in std::iter::once(&r.canonical).chain(std::iter::once(&r.uniform)).chain(&r.arms){check_arm(a);}
        assert!(exact(&arm(&r,"true").guide,&truth_guide));
        let candidate=arm(&r,"common-canonical");let constant=arm(&r,"constant");
        let constant_cfa_error=max4(&constant.planes4,&r.canonical.planes4);let constant_rgb_error=max_error(&constant.rgb,&r.canonical.rgb);
        assert!(constant_cfa_error<=0.02&&constant_rgb_error<=5e-6,"constant guide Gaussian algebra mismatch: {constant_cfa_error} / {constant_rgb_error}");
        // A flat and a mixed-depth case exercise observer identity on every arm.
        if case_index==0||case.family==Family::Thin{
            let (ordinary_planes,ordinary_rgb)=ordinary_canonical(&g,&noise);assert!(exact4(&ordinary_planes,&r.canonical.planes4)&&exact(&ordinary_rgb,&r.canonical.rgb));
            let off=compare_generated(&g.frames,&g.transforms,crop(),&noise,cfg(),Some(&truth_guide),false).unwrap();assert!(off.frames.is_empty());
            observer_equal(&r.canonical,&off.canonical);observer_equal(&r.uniform,&off.uniform);
            for(a,b)in r.arms.iter().zip(&off.arms){observer_equal(a,b);assert!(b.guide_level_sha256.is_empty());}
            observer_rows.push(json!({"case":case.id,"diagnostic_emission_all_arm_cfa_rgb_pre_hull_terminal_bit_exact":true,"ordinary_one_pass_canonical_cfa_rgb_bit_exact":true,"ordinary_cfa_sha256":hashes4(&ordinary_planes),"ordinary_rgb_sha256":hash_f32(&ordinary_rgb),"mandatory_integrity_checks_disabled":false,"on":std::iter::once(&r.canonical).chain(std::iter::once(&r.uniform)).chain(&r.arms).map(arm_hashes).collect::<Vec<_>>(),"emission_off":std::iter::once(&off.canonical).chain(std::iter::once(&off.uniform)).chain(&off.arms).map(arm_hashes).collect::<Vec<_>>() }));
        }
        let decision=judge(case,&g,&r.canonical.rgb,&r.uniform.rgb,&candidate.rgb);all_preserved&=decision["preservation_pass"]==true;positives_pass&=decision["positive_pass"]==true;
        let delta=max_error(&candidate.rgb,&r.canonical.rgb);candidate_live|=delta>1e-6;
        let truth_decision=judge(case,&g,&r.canonical.rgb,&r.uniform.rgb,&g.truth);assert_eq!(truth_decision["pass"],true,"perfect truth must pass scorer");oracle.push(json!({"case":case.id,"decision":truth_decision}));
        if case.family==Family::Flat&&case.iso==100.0{flats.push((case.n,score(&g,&r.canonical.rgb,WHOLE).rgb));}
        if let Some(w)=positive(case.family){let e=score(&g,&r.canonical.rgb,w).rgb;let flat=flats.iter().find(|(n,_)|*n==case.n).unwrap().1;headroom.push(json!({"case":case.id,"window":w.name,"canonical_rgb_rmse":e,"same_N_flat_rgb_rmse":flat,"same_brightness":false,"live":e>2.0*flat}));}
        let mut arm_rows=Vec::new();for a in &r.arms{let d=judge(case,&g,&r.canonical.rgb,&r.uniform.rgb,&a.rgb);let guide_delta=max_error(&a.guide,&candidate.guide);let rgb_delta=max_error(&a.rgb,&candidate.rgb);
            if case.family==Family::Curved&&["displaced","temporal-mean","constant","true"].contains(&a.name.as_str()){assert!(guide_delta>0.02,"guide re-choice was inert");wrong_guides_live|=rgb_delta>1e-6;}
            if case.family!=Family::Flat&&["displaced","temporal-mean"].contains(&a.name.as_str())&&d["preservation_pass"]==false{nuisance_failures.push(json!({"case":case.id,"guide":a.name,"harmful_guide_lock_in":true,"decision":d.clone()}));}
            arm_rows.push(json!({"name":a.name,"diagnostic_only":a.name!="common-canonical","guide_max_delta_dn":guide_delta,"output_max_delta_from_actual_guide":rgb_delta,"decision":d,"hashes":arm_hashes(a)}));
        }
        let mut mutate=|label:&str,mutant:Vec<f32>|{let d=judge(case,&g,&r.canonical.rgb,&r.uniform.rgb,&mutant);assert_eq!(d["pass"],false,"same-path destroyer {label} must reject");destroyers.push(json!({"case":case.id,"name":label,"decision":d}));};
        if case_index==0{let mut noisy=g.truth.clone();for(j,v)in noisy.iter_mut().enumerate(){*v+=0.10*random_normal((j/3)%NW,(j/3)/NW,j%3,0x97650b13);}mutate("independent_added_flat_noise",noisy);}
        if case.family==Family::Thin{witnesses.push(witness(case,&g,&r.canonical.rgb,THIN,1,0));witnesses.push(witness(case,&g,&r.canonical.rgb,THIN,1,1));mutate("erased_near_detail",g.truth.iter().zip(&g.near_detail).map(|(t,n)|t-n).collect());mutate("erased_far_detail",g.truth.iter().zip(&g.far_detail).map(|(t,n)|t-n).collect());}
        if case.family==Family::Glint{witnesses.push(witness(case,&g,&r.canonical.rgb,GLINT,1,1));mutate("erased_genuine_glint",g.truth.iter().zip(&g.far_detail).map(|(t,n)|t-n).collect());}
        if case.family==Family::Colour{witnesses.push(witness(case,&g,&r.canonical.rgb,COLOUR,0,0));witnesses.push(witness(case,&g,&r.canonical.rgb,COLOUR,2,0));mutate("erased_weak_colour",g.truth.iter().zip(&g.near_detail).map(|(t,n)|t-n).collect());}
        rows.push(json!({"id":case.id,"family":case.family.name(),"iso":case.iso,"sources":case.n,"pupil":pupil_name(case),"clipped_original_samples":g.clipped,"truth_sha256":hash_f32(&g.truth),"source_buffer_sha256":input_hashes,"source_evidence":r.frames,"level_sizes":r.level_sizes,"canonical":arm_hashes(&r.canonical),"uniform":arm_hashes(&r.uniform),"constant_guide_cfa_error_dn":constant_cfa_error,"constant_guide_rgb_error":constant_rgb_error,"actual_guide_rgb_delta":delta,"actual_decision":decision,"arms":arm_rows}));
    }
    assert_eq!(rows.len(),8);assert_eq!(observer_rows.len(),2);assert_eq!(destroyers.len(),5);assert_eq!(witnesses.len(),5);assert_eq!(headroom.len(),2);
    let protected_live=witnesses.iter().all(|v|v["live"]==true);let positive_exercised=headroom.iter().all(|v|v["live"]==true);
    let nomination=all_preserved&&positives_pass&&candidate_live&&wrong_guides_live&&protected_live&&positive_exercised;
    let screen=json!({"schema":1,"status":"SCREEN_COMPLETE","cases":rows,"observer_checks":observer_rows,"truth_oracle":oracle,"destroyers":destroyers,"protected_witnesses":witnesses,"positive_headroom":headroom,"nuisance_guide_failures":nuisance_failures,"mechanical_pass":true,"scorer_commissioned":true,"preservation_pass":all_preserved,"positive_pass":positives_pass,"candidate_live":candidate_live,"wrong_guides_live":wrong_guides_live,"protected_witnesses_live":protected_live,"positive_exercised":positive_exercised,"candidate_nominated":nomination,"photographic_replay_admitted":false,"calibration_validation":false,"fresh_validation":false,"seven_band_occlusion_validation":false});
    write(&output().join("screen.json"),&screen);println!("COMMON_EDGE_PYRAMID {}",screen["candidate_nominated"]);
}

include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/common-edge-pyramid/independent-operator-controls.rs"));
