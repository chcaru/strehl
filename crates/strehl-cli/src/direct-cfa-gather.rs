//! Experimental direct original-CFA gather. Off leaves the original path intact.
use anyhow::{Result, bail, ensure};

pub(crate) fn enabled() -> Result<bool> {
    match std::env::var("STREHL_DIRECT_CFA") {
        Err(std::env::VarError::NotPresent) => Ok(false),
        Ok(v) if v == "off" => Ok(false),
        Ok(v) if v == "on" => {
            ensure!(
                cfg!(feature = "direct-cfa-gather"),
                "STREHL_DIRECT_CFA=on requires direct-cfa-gather build feature"
            );
            Ok(true)
        }
        other => bail!("STREHL_DIRECT_CFA expects off or on, got {other:?}"),
    }
}

pub(crate) fn preflight() -> Result<bool> {
    if !enabled()? {
        return Ok(false);
    }
    ensure!(
        super::fullres_gather_enabled(),
        "direct CFA requires full-resolution gather dispatch"
    );
    ensure!(
        super::align_enabled(),
        "direct CFA requires alignment dispatch"
    );
    for name in [
        "STREHL_GPU_GATHER",
        "STREHL_TEMPORAL_ENERGY",
        "STREHL_SPATIAL_NOISE_FLOOR",
        "STREHL_DIRECT_PLANES",
    ] {
        ensure!(
            matches!(
                std::env::var(name).as_deref(),
                Err(std::env::VarError::NotPresent) | Ok("off")
            ),
            "direct CFA does not support active {name}"
        );
    }
    ensure!(
        std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none(),
        "direct CFA does not support local placement"
    );
    Ok(true)
}

#[cfg(feature = "direct-cfa-gather")]
#[allow(clippy::too_many_arguments)]
pub(super) fn warp<const GREEN_ONLY: bool, F>(
    frame: &mut strehl_raw::Frame,
    t: strehl_core::align::Similarity,
    geom: strehl_core::plane::PlaneGeometry,
    resampler: strehl_core::align::Resampler,
    scratch: &mut super::WarpScratch,
    mut sink: F,
    ca: Option<&strehl_core::optics::OpticalProfile>,
) -> Result<f64>
where
    F: FnMut(
        &mut strehl_raw::Frame,
        (usize, usize),
        &[f32],
        &[bool],
        f32,
        f32,
        super::WarpWriteback,
    ) -> Result<usize>,
{
    use anyhow::Context;
    use rayon::prelude::*;
    use strehl_core::cfa_lattice::ActiveCfa;
    ensure!(
        resampler == strehl_core::align::Resampler::CatmullRom,
        "direct CFA currently requires a Catmull-Rom warp map"
    );
    let (gw, gh) = (geom.width, geom.height);
    ensure!(
        frame.active.width / 2 == gw && frame.active.height / 2 == gh,
        "direct CFA geometry mismatch"
    );
    let writeback = super::warp_writeback_mode()?;
    let black = frame.levels.black;
    let gain = super::wb_gains(&frame.wb_coeffs);
    // The sink modifies every phase. Both greens must keep reading original
    // sensels, so retain one u16 source, never a volume of aligned frames.
    let original = frame.data.clone();
    let source = ActiveCfa::new(
        &original,
        frame.stride,
        frame.active.x,
        frame.active.y,
        2 * gw,
        2 * gh,
    )
    .context("invalid direct-CFA active buffer")?;
    let (cx, cy) = (gw as f64 * 0.5, gh as f64 * 0.5);
    let mut covered = 0usize;
    for dy in 0..2usize {
        for dx in 0..2usize {
            let ci = super::rggb_channel_index(dx, dy);
            if GREEN_ONLY && ci != 1 {
                continue;
            }
            let ch = strehl_core::optics::cfa_site_channel(dx, dy);
            let t_site = strehl_core::optics::OpticalProfile::compose(ca, ch, t);
            let (ox, oy) = (dx as f64 * 0.5, dy as f64 * 0.5);
            scratch
                .dst
                .par_chunks_mut(gw)
                .zip(scratch.cover.par_chunks_mut(gw))
                .enumerate()
                .for_each(|(py, (drow, crow))| {
                    for (px, (value, valid)) in drow.iter_mut().zip(crow.iter_mut()).enumerate() {
                        let (sx, sy) = t_site.apply_at(px as f64 + ox, py as f64 + oy, cx, cy);
                        if let Some(dn) = source.sample_checked(ci, 2.0 * sx, 2.0 * sy) {
                            *value = (dn - black) * gain[ci];
                            *valid = true;
                        } else {
                            *value = f32::NAN;
                            *valid = false;
                        }
                    }
                });
            covered += sink(
                frame,
                (dx, dy),
                &scratch.dst,
                &scratch.cover,
                1.0 / gain[ci],
                black,
                writeback,
            )?;
        }
    }
    let phases = if GREEN_ONLY { 2 } else { 4 };
    Ok(covered as f64 / (phases * geom.pixels()) as f64)
}

#[cfg(feature = "direct-cfa-gather")]
pub(crate) fn validate_domain(
    paths: &[std::path::PathBuf],
    map: Option<&strehl_core::warpmap::WarpMap>,
    rect: super::CropRect,
) -> Result<()> {
    use anyhow::Context;
    use strehl_core::warpmap::FrameWarp;
    let map = map.context("direct CFA requires resolved alignment geometry")?;
    ensure!(
        map.resampler() == strehl_core::align::Resampler::CatmullRom,
        "direct CFA requires a Catmull-Rom warp map"
    );
    ensure!(
        map.warps().len() == paths.len(),
        "direct CFA input/map count mismatch"
    );
    let geom = map.geometry();
    let (cx, cy) = (geom.width as f64 * 0.5, geom.height as f64 * 0.5);
    // Every nonzero cubic stencil is within four native pixels of the query.
    // Affine coordinates attain each axis extremum at a rectangle corner.
    for (i, (path, placed)) in paths.iter().zip(map.warps()).enumerate() {
        let FrameWarp::Placed(t) = placed else {
            bail!("direct CFA refuses unplaced frame {i}");
        };
        let ident = strehl_raw::identity(path);
        let ca =
            strehl_core::optics::profile_for_capture_env(ident.model.as_deref(), ident.lens_type3)?;
        for dy in 0..2 {
            for dx in 0..2 {
                let ch = strehl_core::optics::cfa_site_channel(dx, dy);
                let transform = strehl_core::optics::OpticalProfile::compose(ca, ch, *t);
                for py in [rect.y, rect.y + rect.height - 1] {
                    for px in [rect.x, rect.x + rect.width - 1] {
                        let (x, y) = transform.apply_at(
                            px as f64 + dx as f64 * 0.5,
                            py as f64 + dy as f64 * 0.5,
                            cx,
                            cy,
                        );
                        let (x, y) = (2.0 * x, 2.0 * y);
                        ensure!(
                            x.is_finite()
                                && y.is_finite()
                                && x >= 4.0
                                && y >= 4.0
                                && x <= (2 * geom.width - 1) as f64 - 4.0
                                && y <= (2 * geom.height - 1) as f64 - 4.0,
                            "direct CFA crop lacks conservative support: frame {i}, phase ({dx},{dy}), source ({x},{y})"
                        );
                    }
                }
            }
        }
    }
    eprintln!(
        "direct CFA support: all {} placed frames, four phases and delivered crop corners verified",
        paths.len()
    );
    Ok(())
}
