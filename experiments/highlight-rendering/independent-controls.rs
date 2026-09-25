// Independently chosen functional controls. Root executes; author does not verify.
use super::{pixel, shoulder_luminance, shoulder_rgb, Arm};
use crate::image_out::{Develop, Tone};
use strehl_core::{color, noise::Levels};

const ID: [[f32; 3]; 3] = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]];
const XYZ: [[f32; 3]; 3] = [
    [0.7460, -0.2365, -0.0588],
    [-0.5687, 1.3442, 0.2474],
    [-0.0624, 0.1156, 0.6584],
];
const ARMS: [Arm; 4] = [Arm::Current, Arm::SensorRolloffOff, Arm::Shoulder, Arm::Both];

fn dev(matrix: color::Render, white: f32, contrast: f32) -> Develop {
    Develop { matrix: Some(matrix), srgb: true,
        tone: Some(Tone { black: 0., white, contrast }), wants_tone: true,
        exposure_gain: 1. }
}
fn span(v: [u16; 3]) -> u16 { *v.iter().max().unwrap() - *v.iter().min().unwrap() }
fn luma(v: [f32; 3]) -> f32 { v[0]*0.2126 + v[1]*0.7152 + v[2]*0.0722 }
fn decode(v: u16) -> f64 {
    let x = f64::from(v) / 65535.;
    if x <= 0.04045 { x/12.92 } else { ((x+0.055)/1.055).powf(2.4) }
}
fn distinguishes_whites(v: &[[u16; 3]]) -> bool {
    v.len() >= 3 && v.iter().all(|p| span(*p) == 0)
        && v.windows(2).all(|p| p[1][0] > p[0][0])
}
fn preserves_chroma(v: &[[u16; 3]]) -> bool {
    v.len() >= 2 && v.iter().all(|p| span(*p) > 100) && v[0] != v[1]
}

#[test]
fn independent_flat_first_and_actual_current_identity() {
    let levels=Levels { black: 512., white: 15360. };
    let wb=[1.6904297, 1., 2.5205078];
    let render=color::camera_to_srgb(XYZ).unwrap().with_saturation(levels, wb, 1.);
    let d=dev(render, 1., 0.55);
    // Shared supplied noise realization: exact invariance, no calibration claim.
    let mut state=0x95a3_41c7u32;
    let mut distinct=std::collections::BTreeSet::new();
    for _ in 0..4096 {
        let mut p=[0.;3];
        for c in 0..3 {
            state=state.wrapping_mul(1664525).wrapping_add(1013904223);
            p[c]=[0.06,0.04,0.025][c]+((state>>8) as f32/16777216.-0.5)*0.001;
        }
        let expected=crate::image_out::develop_pixel(p,&d);
        distinct.insert(expected);
        for arm in ARMS { assert_eq!(pixel(p,&d,arm),expected,"low noisy flat changed"); }
    }
    assert!(distinct.len()>100,"flat fixture was constant and unexercised");

    let ceiling=render.ceiling();
    let samples=[
        [0.,0.,0.],[-0.01,0.01,0.02],[0.0001,0.0002,0.0003],
        [0.1,0.2,0.3],[0.3,0.1,0.04],[0.05,0.2,0.4],
        [0.6,0.6,0.6],[0.4,0.85,0.65],[0.8,0.9,0.75],
        [1.,1.,1.], [ceiling[0],ceiling[1],ceiling[2]],
        [ceiling[0]*1.2,ceiling[1]*0.8,ceiling[2]*0.9],
    ];
    let mut saw_pin=false;
    let mut saw_knee=false;
    for p in samples {
        saw_pin|=(0..3).any(|c|p[c]>=ceiling[c]);
        saw_knee|=(0..3).any(|c|p[c]/ceiling[c]>0.6);
        assert_eq!(pixel(p,&d,Arm::Current),crate::image_out::develop_pixel(p,&d),
            "actual current developer mismatch at {p:?}");
    }
    assert!(saw_pin && saw_knee);
    // Both factors must actually be reached; exact low-range null alone proves little.
    let hot=[0.4,0.85,0.65];
    assert_ne!(pixel(hot,&d,Arm::Current),pixel(hot,&d,Arm::SensorRolloffOff),
        "sensor-rolloff factor not exercised (check cleaned environment)");
    let neutral_dev=dev(color::Render::new(ID),1.,0.55);
    assert_ne!(pixel([1.1;3],&neutral_dev,Arm::Current),
        pixel([1.1;3],&neutral_dev,Arm::Shoulder),"shoulder factor not exercised");
}

#[test]
fn independent_shoulder_neutral_order_detail_and_destroyer() {
    for y in [-0.1,0.,0.0001,0.2,0.6,0.749,0.75] {
        assert_eq!(shoulder_luminance(y).to_bits(),y.to_bits(),"below-knee scalar changed");
    }
    let levels=[0.7501,0.76,0.8,0.9,1.,1.25,1.5,2.];
    let d=dev(color::Render::new(ID),1.,0.55);
    let mut previous=0.75;
    for y in levels {
        let z=shoulder_luminance(y);
        assert!(z.is_finite() && z>previous && z<=y && z<1.,"invalid shoulder at {y}: {z}");
        if y>=0.76 { assert!(z<y,"shoulder did not compress an exercised level"); }
        previous=z;
        let p=pixel([y;3],&d,Arm::Shoulder);
        assert_eq!(span(p),0,"neutral tinted at {y}");
    }
    let highlights=[1.,1.25,1.5,2.];
    let current:Vec<_>=highlights.iter().map(|&v|pixel([v;3],&d,Arm::Current)).collect();
    let candidate:Vec<_>=highlights.iter().map(|&v|pixel([v;3],&d,Arm::Shoulder)).collect();
    assert!(current.iter().all(|v|*v==[65535;3]),"white plateau fixture unexercised");
    assert!(distinguishes_whites(&candidate),"shoulder erased distinct bright levels");
    assert!(!distinguishes_whites(&current),"hard-clip destroyer escaped the level check");
}

#[test]
fn independent_color_ratios_and_grey_destroyer() {
    for p in [[0.95,0.85,0.75],[1.6,1.2,0.8],[2.,0.7,0.4],[-0.1,1.4,0.2]] {
        let q=shoulder_rgb(p);
        let y=luma(p);
        assert!(y>0.75,"fixture must exercise shoulder");
        assert!(q.iter().all(|v|v.is_finite()));
        let gain=q[1]/p[1];
        assert!(gain>0. && gain<1.);
        for c in 0..3 { assert!((q[c]-p[c]*gain).abs()<2e-6,"color ratio altered"); }
        assert!((luma(q)-shoulder_luminance(y)).abs()<2e-6,"RGB gain not luminance shoulder");
    }
    for p in [[0.;3],[-0.1,0.01,0.02],[0.1,0.2,0.3],[0.75;3]] {
        assert_eq!(shoulder_rgb(p).map(f32::to_bits),p.map(f32::to_bits),"inactive RGB changed");
    }
    let d=dev(color::Render::new(ID),1.,0.);
    let p=[0.95,0.85,0.75];
    let q=pixel(p,&d,Arm::Shoulder).map(decode);
    assert!((q[0]/q[1]-f64::from(p[0]/p[1])).abs()<0.0002);
    assert!((q[2]/q[1]-f64::from(p[2]/p[1])).abs()<0.0002);
    let bright=[[1.6,1.2,0.8],[1.8,1.35,0.9]];
    assert!(bright.iter().all(|&p|luma(p)>1.),"colored white-plateau case absent");
    let current:Vec<_>=bright.iter().map(|&p|pixel(p,&d,Arm::Current)).collect();
    let candidate:Vec<_>=bright.iter().map(|&p|pixel(p,&d,Arm::Shoulder)).collect();
    assert!(current.iter().all(|&p|span(p)==0),"baseline did not lose chroma");
    assert!(preserves_chroma(&candidate),"shoulder retained no distinct bright color");
    let grey:Vec<_>=candidate.iter().map(|p|[p[1];3]).collect();
    assert!(!preserves_chroma(&grey),"grey destroyer escaped chroma check");
}

#[test]
fn independent_sensor_pinning_is_not_disabled_with_rolloff() {
    let levels=Levels{black:512.,white:15360.};
    let wb=[1.6904297,1.,2.5205078];
    let protected=color::Render::new(ID).with_saturation(levels,wb,1.);
    let p=protected.ceiling();
    let d=dev(protected,4.,0.);
    for arm in [Arm::SensorRolloffOff,Arm::Both] {
        assert_eq!(span(pixel(p,&d,arm)),0,"sensor pin protection disabled");
    }
    // Deliberately omit a sensor ceiling: the same input must now remain colored.
    // This proves that neutral output above is evidence of the retained pin guard.
    let broken=dev(color::Render::new(ID),4.,0.);
    assert!(span(pixel(p,&broken,Arm::SensorRolloffOff))>1000,
        "unclipped-pinned destroyer unexercised");
}
