// Independent old-buffer oracle and current consumer controls. Root executes.
use super::*;
use crate::align_cmd::{consumed_fullres_value, write_fullres_plane,
    warp_frame_fullres_into_planes, CropRect, DirectPlaneMode, WarpWriteback};
use strehl_core::align::SimilarityParams;
use strehl_core::plane::QuadSource;

fn bits(values: &[f32]) -> Vec<u32> { values.iter().map(|v| v.to_bits()).collect() }
fn whole(g: PlaneGeometry) -> CropRect { CropRect { x: 0, y: 0, width: g.width, height: g.height } }
fn interior(g: PlaneGeometry) -> CropRect {
    CropRect { x: usize::from(g.width > 1), y: usize::from(g.height > 1),
        width: g.width - usize::from(g.width > 1), height: g.height - usize::from(g.height > 1) }
}
fn old_consumed(v: f32, covered: bool, inv: f32, black: f32) -> f32 {
    let code = if covered { (v * inv + black).round().clamp(0.0, 65535.0) as u16 }
        else { black.round().clamp(0.0, 65535.0) as u16 };
    (f32::from(code) - black).max(0.0)
}
fn float_consumed(v: f32, covered: bool, inv: f32, black: f32) -> f32 {
    if !covered { return old_consumed(v, false, inv, black); }
    let sensor = v * inv + black;
    let sensor = if sensor.is_nan() || sensor < 0.0 { 0.0 }
        else if sensor > 65535.0 { 65535.0 } else { sensor };
    (sensor - black).max(0.0)
}

// Called from the existing 2,304 old scalar writeback comparisons, in that
// fixture's 1/2/8-thread pool. It receives the independent scalar whole buffer.
#[allow(clippy::too_many_arguments)]
pub(super) fn check_writeback_case(expected: &[u16], stride: usize,
    active: (usize, usize), full: PlaneGeometry, site: (usize, usize),
    dst: &[f32], cover: &[bool], inv: f32, black: f32, execution: WarpWriteback) {
    for crop in [whole(full), interior(full)] {
        let n = crop.width * crop.height;
        let mut guarded = vec![f32::from_bits(0x7fc12345); n + 4];
        let count = write_fullres_plane(&mut guarded[2..2+n], full, crop, dst, cover,
            inv, black, DirectPlaneMode::Rounded, execution).unwrap();
        assert_eq!(count, cover.iter().filter(|v| **v).count(), "crop must preserve full-grid coverage count");
        for y in 0..crop.height {
            for x in 0..crop.width {
                let sensor = (active.1 + 2 * (crop.y + y) + site.1) * stride
                    + active.0 + 2 * (crop.x + x) + site.0;
                let want = (f32::from(expected[sensor]) - black).max(0.0);
                assert_eq!(guarded[2 + y * crop.width + x].to_bits(), want.to_bits(),
                    "literal old-buffer compact output site={site:?} crop={crop:?} at {x},{y}");
            }
        }
        assert!([0,1,n+2,n+3].iter().all(|i| guarded[*i].to_bits() == 0x7fc12345), "sink touched guard storage");
        let count = write_fullres_plane(&mut guarded[2..2+n], full, crop, dst, cover,
            inv, black, DirectPlaneMode::Float, execution).unwrap();
        assert_eq!(count, cover.iter().filter(|v| **v).count());
        for y in 0..crop.height {
            for x in 0..crop.width {
                let i = (crop.y + y) * full.width + crop.x + x;
                assert_eq!(guarded[2 + y * crop.width + x].to_bits(),
                    float_consumed(dst[i], cover[i], inv, black).to_bits(), "float operand order/coverage");
            }
        }
        assert!([0,1,n+2,n+3].iter().all(|i| guarded[*i].to_bits() == 0x7fc12345));
    }
}

fn literal_controls() -> usize {
    // Input, inverse WB, black, coverage, literal rounded output, literal float output.
    let cases: [(f32,f32,f32,bool,f32,f32); 24] = [
        (f32::NEG_INFINITY,1.0,0.0,true,0.0,0.0),
        (f32::INFINITY,1.0,0.0,true,65535.0,65535.0),
        (f32::NAN,1.0,-1.5,true,1.5,1.5),
        (f32::from_bits(0xffc01234),1.0,512.25,true,0.0,0.0),
        (-0.0,1.0,0.0,true,0.0,0.0), (0.0,1.0,-0.0,true,0.0,0.0),
        (-0.5,1.0,0.0,true,0.0,0.0), (0.5,1.0,0.0,true,1.0,0.5),
        (1.5,1.0,0.0,true,2.0,1.5), (65534.5,1.0,0.0,true,65535.0,65534.5),
        (65535.5,1.0,0.0,true,65535.0,65535.0),
        (1000.25,1.0,512.25,true,1000.75,1000.25),
        (1.0,1.3,512.25,true,1.75,1.29998779296875),
        (0.0000152587890625,1.0,512.25,true,0.0,0.0),
        (100.0,0.0,512.75,true,0.25,0.0),
        (f32::NAN,1.0,0.5,false,0.5,0.5),
        (f32::NAN,1.0,512.75,false,0.25,0.25),
        (f32::NAN,1.0,-1.5,false,1.5,1.5),
        (1.0,1.0,f32::NAN,true,0.0,0.0),
        (1.0,1.0,f32::NEG_INFINITY,true,f32::INFINITY,f32::INFINITY),
        (1.0,1.0,f32::INFINITY,true,0.0,0.0),
        (100000.0,1.0,-1.5,true,65536.5,65536.5),
        (-100000.0,1.0,-1.5,true,1.5,1.5),
        (10.0,1.0,65536.0,true,0.0,0.0),
    ];
    let mut fractional = 0;
    for (i, &(value, inv, black, covered, rounded, float)) in cases.iter().enumerate() {
        for (mode, want) in [(DirectPlaneMode::Rounded, rounded), (DirectPlaneMode::Float, float)] {
            let actual = consumed_fullres_value(value, covered, inv, black, mode);
            assert_eq!(actual.to_bits(), want.to_bits(), "literal case {i} mode={mode:?}");
        }
        fractional += usize::from(rounded.to_bits() != float.to_bits());
    }
    assert!(fractional >= 5, "precision arm was not exercised by literal fractional samples");
    assert_ne!(cases[13].0.to_bits(), cases[13].5.to_bits(), "simplified inverse-WB cancellation destroyer lost power");
    assert_ne!(cases[15].5.to_bits(), 0.0f32.to_bits(), "uncovered-zero destroyer lost power");

    // Metadata faults are not supported sensor calibrations; they test exact
    // legacy IEEE semantics rather than silently removing the difficult domain.
    let mut checks = cases.len() * 2;
    for value in [-0.0, 0.25, -123.75, 65535.75, f32::INFINITY, f32::NEG_INFINITY, f32::NAN] {
        for inv in [-0.0, 1.0, 1.3, f32::INFINITY, f32::NAN] {
            for black in [-65536.25, -1.5, -0.0, 0.5, 512.25, 65535.5, f32::INFINITY, f32::NEG_INFINITY, f32::NAN] {
                for covered in [false, true] {
                    for (mode, want) in [(DirectPlaneMode::Rounded, old_consumed(value,covered,inv,black)),
                        (DirectPlaneMode::Float, float_consumed(value,covered,inv,black))] {
                        assert_eq!(consumed_fullres_value(value,covered,inv,black,mode).to_bits(),want.to_bits(), "fault arithmetic mode={mode:?}");
                        checks += 1;
                    }
                }
            }
        }
    }
    // A crop-shift destroyer retains size, coverage and the source value histogram.
    let full = PlaneGeometry { width: 7, height: 5 };
    let dst: Vec<_> = (0..full.pixels()).map(|i| 1000.25 + 3.0 * i as f32).collect();
    let cover = vec![true; full.pixels()];
    let right = CropRect { x: 2, y: 1, width: 3, height: 2 };
    let wrong = CropRect { x: 1, ..right };
    let mut a = vec![0.0; 6]; let mut b = a.clone();
    for execution in [WarpWriteback::Serial, WarpWriteback::Parallel] {
        write_fullres_plane(&mut a,full,right,&dst,&cover,1.0,512.25,DirectPlaneMode::Rounded,execution).unwrap();
        write_fullres_plane(&mut b,full,wrong,&dst,&cover,1.0,512.25,DirectPlaneMode::Rounded,execution).unwrap();
        assert_ne!(bits(&a),bits(&b), "wrong-crop-origin destroyer lost power");
        assert_eq!(a[0].to_bits(), 1027.75f32.to_bits());
    }
    checks
}

// Reuses the existing 144 fullres old-RGB/green fixtures: all resamplers,
// layouts, WB arms and identity/partial/absent coverage. No new scene renderer.
pub(super) fn check_warp_case(before: &Frame, old_rgb: &Frame, t: Similarity,
    full: PlaneGeometry, resampler: Resampler) {
    for greens in [false,true] {
        let crop = if greens { interior(full) } else { whole(full) };
        let offsets = if greens { &BAND_PLANE_OFFSETS[1..3] } else { &BAND_PLANE_OFFSETS[..] };
        let domain = PyramidDomain::cropped(full,crop).unwrap();
        let mut expected = vec![vec![0.0;crop.width*crop.height];offsets.len()];
        extract_planes(&old_rgb.data,old_rgb.stride,old_rgb.active.x,old_rgb.active.y,
            old_rgb.levels.black,domain,offsets,&mut expected).unwrap();
        let mut actual = vec![vec![f32::NAN;crop.width*crop.height];offsets.len()];
        let mut source = before.clone();
        if greens {
            warp_frame_fullres_into_planes::<true>(&mut source,t,full,resampler,&mut WarpScratch::new(full),
                crop,offsets,&mut actual,DirectPlaneMode::Rounded).unwrap();
        } else {
            warp_frame_fullres_into_planes::<false>(&mut source,t,full,resampler,&mut WarpScratch::new(full),
                crop,offsets,&mut actual,DirectPlaneMode::Rounded).unwrap();
        }
        assert_eq!(source.data,before.data,"direct sink modified u16 source or padding/odd tail");
        for (a,b) in actual.iter().zip(expected.iter()) { assert_eq!(bits(a),bits(b),"rounded actual gather differs greens={greens} crop={crop:?}"); }
    }
}

fn actual_fractional_witness() -> usize {
    let before = super::m194c_independent_tests::green_fixture(66,46,2,0);
    let full = before.geometry();
    let t = Similarity::from_params(SimilarityParams { g: 0.0, rot: 0.0, ax: 0.25, ay: 0.17 });
    let mut outputs = Vec::new();
    for mode in [DirectPlaneMode::Rounded,DirectPlaneMode::Float] {
        let mut source = before.clone();
        let mut planes = vec![vec![0.0;full.pixels()];4];
        warp_frame_fullres_into_planes::<false>(&mut source,t,full,Resampler::Bilinear,&mut WarpScratch::new(full),
            whole(full),&BAND_PLANE_OFFSETS,&mut planes,mode).unwrap();
        assert_eq!(source.data,before.data);
        let crop=interior(full);
        let mut cropped=vec![vec![0.0;crop.width*crop.height];4];
        warp_frame_fullres_into_planes::<false>(&mut source,t,full,Resampler::Bilinear,&mut WarpScratch::new(full),
            crop,&BAND_PLANE_OFFSETS,&mut cropped,mode).unwrap();
        for c in 0..4 { for y in 0..crop.height { for x in 0..crop.width {
            assert_eq!(cropped[c][y*crop.width+x].to_bits(),planes[c][(crop.y+y)*full.width+crop.x+x].to_bits(),"crop changed full-grid transform centre");
        } } }
        outputs.push(planes);
    }
    let mut changed=0;
    for (rounded,float) in outputs[0].iter().flatten().zip(outputs[1].iter().flatten()) {
        assert!(rounded.is_finite() && float.is_finite() && *float >= 0.0);
        assert!((rounded-float).abs() <= 0.5,"only covered intermediate rounding may change this valid fixture");
        changed += usize::from(rounded.to_bits()!=float.to_bits());
    }
    assert!(changed > full.pixels(),"fractional actual four-colour gather witness lacks power");
    changed
}

#[test]
fn independent_direct_planes_controls() {
    let literal_checks=literal_controls();
    let direct_comparisons=super::native_parallel_writeback_independent_tests::direct_controls();
    let changed=actual_fractional_witness();
    super::native_green_probe_independent_tests::run_for_writeback_controls();
    let dir=std::path::PathBuf::from(std::env::var_os("STREHL_GREEN_PROBE_OUTPUT").unwrap());
    let result=serde_json::json!({"schema":"native-direct-planes-independent-v1",
        "requested_mode":std::env::var("STREHL_DIRECT_PLANES").unwrap_or_else(|_|"off-default".into()),
        "literal_checks":literal_checks,"old_scalar_comparisons":direct_comparisons,
        "threads":[1,2,8],"actual_fractional_changed_sites":changed,
        "rounded_crop_green_allcolour_source_storage_controls":true,
        "scope":"exact consumed-plane/IEEE controls plus existing actual Probe beta and whole/crop TIFFs; root compares process arms; no precision quality or native speed claim"});
    std::fs::write(dir.join("direct-planes-result.json"),serde_json::to_vec_pretty(&result).unwrap()).unwrap();
    println!("NATIVE_DIRECT_PLANES literal-checks={literal_checks} old-scalar-comparisons={direct_comparisons} actual-fractional-changed={changed} actual-rounded-gather/crop/source-storage=true");
}
