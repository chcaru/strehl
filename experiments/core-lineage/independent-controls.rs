// Independent actual-consumer image-truth screen. Root alone builds/runs.
include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/core-lineage/independent-fixtures.rs"));

fn checks(c:&Comparison,frames:&[Frame],before:&[String]) {
    assert_eq!((c.native_width,c.native_height),(2*crop().width,2*crop().height));
    assert_eq!(c.level_sizes,vec![[145,125],[73,63],[37,32],[19,16],[10,8]]);
    assert_eq!(c.alpha.len(),crop().width*crop().height);
    assert_eq!(c.pixel_major_q.len(),c.alpha.len()*frames.len());
    assert!(c.alpha.iter().all(|v|v.is_finite() && (0.0..=1.0).contains(v)));
    assert!(c.baseline_rgb.iter().chain(&c.candidate_rgb).all(|v|v.is_finite()));
    for p in 0..c.alpha.len(){let q=&c.pixel_major_q[p*frames.len()..(p+1)*frames.len()];
        assert!(q.iter().all(|v|v.is_finite() && *v>=0.0));
        assert!((q.iter().sum::<f32>()-c.alpha[p]).abs()<=8e-6);
        if c.alpha[p]==0.0 {for ch in 0..4 {
            assert_eq!(c.candidate_planes4[ch][p].to_bits(),c.baseline_planes4[ch][p].to_bits());
        }}
    }
    assert_eq!(c.frames.len(),frames.len());
    for ((frame,old),e) in frames.iter().zip(before).zip(&c.frames){
        assert_eq!(&hash(&frame.data),old);assert_eq!(&e.source_sha256,old);
        assert!(e.source_unchanged && e.replay_known4_exact);
        assert!(!e.beta.is_empty() && e.beta.iter().all(|v|v.is_finite() && *v>0.0));
    }
}
fn evidence(c:&Comparison)->Value {
    json!({"alpha_positive":c.alpha.iter().filter(|v|**v>0.0).count(),
        "alpha_zero":c.alpha.iter().filter(|v|**v==0.0).count(),"level_sizes":c.level_sizes,
        "baseline_averaged_fraction":c.baseline_averaged_fraction,"lineage":c.membership_evidence,
        "frames":c.frames.iter().map(|f|json!({"source":f.source_sha256,
            "guide":f.guide_sha256,"variance":f.variance_sha256,"beta":f.beta})).collect::<Vec<_>>()})
}
fn alpha_count(c:&Comparison,window:Window)->usize {
    let mut count=0;
    for y in window.y0/2..(window.y1+1)/2 {for x in window.x0/2..(window.x1+1)/2 {
        let p=(y-crop().y)*crop().width+x-crop().x;
        count+=usize::from(c.alpha[p]>0.0);
    }}count
}
fn candidate_equal_baseline(c:&Comparison)->bool {
    exact(&c.baseline_planes4,&c.candidate_planes4) && c.baseline_rgb.iter()
        .zip(&c.candidate_rgb).all(|(a,b)|a.to_bits()==b.to_bits())
}
fn fixed_core_mean_control()->Value {
    // A 2:1 checkerboard split must not silently become a half:half mean.
    let make=|reverse:bool| {
        let mut tracker=super::Tracker::new(5,5,3);
        for frame in 0..3 {let original=if reverse{2-frame}else{frame};
            let mut weights=vec![0.0;25];let (even,odd)=[(4.0,8.0),(2.0,4.0),(1.0,1.0)][original];
            weights[6]=even;weights[8]=even;weights[7]=odd;
            tracker.push(frame,super::Analysis{branches:vec![super::Branch{
                cells:vec![6,7,8],core:vec![6,7,8],peak:10.0,saddle:5.0,
                clipped:false,source_edge:false,alias:false}],field_hash:"fixed-independent-three-cell".into(),
                clipped_stencil_cells:0},&weights).unwrap();
        }tracker.finish().unwrap()
    };
    let actual=make(false);let reverse=make(true);
    for p in 0..25 {assert_eq!(actual.alpha[p].to_bits(),reverse.alpha[p].to_bits());
        if ![6,7,8].contains(&p){assert_eq!(actual.alpha[p],0.0);}
        for k in 0..3 {assert!((actual.pixel_major_q[3*p+k]-reverse.pixel_major_q[3*p+2-k]).abs()<2e-6);}
    }
    assert_eq!(actual.alpha[7],3.0/9.0);
    let expected=[16.0f32/27.0,8.0/27.0,3.0/27.0];
    let got=(0..3).map(|k|actual.pixel_major_q[3*7+k]/actual.alpha[7]).collect::<Vec<_>>();
    assert!(got.iter().zip(expected).all(|(a,b)|(*a-b).abs()<2e-6));
    assert!((got[2]-0.1).abs()>0.005,"Equal weighting of unequal core subsets escaped");
    json!({"scope":"Arithmetic contract only","subset_sizes":[2,1],"expected_weights":expected,
        "actual_weights":got,"fixed_input_reversal":true,"no_support_expansion":true})
}

#[test]
fn independent_core_lineage_actual_truth_screen() {
    let out=PathBuf::from(std::env::var_os("STREHL_CORE_LINEAGE_OUT").expect("root-owned unique output required"));
    std::fs::create_dir(&out).unwrap();let commissioned=commission();let mean_control=fixed_core_mean_control();
    let iso=100.0;let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());
    assert!(noise.is_trustworthy() && noise.prnu().is_none());
    let ts=transforms();let cfg=MergeConfig::default();let mut records=Vec::new();
    let mut admission=true;let mut flat_error=0.0;let mut glint_exercised=false;
    let mut wrong_exercised=false;let mut reversal_pass=false;
    // Flat first. True radial detail and crossed depths precede any admission.
    for scene in [Scene::Flat,Scene::GlintDepth,Scene::NoGlintDepth,Scene::TrueRadial,Scene::ThinDepth] {
        let frames=ts.iter().enumerate().map(|(k,t)|fixture(scene,k,*t,iso,&noise)).collect::<Vec<_>>();
        let before=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
        let c=compare_generated(&frames,&ts,crop(),&noise,cfg,Mode::CoreLineage).unwrap();
        checks(&c,&frames,&before);
        let windows:&[Window]=match scene{Scene::Flat=>&[FLAT],
            Scene::GlintDepth|Scene::NoGlintDepth=>&[FAN,CORE,EDGE,NEAR],
            Scene::TrueRadial=>&[RADIAL],Scene::ThinDepth=>&[THIN_FAR,THIN_NEAR,JUNCTION],_=>unreachable!()};
        let mut pass=true;let mut scores=Vec::new();
        for &window in windows {
            let b=score(scene,&c.baseline_rgb,window);let a=score(scene,&c.candidate_rgb,window);
            let mut gate=if scene==Scene::Flat {flat_error=b.rgb;
                a.rgb<=1.25*b.rgb && a.chroma<=1.25*b.chroma}
                else {a.rgb<=1.10*b.rgb && recovery_pass(&b,&a)};
            if scene==Scene::GlintDepth && window.name=="fan" {
                gate&=a.rgb<=0.95*b.rgb;
                glint_exercised=b.rgb>2.0*flat_error && alpha_count(&c,FAN)>=4
                    && !exact(&c.baseline_planes4,&c.candidate_planes4);
            }
            if scene==Scene::TrueRadial {gate&=a.chroma<=1.10*b.chroma;}
            if matches!(window.name,"nearer-real-texture"|"real-coloured-rays"|"thin-far"|"thin-near") {
                gate&=b.recovery.iter().all(|v|*v>=0.5);
            }
            pass&=gate;scores.push(json!({"name":window.name,"native_bounds":[window.x0,window.y0,window.x1,window.y1],
                "baseline":score_json(&b),"candidate":score_json(&a),"rgb_ratio":a.rgb/b.rgb,
                "chroma_ratio":a.chroma/b.chroma,"active_quads":alpha_count(&c,window),"pass":gate}));
        }
        let mut controls=Value::Null;
        if scene==Scene::GlintDepth {
            let off=compare_generated(&frames,&ts,crop(),&noise,cfg,Mode::Off).unwrap();
            checks(&off,&frames,&before);assert!(candidate_equal_baseline(&off));
            assert!(exact(&off.baseline_planes4,&c.baseline_planes4));
            let wrong=compare_generated_forced(&frames,&ts,crop(),&noise,cfg,Mode::CoreLineage,4).unwrap();
            checks(&wrong,&frames,&before);assert!(exact(&wrong.baseline_planes4,&c.baseline_planes4));
            let wf=score(scene,&wrong.candidate_rgb,FAN);let wc=score(scene,&wrong.candidate_rgb,CORE);
            let bf=score(scene,&c.baseline_rgb,FAN);let bc=score(scene,&c.baseline_rgb,CORE);
            wrong_exercised=wf.rgb>1.10*bf.rgb || !recovery_pass(&bc,&wc);
            let reverse_frames=frames.iter().rev().cloned().collect::<Vec<_>>();
            let reverse_ts=ts.iter().rev().copied().collect::<Vec<_>>();
            let reverse_before=before.iter().rev().cloned().collect::<Vec<_>>();
            let reverse=compare_generated(&reverse_frames,&reverse_ts,crop(),&noise,cfg,Mode::CoreLineage).unwrap();
            checks(&reverse,&reverse_frames,&reverse_before);
            let mut qerror=0.0f32;for p in 0..c.alpha.len(){for k in 0..N {
                qerror=qerror.max((c.pixel_major_q[p*N+k]-reverse.pixel_major_q[p*N+N-1-k]).abs());
            }}
            let alpha_error=worst(&c.alpha,&reverse.alpha);
            let rgb_error=worst(&c.candidate_rgb,&reverse.candidate_rgb);
            let baseline_rgb_error=worst(&c.baseline_rgb,&reverse.baseline_rgb);
            let stage_inputs=c.frames.iter().enumerate().map(|(k,f)|{
                let r=&reverse.frames[N-1-k];
                let beta_exact=f.beta.len()==r.beta.len() && f.beta.iter().zip(&r.beta)
                    .all(|(a,b)|a.to_bits()==b.to_bits());
                json!({"original_source":k,"source_exact":f.source_sha256==r.source_sha256,
                    "known4_exact":f.known4_sha256==r.known4_sha256,"guide_exact":f.guide_sha256==r.guide_sha256,
                    "variance_exact":f.variance_sha256==r.variance_sha256,
                    "energy_exact":f.energy_sha256==r.energy_sha256,"floor_exact":f.floor_sha256==r.floor_sha256,
                    "beta_bits_exact":beta_exact,"forward_beta_bits":f.beta.iter().map(|v|v.to_bits()).collect::<Vec<_>>(),
                    "reverse_beta_bits":r.beta.iter().map(|v|v.to_bits()).collect::<Vec<_>>()})
            }).collect::<Vec<_>>();
            let stage_inputs_exact=stage_inputs.iter().all(|v|["source_exact","known4_exact","guide_exact",
                "variance_exact","energy_exact","floor_exact","beta_bits_exact"].iter().all(|key|v[*key]==true));
            reversal_pass=stage_inputs_exact && qerror<=2e-5 && alpha_error==0.0 && rgb_error<=2e-6;
            controls=json!({"off_exact":true,"forced_wrong_source":4,"wrong_fan":score_json(&wf),
                "wrong_core":score_json(&wc),"wrong_destroyer_exercised":wrong_exercised,
                "reversal":{"q_max_abs":qerror,"alpha_max_abs":alpha_error,"rgb_max_abs":rgb_error,
                    "baseline_rgb_max_abs":baseline_rgb_error,"stage_inputs_exact":stage_inputs_exact,
                    "stage_inputs":stage_inputs,"lineage_ordering_test_valid":stage_inputs_exact,"pass":reversal_pass,
                    "interpretation":"Changed original-source stage evidence invalidates lineage-only attribution; tolerances unchanged."}});
        }
        admission&=pass;
        records.push(json!({"scene":scene.name(),"iso":iso,"pass":pass,"windows":scores,
            "consumer":evidence(&c),"controls":controls}));
    }

    // Same latent world in every frame: no temporal focus advantage exists.
    // Independent source noise remains, so a coherent-looking wrong selector
    // can damage RGB truth even while its component tree looks clean.
    let frames=ts.iter().enumerate().map(|(k,t)|fixture_world(Scene::GlintDepth,k,*t,iso,&noise,true,true)).collect::<Vec<_>>();
    let before=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
    let c=compare_generated(&frames,&ts,crop(),&noise,cfg,Mode::CoreLineage).unwrap();checks(&c,&frames,&before);
    let mut pass=true;let mut scores=Vec::new();
    for window in [FAN,CORE,EDGE,NEAR]{let b=score(Scene::GlintDepth,&c.baseline_rgb,window);
        let a=score(Scene::GlintDepth,&c.candidate_rgb,window);
        let gate=a.rgb<=1.10*b.rgb && a.chroma<=1.10*b.chroma && recovery_pass(&b,&a);
        pass&=gate;scores.push(json!({"name":window.name,"baseline":score_json(&b),"candidate":score_json(&a),"pass":gate}));}
    admission&=pass;records.push(json!({"scene":"same-focused-world-independent-noise","pass":pass,
        "windows":scores,"consumer":evidence(&c)}));

    // Noiseless constant/colour-only and explicit original-site pathologies.
    let identity=Similarity{a:Cx::new(1.0,0.0),b:Cx::new(0.0,0.0)};
    for name in ["constant-flat","constant-green-colour","persistent-hot","clipped-core"] {
        let scene=if name=="constant-green-colour"{Scene::ColourOnly}else{Scene::Flat};
        let mut frames=(0..N).map(|k|fixture_noise(scene,k,identity,iso,&noise,false)).collect::<Vec<_>>();
        for frame in &mut frames {
            if name=="persistent-hot" {let i=(frame.active.y+120)*frame.stride+frame.active.x+122;
                frame.data[i]=14000;}
            if name=="clipped-core" {for y in 116..=124{for x in 118..=126{
                if (x as i32-122).pow(2)+(y as i32-120).pow(2)<=16 {
                    frame.data[(frame.active.y+y)*frame.stride+frame.active.x+x]=15360;
                }
            }}}
        }
        let before=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
        let c=compare_generated(&frames,&vec![identity;N],crop(),&noise,cfg,Mode::CoreLineage).unwrap();
        checks(&c,&frames,&before);
        let pass=c.alpha.iter().all(|v|*v==0.0) && candidate_equal_baseline(&c);
        admission&=pass;records.push(json!({"scene":name,"pass":pass,"literal_zero_and_exact_fallback":pass,
            "consumer":evidence(&c)}));
    }
    admission&=glint_exercised && wrong_exercised && reversal_pass;
    let result=json!({"status":"SCREEN_COMPLETE","photographic_replay_admitted":admission,
        "glint_exercised":glint_exercised,"wrong_source_destroyer_exercised":wrong_exercised,
        "reversal_pass":reversal_pass,"metric_commission":commissioned,"core_mean_control":mean_control,"cases":records,
        "scope":"Fixed automatic lineage with actual whole-AC reconstruction. ISO100 generated truth only; no camera calibration or SOTA claim."});
    write(&out.join("screen.json"),&result);
    eprintln!("CORE_LINEAGE_DECISION {}",json!({"photographic_replay_admitted":admission}));
}
