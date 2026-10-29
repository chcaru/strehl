//! Cached-only two-stage mosaic validation commissioning. No output photograph.
//! The initial FIT artifact and complete attempted support are reloaded and
//! audited before freezing validation islands or reading stage-two signals.
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    time::Instant,
};
use strehl_cli::{session_cache, session_focus, session_input, session_sampling};
use strehl_core::{align::Similarity, warpmap::WarpMap};
#[path = "geometry-replay.rs"]
pub(crate) mod common;
pub(crate) use common::session_mosaic_geometry;
use common::{embed, guide, hash, hash_bytes, read, save};
use session_mosaic_geometry::{
    CoarseCorrespondence, MatchRole, MosaicGeometryConfig, MosaicGuide, NativeCorrespondence,
    PairDiscovery,
    roles::{AncestorFootprint, AnchorGrid, FrozenRolePlan, IslandProposal, Rectangle, RolePlan},
};

#[path = "island-nomination.rs"]
pub(crate) mod nomination;
const WORK_BYTES: usize = 3 << 30;

#[derive(Serialize, Deserialize)]
struct InitialFitEvidence {
    schema: String,
    upstream_binding_sha256: String,
    seed_bits: [u64; 4],
    fit_feature_witnesses: Vec<Value>,
    fit_candidates: Vec<CoarseCorrespondence>,
    /// Every attempted FIT query, including failed/early iterations and refusals.
    fit_native: Vec<NativeCorrespondence>,
    ancestors: Vec<AncestorFootprint>,
    geometrically_proved_no_query: Vec<String>,
    independent_fit_sites: usize,
    dependency_scope: String,
}

/// Restore producing types before rebuilding the artifact: plain JSON numbers
/// would widen a shortest-decimal f32 response to a different f64 value.
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct ReplayedFeatureWitness {
    index: usize,
    point_quad: [f64; 2],
    source: usize,
    focus: Option<[f32; 2]>,
    heldout: bool,
    spatial_block: [usize; 2],
    support_radius_quad: f64,
    response: f32,
}

pub(crate) fn audit_attempts(
    native: &[NativeCorrespondence],
    maps: &[WarpMap],
    config: &MosaicGeometryConfig,
) -> Result<(Vec<AncestorFootprint>, Vec<String>)> {
    let mut ancestors = Vec::new();
    let mut no_query = Vec::new();
    for receipt in native {
        ensure!(
            receipt.candidate.role == MatchRole::Fit,
            "non-FIT receipt in initial evidence"
        );
        let c = &receipt.candidate;
        let placements = [
            maps[c.pass_a].warps()[c.source_a]
                .placed()
                .context("reference unplaced")?,
            maps[c.pass_b].warps()[c.source_b]
                .placed()
                .context("moving unplaced")?,
        ];
        let Some(bounds) = session_mosaic_geometry::native_attempted_support(
            receipt,
            placements,
            maps[0].geometry(),
            config,
        )?
        else {
            no_query.push(c.id.clone());
            continue;
        };
        for (index, (pass, source)) in [(c.pass_a, c.source_a), (c.pass_b, c.source_b)]
            .into_iter()
            .enumerate()
        {
            ancestors.push(AncestorFootprint {
                pass,
                source,
                measurement_id: c.id.clone(),
                bounds: Rectangle {
                    low: bounds[index][0],
                    high: bounds[index][1],
                },
            });
        }
    }
    Ok((ancestors, no_query))
}

fn original_witnesses(
    guide: &MosaicGuide,
    map: &WarpMap,
    point: [f64; 2],
    limit: usize,
) -> Vec<usize> {
    let p = [0, 1].map(|i| ((point[i] - guide.origin[i]) / guide.step as f64).round());
    if p[0] < 0.
        || p[1] < 0.
        || p[0] >= guide.geometry.width as f64
        || p[1] >= guide.geometry.height as f64
    {
        return Vec::new();
    }
    let index = p[1] as usize * guide.geometry.width + p[0] as usize;
    if !guide.covered[index] {
        return Vec::new();
    }
    let mut sources = Vec::new();
    for id in guide.source_indices[index] {
        if id < map.len() && map.warps()[id].placed().is_some() && !sources.contains(&id) {
            sources.push(id);
            if sources.len() == limit {
                break;
            }
        }
    }
    sources
}

fn held_candidates(plan: &FrozenRolePlan) -> Vec<CoarseCorrespondence> {
    let mut out = Vec::new();
    for (island, item) in plan.plan.islands.iter().enumerate() {
        for a in &item.proposal.original_witnesses[0] {
            for b in &item.proposal.original_witnesses[1] {
                out.push(CoarseCorrespondence {
                    id: format!("{}-source-{a}-{b}", item.proposal.id),
                    pass_a: 0,
                    pass_b: 1,
                    point_a_quad: item.proposal.reference_center_quad,
                    point_b_quad: item.nominated_moving_center_quad,
                    source_a: *a,
                    source_b: *b,
                    focus_a: None,
                    focus_b: None,
                    role: MatchRole::Heldout,
                    spatial_blocks: [[island, usize::MAX]; 2],
                    descriptor_distance: 0.,
                    seed_residual_quad: 0.,
                    within_seed_support: true,
                    grid_nomination: false,
                    spatial_roles_match: true,
                });
            }
        }
    }
    out
}

fn replay(
    pilot: &Path,
    compact: &Path,
    cache_root: &Path,
    destination: &Path,
    reuse: Option<&Path>,
    policy: nomination::Policy,
) -> Result<()> {
    let started = Instant::now();
    let session: session_input::ResolvedSession = read(&pilot.join("session.json"))?;
    let ids: Vec<session_input::SourceIdentity> = read(&pilot.join("source-identities.json"))?;
    ensure!(
        session.passes.len() == 2 && session.spec.primary_pass.is_none(),
        "two views, no primary required"
    );
    let current = session
        .spec
        .resolve_from(&session.passes[0].directories[0])?;
    ensure!(current.frames == session.frames, "original census changed");
    for id in &ids {
        id.check_unchanged()?;
    }
    let destination = session.ensure_output_outside_sources(destination)?;
    std::fs::create_dir(&destination)?;
    let mut guides = Vec::new();
    let mut maps = Vec::new();
    for pass in 0..2 {
        let loaded = guide(compact, pilot, pass, &session)?;
        let alignment: Value = read(&pilot.join(format!("pass-{:02}/alignment.json", pass + 1)))?;
        let map = embed(
            &session,
            pass,
            &WarpMap::from_text(alignment["warpmap"].as_str().context("map absent")?)?,
        )?;
        ensure!(
            hash_bytes(map.to_text().as_bytes()) == loaded.receipt.alignment_sha256,
            "embedded map hash differs"
        );
        guides.push(loaded);
        maps.push(map);
    }
    let initial_config = MosaicGeometryConfig {
        max_canvas_pixels: 33_000_000,
        ..Default::default()
    };
    let initial_binding =
        session_mosaic_geometry::binding(&session, &ids, &guides, &initial_config)?;
    let upstream_hash = hash_bytes(&serde_json::to_vec(&initial_binding)?);
    save(&destination.join("session.json"), &session)?;
    save(&destination.join("source-identities.json"), &ids)?;
    save(
        &destination.join("replay-binding.json"),
        &json!({
            "schema":"strehl.cached-two-stage-mosaic-islands.v1", "binding":initial_binding,
            "workers":4,"memory_limit_bytes":4_u64<<30,"raw_decode_policy":"cached only; missing entry refuses",
            "compact_receipt_sha256":hash(&compact.join("receipt.json"))?,
            "upstream_binding_sha256":upstream_hash,"mask_semantics":"raw quad ownership before arithmetic; filter/query halo separately determines validity",
            "performance_claim":"none; concurrent host workload recorded by run wrapper",
            "island_nomination_policy":format!("{policy:?}"),"nomination_rule_sha256":hash_bytes(nomination::RULE.as_bytes()),
            "nomination_protocol_sha256":hash_bytes(include_str!("focus-island-protocol.md").as_bytes())
        }),
    )?;
    let mut cache = session_cache::SourceCache::new(cache_root, &session, 512 << 20)?;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let result = pool.install(|| -> Result<()> {
        let stage1 = destination.join("stage-1"); std::fs::create_dir(&stage1)?;
        let (pairs, features, native): (Vec<PairDiscovery>, Value, Vec<NativeCorrespondence>) = if let Some(origin) = reuse {
            let bound: Value = read(&origin.join("replay-binding.json"))?;
            ensure!(bound["binding"] == serde_json::to_value(&initial_binding)?, "reused stage1 source/config/algorithm binding differs");
            ensure!(hash(&origin.join("session.json"))? == hash(&destination.join("session.json"))? && hash(&origin.join("source-identities.json"))? == hash(&destination.join("source-identities.json"))?, "reused stage1 census differs");
            let root = origin.join("stage-1");
            (read(&root.join("mosaic-candidates.json"))?, read(&root.join("mosaic-source-features.json"))?, read(&root.join("mosaic-native-measurements.json"))?)
        } else {
            let (pairs, features) = session_mosaic_geometry::discover_source_pairs_cached(&session, &ids, &maps, &mut cache, &guides, &initial_config, WORK_BYTES)?;
            let native = session_mosaic_geometry::refine_native_correspondences_cached(&session, &ids, &maps, &mut cache, &guides, &pairs, &initial_config, WORK_BYTES)?;
            (pairs, serde_json::to_value(features)?, native)
        };
        ensure!(pairs.len() == 1 && pairs[0].pass_a == 0 && pairs[0].pass_b == 1, "unexpected pair topology");
        let seed = pairs[0].seed_a_to_b.context("initial FIT-only seed absent")?;
        save(&stage1.join("mosaic-candidates.json"), &pairs)?;
        save(&stage1.join("mosaic-source-features.json"), &features)?;
        save(&stage1.join("mosaic-native-measurements.json"), &native)?;
        let fit_native: Vec<_> = native.into_iter().filter(|r| r.candidate.role == MatchRole::Fit).collect();
        let selected = session_mosaic_geometry::independent_native_constraints(&fit_native, 2, initial_config.maximum_native_residual)?;
        ensure!(selected.receipt_indices.len() >= 8, "fewer than eight independent initial FIT sites");
        let (ancestors, no_query) = audit_attempts(&fit_native, &maps, &initial_config)?;
        let fit_features = features.as_array().context("feature receipts not an array")?.iter().map(|f| -> Result<Value> {
            let witnesses: Vec<ReplayedFeatureWitness> = serde_json::from_value(f["feature_witnesses"].clone())?;
            Ok(json!({"pass":f["pass"],"witnesses":witnesses.iter().filter(|w| !w.heldout).collect::<Vec<_>>()}))
        }).collect::<Result<_>>()?;
        let evidence = InitialFitEvidence {
            schema:"strehl.initial-fit-attempt-evidence.v1".into(), upstream_binding_sha256:upstream_hash.clone(), seed_bits:seed.map(f64::to_bits),
            fit_feature_witnesses:fit_features, fit_candidates:pairs[0].correspondences.iter().filter(|c| c.role == MatchRole::Fit).cloned().collect(),
            fit_native, ancestors, geometrically_proved_no_query:no_query, independent_fit_sites:selected.receipt_indices.len(),
            dependency_scope:"Conditional on bound within-pass maps/focus/source nominations/calibration. FIT descriptor normalization, quotas and competitors are role-isolated. Every attempted FIT native footprint includes all iterations, reverse directions, filtering and interpolation, including refusals; unknown traces refuse planning.".into(),
        };
        let evidence_path = stage1.join("initial-fit-evidence.json");
        save(&evidence_path, &evidence)?;
        let evidence_hash = hash(&evidence_path)?;
        if let Some(origin) = reuse {
            let original = origin.join("stage-1/initial-fit-evidence.json");
            let previous: InitialFitEvidence = read(&original)?;
            ensure!(serde_json::to_value(&previous)? == serde_json::to_value(&evidence)?, "reconstructed FIT evidence differs from original completed stage1");
            let names = ["mosaic-candidates.json","mosaic-source-features.json","mosaic-native-measurements.json","initial-fit-evidence.json"];
            let mut sources = serde_json::Map::new();
            for name in names { sources.insert(name.into(), json!(hash(&origin.join("stage-1").join(name))?)); }
            save(&destination.join("stage-1-reuse.json"), &json!({"origin":origin,"source_files_sha256":sources,"reconstructed_evidence_sha256":evidence_hash,"binding_and_seed_and_all_fit_attempts_and_feature_roles_and_ancestry_rechecked":true}))?;
        }
        let loaded: InitialFitEvidence = read(&evidence_path)?;
        ensure!(loaded.seed_bits == seed.map(f64::to_bits) && loaded.upstream_binding_sha256 == upstream_hash, "reloaded initial evidence differs");
        let (recomputed, no_query) = audit_attempts(&loaded.fit_native, &maps, &initial_config)?;
        ensure!(recomputed == loaded.ancestors && no_query == loaded.geometrically_proved_no_query, "reloaded attempt ancestry differs");
        ensure!(hash(&evidence_path)? == evidence_hash, "initial FIT evidence changed before freeze");
        let grids = [0,1].map(|pass| AnchorGrid {
            source_size_quad:[guides[pass].source_geometry.width,guides[pass].source_geometry.height],
            guide_origin_quad:guides[pass].origin,guide_step_quad:guides[pass].step,
            initial_block_guide_pixels:initial_config.holdout_block_guide_pixels,
            global_source_range:[session.passes[pass].global_range.start,session.passes[pass].global_range.end],
        });
        let (proposals, absent, nominations) = nomination::propose(&guides, &maps, &initial_config, loaded.seed_bits.map(f64::from_bits), policy, nomination::Planning { upstream:&upstream_hash,evidence:&evidence_hash,grids:&grids,ancestors:&loaded.ancestors })?;
        save(&destination.join("island-proposal-unavailable.json"), &absent)?;
        save(&destination.join("island-witness-nominations.json"), &nominations)?;
        let plan = RolePlan::build(upstream_hash, evidence_hash.clone(), grids, loaded.seed_bits.map(f64::from_bits),
            initial_config.coarse_residual_guide_pixels * guides[0].step as f64, loaded.ancestors, proposals)?.freeze()?;
        let plan_path = destination.join("frozen-role-plan.json");
        save(&plan_path, &plan)?;
        let frozen: FrozenRolePlan = read(&plan_path)?; frozen.verify()?;
        ensure!(frozen.sha256 == plan.sha256 && hash(&evidence_path)? == evidence_hash, "plan or initial evidence changed before stage two");
        ensure!(!frozen.plan.islands.is_empty(), "no validation islands survived complete initial dependencies");
        save(&destination.join("stage-2-read-permission.json"), &json!({"frozen_role_plan_sha256":hash(&plan_path)?,"plan_sha256":frozen.sha256,"initial_fit_evidence_sha256":evidence_hash,"nominal_anchors":nominations.len(),"unavailable_anchors":absent.len(),"islands":frozen.plan.islands.len(),"refused_islands":frozen.plan.refused.len(),"initial_fit_attempts":loaded.fit_native.len(),"ancestor_footprints":frozen.plan.ancestor_footprints.len(),"nomination_receipt_sha256":hash(&destination.join("island-witness-nominations.json"))?}))?;
        // This is the first stage-two original-pixel call, after plan publication.
        let config = MosaicGeometryConfig { role_plan:Some(Box::new(frozen)), ..initial_config.clone() };
        let stage2 = destination.join("stage-2"); std::fs::create_dir(&stage2)?;
        let binding = session_mosaic_geometry::binding(&session, &ids, &guides, &config)?;
        save(&stage2.join("binding.json"), &binding)?;
        let (mut pairs, features) = session_mosaic_geometry::discover_source_pairs_cached(&session, &ids, &maps, &mut cache, &guides, &config, WORK_BYTES)?;
        ensure!(pairs.len() == 1, "stage-two topology changed");
        ensure!(pairs[0].correspondences.iter().all(|c| c.role == MatchRole::Fit), "stage-two descriptors consumed validation islands");
        pairs[0].correspondences.extend(held_candidates(config.role_plan.as_ref().unwrap()));
        save(&stage2.join("mosaic-candidates.json"), &pairs)?;
        save(&stage2.join("mosaic-source-features.json"), &features)?;
        let native = session_mosaic_geometry::refine_native_correspondences_cached(&session, &ids, &maps, &mut cache, &guides, &pairs, &config, WORK_BYTES)?;
        save(&stage2.join("mosaic-native-measurements.json"), &native)?;
        let selected = session_mosaic_geometry::independent_native_constraints(&native, 2, config.maximum_native_residual)?;
        save(&stage2.join("independent-native-sites.json"), &json!({"receipt_indices":selected.receipt_indices,"accepted":native.iter().filter(|n|n.accepted).count(),"fit":selected.receipt_indices.iter().filter(|&&i| native[i].candidate.role == MatchRole::Fit).count(),"held":selected.receipt_indices.iter().filter(|&&i| native[i].candidate.role == MatchRole::Heldout).count()}))?;
        let geometry = session_mosaic_geometry::solve_geometry(&session, &ids, &guides, &pairs, &native, &config, WORK_BYTES)?;
        geometry.save(&stage2.join("mosaic-geometry.json"), &session)?;
        save(&stage2.join("mosaic-geometry-report.json"), &geometry.report)?;
        Ok(())
    });
    ensure!(
        cache.stats().decodes == 0,
        "cached-only replay attempted RAW decode"
    );
    save(
        &destination.join("replay-outcome.json"),
        &json!({"elapsed_seconds":started.elapsed().as_secs_f64(),"raw_decodes":cache.stats().decodes,"peak_resident_cfa_bytes":cache.stats().peak_resident_cfa_bytes,"success":result.is_ok(),"error":result.as_ref().err().map(ToString::to_string),"photographic_claim":"none; geometry commissioning only"}),
    )?;
    result
}

fn main() -> Result<()> {
    let args: Vec<_> = std::env::args_os().skip(1).map(PathBuf::from).collect();
    let focus = args
        .last()
        .is_some_and(|p| p.to_str() == Some("focus-coverage"));
    let count = args.len() - usize::from(focus);
    ensure!(
        (4..=5).contains(&count),
        "island-replay PREPARED COMPACT_GUIDES CACHE FRESH_OUTPUT [EXACT_STAGE1_RUN] [focus-coverage]"
    );
    replay(
        &args[0],
        &args[1],
        &args[2],
        &args[3],
        if count == 5 {
            Some(args[4].as_path())
        } else {
            None
        },
        if focus {
            nomination::Policy::FocusCoverage
        } else {
            nomination::Policy::Fixed
        },
    )
}
