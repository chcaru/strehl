//! M95 arm 9 — ringing (B23) and election neutrality (B24) for the resampling
//! kernels, measured in-crate on real `bee-3-cpl` frames.
//!
//! Bars, metrics and controls are registered in
//! `experiments/M95-kernel/PRE-REGISTRATION.md` ADDENDUM 2, written before this
//! file existed.
//!
//! Why in-crate rather than in Python: `merge_cmd.rs:919-960` warps the frame
//! **before** `green_luma_with_clip` and `FocusField::compute` run, so the
//! resampler is upstream of the focus statistic. Answering B24 honestly means
//! running the real `FocusField` at the real `WINDOW_RADIUS` with the real
//! `profile::noise_model_for`, not a Python approximation of them.
//!
//! Run:
//! `cargo run -p strehl-cli --release --example m95-kernel -- <dir> <out.json>`

use std::path::PathBuf;

use anyhow::{Context, Result, bail};
use strehl_core::align::{PlaneRef, Resampler, Similarity, SimilarityParams};
use strehl_core::focus::FocusField;
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;

/// Every kernel the enum offers, in ascending order of support.
const KERNELS: [(&str, Resampler); 4] = [
    ("nearest", Resampler::Nearest),
    ("bilinear", Resampler::Bilinear),
    ("catmull-rom", Resampler::CatmullRom),
    ("lanczos3", Resampler::Lanczos3),
];

/// Quad-grid side of the ringing crop.
const RING_W: usize = 1536;
/// Quad-grid side of the election crop.
const ELECT_W: usize = 1024;
/// Frames sampled across the bracket for the election arm.
const ELECT_N: usize = 16;
/// Container ceiling, matching `merge_cmd`'s `CONTAINER_MAX_DN`.
const CONTAINER_MAX_DN: u16 = u16::MAX;

// ---------------------------------------------------------------------------
// a square quad-grid crop, kept in sensor layout
// ---------------------------------------------------------------------------

/// A `w x w` quad crop held as `2w x 2w` u16 in sensor layout, so that the real
/// [`green_luma_with_clip`] can read it through [`QuadSource`] unchanged.
struct Crop {
    data: Vec<u16>,
    w: usize,
}

impl QuadSource for Crop {
    fn geometry(&self) -> PlaneGeometry {
        PlaneGeometry {
            width: self.w,
            height: self.w,
        }
    }
    fn quad_rows(&self, py: usize) -> (&[u16], &[u16]) {
        let s = 2 * self.w;
        let a = (2 * py) * s;
        let b = (2 * py + 1) * s;
        (&self.data[a..a + s], &self.data[b..b + s])
    }
}

impl Crop {
    /// Cut a centred `w x w` quad crop out of a decoded frame's active area.
    fn centred(frame: &strehl_raw::Frame, w: usize) -> Result<Self> {
        let (qw, qh) = (frame.active.width / 2, frame.active.height / 2);
        if w > qw || w > qh {
            bail!("crop {w} does not fit in quad geometry {qw}x{qh}");
        }
        let (q0x, q0y) = ((qw - w) / 2, (qh - w) / 2);
        let s = 2 * w;
        let mut data = vec![0u16; s * s];
        for row in 0..s {
            let src = (frame.active.y + 2 * q0y + row) * frame.stride + frame.active.x + 2 * q0x;
            data[row * s..(row + 1) * s].copy_from_slice(&frame.data[src..src + s]);
        }
        Ok(Self { data, w })
    }

    fn geom(&self) -> PlaneGeometry {
        PlaneGeometry {
            width: self.w,
            height: self.w,
        }
    }

    /// Lift one CFA phase to an f32 plane.
    fn phase(&self, dx: usize, dy: usize, out: &mut [f32]) {
        let s = 2 * self.w;
        for py in 0..self.w {
            let row = (2 * py + dy) * s + dx;
            let o = &mut out[py * self.w..(py + 1) * self.w];
            for (px, v) in o.iter_mut().enumerate() {
                *v = self.data[row + 2 * px] as f32;
            }
        }
    }

    /// Write one CFA phase back, rounding and clamping exactly as
    /// `align_cmd::warp_frame_in_place` does.
    fn put_phase(&mut self, dx: usize, dy: usize, src: &[f32], cover: &[bool], black_dn: u16) {
        let s = 2 * self.w;
        for py in 0..self.w {
            let row = (2 * py + dy) * s + dx;
            let lo = py * self.w;
            for px in 0..self.w {
                let v = src[lo + px];
                self.data[row + 2 * px] = if cover[lo + px] {
                    v.round().clamp(0.0, u16::MAX as f32) as u16
                } else {
                    black_dn
                };
            }
        }
    }
}

/// Register a crop in place, phase by phase — the same four-gather structure as
/// `align_cmd::warp_frame_in_place`, so no interpolation ever mixes two colours.
///
/// Returns the per-pixel coverage of the last phase, which is the same for all
/// four because they share one transform and one geometry.
fn warp_crop(c: &mut Crop, t: Similarity, r: Resampler, black_dn: u16) -> Result<Vec<bool>> {
    let geom = c.geom();
    let mut src = vec![0f32; geom.pixels()];
    let mut dst = vec![0f32; geom.pixels()];
    let mut cover = vec![false; geom.pixels()];
    for dy in 0..2 {
        for dx in 0..2 {
            c.phase(dx, dy, &mut src);
            let view = PlaneRef::from_geometry(&src, geom).context("phase plane")?;
            strehl_core::warpmap::gather_checked(view, t, geom, r, &mut dst, &mut cover)?;
            c.put_phase(dx, dy, &dst, &cover, black_dn);
        }
    }
    Ok(cover)
}

/// Separable Gaussian, reflect-padded. Used only to plant the power controls.
fn blur(plane: &mut [f32], geom: PlaneGeometry, sigma: f64) {
    let r = (3.0 * sigma).ceil() as isize;
    let mut k = vec![0f64; (2 * r + 1) as usize];
    let mut sum = 0.0;
    for (i, w) in k.iter_mut().enumerate() {
        let d = i as f64 - r as f64;
        *w = (-0.5 * d * d / (sigma * sigma)).exp();
        sum += *w;
    }
    for w in k.iter_mut() {
        *w /= sum;
    }
    let (w, h) = (geom.width as isize, geom.height as isize);
    let mut tmp = vec![0f32; plane.len()];
    for y in 0..h {
        for x in 0..w {
            let mut acc = 0f64;
            for (i, kw) in k.iter().enumerate() {
                let sx = (x + i as isize - r).clamp(0, w - 1);
                acc += kw * plane[(y * w + sx) as usize] as f64;
            }
            tmp[(y * w + x) as usize] = acc as f32;
        }
    }
    for y in 0..h {
        for x in 0..w {
            let mut acc = 0f64;
            for (i, kw) in k.iter().enumerate() {
                let sy = (y + i as isize - r).clamp(0, h - 1);
                acc += kw * tmp[(sy * w + x) as usize] as f64;
            }
            plane[(y * w + x) as usize] = acc as f32;
        }
    }
}

// ---------------------------------------------------------------------------
// B23 — ringing, on a kernel-independent reference interval
// ---------------------------------------------------------------------------

struct RingStat {
    mean: f64,
    p999: f64,
    max: f64,
    #[allow(dead_code)]
    n: usize,
}

/// Overshoot of one gather past the 2x2 bracketing source samples, in **DN**.
///
/// The reference interval is the same 2x2 for every kernel **by construction**.
/// A per-kernel support window would silently reward the wider kernel with a
/// wider interval, which would be a measurement of the instrument.
///
/// DN rather than a fraction of local contrast, because the fraction blows up
/// wherever the bracket is nearly flat: dividing a noise excursion by a ~1 DN
/// range manufactures a huge "overshoot" in a region with no edge in it. That
/// is not hypothetical — the first version of this normalised the value and its
/// argmax landed on a featureless white patch, which the eye rejected on sight.
/// Callers gate on [`contrast_field`] to keep the population on real edges.
fn overshoot_field(src: &[f32], geom: PlaneGeometry, t: Similarity, r: Resampler) -> Vec<f32> {
    let view = PlaneRef::from_geometry(src, geom).expect("plane view");
    let (cx, cy) = (geom.width as f64 * 0.5, geom.height as f64 * 0.5);
    let mut out = vec![f32::NAN; geom.pixels()];
    for py in 0..geom.height {
        for px in 0..geom.width {
            let (sx, sy) = t.apply_at(px as f64, py as f64, cx, cy);
            let Some(v) = r.sample_checked(view, sx, sy) else {
                continue;
            };
            let Some((lo, hi)) = bracket(src, geom, sx, sy) else {
                continue;
            };
            out[py * geom.width + px] = (v - hi).max(lo - v).max(0.0);
        }
    }
    out
}

/// Local contrast of the 2x2 bracketing samples, in DN. Kernel-independent, so
/// it is computed once and gates every kernel's population identically.
fn contrast_field(src: &[f32], geom: PlaneGeometry, t: Similarity) -> Vec<f32> {
    let (cx, cy) = (geom.width as f64 * 0.5, geom.height as f64 * 0.5);
    let mut out = vec![f32::NAN; geom.pixels()];
    for py in 0..geom.height {
        for px in 0..geom.width {
            let (sx, sy) = t.apply_at(px as f64, py as f64, cx, cy);
            if let Some((lo, hi)) = bracket(src, geom, sx, sy) {
                out[py * geom.width + px] = hi - lo;
            }
        }
    }
    out
}

fn bracket(src: &[f32], geom: PlaneGeometry, sx: f64, sy: f64) -> Option<(f32, f32)> {
    let (fx, fy) = (sx.floor(), sy.floor());
    if fx < 0.0 || fy < 0.0 {
        return None;
    }
    let (ix, iy) = (fx as usize, fy as usize);
    if ix + 1 >= geom.width || iy + 1 >= geom.height {
        return None;
    }
    let mut lo = f32::INFINITY;
    let mut hi = f32::NEG_INFINITY;
    for j in 0..2 {
        for i in 0..2 {
            let s = src[(iy + j) * geom.width + ix + i];
            lo = lo.min(s);
            hi = hi.max(s);
        }
    }
    Some((lo, hi))
}

fn summarise(field: &[f32], mask: &[bool]) -> RingStat {
    let mut v: Vec<f32> = field
        .iter()
        .zip(mask)
        .filter(|(o, m)| **m && o.is_finite())
        .map(|(o, _)| *o)
        .collect();
    if v.is_empty() {
        return RingStat {
            mean: 0.0,
            p999: 0.0,
            max: 0.0,
            n: 0,
        };
    }
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = v.len();
    let mean = v.iter().map(|x| *x as f64).sum::<f64>() / n as f64;
    let idx = (((n - 1) as f64) * 0.999).round() as usize;
    RingStat {
        mean,
        p999: v[idx] as f64,
        max: v[n - 1] as f64,
        n,
    }
}

fn gradient_mag(src: &[f32], geom: PlaneGeometry) -> Vec<f32> {
    let mut g = vec![0f32; geom.pixels()];
    for y in 1..geom.height - 1 {
        for x in 1..geom.width - 1 {
            let i = y * geom.width + x;
            let gx = src[i + 1] - src[i - 1];
            let gy = src[i + geom.width] - src[i - geom.width];
            g[i] = (gx * gx + gy * gy).sqrt();
        }
    }
    g
}

/// Chebyshev distance to the nearest `true` in `seed`, capped at `maxd`.
fn distance_to(seed: &[bool], geom: PlaneGeometry, maxd: usize) -> Vec<u8> {
    let mut d = vec![u8::MAX; geom.pixels()];
    let mut front: Vec<usize> = seed
        .iter()
        .enumerate()
        .filter(|(_, s)| **s)
        .map(|(i, _)| i)
        .collect();
    for i in &front {
        d[*i] = 0;
    }
    for step in 1..=maxd as u8 {
        let mut next = Vec::new();
        for i in front.drain(..) {
            let (x, y) = (i % geom.width, i / geom.width);
            for dy in -1isize..=1 {
                for dx in -1isize..=1 {
                    let (nx, ny) = (x as isize + dx, y as isize + dy);
                    if nx < 0 || ny < 0 || nx >= geom.width as isize || ny >= geom.height as isize {
                        continue;
                    }
                    let j = ny as usize * geom.width + nx as usize;
                    if d[j] == u8::MAX {
                        d[j] = step;
                        next.push(j);
                    }
                }
            }
        }
        front = next;
    }
    d
}

// ---------------------------------------------------------------------------
// 100% crops, for the eye
// ---------------------------------------------------------------------------

/// Minimal 24-bit BMP. No crate, no compression, no colour management beyond a
/// plain sRGB transfer — the point is to look at pixels, not to ship a file.
fn write_bmp(path: &std::path::Path, w: usize, h: usize, rgb: &[u8]) -> Result<()> {
    let row = w * 3;
    let pad = (4 - row % 4) % 4;
    let stride = row + pad;
    let size = 54 + stride * h;
    let mut b = Vec::with_capacity(size);
    b.extend_from_slice(b"BM");
    b.extend_from_slice(&(size as u32).to_le_bytes());
    b.extend_from_slice(&0u32.to_le_bytes());
    b.extend_from_slice(&54u32.to_le_bytes());
    b.extend_from_slice(&40u32.to_le_bytes());
    b.extend_from_slice(&(w as i32).to_le_bytes());
    b.extend_from_slice(&(h as i32).to_le_bytes());
    b.extend_from_slice(&1u16.to_le_bytes());
    b.extend_from_slice(&24u16.to_le_bytes());
    for _ in 0..6 {
        b.extend_from_slice(&0u32.to_le_bytes());
    }
    for y in (0..h).rev() {
        for x in 0..w {
            let i = (y * w + x) * 3;
            b.extend_from_slice(&[rgb[i + 2], rgb[i + 1], rgb[i]]);
        }
    }
    b.resize(size, 0);
    // Row padding must sit at the end of each row, not at the end of the file.
    let mut out = b[..54].to_vec();
    let mut p = 54;
    for _ in 0..h {
        out.extend_from_slice(&b[p..p + row]);
        out.extend(std::iter::repeat_n(0u8, pad));
        p += row;
    }
    if let Some(d) = path.parent() {
        std::fs::create_dir_all(d)?;
    }
    std::fs::write(path, out)?;
    Ok(())
}

/// Linear DN to 8-bit sRGB with one shared gain, so panels stay comparable.
fn tone(v: f32, gain: f64) -> u8 {
    let l = (v as f64 * gain).clamp(0.0, 1.0);
    let s = if l <= 0.0031308 {
        12.92 * l
    } else {
        1.055 * l.powf(1.0 / 2.4) - 0.055
    };
    (s * 255.0).round().clamp(0.0, 255.0) as u8
}

/// Luma of a crop, black-subtracted, through the real `green_luma_with_clip`.
fn crop_luma(c: &Crop, black: f32) -> Vec<f32> {
    let geom = c.geom();
    let mut luma = vec![0f32; geom.pixels()];
    let mut clipped = vec![false; geom.pixels()];
    green_luma_with_clip(c, black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
    luma
}

// ---------------------------------------------------------------------------

/// One kernel's election over the bracket: the winner, the coverage, and the
/// top two focus values so a flip can be told from a tie.
struct Elected {
    who: Vec<u16>,
    live: Vec<bool>,
    best: Vec<f32>,
    second: Vec<f32>,
}

fn main() -> Result<()> {
    let mut args = std::env::args().skip(1);
    let dir = PathBuf::from(args.next().context("usage: m95-kernel <dir> <out.json>")?);
    let out = PathBuf::from(args.next().context("usage: m95-kernel <dir> <out.json>")?);

    let mut paths: Vec<PathBuf> = std::fs::read_dir(&dir)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("ARW")))
        .collect();
    paths.sort();
    if paths.len() < ELECT_N {
        bail!("{} has only {} frames", dir.display(), paths.len());
    }
    println!(
        "M95 arm 9 -- kernel ringing and election\n  {}\n  {} frames\n",
        dir.display(),
        paths.len()
    );

    let mut j = String::from("{\n");
    j.push_str(&format!(
        "  \"dir\": {:?},\n  \"frames\": {},\n",
        dir.display().to_string(),
        paths.len()
    ));

    let crops_only = std::env::args().any(|a| a == "--crops-only");
    let port_only = std::env::args().any(|a| a == "--port-only");
    if port_only {
        port_check(&mut j)?;
        j.push_str("  \"schema\": \"m95-kernel-port-1\"\n}\n");
        if let Some(p) = out.parent() {
            std::fs::create_dir_all(p)?;
        }
        std::fs::write(&out, j)?;
        println!("\nwrote {}", out.display());
        return Ok(());
    }
    if !crops_only {
        ringing(&paths, &mut j)?;
        port_check(&mut j)?;
        election(&paths, &mut j)?;
    }
    crops(&paths, &mut j)?;

    if crops_only {
        println!("\n--crops-only: JSON not rewritten");
        return Ok(());
    }
    j.push_str("  \"schema\": \"m95-kernel-1\"\n}\n");
    if let Some(p) = out.parent() {
        std::fs::create_dir_all(p)?;
    }
    std::fs::write(&out, j)?;
    println!("\nwrote {}", out.display());
    Ok(())
}

fn ringing(paths: &[PathBuf], j: &mut String) -> Result<()> {
    let mid = &paths[paths.len() / 2];
    let frame = strehl_raw::decode(mid).map_err(|e| anyhow::anyhow!("{e}"))?;
    let crop = Crop::centred(&frame, RING_W)?;
    let geom = crop.geom();
    let mut src = vec![0f32; geom.pixels()];
    crop.phase(0, 0, &mut src);

    // Half-pixel shift: the phase where an interpolator is worst, and the same
    // phase `align --resampler-cost` uses.
    let t = Similarity::from_params(SimilarityParams {
        ax: 0.5,
        ay: 0.5,
        g: 0.0,
        rot: 0.0,
    });

    let g = gradient_mag(&src, geom);
    let mut sorted: Vec<f32> = g.iter().copied().filter(|v| *v > 0.0).collect();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let thr = |q: f64| sorted[(((sorted.len() - 1) as f64) * q).round() as usize];
    let (t99, t999) = (thr(0.99), thr(0.999));

    // Real edges only. Below a gate the 2x2 bracket is noise and a ratio
    // against it is meaningless -- see `overshoot_field`. One gate would be a
    // number I chose; a ladder lets the reader see the whole dependence.
    const GATES: [f32; 5] = [0.0, 50.0, 100.0, 200.0, 400.0];
    let contrast = contrast_field(&src, geom, t);

    println!(
        "B23 ringing -- {} on {}x{} G1, half-pixel shift, overshoot in DN\n  gradient thresholds: p99 {:.1} DN  p99.9 {:.1} DN\n",
        mid.file_name().unwrap().to_string_lossy(),
        geom.width,
        geom.height,
        t99,
        t999
    );

    let fields: Vec<(String, Vec<f32>)> = KERNELS
        .iter()
        .map(|(n, r)| ((*n).to_string(), overshoot_field(&src, geom, t, *r)))
        .collect();

    j.push_str("  \"b23_ringing\": {\n");
    j.push_str(&format!(
        "    \"frame\": {:?}, \"crop\": {}, \"unit\": \"DN\", \"t99_dn\": {:.4}, \"t999_dn\": {:.4},\n",
        mid.file_name().unwrap().to_string_lossy(),
        RING_W,
        t99,
        t999
    ));
    j.push_str("    \"ladder\": [\n");

    let mut rows = Vec::new();
    for (gi, gate) in GATES.iter().enumerate() {
        let mask: Vec<bool> = (0..geom.pixels())
            .map(|i| contrast[i].is_finite() && contrast[i] >= *gate)
            .collect();
        let npop = mask.iter().filter(|b| **b).count();
        println!(
            "  contrast gate >= {gate:>5.0} DN   population {npop:>9} px ({:.4}% of plane)",
            100.0 * npop as f64 / geom.pixels() as f64
        );
        println!(
            "    {:<12} {:>10} {:>10} {:>10} {:>12}",
            "kernel", "mean DN", "p99.9 DN", "max DN", "mean/contr"
        );
        let mut cells = Vec::new();
        for (name, f) in &fields {
            let s = summarise(f, &mask);
            let fr: Vec<f32> = (0..geom.pixels())
                .map(|i| {
                    if mask[i] && f[i].is_finite() && contrast[i] > 0.0 {
                        f[i] / contrast[i]
                    } else {
                        f32::NAN
                    }
                })
                .collect();
            let sr = summarise(&fr, &mask);
            println!(
                "    {name:<12} {:>10.4} {:>10.4} {:>10.4} {:>11.5}%",
                s.mean,
                s.p999,
                s.max,
                100.0 * sr.mean
            );
            cells.push(format!(
                "{{\"kernel\": {name:?}, \"mean_dn\": {:.8e}, \"p999_dn\": {:.8e}, \"max_dn\": {:.8e}, \"mean_frac\": {:.8e}}}",
                s.mean, s.p999, s.max, sr.mean
            ));
        }
        println!();
        rows.push(format!(
            "      {{\"gate_dn\": {gate:.1}, \"n\": {npop}, \"kernels\": [{}]}}{}",
            cells.join(", "),
            if gi + 1 == GATES.len() { "" } else { "," }
        ));
    }
    j.push_str(&rows.join("\n"));
    j.push_str("\n    ],\n");

    // Spatial extent, on the population that has an edge in it.
    let top: Vec<bool> = (0..geom.pixels())
        .map(|i| g[i] >= t999 && contrast[i].is_finite() && contrast[i] >= 100.0)
        .collect();
    let dist = distance_to(&top, geom, 6);
    let mut radial: Vec<(String, Vec<f64>)> = Vec::new();
    for (name, f) in &fields {
        let mut prof = Vec::new();
        for d in 0..=6u8 {
            let m: Vec<bool> = (0..geom.pixels())
                .map(|i| dist[i] == d && contrast[i].is_finite())
                .collect();
            prof.push(summarise(f, &m).mean);
        }
        radial.push((name.clone(), prof));
    }

    println!(
        "  spatial extent -- mean overshoot (DN) vs Chebyshev distance from a TOP edge ({} px seed)",
        top.iter().filter(|b| **b).count()
    );
    print!("  {:<12}", "kernel");
    for d in 0..=6 {
        print!("{:>11}", format!("d={d}"));
    }
    println!();
    j.push_str("    \"radial\": {\n");
    for (i, (name, prof)) in radial.iter().enumerate() {
        print!("  {name:<12}");
        for v in prof {
            print!("{v:>11.3e}");
        }
        println!();
        let cells: Vec<String> = prof.iter().map(|v| format!("{v:.8e}")).collect();
        j.push_str(&format!(
            "      {:?}: [{}]{}\n",
            name,
            cells.join(", "),
            if i + 1 == radial.len() { "" } else { "," }
        ));
    }
    j.push_str("    },\n");

    // K22 -- power. A synthetic step must make lanczos3 ring. Two structural
    // zeros (K20, K21) plus one positive is what makes the zeros a claim.
    //
    // The step also gives the only *clean* spatial extent available: away from
    // the edge the true signal is constant, so every DN of deviation is
    // ringing and nothing else. On a macro frame the top-0.1% gradient pixels
    // are dense and textured, and one edge's ring lands inside the next edge's
    // neighbourhood.
    const STEP_LO: f32 = 100.0;
    const STEP_HI: f32 = 1100.0;
    let sg = PlaneGeometry {
        width: 64,
        height: 64,
    };
    let mut step = vec![0f32; sg.pixels()];
    for y in 0..sg.height {
        for x in 0..sg.width {
            step[y * sg.width + x] = if x < sg.width / 2 { STEP_LO } else { STEP_HI };
        }
    }
    let smask = vec![true; sg.pixels()];
    println!(
        "\n  K22 power -- synthetic step of {} DN, half-pixel shift",
        STEP_HI - STEP_LO
    );
    println!(
        "  {:<12} {:>14} {:>12} {:>10}",
        "kernel", "overshoot DN", "% of step", "ring px"
    );
    j.push_str("    \"k22_step\": {\n");
    for (n, (name, r)) in KERNELS.iter().enumerate() {
        let f = overshoot_field(&step, sg, t, *r);
        let s = summarise(&f, &smask);
        // Ringing reach: how far from the transition column a flat-region
        // sample still deviates by more than 0.5 DN.
        let mid = sg.width / 2;
        let mut reach = 0usize;
        for y in 8..sg.height - 8 {
            for x in 8..sg.width - 8 {
                let v = f[y * sg.width + x];
                if v.is_finite() && v > 0.5 {
                    let d = (x as isize - mid as isize).unsigned_abs();
                    reach = reach.max(d);
                }
            }
        }
        let pct = 100.0 * s.max / (STEP_HI - STEP_LO) as f64;
        println!("  {name:<12} {:>14.4} {:>11.4}% {:>10}", s.max, pct, reach);
        j.push_str(&format!(
            "      {:?}: {{\"overshoot_dn\": {:.8e}, \"pct_of_step\": {:.8e}, \"reach_px\": {reach}}}{}\n",
            name,
            s.max,
            pct,
            if n + 1 == KERNELS.len() { "" } else { "," }
        ));
    }
    j.push_str("    }\n  },\n");
    Ok(())
}

/// B22 — extract the **shipped** kernel's tap weights by black-box probe, so
/// the ported gain is re-derived from the binary's own arithmetic rather than
/// from a transcription of the source.
///
/// A delta at source index `i0 + off` sampled at `x = i0 + f` returns exactly
/// the tap weight applied to that offset, **including the normalisation**,
/// because the kernel is separable and interpolating along the untouched axis.
fn port_check(j: &mut String) -> Result<()> {
    let geom = PlaneGeometry {
        width: 64,
        height: 64,
    };
    let (i0, jy) = (32usize, 32usize);
    const NPHASE: usize = 64;
    let phases: Vec<f64> = (0..NPHASE).map(|k| k as f64 / NPHASE as f64).collect();
    println!("\nB22 port check -- tap weights read back out of the shipped kernel");

    j.push_str("  \"b22_taps\": {\n");
    for (n, (name, r)) in KERNELS.iter().enumerate() {
        let sup = r.support();
        let lo = -(sup.ceil() as i64) + 1;
        let hi = sup.ceil() as i64;
        let mut rows = Vec::new();
        for f in &phases {
            let mut w = Vec::new();
            for off in lo..=hi {
                let mut p = vec![0f32; geom.pixels()];
                p[jy * geom.width + (i0 as i64 + off) as usize] = 1.0;
                let view = PlaneRef::from_geometry(&p, geom).context("probe plane")?;
                let v = r
                    .sample_checked(view, i0 as f64 + f, jy as f64)
                    .context("probe fell outside the plane")?;
                w.push(v as f64);
            }
            rows.push((*f, w));
        }
        let s: f64 = rows[4].1.iter().sum();
        println!(
            "  {name:<12} support {sup:.1}  taps {:>2}  sum at f=0.5 {s:.10}",
            rows[0].1.len()
        );
        let body: Vec<String> = rows
            .iter()
            .map(|(f, w)| {
                let c: Vec<String> = w.iter().map(|v| format!("{v:.12e}")).collect();
                format!("        {{\"f\": {f:.6}, \"w\": [{}]}}", c.join(", "))
            })
            .collect();
        j.push_str(&format!(
            "    {:?}: {{\"support\": {sup:.1}, \"lo\": {lo}, \"hi\": {hi}, \"rows\": [\n{}\n    ]}}{}\n",
            name,
            body.join(",\n"),
            if n + 1 == KERNELS.len() { "" } else { "," }
        ));
    }
    j.push_str("  },\n");
    Ok(())
}

fn election(paths: &[PathBuf], j: &mut String) -> Result<()> {
    let step = paths.len() / ELECT_N;
    let picks: Vec<&PathBuf> = (0..ELECT_N).map(|i| &paths[i * step]).collect();
    println!(
        "\nB24 election -- {} frames, every {}th, {}x{} quad crop",
        ELECT_N, step, ELECT_W, ELECT_W
    );

    let mut crops = Vec::new();
    let mut camera = String::new();
    let mut iso = None;
    let mut levels = None;
    for p in &picks {
        let f = strehl_raw::decode(p).map_err(|e| anyhow::anyhow!("{e}"))?;
        if camera.is_empty() {
            camera = f.camera.clone();
            iso = f.iso;
            levels = Some(f.levels);
        }
        crops.push(Crop::centred(&f, ELECT_W)?);
    }
    let levels = levels.context("no levels")?;
    let noise = profile::noise_model_for(&camera, iso, levels);
    let geom = crops[0].geom();
    println!("  {camera}  iso {iso:?}  black {:.1}\n", levels.black);

    // Per-frame sub-pixel phase. A single common phase would make the kernel's
    // effect common-mode and bias the answer toward neutrality by construction.
    let warp = |i: usize| {
        Similarity::from_params(SimilarityParams {
            ax: (0.37 * i as f64).fract(),
            ay: (0.61 * i as f64).fract(),
            g: 0.0,
            rot: 0.0,
        })
    };

    // `blur_at` plants the K24 power control on exactly one frame.
    let elect = |r: Resampler, blur_at: Option<usize>| -> Result<Elected> {
        let mut best = vec![f32::NEG_INFINITY; geom.pixels()];
        let mut second = vec![f32::NEG_INFINITY; geom.pixels()];
        let mut who = vec![u16::MAX; geom.pixels()];
        let mut live = vec![true; geom.pixels()];
        let mut field = FocusField::new(geom);
        let mut luma = vec![0f32; geom.pixels()];
        let mut clipped = vec![false; geom.pixels()];
        let mut phase = vec![0f32; geom.pixels()];
        for (i, c) in crops.iter().enumerate() {
            let mut c = Crop {
                data: c.data.clone(),
                w: c.w,
            };
            if blur_at == Some(i) {
                let mut cover = vec![true; geom.pixels()];
                for dy in 0..2 {
                    for dx in 0..2 {
                        c.phase(dx, dy, &mut phase);
                        blur(&mut phase, geom, 1.0);
                        cover.fill(true);
                        c.put_phase(dx, dy, &phase, &cover, 0);
                    }
                }
            }
            let cover = warp_crop(&mut c, warp(i), r, levels.black.round() as u16)?;
            for (l, cv) in live.iter_mut().zip(&cover) {
                *l &= *cv;
            }
            green_luma_with_clip(&c, levels.black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
            field.compute(&luma, &noise);
            for (k, v) in field.values().iter().enumerate() {
                if *v > best[k] {
                    second[k] = best[k];
                    best[k] = *v;
                    who[k] = i as u16;
                } else if *v > second[k] {
                    second[k] = *v;
                }
            }
        }
        Ok(Elected {
            who,
            live,
            best,
            second,
        })
    };

    let m = 32; // discard a border wider than WINDOW_RADIUS = 13
    // Returns (moved fraction, N compared, median relative margin at the pixels
    // that moved). The margin says whether a flip was a real disagreement or a
    // coin-flip between two frames the field could not separate.
    let compare = |a: &Elected, b: &Elected| -> (f64, usize, f64) {
        let (mut diff, mut n) = (0usize, 0usize);
        let mut margins: Vec<f64> = Vec::new();
        for y in m..geom.height - m {
            for x in m..geom.width - m {
                let i = y * geom.width + x;
                if !(a.live[i] && b.live[i]) {
                    continue;
                }
                n += 1;
                if a.who[i] != b.who[i] {
                    diff += 1;
                    if a.best[i] > 0.0 && a.second[i].is_finite() {
                        margins.push(((a.best[i] - a.second[i]) / a.best[i]) as f64);
                    }
                }
            }
        }
        margins.sort_by(|p, q| p.partial_cmp(q).unwrap());
        let med = if margins.is_empty() {
            f64::NAN
        } else {
            margins[margins.len() / 2]
        };
        (diff as f64 / n.max(1) as f64, n, med)
    };

    let cr = elect(Resampler::CatmullRom, None)?;
    let cr2 = elect(Resampler::CatmullRom, None)?;
    let lz = elect(Resampler::Lanczos3, None)?;
    let bl = elect(Resampler::Bilinear, None)?;
    let planted = elect(Resampler::CatmullRom, Some(ELECT_N / 2))?;

    // What share of the crop each frame wins under the reference kernel. K24's
    // registered >= 5% bar assumed the planted frame was a major winner; this
    // is the number that says whether that assumption held.
    let mut share = vec![0usize; ELECT_N];
    let mut live_n = 0usize;
    for y in m..geom.height - m {
        for x in m..geom.width - m {
            let i = y * geom.width + x;
            if cr.live[i] && (cr.who[i] as usize) < ELECT_N {
                share[cr.who[i] as usize] += 1;
                live_n += 1;
            }
        }
    }
    let planted_share = share[ELECT_N / 2] as f64 / live_n.max(1) as f64;

    let (k23, n, _) = compare(&cr, &cr2);
    let (k24, _, _) = compare(&cr, &planted);
    let (b24, _, b24_margin) = compare(&cr, &lz);
    let (b24b, _, _) = compare(&cr, &bl);
    let sep = if k23 > 0.0 { k24 / k23 } else { f64::INFINITY };

    // Baseline for the margin: the median relative margin over *all* live
    // pixels. Without it, "the flips sit at a 0.8% margin" is a number with no
    // scale attached.
    let mut allm: Vec<f64> = Vec::new();
    for y in m..geom.height - m {
        for x in m..geom.width - m {
            let i = y * geom.width + x;
            if cr.live[i] && cr.best[i] > 0.0 && cr.second[i].is_finite() {
                allm.push(((cr.best[i] - cr.second[i]) / cr.best[i]) as f64);
            }
        }
    }
    allm.sort_by(|p, q| p.partial_cmp(q).unwrap());
    let base_margin = allm[allm.len() / 2];

    println!(
        "  {:<44} {:>14} {:>10}",
        "comparison", "winners moved", "of N"
    );
    println!(
        "  {:<44} {:>13.6}% {:>10}",
        "K23 null    catmull-rom vs itself",
        100.0 * k23,
        n
    );
    println!(
        "  {:<44} {:>13.6}%",
        "K24 power   catmull-rom vs sigma=1.0 planted",
        100.0 * k24
    );
    println!(
        "  {:<44} {:>13.6}%",
        "B24         catmull-rom vs lanczos3",
        100.0 * b24
    );
    println!(
        "  {:<44} {:>13.6}%",
        "reference   catmull-rom vs bilinear",
        100.0 * b24b
    );
    println!("\n  separation K24/K23 = {sep:.1}x");
    println!(
        "  planted frame {} wins {:.4}% of the crop; K24 moved {:.1}% of what was reachable",
        ELECT_N / 2,
        100.0 * planted_share,
        100.0 * k24 / planted_share.max(1e-12)
    );
    println!(
        "  median relative margin where lanczos3 disagreed: {:.6}  (0 = an exact tie)",
        b24_margin
    );
    println!(
        "  median relative margin over all live pixels:      {:.6}   ratio {:.1}x",
        base_margin,
        base_margin / b24_margin.max(1e-12)
    );
    print!("  win share by frame:");
    for s in &share {
        print!(" {:.3}", *s as f64 / live_n.max(1) as f64);
    }
    println!();

    let shares: Vec<String> = share
        .iter()
        .map(|s| format!("{:.8e}", *s as f64 / live_n.max(1) as f64))
        .collect();
    j.push_str(&format!(
        "  \"b24_election\": {{\n    \"frames\": {ELECT_N}, \"step\": {step}, \"crop\": {ELECT_W}, \"n_pixels\": {n},\n    \"camera\": {:?}, \"iso\": {},\n    \"k23_null\": {k23:.10e},\n    \"k24_power\": {k24:.10e},\n    \"k24_planted_share\": {planted_share:.10e},\n    \"k24_of_reachable\": {:.10e},\n    \"b24_lanczos3\": {b24:.10e},\n    \"b24_median_margin\": {b24_margin:.10e},\n    \"all_median_margin\": {base_margin:.10e},\n    \"ref_bilinear\": {b24b:.10e},\n    \"win_share\": [{}],\n    \"separation\": {}\n  }},\n",
        camera,
        iso.map(|v| format!("{v}")).unwrap_or_else(|| "null".into()),
        k24 / planted_share.max(1e-12),
        shares.join(", "),
        if sep.is_finite() {
            format!("{sep:.6e}")
        } else {
            "null".into()
        }
    ));
    Ok(())
}

/// 100% crops of the frame's most detailed regions, every kernel side by side,
/// one shared exposure. The metric and the eye get the same pixels.
fn crops(paths: &[PathBuf], j: &mut String) -> Result<()> {
    const WIN: usize = 192;
    const GUT: usize = 6;
    let dst = std::path::Path::new(r"C:\dev\strehl-out\M95-kernel");
    let mid = &paths[paths.len() / 2];
    let frame = strehl_raw::decode(mid).map_err(|e| anyhow::anyhow!("{e}"))?;
    let base = Crop::centred(&frame, RING_W)?;
    let geom = base.geom();
    let black = frame.levels.black;
    let orig = crop_luma(&base, black);

    // Warp the whole crop once per kernel, at the worst phase, exactly as a
    // registered frame is warped on the way into the merge.
    let t = Similarity::from_params(SimilarityParams {
        ax: 0.5,
        ay: 0.5,
        g: 0.0,
        rot: 0.0,
    });
    let mut panels: Vec<(String, Vec<f32>)> = vec![("original".into(), orig.clone())];
    for (name, r) in KERNELS.iter() {
        let mut c = Crop {
            data: base.data.clone(),
            w: base.w,
        };
        warp_crop(&mut c, t, *r, black.round() as u16)?;
        panels.push(((*name).into(), crop_luma(&c, black)));
    }

    // Pick the three most detailed non-overlapping windows: on a macro bee
    // frame these are hairs, facets and silhouette, chosen by the data rather
    // than by me looking for a flattering crop.
    let g = gradient_mag(&orig, geom);
    let mut cand: Vec<(f64, usize, usize)> = Vec::new();
    let stepw = WIN / 2;
    for wy in (64..geom.height - WIN - 64).step_by(stepw) {
        for wx in (64..geom.width - WIN - 64).step_by(stepw) {
            let mut e = 0f64;
            for y in wy..wy + WIN {
                for x in wx..wx + WIN {
                    let v = g[y * geom.width + x] as f64;
                    e += v * v;
                }
            }
            cand.push((e, wx, wy));
        }
    }
    cand.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap());
    let mut picked: Vec<(usize, usize)> = Vec::new();
    for (_, wx, wy) in &cand {
        if picked
            .iter()
            .any(|(px, py)| wx.abs_diff(*px) < WIN && wy.abs_diff(*py) < WIN)
        {
            continue;
        }
        picked.push((*wx, *wy));
        if picked.len() == 3 {
            break;
        }
    }

    println!(
        "\n100% crops -- {} windows of {WIN}x{WIN}, all kernels",
        picked.len()
    );
    let mut files = Vec::new();
    for (k, (wx, wy)) in picked.iter().enumerate() {
        // One shared gain from the unresampled panel, so the eye compares
        // detail rather than brightness.
        let mut v: Vec<f32> = (0..WIN * WIN)
            .map(|i| orig[(wy + i / WIN) * geom.width + wx + i % WIN])
            .collect();
        v.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let hi = v[(v.len() as f64 * 0.995) as usize].max(1.0) as f64;
        let gain = 0.92 / hi;

        let pw = panels.len() * WIN + (panels.len() - 1) * GUT;
        let mut rgb = vec![255u8; pw * WIN * 3];
        for (pi, (_, plane)) in panels.iter().enumerate() {
            let x0 = pi * (WIN + GUT);
            for y in 0..WIN {
                for x in 0..WIN {
                    let s = plane[(wy + y) * geom.width + wx + x];
                    let b = tone(s, gain);
                    let o = (y * pw + x0 + x) * 3;
                    rgb[o] = b;
                    rgb[o + 1] = b;
                    rgb[o + 2] = b;
                }
            }
        }
        let name = format!("crop{}-x{wx}-y{wy}.bmp", k + 1);
        write_bmp(&dst.join(&name), pw, WIN, &rgb)?;
        println!(
            "  {name}  panels: {}",
            panels
                .iter()
                .map(|(n, _)| n.as_str())
                .collect::<Vec<_>>()
                .join(" | ")
        );
        files.push(name);
    }
    let q: Vec<String> = files.iter().map(|f| format!("{f:?}")).collect();
    j.push_str(&format!(
        "  \"crops\": {{\"dir\": {:?}, \"win\": {WIN}, \"panels\": [\"original\", \"nearest\", \"bilinear\", \"catmull-rom\", \"lanczos3\"], \"files\": [{}]}},\n",
        dst.display().to_string(),
        q.join(", ")
    ));

    // A 192 px panel at 1x hides a 1-2 px ring. Two more views for the eye, on
    // every window: a hard zoom, and the signed difference between the two
    // candidate kernels, which shows ringing directly as fringes hugging the
    // edges.
    const ZW: usize = 64;
    const ZS: usize = 6;
    let cr = &panels[3].1;
    let lz = &panels[4].1;
    let mut splits = Vec::new();
    for (wx, wy) in picked.iter().copied() {
        let (zx, zy) = (wx + (WIN - ZW) / 2, wy + (WIN - ZW) / 2);
        let mut v: Vec<f32> = (0..ZW * ZW)
            .map(|i| orig[(zy + i / ZW) * geom.width + zx + i % ZW])
            .collect();
        v.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let gain = 0.92 / v[(v.len() as f64 * 0.995) as usize].max(1.0) as f64;
        let pw = panels.len() * ZW * ZS + (panels.len() - 1) * GUT;
        let ph = ZW * ZS;
        let mut rgb = vec![255u8; pw * ph * 3];
        for (pi, (_, plane)) in panels.iter().enumerate() {
            let x0 = pi * (ZW * ZS + GUT);
            for y in 0..ph {
                for x in 0..ZW * ZS {
                    let s = plane[(zy + y / ZS) * geom.width + zx + x / ZS];
                    let b = tone(s, gain);
                    let o = (y * pw + x0 + x) * 3;
                    rgb[o] = b;
                    rgb[o + 1] = b;
                    rgb[o + 2] = b;
                }
            }
        }
        let zname = format!("zoom-x{zx}-y{zy}-{ZS}x.bmp");
        write_bmp(&dst.join(&zname), pw, ph, &rgb)?;

        // Signed difference, lanczos3 minus catmull-rom.
        let mut d: Vec<f32> = Vec::with_capacity(WIN * WIN);
        for y in 0..WIN {
            for x in 0..WIN {
                let i = (wy + y) * geom.width + wx + x;
                d.push(lz[i] - cr[i]);
            }
        }
        let mut ad: Vec<f32> = d.iter().map(|v| v.abs()).collect();
        ad.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let p999 = ad[(ad.len() as f64 * 0.999) as usize].max(1e-6);
        let amp = 110.0 / p999 as f64;
        let mut drgb = vec![0u8; WIN * ZS * WIN * ZS * 3];
        for y in 0..WIN * ZS {
            for x in 0..WIN * ZS {
                let v = d[(y / ZS) * WIN + x / ZS] as f64 * amp;
                let b = (128.0 + v).clamp(0.0, 255.0) as u8;
                let o = (y * WIN * ZS + x) * 3;
                drgb[o] = b;
                drgb[o + 1] = b;
                drgb[o + 2] = b;
            }
        }
        let dname = format!("diff-lanczos3-minus-catmullrom-x{wx}-y{wy}.bmp");
        write_bmp(&dst.join(&dname), WIN * ZS, WIN * ZS, &drgb)?;

        // Where does that difference live? On edges it is recovered detail
        // plus ringing; on flat ground it is nothing but amplified read and
        // shot noise. A kernel that mostly does the second is not an upgrade.
        let mut gw: Vec<f32> = Vec::with_capacity(WIN * WIN);
        for y in 0..WIN {
            for x in 0..WIN {
                gw.push(g[(wy + y) * geom.width + wx + x]);
            }
        }
        let mut sorted = gw.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let flat_t = sorted[sorted.len() / 2];
        let edge_t = sorted[(sorted.len() as f64 * 0.95) as usize];
        let rms = |sel: &dyn Fn(f32) -> bool| -> f64 {
            let (mut s, mut n) = (0f64, 0usize);
            for (dv, gv) in d.iter().zip(&gw) {
                if sel(*gv) {
                    s += (*dv as f64) * (*dv as f64);
                    n += 1;
                }
            }
            (s / n.max(1) as f64).sqrt()
        };
        let r_flat = rms(&|v| v <= flat_t);
        let r_edge = rms(&|v| v >= edge_t);
        println!(
            "  x{wx:<5} y{wy:<5} zoom+diff  p99.9|d| {p999:>7.2} DN  amp {amp:>5.2}x   RMS diff: edge {r_edge:>7.3} DN  flat {r_flat:>7.3} DN  ratio {:>5.2}x",
            r_edge / r_flat.max(1e-9)
        );
        splits.push(format!(
            "{{\"x\": {wx}, \"y\": {wy}, \"p999_dn\": {p999:.6e}, \"rms_edge_dn\": {r_edge:.6e}, \"rms_flat_dn\": {r_flat:.6e}, \"edge_over_flat\": {:.6e}}}",
            r_edge / r_flat.max(1e-9)
        ));
    }
    j.push_str(&format!("  \"diff_split\": [{}],\n", splits.join(", ")));

    // The honest worst case: zoom on the pixel where lanczos3 overshoots most.
    // Overshoot is computed on the G1 phase, because that is the plane the
    // gather actually runs on.
    let mut g1 = vec![0f32; geom.pixels()];
    base.phase(0, 0, &mut g1);
    let of = overshoot_field(&g1, geom, t, Resampler::Lanczos3);
    let con = contrast_field(&g1, geom, t);
    let (mut bi, mut bv) = (0usize, f32::NEG_INFINITY);
    for (i, v) in of.iter().enumerate() {
        let (x, y) = (i % geom.width, i / geom.width);
        if x < 96 || y < 96 || x + 96 >= geom.width || y + 96 >= geom.height {
            continue;
        }
        if con[i] < 100.0 {
            continue;
        }
        if v.is_finite() && *v > bv {
            bv = *v;
            bi = i;
        }
    }
    let (zx, zy) = (
        (bi % geom.width).saturating_sub(ZW / 2),
        (bi / geom.width).saturating_sub(ZW / 2),
    );
    let mut v: Vec<f32> = (0..ZW * ZW)
        .map(|i| orig[(zy + i / ZW) * geom.width + zx + i % ZW])
        .collect();
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let gain = 0.92 / v[(v.len() as f64 * 0.995) as usize].max(1.0) as f64;
    let pw = panels.len() * ZW * ZS + (panels.len() - 1) * GUT;
    let ph = ZW * ZS;
    let mut rgb = vec![255u8; pw * ph * 3];
    for (pi, (_, plane)) in panels.iter().enumerate() {
        let x0 = pi * (ZW * ZS + GUT);
        for y in 0..ph {
            for x in 0..ZW * ZS {
                let b = tone(plane[(zy + y / ZS) * geom.width + zx + x / ZS], gain);
                let o = (y * pw + x0 + x) * 3;
                rgb[o] = b;
                rgb[o + 1] = b;
                rgb[o + 2] = b;
            }
        }
    }
    write_bmp(&dst.join("worst-overshoot-6x.bmp"), pw, ph, &rgb)?;
    println!(
        "  worst-overshoot-6x.bmp  lanczos3 peak overshoot {bv:.2} DN at x{} y{} (contrast {:.1} DN)",
        bi % geom.width,
        bi / geom.width,
        con[bi]
    );
    j.push_str(&format!(
        "  \"worst_overshoot\": {{\"dn\": {bv:.6e}, \"contrast_dn\": {:.6e}, \"x\": {}, \"y\": {}}},\n",
        con[bi],
        bi % geom.width,
        bi / geom.width
    ));
    Ok(())
}
