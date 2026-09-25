// Generated oracle support on the actual native consumer. No default or RAW path.
use super::*;
use serde_json::{json,Value};
use std::{path::{Path,PathBuf},io::Write};
use strehl_core::{CfaPlane,align::Similarity,pyramid::{LevelSize,reduce,expand,
    rb_own_guide_diagnostic as core,optical_support_veto_diagnostic as invariant,Hull,Fallback}};
use super::shared_source_field::{hash16,hash32};
const W:usize=96;const H:usize=96;const N:usize=5;
fn crop()->align_cmd::CropRect{align_cmd::CropRect{x:8,y:8,width:32,height:32}}
fn levels()->Levels{Levels{black:512.,white:15360.}}
fn same(a:&[Vec<f32>],b:&[Vec<f32>])->bool{a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|
    a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits()))}
fn save_json(path:&Path,value:&Value)->Result<()>{let f=std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(f,value)?;Ok(())}
fn save_f32(path:&Path,v:&[f32])->Result<()>{let mut f=std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    for x in v{f.write_all(&x.to_le_bytes())?;}Ok(())}
fn save_u8(path:&Path,v:&[u8])->Result<()>{std::fs::OpenOptions::new().write(true).create_new(true).open(path)?.write_all(v)?;Ok(())}
fn bytes(path:&Path,n:usize)->Result<Vec<u8>>{let v=std::fs::read(path)?;ensure!(v.len()==n,"fixture extent mismatch");Ok(v)}
fn floats(path:&Path,n:usize)->Result<Vec<f32>>{let b=bytes(path,n*4)?;let v=b.chunks_exact(4)
    .map(|x|f32::from_le_bytes(x.try_into().unwrap())).collect::<Vec<_>>();
    ensure!(v.iter().all(|v|v.is_finite()),"nonfinite fixture");Ok(v)}

/// Propagate surface-ID sets by the ACTUAL positive spatial operators. No
/// interpolation/resizing surrogate or guessed support radius is involved.
fn union_reduce(src:&[u8],sz:LevelSize)->Vec<u8>{
    let dst=sz.reduced();let mut out=vec![0u8;dst.pixels()];
    for bit in [1u8,2,4]{let input=src.iter().map(|v|if v&bit!=0{1.}else{0.}).collect::<Vec<_>>();
        let mut reduced=vec![0.;dst.pixels()];reduce(&input,sz,&mut reduced,&mut vec![0.;dst.width*sz.height]);
        for(o,v)in out.iter_mut().zip(reduced){if v>0.{*o|=bit;}}}out
}
fn union_expand(src:&[u8],sz:LevelSize,dst:LevelSize)->Vec<u8>{
    let mut out=vec![0u8;dst.pixels()];
    for bit in [1u8,2,4]{let input=src.iter().map(|v|if v&bit!=0{1.}else{0.}).collect::<Vec<_>>();
        let mut expanded=vec![0.;dst.pixels()];expand(&input,sz,&mut expanded,dst,&mut vec![0.;dst.width*sz.height]);
        for(o,v)in out.iter_mut().zip(expanded){if v>0.{*o|=bit;}}}out
}
fn coefficient_sets(leaf:&[u8],sizes:&[LevelSize])->Vec<Vec<u8>>{
    assert!(strehl_core::pyramid::KERNEL.iter().all(|v|*v>0.));
    assert_eq!(leaf.len(),sizes[0].pixels());assert!(leaf.iter().all(|v|*v<=7));
    let mut g=vec![leaf.to_vec()];for k in 1..sizes.len(){g.push(union_reduce(&g[k-1],sizes[k-1]));}
    (0..sizes.len()-1).map(|k|g[k].iter().zip(union_expand(&g[k+1],sizes[k+1],sizes[k]))
        .map(|(a,b)|a|b).collect()).collect()
}
fn masks(folder:&Path,opaque:bool,sizes:&[LevelSize])->Result<Vec<Vec<Vec<u8>>>>{
    let sharp=bytes(&folder.join("sharp-labels.u8"),W*H)?;ensure!(sharp.iter().all(|v|*v==1||*v==2),"invalid sharp labels");
    (0..N).map(|i|{let native=bytes(&folder.join(format!("frame-{i}-support.u8")),W*H)?;
        ensure!(native.iter().all(|v|*v>0&&*v<=7),"invalid optical support bits");
        if !opaque{return Ok(sizes[..sizes.len()-1].iter().map(|s|vec![1;s.pixels()]).collect());}
        let cp=crop();let mut leaf=vec![0u8;cp.width*cp.height];
        for y in 0..cp.height{for x in 0..cp.width{for dy in 0..2{for dx in 0..2{
            leaf[y*cp.width+x]|=native[(2*(cp.y+y)+dy)*W+2*(cp.x+x)+dx];}}}}
        let sets=coefficient_sets(&leaf,sizes);
        Ok(sets.iter().enumerate().map(|(k,v)|v.iter().enumerate().map(|(j,&bits)|{
            let x=2*cp.x+2*(j%sizes[k].width)*(1usize<<k);
            let y=2*cp.y+2*(j/sizes[k].width)*(1usize<<k);
            u8::from(bits==sharp[y*W+x])}).collect()).collect())
    }).collect()
}
fn scramble(mut x:u32)->u32{x^=x>>16;x=x.wrapping_mul(0x7feb352d);x^=x>>15;x=x.wrapping_mul(0x846ca68b);x^(x>>16)}
fn gaussian(x:usize,y:usize,k:usize)->f32{let s=x as u32^((y as u32)<<16)^(k as u32).wrapping_mul(0x9e3779b9)^0x54b3e927;
    let u=(scramble(s)as f64+0.5)/4294967296.;let v=(scramble(s^0xa73126bd)as f64+0.5)/4294967296.;
    ((-2.*u.ln()).sqrt()*(std::f64::consts::TAU*v).cos())as f32}
fn frames(folder:&Path,noise:&NoiseModel)->Result<Vec<Frame>>{
    (0..N).map(|i|{let rgb=floats(&folder.join(format!("frame-{i}-rgb-dn.f32")),W*H*3)?;
        let active=strehl_raw::Region{x:3,y:5,width:W,height:H};let stride=W+11;let height=H+13;
        let mut f=Frame{data:vec![64999;stride*height],stride,buffer_height:height,active,levels:levels(),iso:Some(100.),
            wb_coeffs:[1.,1.,1.,f32::NAN],xyz_to_cam_rgbe:[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.],[0.;3]],
            color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),path:std::env::current_dir()?.join(format!("nonexistent-optical-support-{}-{i}.ARW",folder.file_name().unwrap().to_string_lossy()))};
        ensure!(!f.path.exists(),"generated path unexpectedly exists");
        for y in 0..H{for x in 0..W{let (ch,p)=match(x%2,y%2){(0,0)=>(0,CfaPlane::R),(1,0)=>(1,CfaPlane::G1),(0,1)=>(1,CfaPlane::G2),_=>(2,CfaPlane::B)};
            let signal=rgb[3*(y*W+x)+ch];ensure!(signal>=0.&&signal<14848.,"invalid generated expectation");
            let dn=512.+signal+gaussian(x,y,i)*noise.sigma(p,signal);ensure!(dn>0.&&dn<16383.,"fixture clipped sensor code");
            f.data[(active.y+y)*stride+active.x+x]=dn.round()as u16;}}
        Ok(f)
    }).collect()
}
struct Retained{planes:Vec<Vec<f32>>,fields:core::Fields}
fn write_image(folder:&Path,name:&str,planes:&[Vec<f32>])->Result<Value>{
    let cp=crop();let rgb=phase_packed_rgb::camera_rgb(planes,cp.width,cp.height,levels(),[1.,1.,1.,f32::NAN])?;
    save_f32(&folder.join(format!("{name}-rgb.f32")),&rgb)?;
    let dev=crate::image_out::Develop::measurement(true);
    let display=rgb.chunks_exact(3).flat_map(|v|crate::image_out::develop_pixel([v[0],v[1],v[2]],&dev)).collect::<Vec<_>>();
    crate::image_out::write_rgb16_described(&folder.join(format!("{name}.tiff")),64,64,&display,&dev)?;
    save_f32(&folder.join(format!("{name}-cfa.f32")),&planes.concat())?;
    Ok(json!({"cfa_sha256":planes.iter().map(|p|hash32(p)).collect::<Vec<_>>(),"rgb_sha256":hash32(&rgb),"rgb16_sha256":hash16(&display)}))
}
fn arm(retained:&[Retained],q:&[Vec<Vec<u8>>],sizes:&[LevelSize],cfg:MergeConfig,mode:&str,
    baseline:&BandMerge,folder:&Path)->Result<Value>{
    let nb=sizes.len()-1;let mut candidate=BandMerge::new(32,32,4,cfg);let mut ws=FrameWorkspace::new(sizes,4);
    let source=|i:usize|if mode=="permuted"{(i+2)%N}else{i};
    let admitted=(0..nb).map(|k|(0..sizes[k].pixels()).map(|j|(0..N).any(|i|
        retained[i].fields.weights[k][j]>0.&&(mode=="all-one"||q[source(i)][k][j]!=0))).collect::<Vec<_>>()).collect::<Vec<_>>();
    let mut counts=vec![[0usize;4];nb];let mut den=vec![Vec::<f64>::new();nb];let mut sumsq=den.clone();
    for k in 0..nb{den[k]=vec![0.;sizes[k].pixels()];sumsq[k]=den[k].clone();}
    for(i,r)in retained.iter().enumerate(){let mut fields=core::Fields{energy:r.fields.energy.clone(),floor:r.fields.floor.clone(),weights:r.fields.weights.clone()};
        for k in 0..nb{for(j,w)in fields.weights[k].iter_mut().enumerate(){let old=*w;
            let keep=mode=="all-one"||q[source(i)][k][j]!=0||!admitted[k][j];
            if !keep{*w=0.;}counts[k][0]+=usize::from(old>0.&&!keep);counts[k][1]+=usize::from(old>0.&&keep);
            den[k][j]+=f64::from(*w);sumsq[k][j]+=f64::from(*w)*f64::from(*w);
        }}
        core::add_fields(&mut candidate,&r.planes.iter().map(Vec::as_slice).collect::<Vec<_>>(),&fields,&mut ws);
    }
    ensure!(invariant::held_state_exact(baseline,&candidate),"base/fallback/bounds changed");
    let mut diagnostics=Vec::new();
    for k in 0..nb{let mut exercised=vec![0u8;sizes[k].pixels()];let mut no_clean=vec![0u8;sizes[k].pixels()];
        let mut before_mass=0f64;let mut after_mass=0f64;let mut before_neff=0f64;let mut after_neff=0f64;let mut supported=0usize;
        for j in 0..sizes[k].pixels(){let mut d=0f64;let mut sq=0f64;let mut bad=false;let mut clean=false;
            for i in 0..N{let w=retained[i].fields.weights[k][j];d+=f64::from(w);sq+=f64::from(w).powi(2);
                bad|=w>0.&&q[i][k][j]==0;clean|=w>0.&&q[i][k][j]!=0;}
            no_clean[j]=u8::from(d>0.&&!admitted[k][j]);
            let x=16+2*(j%sizes[k].width)*(1usize<<k);let y=16+2*(j/sizes[k].width)*(1usize<<k);
            exercised[j]=u8::from(bad&&clean&&(44..50).contains(&x)&&(20..32).contains(&y));
            counts[k][2]+=usize::from(no_clean[j]!=0);counts[k][3]+=usize::from(exercised[j]!=0);
            before_mass+=d;after_mass+=den[k][j];if d>0.{before_neff+=d*d/sq;after_neff+=den[k][j]*den[k][j]/sumsq[k][j];supported+=1;}
        }
        save_u8(&folder.join(format!("{mode}-b{k}-exercised.u8")),&exercised)?;
        save_u8(&folder.join(format!("{mode}-b{k}-no-clean.u8")),&no_clean)?;
        diagnostics.push(json!({"band":k,"zeroed_positive_source_cells":counts[k][0],"retained_positive_source_cells":counts[k][1],
            "no_clean_coefficients":counts[k][2],"outside_exercised_coefficients":counts[k][3],"before_mass":before_mass,"after_mass":after_mass,
            "positive_coefficients":supported,"mean_before_neff":before_neff/supported.max(1)as f64,"mean_after_neff":after_neff/supported.max(1)as f64}));
    }
    let planes=candidate.finish(&mut Workspace::new(sizes));
    if mode=="all-one"{ensure!(same(&planes,&baseline.finish(&mut Workspace::new(sizes))),"all-one CFA is not exact");}
    Ok(json!({"mode":mode,"state_held_exact":true,"bands":diagnostics,"output":write_image(folder,mode,&planes)?}))
}

#[test]
fn footprint_and_fallback_mechanics(){
    // Actual impulse coefficient support independently checks bit-union propagation,
    // including odd extents, decimation phase, and replicated borders.
    for(w,h)in [(17,19),(32,32)]{let sizes=level_sizes(w,h,2);
        for point in [0,w-1,w*(h-1),w*h-1,(h/2)*w+w/2]{let mut leaf=vec![0u8;w*h];leaf[point]=1;
            let sets=coefficient_sets(&leaf,&sizes);let mut impulse=vec![0.;w*h];impulse[point]=1.;
            let mut p=strehl_core::pyramid::Pyramid::zeros(&sizes);p.build(&impulse,&mut Workspace::new(&sizes));
            for k in 0..sets.len(){assert_eq!(sets[k].iter().map(|v|*v!=0).collect::<Vec<_>>(),
                p.level(k).iter().map(|v|*v!=0.).collect::<Vec<_>>(),"coefficient footprint differs");}}
    }
}

fn export_operator_support(out:&Path)->Result<Value>{
    let mut records=Vec::new();
    for(w,h)in [(9usize,11usize),(32,32)]{let fine=LevelSize{width:w,height:h};let coarse=fine.reduced();
        for operation in ["reduce","expand"]{
            let(input,output)=if operation=="reduce"{(fine,coarse)}else{(coarse,fine)};
            let mut support=Vec::with_capacity(input.pixels()*output.pixels());
            for point in 0..input.pixels(){let mut impulse=vec![0.;input.pixels()];impulse[point]=1.;let mut result=vec![0.;output.pixels()];
                if operation=="reduce"{reduce(&impulse,input,&mut result,&mut vec![0.;output.width*input.height]);}
                else{expand(&impulse,input,&mut result,output,&mut vec![0.;output.width*input.height]);}
                support.extend(result.iter().map(|v|u8::from(*v>0.)));
            }
            let file=format!("support-{operation}-{w}x{h}.u8");save_u8(&out.join(&file),&support)?;
            records.push(json!({"operation":operation,"fine_size":[w,h],"input_size":[input.width,input.height],
                "output_size":[output.width,output.height],"shape":[input.pixels(),output.pixels()],"file":file}));
        }
    }Ok(json!(records))
}

#[test]
#[ignore = "root-owned generated fixture/output paths and bounded GPU job required"]
fn generated_consumer_screen(){run().unwrap();}
fn run()->Result<()>{
    let input=PathBuf::from(std::env::var_os("STREHL_OPTICAL_SUPPORT_INPUT").expect("root-owned input required"));
    let out=PathBuf::from(std::env::var_os("STREHL_OPTICAL_SUPPORT_OUT").expect("root-owned output required"));std::fs::create_dir(&out)?;
    let operator_support=export_operator_support(&out)?;
    let manifest:Value=serde_json::from_slice(&std::fs::read(input.join("manifest.json"))?)?;
    ensure!(manifest["status"]=="PREPARED"&&manifest["native_size"]==json!([96,96])&&manifest["frames"]==5,"wrong fixture manifest");
    ensure!(align_cmd::fullres_gather_enabled()&&gatefloor::enabled()&&align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded
        &&align_cmd::native_gpu_integration::gpu_gather_enabled()?,"actual rounded GPU/probed route required");
    ensure!(strehl_core::pyramid::fine_support_candidate::environment_mode()==strehl_core::pyramid::fine_support_candidate::Mode::Off
        &&align_cmd::native_gpu_integration::ca_stage::mode()?==align_cmd::native_gpu_integration::ca_stage::Mode::Current
        &&std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none(),"other candidate enabled");
    let cfg=MergeConfig::default();ensure!(cfg.select==SelectMode::SoftPower&&cfg.admission==AdmissionMode::HardFloor
        &&cfg.base==BaseBand::Mean&&cfg.fallback==Fallback::Mean&&cfg.hull==Hull::InputRange
        &&cfg.mean_coarse==0&&cfg.significance_scale==0.,"unexpected baseline merge config");
    let noise=strehl_core::profile::noise_model_for("ILCE-7CM2",Some(100.),levels());ensure!(noise.is_trustworthy()&&noise.prnu().is_none(),"wrong noise scope");
    let sizes=level_sizes(32,32,cfg.bands);ensure!(sizes==vec![LevelSize{width:32,height:32},LevelSize{width:16,height:16},LevelSize{width:8,height:8}],"wrong actual levels");
    let mut scenes=Vec::new();
    for name in ["flat","transparent","opaque"]{
        let folder=input.join(name);let output=out.join(name);std::fs::create_dir(&output)?;let fs=frames(&folder,&noise)?;
        let full=fs[0].geometry();let domain=PyramidDomain::cropped(full,crop())?;
        let entries=fs.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes()as u64)).collect::<Vec<_>>();
        let map=WarpMap::new(strehl_core::warpmap::Provenance{stack:StackIdentity::from_entries("optical-support-veto-generated",&entries),
            strategy:"supplied identity".into(),heldout_px:None,cycle_floor_px:None,reference:0,note:"oracle optical source support only".into()},
            full,Resampler::CatmullRom,vec![FrameWarp::Placed(Similarity::IDENTITY);N]);
        struct Source<'a>(&'a[Frame]);impl PyramidFrameSource for Source<'_>{fn len(&self)->usize{self.0.len()}fn decode(&self,i:usize)->Result<Frame>{Ok(self.0[i].clone())}}
        let source=Source(&fs);let mut baseline=BandWorker::new(domain,cfg);let mut retained=Vec::new();let mut evidence=Vec::new();
        let q=masks(&folder,name=="opaque",&sizes)?;
        for(i,f)in fs.iter().enumerate(){let original=hash16(&f.data);validate_pyramid_frame(f,full,i)?;
            let id=strehl_raw::identity(&f.path);ensure!(strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?.is_none(),"unexpected CA profile");
            ensure!(phase_packed_rgb::full_stack::full_source_supported(Similarity::IDENTITY,full,crop(),None),"unsupported identity pull");
            ensure!(baseline.fold(&source,i,f.levels,&noise,Some(&map),None)?,"generated source refused");
            for(c,(dx,dy))in [(0,0),(1,0),(0,1),(1,1)].into_iter().enumerate(){for y in 0..32{for x in 0..32{
                let expected=f.active_row(16+2*y+dy)[16+2*x+dx]as f32-512.;
                ensure!(baseline.planes[c][y*32+x].to_bits()==expected.max(0.).to_bits(),"identity native gather altered a known CFA site");}}}
            ensure!(!baseline.beta.is_empty()&&baseline.beta.iter().all(|v|v.is_finite()&&*v>0.),"actual green probe absent");
            let fields=core::canonical_fields(&baseline.merge,&baseline.fws,Some(&baseline.beta));
            for k in 0..fields.weights.len(){save_f32(&output.join(format!("source-{i}-b{k}-weights.f32")),&fields.weights[k])?;
                save_u8(&output.join(format!("source-{i}-b{k}-q.u8")),&q[i][k])?;}
            ensure!(hash16(&f.data)==original,"original u16 changed");
            evidence.push(json!({"source_sha256":original,"gather_sha256":baseline.planes.iter().map(|p|hash32(p)).collect::<Vec<_>>(),
                "guide_sha256":hash32(&baseline.luma),"variance_sha256":hash32(&baseline.var),"beta":baseline.beta,"identity_gather_exact":true}));
            retained.push(Retained{planes:baseline.planes.clone(),fields});
        }
        let current=write_image(&output,"current",&baseline.merge.finish(&mut Workspace::new(&sizes)))?;
        let mut arms=Vec::new();for mode in ["all-one","oracle","permuted"]{let result=arm(&retained,&q,&sizes,cfg,mode,&baseline.merge,&output)?;
            if mode=="all-one"||name!="opaque"{ensure!(result["output"]==current,"literal/null output is not bit exact");}arms.push(result);}
        let zero_q=q.iter().map(|source|source.iter().map(|band|vec![0u8;band.len()]).collect::<Vec<_>>()).collect::<Vec<_>>();
        let no_clean=arm(&retained,&zero_q,&sizes,cfg,"no-clean",&baseline.merge,&output)?;
        ensure!(no_clean["output"]==current,"all-zero Q failed canonical fallback");arms.push(no_clean);
        scenes.push(json!({"name":name,"current":current,"arms":arms,"frames":evidence}));
    }
    let noise_parameters=[CfaPlane::R,CfaPlane::G1,CfaPlane::G2,CfaPlane::B].map(|p|{let n=noise.plane(p);
        json!({"gain_dn_per_e":n.gain_dn_per_e,"read_noise_e":n.read_noise_e})});
    let result=json!({"status":"CONSUMED","photographic_replay_admitted":false,"scenes":scenes,"operator_support":operator_support,"level_sizes":[[32,32],[16,16],[8,8]],
        "scope":"Generated optical-support mechanism only; quality/exercise decision requires independent scoring","original_shape":[96,96],"crop_plane":[8,8,32,32],
        "noise_parameters_rg1g2b":noise_parameters,"iso":100,"noise_scope":"Same injected camera profile synthesizes and gates; no independent calibration claim"});
    save_json(&out.join("result.json"),&result)?;eprintln!("OPTICAL_SUPPORT_CONSUMED");Ok(())
}
