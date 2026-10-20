// M194d actual candidate consumer controls. Existing independent M194c scene,
// layouts and transforms are deliberately reused per independent-design.md.
// Derived from committed independent-tests.rs; author tests were not copied.
use super::*;
use std::fs;
use std::sync::atomic::{AtomicUsize, Ordering as AtomicOrdering};
use strehl_core::align::SimilarityParams;
use strehl_core::noise::{PlaneNoise, Provenance as NoiseProvenance};
use strehl_core::warpmap::Provenance as WarpProvenance;
use strehl_raw::Region;

struct CountedSource {
    frames: Vec<Frame>,
    reads: Vec<AtomicUsize>,
    observer: ObserverMode,
    placebo: AtomicUsize,
}
#[derive(Clone, Copy, Debug)]
enum ObserverMode {
    Off,
    Count,
    Placebo,
}
impl PyramidFrameSource for CountedSource {
    fn len(&self) -> usize {
        self.frames.len()
    }
    fn decode(&self, index: usize) -> Result<Frame> {
        match self.observer {
            ObserverMode::Off => (),
            ObserverMode::Count => {
                self.reads[index].fetch_add(1, AtomicOrdering::SeqCst);
            }
            ObserverMode::Placebo => {
                self.placebo.fetch_add(1, AtomicOrdering::SeqCst);
            }
        }
        Ok(self.frames[index].clone())
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
        camera: "M194d independent software stimulus".into(),
        path: PathBuf::from(format!("M194D-INDEPENDENT-NO-SUCH-RAW-{k}.ARW")),
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

fn independent_options(out: PathBuf) -> MergeOptions {
    MergeOptions {
        linear_master: None,
        region_recipe: None,
        dir: PathBuf::from("M194D-INDEPENDENT-NO-SUCH-RAW-DIRECTORY"),
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
    mode: AdmissionMode,
) -> Vec<u8> {
    render_with_observer(
        frames,
        dir,
        label,
        cropped,
        mode,
        (model, warp_changed, ObserverMode::Count),
    )
}

fn render_with_observer(
    frames: Vec<Frame>,
    dir: &Path,
    label: &str,
    cropped: bool,
    mode: AdmissionMode,
    controls: (bool, bool, ObserverMode),
) -> Vec<u8> {
    let (model, warp_changed, observer) = controls;
    let output = dir.join(format!("{label}.tif"));
    let mut opts = independent_options(output.clone());
    opts.pyramid.admission = mode;
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
            stack: StackIdentity::from_entries("M194d independent", &entries),
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
            "M194d-independent",
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
    let source = CountedSource {
        reads: (0..frames.len()).map(|_| AtomicUsize::new(0)).collect(),
        observer,
        placebo: AtomicUsize::new(0),
        frames,
    };
    run_pyramid_prepared(&opts, prepared, &source).unwrap();
    let reads: Vec<_> = source
        .reads
        .iter()
        .map(|n| n.load(AtomicOrdering::SeqCst))
        .collect();
    let placebo = source.placebo.load(AtomicOrdering::SeqCst);
    let expected = match observer {
        ObserverMode::Count => 1,
        _ => 0,
    };
    assert_eq!(
        reads,
        vec![expected; source.len()],
        "actual test-source observer count"
    );
    assert_eq!(
        placebo,
        match observer {
            ObserverMode::Placebo => 5,
            _ => 0,
        }
    );
    let bytes = fs::read(&output).unwrap();
    println!(
        "M194D_INDEPENDENT_CONSUMER {}",
        serde_json::json!({"label":label,"path":output,"sha256":digest(&bytes),"reads":reads,"observer":format!("{observer:?}"),"placebo_count":placebo,"admission":format!("{:?}",opts.pyramid.admission),"fullres":align_cmd::fullres_gather_enabled(),"cropped":cropped})
    );
    bytes
}

fn digest(bytes: &[u8]) -> String {
    use sha2::Digest;
    sha2::Sha256::digest(bytes)
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}

#[test]
fn independent_candidate_layout_and_source_power() {
    let dir = match std::env::var("STREHL_M194D_INDEPENDENT_OUTPUT") {
        Ok(value) => PathBuf::from(value),
        Err(_) => Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../experiments/m194d-band-admission/independent-work")
            .join(format!(
                "{}-{}",
                std::process::id(),
                align_cmd::fullres_gather_enabled()
            )),
    };
    fs::create_dir_all(&dir).unwrap();
    let mode = AdmissionMode::FloorPedestalV1;
    let mut equalities = 0;
    let mut live = 0;
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
            mode,
        );
        for (name, observer) in [
            ("counter-off", ObserverMode::Off),
            ("counter-placebo", ObserverMode::Placebo),
        ] {
            let got = render_with_observer(
                frames.clone(),
                &dir,
                &format!("{prefix}-{name}"),
                cropped,
                mode,
                (false, false, observer),
            );
            assert_eq!(
                baseline, got,
                "test-source observer perturbs actual candidate bytes"
            );
        }
        for layout in [1, 2] {
            let mut relocated: Vec<_> = (0..5).map(|k| make_frame(274, 190, layout, k)).collect();
            let got = render(
                relocated.clone(),
                &dir,
                &format!("{prefix}-layout{layout}"),
                cropped,
                false,
                false,
                mode,
            );
            assert_eq!(
                baseline, got,
                "equivalent active layout changes candidate TIFF"
            );
            relocated.iter_mut().for_each(poison_outside);
            let poison = render(
                relocated,
                &dir,
                &format!("{prefix}-poison{layout}"),
                cropped,
                false,
                false,
                mode,
            );
            assert_eq!(baseline, poison, "unused buffer changes candidate TIFF");
            equalities += 2;
        }
        let mut site = frames.clone();
        site[2].data[95 * 274 + 136] += 500;
        let changed = render(
            site,
            &dir,
            &format!("{prefix}-single-site"),
            cropped,
            false,
            false,
            mode,
        );
        assert_ne!(baseline, changed, "genuine active-site control inert");
        let noise = render(
            frames.clone(),
            &dir,
            &format!("{prefix}-noise"),
            cropped,
            true,
            false,
            mode,
        );
        assert_ne!(baseline, noise, "injected model control inert");
        let warped = render(
            frames.clone(),
            &dir,
            &format!("{prefix}-warp"),
            cropped,
            false,
            true,
            mode,
        );
        assert_ne!(baseline, warped, "actual gather placement control inert");
        live += 3;
    }
    println!(
        "M194D_INDEPENDENT_CONSUMER_SUMMARY {}",
        serde_json::json!({"dir":dir,"layout_equalities":equalities,"observer_equalities":4,"live_controls":live,"tiffs":20,"stats_flags_used":false})
    );
}
