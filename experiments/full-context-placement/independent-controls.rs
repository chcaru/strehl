// Independent generated controls. Root executes; see independent-design.md.
// This module is included as a child of align_cmd::local_placement.
use super::{prepare_with_config, Configuration};
use crate::align_cmd::{self, CropRect, DirectPlaneMode, WarpScratch};
use serde_json::{json, Value};
use strehl_core::align::{Cx, Resampler, Similarity};
use strehl_core::noise::Levels;
use strehl_core::optics::{OpticalProfile, A7C2_FE100GM_2XTC_X4CPL};
use strehl_core::plane::PlaneGeometry;
use strehl_core::warpmap::{FrameWarp, Provenance, StackIdentity, WarpMap};
use strehl_raw::{Frame, Region};

const SITES: [(usize, usize); 4] = [(0, 0), (1, 0), (0, 1), (1, 1)];
const SUPPORT: [usize; 4] = [109, 83, 392, 392];
const DELTA: [f64; 2] = [3.125, -1.875];

fn geom() -> PlaneGeometry { PlaneGeometry { width: 340, height: 290 } }
fn crop() -> CropRect { CropRect { x: 29, y: 21, width: 281, height: 237 } }
fn transform() -> Similarity {
    Similarity { a: Cx::new(1.001, 0.006), b: Cx::new(0.375, -0.425) }
}
fn ca() -> OpticalProfile {
    OpticalProfile { eps_r: 0.03, eps_b: Some(-0.017), translation: (0.17, -0.13),
        key: "INDEPENDENT-LOCAL-PLACEMENT-CONTROL", ..A7C2_FE100GM_2XTC_X4CPL }
}
fn channel(x: usize, y: usize) -> usize {
    match (x & 1, y & 1) { (0, 0) => 0, (1, 1) => 2, _ => 1 }
}
fn noise(x: usize, y: usize) -> i32 {
    let mut z = (x as u32).wrapping_mul(0x9e3779b9)
        ^ (y as u32).wrapping_mul(0x85ebca6b) ^ 0x67d41731;
    z ^= z >> 16; z = z.wrapping_mul(0x7feb352d);
    z ^= z >> 15; z = z.wrapping_mul(0x846ca68b); z ^= z >> 16;
    (z % 257) as i32 - 128
}
fn radiance(c: usize, x: f64, y: f64) -> f64 {
    [5000.0, 9000.0, 12000.0][c]
        + [3.0, 5.0, 2.0][c] * x + [7.0, 2.0, 9.0][c] * y
}
fn fixture(kind: &str) -> Frame {
    let g = geom();
    let active = Region { x: 7, y: 11, width: 2 * g.width, height: 2 * g.height };
    let stride = active.x + active.width + 16;
    let height = active.y + active.height + 9;
    let mut f = Frame {
        data: vec![65001; stride * height], stride, buffer_height: height, active,
        levels: Levels { black: 512.0, white: 30000.0 }, iso: Some(100.0),
        wb_coeffs: [1.7, 1.0, 2.3, f32::NAN],
        xyz_to_cam_rgbe: [[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0;3]],
        color_matrices: Vec::new(), camera: "generated-control".into(),
        path: std::env::current_dir().unwrap().join("placement-generated-1.ARW"),
    };
    for y in 0..active.height { for x in 0..active.width {
        let v = match kind {
            "affine" => radiance(channel(x,y), x as f64, y as f64) as u16,
            "constant" => 5000,
            "noise" => (5000 + noise(x,y)) as u16,
            _ => panic!("unknown generated fixture"),
        };
        f.data[(active.y+y)*stride+active.x+x] = v;
    }}
    f
}
fn config_value(f: &Frame, t: Similarity, delta: [f64; 2]) -> Value {
    let bits=[t.a.re,t.a.im,t.b.re,t.b.im].map(|v|format!("{:016x}",v.to_bits()));
    json!({"schema_version":1, "source_dir":f.path.parent().unwrap(),
        "expected_frame_count":3, "native_geometry":[2*geom().width,2*geom().height],
        "support_native":SUPPORT, "taper_native":32,
        "frames":[{"file_name":f.path.file_name().unwrap().to_str().unwrap(),
            "transform_bits":bits,
            "delta_source_native":delta}]})
}
fn config(f: &Frame, t: Similarity, delta: [f64; 2]) -> Configuration {
    Configuration::from_json(&config_value(f,t,delta).to_string()).unwrap()
}
fn empty_planes(offsets: &[(usize,usize)]) -> Vec<Vec<f32>> {
    vec![vec![-12345.0; crop().width*crop().height];offsets.len()]
}
fn uniform(f: &Frame, t: Similarity, profile: Option<OpticalProfile>, offsets: &[(usize,usize)])
    -> Vec<Vec<f32>>
{
    let mut source = f.clone();
    let mut scratch = WarpScratch::new(geom());
    let mut planes = empty_planes(offsets);
    // Existing CPU source reconstruction, sampling and rounded sink. This does
    // not enter the new local placement wrapper or its coordinate code.
    align_cmd::warp_frame_fullres_with_sink_impl::<false,_>(
        &mut source,t,geom(),Resampler::CatmullRom,&mut scratch,
        |_,site,dst,coverage,inv,black,execution| {
            if let Some(i) = offsets.iter().position(|&p|p == site) {
                align_cmd::write_fullres_plane(&mut planes[i],geom(),crop(),dst,coverage,
                    inv,black,DirectPlaneMode::Rounded,execution)
            } else { Ok(0) }
        },Some(profile)).unwrap();
    assert_eq!(source.data,f.data,"oracle sink must preserve its CFA source");
    planes
}
fn corrected(f: &Frame, t: Similarity, profile: Option<OpticalProfile>, cfg: &Configuration,
    offsets: &[(usize,usize)], base: &[Vec<f32>]) -> (Vec<Vec<f32>>,usize)
{
    let before = f.data.clone();
    let mut out = base.to_vec();
    let prepared = prepare_with_config(f,t,geom(),crop(),offsets,DirectPlaneMode::Rounded,
        cfg,profile.as_ref()).unwrap();
    let touched = prepared.map_or(0,|p|p.apply(f,&mut out,DirectPlaneMode::Rounded).unwrap());
    assert_eq!(f.data,before,"local correction altered stored original CFA");
    (out,touched)
}
fn weight(x: f64, y: f64) -> f64 {
    // Independent scalar definition, deliberately not Configuration::weight_at.
    let [left,top,width,height] = SUPPORT;
    let edge = |p:f64,lo:usize,n:usize| {
        let d = (p-lo as f64).min((lo+n-1) as f64-p);
        let u = (d/32.0).clamp(0.0,1.0);
        u*u*(3.0-2.0*u)
    };
    edge(x,left,width)*edge(y,top,height)
}
fn point(c: usize, x: f64, y: f64, w: f64, delta: [f64;2], profile: Option<OpticalProfile>)
    -> (f64,f64)
{
    let t=transform(); let g=geom(); let cx=g.width as f64; let cy=g.height as f64;
    let (u,v)=(x-cx,y-cy);
    let px=t.a.re*u-t.a.im*v+2.0*t.b.re+delta[0]*w;
    let py=t.a.im*u+t.a.re*v+2.0*t.b.im+delta[1]*w;
    let (s,tx,ty)=match (c,profile) {
        (0,Some(p)) => (1.0+p.eps_r,2.0*p.translation.0,2.0*p.translation.1),
        (2,Some(p)) => (1.0+p.eps_b.unwrap(),2.0*p.translation.0,2.0*p.translation.1),
        _ => (1.0,0.0,0.0),
    };
    (cx+s*px+tx,cy+s*py+ty)
}
fn same_bits(a: &[Vec<f32>], b: &[Vec<f32>]) -> bool {
    a.iter().flatten().zip(b.iter().flatten()).all(|(x,y)|x.to_bits()==y.to_bits())
}

#[test]
fn independent_local_placement_disabled_consumer_is_exact() {
    assert!(std::env::var_os(super::ENV).is_none(),"run generated controls with local-placement environment cleared");
    let mut f=fixture("noise"); let before=f.data.clone(); let t=transform();
    let expected=uniform(&f,t,None,&SITES);
    let mut actual=empty_planes(&SITES); let mut scratch=WarpScratch::new(geom());
    align_cmd::warp_frame_fullres_into_planes::<false>(&mut f,t,geom(),Resampler::CatmullRom,
        &mut scratch,crop(),&SITES,&mut actual,DirectPlaneMode::Rounded).unwrap();
    assert!(same_bits(&actual,&expected)); assert_eq!(f.data,before);
    let mut greens=empty_planes(&SITES[1..3]);
    align_cmd::warp_frame_fullres_into_planes::<true>(&mut f,t,geom(),Resampler::CatmullRom,
        &mut scratch,crop(),&SITES[1..3],&mut greens,DirectPlaneMode::Rounded).unwrap();
    assert!(same_bits(&greens,&[expected[1].clone(),expected[2].clone()]));
    assert_eq!(f.data,before);
}

#[test]
fn independent_local_placement_affine_direction_phase_taper_and_scope() {
    let f=fixture("affine"); let t=transform(); let profile=Some(ca());
    let base=uniform(&f,t,profile,&SITES);
    let zero=config(&f,t,[0.0,0.0]);
    let (unchanged,nzero)=corrected(&f,t,profile,&zero,&SITES,&base);
    assert_eq!(nzero,0); assert!(same_bits(&base,&unchanged));
    let cfg=config(&f,t,DELTA);
    let (out,touched)=corrected(&f,t,profile,&cfg,&SITES,&base);
    assert!(touched>0 && !same_bits(&base,&out),"treatment never reached a sample");
    let mut shifted=t;
    shifted.b.re+=DELTA[0]/2.0; shifted.b.im+=DELTA[1]/2.0;
    let full=uniform(&f,shifted,profile,&SITES);
    let mut outside=0usize; let mut core=0usize; let mut taper=0usize;
    let mut wrong_sign=0usize; let mut wrong_factor=0usize; let mut wrong_phase=0usize;
    let r=crop();
    for (slot,&(dx,dy)) in SITES.iter().enumerate() {
        for py in 0..r.height { for px in 0..r.width {
            let i=py*r.width+px;
            let x=(2*(r.x+px)+dx) as f64; let y=(2*(r.y+py)+dy) as f64;
            let w=weight(x,y); let c=channel(dx,dy);
            if w==0.0 { outside+=1; assert_eq!(out[slot][i].to_bits(),base[slot][i].to_bits()); }
            else {
                if w==1.0 {core+=1; assert_eq!(out[slot][i].to_bits(),full[slot][i].to_bits(),
                    "uniform-shift mismatch at {x},{y}, CFA slot {slot}");}
                else {taper+=1;}
                let (sx,sy)=point(c,x,y,w,DELTA,profile);
                let expected=(radiance(c,sx,sy).round()-512.0) as f32;
                assert!((out[slot][i]-expected).abs()<=1.0,
                    "affine coordinate error at {x},{y}, slot {slot}, weight {w}: {} != {expected}",out[slot][i]);
                let (rx,ry)=point(c,x,y,w,[-DELTA[0],-DELTA[1]],profile);
                wrong_sign+=usize::from((radiance(c,rx,ry).round()-512.0-out[slot][i] as f64).abs()>1.0);
                let (rx,ry)=point(c,x,y,w,[2.0*DELTA[0],2.0*DELTA[1]],profile);
                wrong_factor+=usize::from((radiance(c,rx,ry).round()-512.0-out[slot][i] as f64).abs()>1.0);
                if slot==1 {wrong_phase+=usize::from(out[1][i].to_bits()!=out[2][i].to_bits());}
            }
        }}
    }
    assert!(outside>10000 && core>10000 && taper>10000);
    assert!(wrong_sign>10000 && wrong_factor>10000 && wrong_phase>10000,
        "fixture did not distinguish direction, factor two, or green phases");
    let greens=&SITES[1..3];
    let green_base=vec![base[1].clone(),base[2].clone()];
    let (green_out,green_touched)=corrected(&f,t,profile,&cfg,greens,&green_base);
    assert!(green_touched>0);
    assert!(same_bits(&green_out,&[out[1].clone(),out[2].clone()]),"probe greens use different correction");
    let mut absent=f.clone(); absent.path=absent.path.with_file_name("placement-generated-2.ARW");
    let (unchanged,nabsent)=corrected(&absent,t,profile,&cfg,&SITES,&base);
    assert_eq!(nabsent,0); assert!(same_bits(&base,&unchanged));
    eprintln!("independent local affine: outside={outside}, core={core}, taper={taper}, wrong-sign={wrong_sign}, wrong-factor={wrong_factor}, swapped-greens={wrong_phase}");
}

#[test]
fn independent_local_placement_constant_and_flat_noise_control() {
    let t=transform(); let profile=Some(ca());
    for kind in ["constant","noise"] {
        let f=fixture(kind); let cfg=config(&f,t,DELTA);
        let base=uniform(&f,t,profile,&SITES);
        let (out,touched)=corrected(&f,t,profile,&cfg,&SITES,&base);
        assert!(touched>0);
        let uniform_noise = if kind=="noise" {
            let mut shifted=t;
            shifted.b.re+=DELTA[0]/2.0; shifted.b.im+=DELTA[1]/2.0;
            Some(uniform(&f,shifted,profile,&SITES))
        } else { None };
        let mut core_compared=0usize; let mut core_base_mismatches=0usize;
        let mut sum=0.0; let mut sumsq=0.0; let mut count=0usize; let mut changed=0usize;
        let r=crop();
        for (slot,&(dx,dy)) in SITES.iter().enumerate() {
            for py in 0..r.height {for px in 0..r.width {
                let i=py*r.width+px; let x=(2*(r.x+px)+dx) as f64;let y=(2*(r.y+py)+dy) as f64;
                let w=weight(x,y); assert!(out[slot][i].is_finite());
                if w==0.0 {assert_eq!(out[slot][i].to_bits(),base[slot][i].to_bits());}
                if w==1.0 {
                    if let Some(expected)=uniform_noise.as_ref() {
                        core_compared+=1;
                        core_base_mismatches+=usize::from(out[slot][i].to_bits()!=base[slot][i].to_bits());
                        assert_eq!(out[slot][i].to_bits(),expected[slot][i].to_bits(),
                            "noisy uniform-shift mismatch at {x},{y}, CFA slot {slot}");
                    }
                }
                if w>0.0 && w<1.0 {
                    let v=out[slot][i] as f64-4488.0;sum+=v;sumsq+=v*v;count+=1;
                    changed+=usize::from(out[slot][i].to_bits()!=base[slot][i].to_bits());
                    if kind=="constant" {assert_eq!(out[slot][i],4488.0);}
                }
            }}
        }
        assert!(count>10000);
        if kind=="noise" {
            assert!(core_compared>10000 && core_base_mismatches>10000,
                "noisy core did not distinguish corrected sampling from the unchanged gather");
            eprintln!("independent local noisy core: compared={core_compared}, unchanged-gather mismatches={core_base_mismatches}");
            assert!(changed>10000,"noise fixture does not exercise fractional correction");
            let variance=sumsq/count as f64-(sum/count as f64).powi(2);
            let values=(0..2*geom().height).flat_map(|y|(0..2*geom().width).map(move |x|noise(x,y) as f64)).collect::<Vec<_>>();
            let mean=values.iter().sum::<f64>()/values.len() as f64;
            let input=values.iter().map(|v|(v-mean).powi(2)).sum::<f64>()/values.len() as f64;
            assert!(variance>0.0 && variance<=4.0*input,"flat noise variance sanity bound failed");
            eprintln!("independent local flat: transition samples={count}, changed={changed}, output/input variance={}",variance/input);
        }
    }
}

#[test]
fn independent_local_placement_refuses_mismatched_or_nonfinite_geometry() {
    let f=fixture("affine"); let t=transform(); let profile=Some(ca());
    let cfg=config(&f,t,DELTA);
    let bad_t=Similarity {b:Cx::new(t.b.re+0.125,t.b.im),..t};
    assert!(prepare_with_config(&f,bad_t,geom(),crop(),&SITES,DirectPlaneMode::Rounded,&cfg,profile.as_ref()).is_err());
    for bad in [f64::NAN,f64::INFINITY,f64::NEG_INFINITY] {
        let mut v=config_value(&f,t,DELTA);
        v["frames"][0]["transform_bits"][0]=json!(format!("{:016x}",bad.to_bits()));
        assert!(Configuration::from_json(&v.to_string()).is_err(),"nonfinite transform accepted");
    }
    let mut bad_geometry=geom(); bad_geometry.width-=1;
    assert!(prepare_with_config(&f,t,bad_geometry,crop(),&SITES,DirectPlaneMode::Rounded,&cfg,profile.as_ref()).is_err());
    let mut different=f.clone();different.path=f.path.parent().unwrap().join("other-directory").join(f.path.file_name().unwrap());
    assert!(prepare_with_config(&different,t,geom(),crop(),&SITES,DirectPlaneMode::Rounded,&cfg,profile.as_ref()).is_err());
    let mut bad_support=config_value(&f,t,DELTA);bad_support["support_native"]=json!([109,83,usize::MAX,392]);
    assert!(Configuration::from_json(&bad_support.to_string()).is_err());
    for value in [json!(null),json!(4.125),json!(-4.125)] {
        let mut bad_delta=config_value(&f,t,DELTA);bad_delta["frames"][0]["delta_source_native"][0]=value;
        assert!(Configuration::from_json(&bad_delta.to_string()).is_err());
    }
    // JSON has no NaN/Infinity numerical literals. Parser rejection of these
    // tokens is required separately from rejection of finite out-of-bound data.
    for token in ["NaN","Infinity","-Infinity"] {
        let text=config_value(&f,t,DELTA).to_string().replace("3.125",token);
        assert!(Configuration::from_json(&text).is_err());
    }
    // A valid-looking destination support whose left-most active correction
    // cannot supply the MHC+Catmull source stencil must refuse, not clamp.
    let edge_t=Similarity {a:Cx::ONE,b:Cx::new(-56.0,-42.0)};
    let edge_cfg=config(&f,edge_t,DELTA);
    assert!(prepare_with_config(&f,edge_t,geom(),crop(),&SITES,DirectPlaneMode::Rounded,&edge_cfg,None).is_err(),
        "missing original source stencil accepted");
}

#[test]
fn independent_local_placement_stack_identity_refusals() {
    let f=fixture("affine"); let t=transform(); let cfg=config(&f,t,DELTA);
    let paths=(0..3).map(|i|f.path.with_file_name(format!("placement-generated-{i}.ARW"))).collect::<Vec<_>>();
    let names=(0..3).map(|i|(format!("placement-generated-{i}.ARW"),100+i)).collect::<Vec<_>>();
    let provenance=Provenance {stack:StackIdentity::from_entries("generated",&names),strategy:"independent-control".into(),
        heldout_px:None,cycle_floor_px:None,reference:2,note:"no original files read".into()};
    let map=WarpMap::new(provenance.clone(),geom(),Resampler::CatmullRom,
        vec![FrameWarp::Placed(Similarity::IDENTITY),FrameWarp::Placed(t),FrameWarp::Placed(Similarity::IDENTITY)]);
    cfg.validate_stack(&paths,geom(),Some(&map)).unwrap();
    assert!(cfg.validate_stack(&paths[..2],geom(),Some(&map)).is_err());
    assert!(cfg.validate_stack(&paths,geom(),None).is_err());
    let mut wrong_paths=paths.clone();wrong_paths.swap(0,1);
    assert!(cfg.validate_stack(&wrong_paths,geom(),Some(&map)).is_err(),"configured filename accepted wrong transform index");
    let mut absent=paths.clone();absent[1]=f.path.with_file_name("absent.ARW");
    assert!(cfg.validate_stack(&absent,geom(),Some(&map)).is_err());
    let mut repeated=paths.clone();repeated[0]=paths[1].clone();
    assert!(cfg.validate_stack(&repeated,geom(),Some(&map)).is_err());
    let bad_map=WarpMap::new(provenance,geom(),Resampler::Bilinear,
        vec![FrameWarp::Placed(Similarity::IDENTITY),FrameWarp::Placed(t),FrameWarp::Placed(Similarity::IDENTITY)]);
    assert!(cfg.validate_stack(&paths,geom(),Some(&bad_map)).is_err());
}
