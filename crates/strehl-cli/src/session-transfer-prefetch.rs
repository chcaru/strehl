//! Bounded independent transfer-probe prefetch before fusion allocation.
//!
//! Only small measured operator receipts are retained. Each concurrent job owns
//! its original synthetic-u16 probe and existing sampler/pyramid workspace; no
//! RAW acquisition, aligned volume or additional image cache is introduced.
use super::transfer_cache;
use crate::session_sampling::{ProbeConfig, ProbeMemoryEstimate, SamplingDomain, WarpBandTransfer};
use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;
use std::time::Instant;
use strehl_core::align::{Resampler, Similarity};
use strehl_core::optics::{Channel, OpticalProfile};
use strehl_core::pyramid::level_sizes;

const MAX_LANES: usize = 4;
// Vector headers, BTreeMap nodes, validation bookkeeping and one small pending
// result per job. Cache I/O, allocator and thread overhead are covered by the
// caller's separate phase allowance (the consumer reserves at least512MiB).
const RESULT_OVERHEAD_BYTES: usize = 4096;

#[derive(Clone, Copy, Debug)]
pub(super) struct TransferJob {
    pub index: usize,
    pub placement: Similarity,
    pub profile: Option<&'static OpticalProfile>,
}

#[derive(Debug)]
pub(super) struct TransferReceipt {
    pub transfer: WarpBandTransfer,
    /// Actual flag returned by the first measure call for THIS job. Never
    /// reconstructed by re-reading the now-populated cache afterward.
    pub cache_hit: bool,
    pub seconds: f64,
}

#[derive(Debug)]
pub(super) struct TransferBatch {
    pub by_index: BTreeMap<usize, TransferReceipt>,
    /// Planned concurrency cap. Equal-placement jobs are additionally serialized
    /// because they may share a cache entry, including corrupt-entry repair.
    pub lanes: usize,
    pub per_probe_bytes: usize,
    pub retained_result_bytes: usize,
    pub reserved_bytes: usize,
    pub elapsed_seconds: f64,
}

#[derive(Clone, Copy, Debug)]
struct Reservation {
    lanes: usize,
    per_probe_bytes: usize,
    retained_result_bytes: usize,
    reserved_bytes: usize,
}

fn reserve(
    domain: SamplingDomain,
    config: ProbeConfig,
    jobs: usize,
    available_phase_bytes: usize,
    workers: usize,
) -> Result<Reservation> {
    ensure!(jobs > 0, "transfer prefetch requires at least one job");
    ensure!(
        workers > 0,
        "transfer prefetch requires at least one worker"
    );
    ensure!(
        available_phase_bytes <= isize::MAX as usize,
        "transfer phase budget exceeds the addressable size"
    );
    ensure!(
        (1..=128).contains(&config.realizations) && config.min_samples_per_band > 0,
        "invalid transfer probe configuration"
    );
    let per_probe_bytes = ProbeMemoryEstimate::estimate(domain, config.bands)?.peak_bytes;
    let levels = level_sizes(domain.width, domain.height, config.bands).len();
    let numeric_result_bytes = levels
        .checked_mul(6 * std::mem::size_of::<f32>() + std::mem::size_of::<usize>())
        .context("transfer result size overflows")?;
    let retained_result_bytes = numeric_result_bytes
        .checked_add(RESULT_OVERHEAD_BYTES)
        .and_then(|n| n.checked_mul(jobs))
        .context("retained transfer result budget overflows")?;
    let free = available_phase_bytes
        .checked_sub(retained_result_bytes)
        .context("phase budget cannot retain transfer receipts")?;
    let lanes = (free / per_probe_bytes)
        .min(MAX_LANES)
        .min(workers)
        .min(jobs);
    ensure!(
        lanes > 0,
        "transfer phase cannot fit one complete probe: needs {} probe bytes plus {} retained-result bytes, available {}",
        per_probe_bytes,
        retained_result_bytes,
        available_phase_bytes
    );
    let reserved_bytes = per_probe_bytes
        .checked_mul(lanes)
        .and_then(|n| n.checked_add(retained_result_bytes))
        .context("transfer reservation overflows")?;
    ensure!(
        reserved_bytes <= available_phase_bytes,
        "transfer reservation exceeds phase budget"
    );
    Ok(Reservation {
        lanes,
        per_probe_bytes,
        retained_result_bytes,
        reserved_bytes,
    })
}

fn placement_bits(placement: Similarity) -> [u64; 4] {
    [
        placement.a.re.to_bits(),
        placement.a.im.to_bits(),
        placement.b.re.to_bits(),
        placement.b.im.to_bits(),
    ]
}

fn validate_job(job: &TransferJob) -> Result<()> {
    for channel in [Channel::Red, Channel::Green, Channel::Blue] {
        let placement = OpticalProfile::compose(job.profile, channel, job.placement);
        ensure!(
            [
                placement.a.re,
                placement.a.im,
                placement.b.re,
                placement.b.im
            ]
            .into_iter()
            .all(f64::is_finite)
                && placement.a.norm_sq().is_finite()
                && placement.a.norm_sq() > 0.0,
            "transfer job {} has a nonfinite or singular placement",
            job.index
        );
    }
    Ok(())
}

/// The caller supplies the verified source-cache root outside all captures and
/// runs this inside its configured Rayon pool. available_phase_bytes excludes
/// pinned source-cache storage and the caller's allocator/cache-I/O/thread
/// allowance. Call BEFORE allocating the fusion workspaces.
///
/// Batches execute sequentially and contain at most four jobs. Parallelizing
/// all jobs directly would not be a memory bound: nested Rayon work stealing
/// can activate additional outer jobs while an inner pyramid task is waiting.
/// Here no job outside the current bounded batch is ever submitted.
///
/// Errors join the current batch before returning. Completed cache entries may
/// remain reusable; no partial TransferBatch is returned and fusion cannot start
/// with missing results. Each probe preserves the existing exact algorithm.
pub(super) fn compute(
    cache_root: &Path,
    domain: SamplingDomain,
    resampler: Resampler,
    config: ProbeConfig,
    jobs: &[TransferJob],
    available_phase_bytes: usize,
    workers: usize,
) -> Result<TransferBatch> {
    let started = Instant::now();
    ensure!(
        resampler != Resampler::ClampedCatmullRom,
        "nonlinear resampler cannot prefetch a linear noise transfer"
    );
    let reservation = reserve(domain, config, jobs.len(), available_phase_bytes, workers)?;
    let mut seen = BTreeSet::new();
    for job in jobs {
        ensure!(
            seen.insert(job.index),
            "duplicate transfer frame index {}",
            job.index
        );
        validate_job(job)?;
    }
    drop(seen);
    ensure!(
        cache_root.is_dir(),
        "transfer cache root must already exist"
    );
    let mut by_index = BTreeMap::new();
    let mut begin = 0;
    while begin < jobs.len() {
        let mut end = begin + 1;
        while end < jobs.len() && end - begin < reservation.lanes {
            let bits = placement_bits(jobs[end].placement);
            // Same placement is a conservative superset of same cache key.
            // Keep such jobs apart even if their profiles differ. This avoids
            // concurrent corrupt-entry removal in the unchanged cache helper.
            if jobs[begin..end]
                .iter()
                .any(|job| placement_bits(job.placement) == bits)
            {
                break;
            }
            end += 1;
        }
        let completed: Vec<Result<(usize, TransferReceipt)>> = jobs[begin..end]
            .par_iter()
            .map(|job| {
                let started = Instant::now();
                let (transfer, cache_hit) = transfer_cache::measure(
                    cache_root,
                    domain,
                    job.placement,
                    job.profile,
                    resampler,
                    config,
                )
                .with_context(|| format!("prefetching transfer for frame {}", job.index))?;
                Ok((
                    job.index,
                    TransferReceipt {
                        transfer,
                        cache_hit,
                        seconds: started.elapsed().as_secs_f64(),
                    },
                ))
            })
            .collect();
        for result in completed {
            let (index, receipt) = result?;
            by_index.insert(index, receipt);
        }
        begin = end;
    }
    Ok(TransferBatch {
        by_index,
        lanes: reservation.lanes,
        per_probe_bytes: reservation.per_probe_bytes,
        retained_result_bytes: reservation.retained_result_bytes,
        reserved_bytes: reservation.reserved_bytes,
        elapsed_seconds: started.elapsed().as_secs_f64(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};
    use strehl_core::align::Cx;
    use strehl_core::optics::A7C2_FE100GM_2XTC_X4CPL_RADIAL;
    use strehl_core::plane::PlaneGeometry;

    static NEXT_TEST: AtomicU64 = AtomicU64::new(0);
    struct TestRoot(PathBuf);
    impl TestRoot {
        fn new() -> Self {
            let path = std::env::var_os("STREHL_TEST_TMP")
                .map(PathBuf::from)
                .unwrap_or_else(std::env::temp_dir)
                .join(format!(
                    "strehl-transfer-prefetch-{}-{}",
                    std::process::id(),
                    NEXT_TEST.fetch_add(1, Ordering::Relaxed)
                ));
            std::fs::create_dir_all(&path).unwrap();
            Self(path)
        }
    }
    impl Drop for TestRoot {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }
    fn domain() -> SamplingDomain {
        SamplingDomain::full(PlaneGeometry {
            width: 96,
            height: 80,
        })
    }
    fn config() -> ProbeConfig {
        ProbeConfig {
            bands: 2,
            realizations: 2,
            min_samples_per_band: 16,
            seed: 94571,
        }
    }
    fn jobs() -> Vec<TransferJob> {
        (0..7)
            .map(|i| TransferJob {
                index: 40 + i * 3,
                placement: Similarity {
                    a: Cx::new(1.0 + i as f64 * 0.0007, i as f64 * 0.0003),
                    b: Cx::new(i as f64 * 0.125, -(i as f64) * 0.07),
                },
                profile: if i % 2 == 0 {
                    None
                } else {
                    Some(&A7C2_FE100GM_2XTC_X4CPL_RADIAL)
                },
            })
            .collect()
    }
    fn signature(batch: &TransferBatch) -> Vec<u64> {
        let mut out = Vec::new();
        for (&index, receipt) in &batch.by_index {
            out.push(index as u64);
            for beta in receipt.transfer.cfa_beta.iter().chain([
                &receipt.transfer.luma_beta,
                &receipt.transfer.max_color_beta,
            ]) {
                out.extend(beta.iter().map(|v| u64::from(v.to_bits())));
            }
            out.extend(receipt.transfer.samples_per_band.iter().map(|&v| v as u64));
            out.extend([receipt.transfer.realizations as u64, receipt.transfer.seed]);
        }
        out
    }

    #[test]
    fn transfer_prefetch_one_and_four_lanes_preserve_bits_and_original_cache_hits() {
        let serial_root = TestRoot::new();
        let parallel_root = TestRoot::new();
        let jobs = jobs();
        let serial = rayon::ThreadPoolBuilder::new()
            .num_threads(1)
            .build()
            .unwrap();
        let parallel = rayon::ThreadPoolBuilder::new()
            .num_threads(4)
            .build()
            .unwrap();
        let a = serial
            .install(|| {
                compute(
                    &serial_root.0,
                    domain(),
                    Resampler::CatmullRom,
                    config(),
                    &jobs,
                    128 << 20,
                    1,
                )
            })
            .unwrap();
        let b = parallel
            .install(|| {
                compute(
                    &parallel_root.0,
                    domain(),
                    Resampler::CatmullRom,
                    config(),
                    &jobs,
                    128 << 20,
                    4,
                )
            })
            .unwrap();
        assert_eq!(a.lanes, 1);
        assert_eq!(b.lanes, 4);
        assert!(
            a.by_index
                .values()
                .chain(b.by_index.values())
                .all(|r| !r.cache_hit && r.seconds >= 0.0)
        );
        assert_eq!(signature(&a), signature(&b));
        assert_eq!(
            b.reserved_bytes,
            b.retained_result_bytes + b.lanes * b.per_probe_bytes
        );
        assert!(b.elapsed_seconds >= 0.0);
        let mut extended = jobs.clone();
        extended.push(TransferJob {
            index: 99,
            placement: Similarity {
                a: Cx::ONE,
                b: Cx::new(0.31, 0.41),
            },
            profile: None,
        });
        let c = parallel
            .install(|| {
                compute(
                    &parallel_root.0,
                    domain(),
                    Resampler::CatmullRom,
                    config(),
                    &extended,
                    128 << 20,
                    4,
                )
            })
            .unwrap();
        for job in jobs {
            assert!(c.by_index[&job.index].cache_hit);
        }
        assert!(!c.by_index[&99].cache_hit);
        for (&index, receipt) in &b.by_index {
            let check = &c.by_index[&index].transfer;
            assert_eq!(receipt.transfer.cfa_beta, check.cfa_beta);
            assert_eq!(receipt.transfer.luma_beta, check.luma_beta);
        }
    }

    #[test]
    fn transfer_prefetch_budget_and_overflow_are_checked_before_work() {
        let d = domain();
        let c = config();
        let planned = reserve(d, c, 7, 128 << 20, 32).unwrap();
        assert_eq!(planned.lanes, 4);
        let one = planned.retained_result_bytes + planned.per_probe_bytes;
        assert_eq!(reserve(d, c, 7, one, 32).unwrap().lanes, 1);
        assert!(reserve(d, c, 7, one - 1, 32).is_err());
        assert_eq!(reserve(d, c, 7, 128 << 20, 2).unwrap().lanes, 2);
        assert_eq!(reserve(d, c, 1, 128 << 20, 32).unwrap().lanes, 1);
        assert!(reserve(d, c, 7, 128 << 20, 0).is_err());
        assert!(reserve(d, c, 0, 128 << 20, 4).is_err());
        assert!(reserve(d, c, usize::MAX, isize::MAX as usize, 4).is_err());
        assert!(reserve(d, c, 1, usize::MAX, 4).is_err());
        let impossible = SamplingDomain::full(PlaneGeometry {
            width: usize::MAX,
            height: 2,
        });
        assert!(reserve(impossible, c, 1, 128 << 20, 4).is_err());
        let root = TestRoot::new();
        let jobs = jobs();
        assert!(compute(&root.0, d, Resampler::CatmullRom, c, &jobs, one - 1, 4).is_err());
        assert_eq!(std::fs::read_dir(&root.0).unwrap().count(), 0);
    }

    #[test]
    fn transfer_prefetch_rejects_duplicate_indices_and_bad_jobs_before_cache_access() {
        let root = TestRoot::new();
        let mut jobs = jobs();
        jobs[1].index = jobs[0].index;
        assert!(
            compute(
                &root.0,
                domain(),
                Resampler::Bilinear,
                config(),
                &jobs,
                128 << 20,
                4
            )
            .is_err()
        );
        jobs[1].index = 43;
        jobs[1].placement.a = Cx::ZERO;
        assert!(
            compute(
                &root.0,
                domain(),
                Resampler::Bilinear,
                config(),
                &jobs,
                128 << 20,
                4
            )
            .is_err()
        );
        assert_eq!(std::fs::read_dir(&root.0).unwrap().count(), 0);
    }

    #[test]
    fn transfer_prefetch_serializes_identical_operator_repairs_and_retains_hits() {
        let root = TestRoot::new();
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(4)
            .build()
            .unwrap();
        let jobs: Vec<_> = (0..4)
            .map(|index| TransferJob {
                index,
                placement: Similarity::IDENTITY,
                profile: None,
            })
            .collect();
        let first = pool
            .install(|| {
                compute(
                    &root.0,
                    domain(),
                    Resampler::Bilinear,
                    config(),
                    &jobs,
                    128 << 20,
                    4,
                )
            })
            .unwrap();
        assert!(!first.by_index[&0].cache_hit);
        assert!((1..4).all(|i| first.by_index[&i].cache_hit));
        let entry = std::fs::read_dir(&root.0)
            .unwrap()
            .next()
            .unwrap()
            .unwrap()
            .path();
        std::fs::write(entry, b"corrupt derived receipt").unwrap();
        let repaired = pool
            .install(|| {
                compute(
                    &root.0,
                    domain(),
                    Resampler::Bilinear,
                    config(),
                    &jobs,
                    128 << 20,
                    4,
                )
            })
            .unwrap();
        assert!(!repaired.by_index[&0].cache_hit);
        assert!((1..4).all(|i| repaired.by_index[&i].cache_hit));
        assert_eq!(signature(&first), signature(&repaired));
    }
}
