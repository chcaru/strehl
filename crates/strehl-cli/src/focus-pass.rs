//! The streaming focus-evidence pass over one ordered sweep of frames, for
//! any frame source: a multi-stack session's pass (`session_focus`) or an
//! ordinary stack's RAWs (`strehl stack --focus-evidence`).
//!
//! The pass never changes a merge. It reads each placed frame twice (an
//! anchor pass, then a shape pass), gathers its greens at the alignment's
//! placement, and folds the regularised focus response into a
//! [`FocusEvidenceBuilder`]. It stores no aligned volume: per-pixel state is
//! fixed, whatever the frame count ([`reservation_bytes`]).
use crate::session_sampling::{NativeSampler, SamplingDomain, sampling_bytes};
use anyhow::{Context, Result, ensure};
use strehl_core::focus::{FINE_WINDOW_RADIUS, FocusField, window_radius};
use strehl_core::focus_evidence::{
    FocusEvidence, FocusEvidenceBuilder, FocusEvidencePolicy, FocusFrame,
};
use strehl_core::merge::{REGULARISER_RADIUS, regularise};
use strehl_core::noise::{Levels, NoiseModel};
use strehl_core::optics::OpticalProfile;
use strehl_core::plane::{PlaneGeometry, QuadSource};
use strehl_core::warpmap::WarpMap;

/// One decoded original frame, as the pass reads it: its CFA rows and the
/// identity its calibration is checked against.
pub trait FocusSource {
    fn quad(&self) -> &dyn QuadSource;
    fn camera(&self) -> &str;
    fn iso(&self) -> Option<f32>;
    fn levels(&self) -> Levels;
}

/// Where the pass gets frames: by global index, in the order it asks for
/// them (each placed frame of the sweep, then each again).
pub trait FocusFrames {
    type Source: FocusSource;
    fn load(&mut self, global_index: usize) -> Result<Self::Source>;
}

impl FocusSource for strehl_raw::Frame {
    fn quad(&self) -> &dyn QuadSource {
        self
    }
    fn camera(&self) -> &str {
        &self.camera
    }
    fn iso(&self) -> Option<f32> {
        self.iso
    }
    fn levels(&self) -> Levels {
        self.levels
    }
}

/// The pass's result: the full-resolution field and what it cost.
pub struct FocusPass {
    pub field: FocusEvidence,
    /// At least one original source covers the pixel, irrespective of clipping
    /// or focus-filter support. Distinct from field.covered and field.usable.
    pub raw_coverage: Vec<bool>,
    pub reservation_bytes: usize,
    pub elapsed_seconds: f64,
}

/// Actual per-pixel arrays plus source sampler, one source decode/copy allowance,
/// and the caller-owned original cache. The caller reserves its other live work.
pub fn reservation_bytes(domain: SamplingDomain, frames: usize) -> Result<usize> {
    domain.validate()?;
    let geom = PlaneGeometry {
        width: domain.width,
        height: domain.height,
    };
    FocusEvidenceBuilder::reservation_bytes(geom, frames)?
        .checked_add(sampling_bytes(domain)?)
        .and_then(|n| n.checked_add(domain.pixels().checked_mul(48)?))
        .and_then(|n| n.checked_add(domain.full.pixels().checked_mul(32)?))
        .context("focus evidence memory reservation overflow")
}

/// Fold the frames `sweep` (global indices, in acquisition order) into focus
/// evidence. Warp placements use the caller's full anchor grid; ordinal zero
/// is the sweep's first frame, placed or not. `label` prefixes the progress
/// lines.
#[allow(clippy::too_many_arguments)]
pub fn compute<F: FocusFrames>(
    frames_in: &mut F,
    sweep: &[usize],
    map: &WarpMap,
    domain: SamplingDomain,
    noise: &NoiseModel,
    profile: Option<&OpticalProfile>,
    budget: usize,
    label: &str,
) -> Result<FocusPass> {
    let started = std::time::Instant::now();
    ensure!(!sweep.is_empty(), "focus sweep is empty");
    ensure!(
        sweep.iter().all(|&i| i < map.len()),
        "focus sweep outside the warp map"
    );
    ensure!(
        map.geometry() == domain.full,
        "focus warp gauge differs from full domain"
    );
    let reserved = reservation_bytes(domain, sweep.len())?;
    ensure!(
        reserved <= budget,
        "focus evidence needs {:.2} GiB; increase session memory limit",
        reserved as f64 / (1_u64 << 30) as f64
    );
    let lead_index = sweep[0];
    let lead = frames_in.load(lead_index)?;
    let expected_camera = lead.camera().to_owned();
    let expected_iso = lead.iso();
    let expected_levels = lead.levels();
    ensure!(
        lead.quad().geometry() == domain.full
            && expected_iso == Some(noise.iso)
            && strehl_core::CfaPlane::ALL
                .into_iter()
                .all(|p| noise.plane(p).levels == expected_levels),
        "focus injected calibration does not match source geometry, levels or ISO"
    );
    drop(lead);
    let frames: Vec<_> = sweep
        .iter()
        .map(|&global_index| FocusFrame {
            acquisition: global_index as u64,
            global_index,
        })
        .collect();
    let geom = PlaneGeometry {
        width: domain.width,
        height: domain.height,
    };
    let n = geom.pixels();
    let mut builder =
        FocusEvidenceBuilder::new(geom, frames.clone(), FocusEvidencePolicy::default(), budget)?;
    let mut sampler = NativeSampler::new(domain)?;
    let mut field = FocusField::new(geom);
    let mut green = vec![0.0; n];
    let mut fine = vec![0.0; n];
    let mut regularized = vec![0.0; n];
    let mut scratch = vec![0.0; n];
    let mut mask_scratch = vec![0_u32; n];
    let mut valid = vec![false; n];
    let mut raw_coverage = vec![false; n];
    let halo = window_radius()
        .checked_add(1 + REGULARISER_RADIUS)
        .context("focus halo overflow")?;
    for phase in 0..2 {
        if phase == 1 {
            builder.begin_shape_pass()?;
        }
        for (ordinal, &frame) in frames.iter().enumerate() {
            if let Some(placement) = map.warps()[frame.global_index].placed() {
                let source = frames_in.load(frame.global_index)?;
                ensure!(
                    source.quad().geometry() == domain.full
                        && source.camera() == expected_camera
                        && source.iso() == expected_iso
                        && source.levels() == expected_levels,
                    "focus source calibration changes within pass at acquisition {}",
                    frame.global_index
                );
                let sampled = sampler.gather(
                    source.quad(),
                    source.levels(),
                    placement,
                    profile,
                    map.resampler(),
                )?;
                for i in 0..n {
                    green[i] = 0.5 * (sampled.planes[1][i] + sampled.planes[3][i]);
                    raw_coverage[i] |= sampled.coverage[i];
                }
                complete_support(&sampled.support, geom, halo, &mut mask_scratch, &mut valid)?;
                field.compute_with_fine(&green, noise, FINE_WINDOW_RADIUS, &mut fine);
                regularise(field.values(), geom, &mut scratch, &mut regularized);
            } else {
                valid.fill(false);
                regularized.fill(0.0);
                fine.fill(0.0);
            }
            if phase == 0 {
                builder.observe_anchor(ordinal, frame, &regularized, &valid)?;
            } else {
                builder.observe_shape(ordinal, frame, &fine, &regularized, &valid)?;
            }
            if ordinal % 25 == 0 || ordinal + 1 == frames.len() {
                eprintln!(
                    "{label} phase {} frame {}/{}",
                    phase + 1,
                    ordinal + 1,
                    frames.len()
                );
            }
        }
    }
    Ok(FocusPass {
        field: builder.finish()?,
        raw_coverage,
        reservation_bytes: reserved,
        elapsed_seconds: started.elapsed().as_secs_f64(),
    })
}

/// Every tap in the composed Sobel/box/regularizer footprint must be supported.
/// Exterior samples are unknown, not reflected validity. O(pixels), fixed scratch.
pub fn complete_support(
    input: &[bool],
    g: PlaneGeometry,
    r: usize,
    scratch: &mut [u32],
    out: &mut [bool],
) -> Result<()> {
    ensure!(
        g.width > 0
            && g.height > 0
            && input.len() == g.pixels()
            && scratch.len() == input.len()
            && out.len() == input.len(),
        "invalid focus support dimensions"
    );
    out.fill(false);
    scratch.fill(0);
    let width = r
        .checked_mul(2)
        .and_then(|v| v.checked_add(1))
        .context("focus support radius overflow")?;
    if width > g.width || width > g.height {
        return Ok(());
    }
    ensure!(
        width
            .checked_mul(width)
            .is_some_and(|n| n <= u32::MAX as usize),
        "focus support counter overflow"
    );
    for y in 0..g.height {
        let row = &input[y * g.width..(y + 1) * g.width];
        let mut bad = row[..width].iter().filter(|&&ok| !ok).count() as u32;
        for x in r..g.width - r {
            scratch[y * g.width + x] = bad;
            if x + 1 < g.width - r {
                bad += u32::from(!row[x + r + 1]);
                bad -= u32::from(!row[x - r]);
            }
        }
    }
    for x in r..g.width - r {
        let mut bad = (0..width).map(|y| scratch[y * g.width + x]).sum::<u32>();
        for y in r..g.height - r {
            out[y * g.width + x] = bad == 0;
            if y + 1 < g.height - r {
                bad += scratch[(y + r + 1) * g.width + x];
                bad -= scratch[(y - r) * g.width + x];
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn support_requires_all_taps_and_never_invents_exterior() {
        let g = PlaneGeometry {
            width: 13,
            height: 11,
        };
        let mut input = vec![true; g.pixels()];
        let mut scratch = vec![0; g.pixels()];
        let mut out = vec![false; g.pixels()];
        complete_support(&input, g, 2, &mut scratch, &mut out).unwrap();
        assert_eq!(out.iter().filter(|&&v| v).count(), 9 * 7);
        input[g.index(6, 5)] = false;
        complete_support(&input, g, 2, &mut scratch, &mut out).unwrap();
        for y in 0..g.height {
            for x in 0..g.width {
                assert_eq!(
                    out[g.index(x, y)],
                    (2..11).contains(&x)
                        && (2..9).contains(&y)
                        && !(x.abs_diff(6) <= 2 && y.abs_diff(5) <= 2)
                );
            }
        }
        complete_support(&input, g, usize::MAX, &mut scratch, &mut out).unwrap_err();
    }
}
