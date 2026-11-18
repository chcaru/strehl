//! Full colour carried through the pyramid merge (`STREHL_CARRY_RGB`): on by
//! default for pixel-shift stacks (`STREHL_PIXEL_SHIFT=remosaic`), off
//! otherwise, `off` or `on` to override. The default is the owner's call of
//! 2026-11-16 on one subject; it is to be measured on a second.
//!
//! # Why
//!
//! The default gather demosaics each frame (Malvar), warps it, and keeps one
//! colour per CFA site: the four planes the merge folds are a mosaic again,
//! and the output is demosaiced a second time. For a four-shot pixel-shift
//! group the gather already reads measured red, green and blue at every
//! site, and then discards two of them. On the A7CR scarab (2026-11-15) the
//! prototype's outputs pushed through that round trip lost 13-17 % of their
//! fine-detail signal from four-shot data (3-8 % from single shots)
//! (`experiments/a7cr-full-potential-2026-11-14/results.md`, "Merge
//! diagnosis").
//!
//! # What changes
//!
//! The gather also keeps each site's two other channels
//! (`align_cmd::CARRIED_SITES`), quantised exactly as a native site, so the
//! merge folds twelve planes: the four CFA planes, unchanged, then the eight
//! carried ones. The election still runs on the same green luma, so the
//! weights, and the four native planes, are those of a render without the
//! carry; only where the other channels come from differs. The output is the
//! twelve planes interleaved into full-resolution RGB, with no second
//! demosaic. Single shots carry their Malvar estimates. Red and blue are then
//! green plus their difference from green smoothed at one pixel
//! ([`smooth_chroma`]; `STREHL_CARRY_RGB=raw` skips it).
//!
//! # Limits
//!
//! Three times the merge's plane memory. Banded Catmull-Rom gather,
//! `--demosaic` output only; refused with the estimator, temporal energy,
//! axial colour, region repair, the gather-kernel restoration
//! (`STREHL_RESTORE`) and coverage outputs. The GPU fold folds the twelve
//! planes (four per `accum` dispatch).
use super::*;
use std::sync::atomic::{AtomicBool, Ordering};

pub(super) const ENV: &str = "STREHL_CARRY_RGB";

/// Planes folded when carrying: four native, eight carried.
pub(super) const PLANES: usize = BAND_PLANES + align_cmd::CARRIED_SITES.len();

static ACTIVE: AtomicBool = AtomicBool::new(false);

/// Gaussian sigma, output px, of the colour-difference smoothing.
pub(super) const CHROMA_SIGMA: f64 = 1.0;

static RAW: AtomicBool = AtomicBool::new(false);

/// The setting: explicitly on (`Some(raw)`, `raw` true for `raw`), explicitly
/// off, or unset (empty counts as unset).
enum Setting {
    On { raw: bool },
    Off,
    Unset,
}

fn setting() -> Result<Setting> {
    match std::env::var(ENV) {
        Err(std::env::VarError::NotPresent) => Ok(Setting::Unset),
        Err(e) => Err(e).context(ENV),
        Ok(v) => match v.trim() {
            "" => Ok(Setting::Unset),
            "0" | "off" => Ok(Setting::Off),
            "on" | "1" => Ok(Setting::On { raw: false }),
            "raw" => Ok(Setting::On { raw: true }),
            other => anyhow::bail!("{ENV}={other:?} is not off, on or raw"),
        },
    }
}

/// Whether the operator explicitly asked for the carry.
pub(super) fn requested() -> Result<bool> {
    Ok(matches!(setting()?, Setting::On { .. }))
}

/// Whether this render carries colour.
pub(super) fn active() -> bool {
    ACTIVE.load(Ordering::Relaxed)
}

/// Replace red and blue by green plus their Gaussian-smoothed difference
/// from green ([`CHROMA_SIGMA`]), in place, on interleaved RGB `w x h` --
/// unless the render asked for `raw`.
///
/// Carried red and blue are single measured samples per photosite, with all
/// their noise; the Malvar demosaic they replace borrows green's cleaner fine
/// detail for them. Measured on the A7CR scarab four-shot run (odd/even
/// halves, ratios to the plain remosaic): raw carry gave green 1.14x the
/// fine detail at 0.92x the noise but red and blue 0.95-1.03x the detail at
/// 1.09-1.22x the noise (signal-to-noise power 5.8 / 12.8 / 3.5 against
/// 6.6 / 8.3 / 5.9); smoothing the colour difference at 1 px gave 11.9 /
/// 12.8 / 11.8 with colour-edge coherence 0.92-0.94 of the plain render's
/// (2 px: 12.8 in every channel but colour edges at 0.60).
pub(super) fn smooth_chroma(rgb: &mut [f32], w: usize, h: usize) {
    if RAW.load(Ordering::Relaxed) {
        return;
    }
    assert_eq!(rgb.len(), w * h * 3);
    for c in [0usize, 2] {
        let diff: Vec<f32> = rgb.par_chunks_exact(3).map(|p| p[c] - p[1]).collect();
        let smooth = axial_colour::blur(&diff, w, h, CHROMA_SIGMA);
        rgb.par_chunks_exact_mut(3)
            .zip(smooth.par_iter())
            .for_each(|(p, d)| p[c] = p[1] + d);
    }
}

/// Planes the band merge folds in this render.
pub(super) fn band_planes() -> usize {
    if active() { PLANES } else { BAND_PLANES }
}

/// Clears the carry when the render ends, however it ends.
pub(super) struct Active;

impl Drop for Active {
    fn drop(&mut self) {
        ACTIVE.store(false, Ordering::Relaxed);
        RAW.store(false, Ordering::Relaxed);
    }
}

/// Switch the carry on for this render: when asked, or by default on a
/// pixel-shift stack (`pixel_shift_cmd::assembly_requested`). Never for a
/// lateral-CA preview, which only measures channel alignment on the mosaic.
/// Asked for, an unsupported combination is an error; by default, the carry
/// stays off and says why.
pub(super) fn activate_if_requested(
    opts: &MergeOptions,
    temporal_active: bool,
) -> Result<Option<Active>> {
    let raw = match setting()? {
        Setting::On { raw } => raw,
        Setting::Off => return Ok(None),
        Setting::Unset if crate::pixel_shift_cmd::assembly_requested() => {
            let blockers = [
                (!opts.demosaic, "the output is not --demosaic"),
                (axial_colour::is_active(), "axial colour is on"),
                (opts.region_recipe.is_some(), "region repair is on"),
                (
                    strehl_core::restore::gain_cap_from_env().is_some(),
                    "STREHL_RESTORE is on",
                ),
                (temporal_active, "temporal energy is on"),
            ];
            if let Some((_, why)) = blockers.iter().find(|(b, _)| *b) {
                eprintln!(
                    "colour carry    : off for this render -- on by default for pixel-shift stacks, \
                     but {why} ({ENV}=on makes that an error)"
                );
                return Ok(None);
            }
            false
        }
        Setting::Unset => return Ok(None),
    };
    if ca_refine::preview_active() {
        return Ok(None);
    }
    ensure!(
        opts.demosaic,
        "{ENV}=on writes full-resolution RGB and needs --demosaic"
    );
    ensure!(
        !axial_colour::is_active(),
        "{ENV}=on cannot combine with {}=on (the axial correction rewrites the native red and blue \
         planes only)",
        axial_colour::ENV
    );
    ensure!(
        opts.region_recipe.is_none(),
        "{ENV}=on cannot combine with region repair"
    );
    ensure!(
        strehl_core::restore::gain_cap_from_env().is_none(),
        "{ENV}=on cannot combine with STREHL_RESTORE (the gather-kernel restoration runs on the \
         four CFA planes)"
    );
    ACTIVE.store(true, Ordering::Relaxed);
    RAW.store(raw, Ordering::Relaxed);
    eprintln!(
        "colour carry    : ON ({}) -- every site's red, green and blue gathered (measured for \
         a pixel-shift group, Malvar otherwise) and merged as {PLANES} planes on one green \
         election; written as full-resolution RGB with no second demosaic; {}",
        if requested()? {
            format!("{ENV} set")
        } else {
            "default for pixel-shift stacks; to be confirmed on a second subject".to_string()
        },
        if raw {
            "red and blue RAW as carried (comparison arm)".to_string()
        } else {
            format!(
                "red and blue = green + their difference from green smoothed at {CHROMA_SIGMA} px"
            )
        }
    );
    Ok(Some(Active))
}

/// Channel (0 red, 1 green, 2 blue) of each folded plane.
pub(super) fn plane_channel(p: usize) -> usize {
    match p {
        0 => 0,
        1 | 2 => 1,
        3 => 2,
        _ => align_cmd::CARRIED_SITES[p - BAND_PLANES].2,
    }
}

/// Folded plane holding channel `c` at quad site `(dx, dy)`.
pub(super) fn plane_of(dx: usize, dy: usize, c: usize) -> usize {
    let native = BAND_PLANE_OFFSETS
        .iter()
        .position(|&o| o == (dx, dy))
        .expect("a quad site");
    if plane_channel(native) == c {
        return native;
    }
    BAND_PLANES
        + align_cmd::CARRIED_SITES
            .iter()
            .position(|&s| s == (dx, dy, c))
            .expect("every non-native channel is carried")
}

/// Copy the gather's carried planes, cropped to the analysis domain, into
/// `planes[BAND_PLANES..]`.
pub(super) fn copy_carried(
    scratch: &WarpScratch,
    domain: PyramidDomain,
    planes: &mut [Vec<f32>],
) -> Result<()> {
    ensure!(
        scratch.carried_fresh
            && scratch.carried.len() == align_cmd::CARRIED_SITES.len()
            && scratch
                .carried
                .iter()
                .all(|c| c.len() == domain.full.pixels()),
        "{ENV}=on: the gather carried no colour for this frame (it needs the aligned, banded \
         Catmull-Rom gather)"
    );
    let local = domain.analysis();
    let r = domain.rect;
    // Only the gather's computed bands, when it computed some (`bands`).
    let only = scratch.bands.as_deref();
    for (dst, src) in planes[BAND_PLANES..].iter_mut().zip(&scratch.carried) {
        dst.par_chunks_mut(local.width)
            .enumerate()
            .filter(|(y, _)| {
                only.is_none_or(|m| {
                    m.get((r.y + y) / align_cmd::BAND_ROWS)
                        .copied()
                        .unwrap_or(false)
                })
            })
            .for_each(|(y, row)| {
                let o = (r.y + y) * domain.full.width + r.x;
                // Only the gather's computed columns, when it computed some
                // (`columns`).
                match super::local_columns(
                    scratch.columns.as_deref(),
                    (r.y + y) / align_cmd::BAND_ROWS,
                    r.x,
                    local.width,
                ) {
                    None => row.copy_from_slice(&src[o..o + local.width]),
                    Some(spans) => {
                        for (a, b) in spans {
                            row[a..b].copy_from_slice(&src[o + a..o + b]);
                        }
                    }
                }
            });
    }
    Ok(())
}

/// Full-resolution interleaved RGB from twelve normalised planes on a
/// `gw x gh` quad grid.
pub(super) fn interleave(planes: &[Vec<f32>], gw: usize, gh: usize) -> Vec<f32> {
    assert_eq!(planes.len(), PLANES);
    let mw = 2 * gw;
    let table: [[usize; 3]; 4] = std::array::from_fn(|s| {
        let (dx, dy) = BAND_PLANE_OFFSETS[s];
        std::array::from_fn(|c| plane_of(dx, dy, c))
    });
    let mut rgb = vec![0f32; mw * 2 * gh * 3];
    rgb.par_chunks_mut(mw * 3).enumerate().for_each(|(y, row)| {
        let (py, dy) = (y / 2, y % 2);
        for x in 0..mw {
            let (px, dx) = (x / 2, x % 2);
            let site = BAND_PLANE_OFFSETS
                .iter()
                .position(|&o| o == (dx, dy))
                .expect("quad site");
            let i = py * gw + px;
            for c in 0..3 {
                row[3 * x + c] = planes[table[site][c]][i];
            }
        }
    });
    rgb
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_site_has_each_channel_exactly_once() {
        for (dx, dy) in BAND_PLANE_OFFSETS {
            let ps: Vec<usize> = (0..3).map(|c| plane_of(dx, dy, c)).collect();
            for (c, p) in ps.iter().enumerate() {
                assert_eq!(plane_channel(*p), c);
            }
        }
        let mut all: Vec<usize> = BAND_PLANE_OFFSETS
            .iter()
            .flat_map(|&(dx, dy)| (0..3).map(move |c| plane_of(dx, dy, c)))
            .collect();
        all.sort_unstable();
        assert_eq!(all, (0..PLANES).collect::<Vec<_>>());
    }

    #[test]
    fn interleave_puts_each_plane_at_its_site() {
        let (gw, gh) = (3, 2);
        let planes: Vec<Vec<f32>> = (0..PLANES)
            .map(|p| (0..gw * gh).map(|i| (100 * p + i) as f32).collect())
            .collect();
        let rgb = interleave(&planes, gw, gh);
        let mw = 2 * gw;
        for y in 0..2 * gh {
            for x in 0..mw {
                let i = (y / 2) * gw + x / 2;
                for c in 0..3 {
                    let p = plane_of(x % 2, y % 2, c);
                    assert_eq!(rgb[(y * mw + x) * 3 + c], (100 * p + i) as f32);
                }
            }
        }
    }
}
