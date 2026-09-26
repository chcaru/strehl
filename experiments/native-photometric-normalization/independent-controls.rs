include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/native-photometric-normalization/independent-fixtures.rs"));
use super::{compare_generated,estimate_generated,scale_inputs,Comparison,Fit,Mode};
const OUT:&str="STREHL_NATIVE_PHOTOMETRIC_OUT";
fn output(name:&str,value:&Value){let root=std::path::PathBuf::from(std::env::var_os(OUT).expect("explicit owned output required"));assert!(root.is_dir());write(&root.join(name),value);}
fn noise()->NoiseModel{let n=profile::noise_model_for("ILCE-7CM2",Some(100.0),levels());assert!(n.is_trustworthy());n}
fn cfg()->MergeConfig{MergeConfig::default()}
fn available(f:&Fit)->bool{f.status=="AVAILABLE"&&f.mask_count>=1024&&f.refusals.iter().all(Option::is_none)}
fn max_gain_error(f:&Fit,expected:&[f64])->f64{assert_eq!(f.gains.len(),expected.len());f.gains.iter().zip(expected).map(|(g,e)|(f64::from(*g)/e-1.0).abs()).fold(0.0,f64::max)}
fn fit(frames:&[Frame],n:&NoiseModel)->Fit{estimate_generated(frames,&transforms(),crop(),REFERENCE,n,cfg()).unwrap()}
fn check(c:&Comparison,frames:&[Frame],before:&[String]){
    assert_eq!((c.native_width,c.native_height),(368,304));assert_eq!(c.frames.len(),N);assert_eq!(c.applied_gains.len(),N);
    assert_eq!(c.fit.reference,REFERENCE);assert_eq!(c.fit.gains.len(),N);assert_eq!(c.fit.refusals.len(),N);assert_eq!(c.fit.flux.len(),N);
    assert_eq!(c.fit.gains[REFERENCE].to_bits(),1.0f32.to_bits());
    for((f,h),e)in frames.iter().zip(before).zip(&c.frames){assert_eq!(&hash(&f.data),h);assert_eq!(&e.source_sha256,h);assert!(e.source_unchanged&&e.replay_exact);
        assert!(!e.beta.is_empty()&&e.beta.iter().all(|b|b.is_finite()&&*b>=0.0));assert_eq!(e.samples.len(),4);
        let g=e.applied_gain;assert!(g.is_finite()&&g>0.0);let g2=g*g;
        for s in &e.samples{for p in 0..4{assert_eq!(s.after_planes[p].to_bits(),(s.before_planes[p]*g).to_bits());}
            assert_eq!(s.after_luma.to_bits(),(s.before_luma*g).to_bits());assert_eq!(s.after_variance.to_bits(),(s.before_variance*g2).to_bits());}
        if g==1.0{assert_eq!(e.known4_sha256,e.candidate_known4_sha256);assert_eq!(e.guide_sha256,e.candidate_guide_sha256);assert_eq!(e.variance_sha256,e.candidate_variance_sha256);}
    }
    if c.applied_gains.iter().all(|g|*g==1.0){assert!(exact4(&c.baseline_planes4,&c.candidate_planes4));assert!(exact(&c.baseline_rgb,&c.candidate_rgb));}
}
fn compare(fs:&[Frame],n:&NoiseModel,mode:Mode,geometry:&[Similarity])->Comparison{
    let before=fs.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();let c=compare_generated(fs,geometry,crop(),REFERENCE,n,cfg(),mode).unwrap();check(&c,fs,&before);c
}
fn no_harm(b:&Score,c:&Score)->bool{c.rgb<=1.05*b.rgb+1e-7&&c.green<=1.05*b.green+1e-7&&c.chroma<=1.05*b.chroma+1e-7
    &&(0..3).all(|j|b.truth_sd[j]<1e-4||b.recovery[j]<0.5||c.recovery[j].clamp(0.0,1.0)>=0.98*b.recovery[j].min(1.0))}
fn row(scene:Scene,c:&Comparison,w:Window)->(Value,bool){let b=score(scene,&c.baseline_rgb,w);let a=score(scene,&c.candidate_rgb,w);let pass=no_harm(&b,&a);
    (json!({"window":if scene==Scene::Texture&&w.name==FLAT.name{"low-detail-gradient-surround"}else{w.name},"baseline":score_json(&b),"candidate":score_json(&a),"no_harm":pass}),pass)}

#[test]
fn independent_identity_and_noise_controls(){
    let source=vec![vec![-2.0,0.0,100.0,1024.0];4];let luma=vec![-2.0,0.0,100.0,1024.0];let variance=vec![1.0,4.0,9.0,16.0];
    let(mut p,mut l,mut v)=(source.clone(),luma.clone(),variance.clone());scale_inputs(&mut p,&mut l,&mut v,1.0).unwrap();
    assert!(exact4(&p,&source)&&exact(&l,&luma)&&exact(&v,&variance));
    let mut variance_destroyer_exercised=false;
    for g in [0.5f32,1.25]{let(mut p,mut l,mut v)=(source.clone(),luma.clone(),variance.clone());scale_inputs(&mut p,&mut l,&mut v,g).unwrap();
        let expected=variance.iter().map(|x|*x*g*g).collect::<Vec<_>>();assert!(exact(&v,&expected));
        assert!(p.iter().all(|p|exact(p,&source[0].iter().map(|x|*x*g).collect::<Vec<_>>())));assert!(exact(&l,&luma.iter().map(|x|*x*g).collect::<Vec<_>>()));
        assert_eq!(p[0][1].to_bits(),0.0f32.to_bits());assert!(p[0][0]<0.0,"black-subtracted negative was censored");
        let wrong=variance.iter().map(|x|*x*g).collect::<Vec<_>>();assert!(!exact(&wrong,&expected));variance_destroyer_exercised=true;
    }
    for g in [0.0,-1.0,f32::NAN,f32::INFINITY]{assert!(scale_inputs(&mut source.clone(),&mut luma.clone(),&mut variance.clone(),g).is_err());}
    let n=noise();let fs=frames(Scene::Flat,Drift::None,true,&n);
    // A non-integer gather makes the probed variance path nontrivial; all
    // frames share the same known geometry. No photographic score uses it.
    let warped=vec![Similarity{a:Cx::new(1.0,0.0),b:Cx::new(0.5,-0.5)};N];
    let off=compare(&fs,&n,Mode::Off,&warped);let unity=compare(&fs,&n,Mode::Unity,&warped);
    assert!(exact4(&off.baseline_planes4,&unity.baseline_planes4)&&exact4(&off.candidate_planes4,&unity.candidate_planes4));
    assert!(exact(&off.candidate_rgb,&unity.candidate_rgb));
    output("mechanical.json",&json!({"schema":1,"mechanical_pass":true,"unity_cfa_mhc_exact":true,
        "off_unity_identical":true,"variance_destroyer_exercised":variance_destroyer_exercised,
        "half_quad_translation":[0.5,-0.5],"frames":unity.frames}));
}

#[test]
fn independent_estimator_discrimination_controls(){
    let n=noise();let mut cases=Vec::new();let mut estimator_pass=true;
    for scene in [Scene::Texture,Scene::BroadDefocus]{let fs=frames(scene,Drift::None,false,&n);let twin=scaled_twins(&fs);
        assert_eq!(hash(&fs[REFERENCE].data),hash(&twin[REFERENCE].data));
        assert_ne!(hash(&fs[0].data),hash(&twin[0].data));assert_ne!(hash(&fs[4].data),hash(&twin[4].data));
        assert_ne!(hash(&fs[0].data),hash(&fs[REFERENCE].data),"no defocus in estimator stimulus");
        let no_drift_fit=fit(&fs,&n);let drift=fit(&twin,&n);let sampled_means=fs.iter().map(raw_means).collect::<Vec<_>>();
        let reference_means=sampled_means[REFERENCE];
        let max_raw_flux_drift=sampled_means.iter().flat_map(|v|(0..4).map(move|p|(v[p]/reference_means[p]-1.0).abs())).fold(0.0,f64::max);
        assert_eq!(no_drift_fit.mask_sha256,drift.mask_sha256,"identical reference changed fixed mask");assert_eq!(no_drift_fit.mask_count,drift.mask_count);
        let false_gain=max_gain_error(&no_drift_fit,&[1.0;N]);let expected=BRIGHTNESS.map(|x|1.0/x);let error=max_gain_error(&drift,&expected);
        let pass=available(&no_drift_fit)&&available(&drift)&&false_gain<=0.002&&error<=0.002;
        estimator_pass&=pass;
        cases.push(json!({"scene":scene.name(),"same_data_noiseless_twin":true,"reference_gain":1.0,
            "null":no_drift_fit,"uniform":drift,"expected_correction_gains":expected,"max_false_gain":false_gain,
            "max_relative_uniform_gain_error":error,"estimator_pass":pass,
            "raw_cfa_mean_above_black_rggb":sampled_means,"max_raw_cfa_flux_drift":max_raw_flux_drift,
            "raw_flux_within_0_02_percent":max_raw_flux_drift<=0.0002,
            "scope":"Uniform-scaling covariance alone is arithmetic; null gain must independently stay at unity."}));
    }
    output("estimator.json",&json!({"schema":1,"mechanical_pass":true,"estimator_pass":estimator_pass,"gain_tolerance":0.002,"cases":cases}));
}

#[test]
fn independent_refusal_controls(){
    let n=noise();let mut rows=Vec::new();
    let unsupported=frames(Scene::Unsupported,Drift::None,false,&n);let c=compare(&unsupported,&n,Mode::Estimated,&transforms());
    assert!(c.fit.mask_count<1024&&c.fit.status=="UNAVAILABLE"&&c.applied_gains.iter().all(|g|*g==1.0),"unsupported-region guard unexercised");
    rows.push(json!({"name":"insufficient-eroded-support","fit":c.fit,"exact_unity":true}));
    for(name,value,needle)in [("clipped-nonreference",16383u16,"clipped fraction"),("implausibly-dim-nonreference",544u16,"outside")]{
        let mut fs=frames(Scene::Flat,Drift::None,false,&n);let f=&mut fs[0];for y in 0..H{for x in 0..W{f.data[(f.active.y+y)*f.stride+f.active.x+x]=value;}}
        let c=compare(&fs,&n,Mode::Estimated,&transforms());assert_eq!(c.fit.status,"PARTIAL_REFUSAL");assert!(c.fit.refusals[0].as_ref().unwrap().contains(needle));
        assert_eq!(c.fit.gains[0],1.0);assert!(c.applied_gains.iter().all(|g|*g==1.0));
        rows.push(json!({"name":name,"fit":c.fit,"exact_unity":true}));
    }
    output("refusals.json",&json!({"schema":1,"mechanical_pass":true,"cases":rows,
        "scope":"Existing support/clipping/gain-band refusals; no spatial-nonuniformity detector or clipped-reference repair."}));
}

#[test]
fn independent_quality_screen(){
    let n=noise();let mut cases=Vec::new();let mut quality_pass=true;let mut positive_exercised=false;
    // Score brightness and texture destroyers against externally specified
    // radiance. Neither raw variance nor sharpness alone is the quality score.
    let truth=(0..2*crop().height).flat_map(|y|(0..2*crop().width).flat_map(move|x|(0..3).map(move|c|
        radiance(Scene::Texture,c,x+2*crop().x,y+2*crop().y,None)as f32))).collect::<Vec<_>>();
    let dark=truth.iter().map(|v|0.8*v).collect::<Vec<_>>();let good=score(Scene::Texture,&truth,LEFT);let bad=score(Scene::Texture,&dark,LEFT);
    let brightness_destroyer_exercised=good.rgb<1e-7&&bad.rgb>0.04&&!no_harm(&good,&bad);
    assert!(brightness_destroyer_exercised,"brightness-only change escaped image truth score");
    let added=truth.iter().enumerate().map(|(j,v)|*v+0.02*gaussian((j/3)%(2*crop().width),(j/3)/(2*crop().width),j%3)as f32).collect::<Vec<_>>();
    assert!(!no_harm(&score(Scene::Texture,&truth,FLAT),&score(Scene::Texture,&added,FLAT)),"flat-noise destroyer escaped");
    for(scene,drift,noisy)in [(Scene::Flat,Drift::None,true),(Scene::Flat,Drift::Uniform,true),
        (Scene::Texture,Drift::None,true),(Scene::Texture,Drift::Uniform,true),
        (Scene::BroadDefocus,Drift::None,false),(Scene::BroadDefocus,Drift::Uniform,false),
        (Scene::Texture,Drift::LeftOnly,true)]{
        let fs=frames(scene,drift,noisy,&n);let c=compare(&fs,&n,Mode::Estimated,&transforms());
        let windows=if scene==Scene::Texture{vec![WHOLE,FLAT,LEFT,RIGHT]}else{vec![WHOLE,FLAT]};
        let mut rows=Vec::new();let mut preservation=true;for w in windows{let(r,pass)=row(scene,&c,w);rows.push(r);preservation&=pass;}
        let mut improvement=true;
        if scene==Scene::Texture&&drift==Drift::Uniform{
            let whole=score(scene,&c.baseline_rgb,WHOLE);let left=score(scene,&c.baseline_rgb,LEFT);let right=score(scene,&c.baseline_rgb,RIGHT);
            positive_exercised=available(&c.fit)&&whole.rgb>0.001&&[&left,&right].iter().all(|s|s.recovery.iter().all(|r|*r>=0.5))
                &&c.applied_gains.iter().any(|g|(*g-1.0).abs()>0.01)&&!exact(&c.baseline_rgb,&c.candidate_rgb);
            improvement=[WHOLE,LEFT,RIGHT].iter().all(|&w|score(scene,&c.candidate_rgb,w).rgb<=0.95*score(scene,&c.baseline_rgb,w).rgb);
        }
        let false_gain=max_gain_error(&c.fit,&[1.0;N]);
        let pure_defocus_safe=if scene==Scene::BroadDefocus&&drift==Drift::None{available(&c.fit)&&false_gain<=0.002}else{true};
        let pass=preservation&&improvement&&pure_defocus_safe;quality_pass&=pass;
        cases.push(json!({"scene":scene.name(),"drift":drift.name(),"noise":noisy,"fit":c.fit,"applied_gains":c.applied_gains,
            "scores":rows,"preservation_pass":preservation,"required_uniform_improvement":improvement,
            "pure_defocus_safe":pure_defocus_safe,"quality_pass":pass,"frames":c.frames,
            "spatial_scope":if drift==Drift::LeftOnly{Some("Only left half illumination varies; right true detail is unchanged. The estimator has no nonuniformity guard.")}else{None}}));
    }
    output("screen.json",&json!({"schema":1,"mechanical_pass":true,"quality_pass":quality_pass,"positive_exercised":positive_exercised,
        "brightness_destroyer_exercised":brightness_destroyer_exercised,"photographic_replay_admitted":false,"cases":cases,
        "quality_scope":"Known generated truth,5% RMSE non-regression,98% bounded detail retention,5% uniform-drift benefit; no physical calibration or automatic photograph admission."}));
    println!("NATIVE_PHOTOMETRIC_SCREEN quality_pass={quality_pass} positive_exercised={positive_exercised}");
}
