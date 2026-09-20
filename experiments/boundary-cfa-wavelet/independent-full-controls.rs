// Added mechanical scope only; old failed quality controls remain untouched.
use super::*;
use serde_json::{json,Value};
use strehl_core::{align::SimilarityParams,noise::Levels,plane::QuadSource,
    optics::{OpticalProfile,A7C2_FE100GM_2XTC_X4CPL_RADIAL}};
use strehl_native_gpu_gather::{GpuGather,Input,Schedule};
use strehl_raw::Region;

fn magnitude(z:Complex)->f64 {(z.re as f64).hypot(z.im as f64)}
fn extent_controls()->Value {
    let p=BoundaryPlan::full_vitamin_c();assert_eq!((p.input_width,p.input_height,p.padded_width,p.padded_height,p.left,p.top),(3460,2306,4096,4096,318,895));
    assert_eq!(p.depth(),12);assert!(BoundaryPlan::new(3460,2306).is_err());
    assert!(dimensions_scoped(4096,4096,4096*4096,false).is_err());assert!(dimensions_scoped(4096,4096,4096*4096,true).is_ok());
    assert!(dimensions_scoped(8192,4096,8192*4096,true).is_err());
    let mut rows=Vec::new();
    for(w,h)in[(4096,1),(1,4096)] {
        let v=(0..w*h).map(|i|Complex{re:((i*17%53) as f32-26.0)/17.0,im:((i*19%43) as f32-21.0)/29.0}).collect::<Vec<_>>();
        let sizes=level_rectangles_scoped(w,h,true).unwrap();assert_eq!(sizes.len(),12);assert_eq!(sizes.last(),Some(&if w==1{[1,2]}else{[2,1]}));
        let z=transform_all(&v,w,h,false,true).unwrap();let back=transform_all(&z,w,h,true,true).unwrap();
        let peak=v.iter().copied().map(magnitude).fold(1.0,f64::max);let err=v.iter().zip(&back).map(|(a,b)|magnitude(Complex{re:a.re-b.re,im:a.im-b.im})).fold(0.0,f64::max);
        let ein=v.iter().copied().map(|z|magnitude(z).powi(2)).sum::<f64>();let eout=z.iter().copied().map(|z|magnitude(z).powi(2)).sum::<f64>();
        assert!(err<=5e-5*peak && (ein-eout).abs()/ein<=5e-5);
        let bands=subbands_scoped(w,h,true).unwrap();assert_eq!(bands.len(),12);let mut seen=vec![0usize;w*h];seen[0]=1;
        for(band,level)in bands.iter().zip(0..12){assert_eq!(band.level,level);assert_eq!(band.direction,if w==1{2}else{0});for&i in &band.positions{seen[i]+=1;}}
        assert!(seen.iter().all(|&n|n==1));let dc=forward_real_scoped(&vec![1.0;w*h],w,h,true).unwrap();let nondc=dc.iter().skip(1).copied().map(|z|magnitude(z).powi(2)).fold(0.0,f64::max);assert!(nondc<=1e-6);
        rows.push(json!({"shape":[w,h],"levels":12,"roundtrip_max":err,"parseval_relative":(ein-eout).abs()/ein,"non_dc_max_energy":nondc,"packing_exact":true}));
    }
    json!({"full_plan":[3460,2306,4096,4096,318,895],"large_arrays_allocated":false,"one_axis_controls":rows})
}

fn hash_bytes(v:&[u16])->String {let mut h=Sha256::new();for x in v{h.update(x.to_le_bytes());}h.finalize().iter().map(|v|format!("{v:02x}")).collect()}
fn mix(mut x:u32)->u32{x^=x>>16;x=x.wrapping_mul(0x7feb352d);x^=x>>15;x=x.wrapping_mul(0x846ca68b);x^(x>>16)}
fn frozen_fixture(k:usize,noise:&NoiseModel,warp:Similarity)->Frame {
    const W:usize=320;const H:usize=288;let gain=[f32::from_bits(1070374912),1.0,f32::from_bits(1076715520)];
    let levels=Levels{black:512.0,white:15360.0};let amplitude=(2.0*noise.sigma(CfaPlane::R,0.30*levels.range()/gain[0])*gain[0]/levels.range()) as f64;
    let active=Region{x:7,y:11,width:W,height:H};let stride=W+29;let height=H+29;
    let mut f=Frame{data:vec![64999;stride*height],stride,buffer_height:height,active,levels,iso:Some(100.0),wb_coeffs:[gain[0],gain[1],gain[2],f32::NAN],
        xyz_to_cam_rgbe:[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0;3]],color_matrices:Vec::new(),camera:"ILCE-7CM2".into(),
        path:std::env::current_dir().unwrap().join(format!("nonexistent-boundary-wavelet-{k}.ARW"))};
    assert!(!f.path.exists());let p=warp.to_params();let a=1.0+p.g;let b=p.rot;let det=a*a+b*b;let tau=std::f64::consts::TAU;
    for y in 0..H{for x in 0..W{
        let sx=x as f64-W as f64/2.0-2.0*p.ax;let sy=y as f64-H as f64/2.0-2.0*p.ay;let wx=(a*sx+b*sy)/det+W as f64/2.0;
        let(c,plane)=match(x%2,y%2){(0,0)=>(0,CfaPlane::R),(1,0)=>(1,CfaPlane::G1),(0,1)=>(1,CfaPlane::G2),_=>(2,CfaPlane::B)};
        let sigma=1.3*(k as f64-2.0).abs();let rad=0.30+if c==0{amplitude*(-0.5*(tau*46.0/256.0*sigma).powi(2)).exp()*(tau*46.0*wx/256.0+0.37).cos()}else{0.0};
        let signal=(rad*levels.range() as f64/gain[c] as f64) as f32;
        let s=x as u32^((y as u32)<<16)^(k as u32).wrapping_mul(0x9e3779b9)^0x31d59a67;let u=(mix(s) as f64+0.5)/4294967296.0;let v=(mix(s^0xa73126bd) as f64+0.5)/4294967296.0;
        let gaussian=(-2.0*u.ln()).sqrt()*(tau*v).cos();let observed=512.0+signal as f64+gaussian*noise.sigma(plane,signal) as f64;
        f.data[(active.y+y)*stride+active.x+x]=observed.round() as u16;
    }}f
}
fn frozen_generated()->Value {
    let noise=profile::noise_model_for("ILCE-7CM2",Some(100.0),Levels{black:512.0,white:15360.0});let warp=gatefloor::gpu_warp();
    let frames=(0..5).map(|k|frozen_fixture(k,&noise,warp)).collect::<Vec<_>>();let hashes=frames.iter().map(|f|hash_bytes(&f.data)).collect::<Vec<_>>();
    assert_eq!(hashes,vec!["693f258df81f1484273eefc4cb6c6a737b307a856565e5f6fa998927dd9aa7b9","16b911c744223ade7f9cd73c7de917471c330116c3b63fff25e9b6d613005ea2","84af728c362760fd490aaa0c6c3bd513639fdd131fe02865bb2ae41981938e69","385765c36e916c3631d4cf4b15f42f5d36d7548281e4276bd685aa04039998cf","f3c148c7b6312f6660eec741a30336d4ed105d7108dc03e7341e1852362d50ea"]);
    let crop=align_cmd::CropRect{x:7,y:9,width:113,height:101};let c=compare_generated(&frames,crop,&vec![warp;5],&noise,true).unwrap();
    let actual=[hash32(&c.baseline_rgb),hash32(&c.candidate_rgb)];assert_eq!(actual,["76b42e87ca9a53011af3f8a9d6d81b0925534c9075d67476be3c192a57c8be40","893ef6e6fbf4ab76e42e94a8506cfc7ff4bf94c8d33bd2e86142a2a7335a22b7"]);
    for(f,h)in frames.iter().zip(&hashes){assert_eq!(&hash_bytes(&f.data),h);}
    json!({"source_hashes":hashes,"baseline_candidate_rgb_hashes":actual,"previous_failed_result_exact":true})
}

fn headroom()->Value {
    let mut f=gatefloor::gpu_fixture(70,50,1,1);let before=hash_bytes(&f.data);let n=4*f.geometry().pixels();let zero=vec![0.0;n];
    let i=f.active.y*f.stride+f.active.x;
    for value in [0u16,65535]{f.data[i]=value;assert!(noisy_source(&f,&zero,0).is_err());}
    f.data[i]=15424;let legal=noisy_source(&f,&zero,0).unwrap();assert_eq!(legal.data,f.data);assert!(legal.data[i] as f32>f.levels.white);
    let mut invalid=zero.clone();invalid[0]=-1.0;assert!(noisy_source(&f,&invalid,0).is_err());invalid[0]=f32::NAN;assert!(noisy_source(&f,&invalid,0).is_err());
    assert_ne!(hash_bytes(&f.data),before);let original=hash_bytes(&f.data);let variance=vec![4.0;n];let noisy=noisy_source(&f,&variance,79).unwrap();assert_eq!(hash_bytes(&f.data),original);
    assert_eq!(noisy.path,f.path);assert_eq!(noisy.active,f.active);assert_eq!(noisy.stride,f.stride);assert_eq!(noisy.wb_coeffs[..3],f.wb_coeffs[..3]);assert_eq!(noisy.levels,f.levels);
    json!({"zero_and_max_refused":true,"above_sensor_white_not_silently_clamped":true,"invalid_variance_refused":true,"draw_metadata_and_input_preserved":true})
}

fn binding_and_ca()->Value {
    let ca=A7C2_FE100GM_2XTC_X4CPL_RADIAL;let full=PlaneGeometry{width:3516,height:2344};let crop=align_cmd::CropRect{x:28,y:19,width:3460,height:2306};
    full_gather_binding(full,crop,Similarity::IDENTITY,Some(&ca)).unwrap();assert!(full_gather_binding(full,crop,Similarity::IDENTITY,None).is_err());
    assert!(full_gather_binding(PlaneGeometry{width:3515,height:2344},crop,Similarity::IDENTITY,Some(&ca)).is_err());
    assert!(full_gather_binding(full,align_cmd::CropRect{x:29,..crop},Similarity::IDENTITY,Some(&ca)).is_err());
    let wrong=OpticalProfile{key:"wrong-full-profile",..ca};assert!(full_gather_binding(full,crop,Similarity::IDENTITY,Some(&wrong)).is_err());
    let outside=Similarity::from_params(SimilarityParams{ax:10000.0,..Default::default()});assert!(full_gather_binding(full,crop,outside,Some(&ca)).is_err());
    let f=gatefloor::gpu_fixture(70,50,1,1);let original=hash_bytes(&f.data);let geom=f.geometry();let t=gatefloor::gpu_warp();
    let noise=profile::noise_model_for("ILCE-7CM2",Some(100.0),f.levels);let noisy=noisy_source(&f,&original_variances(&f,&noise).unwrap(),57).unwrap();
    let mut gpu=GpuGather::new_with_schedule(Schedule::Device256).unwrap();let mut changed=[0usize;3];let mut rows=Vec::new();
    for(label,frame)in[("signal",&f),("source-noise-draw",&noisy)] {
        let mut cpu=frame.clone();let oracle=align_cmd::gpu_cpu_oracle(&mut cpu,t,geom,Some(ca),false).unwrap();
        let mut none=frame.clone();let no_ca=align_cmd::gpu_cpu_oracle(&mut none,t,geom,None,false).unwrap();
        assert_ne!(oracle.pulls[0],no_ca.pulls[0]);assert_ne!(oracle.pulls[2],no_ca.pulls[2]);assert_eq!(oracle.pulls[1],no_ca.pulls[1]);
        let input=Input{data:&frame.data,stride:frame.stride,active:[frame.active.x,frame.active.y,frame.active.width,frame.active.height],geom,black:frame.levels.black,
            gain:oracle.gain,inverse_gain:oracle.inverse_gain,pulls:oracle.pulls,green_only:false,malvar:true,resampler:Resampler::CatmullRom};
        let output=gpu.run(&input).unwrap();assert_eq!(output.schedule,Schedule::Device256);assert!(output.coordinate_fallback.is_none());
        assert_eq!((output.width,output.height),(70,50));let mut covered=0;
        for y in 0..50{for x in 0..70{
            let j=y*70+x;let word=output.packed[j/2];let code=((word>>(16*(x%2)))&65535) as u16;let valid=(output.coverage[j/2]&(1<<(x%2)))!=0;
            assert_eq!(valid,oracle.coverage[j]);assert_eq!(code,cpu.sample(x,y));covered+=valid as usize;
            let c=match(x%2,y%2){(0,0)=>0,(1,1)=>2,_=>1};if valid && no_ca.coverage[j] && code!=none.sample(x,y){changed[c]+=1;}
        }}assert!(covered>0);rows.push(json!({"source":label,"covered":covered,"cpu_gpu_code_and_support_exact":true}));
    }
    assert!(changed[0]>0 && changed[2]>0);assert_eq!(changed[1],0);assert_eq!(hash_bytes(&f.data),original);
    json!({"full_binding_and_refusals":true,"actual_profile_key":ca.key,"small_actual_ca_changed_rgb_sites":changed,"signal_and_noisy_source":rows,"no_calibration_claim":true})
}

fn writer()->Value {
    let out=PathBuf::from(std::env::var_os("STREHL_BOUNDARY_CFA_WAVELET_OUT").unwrap()).with_extension("full-mechanical");std::fs::create_dir(&out).unwrap();
    let crop=align_cmd::CropRect{x:3,y:5,width:29,height:17};let levels=Levels{black:512.0,white:15360.0};let gain=[f32::from_bits(1070374912),1.0,f32::from_bits(1076715520)];let wb=[gain[0],1.0,gain[2],f32::NAN];
    let planes=(0..4).map(|p|(0..crop.width*crop.height).map(|i|1200.0+((i*47+p*109)%8000) as f32).collect::<Vec<_>>()).collect::<Vec<_>>();let before=planes.iter().map(|p|hash32(p)).collect::<Vec<_>>();
    let matrix=color::camera_to_srgb([[0.746,-0.2365,-0.0588],[-0.5687,1.3442,0.2474],[-0.0624,0.1156,0.6584]]).unwrap().with_saturation(levels,gain,1.0);
    let mut dev=image_out::OutputSpace::Srgb.develop(Some(matrix));dev.tone=Some(image_out::Tone{black:0.090420,white:0.914606,contrast:0.55});dev.exposure_gain=1.0;
    let path=out.join("held-writer.tiff");phase_packed_rgb::full_stack::write_planes(&path,&planes,crop,levels,wb,&dev).unwrap();
    let camera=camera_rgb(&planes,crop.width,crop.height,levels,wb).unwrap();assert!(camera.iter().all(|v|v.is_finite()));let expected=camera.chunks_exact(3).flat_map(|p|image_out::develop_pixel([p[0],p[1],p[2]],&dev)).collect::<Vec<_>>();
    let mut untoned=dev.clone();untoned.tone=None;untoned.wants_tone=false;assert!(camera.chunks_exact(3).any(|p|image_out::develop_pixel([p[0],p[1],p[2]],&dev)!=image_out::develop_pixel([p[0],p[1],p[2]],&untoned)));
    let mut decoder=tiff::decoder::Decoder::new(std::fs::File::open(&path).unwrap()).unwrap();assert_eq!(decoder.dimensions().unwrap(),(58,34));assert_eq!(decoder.colortype().unwrap(),tiff::ColorType::RGB(16));
    let tiff::decoder::DecodingResult::U16(actual)=decoder.read_image().unwrap()else{panic!("writer did not emit u16")};assert_eq!(actual,expected);assert!(!decoder.more_images());
    assert_eq!(planes.iter().map(|p|hash32(p)).collect::<Vec<_>>(),before);json!({"held_tone_matrix_native_samples_exact":actual.len(),"tone_live":true,"source_immutable":true})
}

#[test]
fn independent_full_mechanical_controls() {
    let extent=extent_controls();let simulation=headroom();let ca=binding_and_ca();let regression=frozen_generated();let written=writer();
    eprintln!("BOUNDARY_CFA_FULL_MECHANICAL {}",json!({"extent":extent,"source_simulation":simulation,"ca_binding":ca,"generated_regression":regression,"writer":written,"previous_quality_admission":false,"observational_scope_only":true}));
}
