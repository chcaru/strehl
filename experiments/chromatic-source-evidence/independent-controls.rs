include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/chromatic-source-evidence/independent-fixtures.rs"));
use super::{compare_generated,compare_generated_forced,Comparison,Mode,project_co_sited,
    projected_bands,PairedNoiseEnergy,AdmissionUnion,ColourBands,core};
use strehl_core::pyramid::LevelSize;
const VEIL_CORE:Window=Window{name:"unclipped-focused-highlight-core",x0:112,y0:110,x1:133,y1:132};
fn sizes()->Vec<LevelSize>{vec![LevelSize{width:17,height:13},LevelSize{width:9,height:7},LevelSize{width:5,height:4}]}
fn neutral_packed(n:usize)->Vec<Vec<f32>>{
    let mut p=vec![vec![0.0;n];12];
    // Independently enumerate the four co-sited triples, not the operator table.
    for (site,[r,g,b]) in [[0,4,5],[6,1,7],[8,2,9],[10,11,3]].into_iter().enumerate(){
        for j in 0..n{let light=64.0*(site+1)as f32+4.0*(j%11)as f32;p[r][j]=light/2.0;p[g][j]=light;p[b][j]=light/4.0;}}
    p
}
#[test]
fn independent_projection_controls(){
    let wb=[2.0,1.0,4.0,f32::NAN];let p=neutral_packed(17*13);let q=project_co_sited(&p,wb).unwrap();
    assert!(q.iter().flatten().all(|v|*v==0.0));assert!((p[0][0]*2.0-p[1][0]).abs()>10.0,"wrong-site null is inert");
    let mut changed=p.clone();for j in 0..p[0].len(){changed[8][j]+=8.0;changed[5][j]+=4.0;}
    let colour=project_co_sited(&changed,wb).unwrap();assert!(colour.iter().flatten().all(|v|*v==4.0));
    for [r,g,b] in [[0,4,5],[6,1,7],[8,2,9],[10,11,3]]{for j in 0..p[0].len(){changed[r][j]+=16.0;changed[g][j]+=32.0;changed[b][j]+=8.0;}}
    assert!(exact(&project_co_sited(&changed,wb).unwrap(),&colour));
    let mut wrong=p.clone();wrong[1].fill(999.0);assert!(project_co_sited(&wrong,wb).unwrap().iter().flatten().any(|v|*v!=0.0));
    assert!(project_co_sited(&p,[0.0,1.0,4.0,0.0]).is_err());
}
#[test]
fn independent_paired_floor_controls(){
    let s=sizes();let wb=[2.0,1.0,4.0,f32::NAN];let a=neutral_packed(s[0].pixels());let mut b=a.clone();
    for [r,g,blue] in [[0,4,5],[6,1,7],[8,2,9],[10,11,3]]{for j in 0..a[0].len(){let d=4.0*(1+(j*7)%13)as f32;b[r][j]+=d/2.0;b[g][j]+=d;b[blue][j]+=d/4.0;}}
    let pa=projected_bands(&a,wb,&s).unwrap();let pb=projected_bands(&b,wb,&s).unwrap();
    let mut common=PairedNoiseEnergy::new(&s).unwrap();for _ in 0..8{common.add_pair(&pa,&pb).unwrap();}
    assert!(common.finish().unwrap().iter().flatten().all(|v|*v==0.0));
    assert!(a[0].iter().zip(&b[0]).any(|(x,y)|(x-y).abs()>1.0),"marginal-variance destroyer is inert");
    let coefficients=|v:f32|->ColourBands{std::array::from_fn(|_|s[..s.len()-1].iter().map(|z|vec![v;z.pixels()]).collect())};
    let mut pairs=PairedNoiseEnergy::new(&s).unwrap();for _ in 0..8{pairs.add_pair(&coefficients(2.0),&coefficients(-2.0)).unwrap();}
    assert!(pairs.add_pair(&coefficients(2.0),&coefficients(-2.0)).is_err());
    assert!(pairs.finish().unwrap().iter().flatten().all(|v|*v==16.0));
    assert!(PairedNoiseEnergy::new(&s).unwrap().finish().is_err());
}
fn field(w:Vec<Vec<f32>>)->core::Fields{core::Fields{energy:w.clone(),floor:w.clone(),weights:w}}
#[test]
fn independent_union_controls(){
    let s=sizes();let canonical=s[..s.len()-1].iter().map(|z|vec![3.0;z.pixels()]).collect::<Vec<_>>();
    let mut first=s[..s.len()-1].iter().map(|z|vec![0.0;z.pixels()]).collect::<Vec<_>>();let mut second=first.clone();
    first[0].fill(7.0);first[1][2]=5.0;second[1][3]=9.0;
    let mut union=AdmissionUnion::new(&s,2).unwrap();union.add(&first).unwrap();assert!(union.complete().is_err());union.add(&second).unwrap();
    for (own,other) in [(&first,&second),(&second,&first)]{
        let mut result=field(canonical.clone());let change=union.apply(&mut result,&field(own.clone()),Mode::Chromatic).unwrap();
        assert!(exact(&result.energy,&canonical)&&exact(&result.floor,&canonical));assert_eq!(result.weights[0],canonical[0]);
        for j in 0..s[1].pixels(){assert_eq!(result.weights[1][j],if own[1][j]>0.0||other[1][j]>0.0{own[1][j]}else{3.0});}
        assert_eq!(change.chromatic_sites[1],2);assert_eq!(change.changed[0],0);
        for mode in [Mode::Off,Mode::NoChroma]{let mut off=field(canonical.clone());union.apply(&mut off,&field(own.clone()),mode).unwrap();assert!(exact(&off.weights,&canonical));}
    }
    let zero=s[..s.len()-1].iter().map(|z|vec![0.0;z.pixels()]).collect::<Vec<_>>();let mut empty=AdmissionUnion::new(&s,1).unwrap();empty.add(&zero).unwrap();
    let mut result=field(canonical.clone());empty.apply(&mut result,&field(zero),Mode::Chromatic).unwrap();assert!(exact(&result.weights,&canonical));
}
fn changed(c:&Comparison)->usize{c.frames.iter().map(|f|f.changes.changed.iter().skip(1).sum::<usize>()).sum()}
fn checks(c:&Comparison,frames:&[Frame],before:&[String]){
    assert_eq!((c.native_width,c.native_height),(290,250));assert!(c.held_state_bit_exact);
    assert_eq!(c.level_sizes,vec![[145,125],[73,63],[37,32],[19,16],[10,8]]);
    let mut seeds=std::collections::BTreeSet::new();
    for ((frame,h),ev) in frames.iter().zip(before).zip(&c.frames){assert_eq!(&hash(&frame.data),h);assert_eq!(&ev.source_sha256,h);
        assert!(ev.source_unchanged&&ev.replay_exact);assert_eq!(ev.verified_probe_draws,16);assert_eq!(ev.projected_draw_sha256.len(),16);
        assert_eq!(ev.canonical_weight_sha256[0],ev.candidate_weight_sha256[0]);assert_eq!(ev.changes.changed[0],0);
        for seed in ev.probe_seeds{assert!(seeds.insert(seed));}}
}
fn ratio(a:f64,b:f64)->f64{if b>0.0{a/b}else if a==0.0{1.0}else{f64::MAX}}
fn keep(b:&Score,a:&Score)->bool{(0..3).all(|j|b.recovery[j]<0.5||a.recovery[j].clamp(0.0,1.0)>=0.98*b.recovery[j].clamp(0.0,1.0))}
fn safe(b:&Score,a:&Score)->bool{a.rgb<=1.05*b.rgb&&a.chroma<=1.05*b.chroma&&a.green<=1.05*b.green&&keep(b,a)}
fn signed_bias(scene:Scene,rgb:&[f32],w:Window)->f64{
    let mut sum=0.0;for y in w.y0..w.y1{for x in w.x0..w.x1{let p=((y-2*crop().y)*2*crop().width+x-2*crop().x)*3;
        for c in 0..3{sum+=f64::from(rgb[p+c])-radiance(scene,c,x as f64,y as f64,None);}}}sum/(3*(w.x1-w.x0)*(w.y1-w.y0))as f64
}
#[test]
fn independent_quality_screen(){
    let out=PathBuf::from(std::env::var_os("STREHL_CHROMATIC_SOURCE_EVIDENCE_OUT").expect("root output required"));std::fs::create_dir(&out).unwrap();
    let metric=commission();
    let truth=truth_image(Scene::Radial);let good=score(Scene::Radial,&truth,RADIAL);let mut erased=truth.clone();
    for pixel in erased.chunks_exact_mut(3){for c in 0..3{let base=[0.24,0.26,0.22][c];pixel[c]=base+0.5*(pixel[c]-base);}}
    assert!(!keep(&good,&score(Scene::Radial,&erased,RADIAL)),"actual retention gate failed its half-detail destroyer");
    let ts=transforms();let mut cases=Vec::new();let(mut quality,mut exercised,mut wrong_live)=(true,true,false);
    for iso in [100.0f32,400.0]{let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());assert!(noise.is_trustworthy()&&noise.prnu().is_none());
        let scenes:&[Scene]=if iso==100.0{&[Scene::Flat,Scene::Veil,Scene::Neutral,Scene::ThinDepth,Scene::Radial,Scene::NeutralClipped]}else{&[Scene::Flat,Scene::Veil]};
        let mut flat=0.0;
        for &scene in scenes{let frames=ts.iter().enumerate().map(|(k,&t)|fixture(scene,k,t,iso,&noise)).collect::<Vec<_>>();let before=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
            let c=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default(),Mode::Chromatic).unwrap();checks(&c,&frames,&before);
            let regions:&[Window]=match scene{Scene::ThinDepth=>&[THIN_FAR,THIN_NEAR,JUNCTION],Scene::Radial=>&[RADIAL],Scene::Veil=>&[OUTSIDE,NEAR,VEIL_CORE],Scene::NeutralClipped=>&[OUTSIDE,NEAR],_=>&[INTERIOR]};
            let mut windows=Vec::new();let mut pass=true;let mut positive_exercised=true;
            for &window in regions{let b=score(scene,&c.baseline_rgb,window);let a=score(scene,&c.candidate_rgb,window);let mut bar=safe(&b,&a);
                if scene==Scene::Flat{flat=b.rgb;}
                let bias=signed_bias(scene,&c.baseline_rgb,window);
                if scene==Scene::Veil&&window.name==OUTSIDE.name{positive_exercised=b.rgb>2.0*flat&&bias>flat&&changed(&c)>0;
                    bar&=a.rgb<=0.95*b.rgb&&a.chroma<=0.95*b.chroma;}
                if matches!(scene,Scene::ThinDepth|Scene::Radial|Scene::Neutral)||window.name==NEAR.name||window.name==VEIL_CORE.name{bar&=b.recovery.iter().all(|v|*v>=0.5);}
                pass&=bar;windows.push(json!({"name":window.name,"native_xyxy":[window.x0,window.y0,window.x1,window.y1],"baseline":score_json(&b),"candidate":score_json(&a),
                    "rgb_ratio":ratio(a.rgb,b.rgb),"chroma_ratio":ratio(a.chroma,b.chroma),"green_ratio":ratio(a.green,b.green),"baseline_signed_rgb_bias":bias,"pass":bar}));}
            let mut clipped=[0usize;4];for frame in &frames{for y in 0..H{for x in 0..W{if frame.active_row(y)[x]==levels().white as u16{clipped[(y%2)*2+x%2]+=1;}}}}
            if scene==Scene::NeutralClipped{assert!(clipped.iter().sum::<usize>()>0&&clipped.iter().min()!=clipped.iter().max(),"unequal original-channel clipping not exercised");}
            else{assert_eq!(clipped.iter().sum::<usize>(),0);}
            let mut placebo=Value::Null;
            if scene==Scene::Veil&&iso==100.0{
                for mode in [Mode::Off,Mode::NoChroma]{let p=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default(),mode).unwrap();checks(&p,&frames,&before);
                    assert!(exact(&p.baseline_planes4,&p.candidate_planes4)&&exact(&p.baseline_planes4,&c.baseline_planes4)&&exact_slice(&p.baseline_rgb,&p.candidate_rgb));}
                let wrong=compare_generated_forced(&frames,&ts,crop(),&noise,MergeConfig::default(),Mode::Chromatic,0).unwrap();checks(&wrong,&frames,&before);
                let b=score(scene,&c.baseline_rgb,NEAR);let w=score(scene,&wrong.candidate_rgb,NEAR);
                wrong_live=changed(&wrong)>0&&!exact(&wrong.baseline_planes4,&wrong.candidate_planes4)&&(!safe(&b,&w)||!keep(&b,&w));
                placebo=json!({"off_exact":true,"no_chroma_exact":true,"forced_source":0,"wrong_source_exercised":wrong_live,"wrong_adjacent_texture":score_json(&w)});
            }
            if scene==Scene::Veil{exercised&=positive_exercised;}quality&=pass;
            cases.push(json!({"scene":scene.name(),"iso":iso,"quality_pass":pass,"positive_exercised":positive_exercised,"windows":windows,"clipped_original_sites_by_phase":clipped,
                "changed_coarse_weights":changed(&c),"chromatic_union_sites":c.admission.supported.iter().map(|v|v.iter().filter(|v|**v).count()).collect::<Vec<_>>(),
                "true_neutral_scene":matches!(scene,Scene::Neutral|Scene::NeutralClipped),"held_state_exact":c.held_state_bit_exact,"placebo":placebo,"sources":c.frames}));
        }
    }
    assert_eq!(cases.len(),8);let qualified=quality&&exercised&&wrong_live;
    write(&out.join("screen.json"),&json!({"status":"SCREEN_COMPLETE","mechanical_pass":true,"quality_pass":quality,"positive_exercised":exercised,
        "wrong_source_destroyer_exercised":wrong_live,"candidate_qualified":qualified,"photographic_replay_admitted":false,"metric_commission":metric,"cases":cases,
        "scope":"Generated operator screen only; original injected noise is shared and not calibrated here. Clipped null failure is not evidence actual minerals clip."}));
    eprintln!("CHROMATIC_SOURCE_EVIDENCE {}",json!({"candidate_qualified":qualified,"photographic_replay_admitted":false}));
}
