// Reviewer-owned controls. No RAW files or external implementation are read.
include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/consistent-reconstruction/independent-fixtures.rs"));
use super::{compare_generated,Comparison,Mode,operator};
use strehl_core::pyramid::{Pyramid,Workspace,level_sizes};

const ERROR_DN:f64=0.02;
fn exact(a:&[Vec<f32>],b:&[Vec<f32>])->bool {a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|a.len()==b.len()&&a.iter().zip(b).all(|(x,y)|x.to_bits()==y.to_bits()))}
fn flat_bands(b:&[Vec<f32>])->Vec<f64>{b.iter().flatten().map(|x|f64::from(*x)).collect()}
fn max_error(a:&[f32],b:&[f64])->f64{assert_eq!(a.len(),b.len());a.iter().zip(b).map(|(a,b)|(f64::from(*a)-b).abs()).fold(0.0,f64::max)}
fn oracle_ok(a:&[f32],b:&[f64])->bool{assert_eq!(a.len(),b.len());let rms=(a.iter().zip(b).map(|(a,b)|(f64::from(*a)-b).powi(2)).sum::<f64>()/a.len()as f64).sqrt();
    rms<=ERROR_DN&&max_error(a,b)<=(a.len()as f64).sqrt()*ERROR_DN}
fn direct_analysis(s:&[LevelSize],x:&[f32])->Vec<Vec<f32>>{let mut p=Pyramid::zeros(s);p.build(x,&mut Workspace::new(s));(0..p.levels()).map(|k|p.level(k).to_vec()).collect()}
fn direct_collapse(s:&[LevelSize],c:&[Vec<f32>])->Vec<f32>{let mut p=Pyramid::zeros(s);for(k,v)in c.iter().enumerate(){p.level_mut(k).copy_from_slice(v);}p.collapse(&mut Workspace::new(s))}
fn unflatten(s:&[LevelSize],b:&[f64])->Vec<Vec<f32>>{let mut i=0;let result=s.iter().map(|z|{let v=b[i..i+z.pixels()].iter().map(|x|*x as f32).collect();i+=z.pixels();v}).collect();assert_eq!(i,b.len());result}
fn admissible_fields(converged:bool,refused:bool,steps:usize,error:f64,finite:bool)->bool{converged&&!refused&&steps<=32&&error.is_finite()&&error>=0.0&&error<=ERROR_DN&&finite}
fn admitted(s:&operator::Solve)->bool{admissible_fields(s.converged,s.refusal.is_some(),s.iterations,s.error_bound_rms,s.image.iter().all(|v|v.is_finite()))}
fn solver_json(s:&operator::Solve)->Value{json!({"iterations":s.iterations,"converged":s.converged,"relative_residual":s.relative_residual,"error_bound_rms_dn":s.error_bound_rms,"correction_rhs_norm":s.correction_rhs_norm,"correction_residual_norm":s.correction_residual_norm,"correction_objective":s.correction_objective,"final_addition_rounding_rms_dn":s.final_rounding_bound,"initial_objective":s.initial_objective,"objective":s.objective,"refusal":s.refusal,"independently_admissible":admitted(s)})}
fn write(path:&Path,value:&Value){serde_json::to_writer_pretty(std::fs::OpenOptions::new().write(true).create_new(true).open(path).unwrap(),value).unwrap();}

// Columns come from the actual analysis applied to coordinate basis vectors.
// Neither the candidate adjoint nor its normal operator appears in this oracle.
struct Dense{columns:Vec<Vec<f64>>,lower:Vec<Vec<f64>>}
impl Dense{
    fn new(s:&[LevelSize])->Self{let n=s[0].pixels();let mut columns=Vec::with_capacity(n);
        for j in 0..n{let mut e=vec![0.0;n];e[j]=1.0;columns.push(flat_bands(&direct_analysis(s,&e)));}
        let mut lower=vec![vec![0.0;n];n];
        for i in 0..n{for j in 0..=i{let mut v=columns[i].iter().zip(&columns[j]).map(|(a,b)|a*b).sum::<f64>();
            for k in 0..j{v-=lower[i][k]*lower[j][k];}
            if i==j{assert!(v>1e-12,"analysis lost full column rank");lower[i][j]=v.sqrt();}else{lower[i][j]=v/lower[j][j];}}}
        Self{columns,lower}}
    fn adjoint(&self,b:&[f64])->Vec<f64>{self.columns.iter().map(|a|{assert_eq!(a.len(),b.len());a.iter().zip(b).map(|(x,y)|x*y).sum()}).collect()}
    fn solve(&self,b:&[f64])->Vec<f64>{let mut x=self.adjoint(b);let n=x.len();
        for i in 0..n{for j in 0..i{x[i]-=self.lower[i][j]*x[j];}x[i]/=self.lower[i][i];}
        for i in (0..n).rev(){for j in i+1..n{x[i]-=self.lower[j][i]*x[j];}x[i]/=self.lower[i][i];}x}
}
fn adjoint_ok(actual:&[f32],truth:&[f64])->bool{max_error(actual,truth)<=2e-5}

#[test]
fn independent_adjoint_dense_controls(){
    for (w,h) in [(17,19),(18,20)]{let s=level_sizes(w,h,1);let d=Dense::new(&s);let m=s.iter().map(|z|z.pixels()).sum::<usize>();
        let values=(0..m).map(|j|((j*37+11)%101)as f64/50.0-1.0).collect::<Vec<_>>();let b=unflatten(&s,&values);let b64=flat_bands(&b);
        let expected=d.adjoint(&b64);let got=operator::adjoint(&s,&b);assert!(adjoint_ok(&got,&expected));
        let doubled=got.iter().map(|v|2.0*v).collect::<Vec<_>>();assert!(!adjoint_ok(&doubled,&expected),"doubled adjoint was not rejected");
        let mut erased=got.clone();for y in 0..h{erased[y*w+w-1]=0.0;}assert!(!adjoint_ok(&erased,&expected),"last-column boundary error not exercised");
        // A coefficient impulse at every corner of both levels catches clamp
        // multiplicity and asymmetric odd/even terminal phases.
        let mut offset=0;for z in &s{for j in [0,z.width-1,(z.height-1)*z.width,z.pixels()-1]{let mut impulse=vec![0.0;m];impulse[offset+j]=1.0;
            assert!(adjoint_ok(&operator::adjoint(&s,&unflatten(&s,&impulse)),&d.adjoint(&impulse)));}offset+=z.pixels();}
        // Independently enumerate synthesis columns for its separately needed
        // transpose; a correct analysis adjoint does not commission this one.
        let x=(0..w*h).map(|j|((j*13)%31)as f32/16.0-0.8).collect::<Vec<_>>();let st=flat_bands(&operator::synthesis_adjoint(&s,&x));
        for j in 0..m{let mut e=vec![0.0;m];e[j]=1.0;let col=direct_collapse(&s,&unflatten(&s,&e));let expected=col.iter().zip(&x).map(|(a,b)|f64::from(*a)*f64::from(*b)).sum::<f64>();assert!((st[j]-expected).abs()<2e-5);}
    }
    // Multilevel dot-product control includes internal odd sizes as well as
    // the single-level dense oracle. Deterministic signed data avoids a DC-only test.
    let s=level_sizes(35,37,7);assert_eq!(s.len(),3);let x=(0..s[0].pixels()).map(|j|((j*7)%97)as f32/48.0-1.0).collect::<Vec<_>>();
    let b=s.iter().enumerate().map(|(k,z)|(0..z.pixels()).map(|j|((j*19+k*11)%71)as f32/35.0-1.0).collect()).collect::<Vec<Vec<f32>>>();
    let a=direct_analysis(&s,&x);assert!(exact(&a,&operator::analysis(&s,&x)));
    let lhs=a.iter().flatten().zip(b.iter().flatten()).map(|(a,b)|f64::from(*a)*f64::from(*b)).sum::<f64>();
    let rhs=x.iter().zip(operator::adjoint(&s,&b)).map(|(a,b)|f64::from(*a)*f64::from(b)).sum::<f64>();assert!((lhs-rhs).abs()<2e-4);
}

#[test]
fn independent_solver_controls(){
    for (w,h) in [(17,19),(18,20)]{let s=level_sizes(w,h,1);let d=Dense::new(&s);
        for dc in [0.0f32,8192.0]{let truth=(0..w*h).map(|j|dc+if j%w>w/2{384.0}else{0.0}+((j*17)%13)as f32).collect::<Vec<_>>();
            let realizable=direct_analysis(&s,&truth);let initial=direct_collapse(&s,&realizable);let solved=operator::reconstruct(&s,&realizable,&initial).unwrap();
            assert!(admitted(&solved),"realizable finite case refused: {:?}",solved.refusal);assert!(oracle_ok(&solved.image,&truth.iter().map(|v|f64::from(*v)).collect::<Vec<_>>()));
            let mut mixed=realizable.clone();mixed[1][0]+=73.0;mixed[1][s[1].pixels()-1]-=51.0;mixed[0][w+1]+=29.0;
            let initial=direct_collapse(&s,&mixed);let oracle=d.solve(&flat_bands(&mixed));let solved=operator::reconstruct(&s,&mixed,&initial).unwrap();
            assert!(admitted(&solved),"inconsistent dense case refused: {:?}",solved.refusal);assert!(oracle_ok(&solved.image,&oracle));
            assert!(max_error(&initial,&oracle)>1.0,"inconsistent case is accidentally a no-op");assert!(solved.objective<solved.initial_objective);
        }
        // A synthesis-null perturbation is an explicit counterexample to
        // treating lower coefficient residual as better image truth. Standard
        // collapse already returns zero; the Euclidean dual need not do so.
        let mut c=s.iter().map(|z|vec![0.0;z.pixels()]).collect::<Vec<_>>();c[1][0]=64.0;
        let expanded=direct_collapse(&s,&c);for(j,v)in c[0].iter_mut().enumerate(){*v=-expanded[j];}
        let initial=direct_collapse(&s,&c);assert!(initial.iter().all(|v|*v==0.0));let oracle=d.solve(&flat_bands(&c));
        assert!(oracle.iter().any(|v|v.abs()>1.0));let solved=operator::reconstruct(&s,&c,&initial).unwrap();assert!(admitted(&solved));assert!(oracle_ok(&solved.image,&oracle));
    }
    let s=level_sizes(1031,1029,7);assert_eq!(s.len(),8);
    let dc=vec![8192.0;s[0].pixels()];let c=direct_analysis(&s,&dc);let initial=direct_collapse(&s,&c);let solved=operator::reconstruct(&s,&c,&initial).unwrap();
    assert!(admitted(&solved));assert!(solved.image.iter().all(|v|(*v-8192.0).abs()<=ERROR_DN as f32));
    let edge=(0..s[0].pixels()).map(|j|8192.0+if j%s[0].width>511{512.0}else{0.0}+if j==s[0].pixels()-1{128.0}else{0.0}).collect::<Vec<_>>();
    let c=direct_analysis(&s,&edge);let initial=direct_collapse(&s,&c);assert!(max_error(&initial,&edge.iter().map(|v|f64::from(*v)).collect::<Vec<_>>())<=ERROR_DN);
    let solved=operator::reconstruct(&s,&c,&initial).unwrap();
    assert!(admitted(&solved),"seven-band high-DN realizable edge failed numerical qualification: {:?}",solved.refusal);
    assert!(oracle_ok(&solved.image,&edge.iter().map(|v|f64::from(*v)).collect::<Vec<_>>()));
}

#[test]
fn independent_refusal_controls(){
    assert!(admissible_fields(true,false,32,ERROR_DN,true));
    for a in [(false,false,32,0.0,true),(true,true,1,0.0,true),(true,false,33,0.0,true),(true,false,1,0.02001,true),(true,false,1,f64::NAN,true),(true,false,1,0.0,false)]{assert!(!admissible_fields(a.0,a.1,a.2,a.3,a.4),"actual admission predicate accepted a destroyer");}
    let s=level_sizes(17,19,1);let c=direct_analysis(&s,&vec![0.0;s[0].pixels()]);let x=vec![0.0;s[0].pixels()];
    for bad in [f32::NAN,f32::INFINITY]{let mut b=c.clone();b[1][0]=bad;assert!(operator::reconstruct(&s,&b,&x).is_err());let mut a=x.clone();a[0]=bad;assert!(operator::reconstruct(&s,&c,&a).is_err());}
    assert!(operator::reconstruct(&s,&c[..1],&x).is_err());assert!(operator::reconstruct(&s,&c,&x[..x.len()-1]).is_err());
}

fn checks(c:&Comparison,frames:&[Frame],before:&[String]){
    assert_eq!((c.native_width,c.native_height),(290,250));assert_eq!(c.level_sizes,vec![[145,125],[73,63],[37,32],[19,16],[10,8]]);
    assert!(c.held_state_bit_exact);assert_eq!(c.canonical_coefficients_sha256,c.coefficients_after_sha256);
    assert_eq!(c.accumulator_before_sha256,c.accumulator_after_sha256);assert_eq!(c.hull_before_sha256,c.hull_after_sha256);
    assert_eq!(c.frames.len(),frames.len());assert_eq!(before.len(),frames.len());
    for((f,h),ev)in frames.iter().zip(before).zip(&c.frames){assert_eq!(&hash(&f.data),h);assert_eq!(&ev.source_sha256,h);assert!(ev.source_unchanged);
        assert_eq!(ev.known4_sha256.len(),4);assert_eq!(ev.source_coefficients_sha256.len(),4);assert!(ev.source_coefficients_sha256.iter().all(|p|p.len()==5));
        assert_eq!(ev.canonical_weight_sha256.len(),4);assert_eq!(ev.energy_sha256.len(),4);assert_eq!(ev.floor_sha256.len(),4);}
    assert_eq!(c.inconsistency_l2.len(),4);assert_eq!(c.final_delta_l2.len(),4);assert_eq!(c.pre_hull_delta_l2.len(),4);
    if c.mode==Mode::Off{assert!(c.candidate_valid&&c.solves.is_empty());assert!(exact(&c.baseline_planes4,&c.candidate_planes4));}
    else{assert_eq!(c.solves.len(),4);assert_eq!(c.candidate_valid,c.solves.iter().all(admitted));
        for s in &c.solves{assert!(s.iterations<=32);if s.converged{assert!(s.refusal.is_none()&&s.objective<=s.initial_objective);}else{assert!(s.refusal.is_some());}}
        if !c.candidate_valid{assert!(exact(&c.baseline_planes4,&c.candidate_planes4));}}
}

#[test]
fn independent_quality_screen(){
    let out=PathBuf::from(std::env::var_os("STREHL_CONSISTENT_RECONSTRUCTION_OUT").expect("root output required"));std::fs::create_dir(&out).unwrap();
    let metric=commission();let ts=transforms();let mut cases=Vec::new();let mut decisions=Vec::new();let mut wrong_source_exercised=false;
    for iso in [100.0f32,400.0]{let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());assert!(noise.is_trustworthy()&&noise.prnu().is_none());
        let(mut flat,mut numerical,mut preservation,mut positive,mut old_outside_exercised)=(0.0,true,true,false,false);
        for scene in [Scene::Flat,Scene::Contact,Scene::GlintNeutral,Scene::GlintColour,Scene::NearFar,Scene::Radial]{
            let frames=ts.iter().enumerate().map(|(k,&t)|fixture(scene,k,t,iso,&noise)).collect::<Vec<_>>();let before=frames.iter().map(|f|hash(&f.data)).collect::<Vec<_>>();
            let c=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default(),Mode::Consistent).unwrap();checks(&c,&frames,&before);
            let native_plane_samples=(crop().width*crop().height)as f64;
            let inconsistent=c.inconsistency_l2.iter().any(|v|*v/native_plane_samples.sqrt()>ERROR_DN);
            let changed=c.final_delta_l2.iter().any(|v|*v/native_plane_samples.sqrt()>ERROR_DN);
            let mut windows=Vec::new();let mut joint=Value::Null;let mut placebo=Value::Null;let mut safety=c.candidate_valid;let mut case_positive=false;
            // Baseline scoring defines the fixed flat and positive excitation,
            // but refused candidate placeholders never receive quality scores.
            if scene==Scene::Flat{flat=score(scene,&c.baseline_rgb,WHOLE).rgb;}
            if scene==Scene::Contact{let outside=score(scene,&c.baseline_rgb,SPILL);old_outside_exercised=outside.rgb>2.0*flat&&outside.bias.iter().sum::<f64>()/3.0>flat;}
            if c.candidate_valid{
                let regions:&[Window]=match scene{Scene::Flat=>&[WHOLE],Scene::Contact=>&[SPILL,CONTACT,CONTACT_EDGE,WHOLE],
                    Scene::GlintNeutral|Scene::GlintColour=>&[FAN,CORE,EDGE,NEAR,WHOLE],Scene::NearFar=>&[WHOLE],Scene::Radial=>&[RADIAL,WHOLE]};
                for &window in regions{let b=score(scene,&c.baseline_rgb,window);let a=score(scene,&c.candidate_rgb,window);let mut pass=no_harm(&b,&a);
                    if window.protect{pass&=live(&b)&&protected(&b,&a);}safety&=pass;
                    if scene==Scene::Contact&&window.name==CONTACT_EDGE.name{case_positive=b.rgb>2.0*flat&&inconsistent&&changed&&a.rgb<=0.95*b.rgb;positive=case_positive;}
                    windows.push(json!({"name":window.name,"active_native_bounds":[window.x0,window.y0,window.x1,window.y1],"baseline":sj(&b),"candidate":sj(&a),
                        "rgb_ratio":a.rgb/b.rgb,"green_ratio":a.green/b.green,"chroma_ratio":a.chroma/b.chroma,"protected_component":window.protect,"preservation_pass":pass}));}
                if scene==Scene::NearFar{let b=two_components(&c.baseline_rgb);let a=two_components(&c.candidate_rgb);
                    let live=b.iter().flatten().all(|v|*v>=0.5);let keep=(0..2).all(|k|(0..3).all(|ch|retained(b[k][ch],a[k][ch])));safety&=live&&keep;
                    joint=json!({"order":["near-fine","far-coarse"],"baseline":b,"candidate":a,"live":live,"retention_pass":keep});}
            }
            // One actual Off identity and one prescribed source-0 destroyer,
            // independent of solver success. No argmax source attribution.
            if scene==Scene::NearFar&&iso==100.0{
                let off=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default(),Mode::Off).unwrap();checks(&off,&frames,&before);
                assert!(exact(&off.baseline_planes4,&c.baseline_planes4));assert!(off.baseline_rgb.iter().zip(&off.candidate_rgb).all(|(a,b)|a.to_bits()==b.to_bits()));
                let wrong=compare_generated(&frames[..1],&ts[..1],crop(),&noise,MergeConfig::default(),Mode::Off).unwrap();checks(&wrong,&frames[..1],&before[..1]);
                let baseline=two_components(&c.baseline_rgb);let bad=two_components(&wrong.candidate_rgb);let b=score(scene,&c.baseline_rgb,WHOLE);let a=score(scene,&wrong.candidate_rgb,WHOLE);
                wrong_source_exercised=!exact(&wrong.candidate_planes4,&c.baseline_planes4)&&((0..3).any(|ch|!retained(baseline[1][ch],bad[1][ch]))||!no_harm(&b,&a));
                assert!(wrong_source_exercised,"prescribed wrong-depth actual input failed to destroy detail");
                placebo=json!({"off_exact":true,"wrong_source":0,"wrong_source_exercised":true,"wrong_components":bad,"wrong_score":sj(&a)});
            }
            numerical&=c.candidate_valid;preservation&=safety;
            let row=json!({"scene":scene.name(),"iso":iso,"numerical_valid":c.candidate_valid,"candidate_placeholder":!c.candidate_valid,"preservation_pass":safety,
                "contact_positive":case_positive,"actual_coefficients_inconsistent":inconsistent,"actual_output_changed":changed,"inconsistency_l2":c.inconsistency_l2,
                "pre_hull_delta_l2":c.pre_hull_delta_l2,"final_delta_l2":c.final_delta_l2,"solves":c.solves.iter().map(solver_json).collect::<Vec<_>>(),
                "windows":windows,"joint_components":joint,"placebos":placebo,"held_state_bit_exact":c.held_state_bit_exact,
                "canonical_coefficients_sha256":c.canonical_coefficients_sha256,"accumulator_sha256":c.accumulator_before_sha256,"hull_sha256":c.hull_before_sha256,"sources":c.frames});
            eprintln!("CONSISTENT_RECONSTRUCTION_CASE {}",json!({"scene":scene.name(),"iso":iso,"numerical_valid":c.candidate_valid,"preservation_pass":safety,"contact_positive":case_positive}));cases.push(row);
        }
        decisions.push(json!({"iso":iso,"numerical_pass":numerical,"preservation_pass":preservation,"contact_positive":positive,"legacy_outside_positive_exercised":old_outside_exercised}));
    }
    assert_eq!(cases.len(),12);let numerical=decisions.iter().all(|d|d["numerical_pass"]==true);let preservation=decisions.iter().all(|d|d["preservation_pass"]==true);let positive=decisions.iter().all(|d|d["contact_positive"]==true);
    let qualified=numerical&&preservation&&positive&&wrong_source_exercised;
    write(&out.join("screen.json"),&json!({"status":"SCREEN_COMPLETE","mechanical_pass":true,"numerical_pass":numerical,"preservation_pass":preservation,"contact_positive":positive,
        "wrong_source_destroyer_exercised":wrong_source_exercised,"candidate_qualified":qualified,"photographic_replay_admitted":false,"iso_decisions":decisions,"metric_commission":metric,"cases":cases,
        "scope":"One fixed unweighted coefficient norm. The exact-linear error bound is numerically commissioned, not an interval certificate for f32. Old outside-spill exercise remains separate. No noise calibration, glare, default, or full-photo admission claim."}));
    eprintln!("CONSISTENT_RECONSTRUCTION {}",json!({"numerical_pass":numerical,"candidate_qualified":qualified,"photographic_replay_admitted":false}));
}
