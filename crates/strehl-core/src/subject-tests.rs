//! Synthetic-frame tests of the selection (plan S5's unit gates).

use super::*;

/// xorshift64* with Box-Muller normals; deterministic.
struct Rng(u64);

impl Rng {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        self.0.wrapping_mul(0x2545_f491_4f6c_dd1d)
    }
    fn uniform(&mut self) -> f64 {
        (self.next() >> 11) as f64 / (1u64 << 53) as f64
    }
    fn normal(&mut self) -> f64 {
        let u = self.uniform().max(1e-300);
        let v = self.uniform();
        (-2.0 * u.ln()).sqrt() * (std::f64::consts::TAU * v).cos()
    }
}

const BLACK: f32 = 512.0;
const WHITE: f32 = 15360.0;
const W: usize = 640;
const H: usize = 480;
const DISC: (f64, f64, f64) = (300.0, 250.0, 120.0);
/// The textured disc's rim width, px.
const RIM: f64 = 24.0;

/// The A7CR profile's ISO 100 green model, in DN.
fn variance(s: f32) -> f32 {
    0.404 * s.max(0.0) + 1.334 * 1.334
}

/// Cosine step from 1 (inside) to 0 over `ramp` pixels centred on radius
/// `r0`: a soft edge, as a defocused rim.
fn soft(d: f64, r0: f64, ramp: f64) -> f64 {
    let t = ((d - r0) / ramp + 0.5).clamp(0.0, 1.0);
    0.5 * (1.0 + (std::f64::consts::PI * t).cos())
}

/// A CFA frame: backdrop at `back` DN, a disc at `disc` DN with a soft rim
/// `ramp` px wide, whose texture has amplitude `texture(r / R)` (uniform,
/// +- that many DN per sample) inside the radius, plus sensor noise drawn
/// from [`variance`].
fn raw_frame(seed: u64, back: f64, disc: f64, ramp: f64, texture: &dyn Fn(f64) -> f64) -> Vec<u16> {
    let mut rng = Rng(seed.wrapping_mul(0x9e37_79b9_7f4a_7c15) | 1);
    let mut out = vec![0u16; W * H];
    for y in 0..H {
        for x in 0..W {
            let d = (x as f64 - DISC.0).hypot(y as f64 - DISC.1);
            let r = d / DISC.2;
            let mut s = back + (disc - back) * soft(d, DISC.2, ramp);
            if r < 1.0 {
                s += texture(r) * (2.0 * rng.uniform() - 1.0);
            }
            s += rng.normal() * f64::from(variance(s as f32)).sqrt();
            out[y * W + x] = (s + f64::from(BLACK)).round().clamp(0.0, 16383.0) as u16;
        }
    }
    out
}

fn evidence_of(frames: &[Vec<u16>]) -> Evidence {
    let cells: Vec<FrameCells> = frames
        .iter()
        .map(|d| {
            let v = CfaView {
                data: d,
                stride: W,
                x0: 0,
                y0: 0,
                width: W,
                height: H,
                black: BLACK,
                white: WHITE,
            };
            raw_frame_cells(&v, &variance)
        })
        .collect();
    let planes = (0..frames.len())
        .map(|k| PlaneRef {
            ordinal: 10 + k as u64,
            position: Some(1000.0 + 7.0 * k as f64),
        })
        .collect();
    assemble(cells, planes, raw_layout(W, H), Registration::Fit)
}

/// Nine planes; the disc's texture is sharp around plane 4 and fades away
/// from it, as a subject passing through focus.
fn disc_stack(texture: &dyn Fn(f64) -> f64) -> Evidence {
    let frames: Vec<Vec<u16>> = (0..9)
        .map(|k| {
            let a = (-(k as f64 - 4.0).powi(2) / (2.0 * 1.5f64.powi(2))).exp();
            raw_frame(k as u64 + 1, 150.0, 2000.0, RIM, &|r| a * texture(r))
        })
        .collect();
    evidence_of(&frames)
}

fn count(m: &[bool]) -> usize {
    m.iter().filter(|&&v| v).count()
}

/// Noise alone sits near one in the injected model's units: the model, not
/// a fitted floor, normalises the evidence.
#[test]
fn noise_alone_is_near_the_floor() {
    let f = raw_frame(7, 900.0, 900.0, RIM, &|_| 0.0);
    let v = CfaView {
        data: &f,
        stride: W,
        x0: 0,
        y0: 0,
        width: W,
        height: H,
        black: BLACK,
        white: WHITE,
    };
    let c = raw_frame_cells(&v, &variance);
    let mean = c.energy.iter().sum::<f32>() / c.energy.len() as f32;
    assert!((mean - 1.0).abs() < 0.05, "{mean}");
}

#[test]
fn a_textured_disc_is_found_within_a_few_cells() {
    let e = disc_stack(&|_| 300.0);
    let q = quiet(&e);
    let p = Params::default();
    let s = select(&e, &q, &p);
    assert_eq!(s.stats.threshold, ThresholdKind::Relative);
    assert_eq!(s.stats.parts, 1, "{}", s.summary);
    // Expected outline: the textured disc, at most its soft rim (whose level
    // differs from the backdrop: growth takes it), plus the 16 px buffer.
    let inner = DISC.2 / 8.0;
    let outer = (DISC.2 + RIM / 2.0 + 16.0) / 8.0;
    let mut misplaced = 0;
    for y in 0..e.rows {
        for x in 0..e.cols {
            let d = ((x as f64 + 0.5) * 8.0 - DISC.0).hypot((y as f64 + 0.5) * 8.0 - DISC.1) / 8.0;
            let inside = s.mask[y * e.cols + x];
            if (d < inner - 3.0 && !inside) || (d > outer + 3.0 && inside) {
                misplaced += 1;
            }
        }
    }
    assert_eq!(misplaced, 0, "{}", s.summary);
    let d = s.depth.expect("depth range");
    let (first, last) = (e.planes[d.first].ordinal, e.planes[d.last].ordinal);
    assert!(first >= 12 && last <= 16, "{first} {last}");
    assert_eq!(s.rings.len(), 1);
    assert!(s.rings[0].len() <= MAX_RING_POINTS);
    // The rings fill back to the raster.
    let back = rasterize(&s.rings, e.cols, e.rows, e.layout.cell_norm);
    let inter = back.iter().zip(&s.mask).filter(|(a, b)| **a && **b).count();
    let union = back.iter().zip(&s.mask).filter(|(a, b)| **a || **b).count();
    assert!(inter as f64 / union as f64 > 0.97);
    // The registration found no magnification change.
    let fit = e.registration.expect("fitted");
    assert!((fit.scale.unwrap() - 1.0).abs() <= 0.002, "{fit:?}");
}

#[test]
fn a_blank_frame_gives_an_empty_mask_and_says_so() {
    let frames: Vec<Vec<u16>> = (0..9)
        .map(|k| raw_frame(100 + k, 300.0, 300.0, RIM, &|_| 0.0))
        .collect();
    let e = evidence_of(&frames);
    let s = select(&e, &quiet(&e), &Params::default());
    assert_eq!(count(&s.mask), 0);
    assert!(s.rings.is_empty());
    assert!(s.depth.is_none());
    assert!(s.summary.starts_with("No subject"), "{}", s.summary);
}

/// A defocused bright blob on a dark backdrop, never sharp: its level
/// differs from the backdrop, but without in-focus evidence it is not a
/// subject.
#[test]
fn an_out_of_focus_blob_is_not_a_subject() {
    let frames: Vec<Vec<u16>> = (0..9)
        .map(|k| raw_frame(200 + k, 150.0, 2000.0, 80.0, &|_| 0.0))
        .collect();
    let e = evidence_of(&frames);
    let s = select(&e, &quiet(&e), &Params::default());
    assert_eq!(count(&s.mask), 0, "{}", s.summary);
    assert!(s.summary.starts_with("No subject"));
}

#[test]
fn higher_sensitivity_shrinks_monotonically() {
    // Texture fading towards the rim: evidence graded across the disc.
    let e = disc_stack(&|r| 600.0 * (1.0 - r).max(0.0));
    let q = quiet(&e);
    for grow in [0.0, 3.0] {
        let mut prev: Option<Vec<bool>> = None;
        let mut areas = Vec::new();
        for sens in [2.5, 3.0, 4.0, 6.0, 8.0, 12.0] {
            let s = select(
                &e,
                &q,
                &Params {
                    sensitivity: sens,
                    grow,
                    buffer_px: 16.0,
                },
            );
            if let Some(p) = &prev {
                assert!(
                    s.mask.iter().zip(p).all(|(a, b)| !*a || *b),
                    "grow {grow}: sensitivity {sens} is not inside the lower one"
                );
            }
            areas.push(count(&s.mask));
            prev = Some(s.mask);
        }
        assert!(areas[0] > 0, "{areas:?}");
        if grow == 0.0 {
            assert!(areas.last().unwrap() < &areas[0], "{areas:?}");
        }
    }
}

/// Live view: an RGB8 sweep whose disc is sharp in the middle frames.
fn live_frames(texture: bool, disc: f64, rim: f64) -> Vec<Vec<u8>> {
    let (w, h) = (320usize, 240usize);
    (0..10)
        .map(|k| {
            let mut rng = Rng(1000 + k as u64);
            let a = if texture {
                (-(k as f64 - 5.0).powi(2) / 2.0).exp()
            } else {
                0.0
            };
            let mut out = vec![0u8; 3 * w * h];
            for y in 0..h {
                for x in 0..w {
                    let d = (x as f64 - 150.0).hypot(y as f64 - 130.0);
                    let mut v = 25.0 + disc * soft(d, 60.0, rim) + 1.5 * rng.normal();
                    if d < 60.0 {
                        v += a * 90.0 * (2.0 * rng.uniform() - 1.0);
                    }
                    let v = v.round().clamp(0.0, 255.0) as u8;
                    out[3 * (y * w + x)..3 * (y * w + x) + 3].copy_from_slice(&[v, v, v]);
                }
            }
            out
        })
        .collect()
}

#[test]
fn live_view_finds_a_textured_disc_loosely() {
    let frames = live_frames(true, 115.0, 8.0);
    let views: Vec<LiveFrame> = frames
        .iter()
        .map(|f| LiveFrame {
            rgb: f,
            width: 320,
            height: 240,
        })
        .collect();
    let (e, s) = live_view_subject(&views, None, [9504, 6336], &Params::live());
    assert_eq!(e.layout.source, Source::LiveView);
    assert_eq!(s.stats.parts, 1, "{}", s.summary);
    // Cells are 4 live px; the disc's radius is 15 cells. Loose: allow a
    // margin outside, nothing missing well inside.
    let mut missing = 0;
    let mut far = 0;
    for y in 0..e.rows {
        for x in 0..e.cols {
            let d = ((x as f64 + 0.5) * 4.0 - 150.0).hypot((y as f64 + 0.5) * 4.0 - 130.0) / 4.0;
            let inside = s.mask[y * e.cols + x];
            missing += usize::from(d < 12.0 && !inside);
            far += usize::from(d > 21.0 && inside);
        }
    }
    assert_eq!((missing, far), (0, 0), "{}", s.summary);
    let ring = &s.rings[0];
    let (mut lo, mut hi) = (1.0f32, 0.0f32);
    for p in ring {
        lo = lo.min(p[0]);
        hi = hi.max(p[0]);
    }
    // Normalised to the frame (= the active area).
    assert!(lo > 0.2 && hi < 0.8, "{lo} {hi}");
}

/// A blank sweep gives nothing. (A bright untextured blob is not a test
/// here: live view's noise is normalised by one quiet level per frame, so
/// brighter areas carry more noise energy than the backdrop; that is the
/// live outline's known looseness, and the RAW outline does not share it.)
#[test]
fn live_view_of_a_blank_sweep_is_empty() {
    let frames = live_frames(false, 0.0, 40.0);
    let views: Vec<LiveFrame> = frames
        .iter()
        .map(|f| LiveFrame {
            rgb: f,
            width: 320,
            height: 240,
        })
        .collect();
    let (_, s) = live_view_subject(&views, None, [9504, 6336], &Params::live());
    assert_eq!(count(&s.mask), 0, "{}", s.summary);
}
