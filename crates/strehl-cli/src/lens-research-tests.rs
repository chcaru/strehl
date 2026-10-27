//! Independent generated commission of the actual CPU consumers. No RAW files.
//! Frozen decisions and provenance: rea-a7c2-2026-10-24-l/consumer-commission-plan.md.
use super::*;
use crate::lens_research::{self, Arm, FramePull, NativeSimilarity, RadialCurve, ResearchPull};
use strehl_core::align::{Similarity, SimilarityParams};
use strehl_core::pyramid::Pyramid;
use strehl_core::warpmap::Provenance as MapProvenance;

const LEVELS: Levels = Levels {
    black: 512.0,
    white: 15360.0,
};
const SCALES: [f64; 9] = [
    1.0, 0.98563, 0.972665, 0.960025, 0.94686, 0.928585, 0.90907, 0.87959, 0.85714,
];
const NOISE_N: usize = 24;

fn curve(full: PlaneGeometry, dose: i16) -> RadialCurve {
    let radius = (full.width as f32).hypot(full.height as f32);
    RadialCurve {
        center: [full.width as f32 - 0.5, full.height as f32 - 0.5],
        reference_radius: radius,
        input_scale: 1.0,
        output_scale: 1.0,
        max_input_radius: radius * 2.0,
        knots: std::array::from_fn(|j| dose * (j * j) as i16),
    }
}
fn identity_native(full: PlaneGeometry) -> NativeSimilarity {
    lens_research::native_similarity(Similarity::IDENTITY, full)
}
fn placement(i: usize) -> Similarity {
    Similarity::from_params(SimilarityParams {
        ax: (i as f64 - 4.0) * 0.17,
        ay: (i as f64 - 4.0) * -0.11,
        g: SCALES[i] / SCALES[4] - 1.0,
        rot: (i as f64 - 4.0) * 0.0004,
    })
}
fn pull(
    full: PlaneGeometry,
    crop: align_cmd::CropRect,
    a: RadialCurve,
    s: RadialCurve,
    t: Similarity,
    ca: [NativeSimilarity; 3],
) -> FramePull {
    FramePull::new(
        ResearchPull {
            anchor: a,
            source: s,
            placement: lens_research::native_placement(t, full),
        },
        ca,
        crop,
    )
    .unwrap()
}

// Independent forward law in f64. No calls to candidate forward/inverse/map.
fn forward_ref(c: RadialCurve, p: [f64; 2]) -> [f64; 2] {
    let d = [p[0] - c.center[0] as f64, p[1] - c.center[1] as f64];
    let t = 15.0 * c.input_scale as f64 * d[0].hypot(d[1]) / c.reference_radius as f64;
    let i = (t.floor() as usize).min(14);
    let k = c.knots[i] as f64 + (t - i as f64) * (c.knots[i + 1] - c.knots[i]) as f64;
    let gain = c.output_scale as f64 * (1.0 + k / 16384.0);
    [
        c.center[0] as f64 + gain * d[0],
        c.center[1] as f64 + gain * d[1],
    ]
}
// Solve d = output_scale * r * (a+b*r) on the independently selected interval.
fn inverse_ref(c: RadialCurve, p: [f64; 2]) -> [f64; 2] {
    let d = [p[0] - c.center[0] as f64, p[1] - c.center[1] as f64];
    let rho = d[0].hypot(d[1]);
    if rho == 0.0 {
        return p;
    }
    let h = c.reference_radius as f64 / (15.0 * c.input_scale as f64);
    let mut i = 0;
    while i < 14 {
        let end = (i + 1) as f64 * h;
        let out = c.output_scale as f64 * end * (1.0 + c.knots[i + 1] as f64 / 16384.0);
        if rho <= out {
            break;
        }
        i += 1;
    }
    let b = (c.knots[i + 1] - c.knots[i]) as f64 / (16384.0 * h);
    let a = 1.0 + c.knots[i] as f64 / 16384.0 - b * i as f64 * h;
    let z = rho / c.output_scale as f64;
    let r = 2.0 * z / (a + (a * a + 4.0 * b * z).sqrt());
    [
        c.center[0] as f64 + d[0] * r / rho,
        c.center[1] as f64 + d[1] * r / rho,
    ]
}
fn apply_ref(t: NativeSimilarity, p: [f64; 2]) -> [f64; 2] {
    let x = p[0] - t.center[0] as f64;
    let y = p[1] - t.center[1] as f64;
    [
        t.center[0] as f64 + t.a[0] as f64 * x - t.a[1] as f64 * y + t.b[0] as f64,
        t.center[1] as f64 + t.a[1] as f64 * x + t.a[0] as f64 * y + t.b[1] as f64,
    ]
}
fn unapply_ref(t: NativeSimilarity, p: [f64; 2]) -> [f64; 2] {
    let x = p[0] - t.center[0] as f64 - t.b[0] as f64;
    let y = p[1] - t.center[1] as f64 - t.b[1] as f64;
    let den = (t.a[0] as f64).powi(2) + (t.a[1] as f64).powi(2);
    [
        t.center[0] as f64 + (t.a[0] as f64 * x + t.a[1] as f64 * y) / den,
        t.center[1] as f64 + (-t.a[1] as f64 * x + t.a[0] as f64 * y) / den,
    ]
}
fn scene(p: [f64; 2]) -> f32 {
    let (x, y) = (p[0] as f32, p[1] as f32);
    1700.0
        + 200.0 * (0.073 * x + 0.017 * y).sin()
        + 170.0 * (0.023 * x - 0.061 * y).cos()
        + 120.0 * (0.00012 * x * y + 0.008 * x).sin()
        + 100.0 * (0.00021 * x * x + 0.00016 * y * y).cos()
        + 90.0 * (0.13 * x + 0.101 * y).sin() * (0.019 * y).sin()
}
fn frame_with(
    full: PlaneGeometry,
    index: usize,
    mut value: impl FnMut(usize, usize) -> f32,
) -> Frame {
    let (width, height) = (2 * full.width, 2 * full.height);
    let (stride, buffer_height) = (width + 12, height + 14);
    let mut f = Frame {
        data: vec![63000; stride * buffer_height],
        stride,
        buffer_height,
        active: strehl_raw::Region {
            x: 4,
            y: 6,
            width,
            height,
        },
        levels: LEVELS,
        iso: Some(100.0),
        wb_coeffs: [1.0, 1.0, 1.0, f32::NAN],
        xyz_to_cam_rgbe: [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [0.0; 3]],
        color_matrices: Vec::new(),
        camera: "ILCE-7CM2".into(),
        path: PathBuf::from(format!("generated-lens-{index:03}.ARW")),
    };
    for y in 0..height {
        for x in 0..width {
            f.data[(y + 6) * stride + x + 4] =
                (LEVELS.black + value(x, y)).round().clamp(0.0, 65535.0) as u16;
        }
    }
    f
}
fn source_frame(
    full: PlaneGeometry,
    index: usize,
    source: RadialCurve,
    motion: NativeSimilarity,
    ca: [NativeSimilarity; 3],
) -> Frame {
    frame_with(full, index, |x, y| {
        let ci = match (x & 1, y & 1) {
            (0, 0) => 0,
            (1, 1) => 2,
            _ => 1,
        };
        scene(unapply_ref(
            motion,
            inverse_ref(source, unapply_ref(ca[ci], [x as f64, y as f64])),
        ))
    })
}
fn sample(f: &Frame, x: usize, y: usize) -> u16 {
    f.data[(y + f.active.y) * f.stride + x + f.active.x]
}
fn verify_padding(f: &Frame) {
    for y in 0..f.buffer_height {
        for x in 0..f.stride {
            if x < f.active.x
                || x >= f.active.x + f.active.width
                || y < f.active.y
                || y >= f.active.y + f.active.height
            {
                assert_eq!(
                    f.data[y * f.stride + x],
                    63000,
                    "synthetic padding consumed/modified"
                );
            }
        }
    }
}
fn gather(f: &Frame, full: PlaneGeometry, t: Similarity, p: &FramePull) -> Frame {
    let mut out = f.clone();
    align_cmd::warp_frame_lens_research::<false>(
        &mut out,
        t,
        full,
        Resampler::CatmullRom,
        &mut WarpScratch::new(full),
        p,
    )
    .unwrap();
    verify_padding(&out);
    out
}
fn crop_values(f: &Frame, r: align_cmd::CropRect) -> Vec<u16> {
    let mut v = Vec::with_capacity(4 * r.width * r.height);
    for y in 2 * r.y..2 * (r.y + r.height) {
        for x in 2 * r.x..2 * (r.x + r.width) {
            v.push(sample(f, x, y));
        }
    }
    v
}
fn identity_for(frames: &[Frame]) -> StackIdentity {
    let e: Vec<_> = frames
        .iter()
        .map(|f| {
            (
                f.path.to_string_lossy().into_owned(),
                f.allocated_bytes() as u64,
            )
        })
        .collect();
    StackIdentity::from_entries("generated-lens-consumer", &e)
}
fn map_for(frames: &[Frame], full: PlaneGeometry, ts: &[Similarity]) -> WarpMap {
    WarpMap::new(
        MapProvenance {
            stack: identity_for(frames),
            strategy: "generated-forward-truth".into(),
            heldout_px: None,
            cycle_floor_px: None,
            reference: frames.len() / 2,
            note: "operator control only".into(),
        },
        full,
        Resampler::CatmullRom,
        ts.iter().copied().map(FrameWarp::Placed).collect(),
    )
}
struct Sources {
    frames: Vec<Frame>,
    pulls: Vec<FramePull>,
    decodes: AtomicUsize,
    lookups: AtomicUsize,
}
impl Sources {
    fn new(frames: Vec<Frame>, pulls: Vec<FramePull>) -> Self {
        Self {
            frames,
            pulls,
            decodes: AtomicUsize::new(0),
            lookups: AtomicUsize::new(0),
        }
    }
}
impl PyramidFrameSource for Sources {
    fn len(&self) -> usize {
        self.frames.len()
    }
    fn decode(&self, index: usize) -> Result<Frame> {
        self.decodes.fetch_add(1, Ordering::SeqCst);
        Ok(self.frames[index].clone())
    }
    fn lens_pull(&self, index: usize) -> Result<Option<&FramePull>> {
        self.lookups.fetch_add(1, Ordering::SeqCst);
        Ok(Some(&self.pulls[index]))
    }
}
fn load_luma(s: &Sources, index: usize, d: PyramidDomain, map: &WarpMap) -> Vec<f32> {
    let mut planes: Vec<_> = (0..BAND_PLANES)
        .map(|_| vec![0.0; d.analysis().pixels()])
        .collect();
    let mut l = vec![0.0; d.analysis().pixels()];
    assert!(
        load_frame(
            s,
            index,
            d,
            LEVELS,
            Some(map),
            None,
            &mut WarpScratch::new(d.full),
            None,
            &mut planes,
            &mut l
        )
        .unwrap()
    );
    l
}
fn dist(a: [f64; 2], b: [f64; 2]) -> f64 {
    (a[0] - b[0]).hypot(a[1] - b[1])
}
fn flat_controls(full: PlaneGeometry, r: align_cmd::CropRect) {
    let f = frame_with(full, 0, |_, _| 1024.0);
    let original = f.data.clone();
    let t = Similarity::from_params(SimilarityParams {
        ax: 0.25,
        ay: -0.4,
        g: -0.03,
        rot: 0.015,
    });
    for (a, s) in [(0, 0), (2, 2), (1, 3)] {
        let p = pull(
            full,
            r,
            curve(full, a),
            curve(full, s),
            t,
            [identity_native(full); 3],
        );
        let out = gather(&f, full, t, &p);
        assert!(
            crop_values(&out, r).iter().all(|&v| v == 1536),
            "flat DC control {a}/{s}"
        );
    }
    assert_eq!(f.data, original);
    eprintln!("LENS-COMMISSION flat: zero/common/variable exact DC; u16 source/padding unchanged");
}
fn gauge_controls(full: PlaneGeometry, r: align_cmd::CropRect) {
    let t = Similarity::from_params(SimilarityParams {
        ax: 0.25,
        ay: -0.4,
        g: -0.08,
        rot: 0.06,
    });
    let lift = lens_research::native_placement(t, full);
    let old = lens_research::native_similarity(t, full);
    let mut error = 0.0_f64;
    let mut phase = 0.0_f64;
    for (x, y) in [(31, 27), (91, 71), (145, 99)] {
        for (dx, dy) in [(0, 0), (1, 0), (0, 1), (1, 1)] {
            let p = [(2 * x + dx) as f64, (2 * y + dy) as f64];
            let (u, v) = t.apply_at(
                (p[0] - 0.5) / 2.0 - r.x as f64,
                (p[1] - 0.5) / 2.0 - r.y as f64,
                r.width as f64 / 2.0,
                r.height as f64 / 2.0,
            );
            let expected = [2.0 * (u + r.x as f64) + 0.5, 2.0 * (v + r.y as f64) + 0.5];
            error = error.max(dist(expected, apply_ref(lift, p)));
            phase = phase.max(dist(expected, apply_ref(old, p)));
        }
    }
    assert!(error <= 0.001, "physical lift error={error}");
    assert!(phase > 0.001, "old phase falsifier inactive: {phase}");
    let mut ca = identity_native(full);
    ca.a = [1.013, 0.011];
    ca.b = [0.3, -0.2];
    let a = curve(full, 2);
    let s = curve(full, 4);
    let p = pull(full, r, a, s, t, [ca; 3]);
    let mut wrong_order = 0.0_f64;
    let mut omitted = 0.0_f64;
    let mut assignment = 0.0_f64;
    for xy in [[60.0, 50.0], [290.0, 60.0], [65.0, 220.0], [300.0, 220.0]] {
        let correct = apply_ref(ca, forward_ref(s, apply_ref(lift, inverse_ref(a, xy))));
        let got = p.map_native([xy[0] as f32, xy[1] as f32], 1).unwrap();
        assert!(dist(correct, [got[0] as f64, got[1] as f64]) <= 0.001);
        wrong_order = wrong_order.max(dist(
            correct,
            forward_ref(s, apply_ref(lift, inverse_ref(a, apply_ref(ca, xy)))),
        ));
        omitted = omitted.max(dist(
            correct,
            apply_ref(ca, forward_ref(s, apply_ref(lift, xy))),
        ));
        assignment = assignment.max(dist(
            correct,
            apply_ref(ca, forward_ref(a, apply_ref(lift, inverse_ref(a, xy)))),
        ));
    }
    assert!(
        wrong_order > 0.001 && omitted > 0.05 && assignment > 0.05,
        "inactive geometry falsifier order={wrong_order} omitted={omitted} table={assignment}"
    );
    let z = curve(full, 0);
    let f = source_frame(
        full,
        0,
        z,
        identity_native(full),
        [identity_native(full); 3],
    );
    let zero = pull(full, r, z, z, t, [identity_native(full); 3]);
    let out = gather(&f, full, t, &zero);
    let mut shifted = t.to_params();
    // Complex A: (I-A)*[.25,.25], in plane units.
    shifted.ax += 0.25 * (1.0 - t.a.re + t.a.im);
    shifted.ay += 0.25 * (1.0 - t.a.re - t.a.im);
    let mut legacy = f.clone();
    align_cmd::warp_frame_in_place_fullres(
        &mut legacy,
        Similarity::from_params(shifted),
        full,
        Resampler::CatmullRom,
        &mut WarpScratch::new(full),
    )
    .unwrap();
    let maxdn = crop_values(&out, r)
        .iter()
        .zip(crop_values(&legacy, r))
        .map(|(&a, b)| a.abs_diff(b))
        .max()
        .unwrap();
    assert!(
        maxdn <= 1,
        "f32-vs-lifted-f64 gather discrepancy {maxdn} DN"
    );
    let mut unadjusted = f.clone();
    align_cmd::warp_frame_in_place_fullres(
        &mut unadjusted,
        t,
        full,
        Resampler::CatmullRom,
        &mut WarpScratch::new(full),
    )
    .unwrap();
    let phase_changed = crop_values(&out, r)
        .iter()
        .zip(crop_values(&unadjusted, r))
        .filter(|(a, b)| **a != *b)
        .count();
    assert!(
        phase_changed > 0,
        "unadjusted legacy phase image falsifier inactive"
    );
    eprintln!(
        "LENS-COMMISSION gauge: phase_intervention_changed_sites={phase_changed} lift_max_px={error} old_phase_px={phase} wrong_order_px={wrong_order} omitted_px={omitted} table_px={assignment} lifted_legacy_max_dn={maxdn}"
    );
}

struct Rng(u64);
impl Rng {
    fn uniform(&mut self) -> f32 {
        self.0 = self.0.wrapping_add(0x9e3779b97f4a7c15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94d049bb133111eb);
        z ^= z >> 31;
        ((z >> 40) as f32 + 0.5) / 16777216.0
    }
    fn normal(&mut self) -> f32 {
        let u = self.uniform();
        let v = self.uniform();
        (-2.0 * u.ln()).sqrt() * (std::f32::consts::TAU * v).cos()
    }
}
fn equal_coefficients(a: &[f32], b: &[f32]) {
    assert_eq!(a.len(), b.len());
    for (&x, &y) in a.iter().zip(b) {
        assert!(x.to_bits() == y.to_bits() || (x.is_nan() && y.is_nan()));
    }
}
fn noise_controls(full: PlaneGeometry, r: align_cmd::CropRect, noise: &NoiseModel) {
    let d = PyramidDomain::cropped(full, r).unwrap();
    let sizes = level_sizes(r.width, r.height, 3);
    let mut pyr = Pyramid::zeros(&sizes);
    let mut ws = Workspace::new(&sizes);
    let t = Similarity::from_params(SimilarityParams {
        ax: 0.25,
        ay: 0.25,
        g: 0.0,
        rot: 0.0,
    });
    let p = pull(
        full,
        r,
        curve(full, 1),
        curve(full, 2),
        t,
        [identity_native(full); 3],
    );
    let wrong = pull(
        full,
        r,
        curve(full, 0),
        curve(full, 0),
        Similarity::IDENTITY,
        [identity_native(full); 3],
    );
    let template = frame_with(full, 0, |_, _| 1024.0);
    let mut probe = gatefloor::Probe::new(d, 3);
    let mut scratch = WarpScratch::new(full);
    let mut avg = 0.0_f64;
    let mut wrong_avg = 0.0_f64;
    let mut mean = vec![0.0_f64; r.width * r.height];
    let mut m2 = mean.clone();
    let sigma = noise.plane(CfaPlane::G1).sigma(1024.0);
    let mut rng = Rng(0x6c656e735f6e6f69);
    for n in 0..NOISE_N {
        let green = probe
            .measure_research_with_gather(
                &template,
                n,
                t,
                Resampler::CatmullRom,
                &mut scratch,
                &p,
                true,
            )
            .unwrap()
            .to_vec();
        let rgb = probe
            .measure_research_with_gather(
                &template,
                n,
                t,
                Resampler::CatmullRom,
                &mut scratch,
                &p,
                false,
            )
            .unwrap()
            .to_vec();
        equal_coefficients(&green, &rgb);
        let default = probe
            .measure_research(&template, n, t, Resampler::CatmullRom, &mut scratch, &p)
            .unwrap()
            .to_vec();
        equal_coefficients(&green, &default);
        assert!(green[0].is_finite() && green[0] > 0.0);
        avg += green[0] as f64;
        wrong_avg += probe
            .measure_research_with_gather(
                &template,
                n,
                Similarity::IDENTITY,
                Resampler::CatmullRom,
                &mut scratch,
                &wrong,
                true,
            )
            .unwrap()[0] as f64;
        let frame = frame_with(full, n, |_, _| 1024.0 + sigma * rng.normal());
        let s = Sources::new(vec![frame], vec![p]);
        let map = map_for(&s.frames, full, &[t]);
        let mut l = load_luma(&s, 0, d, &map);
        let center = l.iter().copied().sum::<f32>() / l.len() as f32;
        for x in &mut l {
            *x -= center;
        }
        pyr.build(&l, &mut ws);
        for (i, &v) in pyr.level(0).iter().enumerate() {
            let delta = v as f64 - mean[i];
            mean[i] += delta / (n + 1) as f64;
            m2[i] += delta * (v as f64 - mean[i]);
        }
    }
    let mut sum = 0.0;
    let mut count = 0;
    let mx = (r.width / 8).max(3);
    let my = (r.height / 8).max(3);
    for y in my..r.height - my {
        for x in mx..r.width - mx {
            sum += m2[y * r.width + x] / (NOISE_N - 1) as f64;
            count += 1;
        }
    }
    let measured = sum / count as f64 / (0.5 * noise.plane(CfaPlane::G1).variance(1024.0) as f64);
    avg /= NOISE_N as f64;
    wrong_avg /= NOISE_N as f64;
    let ratio = measured / avg;
    let wrong_ratio = measured / wrong_avg;
    eprintln!(
        "LENS-COMMISSION noise: temporal_beta={measured} nonlinear_probe_beta={avg} identity_probe_beta={wrong_avg} ratio={ratio} wrong_ratio={wrong_ratio} n={NOISE_N} model={noise:?}"
    );
    assert!(
        (0.90..=1.10).contains(&ratio),
        "actual nonlinear probe fails independent temporal control"
    );
    assert!(
        (wrong_ratio - 1.0).abs() > 0.10,
        "wrong probe falsifier inactive"
    );
}
fn detail_error(frame: &Frame, anchor: RadialCurve, r: align_cmd::CropRect) -> [f64; 4] {
    let mut sq = [0.0; 4];
    let mut n = [0; 4];
    for y in 2 * r.y..2 * (r.y + r.height) {
        for x in 2 * r.x..2 * (r.x + r.width) {
            let phase = (y & 1) * 2 + (x & 1);
            let truth = scene(inverse_ref(anchor, [x as f64, y as f64]));
            let e = sample(frame, x, y) as f32 - LEVELS.black - truth;
            sq[phase] += (e as f64).powi(2);
            n[phase] += 1;
        }
    }
    std::array::from_fn(|i| (sq[i] / n[i] as f64).sqrt())
}
fn detail_and_confidence(full: PlaneGeometry, r: align_cmd::CropRect, noise: &NoiseModel) {
    let d = PyramidDomain::cropped(full, r).unwrap();
    let a = curve(full, 2);
    let doses = [1, 2, 4];
    let ids = [0, 4, 8];
    let ts: Vec<_> = ids.into_iter().map(placement).collect();
    let mut ca = [identity_native(full); 3];
    ca[0].a = [1.003, 0.001];
    ca[0].b = [0.15, -0.1];
    ca[2].a = [0.997, -0.001];
    ca[2].b = [-0.12, 0.08];
    let mut frames = Vec::new();
    let mut pulls = Vec::new();
    let mut correct = 0.0;
    let mut wrong_table = 0.0;
    let mut omitted = 0.0;
    for (j, &i) in ids.iter().enumerate() {
        let c = curve(full, doses[j]);
        let frame = source_frame(full, i, c, lens_research::native_placement(ts[j], full), ca);
        let p = pull(full, r, a, c, ts[j], ca);
        let out = gather(&frame, full, ts[j], &p);
        let e = detail_error(&out, a, r);
        assert!(
            e.iter().all(|v| *v <= 2.0),
            "correct gather per-phase RMSE {e:?}"
        );
        correct += e.iter().sum::<f64>() / 4.0;
        let bad = pull(full, r, a, curve(full, doses[2 - j]), ts[j], ca);
        wrong_table += detail_error(&gather(&frame, full, ts[j], &bad), a, r)
            .iter()
            .sum::<f64>()
            / 4.0;
        let bad = pull(full, r, curve(full, 0), c, ts[j], ca);
        omitted += detail_error(&gather(&frame, full, ts[j], &bad), a, r)
            .iter()
            .sum::<f64>()
            / 4.0;
        eprintln!("LENS-COMMISSION gather: frame={i} correct_rmse_by_physical_phase={e:?}");
        frames.push(frame);
        pulls.push(p);
    }
    correct /= 3.0;
    wrong_table /= 3.0;
    omitted /= 3.0;
    eprintln!(
        "LENS-COMMISSION gather falsifiers: correct={correct} wrong_table={wrong_table} omitted_anchor_inverse={omitted}"
    );
    assert!(wrong_table > correct + 1.0 && omitted > correct + 1.0);
    // Constant and forced-zero table arms have no hidden arm-dependent consumer.
    for dose in [0, 2] {
        let c = curve(full, dose);
        let t = ts[2];
        let f = source_frame(full, 8, c, lens_research::native_placement(t, full), ca);
        let supplied = [c; 3];
        let varying = lens_research::curves_for_arm(&supplied, 1, Arm::PerFrame).unwrap();
        let fixed = lens_research::curves_for_arm(&supplied, 1, Arm::AnchorFixed).unwrap();
        let per_frame = pull(full, r, varying[1], varying[2], t, ca);
        let anchor_fixed = pull(full, r, fixed[1], fixed[2], t, ca);
        let got = crop_values(&gather(&f, full, t, &per_frame), r);
        assert_eq!(got, crop_values(&gather(&f, full, t, &anchor_fixed), r));
        if dose == 0 {
            let zeros = lens_research::curves_for_arm(&supplied, 1, Arm::ForcedZero).unwrap();
            let forced = pull(full, r, zeros[1], zeros[2], t, ca);
            assert_eq!(got, crop_values(&gather(&f, full, t, &forced), r));
        }
    }
    let source = Sources::new(frames, pulls);
    let map = map_for(&source.frames, full, &ts);
    let paths: Vec<_> = source.frames.iter().map(|f| f.path.clone()).collect();
    let cfg = MergeConfig {
        bands: 3,
        ..MergeConfig::default()
    };
    let mut worker = BandWorker::new(d, cfg);
    for (i, &t) in ts.iter().enumerate() {
        assert!(
            worker
                .fold(&source, i, LEVELS, noise, Some(&map), None)
                .unwrap()
        );
        let expected = gatefloor::Probe::new(d, 3)
            .measure_research(
                &source.frames[i],
                i,
                t,
                Resampler::CatmullRom,
                &mut WarpScratch::new(full),
                &source.pulls[i],
            )
            .unwrap()
            .to_vec();
        assert!(!worker.beta.is_empty());
        for (a, b) in worker.beta.iter().zip(expected.iter()) {
            assert_eq!(a.to_bits(), b.to_bits());
        }
    }
    let merged = worker
        .merge
        .finish(&mut Workspace::new(&level_sizes(r.width, r.height, 3)));
    assert!(merged.iter().flatten().all(|v| v.is_finite()));
    // Explicit CFA slots prevent an RGB/quad-order assumption in this reference.
    let merged_luma: Vec<_> = merged[band_slot(CfaPlane::G1)]
        .iter()
        .zip(&merged[band_slot(CfaPlane::G2)])
        .map(|(a, b)| 0.5 * (a + b))
        .collect();
    let mut below = vec![0_u32; r.width * r.height];
    for i in 0..source.len() {
        for (b, (l, m)) in below
            .iter_mut()
            .zip(load_luma(&source, i, d, &map).iter().zip(&merged_luma))
        {
            *b += u32::from(l < m);
        }
    }
    let before = (
        source.decodes.load(Ordering::SeqCst),
        source.lookups.load(Ordering::SeqCst),
    );
    let got = confidence_pass(
        &source,
        &paths,
        d,
        LEVELS,
        Some(&map),
        None,
        &merged_luma,
        source.len(),
    )
    .unwrap();
    assert_eq!(got.below, below);
    assert!(got.seen.iter().all(|&v| v == source.len() as u32));
    assert_eq!(
        source.decodes.load(Ordering::SeqCst) - before.0,
        source.len()
    );
    assert_eq!(
        source.lookups.load(Ordering::SeqCst) - before.1,
        source.len()
    );
    let misbound = Sources::new(
        source.frames.clone(),
        source.pulls.iter().rev().copied().collect(),
    );
    assert!(
        confidence_pass(
            &misbound,
            &paths,
            d,
            LEVELS,
            Some(&map),
            None,
            &merged_luma,
            misbound.len()
        )
        .is_err(),
        "confidence accepted wrong placement binding"
    );
    let wrong = Sources::new(
        source.frames.clone(),
        ts.iter()
            .enumerate()
            .map(|(i, &t)| pull(full, r, a, curve(full, doses[2 - i]), t, ca))
            .collect(),
    );
    let bad = confidence_pass(
        &wrong,
        &paths,
        d,
        LEVELS,
        Some(&map),
        None,
        &merged_luma,
        wrong.len(),
    )
    .unwrap();
    let changed = got
        .below
        .iter()
        .zip(&bad.below)
        .filter(|(a, b)| a != b)
        .count();
    assert!(
        changed > 0,
        "confidence wrong-source-pull falsifier inactive"
    );
    eprintln!(
        "LENS-COMMISSION confidence: exact strict counts, all {} sources reread; wrong-source-pull changes {changed}/{} sites",
        source.len(),
        below.len()
    );
}

fn solver_crop() -> (PlaneGeometry, align_cmd::CropRect, [i16; 9]) {
    let full = PlaneGeometry {
        width: 640,
        height: 576,
    };
    let doses = [1, 1, 2, 2, 2, 3, 3, 4, 4];
    let curves: Vec<_> = doses.iter().map(|&dose| curve(full, dose)).collect();
    let failed = align_cmd::CropRect {
        x: 16,
        y: 16,
        width: 608,
        height: 544,
    };
    let native = [32.5, 32.5, 1246.5, 1118.5];
    let g = ResearchPull {
        anchor: curve(full, 0),
        source: curve(full, 4),
        placement: identity_native(full),
    };
    assert!(
        !g.covers(native, [1280, 1152], 4.0, identity_native(full)),
        "failed fixed16 crop passed certificate"
    );
    let original = vec![1024.0; full.pixels()];
    assert!(align_cmd::remap_lens_guide(&original, full, failed, curve(full, 4)).is_err());
    let r = lens_research::guide_crop_for_curves(full, &curves).unwrap();
    assert_eq!(r.x, r.y);
    assert_eq!(r.x * 2 + r.width, full.width);
    assert_eq!(r.y * 2 + r.height, full.height);
    assert!(
        r.width / 8 > 60 && r.height / 8 > 60,
        "certified crop cannot support nondegenerate production coarse grid"
    );
    assert!(align_cmd::remap_lens_guide(&original, full, r, curve(full, 4)).is_ok());
    let query = forward_ref(curve(full, 4), [32.5, 32.5]);
    eprintln!(
        "LENS-COMMISSION crop: actual-production-selected=[{},{},{},{}] coarse={}x{} failed16-source={query:?} failed16-guide=[{},{}] minimum_checked_guide=1.5",
        r.x,
        r.y,
        r.width,
        r.height,
        r.width / 8,
        r.height / 8,
        (query[0] - 0.5) / 2.0,
        (query[1] - 0.5) / 2.0
    );
    (full, r, doses)
}
#[test]
fn lens_research_guide_crop_commission() {
    solver_crop();
}
fn solver_controls() {
    let (full, r, doses) = solver_crop();
    let ca = [identity_native(full); 3];
    // Reject malformed inputs and a real flat graph before textured fits.
    let flat_frames: Vec<_> = (0..3).map(|i| frame_with(full, i, |_, _| 1024.0)).collect();
    let flat: Vec<_> = flat_frames
        .iter()
        .map(|f| align_cmd::lens_guide(f, curve(full, 0), full, r).unwrap())
        .collect();
    assert!(
        align_cmd::solve_lens_guides(identity_for(&flat_frames), full, r, flat.clone(), 1).is_err()
    );
    let mut malformed = flat.clone();
    malformed[0].pop();
    assert!(
        align_cmd::solve_lens_guides(identity_for(&flat_frames), full, r, malformed, 1).is_err()
    );
    let mut nonfinite = flat;
    nonfinite[0][0] = f32::NAN;
    assert!(
        align_cmd::solve_lens_guides(identity_for(&flat_frames), full, r, nonfinite, 1).is_err()
    );
    let frames: Vec<_> = (0..9)
        .map(|i| {
            source_frame(
                full,
                i,
                curve(full, doses[i]),
                lens_research::native_placement(placement(i), full),
                ca,
            )
        })
        .collect();
    let mut correct_max = f64::INFINITY;
    let supplied: Vec<_> = doses.iter().map(|&dose| curve(full, dose)).collect();
    assert!(lens_research::curves_for_arm(&[], 0, Arm::PerFrame).is_err());
    assert!(lens_research::curves_for_arm(&supplied, 9, Arm::AnchorFixed).is_err());
    for (arm, selection) in [
        ("per-frame", Arm::PerFrame),
        ("forced-zero", Arm::ForcedZero),
        ("anchor-fixed", Arm::AnchorFixed),
    ] {
        let curves = lens_research::curves_for_arm(&supplied, 4, selection).unwrap();
        let guides: Vec<_> = frames
            .iter()
            .zip(&curves)
            .map(|(f, &c)| align_cmd::lens_guide(f, c, full, r).unwrap())
            .collect();
        let (map, receipt) =
            align_cmd::solve_lens_guides(identity_for(&frames), full, r, guides, 1)
                .unwrap_or_else(|e| panic!("{arm} actual generated global solve refused: {e:#}"));
        lens_research::validate_solve(&receipt, 9).unwrap();
        assert_eq!(
            map.warp(4).unwrap(),
            &FrameWarp::Placed(Similarity::IDENTITY)
        );
        assert!(receipt.cycle_rank > 0);
        assert_eq!(receipt.guide_crop, [r.x, r.y, r.width, r.height]);
        assert_eq!(receipt.threads, 1);
        let mut errors = Vec::new();
        for i in 0..9 {
            let FrameWarp::Placed(t) = map.warp(i).unwrap() else {
                panic!("refused source {i}")
            };
            let p = pull(full, r, curves[4], curves[i], *t, ca);
            let mut maximum = 0.0_f64;
            for x in [320.0, 640.0, 960.0] {
                for y in [288.0, 576.0, 864.0] {
                    let truth = forward_ref(
                        curve(full, doses[i]),
                        apply_ref(
                            lens_research::native_placement(placement(i), full),
                            inverse_ref(curve(full, doses[4]), [x, y]),
                        ),
                    );
                    let got = p.map_native([x as f32, y as f32], 1).unwrap();
                    maximum = maximum.max(dist(truth, [got[0] as f64, got[1] as f64]));
                }
            }
            errors.push(maximum);
        }
        let maximum = errors.iter().copied().fold(0.0_f64, f64::max);
        eprintln!(
            "LENS-COMMISSION solve: arm={arm} requested={} accepted={} cycles={} native_site_max={maximum} by_frame={errors:?} policy={} pair={} global={}",
            receipt.requested_pairs.len(),
            receipt.accepted_edges.len(),
            receipt.cycle_rank,
            receipt.guide_policy,
            receipt.pair_config,
            receipt.global_config
        );
        if arm == "per-frame" {
            correct_max = maximum;
            let mut duplicate = receipt.clone();
            duplicate
                .accepted_edges
                .push(duplicate.accepted_edges[0].clone());
            duplicate.cycle_rank += 1;
            assert!(lens_research::validate_solve(&duplicate, 9).is_err());
            // Enough unique measured-looking edges/cycles do not prove connectivity.
            let mut disconnected = receipt.clone();
            disconnected.accepted_edges = receipt
                .requested_pairs
                .iter()
                .filter(|p| p[1] < 6)
                .map(|p| {
                    let mut e = receipt.accepted_edges[0].clone();
                    e.pair = *p;
                    e
                })
                .collect();
            assert!(disconnected.accepted_edges.len() >= 9);
            disconnected.cycle_rank = disconnected.accepted_edges.len() + 1 - 9;
            assert!(lens_research::validate_solve(&disconnected, 9).is_err());
        }
    }
    assert!(
        correct_max <= 2.0,
        "actual guide/refit placement error={correct_max} native px"
    );
}

#[test]
fn lens_research_actual_consumer_commission() {
    // A fresh test process supplies defaults. Never mutate process-global switches.
    for key in [
        "STREHL_GATE_FLOOR",
        "STREHL_GATE_FLOOR_SCALE",
        "STREHL_PROBE_GATHER",
        "STREHL_FULLRES_GATHER",
        "STREHL_WARP_WRITEBACK",
        "STREHL_DIRECT_PLANES",
        "STREHL_RESEARCH_LENS_MAP",
        "STREHL_FIX_CA",
        "STREHL_SPATIAL_NOISE_FLOOR",
    ] {
        assert!(
            std::env::var_os(key).is_none(),
            "commission requires unset {key}"
        );
    }
    assert!(align_cmd::fullres_gather_enabled());
    assert!(gatefloor::enabled());
    assert!(gatefloor::probe_gather_uses_green().unwrap());
    rayon::ThreadPoolBuilder::new()
        .num_threads(1)
        .build()
        .unwrap()
        .install(|| {
            let full = PlaneGeometry {
                width: 192,
                height: 144,
            };
            let r = align_cmd::CropRect {
                x: 24,
                y: 18,
                width: 144,
                height: 108,
            };
            let noise = profile::noise_model_for("ILCE-7CM2", Some(100.0), LEVELS);
            assert_eq!(noise.provenance, strehl_core::noise::Provenance::Profile);
            assert!(noise.prnu().is_none());
            flat_controls(full, r);
            gauge_controls(full, r);
            noise_controls(full, r, &noise);
            detail_and_confidence(full, r, &noise);
            solver_controls();
        });
}
