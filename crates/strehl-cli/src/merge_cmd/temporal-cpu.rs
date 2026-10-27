//! Explicit experimental CPU scheduler for the fixed finest-two temporal guide.
//! Default/off dispatch stays in the ordinary loop. This module never retains
//! an aligned frame or coefficient volume; centers are identically regathered.
use super::*;
use strehl_core::pyramid::temporal_energy::{Mode, Ring};
use strehl_core::pyramid::{BandObservation, Fallback, FoldPhase, MergeObserver};

pub(super) const ENV: &str = "STREHL_TEMPORAL_ENERGY";

pub(super) fn parse_mode(value: Option<&str>) -> Result<Mode> {
    match value {
        None | Some("off") => Ok(Mode::Off),
        Some("on") => Ok(Mode::On),
        Some("shift") => Ok(Mode::ShiftNeighbors),
        _ => bail!("invalid {ENV}={value:?}; use off/on/shift"),
    }
}

pub(super) fn environment_mode() -> Result<Mode> {
    match std::env::var(ENV) {
        Ok(value) => parse_mode(Some(&value)),
        Err(std::env::VarError::NotPresent) => parse_mode(None),
        Err(error) => Err(error).context(ENV),
    }
}

/// Check every placement before decoding any guide; gaps must never become
/// neighboring captures. With no map, the caller explicitly chose identity.
pub(super) fn preflight(
    cfg: MergeConfig,
    total: usize,
    warps: Option<&WarpMap>,
    region_recipe_active: bool,
) -> Result<()> {
    ensure!(
        total > 0 && total <= u32::MAX as usize,
        "invalid temporal source count"
    );
    ensure!(
        !region_recipe_active,
        "experimental temporal energy does not support region repair"
    );
    ensure!(
        cfg.select == SelectMode::SoftPower
            && cfg.admission == AdmissionMode::HardFloor
            && cfg.base == BaseBand::Mean
            && cfg.fallback == Fallback::Mean,
        "experimental temporal energy requires SoftPower, HardFloor, Mean base and Mean fallback"
    );
    ensure!(
        cfg.gate.is_finite() && cfg.gate > 0.0,
        "invalid temporal gate"
    );
    ensure!(
        !cfg!(feature = "m194h-pedestal-causality")
            && !cfg!(feature = "native-sensor-transfer")
            && !cfg!(feature = "native-boundary-radiance"),
        "experimental temporal energy cannot combine coefficient/boundary rewriter features"
    );
    #[cfg(feature = "native-gpu-gather")]
    ensure!(
        !align_cmd::native_gpu_integration::gpu_gather_enabled()?,
        "experimental temporal energy requires the CPU gather path"
    );
    #[cfg(feature = "native-correction-variance")]
    ensure!(
        strehl_core::pyramid::fine_support_candidate::environment_mode()
            == strehl_core::pyramid::fine_support_candidate::Mode::Off,
        "experimental temporal energy requires fine-support rewriting Off"
    );
    #[cfg(feature = "spatial-noise-floor")]
    ensure!(
        matches!(
            std::env::var("STREHL_SPATIAL_NOISE_FLOOR"),
            Err(std::env::VarError::NotPresent)
        ) || matches!(
            std::env::var("STREHL_SPATIAL_NOISE_FLOOR").as_deref(),
            Ok("off" | "0")
        ),
        "experimental temporal energy requires STREHL_SPATIAL_NOISE_FLOOR=off"
    );
    if let Some(map) = warps {
        for index in 0..total {
            ensure!(
                matches!(map.warp(index)?, FrameWarp::Placed(_)),
                "experimental temporal energy requires all sources placed; frame {index} was refused"
            );
        }
    }
    Ok(())
}

/// Reserve known buffers omitted from the historical arithmetic-partition
/// formula. Full-grid sizes deliberately overestimate cropped workspaces.
/// Includes both accumulators' optional level hulls/diagnostics, hidden
/// workspace pyramids, probe arrays and clone, and shared warp scratch.
/// This is a buffer reservation, not a claim about decoder/allocator peak RSS.
pub(super) fn extra_buffer_bytes(
    full_sizes: &[strehl_core::pyramid::LevelSize],
    frame_bytes: usize,
    execution_threads: usize,
) -> Result<usize> {
    let size = full_sizes.first().context("missing temporal geometry")?;
    let n = size.pixels() as u128;
    let pyramid: u128 = full_sizes.iter().map(|s| s.pixels() as u128).sum();
    let width = size.width as u128;
    let accumulators = 2 * (3 * BAND_PLANES as u128 * (pyramid - n) + 4 * pyramid);
    let workspace = pyramid + 2 * n + width;
    let probe = 5 * n + width + pyramid;
    // Native gather simultaneously owns mosaic + R/G/B at four times the
    // quad pixel count, plus one RGB row per active execution thread.
    let native_gather = 64 * n + 24 * width * execution_threads as u128;
    usize::try_from(
        4 * (accumulators + workspace + probe) + 9 * n + native_gather + frame_bytes as u128,
    )
    .context("temporal extra buffer byte overflow")
}

/// This check does not participate in canonical chunk selection. It adds the
/// bounded guide fields and retained accumulator to the existing worker plan.
pub(super) fn memory_preflight(
    planning_bytes: usize,
    retained_accumulator_bytes: usize,
    sizes: &[strehl_core::pyramid::LevelSize],
) -> Result<usize> {
    let samples = sizes
        .iter()
        .take(sizes.len().saturating_sub(1).min(2))
        .try_fold(0usize, |n, size| n.checked_add(size.pixels()))
        .context("temporal guide size overflow")?;
    // E + F, three raw guides during push and one emitted guide, f32 storage.
    let guide_bytes = samples
        .checked_mul(2 * 4 * std::mem::size_of::<f32>())
        .context("temporal guide byte overflow")?;
    let peak = planning_bytes
        .checked_add(retained_accumulator_bytes)
        .and_then(|v| v.checked_add(guide_bytes))
        .context("temporal memory plan overflow")?;
    ensure!(
        peak <= MEMORY_BUDGET_BYTES,
        "experimental temporal estimated working set {peak} exceeds budget {MEMORY_BUDGET_BYTES}; guide fields alone {guide_bytes} bytes"
    );
    Ok(guide_bytes)
}

/// Optional commissioning view. Production diagnostics use FrameTap directly.
/// No callback returns data to the scheduler or allocates an image here.
pub(super) trait Observer: MergeObserver {
    fn guide(&self, _index: usize, _beta: &[f32]) {}
    fn ready(&self, _index: usize, _chunk: usize, _original: bool, _neighbors: Option<[usize; 2]>) {
    }
    fn folded(&self, _index: usize, _merge: &BandMerge) {}
    fn chunk(&self, _chunk: usize, _merge: &BandMerge) {}
}

struct Relay<'a> {
    tap: Option<crate::ui_progress::FrameTap<'a>>,
    external: Option<&'a dyn Observer>,
}
impl MergeObserver for Relay<'_> {
    fn supports_absolute_floor(&self) -> bool {
        self.external.is_none_or(|o| o.supports_absolute_floor())
    }
    fn phase(&self, phase: FoldPhase) {
        if let Some(tap) = &self.tap {
            tap.phase(phase);
        }
        if let Some(observer) = self.external {
            observer.phase(phase);
        }
    }
    fn band(&self, band: BandObservation<'_>) {
        if let Some(tap) = &self.tap {
            tap.band(band);
        }
        if let Some(observer) = self.external {
            observer.band(band);
        }
    }
}

pub(super) struct FoldResult {
    pub merge: BandMerge,
    pub folded_total: usize,
    pub beta_sum: Vec<f64>,
    pub beta_n: usize,
}

/// One global ring spans the exact existing canonical chunks. Every emitted
/// center folds into its own chunk, including the last center after lookahead
/// from the next chunk. Off is accepted here for commissioning against the
/// unchanged ordinary loop; normal default/off dispatch never calls this path.
#[allow(clippy::too_many_arguments)]
pub(super) fn fold(
    source: &impl PyramidFrameSource,
    worker: &mut BandWorker,
    levels: Levels,
    noise: &NoiseModel,
    warps: Option<&WarpMap>,
    defect: Option<(&crate::stack::DefectPlan, &crate::stack::DefectTally)>,
    progress: Option<&crate::ui_progress::Progress>,
    total: usize,
    per_chunk: usize,
    mode: Mode,
    observer: Option<&dyn Observer>,
) -> Result<FoldResult> {
    preflight(worker.config, total, warps, false)?;
    ensure!(
        source.len() == total && per_chunk > 0,
        "invalid temporal source/chunk plan"
    );
    ensure!(
        worker.merge.frames() == 0 && worker.beta_n == 0,
        "temporal scheduler needs an empty worker"
    );
    ensure!(
        observer.is_none_or(|o| o.supports_absolute_floor()),
        "temporal observer does not support absolute floors"
    );
    #[cfg(feature = "native-green-cue")]
    ensure!(
        !source.green_cue_enabled(),
        "temporal scheduler does not support native green cue"
    );
    let mut ring = Ring::new(total, mode);
    let mut merged: Option<BandMerge> = None;
    let mut folded_total = 0;
    let mut beta_sum = Vec::<f64>::new();
    let mut beta_n = 0;
    worker
        .merge
        .set_temporal_source_range(0..total.min(per_chunk));
    for next in 0..=total {
        let ready = if next < total {
            // Apply identical corrections, but account only on the actual fold.
            let guide_tally = crate::stack::DefectTally::default();
            let guide_defect = defect.map(|(plan, _)| (plan, &guide_tally));
            ensure!(
                worker.prepare_observed(source, next, levels, noise, warps, guide_defect, None)?,
                "temporal source {next} became refused after preflight"
            );
            if let Some(observer) = observer {
                observer.guide(next, &worker.beta);
            }
            let refs: Vec<&[f32]> = worker.planes.iter().map(Vec::as_slice).collect();
            let beta = (!worker.beta.is_empty()).then_some(worker.beta.as_slice());
            let guide = worker.merge.temporal_guide(
                next,
                &refs,
                &worker.luma,
                &worker.var,
                beta,
                &mut worker.fws,
            );
            ring.push(guide)
        } else {
            ring.finish()
        };
        let Some(ready) = ready else {
            continue;
        };
        let index = ready.source_index();
        ensure!(index == folded_total, "temporal center order changed");
        let chunk = index / per_chunk;
        if let Some(observer) = observer {
            observer.ready(index, chunk, ready.is_original(), ready.neighbor_indices());
        }
        if let Some(progress) = progress {
            progress.frame_started(index);
        }
        ensure!(
            worker.prepare_observed(source, index, levels, noise, warps, defect, progress)?,
            "temporal center {index} became refused after preflight"
        );
        let frame_beta = (!worker.beta.is_empty()).then_some(worker.beta.as_slice());
        if let Some(beta) = frame_beta {
            if worker.beta_sum.len() < beta.len() {
                worker.beta_sum.resize(beta.len(), 0.0);
            }
            for (acc, value) in worker.beta_sum.iter_mut().zip(beta) {
                *acc += f64::from(*value);
            }
            worker.beta_n += 1;
        }
        #[cfg(all(test, feature = "native-direct-planes"))]
        source.observe_direct_inputs(index, &worker.planes, &worker.luma, frame_beta)?;
        let refs: Vec<&[f32]> = worker.planes.iter().map(Vec::as_slice).collect();
        let relay = Relay {
            tap: progress
                .map(|p| crate::ui_progress::FrameTap::new(p, index, worker.merge.sizes().len())),
            external: observer,
        };
        worker.merge.add_frame_with_temporal_guide(
            index,
            &refs,
            &worker.luma,
            &worker.var,
            frame_beta,
            &mut worker.fws,
            &ready,
            Some(&relay),
        );
        folded_total += 1;
        if let Some(observer) = observer {
            observer.folded(index, &worker.merge);
        }
        if let Some(progress) = progress {
            progress.frame_finished(index, true);
            progress.live_accumulator(merged.as_ref(), &worker.merge, index);
        }
        if (index + 1) % per_chunk == 0 || index + 1 == total {
            if beta_sum.len() < worker.beta_sum.len() {
                beta_sum.resize(worker.beta_sum.len(), 0.0);
            }
            for (acc, value) in beta_sum.iter_mut().zip(&worker.beta_sum) {
                *acc += value;
            }
            beta_n += worker.beta_n;
            match merged.as_mut() {
                Some(acc) => acc.absorb(&worker.merge),
                None => {
                    let geom = worker.domain.analysis();
                    merged = Some(std::mem::replace(
                        &mut worker.merge,
                        BandMerge::new(geom.width, geom.height, BAND_PLANES, worker.config),
                    ));
                }
            }
            let acc = merged.as_ref().unwrap();
            if let Some(observer) = observer {
                observer.chunk(chunk, acc);
            }
            if let Some(progress) = progress {
                progress.accumulator(acc, index, chunk, total.div_ceil(per_chunk));
            }
            if index + 1 < total {
                worker.reset_chunk();
                let end = (index + 1).saturating_add(per_chunk).min(total);
                worker.merge.set_temporal_source_range(index + 1..end);
            }
        }
    }
    ensure!(
        folded_total == total && ring.retained_guides() == 0,
        "incomplete temporal fold"
    );
    Ok(FoldResult {
        merge: merged.context("no temporal centers folded")?,
        folded_total,
        beta_sum,
        beta_n,
    })
}

pub(super) fn receipt_path(output: &Path) -> PathBuf {
    let mut name = output.as_os_str().to_owned();
    name.push(".temporal-energy.json");
    PathBuf::from(name)
}

pub(super) fn receipt_preflight(output: &Path) -> Result<()> {
    ensure!(
        !receipt_path(output).exists(),
        "temporal receipt already exists; choose a new output path"
    );
    Ok(())
}

fn file_identity(path: &Path) -> Result<serde_json::Value> {
    use sha2::{Digest, Sha256};
    use std::io::Read;
    let mut input = std::fs::File::open(path)
        .with_context(|| format!("opening completed temporal artifact {}", path.display()))?;
    let mut hash = Sha256::new();
    let mut buffer = vec![0u8; 1024 * 1024];
    let mut bytes = 0u64;
    loop {
        let count = input.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        hash.update(&buffer[..count]);
        bytes += count as u64;
    }
    let digest = hash
        .finalize()
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>();
    Ok(serde_json::json!({"path":path,"bytes":bytes,"sha256":digest}))
}

/// Only enabled experimental outputs receive this adjacent process receipt.
/// Writing/hash errors propagate to the command, even if image writing passed.
pub(super) fn write_receipt(
    output: &Path,
    master: Option<&Path>,
    mut process: serde_json::Value,
) -> Result<()> {
    use std::io::Write;
    process["completed_output"] = file_identity(output)?;
    process["completed_linear_master"] = match master {
        Some(path) => file_identity(path)?,
        None => serde_json::Value::Null,
    };
    process["executable"] = file_identity(&std::env::current_exe()?)?;
    process["completion"] = serde_json::json!("images written and hashed");
    let path = receipt_path(output);
    let mut file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&path)
        .with_context(|| format!("creating temporal experiment receipt {}", path.display()))?;
    let mut text = serde_json::to_vec_pretty(&process)?;
    text.push(b'\n');
    file.write_all(&text)
        .with_context(|| format!("writing temporal receipt {}", path.display()))?;
    file.sync_all().context("syncing temporal receipt")?;
    eprintln!("temporal receipt: {}", path.display());
    Ok(())
}
