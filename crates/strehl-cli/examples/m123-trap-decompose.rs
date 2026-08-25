//! M123b — is the trap's displacement pedestal coherent or incoherent?
//!
//! Run:
//! ```text
//! cargo run --release -p strehl-cli --example m123-trap-decompose
//! ```
//!
//! **Reads only.**
//!
//! # Why this exists
//!
//! `m123-outlier-real` measures `ShiftFree` firing on **29.55%** of tiles of
//! `109MSDCF` — a tripod-mounted subject whose adjacent frames differ only in
//! focus — with a mean apparent displacement of **0.95 px**, against a
//! `DEFAULT_MIN_SHIFT_PX` bar of 0.35 px. That is fatal for the mask as
//! specified, but it has **two** possible causes and they imply opposite fixes:
//!
//! 1. **Coherent** — the frames genuinely move relative to each other. Focus
//!    breathing and magnification drift are documented on this corpus
//!    (`1/S_W(1) = 1.32` for `109MSDCF`), and the module compares frames with no
//!    alignment stage in front of it. Then the mask is *correct* and is being
//!    fed unaligned input; the fix is the seam, not the statistic.
//! 2. **Incoherent** — defocus curvature displacing curved features (M97r W5),
//!    at a magnitude the synthetic disc-and-ripple plant could not express. Then
//!    the 0.35 px bar is simply wrong for real scenes and no seam saves it.
//!
//! Distinguishing them is one least-squares fit. Model each tile's displacement
//! as a global similarity transform about the plane centre,
//!
//! ```text
//! sx = tx + a*cx - r*cy
//! sy = ty + a*cy + r*cx
//! ```
//!
//! where `a` is fractional scale change and `r` rotation, then report how much
//! of the field that removes. A high explained fraction means breathing; a low
//! one means curvature.
//!
//! # The control that makes the answer readable
//!
//! `coffee-bubbles` is run through the identical decomposition. Its focus is
//! constant (0.2841 m throughout) and its bubbles drift independently, so its
//! field should be *incoherent* — a global transform should explain little of
//! it. If the trap is coherent and the plant is not, then the residual after a
//! global fit is a discriminant where the raw displacement is not, and that is
//! an actionable design correction rather than only a negative result.
//!
//! Without this control a low explained fraction on the trap would be
//! uninterpretable: it could mean "no breathing" or "the fit does not work"
//! (AGENTS rule 20).

use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use strehl_core::clip::CONTAINER_MAX_DN;
use strehl_core::noise::NoiseModel;
use strehl_core::outlier::{
    DEFAULT_MIN_SHIFT_PX, Params, RESOLUTION_MARGIN, TileGrid, TileShift, shift_tiles,
};
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;

const CROP: usize = 1024;
const PAIRS: usize = 6;

fn load(path: &Path) -> Result<(Vec<f32>, PlaneGeometry, NoiseModel)> {
    let frame =
        strehl_raw::decode(path).with_context(|| format!("decoding {}", path.display()))?;
    let geom = frame.geometry();
    let levels = frame.levels;
    let noise = profile::noise_model_for(&frame.camera, frame.iso, levels);
    let mut luma = vec![0.0f32; geom.pixels()];
    let mut clipped = vec![false; geom.pixels()];
    green_luma_with_clip(&frame, levels.black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
    let (x0, y0) = ((geom.width - CROP) / 2, (geom.height - CROP) / 2);
    let mut out = vec![0.0f32; CROP * CROP];
    for row in 0..CROP {
        let src = (y0 + row) * geom.width + x0;
        out[row * CROP..(row + 1) * CROP].copy_from_slice(&luma[src..src + CROP]);
    }
    Ok((
        out,
        PlaneGeometry {
            width: CROP,
            height: CROP,
        },
        noise,
    ))
}

fn arws(dir: &Path) -> Result<Vec<PathBuf>> {
    let mut v: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("listing {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .and_then(|e| e.to_str())
                .is_some_and(|e| e.eq_ignore_ascii_case("ARW"))
        })
        .collect();
    v.sort();
    Ok(v)
}

/// Tiles trustworthy enough to enter the fit: informative, and precise enough
/// that the gate would have been willing to judge them.
fn usable(t: &TileShift) -> bool {
    t.informative && t.sigma_px.is_finite() && t.sigma_px * RESOLUTION_MARGIN <= DEFAULT_MIN_SHIFT_PX
}

struct Fit {
    tx: f64,
    ty: f64,
    scale: f64,
    rot: f64,
    rms_before: f64,
    rms_after: f64,
    n: usize,
}

/// Least-squares similarity fit over the tile displacement field.
///
/// Four parameters against `2n` equations, solved by normal equations. The
/// translation and the (scale, rotation) block are orthogonal once the tile
/// centres are mean-centred, which is why this is stable without any
/// regularisation.
fn fit_similarity(tiles: &[TileShift], grid: &TileGrid) -> Option<Fit> {
    let pts: Vec<(f64, f64, f64, f64)> = tiles
        .iter()
        .enumerate()
        .filter(|(_, t)| usable(t))
        .map(|(i, t)| {
            let (tx, ty) = (i % grid.cols, i / grid.cols);
            let cx = (tx * grid.tile + grid.tile / 2) as f64 - grid.width as f64 / 2.0;
            let cy = (ty * grid.tile + grid.tile / 2) as f64 - grid.height as f64 / 2.0;
            (cx, cy, f64::from(t.sx), f64::from(t.sy))
        })
        .collect();
    if pts.len() < 8 {
        return None;
    }
    let n = pts.len() as f64;
    let mx = pts.iter().map(|p| p.0).sum::<f64>() / n;
    let my = pts.iter().map(|p| p.1).sum::<f64>() / n;
    let tx = pts.iter().map(|p| p.2).sum::<f64>() / n;
    let ty = pts.iter().map(|p| p.3).sum::<f64>() / n;

    // With centres mean-centred and translation removed, scale and rotation
    // decouple into two independent projections.
    let (mut num_a, mut num_r, mut den) = (0.0, 0.0, 0.0);
    for (cx, cy, sx, sy) in &pts {
        let (dx, dy) = (cx - mx, cy - my);
        let (ux, uy) = (sx - tx, sy - ty);
        num_a += dx * ux + dy * uy;
        num_r += dx * uy - dy * ux;
        den += dx * dx + dy * dy;
    }
    if den <= 0.0 {
        return None;
    }
    let (a, r) = (num_a / den, num_r / den);

    let mut before = 0.0;
    let mut after = 0.0;
    for (cx, cy, sx, sy) in &pts {
        let (dx, dy) = (cx - mx, cy - my);
        before += sx * sx + sy * sy;
        let px = tx + a * dx - r * dy;
        let py = ty + a * dy + r * dx;
        after += (sx - px).powi(2) + (sy - py).powi(2);
    }
    Some(Fit {
        tx,
        ty,
        scale: a,
        rot: r,
        rms_before: (before / n).sqrt(),
        rms_after: (after / n).sqrt(),
        n: pts.len(),
    })
}

fn main() -> Result<()> {
    let params = Params::default();
    println!("M123b - is the apparent displacement a global transform or is it local?");
    println!("crop {CROP}x{CROP} green luma, tile {}px, usable = informative and sigma_px*{RESOLUTION_MARGIN} <= {DEFAULT_MIN_SHIFT_PX}\n", params.tile);
    println!(
        "{:<16} {:>5} {:>6} {:>8} {:>8} {:>10} {:>9} {:>9} {:>9} {:>8}",
        "stack", "pair", "tiles", "tx px", "ty px", "scale ppm", "rot urad", "rms|s|", "rms resid", "expl%"
    );
    println!("{}", "-".repeat(104));

    for (name, dir) in [
        ("109MSDCF TRAP", r"D:\personal\macro\109MSDCF"),
        ("coffee-bubbles", r"D:\personal\macro\coffee-bubbles"),
        ("foam", r"D:\personal\macro\foam"),
    ] {
        let d = Path::new(dir);
        if !d.exists() {
            println!("{name:<16} MISSING");
            continue;
        }
        let paths = arws(d)?;
        if paths.len() < 2 {
            bail!("{dir} has {} ARW", paths.len());
        }
        let n = PAIRS.min(paths.len() - 1);
        let (mut sb, mut sa, mut cnt) = (0.0f64, 0.0f64, 0usize);
        for i in 0..n {
            let (a, geom, noise) = load(&paths[i])?;
            let (b, _, _) = load(&paths[i + 1])?;
            let grid = TileGrid::new(geom, params.tile);
            let tiles = shift_tiles(&a, &b, geom, &noise, params, true);
            let Some(f) = fit_similarity(&tiles, &grid) else {
                println!("{name:<16} {i:>5}  too few usable tiles");
                continue;
            };
            let expl = if f.rms_before > 0.0 {
                100.0 * (1.0 - (f.rms_after / f.rms_before).powi(2))
            } else {
                f64::NAN
            };
            println!(
                "{name:<16} {i:>5} {:>6} {:>8.4} {:>8.4} {:>10.1} {:>9.1} {:>9.4} {:>9.4} {expl:>7.1}%",
                f.n,
                f.tx,
                f.ty,
                f.scale * 1e6,
                f.rot * 1e6,
                f.rms_before,
                f.rms_after,
            );
            sb += f.rms_before;
            sa += f.rms_after;
            cnt += 1;
        }
        if cnt > 0 {
            let (mb, ma) = (sb / cnt as f64, sa / cnt as f64);
            println!(
                "{:<16} {:>5} {:>6} {:>8} {:>8} {:>10} {:>9} {:>9.4} {:>9.4} {:>7.1}%",
                format!("{name} MEAN"),
                "",
                "",
                "",
                "",
                "",
                "",
                mb,
                ma,
                100.0 * (1.0 - (ma / mb).powi(2))
            );
        }
        println!();
    }
    Ok(())
}
