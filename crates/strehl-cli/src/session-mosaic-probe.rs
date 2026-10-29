//! Known-noise probes of the actual spatial CFA gather and pyramid. There is
//! no private sensor-noise fit. Missing coefficients have zero observations,
//! never an identity-noise substitution.
use crate::session_mapped_sampling::{MappedSamplingDomain, NativeMappedSampler};
use crate::session_sampling::{ProbeConfig, WarpBandTransfer};
use anyhow::{Result, ensure};
use rayon::prelude::*;
use std::collections::BTreeMap;
use std::time::Instant;
use strehl_core::align::{Resampler, Similarity};
use strehl_core::mosaic::MappedPoint;
use strehl_core::noise::Levels;
use strehl_core::optics::OpticalProfile;
use strehl_core::plane::{PlaneGeometry, QuadSource};
use strehl_core::pyramid::{LevelSize, Pyramid, Workspace, level_sizes};

struct Probe {
    geometry: PlaneGeometry,
    pixels: Vec<u16>,
}
impl QuadSource for Probe {
    fn geometry(&self) -> PlaneGeometry {
        self.geometry
    }
    fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
        let w = 2 * self.geometry.width;
        let start = 2 * y * w;
        (
            &self.pixels[start..start + w],
            &self.pixels[start + w..start + 2 * w],
        )
    }
}
fn mix(mut x: u64) -> u64 {
    x = x.wrapping_add(0x9e3779b97f4a7c15);
    x = (x ^ (x >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94d049bb133111eb);
    x ^ (x >> 31)
}

// Follow the production pyramid's complete, clamped dependency footprint.
// Tile-edge replication is measured too; the tile halo later excludes its
// influence from interior output. A zero count is legal only for a band with
// no coverage-valid coefficient, which the merge cannot admit.
fn masks(base: &[bool], sizes: &[LevelSize]) -> Vec<Vec<bool>> {
    let mut gaussian = vec![base.to_vec()];
    for k in 1..sizes.len() {
        let prev = sizes[k - 1];
        let next = sizes[k];
        let mut mask = vec![false; next.pixels()];
        for y in 0..next.height {
            for x in 0..next.width {
                mask[y * next.width + x] = (-2_isize..=2).all(|dy| {
                    (-2_isize..=2).all(|dx| {
                        let sx = (2 * x).saturating_add_signed(dx).min(prev.width - 1);
                        let sy = (2 * y).saturating_add_signed(dy).min(prev.height - 1);
                        gaussian[k - 1][sy * prev.width + sx]
                    })
                });
            }
        }
        gaussian.push(mask);
    }
    (0..sizes.len())
        .map(|k| {
            let mut out = gaussian[k].clone();
            if k + 1 < sizes.len() {
                let fine = sizes[k];
                let coarse = sizes[k + 1];
                for y in 0..fine.height {
                    for x in 0..fine.width {
                        let x0 = x / 2;
                        let y0 = y / 2;
                        let xmin = x0.saturating_sub(usize::from(x % 2 == 0));
                        let ymin = y0.saturating_sub(usize::from(y % 2 == 0));
                        out[y * fine.width + x] &=
                            (ymin..=(y0 + 1).min(coarse.height - 1)).all(|sy| {
                                (xmin..=(x0 + 1).min(coarse.width - 1))
                                    .all(|sx| gaussian[k + 1][sy * coarse.width + sx])
                            });
                    }
                }
            }
            out
        })
        .collect()
}

#[allow(clippy::too_many_arguments)]
pub(super) fn measure<F: Fn([f64; 2]) -> MappedPoint + Sync>(
    source_geometry: PlaneGeometry,
    domain: MappedSamplingDomain,
    mapping: &F,
    placement: Similarity,
    profile: Option<&OpticalProfile>,
    resampler: Resampler,
    config: ProbeConfig,
    budget: usize,
) -> Result<WarpBandTransfer> {
    ensure!(
        (1..=128).contains(&config.realizations) && config.bands <= 12,
        "invalid mapped probe realization count"
    );
    let reserved = reservation_bytes(source_geometry, domain)?;
    ensure!(
        reserved <= budget,
        "mapped probe exceeds reserved workspace"
    );
    let sizes = level_sizes(domain.rect.width, domain.rect.height, config.bands);
    let levels = sizes.len();
    let mut source = Probe {
        geometry: source_geometry,
        pixels: vec![0; source_geometry.pixels() * 4],
    };
    let mut sampler = NativeMappedSampler::new(source_geometry, domain, budget)?;
    let mut pyramid = Pyramid::zeros(&sizes);
    let mut workspace = Workspace::new(&sizes);
    let mut green = vec![0.0; domain.pixels()];
    let mut support = Vec::new();
    let mut counts = vec![0; levels];
    let mut sums: [Vec<f64>; 5] = std::array::from_fn(|_| vec![0.0; levels]);
    for realization in 0..config.realizations {
        let stream = mix(config.seed ^ (realization as u64).wrapping_mul(0xd1342543de82ef95));
        source.pixels.par_iter_mut().enumerate().for_each(|(i, v)| {
            *v = if mix(stream.wrapping_add(i as u64)) & 1 == 0 {
                8160
            } else {
                8224
            }
        });
        let sampled = sampler.gather_with_mapping(
            &source,
            Levels {
                black: 8192.0,
                white: 65535.0,
            },
            mapping,
            placement,
            profile,
            resampler,
        )?;
        if realization == 0 {
            support = masks(&sampled.coverage, &sizes);
            for (k, m) in support.iter().enumerate() {
                counts[k] = m.iter().filter(|&&v| v).count() * config.realizations;
            }
        }
        for (i, g) in green.iter_mut().enumerate() {
            *g = 0.5 * (sampled.planes[1][i] + sampled.planes[3][i]);
        }
        for (c, sum) in sums.iter_mut().enumerate() {
            pyramid.build(
                if c < 4 { &sampled.planes[c] } else { &green },
                &mut workspace,
            );
            for k in 0..levels {
                sum[k] += pyramid
                    .level(k)
                    .iter()
                    .zip(&support[k])
                    .filter(|(_, valid)| **valid)
                    .map(|(&v, _)| f64::from(v).powi(2))
                    .sum::<f64>();
            }
        }
    }
    let beta = |c: usize, k: usize| {
        if counts[k] == 0 {
            0.0
        } else {
            (sums[c][k] / (counts[k] as f64 * 1024.0 * if c == 4 { 0.5 } else { 1.0 })) as f32
        }
    };
    let cfa_beta: [Vec<f32>; 4] =
        std::array::from_fn(|c| (0..levels).map(|k| beta(c, k)).collect());
    let luma_beta = (0..levels).map(|k| beta(4, k)).collect::<Vec<_>>();
    ensure!(
        cfa_beta.iter().chain(std::iter::once(&luma_beta)).all(|v| v
            .iter()
            .enumerate()
            .all(|(k, &v)| v.is_finite() && (v > 0.0 || counts[k] == 0))),
        "invalid mapped noise-transfer measurement"
    );
    let max_color_beta = (0..levels)
        .map(|k| cfa_beta.iter().map(|v| v[k]).fold(0.0, f32::max))
        .collect();
    Ok(WarpBandTransfer {
        cfa_beta,
        luma_beta,
        max_color_beta,
        samples_per_band: counts,
        realizations: config.realizations,
        seed: config.seed,
    })
}

pub(super) fn reservation_bytes(
    source: PlaneGeometry,
    domain: MappedSamplingDomain,
) -> Result<usize> {
    domain.validate()?;
    source
        .width
        .checked_mul(source.height)
        .and_then(|n| n.checked_mul(16))
        .and_then(|n| {
            domain
                .pixels()
                .checked_mul(64)
                .and_then(|m| n.checked_add(m))
        })
        .ok_or_else(|| anyhow::anyhow!("mapped probe reservation overflow"))
}
pub(super) struct Job {
    pub index: usize,
    pub pass: usize,
    pub placement: Similarity,
    pub profile: Option<&'static OpticalProfile>,
    pub resampler: Resampler,
}
pub(super) struct Receipt {
    pub transfer: WarpBandTransfer,
    pub seconds: f64,
}
pub(super) struct Prefetched {
    pub by_index: BTreeMap<usize, Receipt>,
    pub lanes: usize,
    pub reserved_bytes: usize,
    pub per_probe_bytes: usize,
    pub result_bytes: usize,
    pub elapsed_seconds: f64,
}

/// A canonical domain makes the estimator independent of chosen output tiles.
/// Complete these bounded batches before allocating the final output planes.
#[allow(clippy::too_many_arguments)]
pub(super) fn prefetch<F: Fn(usize, [f64; 2]) -> MappedPoint + Sync>(
    jobs: &[Job],
    source: PlaneGeometry,
    domain: MappedSamplingDomain,
    mapping: &F,
    config: ProbeConfig,
    budget: usize,
    workers: usize,
) -> Result<Prefetched> {
    ensure!(
        workers > 0 && !jobs.is_empty(),
        "mapped transfer prefetch needs workers and placed sources"
    );
    ensure!(
        domain.rect.x == 0
            && domain.rect.y == 0
            && domain.rect.width == domain.canvas.width
            && domain.rect.height == domain.canvas.height,
        "mapped transfer probe must use the canonical full canvas"
    );
    let result_bytes = jobs
        .len()
        .checked_mul(2048)
        .ok_or_else(|| anyhow::anyhow!("mapped transfer receipt reservation overflow"))?;
    let per_probe_bytes = reservation_bytes(source, domain)?;
    ensure!(per_probe_bytes > 0, "mapped probe has empty source/domain");
    let available = budget
        .checked_sub(result_bytes)
        .ok_or_else(|| anyhow::anyhow!("mapped transfer receipts exceed memory budget"))?;
    let lanes = (available / per_probe_bytes)
        .min(4)
        .min((workers / 4).max(1))
        .min(jobs.len());
    ensure!(
        lanes > 0,
        "one canonical mosaic transfer probe cannot fit; increase memory limit"
    );
    let reserved_bytes = lanes * per_probe_bytes + result_bytes;
    let started = Instant::now();
    let mut by_index = BTreeMap::new();
    for (batch_index, batch) in jobs.chunks(lanes).enumerate() {
        let results = batch
            .par_iter()
            .map(|job| -> Result<_> {
                let start = Instant::now();
                let transfer = measure(
                    source,
                    domain,
                    &|point| mapping(job.pass, point),
                    job.placement,
                    job.profile,
                    job.resampler,
                    config,
                    per_probe_bytes,
                )?;
                Ok((
                    job.index,
                    Receipt {
                        transfer,
                        seconds: start.elapsed().as_secs_f64(),
                    },
                ))
            })
            .collect::<Result<Vec<_>>>()?;
        for (index, receipt) in results {
            ensure!(
                by_index.insert(index, receipt).is_none(),
                "duplicate source in mapped transfer prefetch"
            );
        }
        if batch_index % 10 == 0 || by_index.len() == jobs.len() {
            eprintln!(
                "mosaic canonical transfer {}/{} sources, {} lanes",
                by_index.len(),
                jobs.len(),
                lanes
            );
        }
    }
    Ok(Prefetched {
        by_index,
        lanes,
        reserved_bytes,
        per_probe_bytes,
        result_bytes,
        elapsed_seconds: started.elapsed().as_secs_f64(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use strehl_core::mosaic::{MosaicCanvas, PixelRect};
    #[test]
    fn canonical_prefetch_matches_scalar_bits_across_lane_counts_and_refuses_budget_or_subtile() {
        let g = PlaneGeometry {
            width: 96,
            height: 80,
        };
        let d = MappedSamplingDomain {
            canvas: MosaicCanvas {
                origin: [-3, 2],
                width: g.width,
                height: g.height,
            },
            rect: PixelRect {
                x: 0,
                y: 0,
                width: g.width,
                height: g.height,
            },
        };
        let jobs: Vec<_> = (0..4)
            .map(|index| Job {
                index,
                pass: index,
                placement: Similarity::IDENTITY,
                profile: None,
                resampler: Resampler::Bilinear,
            })
            .collect();
        let mapping = |pass: usize, p: [f64; 2]| MappedPoint::Supported {
            source: [
                p[0] + 3.0 + pass as f64 * 0.25,
                p[1] - 2.0 + pass as f64 * 0.25,
            ],
            cell: 0,
        };
        let cfg = ProbeConfig {
            bands: 2,
            realizations: 2,
            ..ProbeConfig::default()
        };
        let one = prefetch(&jobs, g, d, &mapping, cfg, 32 << 20, 4).unwrap();
        let many = prefetch(&jobs, g, d, &mapping, cfg, 32 << 20, 16).unwrap();
        assert_eq!(one.lanes, 1);
        assert_eq!(many.lanes, 4);
        for index in 0..4 {
            let a = &one.by_index[&index].transfer;
            let b = &many.by_index[&index].transfer;
            assert_eq!(a.samples_per_band, b.samples_per_band);
            assert_eq!(a.cfa_beta, b.cfa_beta);
            assert_eq!(a.luma_beta, b.luma_beta);
            assert_eq!(a.max_color_beta, b.max_color_beta);
        }
        let need = reservation_bytes(g, d).unwrap() + jobs.len() * 2048;
        assert!(prefetch(&jobs, g, d, &mapping, cfg, need - 1, 16).is_err());
        let mut subtile = d;
        subtile.rect.width -= 1;
        assert!(prefetch(&jobs, g, subtile, &mapping, cfg, 32 << 20, 16).is_err());
    }
    #[test]
    fn flat_mapped_operator_rejects_identity_beta_at_half_phase_and_keeps_holes() {
        let g = PlaneGeometry {
            width: 96,
            height: 80,
        };
        let d = MappedSamplingDomain {
            canvas: MosaicCanvas {
                origin: [0, 0],
                width: g.width,
                height: g.height,
            },
            rect: PixelRect {
                x: 0,
                y: 0,
                width: g.width,
                height: g.height,
            },
        };
        for (shift, expected) in [(0.0, 1.0), (0.5, 0.25)] {
            let mapping = |p: [f64; 2]| {
                if p[0] < 15.0 {
                    MappedPoint::Uncovered
                } else {
                    MappedPoint::Supported {
                        source: [p[0] + shift, p[1] + shift],
                        cell: 0,
                    }
                }
            };
            let result = measure(
                g,
                d,
                &mapping,
                Similarity::IDENTITY,
                None,
                Resampler::Bilinear,
                ProbeConfig {
                    bands: 0,
                    realizations: 8,
                    seed: 701,
                    min_samples_per_band: 1,
                },
                8 << 20,
            )
            .unwrap();
            assert!((result.luma_beta[0] - expected).abs() < 0.02);
            assert!(result.samples_per_band[0] < d.pixels() * 8);
            if shift > 0.0 {
                assert!((result.luma_beta[0] - 1.0).abs() > 0.6);
            }
        }
        let result = measure(
            g,
            d,
            &|_| MappedPoint::Uncovered,
            Similarity::IDENTITY,
            None,
            Resampler::Bilinear,
            ProbeConfig {
                bands: 3,
                ..ProbeConfig::default()
            },
            8 << 20,
        )
        .unwrap();
        assert!(result.samples_per_band.iter().all(|&n| n == 0));
        assert!(result.luma_beta.iter().all(|&v| v == 0.0));
    }
}
