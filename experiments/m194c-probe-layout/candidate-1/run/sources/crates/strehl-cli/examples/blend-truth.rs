//! Two-layer synthetic scene with **known ground truth**, scoring the shipped
//! per-pixel selection merge and the BUILD-BLEND multi-band merge on the same
//! scene, with the same instruments.
//!
//! # Why this exists
//!
//! Every number this project has been burned by was a number that could be
//! satisfied by injected structure. Gradient energy went up when an agent
//! measured its own blotchy artifact; high-pass energy went up on crops chosen
//! for containing no structure. A scene whose correct answer is known **by
//! construction** cannot be gamed that way: you can only score well by being
//! close to the right picture.
//!
//! `merge_cmd/halo.rs` cites "a synthetic two-layer scene with known ground
//! truth (M87 section 6.3)" as the instrument that caught the occlusion filter
//! making the image measurably more wrong while making the halo metric look
//! `-79.8%` better. This is that instrument, rebuilt in-crate so both merge
//! arms can be run through it directly. The CLI only ingests `.arw` from a
//! directory, so a synthetic scene cannot be fed through the normal route.
//!
//! # The two instruments, and why neither is sufficient alone
//!
//! - **ISO** (M87 §2.1) is edge-referenced isotonic-residual overshoot. It
//!   answers "is there a non-monotone bump in the edge-normal profile", which
//!   is what the rim *is*. M87 records its failure direction explicitly: **"a
//!   reconstruction that flattens the band by discarding information"** also
//!   scores well. Blur passes ISO.
//! - **RMSE against truth** answers "is this the right picture". Blur fails it.
//!
//! Run together on a scene with known truth, the pair is not gameable by either
//! cheat: you cannot flatten the band without moving away from truth, and you
//! cannot match truth while leaving a rim. That is the whole reason to build a
//! synthetic scene rather than argue about a photograph.
//!
//! # The scenes
//!
//! - `occluding` — a foreground layer at one depth partially covering a
//!   background at another, composited through a **blurred matte**, which is
//!   the compositing model that actually produces occlusion halos. This is the
//!   `flower-bud` / `lavendar` analogue.
//! - `texture` — one layer, dense texture, **no silhouette anywhere**. This is
//!   the `couch-fibers-cpl` analogue and the do-no-harm guard. ORCH's standing
//!   rule is that a change which improves the rim and damages this is rejected.
//!
//! Both polarities of the occluding scene are run (dark subject on bright
//! backdrop, and bright subject on dark backdrop), because the rim reverses
//! sign between `flower-bud` and `lavendar` and a fix that only works on one
//! polarity is not a fix.

use anyhow::Result;
use strehl_core::focus::FocusField;
use strehl_core::plane::PlaneGeometry;
use strehl_core::merge::regularise;
use strehl_core::noise::{Levels, NoiseModel, PlaneNoise, Provenance};
use strehl_core::pyramid::{BandMerge, FrameWorkspace, MergeConfig, Workspace, level_sizes};

const W: usize = 512;
const H: usize = 384;
/// The silhouette sits here, with `>= 64 px` of clean backdrop to its right so
/// an ISO profile never runs off the plane.
const EDGE_X: usize = 200;
const FRAMES: usize = 48;
/// Circle-of-confusion radius grows this fast as the focus plane leaves a
/// layer. Over 48 frames the far layer reaches ~23 px of blur, comparable to
/// the real brackets where the backdrop is far out of focus.
const COC_PER_FRAME: f32 = 0.55;
/// The foreground's depth at row `y`.
///
/// **The subject spans most of the bracket, and that is not cosmetic.** M87
/// §16.5 records that the flower's subject spans 248 of 299 frames p10-p90,
/// and that a *global* foreground depth removes only 1.2% of its halo because
/// "no single frame is the foreground". An earlier version of this scene put
/// the whole foreground at a single depth, and the resulting selection merge
/// scored only 2.1x its own single-frame null where M87's real merge scores
/// 2617x — the scene did not contain the defect it was built to adjudicate.
///
/// Depth varies with `y` only, so each row is an independent and physically
/// consistent 1-D occlusion problem — which is also exactly the unit ISO
/// scores, since it takes one profile per row and medians over them.
fn fg_depth(y: usize) -> f32 {
    2.0 + (FRAMES as f32 - 4.0) * (y as f32 / (H - 1) as f32)
}
/// **Deliberately outside the bracket.** On the real subjects the backdrop
/// never comes into focus — BUILD-HALO §17.2 records the fern as "a subject
/// with no sharp frame anywhere in the bracket", and the flower-bud's white
/// card is the same. An earlier version of this harness put the background at
/// frame 36 of 48, *inside* the sweep, which let the selection arm win the far
/// field by simply electing frame 36 everywhere. That is not the regime the
/// rim lives in, and it made the whole scene the wrong test.
const BG_DEPTH: f32 = 78.0;

/// White level of the synthetic sensor, matching the real stacks' 14-bit range.
const WHITE: f32 = 15360.0;

// ---------------------------------------------------------------------------
// scene
// ---------------------------------------------------------------------------

/// A cheap deterministic hash-based value noise. Deterministic across runs and
/// platforms, which matters because this harness is a measuring instrument.
fn hash2(x: i32, y: i32, seed: u32) -> f32 {
    let mut h = (x as u32).wrapping_mul(0x8da6_b343);
    h ^= (y as u32).wrapping_mul(0xd8163841);
    h ^= seed.wrapping_mul(0xcb1a_b31f);
    h ^= h >> 15;
    h = h.wrapping_mul(0x2c1b_3c6d);
    h ^= h >> 12;
    h = h.wrapping_mul(0x297a_2d39);
    h ^= h >> 15;
    (h & 0xff_ffff) as f32 / 16_777_215.0
}

fn smooth_noise(x: f32, y: f32, seed: u32) -> f32 {
    let (x0, y0) = (x.floor(), y.floor());
    let (fx, fy) = (x - x0, y - y0);
    let (sx, sy) = (fx * fx * (3.0 - 2.0 * fx), fy * fy * (3.0 - 2.0 * fy));
    let (xi, yi) = (x0 as i32, y0 as i32);
    let a = hash2(xi, yi, seed);
    let b = hash2(xi + 1, yi, seed);
    let c = hash2(xi, yi + 1, seed);
    let d = hash2(xi + 1, yi + 1, seed);
    let top = a + (b - a) * sx;
    let bot = c + (d - c) * sx;
    top + (bot - top) * sy
}

/// Multi-octave texture. Real subjects carry detail at many scales at once,
/// which is the whole argument for a multi-scale merge, so a single-scale test
/// texture would beg the question this harness is asked to answer.
fn texture(x: usize, y: usize, seed: u32) -> f32 {
    let (fx, fy) = (x as f32, y as f32);
    let mut v = 0.0;
    let mut amp = 1.0;
    let mut freq = 1.0 / 24.0;
    let mut norm = 0.0;
    for o in 0..5 {
        v += amp * smooth_noise(fx * freq, fy * freq, seed.wrapping_add(o * 7919));
        norm += amp;
        amp *= 0.55;
        freq *= 2.3;
    }
    v / norm
}

/// Pillbox (disc) defocus, the physically correct out-of-focus kernel for a
/// circular aperture. A Gaussian would be easier and would understate the
/// problem: a disc has a hard rim, and hard-rimmed bokeh is what makes
/// occlusion halos sharp enough to see.
///
/// Cost is `O(radius)` per pixel, not `O(radius^2)`: for each vertical offset
/// the disc's horizontal extent is a contiguous run, so a per-row prefix sum
/// makes each row's contribution `O(1)` per pixel.
fn disc_blur(src: &[f32], w: usize, h: usize, radius: f32, dst: &mut [f32]) {
    let r = radius.round() as i32;
    if r <= 0 {
        dst.copy_from_slice(src);
        return;
    }
    let mut prefix = vec![0.0f32; (w + 1) * h];
    for y in 0..h {
        let row = &src[y * w..y * w + w];
        let pr = &mut prefix[y * (w + 1)..y * (w + 1) + w + 1];
        let mut acc = 0.0;
        pr[0] = 0.0;
        for x in 0..w {
            acc += row[x];
            pr[x + 1] = acc;
        }
    }
    let rr = (r * r) as f32;
    for y in 0..h {
        for x in 0..w {
            let mut sum = 0.0;
            let mut count = 0.0;
            for dy in -r..=r {
                let sy = y as i32 + dy;
                let sy = sy.clamp(0, h as i32 - 1) as usize;
                let ext = (rr - (dy * dy) as f32).max(0.0).sqrt() as i32;
                let x0 = (x as i32 - ext).clamp(0, w as i32 - 1) as usize;
                let x1 = (x as i32 + ext).clamp(0, w as i32 - 1) as usize;
                let pr = &prefix[sy * (w + 1)..sy * (w + 1) + w + 1];
                sum += pr[x1 + 1] - pr[x0];
                count += (x1 - x0 + 1) as f32;
            }
            dst[y * w + x] = sum / count;
        }
    }
}

struct Scene {
    fg: Vec<f32>,
    bg: Vec<f32>,
    alpha: Vec<f32>,
    truth: Vec<f32>,
    /// `true` when the scene has a silhouette to score ISO against.
    has_edge: bool,
    name: &'static str,
}

/// `fg_level` and `bg_level` are mean signal in DN. Swapping them flips the
/// rim's polarity, which is the difference between `flower-bud` and `lavendar`.
fn occluding_scene(name: &'static str, fg_level: f32, bg_level: f32) -> Scene {
    let n = W * H;
    let (mut fg, mut bg, mut alpha) = (vec![0.0; n], vec![0.0; n], vec![0.0; n]);
    for y in 0..H {
        for x in 0..W {
            let i = y * W + x;
            fg[i] = fg_level * (0.55 + 0.9 * texture(x, y, 11));
            // A backdrop that is never in focus is **smooth**, and it must be
            // here for a second reason: ISO reads non-monotonicity of the
            // edge-normal profile, and M87 §2.1 names "background texture with
            // a scale near the rim width" as a thing that scores. An earlier
            // version of this scene gave the backdrop the same contrast as the
            // subject, and the instrument's own null caught it — ground truth
            // itself scored 0.04856 against a selection merge's 0.05558, i.e.
            // the metric was reading texture, not rim. Keep this smooth or the
            // ISO column means nothing.
            bg[i] = bg_level * (0.985 + 0.03 * texture(x, y, 977));
            // A straight, pixel-aligned silhouette. The outward normal is then
            // exactly +x and ISO needs no normal estimation at all, so any
            // overshoot it reports is the image's, not the instrument's.
            alpha[i] = if x < EDGE_X { 1.0 } else { 0.0 };
        }
    }
    // **Achievable** ground truth, not ideal ground truth.
    //
    // The background is out of bracket, so no frame contains a sharp version of
    // it and no stacker can produce one. Scoring against a sharp background
    // would measure the optics, not the merge: both arms would be penalised by
    // the same large constant for failing to invent detail that was never
    // captured, and that constant would swamp the difference under test.
    //
    // The correct target is what the *best possible* stacker could output: the
    // foreground sharp (frame 12 has it), and the background at the least blur
    // any frame in the bracket contains.
    let best_bg_r = (0..FRAMES)
        .map(|k| ((k as f32 - BG_DEPTH).abs() * COC_PER_FRAME * 100.0) as i32)
        .min()
        .unwrap() as f32
        / 100.0;
    let mut bg_best = vec![0.0f32; n];
    disc_blur(&bg, W, H, best_bg_r, &mut bg_best);
    let truth: Vec<f32> = (0..n)
        .map(|i| alpha[i] * fg[i] + (1.0 - alpha[i]) * bg_best[i])
        .collect();
    Scene { fg, bg, alpha, truth, has_edge: true, name }
}

/// The `couch-fibers-cpl` analogue: dense multi-scale texture at a *range* of
/// depths, and no silhouette anywhere. Depth varies smoothly across the frame
/// so every pixel has a genuine best frame, which is what makes this a real
/// test of acuity rather than a test of copying one frame.
fn texture_scene() -> Scene {
    let n = W * H;
    let (mut fg, mut alpha) = (vec![0.0; n], vec![0.0; n]);
    for y in 0..H {
        for x in 0..W {
            let i = y * W + x;
            fg[i] = 0.5 * WHITE * (0.5 + 1.0 * texture(x, y, 4242));
            alpha[i] = 1.0;
        }
    }
    let truth = fg.clone();
    Scene { fg, bg: vec![0.0; n], alpha, truth, has_edge: false, name: "texture" }
}

/// Per-pixel depth for the texture scene.
///
/// **Varies at pixel scale, not as a smooth ramp.** `couch-fibers-cpl` is a
/// tangle of filaments at many depths interleaved at pixel scale — BUILD-HALO
/// §17.1 identifies that as exactly why an adaptive-radius rule collapses there
/// and turns the image to mush. A smooth depth ramp would be a much easier
/// scene and would not test the thing this guard exists to test.
fn texture_depth(x: usize, y: usize) -> f32 {
    let t = smooth_noise(x as f32 / 3.0, y as f32 / 3.0, 31337);
    2.0 + t * (FRAMES as f32 - 5.0)
}

/// Render frame `k`, compositing through a **blurred matte**.
///
/// This is the part that matters. The foreground and its own alpha are blurred
/// together by the foreground's defocus, and the background is blurred by its
/// own; the composite is `fg_pre + bg_blur * (1 - alpha_blur)`. That is the
/// standard occlusion model, and the reason a defocused foreground *spreads its
/// own silhouette outward over the backdrop* — which is precisely the mechanism
/// that gives a selection merge a rim to inherit.
fn render_frame(scene: &Scene, k: usize, out: &mut [f32], seed: u32) {
    let n = W * H;
    if !scene.has_edge {
        // Depth varies per pixel, so build the frame by blurring the whole
        // plane at each distinct radius once and then selecting per pixel.
        // `blurs[r]` is the plane at circle-of-confusion radius `r`.
        let max_r = (FRAMES as f32 * COC_PER_FRAME).ceil() as usize + 1;
        let mut blurs: Vec<Vec<f32>> = Vec::with_capacity(max_r + 1);
        for r in 0..=max_r {
            let mut b = vec![0.0f32; n];
            disc_blur(&scene.fg, W, H, r as f32, &mut b);
            blurs.push(b);
        }
        for y in 0..H {
            for x in 0..W {
                let d = texture_depth(x, y);
                let r = (((k as f32 - d).abs() * COC_PER_FRAME).round() as usize).min(max_r);
                out[y * W + x] = blurs[r][y * W + x];
            }
        }
    } else {
        let r_bg = (k as f32 - BG_DEPTH).abs() * COC_PER_FRAME;
        let premult: Vec<f32> = (0..n).map(|i| scene.fg[i] * scene.alpha[i]).collect();
        let mut bg_bl = vec![0.0f32; n];
        disc_blur(&scene.bg, W, H, r_bg, &mut bg_bl);
        // The foreground's defocus varies by row, so blur once per distinct
        // radius and take each row from the plane matching its own depth.
        let max_r = (FRAMES as f32 * COC_PER_FRAME).ceil() as usize + 1;
        let mut fg_pre = vec![0.0f32; n];
        let mut alpha_bl = vec![0.0f32; n];
        let (mut tp, mut ta) = (vec![0.0f32; n], vec![0.0f32; n]);
        let mut last = usize::MAX;
        for y in 0..H {
            let r = ((((k as f32 - fg_depth(y)).abs() * COC_PER_FRAME).round()) as usize)
                .min(max_r);
            if r != last {
                disc_blur(&premult, W, H, r as f32, &mut tp);
                disc_blur(&scene.alpha, W, H, r as f32, &mut ta);
                last = r;
            }
            fg_pre[y * W..y * W + W].copy_from_slice(&tp[y * W..y * W + W]);
            alpha_bl[y * W..y * W + W].copy_from_slice(&ta[y * W..y * W + W]);
        }
        for i in 0..n {
            out[i] = fg_pre[i] + bg_bl[i] * (1.0 - alpha_bl[i]);
        }
    }
    // Shot + read noise at the real profile's scale, so the noise gate in the
    // multi-band merge is exercised rather than bypassed.
    let noise = synthetic_noise();
    for (i, v) in out.iter_mut().enumerate() {
        let sigma = noise.green_luma_sigma(*v);
        let u1 = hash2((i % W) as i32, (i / W) as i32, seed.wrapping_add(k as u32 * 31 + 1))
            .max(1e-6);
        let u2 = hash2((i % W) as i32, (i / W) as i32, seed.wrapping_add(k as u32 * 31 + 2));
        let g = (-2.0 * u1.ln()).sqrt() * (std::f32::consts::TAU * u2).cos();
        *v = (*v + sigma * g).max(0.0);
    }
}

/// A noise model in the same regime as the real A7C II profile at ISO 200.
fn synthetic_noise() -> NoiseModel {
    let levels = Levels { black: 512.0, white: 15360.0 };
    let p = PlaneNoise { gain_dn_per_e: 0.62, read_noise_e: 3.4, levels };
    NoiseModel::new([p, p, p, p], 200.0, Provenance::Profile)
}

// ---------------------------------------------------------------------------
// arm A -- the shipped per-pixel selection merge
// ---------------------------------------------------------------------------

/// Focus measure -> `regularise` -> per-pixel argmax -> gather.
///
/// Assembled from the **shipped** primitives (`FocusField::compute`,
/// `merge::regularise`) rather than reimplemented, so this is the real
/// operator's behaviour and not a strawman built to lose.
fn merge_selection(frames: &[Vec<f32>], geom: PlaneGeometry) -> (Vec<f32>, Vec<u16>) {
    let n = geom.pixels();
    let noise = synthetic_noise();
    let mut field = FocusField::new(geom);
    let mut scratch = vec![0.0f32; n];
    let mut reg = vec![0.0f32; n];
    let mut best = vec![f32::NEG_INFINITY; n];
    let mut winner = vec![0u16; n];
    for (k, f) in frames.iter().enumerate() {
        field.compute(f, &noise);
        regularise(field.values(), geom, &mut scratch, &mut reg);
        for i in 0..n {
            if reg[i] > best[i] {
                best[i] = reg[i];
                winner[i] = k as u16;
            }
        }
    }
    let out: Vec<f32> = (0..n).map(|i| frames[winner[i] as usize][i]).collect();
    (out, winner)
}

// ---------------------------------------------------------------------------
// arm B -- the multi-band merge
// ---------------------------------------------------------------------------

fn merge_multiband(frames: &[Vec<f32>], geom: PlaneGeometry, cfg: MergeConfig) -> Vec<f32> {
    let n = geom.pixels();
    let noise = synthetic_noise();
    let sizes = level_sizes(geom.width, geom.height, cfg.bands);
    let mut merge = BandMerge::new(geom.width, geom.height, 1, cfg);
    let mut fws = FrameWorkspace::new(&sizes, 1);
    let mut var = vec![0.0f32; n];
    for f in frames {
        for i in 0..n {
            let s = noise.green_luma_sigma(f[i]);
            var[i] = s * s;
        }
        fws.next_frame();
        merge.add_frame(&[f.as_slice()], f, &var, &mut fws);
    }
    let planes = merge.finish(&mut Workspace::new(&sizes));
    planes[0].clone()
}

// ---------------------------------------------------------------------------
// the oracle -- the achievable floor
// ---------------------------------------------------------------------------

/// The true depth at a pixel, which the oracle is allowed to know.
fn true_depth(scene: &Scene, x: usize, y: usize) -> f32 {
    if scene.has_edge {
        if scene.alpha[y * W + x] > 0.5 { fg_depth(y) } else { BG_DEPTH }
    } else {
        texture_depth(x, y)
    }
}

/// A stacker that knows the scene's depth map exactly and elects the nearest
/// frame per pixel. It is **not** allowed to see the answer — it sees the
/// geometry, which is the most any election could ever recover.
///
/// M87 §26.3's rule, learned the hard way on this project: *"score arms against
/// an achievable floor, not against each other. A ratio between two arms is
/// uninterpretable until you know where the ceiling is."* Without this row,
/// "blend is 32% worse than selection" could mean either arm is close to
/// perfect or both are far from it.
fn merge_oracle(scene: &Scene, frames: &[Vec<f32>]) -> Vec<f32> {
    let mut out = vec![0.0f32; W * H];
    for y in 0..H {
        for x in 0..W {
            let d = true_depth(scene, x, y);
            let k = (d.round() as usize).min(FRAMES - 1);
            out[y * W + x] = frames[k][y * W + x];
        }
    }
    out
}

// ---------------------------------------------------------------------------
// instruments
// ---------------------------------------------------------------------------

fn rmse(a: &[f32], b: &[f32], mask: impl Fn(usize, usize) -> bool) -> f32 {
    let mut acc = 0.0f64;
    let mut cnt = 0u64;
    for y in 0..H {
        for x in 0..W {
            if mask(x, y) {
                let d = (a[y * W + x] - b[y * W + x]) as f64;
                acc += d * d;
                cnt += 1;
            }
        }
    }
    if cnt == 0 { return f32::NAN; }
    ((acc / cnt as f64).sqrt()) as f32
}

/// Pool-adjacent-violators isotonic regression.
fn pava(y: &[f32], increasing: bool) -> Vec<f32> {
    let s: Vec<f32> = if increasing { y.to_vec() } else { y.iter().map(|v| -v).collect() };
    let mut val: Vec<f32> = Vec::with_capacity(s.len());
    let mut wgt: Vec<f32> = Vec::with_capacity(s.len());
    for &v in &s {
        val.push(v);
        wgt.push(1.0);
        while val.len() > 1 && val[val.len() - 2] > val[val.len() - 1] {
            let (v1, w1) = (val.pop().unwrap(), wgt.pop().unwrap());
            let (v0, w0) = (val.pop().unwrap(), wgt.pop().unwrap());
            val.push((v0 * w0 + v1 * w1) / (w0 + w1));
            wgt.push(w0 + w1);
        }
    }
    let mut out = Vec::with_capacity(s.len());
    for (v, w) in val.iter().zip(&wgt) {
        for _ in 0..(*w as usize) {
            out.push(if increasing { *v } else { -*v });
        }
    }
    out
}

fn gauss1d(v: &[f32], sigma: f32) -> Vec<f32> {
    let r = (3.0 * sigma).ceil() as i32;
    let k: Vec<f32> = (-r..=r)
        .map(|d| (-(d * d) as f32 / (2.0 * sigma * sigma)).exp())
        .collect();
    let ksum: f32 = k.iter().sum();
    (0..v.len())
        .map(|i| {
            let mut acc = 0.0;
            for (j, kv) in k.iter().enumerate() {
                let idx = (i as i32 + j as i32 - r).clamp(0, v.len() as i32 - 1) as usize;
                acc += v[idx] * kv;
            }
            acc / ksum
        })
        .collect()
}

/// **ISO — isotonic-residual overshoot**, M87 §2.1, ported exactly.
///
/// The silhouette here is straight and pixel-aligned, so the outward normal is
/// exactly `+x` and profiles need no bilinear resampling. That removes the
/// normal-estimation error M87's v1 had to fight, and it means a non-zero
/// score is a property of the image rather than of the profile geometry.
///
/// Its null is a physical statement, not a fitted baseline: a defocused
/// occluding edge in a **single exposure** has a monotone edge-spread profile,
/// so any single frame must score ~0. That null is measured and reported.
fn score_iso(img: &[f32]) -> f32 {
    let mut scores: Vec<f32> = Vec::with_capacity(H);
    for y in 0..H {
        let s: Vec<f32> = (0..=64).map(|d| img[y * W + (EDGE_X + d).min(W - 1)]).collect();
        let mut tail: Vec<f32> = s[48..=64].to_vec();
        tail.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let asymptote = tail[tail.len() / 2];
        if asymptote.abs() < 1e-6 {
            continue;
        }
        let q: Vec<f32> = s.iter().map(|v| v / asymptote).collect();
        let qs = gauss1d(&q, 3.0);
        let increasing = qs[64] >= qs[0];
        let m = pava(&qs, increasing);
        let mut o = f32::NEG_INFINITY;
        for d in 3..=40 {
            o = o.max(qs[d] - m[d]);
        }
        scores.push(o);
    }
    if scores.is_empty() {
        return f32::NAN;
    }
    scores.sort_by(|a, b| a.partial_cmp(b).unwrap());
    scores[scores.len() / 2]
}

/// The largest jump in elected frame index between horizontally adjacent
/// pixels. BUILD-CHROMA measured up to 191 frames on a real 299-frame bracket;
/// a coefficient-space merge never forms this field at all, so it cannot
/// inherit the failure of box-filtering across such a jump.
fn max_index_jump(winner: &[u16]) -> (u16, f64) {
    let mut max = 0u16;
    let mut acc = 0f64;
    let mut cnt = 0u64;
    for y in 0..H {
        for x in 1..W {
            let a = winner[y * W + x] as i32;
            let b = winner[y * W + x - 1] as i32;
            let d = (a - b).unsigned_abs() as u16;
            max = max.max(d);
            acc += d as f64;
            cnt += 1;
        }
    }
    (max, acc / cnt as f64)
}

// ---------------------------------------------------------------------------

fn run_scene(scene: &Scene) -> Result<()> {
    let geom = PlaneGeometry { width: W, height: H };
    println!("\n=== scene: {} ===", scene.name);

    let mut frames: Vec<Vec<f32>> = Vec::with_capacity(FRAMES);
    for k in 0..FRAMES {
        let mut f = vec![0.0f32; W * H];
        render_frame(scene, k, &mut f, 7);
        frames.push(f);
    }

    let (sel, winner) = merge_selection(&frames, geom);
    let blend = merge_multiband(&frames, geom, MergeConfig::default());
    let oracle = merge_oracle(scene, &frames);

    // Bands, following M87: the artifact lives within one window support of the
    // silhouette (SUPPORT_RADIUS = 14), and ORCH's single-frame reference put
    // the departure at 10-20 px. Everything past 40 px is scene.
    let band = |x: usize, _y: usize| scene.has_edge && x > EDGE_X && x <= EDGE_X + 20;
    let far = |x: usize, _y: usize| scene.has_edge && x > EDGE_X + 40 && x < W - 8;
    let all = |x: usize, _y: usize| x >= 8 && x < W - 8;

    // Fraction of the headroom between the selection arm and the achievable
    // floor that an arm captures. 100% is the oracle; 0% is the selection arm;
    // negative is worse than the selection arm.
    let headroom = |arm: f32, sel: f32, orc: f32| {
        if (sel - orc).abs() < 1e-9 { f32::NAN } else { 100.0 * (sel - arm) / (sel - orc) }
    };

    let row = |label: &str, m: &dyn Fn(usize, usize) -> bool| {
        let (s, b, o) = (
            rmse(&sel, &scene.truth, m),
            rmse(&blend, &scene.truth, m),
            rmse(&oracle, &scene.truth, m),
        );
        println!(
            "    {label:<24} selection {s:8.1}   blend {b:8.1}   oracle {o:8.1}   \
             blend captures {:+6.1}% of headroom",
            headroom(b, s, o)
        );
    };

    println!("  RMSE against ACHIEVABLE truth (DN of {WHITE:.0} white), lower is better");
    if scene.has_edge {
        row("in the band (<=20 px)", &band);
        row("far field (>40 px)", &far);
    }
    row("whole frame", &all);

    if scene.has_edge {
        let iso_sel = score_iso(&sel);
        let iso_bl = score_iso(&blend);
        let iso_frame = score_iso(&frames[FRAMES / 2]);
        let iso_truth = score_iso(&scene.truth);
        let iso_oracle = score_iso(&oracle);
        println!("  ISO (isotonic-residual overshoot, M87 s2.1)");
        println!("    selection merge         {iso_sel:.5}");
        println!("    multi-band merge        {iso_bl:.5}");
        println!("    oracle                  {iso_oracle:.5}");
        println!("    single frame  [null]    {iso_frame:.5}");
        println!("    ground truth  [null]    {iso_truth:.5}");
        if iso_truth > 0.25 * iso_sel {
            println!(
                "    *** ISO IS NOT USABLE ON THIS SCENE: ground truth scores {:.0}% of the \
                 selection arm. The metric is reading scene texture, not the rim.",
                100.0 * iso_truth / iso_sel
            );
        }

        // COMMISSIONING GATE. An instrument that cannot see the defect on a
        // scene built to contain it cannot adjudicate a fix for that defect.
        // M87 measured the real merge at ISO 0.06804 against a single-frame
        // null of 0.000026 -- a ratio of 2617x. If this scene's selection arm
        // is not well clear of its own null, the scene does not reproduce the
        // halo and every comparison below it is meaningless.
        let potency = iso_sel / iso_frame.max(1e-9);
        println!(
            "  COMMISSIONING: selection arm is {potency:.1}x its single-frame null \
             (M87 on real data: 2617x)"
        );
        if potency < 20.0 {
            println!(
                "    *** SCENE NOT COMMISSIONED -- it does not reproduce the halo. \
                 Do NOT report the rows above as evidence about the rim."
            );
        } else {
            println!("    scene reproduces the defect; the comparison above is admissible.");
        }
    }

    let (mx, mean) = max_index_jump(&winner);
    println!("  election index field (selection arm only)");
    println!("    max jump between adjacent px  {mx} frames of {FRAMES}");
    println!("    mean |jump|                   {mean:.4}");
    println!("    the multi-band merge forms no index field, so this is N/A for it");

    Ok(())
}

fn main() -> Result<()> {
    println!("BUILD-BLEND -- two-layer synthetic scene with known ground truth");
    println!(
        "plane {W}x{H}, {FRAMES} frames, CoC {COC_PER_FRAME} px/frame, \
         fg depth {:.0}..{:.0} (spans {:.0}% of the bracket), bg depth {BG_DEPTH} (out of bracket)",
        fg_depth(0),
        fg_depth(H - 1),
        100.0 * (fg_depth(H - 1) - fg_depth(0)) / FRAMES as f32
    );
    println!("lower RMSE is better; lower ISO is better; the nulls bound what ISO can mean");

    run_scene(&occluding_scene("occluding, dark subject on bright backdrop", 0.18 * WHITE, 0.80 * WHITE))?;
    run_scene(&occluding_scene("occluding, bright subject on dark backdrop", 0.80 * WHITE, 0.30 * WHITE))?;
    run_scene(&texture_scene())?;
    Ok(())
}
