// Independent stimulus and controls; see independent-preregister.md for timing.
use super::super::*;
use super::*;
use std::fs;
use strehl_core::align::SimilarityParams;
use strehl_core::noise::{PlaneNoise, Provenance as NoiseProvenance};
use strehl_core::warpmap::Provenance as WarpProvenance;
use strehl_raw::Region;

mod legacy {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/m194c-probe-layout/legacy-fill-noise.rs"
    ));
    pub(super) fn apply(data: &mut [u16], index: usize) {
        fill_noise(data, 2512.0, 40.0, index);
    }
}

fn make_frame(w: usize, h: usize, layout: usize, k: usize) -> Frame {
    let (ax, ay, stride, bh, tail) = match layout {
        0 => (0, 0, w, h, 0),
        1 => (5, 7, w + 18, h + 18, 0),
        2 => (2, 9, w + 31, h + 25, 1),
        _ => panic!("unknown layout"),
    };
    let mut data: Vec<u16> = (0..stride * bh).map(|j| 65000 - (j % 31) as u16).collect();
    for y in 0..h {
        for x in 0..w {
            let site = 2 * (y % 2) + x % 2;
            let lo = std::f64::consts::TAU * (x as f64 / 31.0 + y as f64 / 19.0);
            let hi = std::f64::consts::TAU * (x as f64 / 7.0 + y as f64 / 11.0) + 0.19 * k as f64;
            let noise = ((x * 73 + y * 107 + x * y * 3 + k * 29) % 13) as f64 - 6.0;
            let v = 3512.0
                + [0.0, 80.0, -70.0, 160.0][site]
                + 70.0 * lo.sin()
                + [18.0, 60.0, 135.0, 50.0, 25.0][k % 5] * hi.sin()
                + 15.0 * k as f64
                + noise;
            data[(ay + y) * stride + ax + x] = v.round() as u16;
        }
    }
    Frame {
        data,
        stride,
        buffer_height: bh,
        active: Region {
            x: ax,
            y: ay,
            width: w + tail,
            height: h + tail,
        },
        levels: Levels {
            black: 512.0,
            white: 15360.0,
        },
        iso: Some(160.0),
        wb_coeffs: [1.15, 1.0, 1.65, f32::NAN],
        xyz_to_cam_rgbe: [[0.0; 3]; 4],
        color_matrices: Vec::new(),
        camera: "M194c independent software stimulus".into(),
        path: PathBuf::from(format!("M194C-INDEPENDENT-NO-SUCH-RAW-{k}.ARW")),
    }
}

fn active_values(f: &Frame) -> Vec<u16> {
    let g = f.geometry();
    (0..2 * g.height)
        .flat_map(|y| (0..2 * g.width).map(move |x| f.sample(x, y)))
        .collect()
}

fn outside_equal(before: &Frame, after: &Frame) {
    let g = before.geometry();
    for y in 0..before.buffer_height {
        for x in 0..before.stride {
            let consumed = y >= before.active.y
                && y < before.active.y + 2 * g.height
                && x >= before.active.x
                && x < before.active.x + 2 * g.width;
            if !consumed {
                assert_eq!(
                    before.data[y * before.stride + x],
                    after.data[y * after.stride + x],
                    "outside {x},{y}"
                );
            }
        }
    }
}

fn poison_outside(f: &mut Frame) {
    let g = f.geometry();
    for y in 0..f.buffer_height {
        for x in 0..f.stride {
            if !(y >= f.active.y
                && y < f.active.y + 2 * g.height
                && x >= f.active.x
                && x < f.active.x + 2 * g.width)
            {
                f.data[y * f.stride + x] = ((x * 23 + y * 47) % 509) as u16;
            }
        }
    }
}

fn warp(k: usize) -> Similarity {
    let s = [1.041, 1.023, 1.0, 0.992, 0.969][k];
    let theta: f64 = [0.009, -0.007, 0.0, 0.004, -0.003][k];
    let (tx, ty) = [
        (0.17, -0.21),
        (0.23, 0.17),
        (0.0, 0.0),
        (0.41, -0.19),
        (-0.13, 0.11),
    ][k];
    let (a, b) = (s * theta.cos(), s * theta.sin());
    let (dx, dy) = (81.5 - 68.5, 35.5 - 47.5);
    Similarity::from_params(SimilarityParams {
        ax: tx + (1.0 - a) * dx + b * dy,
        ay: ty - b * dx + (1.0 - a) * dy,
        g: a - 1.0,
        rot: b,
    })
}

fn crop() -> align_cmd::CropRect {
    align_cmd::CropRect {
        x: 9,
        y: 6,
        width: 112,
        height: 78,
    }
}

fn measured(
    f: &Frame,
    domain: PyramidDomain,
    bands: usize,
    seed: usize,
    t: Similarity,
) -> Vec<u32> {
    let mut p = Probe::new(domain, bands);
    let v = p
        .measure(
            f,
            seed,
            t,
            Resampler::CatmullRom,
            &mut WarpScratch::new(domain.full),
        )
        .unwrap();
    assert!(v.iter().all(|x| x.is_finite()));
    v.iter().map(|x| x.to_bits()).collect()
}

#[test]
fn independent_sequence_layout_legacy_and_seed() {
    let mut comparisons = 0;
    for (w, h) in [(70, 46), (118, 82)] {
        for seed in [0, 17, 43] {
            let mut packed = make_frame(w, h, 0, 0);
            let mut old = packed.clone();
            legacy::apply(&mut old.data, seed);
            let geom = packed.geometry();
            fill_probe_noise(&mut packed, geom, 2512.0, 40.0, seed).unwrap();
            assert_eq!(old.data, packed.data, "packed legacy sequence");
            let expected = active_values(&packed);
            for layout in [1, 2] {
                let before = make_frame(w, h, layout, 0);
                let mut got = before.clone();
                fill_probe_noise(&mut got, geom, 2512.0, 40.0, seed).unwrap();
                assert_eq!(expected, active_values(&got));
                outside_equal(&before, &got);
                let mut old_relocated = before;
                legacy::apply(&mut old_relocated.data, seed);
                let changed = expected
                    .iter()
                    .zip(active_values(&old_relocated))
                    .filter(|(a, b)| **a != *b)
                    .count();
                assert!(
                    changed > expected.len() / 2,
                    "legacy failing control lost power"
                );
                println!(
                    "M194C_INDEPENDENT legacy-layout w={w} h={h} seed={seed} layout={layout} changed={changed}/{}",
                    expected.len()
                );
                comparisons += 1;
            }
            let mut other_seed = packed.clone();
            fill_probe_noise(&mut other_seed, geom, 2512.0, 40.0, seed + 1).unwrap();
            assert_ne!(packed.data, other_seed.data);
        }
    }
    println!("M194C_INDEPENDENT sampler comparisons={comparisons} legacy-packed=6 seed-live=6");
}

#[test]
fn independent_actual_probe_layout_and_live_metadata() {
    let f = make_frame(274, 190, 0, 0);
    let full = f.geometry();
    let mut comparisons = 0;
    for d in [
        PyramidDomain::whole(full),
        PyramidDomain::cropped(full, crop()).unwrap(),
    ] {
        for bands in [3, 6] {
            for k in 0..5 {
                let baseline = measured(&f, d, bands, 17, warp(k));
                assert!(!baseline.is_empty());
                for layout in [1, 2] {
                    let mut relocated = make_frame(274, 190, layout, 0);
                    assert_eq!(baseline, measured(&relocated, d, bands, 17, warp(k)));
                    poison_outside(&mut relocated);
                    assert_eq!(baseline, measured(&relocated, d, bands, 17, warp(k)));
                    comparisons += 2;
                }
                assert_ne!(
                    baseline,
                    measured(&f, d, bands, 43, warp(k)),
                    "seed must be live"
                );
            }
        }
    }
    let domain = PyramidDomain::whole(full);
    let baseline = measured(&f, domain, 6, 17, warp(0));
    assert_ne!(baseline, measured(&f, domain, 6, 17, Similarity::IDENTITY));
    let mut changed = f.clone();
    changed.data.fill(9000);
    assert_eq!(
        baseline,
        measured(&changed, domain, 6, 17, warp(0)),
        "probe intentionally replaces template pixels"
    );
    changed.wb_coeffs = [1.9, 1.0, 0.7, f32::NAN];
    let wb = measured(&changed, domain, 6, 17, warp(0));
    if align_cmd::fullres_gather_enabled() {
        assert_ne!(baseline, wb);
    } else {
        assert_eq!(baseline, wb);
    }
    let tiny = make_frame(28, 18, 2, 0);
    assert!(
        measured(
            &tiny,
            PyramidDomain::whole(tiny.geometry()),
            6,
            17,
            Similarity::IDENTITY
        )
        .is_empty()
    );
    let mut p = Probe::new(domain, 6);
    p.beta = vec![1.0, f32::NAN];
    p.apply_scale();
    assert!(p.last()[1].is_nan(), "direct injected NaN preserved");
    p.invalidate();
    assert!(p.last().is_empty());
    println!(
        "M194C_INDEPENDENT actual-probe layout-comparisons={comparisons} seed-controls=20 warp-live=true wb-fullres={} beta0-bits={:?}",
        align_cmd::fullres_gather_enabled(),
        baseline
    );
}

fn fallback_output(beta: Option<&[f32]>, variance: f32, checkerboard: bool) -> Vec<u32> {
    let (w, h) = (72, 54);
    let cfg = MergeConfig {
        bands: 3,
        ..MergeConfig::default()
    };
    let mut merge = BandMerge::new(w, h, 1, cfg);
    let mut work = FrameWorkspace::new(merge.sizes(), 1);
    for k in 0..3 {
        let field: Vec<f32> = (0..w * h)
            .map(|j| {
                let x = (j % w) as f32;
                let y = (j / w) as f32;
                let carrier = if checkerboard {
                    if (j % w + j / w) % 2 == 0 { 1.0 } else { -1.0 }
                } else {
                    (x * 0.69 + y * 0.41 + k as f32 * 0.37).sin()
                };
                3000.0 + [12.0, 110.0, 34.0][k] * carrier
            })
            .collect();
        merge.add_frame_with_gain(&[&field], &field, &vec![variance; w * h], beta, &mut work);
    }
    let mut ws = Workspace::new(merge.sizes());
    merge.finish(&mut ws)[0]
        .iter()
        .map(|v| v.to_bits())
        .collect()
}

#[test]
#[should_panic(expected = "M194c original sinusoid has no demonstrated finite-floor power")]
fn independent_original_inert_fallback_power_retained() {
    let baseline = fallback_output(None, 800.0, false);
    assert_eq!(baseline, fallback_output(Some(&[]), 800.0, false));
    assert_eq!(
        baseline,
        fallback_output(Some(&[f32::NAN; 3]), 800.0, false)
    );
    assert!(
        baseline != fallback_output(Some(&[1.0e6; 3]), 800.0, false),
        "M194c original sinusoid has no demonstrated finite-floor power"
    );
}

#[test]
fn independent_empty_nan_and_real_merge_fallback() {
    assert!(
        pooled_mean_square(
            &vec![1.0; 16 * 24],
            LevelSize {
                width: 16,
                height: 24
            }
        )
        .is_none()
    );
    let mut field = vec![2.0; 32 * 30];
    assert_eq!(
        pooled_mean_square(
            &field,
            LevelSize {
                width: 32,
                height: 30
            }
        ),
        Some(4.0)
    );
    field[15 * 32 + 16] = f32::NAN;
    assert!(
        pooled_mean_square(
            &field,
            LevelSize {
                width: 32,
                height: 30
            }
        )
        .unwrap()
        .is_nan()
    );
    let baseline = fallback_output(None, 800.0, true);
    assert_eq!(baseline, fallback_output(Some(&[]), 800.0, true));
    assert_eq!(baseline, fallback_output(Some(&[f32::NAN; 3]), 800.0, true));
    let mean = fallback_output(Some(&[1.0e6; 3]), 800.0, true);
    assert!(
        baseline != mean,
        "additive checkerboard finite-floor power failed"
    );
    assert!(
        baseline != fallback_output(None, 80000.0, true),
        "additive checkerboard variance power failed"
    );
    for (x, expected) in [(30, 3052.0), (31, 2948.0)] {
        let j = 20 * 72 + x;
        assert!((f32::from_bits(mean[j]) - expected).abs() < 0.02);
        assert!((f32::from_bits(baseline[j]) - 3000.0).abs() > 60.0);
    }
    println!(
        "M194C_INDEPENDENT additive-checkerboard empty/direct-nan/fallback=true finite-floor-live=true variance-live=true mean-sites={:?} selected-sites={:?}",
        [
            f32::from_bits(mean[20 * 72 + 30]),
            f32::from_bits(mean[20 * 72 + 31])
        ],
        [
            f32::from_bits(baseline[20 * 72 + 30]),
            f32::from_bits(baseline[20 * 72 + 31])
        ]
    );
}

struct Source(Vec<Frame>);
impl PyramidFrameSource for Source {
    fn len(&self) -> usize {
        self.0.len()
    }
    fn decode(&self, index: usize) -> Result<Frame> {
        Ok(self.0[index].clone())
    }
}

fn options(out: PathBuf) -> MergeOptions {
    MergeOptions {
        dir: PathBuf::from("M194C-INDEPENDENT-NO-SUCH-RAW-DIRECTORY"),
        out: Some(out),
        limit: None,
        srgb: false,
        space: image_out::OutputSpace::CameraLinear,
        demosaic: true,
        exposure: 0.0,
        auto_exposure: false,
        gates: vec![2.0],
        focus: None,
        flat_roi: None,
        detail_roi: None,
        index_map: None,
        n_eff_map: None,
        confidence_map: None,
        photometric: PhotometricMode::Off,
        photometric_source: SettingSource::Default,
        target_n_eff: None,
        stats: false,
        stats_placebo: false,
        confidence_tail: 0.05,
        resampler: Resampler::CatmullRom,
        backend: MergeBackend::Pyramid,
        cover: align_cmd::CoverMode::Scale,
        cover_source: SettingSource::Default,
        pyramid: MergeConfig {
            bands: 3,
            ..MergeConfig::default()
        },
    }
}

fn render(
    frames: Vec<Frame>,
    dir: &Path,
    label: &str,
    cropped: bool,
    model: bool,
    warp_changed: bool,
    observer: usize,
) -> Vec<u8> {
    let output = dir.join(format!("{label}.tif"));
    let mut opts = options(output.clone());
    opts.stats = observer == 1;
    opts.stats_placebo = observer == 2;
    if cropped {
        opts.cover = align_cmd::CoverMode::Crop;
    }
    let first = &frames[0];
    let paths: Vec<_> = frames.iter().map(|f| f.path.clone()).collect();
    assert!(paths.iter().all(|p| !p.exists()));
    let geom = first.geometry();
    let domain = if cropped {
        PyramidDomain::cropped(geom, crop()).unwrap()
    } else {
        PyramidDomain::whole(geom)
    };
    let entries: Vec<_> = paths
        .iter()
        .map(|p| (p.to_string_lossy(), first.allocated_bytes() as u64))
        .collect();
    let warps: Vec<_> = (0..5)
        .map(|k| {
            let mut t = warp(k);
            if warp_changed && k == 1 {
                let mut p = t.to_params();
                p.ax += 0.37;
                t = Similarity::from_params(p);
            }
            FrameWarp::Placed(t)
        })
        .collect();
    let map = WarpMap::new(
        WarpProvenance {
            stack: StackIdentity::from_entries("M194c independent", &entries),
            strategy: "independent software transform stimulus".into(),
            heldout_px: None,
            cycle_floor_px: None,
            reference: 2,
            note: "no optical alignment claim".into(),
        },
        geom,
        opts.resampler,
        warps,
    );
    let noise = NoiseModel::new(
        [PlaneNoise {
            gain_dn_per_e: if model { 2.0 } else { 0.25 },
            read_noise_e: if model { 10.0 } else { 4.0 },
            levels: first.levels,
        }; 4],
        160.0,
        NoiseProvenance::Fallback,
    );
    let local = domain.analysis();
    let prepared = PreparedPyramid {
        paths: &paths,
        geom,
        levels: first.levels,
        noise,
        wb: first.wb_gains(),
        xyz_to_cam: first.xyz_to_cam_rgb_with_source(),
        frame_bytes: first.allocated_bytes(),
        alignment: Some((
            map,
            "M194c-independent",
            if cropped {
                align_cmd::CoverFit::Cropped {
                    k: 1.0,
                    rect: crop(),
                }
            } else {
                align_cmd::CoverFit::Uncovered
            },
        )),
        domain,
        sizes: level_sizes(local.width, local.height, opts.pyramid.bands),
        defect_plan: None,
        prologue_secs: 0.0,
        align_secs: 0.0,
        t_start: Instant::now(),
        exposure: Exposure::resolve(opts.srgb, opts.exposure, opts.auto_exposure).unwrap(),
    };
    run_pyramid_prepared(&opts, prepared, &Source(frames)).unwrap();
    fs::read(output).unwrap()
}

fn digest(bytes: &[u8]) -> String {
    use sha2::Digest;
    sha2::Sha256::digest(bytes)
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}

#[test]
fn independent_actual_writer_layout_and_power() {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../experiments/m194c-probe-layout/independent-work")
        .join(format!(
            "{}-{}",
            std::process::id(),
            align_cmd::fullres_gather_enabled()
        ));
    fs::create_dir_all(&dir).unwrap();
    for cropped in [false, true] {
        let frames: Vec<_> = (0..5).map(|k| make_frame(274, 190, 0, k)).collect();
        let prefix = if cropped { "crop" } else { "whole" };
        let baseline = render(
            frames.clone(),
            &dir,
            &format!("{prefix}-baseline"),
            cropped,
            false,
            false,
            0,
        );
        for layout in [1, 2] {
            let mut relocated: Vec<_> = (0..5).map(|k| make_frame(274, 190, layout, k)).collect();
            let got = render(
                relocated.clone(),
                &dir,
                &format!("{prefix}-layout{layout}"),
                cropped,
                false,
                false,
                0,
            );
            assert_eq!(digest(&baseline), digest(&got));
            relocated.iter_mut().for_each(poison_outside);
            let poisoned = render(
                relocated,
                &dir,
                &format!("{prefix}-poison{layout}"),
                cropped,
                false,
                false,
                0,
            );
            assert_eq!(digest(&baseline), digest(&poisoned));
        }
        let mut single = frames.clone();
        single[2].data[95 * 274 + 136] += 500;
        assert_ne!(
            digest(&baseline),
            digest(&render(
                single,
                &dir,
                &format!("{prefix}-single-site"),
                cropped,
                false,
                false,
                0
            ))
        );
        let mut active = frames.clone();
        for f in &mut active {
            for v in &mut f.data {
                *v += 200;
            }
        }
        assert_ne!(
            digest(&baseline),
            digest(&render(
                active,
                &dir,
                &format!("{prefix}-active"),
                cropped,
                false,
                false,
                0
            ))
        );
        assert_ne!(
            digest(&baseline),
            digest(&render(
                frames.clone(),
                &dir,
                &format!("{prefix}-noise"),
                cropped,
                true,
                false,
                0
            ))
        );
        assert_ne!(
            digest(&baseline),
            digest(&render(
                frames.clone(),
                &dir,
                &format!("{prefix}-warp"),
                cropped,
                false,
                true,
                0
            ))
        );
        let mut wb = frames.clone();
        for f in &mut wb {
            f.wb_coeffs = [1.9, 1.0, 0.7, f32::NAN];
        }
        assert_ne!(
            digest(&baseline),
            digest(&render(
                wb,
                &dir,
                &format!("{prefix}-wb"),
                cropped,
                false,
                false,
                0
            ))
        );
        for observer in [1, 2] {
            assert_eq!(
                digest(&baseline),
                digest(&render(
                    frames.clone(),
                    &dir,
                    &format!("{prefix}-observer{observer}"),
                    cropped,
                    false,
                    false,
                    observer
                ))
            );
        }
        println!(
            "M194C_INDEPENDENT delivered prefix={prefix} fullres={} sha256={} layout-equalities=4 active/noise/warp/WB-live=true observer-on/placebo-identical=true dir={}",
            align_cmd::fullres_gather_enabled(),
            digest(&baseline),
            dir.display()
        );
    }
}
