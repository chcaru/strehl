//! M194 path commissioning only: no physical focus/occlusion quality claim.
use super::*;
use std::fs;
use std::sync::atomic::AtomicUsize;
use strehl_core::align::{Similarity, SimilarityParams};
use strehl_core::warpmap::Provenance as WarpProvenance;
use strehl_raw::Region;

struct FixtureSource {
    frames: Vec<Frame>,
    calls: Vec<AtomicUsize>,
    fail_at: Option<usize>,
    fail_on_call: Option<(usize, usize)>,
    declared_len: usize,
}

impl FixtureSource {
    fn new(frames: Vec<Frame>) -> Self {
        let declared_len = frames.len();
        Self {
            frames,
            calls: (0..declared_len).map(|_| AtomicUsize::new(0)).collect(),
            fail_at: None,
            fail_on_call: None,
            declared_len,
        }
    }

    fn counts(&self) -> Vec<usize> {
        self.calls
            .iter()
            .map(|n| n.load(Ordering::SeqCst))
            .collect()
    }
}

impl PyramidFrameSource for FixtureSource {
    fn len(&self) -> usize {
        self.declared_len
    }

    fn decode(&self, index: usize) -> Result<Frame> {
        let call = self
            .calls
            .get(index)
            .context("fixture index outside source")?
            .fetch_add(1, Ordering::SeqCst)
            + 1;
        ensure!(
            self.fail_at != Some(index) && self.fail_on_call != Some((index, call)),
            "M194 injected source failure at index {index}, call {call}"
        );
        Ok(self.frames[index].clone())
    }
}

fn work_dir(label: &str) -> PathBuf {
    static NEXT: AtomicUsize = AtomicUsize::new(0);
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../experiments/m194-production-truth/work")
        .join(format!(
            "{label}-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::SeqCst)
        ));
    fs::create_dir_all(&path).unwrap();
    path
}

/// Non-square/padded RGGB stimulus. This is deliberately not a defocus model.
fn fixture_frame(width: usize, height: usize, k: usize) -> Frame {
    let (ax, ay) = (2, 4);
    let stride = width + ax + 5;
    let buffer_height = height + ay + 3;
    let mut data = vec![65000; stride * buffer_height];
    for y in 0..height {
        for x in 0..width {
            let site = (y % 2) * 2 + x % 2;
            let texture = ((x * 17 + y * 23 + (x * y) % 113 + k * 31) % 1300) as u16;
            data[(ay + y) * stride + ax + x] = 512 + [1400, 2300, 3100, 4200][site] + texture;
        }
    }
    Frame {
        data,
        stride,
        buffer_height,
        active: Region {
            x: ax,
            y: ay,
            width,
            height,
        },
        levels: Levels {
            black: 512.0,
            white: 15360.0,
        },
        iso: Some(200.0),
        wb_coeffs: [1.25, 1.0, 0.8, f32::NAN],
        xyz_to_cam_rgbe: [[0.0; 3]; 4],
        color_matrices: Vec::new(),
        camera: "M194 synthetic path stimulus".into(),
        path: PathBuf::from(format!("M194-NO-SUCH-RAW-{k}.ARW")),
    }
}

fn fixture_options(out: PathBuf) -> MergeOptions {
    MergeOptions {
        dir: PathBuf::from("M194-NO-SUCH-RAW-DIRECTORY"),
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
        pyramid: MergeConfig::default(),
    }
}

/// Metadata is deliberately prepared without decoding: counts cover the
/// shared body only. The real RAW wrapper's initial decode remains outside.
fn run_fixture(
    opts: &MergeOptions,
    source: &FixtureSource,
    placements: Option<Vec<FrameWarp>>,
    crop: Option<align_cmd::CropRect>,
) -> Result<()> {
    run_fixture_from(opts, &source.frames, source, placements, crop)
}

fn run_fixture_from(
    opts: &MergeOptions,
    frames: &[Frame],
    source: &impl PyramidFrameSource,
    placements: Option<Vec<FrameWarp>>,
    crop: Option<align_cmd::CropRect>,
) -> Result<()> {
    let first = frames.first().context("empty fixture")?;
    let paths: Vec<_> = frames.iter().map(|f| f.path.clone()).collect();
    ensure!(
        paths.iter().all(|p| !p.exists()),
        "fixture sentinel RAW path exists"
    );
    let geom = first.geometry();
    let levels = first.levels;
    let noise = profile::noise_model_for(&first.camera, first.iso, levels);
    let domain = match crop {
        Some(rect) => PyramidDomain::cropped(geom, rect)?,
        None => PyramidDomain::whole(geom),
    };
    let alignment = placements.map(|warps| {
        let entries: Vec<_> = paths
            .iter()
            .map(|p| (p.to_string_lossy(), first.allocated_bytes() as u64))
            .collect();
        let map = WarpMap::new(
            WarpProvenance {
                stack: StackIdentity::from_entries("M194 fixture", &entries),
                strategy: "M194 known placements, no solver".into(),
                heldout_px: None,
                cycle_floor_px: None,
                reference: 0,
                note: "input-path commissioning; not physical registration evidence".into(),
            },
            geom,
            opts.resampler,
            warps,
        );
        let fit = match crop {
            Some(rect) => align_cmd::CoverFit::Cropped { k: 1.0, rect },
            None => align_cmd::CoverFit::Uncovered,
        };
        (map, "M194-known-input", fit)
    });
    let local = domain.analysis();
    run_pyramid_prepared(
        opts,
        PreparedPyramid {
            paths: &paths,
            geom,
            levels,
            noise,
            wb: first.wb_gains(),
            xyz_to_cam: first.xyz_to_cam_rgb_with_source(),
            frame_bytes: first.allocated_bytes(),
            alignment,
            domain,
            sizes: level_sizes(local.width, local.height, opts.pyramid.bands),
            defect_plan: None,
            prologue_secs: 0.0,
            align_secs: 0.0,
            t_start: Instant::now(),
            exposure: Exposure::resolve(opts.srgb, opts.exposure, opts.auto_exposure)?,
        },
        source,
    )
}

fn read_tiff(path: &Path) -> (u32, u32, Vec<u16>, String) {
    let mut decoder = tiff::decoder::Decoder::new(fs::File::open(path).unwrap()).unwrap();
    let (width, height) = decoder.dimensions().unwrap();
    let software = decoder
        .get_tag_ascii_string(tiff::tags::Tag::Software)
        .unwrap();
    let tiff::decoder::DecodingResult::U16(pixels) = decoder.read_image().unwrap() else {
        panic!("writer did not emit u16 pixels")
    };
    assert_eq!(pixels.len(), width as usize * height as usize * 3);
    (width, height, pixels, software)
}

fn curved_placements(n: usize) -> Vec<FrameWarp> {
    (0..n)
        .map(|k| {
            let t = k as f64 / (n - 1) as f64;
            FrameWarp::Placed(Similarity::from_params(SimilarityParams {
                ax: 0.8 * t * t,
                ay: -0.6 * t * t,
                g: 0.004 * t + 0.012 * t * (1.0 - t),
                rot: 0.001 * t,
            }))
        })
        .collect()
}

#[test]
fn m194_actual_source_gather_fold_writer_controls() {
    let dir = work_dir("author");
    let frames: Vec<_> = (0..7).map(|k| fixture_frame(192, 136, k)).collect();
    let warps = curved_placements(frames.len());
    let [
        FrameWarp::Placed(start),
        FrameWarp::Placed(mid),
        FrameWarp::Placed(end),
    ] = [warps[0].clone(), warps[3].clone(), warps[6].clone()]
    else {
        panic!("the curved stimulus must place every selected frame")
    };
    let chord = Similarity {
        a: (start.a + end.a).scale(0.5),
        b: (start.b + end.b).scale(0.5),
    };
    assert!(
        mid.corner_err(chord, frames[0].geometry()) > 0.1,
        "the intermediate placement became a straight endpoint chord"
    );
    let sites: Vec<_> = BAND_PLANE_OFFSETS
        .iter()
        .map(|&(x, y)| frames[0].sample(x, y))
        .collect();
    assert!(sites.windows(2).all(|pair| pair[0] != pair[1]));
    let crop = align_cmd::CropRect {
        x: 3,
        y: 5,
        width: 84,
        height: 56,
    };
    let baseline = dir.join("baseline.tif");
    let mut opts = fixture_options(baseline.clone());
    let source = FixtureSource::new(frames.clone());
    run_fixture(&opts, &source, Some(warps.clone()), Some(crop)).unwrap();
    assert_eq!(source.counts(), vec![1; frames.len()]);
    let bytes = fs::read(&baseline).unwrap();
    let (w, h, pixels, software) = read_tiff(&baseline);
    assert_eq!((w, h), (168, 112));
    assert!(software.contains("strehl"));
    assert!(
        pixels.iter().min() < pixels.iter().max(),
        "stimulus became constant"
    );

    let same = FixtureSource::new(frames.clone());
    opts.out = Some(dir.join("same.tif"));
    run_fixture(&opts, &same, Some(warps.clone()), Some(crop)).unwrap();
    assert_eq!(bytes, fs::read(opts.out.as_ref().unwrap()).unwrap());

    let confidence = FixtureSource::new(frames.clone());
    opts.out = Some(dir.join("confidence-main.tif"));
    opts.confidence_map = Some(dir.join("confidence.tif"));
    run_fixture(&opts, &confidence, Some(warps.clone()), Some(crop)).unwrap();
    assert_eq!(confidence.counts(), vec![2; frames.len()]);
    assert_eq!(bytes, fs::read(opts.out.as_ref().unwrap()).unwrap());
    assert!(opts.confidence_map.as_ref().unwrap().is_file());
    opts.confidence_map = None;

    let mut changed = frames.clone();
    for y in 30..70 {
        for x in 30..90 {
            let i = (changed[3].active.y + y) * changed[3].stride + changed[3].active.x + x;
            changed[3].data[i] += 5000;
        }
    }
    opts.out = Some(dir.join("changed-frame.tif"));
    run_fixture(
        &opts,
        &FixtureSource::new(changed),
        Some(warps.clone()),
        Some(crop),
    )
    .unwrap();
    assert_ne!(pixels, read_tiff(opts.out.as_ref().unwrap()).2);

    let mut changed_warps = warps.clone();
    changed_warps[3] = FrameWarp::Placed(Similarity::from_params(SimilarityParams {
        ax: 4.0,
        ay: -3.0,
        g: 0.025,
        rot: 0.0,
    }));
    assert_eq!(warps[0], changed_warps[0]);
    assert_eq!(warps[6], changed_warps[6]);
    opts.out = Some(dir.join("changed-interior-warp.tif"));
    run_fixture(
        &opts,
        &FixtureSource::new(frames.clone()),
        Some(changed_warps),
        Some(crop),
    )
    .unwrap();
    assert_ne!(pixels, read_tiff(opts.out.as_ref().unwrap()).2);

    opts.demosaic = false;
    opts.out = Some(dir.join("binned.tif"));
    run_fixture(
        &opts,
        &FixtureSource::new(frames.clone()),
        Some(warps.clone()),
        Some(crop),
    )
    .unwrap();
    let binned = read_tiff(opts.out.as_ref().unwrap());
    assert_eq!((binned.0, binned.1), (84, 56));

    opts.out = Some(dir.join("source-failure.tif"));
    let mut fail = FixtureSource::new(frames.clone());
    fail.fail_at = Some(2);
    assert!(
        format!(
            "{:#}",
            run_fixture(&opts, &fail, Some(warps), Some(crop)).unwrap_err()
        )
        .contains("M194 injected source failure")
    );
    assert!(!opts.out.as_ref().unwrap().exists());
    let mut count = FixtureSource::new(frames);
    count.declared_len += 1;
    assert!(
        run_fixture(&opts, &count, None, None)
            .unwrap_err()
            .to_string()
            .contains("source count")
    );
    println!("M194 AUTHOR PATH CONTROLS PASS: {}", dir.display());
}

#[path = "../../../../experiments/m194-production-truth/independent-controls.rs"]
mod independent;

// Private output-coordinate and interpolation commissioning. These ignored
// tests use generated CFA sources and never participate in the product CLI.
mod m193c_output_grid {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/m193c-output-grid/private-adapter.rs"
    ));

    mod precision_witness {
        include!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../experiments/m193c-output-grid/precision-witness.rs"
        ));
    }
}

// Full native active-CFA derivatives for the separately released experiment.
mod m193c_registration_derivative {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/m193c-output-grid/registration-derivative.rs"
    ));
}
