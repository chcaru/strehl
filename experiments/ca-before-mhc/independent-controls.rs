// Root executes these tests against the author's actual consumer.
use super::{compare_generated,gather_single,Mode};
use serde_json::{json,Value};
use std::path::PathBuf;
use strehl_core::{align::{Cx,Similarity},profile,pyramid::MergeConfig};
use crate::align_cmd::CropRect;
mod fixture {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/ca-before-mhc/independent-fixtures.rs"));
}
use fixture::*;
const SITES:[(usize,usize);4]=[(0,0),(1,0),(0,1),(1,1)];
fn exact(a:&[Vec<f32>],b:&[Vec<f32>])->bool {a.len()==b.len() && a.iter().zip(b).all(|(x,y)|x.len()==y.len() && x.iter().zip(y).all(|(p,q)|p.to_bits()==q.to_bits()))}
fn out()->PathBuf {let p=PathBuf::from(std::env::var_os("STREHL_CA_BEFORE_MHC_OUT").expect("root-owned output required"));std::fs::create_dir_all(&p).unwrap();p}
fn save(name:&str,v:&Value) {serde_json::to_writer_pretty(std::fs::OpenOptions::new().write(true).create_new(true).open(out().join(name)).unwrap(),v).unwrap();}
fn rgb(planes:&[Vec<f32>],c:CropRect)->Vec<f32> {
    crate::merge_cmd::phase_packed_rgb::camera_rgb(planes,c.width,c.height,levels(),[WB[0],WB[1],WB[2],f32::NAN]).unwrap()
}
fn component_commission()->Value {
    let c=crop(false);let (w,h)=(2*c.width,2*c.height);let truth=truth(Scene::ColourFine,c);let good=score(Scene::ColourFine,&truth,c);
    assert!(good.rgb<1e-7 && good.chroma<1e-7 && good.inphase.iter().all(|v|(v-1.0).abs()<1e-6));
    let mut half=truth.clone();let mut grey=truth.clone();
    for (a,b) in half.chunks_exact_mut(3).zip(grey.chunks_exact_mut(3)) {let m=(b[0]+b[1]+b[2])/3.0;for k in 0..3 {let base=wave(k,0.0,0.0).1 as f32;a[k]=base+0.5*(a[k]-base);b[k]=m;}}
    let mut horizontal=truth.clone();let mut blurred=truth.clone();let weights=[1.0f32,4.0,6.0,4.0,1.0];
    for y in 0..h {for x in 2..w-2 {for k in 0..3 {horizontal[3*(y*w+x)+k]=(0..5).map(|d|weights[d]*truth[3*(y*w+x+d-2)+k]).sum::<f32>()/16.0;}}}
    for y in 2..h-2 {for x in 0..w {for k in 0..3 {blurred[3*(y*w+x)+k]=(0..5).map(|d|weights[d]*horizontal[3*((y+d-2)*w+x)+k]).sum::<f32>()/16.0;}}}
    let half_score=score(Scene::ColourFine,&half,c);let grey_score=score(Scene::ColourFine,&grey,c);let blur_score=score(Scene::ColourFine,&blurred,c);
    assert!(!preserves(&good,&half_score) && !preserves(&good,&blur_score));
    assert!(grey_score.chroma>0.02 && !preserves(&good,&grey_score));
    let mut overshoot=truth.clone();for p in overshoot.chunks_exact_mut(3) {for k in 0..3 {let base=wave(k,0.0,0.0).1 as f32;p[k]=base+1.4*(p[k]-base);}}
    let over=score(Scene::ColourFine,&overshoot,c);assert!(preserves(&over,&good),"removing manufactured contrast cannot count as lost truth");
    json!({"truth":good.json(),"half_detail":half_score.json(),"desaturated":grey_score.json(),"extra_blur":blur_score.json(),"overcontrast_truth_cap":true})
}

#[test]
fn independent_operator_controls() {
    let c=crop(false);let noise=profile::noise_model_for("ILCE-7CM2",Some(100.0),levels());let zero=[Similarity::IDENTITY;3];
    let f=fixture(Scene::ColourFine,0,transforms(true)[0],zero,100.0,&noise,true);let original=hash16(&f.data);
    let old=gather_single(&f,transforms(true)[0],c,zero,Mode::Current).unwrap();
    for mode in [Mode::Before,Mode::StagedAfter] {assert!(exact(&old,&gather_single(&f,transforms(true)[0],c,zero,mode).unwrap()),"zero CA changed current gather");}
    // Independently execute the existing CPU source/MHC/Catmull/rounded sink with
    // absent profile. This tests absence independently of the new zero bypass.
    let mut cpu=f.clone();let geometry=cpu.geometry();crate::align_cmd::gpu_cpu_oracle(&mut cpu,transforms(true)[0],geometry,None,false).unwrap();
    let cpu_planes=SITES.map(|(dx,dy)|(0..c.height).flat_map(|y|(0..c.width).map(move|x|(x,y))).map(|(x,y)| {
        (cpu.data[(cpu.active.y+2*(c.y+y)+dy)*cpu.stride+cpu.active.x+2*(c.x+x)+dx] as f32-levels().black).max(0.0)
    }).collect::<Vec<_>>()).to_vec();
    assert!(exact(&old,&cpu_planes),"zero CA GPU bypass differs from absent-profile CPU rounded consumer");
    // Identity native sites, including independent G1/G2 codes. The active origin
    // is odd in the decoded storage and must not alter local RGGB phase.
    let mut coded=f.clone();for y in 0..H {for x in 0..W {
        let site=match(x%2,y%2){(0,0)=>0,(1,0)=>1,(0,1)=>2,_=>3};
        coded.data[(coded.active.y+y)*coded.stride+coded.active.x+x]=512+[1800,2900,3700,4600][site]+((x*17+y*31)%61) as u16;
    }}
    let known=gather_single(&coded,Similarity::IDENTITY,c,zero,Mode::Before).unwrap();
    for (k,(dx,dy)) in SITES.into_iter().enumerate() {for y in 0..c.height {for x in 0..c.width {
        assert_eq!(known[k][y*c.width+x],coded.data[(coded.active.y+2*(c.y+y)+dy)*coded.stride+coded.active.x+2*(c.x+x)+dx] as f32-512.0);
    }}}
    let ca=ca_pulls(1.0);let corrected=gather_single(&coded,Similarity::IDENTITY,c,ca,Mode::Before).unwrap();
    for k in [1,2] {assert_eq!(known[k],corrected[k],"CA preprocessing altered known green sites before alignment");}
    assert!(!exact(&known,&corrected),"nonzero CA correction was not exercised");
    // Continuous affine per-colour fields: literal inverse pull and output
    // expectation, independent of the implementation's coordinate generation.
    let mut affine=f.clone();let t=transforms(true)[1];
    let affine_value=|ch:usize,x:f64,y:f64|[2100.0,3300.0,4200.0][ch]+[1.25,2.0,-1.5][ch]*x+[0.75,-0.5,1.0][ch]*y;
    for y in 0..H {for x in 0..W {let ch=channel(x,y);let(qx,qy)=inverse_native(x as f64,y as f64,ca[ch]);let(px,py)=inverse_native(qx,qy,t);
        affine.data[(affine.active.y+y)*affine.stride+affine.active.x+x]=(512.0+affine_value(ch,px,py)).round() as u16;
    }}
    let mut affine_errors=Vec::new();for mode in [Mode::Current,Mode::Before,Mode::StagedAfter] {
        let got=gather_single(&affine,t,c,ca,mode).unwrap();let mut max_error=0.0f64;
        for(k,(dx,dy))in SITES.into_iter().enumerate(){for y in 0..c.height{for x in 0..c.width{
            let expected=affine_value(channel(dx,dy),(2*(c.x+x)+dx) as f64,(2*(c.y+y)+dy) as f64);
            max_error=max_error.max((got[k][y*c.width+x] as f64-expected).abs());
        }}}
        assert!(max_error<=3.0,"affine colour/phase/coordinate mismatch: {max_error}");affine_errors.push(max_error);
    }
    let n=fixture(Scene::NeutralChip,0,Similarity::IDENTITY,ca,100.0,&noise,false);
    let correct=score(Scene::NeutralChip,&rgb(&gather_single(&n,Similarity::IDENTITY,c,ca,Mode::Before).unwrap(),c),c);
    let wrong=score(Scene::NeutralChip,&rgb(&gather_single(&n,Similarity::IDENTITY,c,ca_pulls(-1.0),Mode::Before).unwrap(),c),c);
    assert!(wrong.rgb>1.05*correct.rgb && wrong.chroma>1.05*correct.chroma,"wrong-sign correction was not a live destroyer");
    // The old composed pull can remain covered while a neighbour needed by
    // pre-corrected MHC reaches beyond the genuine same-colour source lattice.
    let edge=CropRect{x:2,y:8,width:15,height:15};let shift=Similarity{a:Cx::new(1.0,0.0),b:Cx::new(0.125,0.125)};
    assert!(gather_single(&n,shift,edge,ca,Mode::Current).is_ok(),"boundary control did not retain the old supported pull");
    assert!(gather_single(&n,shift,edge,ca,Mode::Before).is_err(),"new same-CFA support loss was silently filled");
    let mut invalid=ca;invalid[0].b.re=f64::NAN;assert!(gather_single(&n,Similarity::IDENTITY,c,invalid,Mode::Before).is_err());
    assert_eq!(hash16(&f.data),original,"original source storage changed");
    let record=json!({"passed":true,"zero_ca_and_absent_profile_cpu_exact":true,"native_known_sites_exact":true,
        "identity_green_known_sites_exact":true,"nonzero_ca_live":true,"affine_max_dn":affine_errors,
        "wrong_sign":{"correct":correct.json(),"wrong":wrong.json()},"new_boundary_refusal":true,
        "nonfinite_refusal":true,"original_source_unchanged":true,"metric_commission":component_commission()});
    eprintln!("CA_BEFORE_MHC_OPERATOR {record}");save("operator.json",&record);
}

#[test]
fn independent_quality_screen() {
    let mut cases=Vec::new();let mut admitted=true;let mut probe_live=false;let mut zero_merge_checked=false;
    for iso in [100.0f32,400.0] {let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());assert!(noise.is_trustworthy() && noise.prnu().is_none());
        for phase in [false,true] {let c=crop(phase);let ts=transforms(phase);
            for scene in SCENES {
                let frames=ts.iter().enumerate().map(|(i,t)|fixture(scene,i,*t,ca_pulls(1.0),iso,&noise,true)).collect::<Vec<_>>();
                let originals=frames.iter().map(|f|hash16(&f.data)).collect::<Vec<_>>();
                let cmp=compare_generated(&frames,&ts,c,&noise,MergeConfig::default(),ca_pulls(1.0)).unwrap();
                assert_eq!((cmp.native_width,cmp.native_height),(2*c.width,2*c.height));
                let scores=[&cmp.current,&cmp.before,&cmp.staged_after].map(|a|score(scene,&a.rgb,c));
                for arm in [&cmp.current,&cmp.before,&cmp.staged_after] {
                    assert_eq!(arm.frames.len(),N);
                    for (i,e) in arm.frames.iter().enumerate(){assert_eq!(e.source_sha256,originals[i]);assert!(e.source_unchanged);assert!(!e.beta.is_empty() && e.beta.iter().all(|v|v.is_finite() && *v>=0.0));}
                }
                for k in [1,2] {assert_eq!(cmp.current.planes4[k],cmp.staged_after.planes4[k],"staged-after changed the identity-CA green consumer");}
                for (a,b) in cmp.current.frames.iter().zip(&cmp.staged_after.frames) {
                    assert_eq!(a.guide_sha256,b.guide_sha256);assert_eq!(a.variance_sha256,b.variance_sha256);assert_eq!(a.beta,b.beta);
                    for k in [1,2] {assert_eq!(a.known4_sha256[k],b.known4_sha256[k]);}
                }
                for i in 0..N {assert_eq!(hash16(&frames[i].data),originals[i]);}
                probe_live|=cmp.current.frames.iter().zip(&cmp.before.frames).any(|(a,b)|a.beta.iter().zip(&b.beta).any(|(x,y)|x.to_bits()!=y.to_bits()));
                let component_live=!scene.components() || scores[0].inphase.iter().all(|v|*v>=0.5);
                let component_pass=!scene.components() || preserves(&scores[0],&scores[1]);
                let rgb_pass=scores[1].rgb<=1.05*scores[0].rgb;let chroma_pass=scores[1].chroma<=1.05*scores[0].chroma;
                let neutral_gain=scene!=Scene::NeutralChip || scores[1].chroma<=0.95*scores[0].chroma;
                let pass=rgb_pass && chroma_pass && component_live && component_pass && neutral_gain;admitted&=pass;
                if scene==Scene::ColourFocus {assert!(cmp.current.averaged_fraction[0]<1.0,"varying-focus selection unexercised");}
                let evidence=[&cmp.current,&cmp.before,&cmp.staged_after].map(|a|json!({"frames":a.frames.iter().map(|e|json!({
                    "source_sha256":e.source_sha256,"known4_sha256":e.known4_sha256,"guide_sha256":e.guide_sha256,
                    "variance_sha256":e.variance_sha256,"beta":e.beta,"source_unchanged":e.source_unchanged})).collect::<Vec<_>>(),"averaged_fraction":a.averaged_fraction}));
                let record=json!({"scene":scene.name(),"iso":iso,"fractional_and_shifted_crop":phase,"crop":[c.x,c.y,c.width,c.height],
                    "current":scores[0].json(),"before":scores[1].json(),"staged_after":scores[2].json(),
                    "before_rgb_ratio":scores[1].rgb/scores[0].rgb,"before_chroma_ratio":scores[1].chroma/scores[0].chroma,
                    "staged_rgb_ratio":scores[2].rgb/scores[0].rgb,"staged_chroma_ratio":scores[2].chroma/scores[0].chroma,
                    "component_live":component_live,"component_pass":component_pass,"rgb_pass":rgb_pass,"chroma_pass":chroma_pass,
                    "neutral_gain_pass":neutral_gain,"case_admitted":pass,"level_sizes":cmp.level_sizes,"evidence":evidence});
                eprintln!("CA_BEFORE_MHC_CASE {record}");cases.push(record);
                if !zero_merge_checked {
                    let zero=compare_generated(&frames,&ts,c,&noise,MergeConfig::default(),[Similarity::IDENTITY;3]).unwrap();
                    assert!(exact(&zero.current.planes4,&zero.before.planes4) && exact(&zero.current.planes4,&zero.staged_after.planes4));
                    for (a,b) in zero.current.frames.iter().zip(&zero.before.frames) {assert_eq!(a.guide_sha256,b.guide_sha256);assert_eq!(a.variance_sha256,b.variance_sha256);assert_eq!(a.beta,b.beta);}
                    zero_merge_checked=true;
                }
            }
        }
    }
    assert!(probe_live,"changed interpolation never changed actual probe transfer");
    let record=json!({"instrument_passed":true,"photographic_replay_admitted":admitted,"case_count":cases.len(),"zero_ca_actual_merge_exact":zero_merge_checked,
        "actual_probe_transfer_changed":probe_live,"staged_after_green_and_probe_exact":true,"fixed_ca_radial_slopes":[-508.4e-6,0.0,174.4e-6],"virtual_full_sensor":[7032,4688],"virtual_patch_centre":[5984,560],"cases":cases});
    eprintln!("CA_BEFORE_MHC_SCREEN {record}");save("screen.json",&record);
}
