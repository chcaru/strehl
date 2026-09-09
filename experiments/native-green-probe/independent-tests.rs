// Independent consumer controls. Root runs this exact test in fresh env processes.
use super::*;
use super::super::PyramidDomain;
use strehl_core::align::SimilarityParams;
use strehl_core::demosaic::{self, Mosaic};
use strehl_core::plane::QuadSource;
use serde_json::json;
use sha2::Digest;

fn hash(bytes: &[u8]) -> String {
    sha2::Sha256::digest(bytes).iter().map(|b| format!("{b:02x}")).collect()
}
fn bits_hash(bits: &[u32]) -> String {
    hash(&bits.iter().flat_map(|v| v.to_le_bytes()).collect::<Vec<_>>())
}
fn frame(w: usize, h: usize, layout: usize, k: usize) -> Frame {
    super::m194c_independent_tests::green_fixture(w, h, layout, k)
}
fn transform(k: usize) -> Similarity {
    match k {
        0 => Similarity::IDENTITY,
        1 => Similarity::from_params(SimilarityParams { g: 0.021, rot: -0.007, ax: 0.23, ay: -0.31 }),
        _ => Similarity::from_params(SimilarityParams { g: 0.0, rot: 0.0, ax: 10000.0, ay: -10000.0 }),
    }
}
fn green_codes(f: &Frame) -> Vec<u16> {
    let g = f.geometry();
    (0..2 * g.height).flat_map(|y| (0..2 * g.width)
        .filter(move |x| (x + y) % 2 == 1)
        .map(move |x| f.data[(f.active.y + y) * f.stride + f.active.x + x])).collect()
}
fn core_rows(data: &[f32], w: usize, h: usize) -> Vec<u32> {
    let m = Mosaic { data, width: w, height: h };
    let mut rgb = vec![0.0; 3 * w];
    let mut green = vec![0.0; w];
    let mut result = Vec::new();
    for y in 0..h {
        demosaic::demosaic_row(&m, y, &mut rgb);
        demosaic::demosaic_green_row(&m, y, &mut green);
        for x in 0..w {
            assert_eq!(green[x].to_bits(), rgb[3 * x + 1].to_bits(), "core green {w}x{h} at {x},{y}");
            result.push(green[x].to_bits());
        }
    }
    result
}
fn core_controls() -> (usize, String) {
    let mut sites = 0;
    let mut all_bits = Vec::new();
    for (w, h) in [(1, 1), (2, 2), (3, 5), (18, 11), (65, 49)] {
        let data: Vec<f32> = (0..w * h).map(|i| {
            let (x, y) = (i % w, i / w);
            ((17 * x + 31 * y + 3 * x * y) % 127) as f32 - 61.5
        }).collect();
        all_bits.extend(core_rows(&data, w, h));
        sites += w * h;
    }
    let (w, h) = (27, 19);
    let data: Vec<f32> = (0..w * h).map(|i| ((i * 37 + (i / w) * 11) % 101) as f32 + 3.25).collect();
    let baseline = core_rows(&data, w, h);
    for phase in [0, 3] {
        let mut changed = data.clone();
        for (i, v) in changed.iter_mut().enumerate() {
            if 2 * ((i / w) % 2) + (i % w) % 2 == phase { *v = 0.0; }
        }
        let poisoned = core_rows(&changed, w, h);
        let mut reconstructed_changes = 0;
        for i in 0..w * h {
            if ((i % w) + (i / w)) % 2 == 1 {
                assert_eq!(baseline[i], poisoned[i], "source G must remain unchanged");
            } else { reconstructed_changes += usize::from(baseline[i] != poisoned[i]); }
        }
        assert!(reconstructed_changes > 0, "source R/B destroyer did not reach reconstructed green, phase={phase}");
    }
    (sites, bits_hash(&all_bits))
}
fn warp_controls() -> (usize, usize) {
    let kernels = [Resampler::Nearest, Resampler::Bilinear, Resampler::CatmullRom,
                   Resampler::ClampedCatmullRom, Resampler::Lanczos2, Resampler::Lanczos3];
    let mut pairs = 0;
    let mut sites = 0;
    let (mut partial, mut absent, mut omitted_rb_live, mut odd_tail, mut dispatches) = (false, false, false, false, 0);
    for (w, h, layout) in [(2, 2, 0), (14, 10, 2), (66, 46, 1), (138, 94, 2)] {
        for wb in 0..2 {
            let mut before = frame(w, h, layout, 0);
            if wb == 1 { before.wb_coeffs = [1.9, 0.8, 0.7, f32::NAN]; }
            let g = before.geometry();
            odd_tail |= before.active.width > 2 * g.width && before.active.height > 2 * g.height;
            for kernel in kernels {
                for k in 0..3 {
                    let t = transform(k);
                    let mut rgb = before.clone();
                    let covered = align_cmd::warp_frame_in_place_fullres(&mut rgb, t, g, kernel, &mut WarpScratch::new(g)).unwrap();
                    let mut green = before.clone();
                    align_cmd::warp_probe_greens_in_place_fullres(&mut green, t, g, kernel, &mut WarpScratch::new(g)).unwrap();
                    partial |= covered > 0.0 && covered < 1.0;
                    absent |= covered == 0.0;
                    for y in 0..before.buffer_height {
                        for x in 0..before.stride {
                            let i = y * before.stride + x;
                            let inside = x >= before.active.x && y >= before.active.y &&
                                x < before.active.x + 2 * g.width && y < before.active.y + 2 * g.height;
                            let consumed = inside && (x - before.active.x + y - before.active.y) % 2 == 1;
                            if consumed {
                                assert_eq!(green.data[i], rgb.data[i], "G gather layout={layout} wb={wb} kernel={kernel:?} warp={k} at{x},{y}");
                                sites += 1;
                            } else {
                                assert_eq!(green.data[i], before.data[i], "green-only path touched unconsumed storage");
                                if !inside { assert_eq!(rgb.data[i], before.data[i], "RGB touched unused storage"); }
                                else { omitted_rb_live |= rgb.data[i] != before.data[i]; }
                            }
                        }
                    }
                    if wb == 0 && k == 1 && kernel == Resampler::CatmullRom {
                        let mut dispatched = before.clone();
                        align_cmd::warp_probe_greens_in_place(&mut dispatched, t, g, kernel, &mut WarpScratch::new(g)).unwrap();
                        if align_cmd::fullres_gather_enabled() {
                            assert_eq!(dispatched.data, green.data, "fullres dispatch missed green arm");
                        } else {
                            let mut plane = before.clone();
                            align_cmd::warp_frame_in_place_plane(&mut plane, t, g, kernel, &mut WarpScratch::new(g)).unwrap();
                            assert_eq!(dispatched.data, plane.data, "plane fallback changed");
                        }
                        dispatches += 1;
                    }
                    pairs += 1;
                }
            }
        }
    }
    assert_eq!(pairs, 144);
    assert_eq!(dispatches, 4);
    assert!(partial && absent && omitted_rb_live && odd_tail, "required geometry/output omission case was not live");
    let before = frame(66, 46, 2, 0);
    let g = before.geometry();
    let mut baseline = before.clone();
    align_cmd::warp_probe_greens_in_place_fullres(&mut baseline, transform(1), g, Resampler::CatmullRom, &mut WarpScratch::new(g)).unwrap();
    for phase in [0, 3] {
        let mut changed = before.clone();
        for y in 0..2 * g.height {
            for x in 0..2 * g.width {
                if 2 * (y % 2) + x % 2 == phase {
                    changed.data[(changed.active.y + y) * changed.stride + changed.active.x + x] = 512;
                }
            }
        }
        assert_eq!(green_codes(&changed), green_codes(&before), "destroyer touched source greens");
        align_cmd::warp_probe_greens_in_place_fullres(&mut changed, transform(1), g, Resampler::CatmullRom, &mut WarpScratch::new(g)).unwrap();
        assert_ne!(green_codes(&changed), green_codes(&baseline), "source R/B did not affect consumed destination greens, phase={phase}");
    }
    (pairs, sites)
}
fn measure_bits(f: &Frame, d: PyramidDomain, seed: usize) -> Vec<u32> {
    let mut p = Probe::new(d, 6);
    let bits: Vec<_> = p.measure(f, seed, transform(1), Resampler::CatmullRom,
        &mut WarpScratch::new(d.full)).unwrap().iter().map(|v| v.to_bits()).collect();
    p.invalidate();
    assert!(p.last().is_empty());
    bits
}

#[test]
fn independent_green_probe_controls() {
    let dir = std::path::PathBuf::from(std::env::var_os("STREHL_GREEN_PROBE_OUTPUT").expect("root provides a fresh output directory"));
    std::fs::create_dir(&dir).expect("refuse existing output directory");
    let (core_sites, core_hash) = core_controls();
    let (warp_pairs, green_sites) = warp_controls();
    let f = frame(274, 190, 2, 0);
    let full = f.geometry();
    let crop = align_cmd::CropRect { x: 9, y: 6, width: 112, height: 78 };
    let mut beta_cases = Vec::new();
    for cropped in [false, true] {
        let domain = if cropped { PyramidDomain::cropped(full, crop).unwrap() } else { PyramidDomain::whole(full) };
        for wb in 0..2 {
            let mut template = f.clone();
            if wb == 1 { template.wb_coeffs = [1.9, 1.0, 0.7, f32::NAN]; }
            for seed in [0, 17] {
                let bits = measure_bits(&template, domain, seed);
                assert!(!bits.is_empty() && bits.iter().all(|b| f32::from_bits(*b).is_finite()));
                beta_cases.push(json!({"crop":cropped,"wb":wb,"seed":seed,"bits":bits}));
            }
        }
    }
    assert_ne!(beta_cases[0]["bits"], beta_cases[1]["bits"], "actual beta seed was inert");
    if align_cmd::fullres_gather_enabled() {
        assert_ne!(beta_cases[0]["bits"], beta_cases[2]["bits"], "fullres beta WB was inert");
    } else { assert_eq!(beta_cases[0]["bits"], beta_cases[2]["bits"], "plane fallback unexpectedly uses WB"); }
    let tiny = frame(28, 18, 2, 0);
    let empty_beta = measure_bits(&tiny, PyramidDomain::whole(tiny.geometry()), 0);
    assert!(empty_beta.is_empty(), "tiny no-certified-band control not exercised");
    // Fault injection at existing Probe input, not a valid sensor calibration.
    // -infinity produces infinite black-subtracted luma and NaN after centering.
    let mut invalid_levels = f.clone();
    invalid_levels.levels.black = f32::NEG_INFINITY;
    let nan_beta = measure_bits(&invalid_levels, PyramidDomain::whole(full), 0);
    assert!(!nan_beta.is_empty() && nan_beta.iter().all(|b| f32::from_bits(*b).is_nan()), "actual NaN beta fault was not exercised");
    let mut whole_hashes = Vec::new();
    for cropped in [false, true] {
        let label = if cropped { "crop" } else { "whole" };
        let frames: Vec<_> = (0..5).map(|k| frame(274, 190, 2, k)).collect();
        let bytes = super::m194c_independent_tests::green_render(frames, &dir, label, cropped);
        assert!(!bytes.is_empty());
        whole_hashes.push(json!({"name":format!("{label}.tif"),"bytes":bytes.len(),"sha256":hash(&bytes)}));
    }
    let result = json!({
        "schema":"native-green-probe-independent-v1",
        "mode":{"green":probe_gather_uses_green().unwrap(),"fullres":align_cmd::fullres_gather_enabled(),"demosaic":std::env::var("STREHL_DEMOSAIC").unwrap_or_default()},
        "measurements":{"core_sites":core_sites,"core_green_sha256":core_hash,"warp_pairs":warp_pairs,"green_sites":green_sites,
            "beta_cases":beta_cases,"empty_beta_bits":empty_beta,"nan_fault_beta_bits":nan_beta,"outputs":whole_hashes},
        "limits":"generated consumer equivalence; NaN arm uses invalid black metadata; no calibration or speed claim"
    });
    std::fs::write(dir.join("result.json"), serde_json::to_vec_pretty(&result).unwrap()).unwrap();
    println!("NATIVE_GREEN_PROBE core-sites={core_sites} warp-pairs={warp_pairs} green-sites={green_sites} source-R/B-live=true partial/uncovered/odd-tail-live=true beta-seed/WB-live=true NaN-fault-live=true whole/crop-written=true output={}",dir.display());
}
