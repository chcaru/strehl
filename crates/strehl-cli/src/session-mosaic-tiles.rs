//! Globally phased tiled reconstruction and explicit cross-view admission.
use super::*;
use crate::session_mapped_sampling::{
    MappedSamplingDomain, NativeMappedSampler, mapped_sampling_bytes,
};
use crate::session_mosaic_geometry::MosaicGeometry;
use crate::session_sampling::ProbeConfig;
use std::io::{BufWriter, Write};
#[cfg(test)]
use strehl_core::mosaic::Visibility;
use strehl_core::mosaic::{
    BackwardMesh, IndexLimits, MappedPoint, MeshValidation, MosaicCanvas, MosaicTilePlan, PixelRect,
};
use strehl_core::plane::PlaneGeometry;
use strehl_core::pyramid::level_sizes;
use strehl_core::pyramid::session_fusion::{
    GroupMode, GroupPolicy, GroupWorkspace, PreparedSource, SessionMerge, SourceKey,
    workspace_bytes,
};

pub(super) struct ViewMap {
    fitted: BackwardMesh,
    source: PlaneGeometry,
}
impl ViewMap {
    fn new(geometry: &MosaicGeometry, pass: usize) -> Result<Self> {
        let limits = IndexLimits {
            bin_side: 64,
            max_bins: 1_000_000,
            max_entries: 10_000_000,
        };
        Ok(Self {
            fitted: BackwardMesh::new(&geometry.meshes[pass], MeshValidation::default(), limits)?,
            source: geometry.meshes[pass].source,
        })
    }
    fn qualified(&self, p: [f64; 2]) -> Option<[f64; 2]> {
        match self.fitted.map(p) {
            MappedPoint::Supported { source, cell } if self.fitted.join_supported(cell, source) => {
                Some(source)
            }
            _ => None,
        }
    }
    fn map(&self, p: [f64; 2]) -> MappedPoint {
        // Positive SingleView cells retain the same continuous regularized
        // placement, without gaining a cross-view geometry certificate. Never
        // switch abruptly to the global seed at a failed/qualification edge:
        // rejected cells stay alpha-invalid through complete filter support.
        self.fitted.map(p)
    }
    fn properties(&self, p: [f64; 2]) -> Option<(bool, f32)> {
        let MappedPoint::Supported { source, .. } = self.map(p) else {
            return None;
        };
        let qualified = [[-0.25, -0.25], [0.25, -0.25], [-0.25, 0.25], [0.25, 0.25]]
            .into_iter()
            .all(|d| self.qualified([p[0] + d[0], p[1] + d[1]]).is_some());
        let margin = source[0]
            .min(source[1])
            .min(self.source.width as f64 - 1.0 - source[0])
            .min(self.source.height as f64 - 1.0 - source[1])
            .max(0.0) as f32;
        Some((qualified, margin))
    }
}

pub(super) struct Output {
    pub planes: [Vec<f32>; 4],
    pub valid: Vec<bool>,
    pub owner: Vec<u16>,
    pub join: Vec<u8>,
    pub report: Value,
}

#[derive(Clone, Copy, Default)]
struct Composite {
    value: [f32; 4],
    variance: [f32; 4],
    owner_value: [f32; 4],
    owner_variance: [f32; 4],
    weight: f32,
    margin: f32,
    owner: u16,
    qualified: bool,
    unmerged: bool,
    blended: bool,
    count: u16,
}
impl Composite {
    fn add(
        &mut self,
        value: [f32; 4],
        variance: [f32; 4],
        qualified: bool,
        margin: f32,
        pass: usize,
        sigma: f32,
    ) {
        let weight = margin.clamp(1.0, 256.0);
        if self.count == 0 {
            *self = Self {
                value,
                variance,
                owner_value: value,
                owner_variance: variance,
                weight,
                margin,
                owner: (pass + 1) as u16,
                qualified,
                count: 1,
                ..Self::default()
            };
            return;
        }
        let compatible = self.qualified
            && qualified
            && !self.unmerged
            && (0..4).all(|c| {
                (self.value[c] - value[c]).powi(2)
                    <= sigma * sigma * (self.variance[c] + variance[c]).max(1e-20)
            });
        if compatible {
            let total = self.weight + weight;
            for c in 0..4 {
                self.value[c] = (self.value[c] * self.weight + value[c] * weight) / total;
                self.variance[c] = self.variance[c].max(variance[c]);
            }
            self.weight = total;
            self.blended = true;
            if margin > self.margin {
                self.margin = margin;
                self.owner = (pass + 1) as u16;
                self.owner_value = value;
                self.owner_variance = variance;
            }
        } else {
            self.unmerged = true;
            self.blended = false;
            // A deterministic maximum-interior rule, not a primary or a
            // claim that conflicting observations describe the same surface.
            if margin > self.margin {
                self.value = value;
                self.variance = variance;
                self.margin = margin;
                self.owner = (pass + 1) as u16;
                self.qualified = qualified;
                self.weight = weight;
                self.owner_value = value;
                self.owner_variance = variance;
            }
            self.value = self.owner_value;
            self.variance = self.owner_variance;
            self.weight = self.margin.clamp(1.0, 256.0);
        }
        self.count = self.count.saturating_add(1);
    }
    fn join(self) -> u8 {
        if self.count == 0 {
            0
        } else if self.unmerged {
            3
        } else if self.blended {
            2
        } else {
            1
        }
    }
}

fn plan(
    args: &StackArgs,
    geometry: &MosaicGeometry,
    cache_budget: usize,
    retained: usize,
) -> Result<(MosaicTilePlan, usize, usize)> {
    let cfg = args.merge_config()?;
    let canvas = geometry.canvas;
    let policy = GroupPolicy {
        mode: GroupMode::Combine,
        primary: None,
        agreement_sigma: args.agreement_sigma,
    };
    plan_domain(
        canvas,
        geometry.meshes[0].source,
        cfg,
        policy,
        args.resources.config()?.memory_limit_bytes,
        cache_budget,
        retained,
    )
}
#[allow(clippy::too_many_arguments)]
fn plan_domain(
    canvas: MosaicCanvas,
    source: PlaneGeometry,
    cfg: strehl_core::pyramid::MergeConfig,
    policy: GroupPolicy,
    limit: usize,
    cache_budget: usize,
    retained: usize,
) -> Result<(MosaicTilePlan, usize, usize)> {
    let levels = level_sizes(canvas.width, canvas.height, cfg.bands).len() - 1;
    let phase = 1_usize << levels;
    let halo = 8 * phase;
    let output = canvas
        .width
        .checked_mul(canvas.height)
        .and_then(|n| n.checked_mul(256))
        .context("mosaic development reservation overflow")?;
    let fixed = output
        .checked_add(cache_budget)
        .and_then(|n| n.checked_add(source.pixels().checked_mul(32)?))
        .and_then(|n| n.checked_add(retained))
        .and_then(|n| n.checked_add(512 << 20))
        .context("mosaic fixed reservation overflow")?;
    ensure!(
        fixed < limit,
        "mosaic output/decode reservation needs {:.2} GiB before tile work",
        fixed as f64 / (1_u64 << 30) as f64
    );
    let largest = canvas.width.max(canvas.height);
    let mut candidates = vec![largest];
    candidates.extend(
        [8192, 4096, 2048, 1024, 512, 256, 128]
            .into_iter()
            .filter(|&side| side < largest),
    );
    for side in candidates {
        let plan = MosaicTilePlan::new(
            canvas,
            side,
            levels as u32,
            halo,
            canvas.width * canvas.height,
            100_000,
        )?;
        let mut maximum = 0;
        for tile in &plan.tiles {
            let domain = MappedSamplingDomain {
                canvas,
                rect: tile.work,
            };
            let n = domain.pixels();
            let workspace = workspace_bytes(tile.work.width, tile.work.height, cfg, policy)?;
            let work = workspace
                .checked_add(mapped_sampling_bytes(source, domain)?)
                .and_then(|x| n.checked_mul(128).and_then(|y| x.checked_add(y)))
                .context("mosaic tile reservation overflow")?;
            maximum = maximum.max(work);
        }
        if fixed.checked_add(maximum).is_some_and(|n| n <= limit) {
            return Ok((plan, fixed + maximum, maximum));
        }
    }
    anyhow::bail!(
        "mosaic tile/filter dependencies exceed memory budget; increase --memory-limit-gib"
    )
}

#[allow(clippy::too_many_arguments)]
pub(super) fn render(
    args: &StackArgs,
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    maps: &[WarpMap],
    cache: &mut SourceCache,
    calibrations: &[Calibration],
    geometry: &MosaicGeometry,
    destination: &Path,
    retained: usize,
) -> Result<Output> {
    ensure!(
        session.passes.len() < u16::MAX as usize,
        "mosaic owner map pass limit exceeded"
    );
    let cfg = args.merge_config()?;
    let policy = GroupPolicy {
        mode: GroupMode::Combine,
        primary: None,
        agreement_sigma: args.agreement_sigma,
    };
    let canvas = geometry.canvas;
    let source_geometry = geometry.meshes[0].source;
    let n = canvas.width * canvas.height;
    let views = (0..session.passes.len())
        .map(|p| ViewMap::new(geometry, p))
        .collect::<Result<Vec<_>>>()?;
    let progress = crate::ui_progress::Progress::new(session.len());
    progress.stage("merge");
    let started = Instant::now();
    let jobs: Vec<_> = session
        .frames
        .iter()
        .filter_map(|frame| {
            maps[frame.pass_index].warps()[frame.global_index]
                .placed()
                .map(|placement| super::probe::Job {
                    index: frame.global_index,
                    pass: frame.pass_index,
                    placement,
                    profile: calibrations[frame.pass_index].profile,
                    resampler: maps[frame.pass_index].resampler(),
                })
        })
        .collect();
    let planned_results = jobs
        .len()
        .checked_mul(2048)
        .context("mosaic transfer receipt reservation overflow")?;
    let (plan, tile_reservation, tile_budget) = plan(
        args,
        geometry,
        cache.budget_bytes(),
        retained
            .checked_add(planned_results)
            .context("mosaic retained receipt reservation overflow")?,
    )?;
    let phase_overhead = cache
        .budget_bytes()
        .checked_add(retained)
        .and_then(|n| n.checked_add(source_geometry.pixels().checked_mul(32)?))
        .and_then(|n| n.checked_add(512 << 20))
        .context("mosaic probe phase reservation overflow")?;
    let phase_budget = args
        .resources
        .config()?
        .memory_limit_bytes
        .checked_sub(phase_overhead)
        .context("no memory for canonical mosaic probe phase")?;
    let canonical_domain = MappedSamplingDomain {
        canvas,
        rect: PixelRect {
            x: 0,
            y: 0,
            width: canvas.width,
            height: canvas.height,
        },
    };
    let transfers = super::probe::prefetch(
        &jobs,
        source_geometry,
        canonical_domain,
        &|pass, point| views[pass].map(point),
        ProbeConfig {
            bands: cfg.bands,
            min_samples_per_band: 1,
            ..ProbeConfig::default()
        },
        phase_budget,
        args.resources.threads,
    )?;
    ensure!(
        transfers.result_bytes == planned_results,
        "mosaic transfer reservation changed"
    );
    let reservation = tile_reservation.max(phase_overhead + transfers.reserved_bytes);
    let probes = transfers.by_index.len();
    // Probe scratch is gone before final output; only scalar receipts remain.
    let mut output = Output {
        planes: std::array::from_fn(|_| vec![0.0; n]),
        valid: vec![false; n],
        owner: vec![0; n],
        join: vec![0; n],
        report: json!({}),
    };
    let receipt_file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(destination.join("mosaic-tile-sources.jsonl"))?;
    let mut receipts = BufWriter::new(receipt_file);
    let mut tile_reports = Vec::new();
    for (tile_index, tile) in plan.tiles.iter().enumerate() {
        let tile_started = Instant::now();
        let domain = MappedSamplingDomain {
            canvas,
            rect: tile.work,
        };
        let mut composite = vec![Composite::default(); tile.core.width * tile.core.height];
        eprintln!(
            "mosaic tile {}/{}: core {},{} {}x{}, work {},{} {}x{} quad pixels",
            tile_index + 1,
            plan.tiles.len(),
            tile.core.x,
            tile.core.y,
            tile.core.width,
            tile.core.height,
            tile.work.x,
            tile.work.y,
            tile.work.width,
            tile.work.height
        );
        let mut pass_reports = Vec::new();
        for pass in 0..session.passes.len() {
            let view = &views[pass];
            let calibration = &calibrations[pass];
            let gain = (calibrations[0].shutter / calibration.shutter) as f32;
            let mut sampler = NativeMappedSampler::new(view.source, domain, tile_budget)?;
            let mut prepared = PreparedSource::new(tile.work.width, tile.work.height, cfg)?;
            let mut group = GroupWorkspace::new(tile.work.width, tile.work.height, cfg, policy)?;
            let mut merge = SessionMerge::new(tile.work.width, tile.work.height, cfg)?;
            let mut sources = 0;
            for index in session.passes[pass].global_range.clone() {
                let Some(placement) = maps[pass].warps()[index].placed() else {
                    continue;
                };
                let receipt = transfers
                    .by_index
                    .get(&index)
                    .context("canonical mosaic transfer receipt missing")?;
                let transfer = &receipt.transfer;
                let probe_seconds = receipt.seconds;
                let source = cache.load_or_decode(&session.frames[index], &identities[index])?;
                check_source(&source, calibration, view.source)?;
                let sampled = sampler.gather_with_mapping(
                    source.as_ref(),
                    source.levels(),
                    &|p| view.map(p),
                    placement,
                    calibration.profile,
                    maps[pass].resampler(),
                )?;
                if !sampled.coverage.iter().any(|&v| v) {
                    continue;
                }
                prepared.prepare_with_masks(
                    SourceKey {
                        acquisition: index as u64,
                        bracket: pass,
                    },
                    std::array::from_fn(|c| sampled.planes[c].as_slice()),
                    &calibration.noise,
                    Some(&transfer.luma_beta),
                    Some(&transfer.max_color_beta),
                    &sampled.coverage,
                    &sampled.support,
                    gain,
                )?;
                merge.add_source(&mut group, &prepared)?;
                merge.fold_group(&mut group)?;
                sources += 1;
                serde_json::to_writer(
                    &mut receipts,
                    &json!({"tile":tile_index,"pass":pass,"source":index,"gain":gain,"covered":sampled.coverage.iter().filter(|&&v|v).count(),"luma_beta":transfer.luma_beta,"color_beta":transfer.max_color_beta,"samples_per_band":transfer.samples_per_band,"probe_seconds":probe_seconds,"probe_realizations":transfer.realizations,"probe_seed":transfer.seed}),
                )?;
                receipts.write_all(b"\n")?;
            }
            if sources == 0 {
                pass_reports.push(json!({"pass":pass,"sources":0,"valid_core":0}));
                continue;
            }
            let fused = merge.finish()?;
            let mut valid_core = 0;
            for y in 0..tile.core.height {
                for x in 0..tile.core.width {
                    let wx = tile.core.x + x - tile.work.x;
                    let wy = tile.core.y + y - tile.work.y;
                    let i = wy * tile.work.width + wx;
                    if !fused.valid[i] {
                        continue;
                    }
                    let world = canvas.world((tile.core.x + x) as f64, (tile.core.y + y) as f64);
                    let Some((qualified, margin)) = view.properties(world) else {
                        continue;
                    };
                    let value = std::array::from_fn(|c| fused.planes[c][i]);
                    // A single-acquisition model supplies the policy's nominal
                    // noise unit, not posterior selected/merged-pixel uncertainty.
                    let variance = std::array::from_fn(|c| {
                        calibration
                            .noise
                            .plane(CfaPlane::ALL[c])
                            .variance(value[c] / gain)
                            * gain
                            * gain
                    });
                    composite[y * tile.core.width + x].add(
                        value,
                        variance,
                        qualified,
                        margin,
                        pass,
                        args.agreement_sigma,
                    );
                    valid_core += 1;
                }
            }
            pass_reports.push(json!({"pass":pass,"sources":sources,"valid_core":valid_core,"total_work_valid":fused.valid.iter().filter(|&&v|v).count()}));
        }
        for y in 0..tile.core.height {
            for x in 0..tile.core.width {
                let sample = composite[y * tile.core.width + x];
                let i = (tile.core.y + y) * canvas.width + tile.core.x + x;
                output.valid[i] = sample.count > 0;
                output.owner[i] = sample.owner;
                output.join[i] = sample.join();
                for c in 0..4 {
                    output.planes[c][i] = sample.value[c];
                }
            }
        }
        tile_reports.push(json!({"tile":tile_index,"core":[tile.core.x,tile.core.y,tile.core.width,tile.core.height],"work":[tile.work.x,tile.work.y,tile.work.width,tile.work.height],"passes":pass_reports,"elapsed_seconds":tile_started.elapsed().as_secs_f64()}));
    }
    receipts.flush()?;
    receipts.get_ref().sync_all()?;
    for index in 0..session.len() {
        progress.frame_finished(
            index,
            maps[session.frames[index].pass_index].warps()[index]
                .placed()
                .is_some(),
        );
    }
    output.report = json!({"schema":"strehl.mosaic-render.v1","canvas_origin_quad":canvas.origin,"canvas_size_quad":[canvas.width,canvas.height],"valid_pixels":output.valid.iter().filter(|&&v|v).count(),"qualified_blend_pixels":output.join.iter().filter(|&&v|v==2).count(),"unmerged_overlap_pixels":output.join.iter().filter(|&&v|v==3).count(),"single_view_pixels":output.join.iter().filter(|&&v|v==1).count(),"tile_phase":plan.phase,"dependency_halo_quad":8*plan.phase,"tiles":tile_reports,"working_memory_reservation_bytes":reservation,"tile_work_reservation_bytes":tile_budget,"transfer_probes":probes,"elapsed_seconds":started.elapsed().as_secs_f64(),"join_policy":"Only locally native/held-out-qualified geometry and compatible CFA values enter a feathered mean. Other overlap selects maximum source-interior distance and is marked unmerged; ties follow declared pass order, never a primary preference.","noise_semantics":"Known original-sensel noise probes measure the actual gather+pyramid spatial average. Compatibility uses the injected single-acquisition model as a nominal policy unit, not merged uncertainty, calibrated probability or independent-noise gain.","alpha_policy":"Strict complete multiscale coverage, then writer demosaic-support erosion; no boundary estimator or black-pixel observation."});
    output.report["geometry_sampling_policy"] = json!(
        "Each view uses one continuous positive fitted mesh. Cross-view blending requires the complete CFA quad inside the actual held-witness hull of a ValidatedOverlap cell. Outside that hull retains SingleView ownership without a join certificate. Failed local cells remain alpha-invalid through operator support; no abrupt fitted/global substitution occurs."
    );
    output.report["transfer_prefetch"] = json!({"domain":"canonical full mosaic canvas; independent of output tile size","sources":probes,"lanes":transfers.lanes,"per_probe_bytes":transfers.per_probe_bytes,"reserved_bytes":transfers.reserved_bytes,"retained_result_bytes":transfers.result_bytes,"elapsed_seconds":transfers.elapsed_seconds});
    Ok(output)
}

pub(super) fn write_masks(
    destination: &Path,
    geometry: PlaneGeometry,
    owner: &[u16],
    join: &[u8],
) -> Result<()> {
    for (name, is_owner) in [("view-owner.tiff", true), ("join-confidence.tiff", false)] {
        let file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(destination.join(name))?;
        let mut writer = BufWriter::new(file);
        {
            let mut encoder = tiff::encoder::TiffEncoder::new(&mut writer)?;
            if is_owner {
                encoder.write_image::<tiff::encoder::colortype::Gray16>(
                    geometry.width.try_into()?,
                    geometry.height.try_into()?,
                    owner,
                )?;
            } else {
                encoder.write_image::<tiff::encoder::colortype::Gray8>(
                    geometry.width.try_into()?,
                    geometry.height.try_into()?,
                    join,
                )?;
            }
        }
        writer.flush()?;
        writer.get_ref().sync_all()?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use strehl_core::align::Similarity;
    use strehl_core::mosaic::{FocusEvidence, ForwardMesh, MosaicCanvas};
    use strehl_core::noise::{Levels, NoiseModel, PlaneNoise, Provenance};
    use strehl_core::plane::QuadSource;
    use strehl_core::pyramid::MergeConfig;
    #[test]
    fn planner_uses_whole_canvas_when_budget_allows_and_reduces_cores_before_refusal() {
        let canvas = MosaicCanvas {
            origin: [-20, 10],
            width: 4096,
            height: 3072,
        };
        let source = PlaneGeometry {
            width: 3504,
            height: 2336,
        };
        let cfg = MergeConfig {
            bands: 4,
            ..MergeConfig::default()
        };
        let policy = GroupPolicy {
            mode: GroupMode::Combine,
            primary: None,
            agreement_sigma: 4.0,
        };
        let (whole, total, _) =
            plan_domain(canvas, source, cfg, policy, 48_usize << 30, 128 << 20, 4096).unwrap();
        assert_eq!(whole.tiles.len(), 1);
        let (smaller, used, _) =
            plan_domain(canvas, source, cfg, policy, total - 1, 128 << 20, 4096).unwrap();
        assert!(smaller.tiles.len() > 1);
        assert!(used < total);
        assert_eq!(whole.phase, smaller.phase);
        assert!(plan_domain(canvas, source, cfg, policy, 512 << 20, 128 << 20, 4096).is_err());
    }

    struct FlatSource {
        geometry: PlaneGeometry,
        data: Vec<u16>,
    }
    impl QuadSource for FlatSource {
        fn geometry(&self) -> PlaneGeometry {
            self.geometry
        }
        fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
            let w = self.geometry.width * 2;
            let i = y * w * 2;
            (&self.data[i..i + w], &self.data[i + w..i + 2 * w])
        }
    }
    fn view(g: PlaneGeometry, shift: f64, qualified: bool) -> ViewMap {
        let mut mesh = ForwardMesh::new(
            g,
            2,
            2,
            vec![
                [shift, 0.0],
                [shift + g.width as f64 - 1.0, 0.0],
                [shift, g.height as f64 - 1.0],
                [shift + g.width as f64 - 1.0, g.height as f64 - 1.0],
            ],
            vec![if qualified {
                Visibility::ValidatedOverlap
            } else {
                Visibility::SingleView
            }],
            vec![
                FocusEvidence {
                    ordinal: 0.0,
                    width: 1.0,
                    usable: true
                };
                4
            ],
        )
        .unwrap();
        if qualified {
            mesh.join_hulls[0] = vec![
                [0., 0.],
                [g.width as f64 - 1., 0.],
                [g.width as f64 - 1., g.height as f64 - 1.],
                [0., g.height as f64 - 1.],
            ];
        }
        let limits = IndexLimits {
            bin_side: 32,
            max_bins: 1000,
            max_entries: 10000,
        };
        ViewMap {
            fitted: BackwardMesh::new(&mesh, MeshValidation::default(), limits).unwrap(),
            source: g,
        }
    }
    #[test]
    fn measured_hull_limits_complete_cfa_join_but_keeps_single_view_coverage() {
        let g = PlaneGeometry {
            width: 101,
            height: 101,
        };
        let mut mesh = ForwardMesh::new(
            g,
            2,
            2,
            vec![[0., 0.], [100., 0.], [0., 100.], [100., 100.]],
            vec![Visibility::ValidatedOverlap],
            vec![
                FocusEvidence {
                    ordinal: 0.,
                    width: 1.,
                    usable: true
                };
                4
            ],
        )
        .unwrap();
        mesh.join_hulls[0] = vec![[0., 0.], [100., 0.], [0., 100.]];
        let view = ViewMap {
            fitted: BackwardMesh::new(
                &mesh,
                MeshValidation::default(),
                IndexLimits {
                    bin_side: 16,
                    max_bins: 100,
                    max_entries: 1000,
                },
            )
            .unwrap(),
            source: g,
        };
        assert!(view.properties([49., 49.]).unwrap().0);
        assert!(
            !view.properties([50., 50.]).unwrap().0,
            "the CFA quad crosses the measured hull boundary"
        );
        assert!(!view.properties([75., 75.]).unwrap().0);
        assert!(
            matches!(view.map([75., 75.]), MappedPoint::Supported { .. }),
            "unqualified overlap remains covered by its original view"
        );
    }
    #[test]
    fn qualification_boundary_keeps_one_continuous_map_and_failed_cell_has_no_global_substitution()
    {
        let g = PlaneGeometry {
            width: 101,
            height: 81,
        };
        let mut mesh = ForwardMesh::new(
            g,
            3,
            2,
            vec![
                [0.0, 0.0],
                [54.0, 0.0],
                [100.0, 0.0],
                [0.0, 80.0],
                [54.0, 80.0],
                [100.0, 80.0],
            ],
            vec![Visibility::ValidatedOverlap, Visibility::SingleView],
            vec![
                FocusEvidence {
                    ordinal: 0.0,
                    width: 1.0,
                    usable: true
                };
                6
            ],
        )
        .unwrap();
        mesh.join_hulls[0] = vec![[0., 0.], [50., 0.], [50., 80.], [0., 80.]];
        let limits = IndexLimits {
            bin_side: 16,
            max_bins: 100,
            max_entries: 1000,
        };
        let view = ViewMap {
            fitted: BackwardMesh::new(&mesh, MeshValidation::default(), limits).unwrap(),
            source: g,
        };
        let source = |point| match view.map(point) {
            MappedPoint::Supported { source, .. } => source,
            _ => panic!("continuous positive cells must be covered"),
        };
        let left = source([54.0 - 0.001, 40.0]);
        let right = source([54.0 + 0.001, 40.0]);
        assert!(
            (right[0] - left[0]).abs() < 0.003,
            "qualification is not a geometric discontinuity"
        );
        assert!(
            (54.001 - left[0]).abs() > 3.9,
            "global-map substitution foil must expose the jump"
        );
        assert!(view.qualified([53.0, 40.0]).is_some());
        assert!(view.qualified([55.0, 40.0]).is_none());
        mesh.visibility[1] = Visibility::HeldoutFailure;
        let failed = ViewMap {
            fitted: BackwardMesh::new(&mesh, MeshValidation::default(), limits).unwrap(),
            source: g,
        };
        assert!(matches!(
            failed.map([60.0, 40.0]),
            MappedPoint::Rejected(Visibility::HeldoutFailure)
        ));
    }
    // Commission the actual mapped sampler, measured operator transfer, existing
    // multiscale focus consumer and compositor together before photographic work.
    // A complete union and a qualified overlap are positive requirements; zero
    // holes or a successful rejection alone cannot satisfy this control.
    #[test]
    fn flat_native_consumer_extends_union_and_is_invariant_to_global_phase_tiles() {
        let g = PlaneGeometry {
            width: 160,
            height: 128,
        };
        let canvas = MosaicCanvas {
            origin: [0, 0],
            width: 224,
            height: 128,
        };
        let source = FlatSource {
            geometry: g,
            data: vec![2024; g.pixels() * 4],
        };
        let levels = Levels {
            black: 1024.0,
            white: 16384.0,
        };
        let noise = NoiseModel::new(
            [PlaneNoise {
                gain_dn_per_e: 1e-6,
                read_noise_e: 1e6,
                levels,
            }; 4],
            100.0,
            Provenance::Profile,
        );
        let cfg = MergeConfig {
            bands: 2,
            sharpen_per_octave: 1.0,
            ..MergeConfig::default()
        };
        let policy = GroupPolicy {
            mode: GroupMode::Combine,
            primary: None,
            agreement_sigma: 4.0,
        };
        let render = |side: usize, qualified: bool| {
            let plan = MosaicTilePlan::new(canvas, side, 2, 32, canvas.width * canvas.height, 100)
                .unwrap();
            let mut output = vec![Composite::default(); canvas.width * canvas.height];
            for tile in plan.tiles {
                let d = MappedSamplingDomain {
                    canvas,
                    rect: tile.work,
                };
                let mut combined = vec![Composite::default(); tile.core.width * tile.core.height];
                for pass in 0..2 {
                    let view = view(g, 64.0 * pass as f64, qualified);
                    let mapping = |p| view.map(p);
                    let transfer = super::super::probe::measure(
                        g,
                        d,
                        &mapping,
                        Similarity::IDENTITY,
                        None,
                        Resampler::Bilinear,
                        ProbeConfig {
                            bands: 2,
                            realizations: 2,
                            ..ProbeConfig::default()
                        },
                        32 << 20,
                    )
                    .unwrap();
                    let mut sampler = NativeMappedSampler::new(g, d, 32 << 20).unwrap();
                    let sampled = sampler
                        .gather_with_mapping(
                            &source,
                            levels,
                            &mapping,
                            Similarity::IDENTITY,
                            None,
                            Resampler::Bilinear,
                        )
                        .unwrap();
                    let mut prepared =
                        PreparedSource::new(tile.work.width, tile.work.height, cfg).unwrap();
                    let mut group =
                        GroupWorkspace::new(tile.work.width, tile.work.height, cfg, policy)
                            .unwrap();
                    let mut merge =
                        SessionMerge::new(tile.work.width, tile.work.height, cfg).unwrap();
                    prepared
                        .prepare_with_masks(
                            SourceKey {
                                acquisition: pass as u64,
                                bracket: pass,
                            },
                            std::array::from_fn(|c| sampled.planes[c].as_slice()),
                            &noise,
                            Some(&transfer.luma_beta),
                            Some(&transfer.max_color_beta),
                            &sampled.coverage,
                            &sampled.support,
                            1.0,
                        )
                        .unwrap();
                    merge.add_source(&mut group, &prepared).unwrap();
                    merge.fold_group(&mut group).unwrap();
                    let result = merge.finish().unwrap();
                    for y in 0..tile.core.height {
                        for x in 0..tile.core.width {
                            let i =
                                (tile.core.y + y - tile.work.y) * tile.work.width + tile.core.x + x
                                    - tile.work.x;
                            if result.valid[i] {
                                let (qualified, margin) = view
                                    .properties(
                                        canvas.world(
                                            (tile.core.x + x) as f64,
                                            (tile.core.y + y) as f64,
                                        ),
                                    )
                                    .unwrap();
                                combined[y * tile.core.width + x].add(
                                    std::array::from_fn(|c| result.planes[c][i]),
                                    [1.0; 4],
                                    qualified,
                                    margin,
                                    pass,
                                    4.0,
                                );
                            }
                        }
                    }
                }
                for y in 0..tile.core.height {
                    for x in 0..tile.core.width {
                        output[(tile.core.y + y) * canvas.width + tile.core.x + x] =
                            combined[y * tile.core.width + x];
                    }
                }
            }
            output
        };
        let whole = render(256, true);
        let tiled = render(64, true);
        let row = 64 * canvas.width;
        let supported: Vec<_> = (0..canvas.width)
            .filter(|&x| whole[row + x].count > 0)
            .collect();
        assert!(
            supported.last().unwrap() - supported[0] + 1 > g.width,
            "mosaic must extend one-view FOV"
        );
        assert!(
            whole.iter().any(|v| v.join() == 2),
            "requires a positive qualified join"
        );
        assert!(
            whole.iter().any(|v| v.join() == 0),
            "exterior must remain masked"
        );
        for (a, b) in whole.iter().zip(&tiled) {
            assert_eq!(a.join(), b.join(), "tile phase/support changed");
            if a.count > 0 {
                for c in 0..4 {
                    assert!((a.value[c] - 1000.0).abs() < 0.001);
                    assert!((a.value[c] - b.value[c]).abs() < 0.001);
                }
            }
        }
        let refused = render(256, false);
        assert!(!refused.iter().any(|v| v.join() == 2));
        assert!(refused.iter().any(|v| v.join() == 3));
        assert!(refused.iter().any(|v| v.join() == 1));
    }
    #[test]
    fn compositor_never_blends_unqualified_or_disagreeing_views_and_retains_coverage() {
        let mut flat = Composite::default();
        flat.add([10.0; 4], [1.0; 4], true, 10.0, 0, 4.0);
        flat.add([12.0; 4], [1.0; 4], true, 10.0, 1, 4.0);
        assert_eq!(flat.value, [11.0; 4]);
        assert_eq!(flat.join(), 2);
        flat.add([100.0; 4], [1.0; 4], true, 5.0, 2, 4.0);
        assert_eq!(
            flat.value, [10.0; 4],
            "a third-view disagreement restores one original view, not the prior mean"
        );
        assert_eq!(flat.join(), 3);
        let mut unqualified = Composite::default();
        unqualified.add([10.0; 4], [1.0; 4], false, 10.0, 0, 4.0);
        unqualified.add([12.0; 4], [1.0; 4], true, 20.0, 1, 4.0);
        assert_eq!(unqualified.value, [12.0; 4]);
        assert_eq!(unqualified.join(), 3);
        assert_eq!(unqualified.owner, 2);
        let mut changed = Composite::default();
        changed.add([10.0; 4], [1.0; 4], true, 10.0, 0, 4.0);
        changed.add([100.0; 4], [1.0; 4], true, 20.0, 1, 4.0);
        assert_eq!(changed.value, [100.0; 4]);
        assert_eq!(changed.join(), 3);
        let mut negative = Composite::default();
        negative.add([-2.0; 4], [1.0; 4], false, 10.0, 0, 4.0);
        assert_eq!(negative.value, [-2.0; 4]);
        assert_eq!(negative.join(), 1);
        assert_eq!(Composite::default().join(), 0);
    }
}
