include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/variance-stabilized-guide/independent-fixtures.rs"));
use super::{Transform,Bands,PairedEnergy,guide_bands,Arm,Comparison,compare_generated,compare_generated_with_diagnostics};
use strehl_core::pyramid::{LevelSize,Pyramid,Workspace,level_sizes};

fn artificial_noise()->NoiseModel{NoiseModel::new(CfaPlane::ALL.map(|p|{let gain=match p{CfaPlane::G1=>0.5,CfaPlane::G2=>1.5,_=>0.75};PlaneNoise{gain_dn_per_e:gain,read_noise_e:2.0,levels:levels()}}),100.0,Provenance::Measured)}
#[test]
fn independent_transform_controls(){
    let t=Transform::from_noise(&artificial_noise()).unwrap();assert_eq!(t.a,0.5);assert_eq!(t.b,2.5);assert_eq!(t.pedestal,2.59375);assert_eq!(t.reference_signal,2000.0);
    let inputs=[-3.0,0.0,1.0,16.0,200.0,2000.0,8000.0,14848.0];let values=t.apply(&inputs).unwrap();
    for(&s,&actual)in inputs.iter().zip(&values){let expected=2.0*(1002.59375f64).sqrt()/0.5*((0.5*f64::from(s.max(0.0))+2.59375).sqrt()-2.59375f64.sqrt());
        assert!((f64::from(actual)-expected).abs()<=0.002+2e-6*expected.abs());}
    assert_eq!(values[0],0.0);assert_eq!(values[1],0.0);assert!(values[2..].windows(2).all(|w|w[1]>w[0]));
    let d=t.apply(&[1998.0,2002.0]).unwrap();assert!(((d[1]-d[0])/4.0-1.0).abs()<0.001);
    let raw=t.apply(&[100.0,8000.0,4050.0]).unwrap();assert!((raw[2]-0.5*(raw[0]+raw[1])).abs()>50.0,"transform-before-green-average destroyer inert");
    let no_pedestal=2.0*(1000.0f64).sqrt()/0.5*(0.5*16.0f64).sqrt();assert!((f64::from(values[3])-no_pedestal).abs()>10.0);
    assert!(t.apply(&[f32::NAN]).is_err());assert!(t.apply(&[f32::INFINITY]).is_err());
}
fn literal_bands(v:&[f32],s:&[LevelSize])->Bands{let mut p=Pyramid::zeros(s);p.build(v,&mut Workspace::new(s));(0..s.len()-1).map(|k|p.level(k).to_vec()).collect()}
fn literal_smooth(v:&[f32],s:LevelSize)->Vec<f32>{let tap=[1.0,4.0,6.0,4.0,1.0];let mut out=vec![0.0;v.len()];for y in 0..s.height{for x in 0..s.width{
    let mut sum=0.0;for ky in 0..5{for kx in 0..5{let xx=(x as isize+kx as isize-2).clamp(0,s.width as isize-1)as usize;let yy=(y as isize+ky as isize-2).clamp(0,s.height as isize-1)as usize;sum+=tap[kx]*tap[ky]*f64::from(v[yy*s.width+xx]);}}out[y*s.width+x]=(sum/256.0)as f32;
}}out}
fn band_close(a:&[Bands;2],b:&[Bands;2])->bool{a.iter().zip(b).all(|(a,b)|a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|a.len()==b.len()&&a.iter().zip(b).all(|(&a,&b)|(a-b).abs()<=0.001+3e-5*a.abs().max(b.abs()))))}
#[test]
fn independent_paired_floor_controls(){
    let sizes=level_sizes(89,73,7);assert_eq!(sizes.len(),4);let t=Transform::from_noise(&artificial_noise()).unwrap();
    let make=|draw:usize,anti:bool|{let n=sizes[0].pixels();let mut v=vec![vec![999.0;n];4];for j in 0..n{let d=(((j*7+draw*17+(j%89)*(draw+3))%71)as f32-35.0)*4.0;
        let base=if (j%89)<44{200.0}else{8000.0};v[1][j]=base+d;v[2][j]=base+if anti{-d}else{d};}v};
    let mut actual=PairedEnergy::new(&sizes);let mut expected:[Bands;2]=std::array::from_fn(|_|sizes[..sizes.len()-1].iter().map(|s|vec![0.0;s.pixels()]).collect());
    let mut anti=PairedEnergy::new(&sizes);
    for pair in 0..8{let mut pair_bands=Vec::new();for draw in [2*pair,2*pair+1]{let v=make(draw,false);let green=v[1].iter().zip(&v[2]).map(|(a,b)|0.5*(a+b)).collect::<Vec<_>>();
        let literal=[literal_bands(&green,&sizes),literal_bands(&t.apply(&green).unwrap(),&sizes)];let computed=guide_bands(&v,&sizes,&t).unwrap();assert!(exact(&literal[0],&computed[0])&&exact(&literal[1],&computed[1]));pair_bands.push(literal);}
        actual.add_pair(&pair_bands[0],&pair_bands[1]).unwrap();for arm in 0..2{for k in 0..sizes.len()-1{for j in 0..expected[arm][k].len(){let d=pair_bands[0][arm][k][j]-pair_bands[1][arm][k][j];expected[arm][k][j]+=d*d;}}}
        anti.add_pair(&guide_bands(&make(2*pair,true),&sizes,&t).unwrap(),&guide_bands(&make(2*pair+1,true),&sizes,&t).unwrap()).unwrap();
    }
    let invalid:[Bands;2]=std::array::from_fn(|_|sizes[..sizes.len()-1].iter().map(|s|vec![0.0;s.pixels()]).collect());assert!(actual.add_pair(&invalid,&invalid).is_err());
    for arm in 0..2{for k in 0..sizes.len()-1{for v in &mut expected[arm][k]{*v/=16.0;}expected[arm][k]=literal_smooth(&expected[arm][k],sizes[k]);}}
    let got=actual.finish().unwrap();assert!(band_close(&got,&expected));assert!(anti.finish().unwrap().iter().flatten().flatten().all(|v|*v==0.0));
    assert!(got.iter().all(|a|a.iter().flatten().any(|v|*v>1.0)));let doubled:[Bands;2]=std::array::from_fn(|a|expected[a].iter().map(|v|v.iter().map(|x|2.0*x).collect()).collect());assert!(!band_close(&got,&doubled));
    let omitted:[Bands;2]=[expected[0].clone(),expected[0].clone()];assert!(!band_close(&got,&omitted),"linear floor substituted for nonlinear floor escaped");
    let mut short=PairedEnergy::new(&sizes);for _ in 0..7{short.add_pair(&invalid,&invalid).unwrap();}assert!(short.finish().is_err());
    let mut bad=invalid.clone();bad[1][0][0]=f32::NAN;assert!(PairedEnergy::new(&sizes).add_pair(&bad,&invalid).is_err());
}
fn commission()->Value{
    let truth=truth_image(Scene::WeakColour);let good=score(Scene::WeakColour,&truth,INTERIOR);assert!(good.rgb<1e-7);let mut half=truth.clone();let mut noisy=truth.clone();
    for(p,(a,b))in half.chunks_exact_mut(3).zip(noisy.chunks_exact_mut(3)).enumerate(){for c in 0..3{a[c]=0.18+0.5*(a[c]-0.18);b[c]+=0.03*gaussian(p%(2*crop().width),p/(2*crop().width),c)as f32;}}
    let half_score=score(Scene::WeakColour,&half,INTERIOR);assert!(!keep(&good,&half_score));let noise_score=score(Scene::WeakColour,&noisy,INTERIOR);assert!(noise_score.rgb>0.02&&!safe(&good,&noise_score));
    let zero=vec![0.0;truth.len()];assert!(!safe(&good,&score(Scene::WeakColour,&zero,INTERIOR))&&!keep(&good,&score(Scene::WeakColour,&zero,INTERIOR)));
    let vt=truth_image(Scene::Veil);let joint=joint_core(&vt);assert!(joint.coefficients.iter().flatten().all(|v|(v-1.0).abs()<1e-5));let mut reduced=vt.clone();
    for y in 0..2*crop().height{for x in 0..2*crop().width{for c in 0..3{let[b,t,g]=components(Scene::Veil,c,(x+2*crop().x)as f64,(y+2*crop().y)as f64,None);reduced[(y*2*crop().width+x)*3+c]=(b+0.5*t+g)as f32;}}}
    let half_texture=joint_core(&reduced);assert!(half_texture.coefficients.iter().all(|v|(v[0]-0.5).abs()<1e-5&&(v[1]-1.0).abs()<1e-5)&&!joint_keep(&joint,&half_texture));
    json!({"truth":score_json(&good),"half_detail":score_json(&half_score),"added_noise":score_json(&noise_score),"zero_rejected":true,"joint_truth":joint_json(&joint),"joint_half_texture":joint_json(&half_texture)})
}
#[test]fn independent_metric_controls(){let _=commission();}
fn arms(c:&Comparison)->[(&'static str,&Arm);4]{[("canonical",&c.canonical),("identity",&c.identity),("matched-linear",&c.matched_linear),("stabilized",&c.stabilized)]}
fn exact_arm(a:&Arm,b:&Arm)->bool{exact(&a.planes4,&b.planes4)&&exact_slice(&a.rgb,&b.rgb)}
fn checks(c:&Comparison,frames:&[Frame],ts:&[Similarity],before:&[String])->Value{
    assert_eq!((c.native_width,c.native_height),(290,250));assert_eq!(c.level_sizes,vec![[145,125],[73,63],[37,32],[19,16],[10,8]]);assert_eq!(c.frames.len(),N);assert!(exact_arm(&c.canonical,&c.identity));
    let n=crop().width*crop().height;let mut lo=vec![vec![f32::INFINITY;n];4];let mut hi=vec![vec![f32::NEG_INFINITY;n];4];let mut seeds=std::collections::BTreeSet::new();
    for(k,f)in frames.iter().enumerate(){let ev=&c.frames[k];assert_eq!(hash16(&f.data),before[k]);assert_eq!(ev.source_sha256,before[k]);assert!(ev.source_unchanged);
        let active=(0..H).flat_map(|y|f.active_row(y).iter().copied()).collect::<Vec<_>>();assert_eq!(hash16(&active),ev.active_sha256);assert!(active.iter().all(|v|*v>512&&*v<15360));
        for seed in ev.probe_seeds{assert!(seeds.insert(seed));}let gathered=super::super::boundary_cfa_wavelet::gather_known4(f,ts[k],crop()).unwrap();
        for ch in 0..4{assert_eq!(hash_f32(&gathered[ch]),ev.known4_sha256[ch]);for j in 0..n{lo[ch][j]=lo[ch][j].min(gathered[ch][j]);hi[ch][j]=hi[ch][j].max(gathered[ch][j]);}}
        for field in [&ev.canonical_fields,&ev.linear_fields,&ev.stabilized_fields]{assert_eq!(field.energy_sha256.len(),c.level_sizes.len()-1);assert_eq!(field.floor_sha256.len(),field.energy_sha256.len());assert_eq!(field.weight_sha256.len(),field.energy_sha256.len());assert_eq!(field.positive_weight_counts.len(),field.energy_sha256.len());}
    }
    for(_,arm)in arms(c){assert!(arm.terminal_base_exact&&arm.rgb.iter().all(|v|v.is_finite()));assert_eq!(arm.planes4.len(),4);for ch in 0..4{assert_eq!(arm.planes4[ch].len(),n);for j in 0..n{assert!(arm.planes4[ch][j]>=lo[ch][j]&&arm.planes4[ch][j]<=hi[ch][j]);}}}
    json!({"canonical_identity_exact":true,"all_linear_terminal_bases_exact":true,"all_original_input_hulls_exact":true,"originals_unchanged":true,"probe_seed_count":seeds.len(),"original_clipped_codes":0})
}
fn output_hashes(c:&Comparison)->Value{json!(arms(c).iter().map(|(name,a)|json!({"name":name,"rgb_sha256":hash_f32(&a.rgb),"planes4_sha256":a.planes4.iter().map(|v|hash_f32(v)).collect::<Vec<_>>(),"averaged_fraction":a.averaged_fraction})).collect::<Vec<_>>())}
#[test]
fn independent_quality_screen(){
    let out=PathBuf::from(std::env::var_os("STREHL_VARIANCE_STABILIZED_GUIDE_OUT").expect("root-owned output required"));std::fs::create_dir(&out).unwrap();let metric=commission();let ts=transforms();
    let mut cases=Vec::new();let(mut quality,mut positive,mut positive_exercised)=(true,true,false);
    for iso in [100.0f32,400.0]{let noise=profile::noise_model_for("ILCE-7CM2",Some(iso),levels());assert!(noise.is_trustworthy()&&noise.prnu().is_none());let mut flat=[0.0;2];
        // Flat executes before any image-detail metric at each injected noise level.
        for scene in [Scene::Flat,Scene::Veil,Scene::BrightRidge,Scene::WeakColour]{let frames=ts.iter().enumerate().map(|(k,&t)|fixture(scene,k,t,iso,&noise)).collect::<Vec<_>>();let before=frames.iter().map(|f|hash16(&f.data)).collect::<Vec<_>>();
            let c=compare_generated(&frames,&ts,crop(),&noise,MergeConfig::default()).unwrap();let structural=checks(&c,&frames,&ts,&before);let refs=[&c.canonical,&c.matched_linear];let mut windows=Vec::new();let mut pass=true;let mut exercised=false;
            let regions:&[Window]=match scene{Scene::Veil=>&[SPILL,ADJACENT,CORE],Scene::BrightRidge=>&[RIDGE,INTERIOR],_=>&[INTERIOR]};
            for &w in regions{let candidate=score(scene,&c.stabilized.rgb,w);let bs=refs.map(|a|score(scene,&a.rgb,w));let mut gate=bs.iter().all(|b|safe(b,&candidate));
                if scene==Scene::Flat{flat=[bs[0].rgb,bs[1].rgb];}
                let protected=scene==Scene::WeakColour||scene==Scene::BrightRidge&&w.name==RIDGE.name||scene==Scene::Veil&&(w.name==ADJACENT.name||w.name==CORE.name);
                if protected{gate&=bs.iter().all(|b|keep(b,&candidate));}
                let mut joint=Value::Null;if scene==Scene::Veil&&w.name==CORE.name{let a=joint_core(&c.stabilized.rgb);let b=refs.map(|r|joint_core(&r.rgb));gate&=b.iter().all(|b|joint_keep(b,&a));joint=json!({"canonical":joint_json(&b[0]),"matched_linear":joint_json(&b[1]),"stabilized":joint_json(&a)});}
                if scene==Scene::Veil&&w.name==SPILL.name{let live=c.frames.iter().any(|f|f.stabilized_fields.weight_sha256!=f.linear_fields.weight_sha256&&f.stabilized_fields.positive_weight_counts.iter().any(|&n|n>0))&&!exact_arm(&c.stabilized,&c.matched_linear)&&!exact_arm(&c.stabilized,&c.canonical);
                    exercised=live&&(0..2).all(|i|bs[i].rgb>2.0*flat[i]&&bs[i].bias>flat[i]);
                    if iso==100.0{let benefit=bs.iter().all(|b|candidate.rgb<=0.95*b.rgb);positive=benefit;positive_exercised=exercised;gate&=benefit&&exercised;}}
                pass&=gate;windows.push(json!({"name":w.name,"native_xyxy":[w.x0,w.y0,w.x1,w.y1],"canonical":score_json(&bs[0]),"matched_linear":score_json(&bs[1]),"stabilized":score_json(&candidate),"pass":gate,"joint":joint}));
            }
            let mut observer=Value::Null;if scene==Scene::Veil&&iso==100.0{let off=compare_generated_with_diagnostics(&frames,&ts,crop(),&noise,MergeConfig::default(),false).unwrap();for((name,a),(name2,b))in arms(&c).into_iter().zip(arms(&off)){assert_eq!(name,name2);assert!(exact_arm(a,b));}assert!(off.frames.is_empty());assert_eq!(serde_json::to_value(c.transform).unwrap(),serde_json::to_value(off.transform).unwrap());for(k,f)in frames.iter().enumerate(){assert_eq!(hash16(&f.data),before[k]);}observer=json!({"all_four_arms_exact":true,"on":output_hashes(&c),"off":output_hashes(&off)});}
            quality&=pass;cases.push(json!({"scene":scene.name(),"iso":iso,"quality_pass":pass,"positive_exercised":exercised,"positive_required":scene==Scene::Veil&&iso==100.0,"windows":windows,"structural":structural,"transform":c.transform,"sources":c.frames,"output_hashes":output_hashes(&c),"observer":observer}));
        }
    }
    assert_eq!(cases.len(),8);let nominated=quality&&positive&&positive_exercised;write(&out.join("screen.json"),&json!({"status":"SCREEN_COMPLETE","mechanical_pass":true,"quality_pass":quality,"positive_pass":positive,"positive_exercised":positive_exercised,"candidate_nominated":nominated,"photographic_replay_admitted":false,"metric_commission":metric,"cases":cases,"scope":"Generated original-u16 actual-consumer screen only. Shared injected noise is not calibrated here. No RAW/full-photo/default/SOTA claim."}));
    eprintln!("VARIANCE_STABILIZED_GUIDE {}",json!({"candidate_nominated":nominated,"photographic_replay_admitted":false}));
}
