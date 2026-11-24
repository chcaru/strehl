//! Region-only depth repair (implementation plan E4, phase P7d).
//!
//! A source-range repair re-folds a region's permitted frames in a separate
//! accumulator and blends the result into the merged CFA before colour
//! development (`region-repair.rs`). A full repair runs that after re-running
//! the whole stack. This runs only the repair, against the master an earlier
//! render of the same stack wrote:
//!
//! - **The repair pass is the full render's, unchanged.** Same frames, same
//!   canonical chunks, same full analysis domain, same noise model, warps and
//!   merge configuration. A cropped domain would be cheaper but cannot be
//!   exact: the ensemble gate measures its null on a window centred in the
//!   domain, so a crop measures different thresholds and selects differently.
//! - **The original CFA is rebuilt from the master** by inverting the colour
//!   matrix at every site (the demosaic keeps each site's own sample). Only
//!   the blend ring reads it: a site any region covers fully takes the
//!   repair's value, exactly as in the full render.
//! - **Everything else is pinned to the original:** the tone (from the
//!   master's baseline), the lateral-CA refinement (`--reuse-ca-from`) and
//!   the alignment (the run's warp map, by `STREHL_WARPMAP`).
//! - **Outside the repair's reach the original bytes are kept.** A pixel
//!   whose 5 x 5 Malvar stencil meets no site of any region keeps the
//!   original master's and photograph's samples bit for bit.
//!
//! Pixels whose whole stencil lies on fully covered sites are bit-identical
//! to a full render with the same repair, tone and CA. The ring between
//! carries the inverse's rounding (and, above the highlight knee, where the
//! matrix is not inverted exactly, more); the gate measures it.
use super::*;
use std::io::BufReader;

/// The Malvar-He-Cutler stencil's reach, in output pixels.
const STENCIL: usize = 2;

/// Why a render cannot be repaired region-only; empty when it can.
pub(super) fn refusals(
    opts: &MergeOptions,
    temporal_active: bool,
    frame_refine: bool,
) -> Vec<&'static str> {
    let mut why = Vec::new();
    let mut refuse = |cond: bool, reason: &'static str| {
        if cond {
            why.push(reason);
        }
    };
    refuse(!opts.demosaic, "the render is not full resolution");
    refuse(
        !opts.space.wants_matrix(),
        "the render has no colour matrix to invert",
    );
    refuse(opts.linear_master.is_none(), "no linear master is written");
    refuse(opts.sensor_master.enabled(), "a sensor master is written");
    refuse(temporal_active, "temporal energy is on");
    refuse(
        colour_carry::active(),
        "colour is carried through the merge",
    );
    refuse(optical_restore::active(), "the optical restoration is on");
    refuse(
        fusion_calibrated::requested(),
        "the calibrated fusion is on",
    );
    refuse(
        depth_guide::active().is_some(),
        "the depth guide replaces the election",
    );
    refuse(
        axial_colour::is_active(),
        "the axial-colour correction is on",
    );
    refuse(frame_refine, "frame refinement measures every frame");
    refuse(
        std::env::var_os(self_flat::ENV).is_some_and(|v| !v.is_empty() && v != "off"),
        "the self flat is built from every frame",
    );
    refuse(
        strehl_core::restore::gain_cap_from_env().is_some(),
        "a restoration gain cap is set",
    );
    refuse(
        std::env::var(strehl_core::demosaic::DEMOSAIC_ENV)
            .is_ok_and(|v| v.eq_ignore_ascii_case("directional")),
        "the directional demosaic's stencil is not the Malvar one",
    );
    why
}

/// The original render's outputs, checked against this render's geometry.
struct Original {
    master: Vec<f32>,
    photo: Vec<u16>,
    tone: image_out::Tone,
    exposure_gain: f32,
}

fn load(plan: &RegionOnly, size: [usize; 2]) -> Result<Original> {
    let master = strehl_edit::load_tiff(&plan.master)
        .with_context(|| format!("reading the original master {}", plan.master.display()))?;
    ensure!(
        master.origin == strehl_edit::ImageOrigin::SceneLinear,
        "{} is not a scene-linear master",
        plan.master.display()
    );
    ensure!(
        [master.width as usize, master.height as usize] == size,
        "the original master is {} x {}, this render {} x {}",
        master.width,
        master.height,
        size[0],
        size[1]
    );
    let baseline = master
        .baseline
        .context("the original master does not record its tone")?;
    let photo = read_rgb16(&plan.photo, size)?;
    Ok(Original {
        master: master.pixels,
        photo,
        tone: image_out::Tone {
            black: baseline.black,
            white: baseline.white,
            contrast: baseline.contrast,
            shoulder: baseline.shoulder,
        },
        exposure_gain: baseline.exposure_gain,
    })
}

fn read_rgb16(path: &Path, size: [usize; 2]) -> Result<Vec<u16>> {
    let file = std::fs::File::open(path)
        .with_context(|| format!("opening the original photograph {}", path.display()))?;
    let mut decoder = tiff::decoder::Decoder::new(BufReader::new(file))?
        .with_limits(tiff::decoder::Limits::unlimited());
    let (w, h) = decoder.dimensions()?;
    ensure!(
        [w as usize, h as usize] == size,
        "the original photograph is {w} x {h}, this render {} x {}",
        size[0],
        size[1]
    );
    ensure!(
        decoder.colortype()? == tiff::ColorType::RGB(16),
        "the original photograph is not 16-bit RGB"
    );
    match decoder.read_image()? {
        tiff::decoder::DecodingResult::U16(v) if v.len() == size[0] * size[1] * 3 => Ok(v),
        _ => anyhow::bail!("the original photograph's samples do not decode as 16-bit RGB"),
    }
}

/// What the repair does to one output site.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Site {
    /// No region reaches it: the original value.
    Original,
    /// Blended between the original and repairs.
    Mixed,
    /// Some region covers it fully: repaired values only.
    Repaired,
}

/// Every output site's fate, row-major over the full-resolution mosaic.
fn sites(repairs: &region_repair::Repairs, geom: PlaneGeometry) -> Vec<Site> {
    let (mw, mh) = (2 * geom.width, 2 * geom.height);
    let shapes: Vec<_> = repairs
        .regions()
        .map(|r| (r.shape.prepare(), r.feather))
        .collect();
    let mut out = vec![Site::Original; mw * mh];
    out.par_chunks_mut(mw).enumerate().for_each(|(row, sites)| {
        let (y, cy) = (row / 2, row % 2);
        for (col, site) in sites.iter_mut().enumerate() {
            let (x, cx) = (col / 2, col % 2);
            // The same coordinates, to the bit, as the blend's.
            let uv = region_repair::uv(x, y, 2 * cy + cx, geom);
            for (shape, feather) in &shapes {
                let w = shape.weight(uv, *feather);
                if w >= 1.0 {
                    *site = Site::Repaired;
                    break;
                }
                if w > 0.0 {
                    *site = Site::Mixed;
                }
            }
        }
    });
    out
}

/// Per output pixel: keep the original (no site in reach), exact (only
/// repaired sites in reach), or ring. Counts of the last two.
fn reach(sites: &[Site], mw: usize, mh: usize) -> (Vec<bool>, usize, usize) {
    // Row-wise then column-wise maxima of two flags over the stencil.
    let flag = |pick: fn(Site) -> bool| -> Vec<bool> {
        let rows: Vec<bool> = (0..mw * mh)
            .into_par_iter()
            .map(|i| {
                let (x, y) = (i % mw, i / mw);
                (x.saturating_sub(STENCIL)..=(x + STENCIL).min(mw - 1))
                    .any(|xx| pick(sites[y * mw + xx]))
            })
            .collect();
        (0..mw * mh)
            .into_par_iter()
            .map(|i| {
                let (x, y) = (i % mw, i / mw);
                (y.saturating_sub(STENCIL)..=(y + STENCIL).min(mh - 1)).any(|yy| rows[yy * mw + x])
            })
            .collect()
    };
    let touched = flag(|s| s != Site::Original);
    let inexact = flag(|s| s != Site::Repaired);
    let keep: Vec<bool> = touched.iter().map(|t| !t).collect();
    let rebuilt = touched.iter().filter(|&&t| t).count();
    let exact = touched
        .iter()
        .zip(&inexact)
        .filter(|&(&t, &i)| t && !i)
        .count();
    (keep, exact, rebuilt - exact)
}

/// The merged CFA planes (black-subtracted DN, as the band merge returns
/// them) that developed into `master`: the colour matrix inverted at each
/// site, then the writer's normalisation undone.
fn original_planes(
    master: &[f32],
    geom: PlaneGeometry,
    to_srgb: &[[f32; 3]; 3],
    gains: [f32; 3],
    exposure_gain: f32,
    range: f32,
) -> Result<Vec<Vec<f32>>> {
    let inverse = invert(to_srgb).context("the colour matrix is singular")?;
    let mw = 2 * geom.width;
    let channel = [0usize, 1, 1, 2];
    Ok((0..BAND_PLANES)
        .map(|c| {
            let ch = channel[c];
            let scale = f64::from(range) / (f64::from(gains[ch]) * f64::from(exposure_gain));
            (0..geom.pixels())
                .into_par_iter()
                .map(|i| {
                    let (x, y) = (i % geom.width, i / geom.width);
                    let at = ((2 * y + c / 2) * mw + 2 * x + c % 2) * 3;
                    let rgb = &master[at..at + 3];
                    let cam: f64 = (0..3).map(|k| inverse[ch][k] * f64::from(rgb[k])).sum();
                    (cam * scale) as f32
                })
                .collect()
        })
        .collect())
}

fn invert(m: &[[f32; 3]; 3]) -> Option<[[f64; 3]; 3]> {
    let a = m.map(|r| r.map(f64::from));
    let det = a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
        - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
        + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]);
    if !det.is_finite() || det.abs() < 1e-12 {
        return None;
    }
    let c =
        |r0: usize, c0: usize, r1: usize, c1: usize| a[r0][c0] * a[r1][c1] - a[r0][c1] * a[r1][c0];
    Some([
        [
            c(1, 1, 2, 2) / det,
            -c(0, 1, 2, 2) / det,
            c(0, 1, 1, 2) / det,
        ],
        [
            -c(1, 0, 2, 2) / det,
            c(0, 0, 2, 2) / det,
            -c(0, 0, 1, 2) / det,
        ],
        [
            c(1, 0, 2, 1) / det,
            -c(0, 0, 2, 1) / det,
            c(0, 0, 1, 1) / det,
        ],
    ])
}

/// Everything the region-only render borrows from the full render's setup.
pub(super) struct Inputs<'a, S> {
    pub opts: &'a MergeOptions,
    pub plan: &'a RegionOnly,
    pub repairs: &'a region_repair::Repairs,
    pub cx: region_repair::RepairContext<'a, S>,
    pub pool: &'a rayon::ThreadPool,
    pub wb: Option<[f32; 3]>,
    pub xyz_to_cam: Option<&'a ([[f32; 3]; 3], String)>,
    pub exposure: Exposure,
    pub progress: &'a crate::ui_progress::Progress,
}

pub(super) fn render<S: PyramidFrameSource>(inputs: Inputs<'_, S>) -> Result<()> {
    let Inputs {
        opts,
        plan,
        repairs,
        cx,
        pool,
        wb,
        xyz_to_cam,
        exposure,
        progress,
    } = inputs;
    let started = Instant::now();
    let path = opts.out.as_deref().context("region-only needs --out")?;
    let master_out = opts
        .linear_master
        .as_deref()
        .context("region-only needs --linear-master")?;
    ensure!(
        repairs.active(),
        "region-only needs a region with a source range"
    );
    let (domain, levels) = (cx.domain, cx.levels);
    let geom = domain.analysis();
    let (mw, mh) = (2 * geom.width, 2 * geom.height);
    let render = xyz_to_cam
        .and_then(|(m, _)| strehl_core::color::camera_to_srgb(*m))
        .context("region-only needs the camera's colour matrix")?;
    let original = load(plan, [mw, mh])?;
    eprintln!(
        "region only     : rebuilding the painted regions against {} (frames outside their \
         ranges are not decoded)",
        plan.master.display()
    );
    let site = sites(repairs, geom);
    let (keep, exact, ring) = reach(&site, mw, mh);
    drop(site);
    let mut planes = original_planes(
        &original.master,
        geom,
        render.matrix(),
        wb.unwrap_or([1.0, 1.0, 1.0]),
        original.exposure_gain,
        levels.range(),
    )?;
    progress.render_step("region-repair", "started");
    pool.install(|| repairs.apply(&mut planes, cx))?;
    progress.render_step("region-repair", "finished");
    image_out::begin_region_composite(image_out::RegionComposite {
        tone: original.tone,
        exposure_gain: original.exposure_gain,
        keep,
        master: original.master,
        photo: original.photo,
        wrote_master: false,
        wrote_photo: false,
    });
    let written = write_merged_observed(
        Merged::Bands {
            domain,
            planes: &planes,
        },
        levels,
        wb,
        xyz_to_cam,
        opts.space,
        opts.demosaic,
        exposure,
        None,
        path,
        progress.observer(),
        Some(master_out),
        repairs.applied_recipe(),
    );
    let composite = image_out::end_region_composite();
    written?;
    let composite = composite.context("the region-only composite was lost")?;
    ensure!(
        composite.wrote_master && composite.wrote_photo,
        "the writer did not keep the original outside the repair (another output path ran)"
    );
    let total = mw * mh;
    eprintln!(
        "region only     : {} of {total} pixels rebuilt ({:.2} %): {exact} only from repaired \
         sites, {ring} in the blend ring; the other {} keep the original bytes; {:.2} s",
        exact + ring,
        100.0 * (exact + ring) as f64 / total as f64,
        total - exact - ring,
        started.elapsed().as_secs_f64()
    );
    Ok(())
}
