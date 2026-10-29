//! Known-scene source-focus diagnostic; prior held measurements are reused.
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    time::Instant,
};
use strehl_cli::{session_cache, session_focus, session_input, session_sampling};
use strehl_core::{align::Similarity, warpmap::WarpMap};
#[path = "island-replay.rs"]
mod staged;
use session_mosaic_geometry::{
    CoarseCorrespondence, MatchRole, MosaicBinding, MosaicGeometry, MosaicGeometryConfig,
    MosaicGuide, NativeCorrespondence, PairDiscovery,
    roles::{AnchorGrid, IslandProposal, Rectangle, RolePlan, SpatialRole},
};
use staged::common::{embed, guide, hash, hash_bytes, read, save};
pub(crate) use staged::session_mosaic_geometry;
#[path = "focus-fit-nomination.rs"]
mod nomination;
const WORK_BYTES: usize = 3 << 30;

fn require_same_sources(
    a: &[session_input::SourceIdentity],
    b: &[session_input::SourceIdentity],
) -> Result<()> {
    ensure!(a == b, "prior ordered source identities differ");
    Ok(())
}

fn run(pilot: &Path, compact: &Path, cache_root: &Path, previous: &Path, out: &Path) -> Result<()> {
    let started = Instant::now();
    let session: session_input::ResolvedSession = read(&pilot.join("session.json"))?;
    let ids: Vec<session_input::SourceIdentity> = read(&pilot.join("source-identities.json"))?;
    ensure!(
        session.passes.len() == 2 && session.spec.primary_pass.is_none(),
        "two views and no primary required"
    );
    ensure!(
        session
            .spec
            .resolve_from(&session.passes[0].directories[0])?
            .frames
            == session.frames,
        "source census changed"
    );
    for id in &ids {
        id.check_unchanged()?;
    }
    let out = session.ensure_output_outside_sources(out)?;
    std::fs::create_dir(&out)?;
    let mut guides = Vec::new();
    let mut maps = Vec::new();
    for pass in 0..2 {
        let loaded = guide(compact, pilot, pass, &session)?;
        let envelope: Value = read(&pilot.join(format!("pass-{:02}/alignment.json", pass + 1)))?;
        let map = embed(
            &session,
            pass,
            &WarpMap::from_text(envelope["warpmap"].as_str().context("map absent")?)?,
        )?;
        ensure!(
            hash_bytes(map.to_text().as_bytes()) == loaded.receipt.alignment_sha256,
            "map/guide binding differs"
        );
        guides.push(loaded);
        maps.push(map);
    }
    let prior = previous.join("stage-2");
    let bound: MosaicBinding = read(&prior.join("binding.json"))?;
    let config = bound.config.clone();
    let frozen = config
        .role_plan
        .as_ref()
        .context("prior frozen plan absent")?;
    frozen.verify()?;
    ensure!(
        serde_json::to_value(session_mosaic_geometry::binding(
            &session, &ids, &guides, &config
        )?)? == serde_json::to_value(&bound)?,
        "current source/config/algorithm binding differs"
    );
    let prior_ids: Vec<session_input::SourceIdentity> =
        read(&previous.join("source-identities.json"))?;
    require_same_sources(&prior_ids, &ids)?;
    let evidence_path = previous.join("stage-1/initial-fit-evidence.json");
    ensure!(
        hash(&evidence_path)? == frozen.plan.initial_fit_evidence_sha256,
        "initial FIT evidence digest differs"
    );
    let evidence: Value = read(&evidence_path)?;
    let initial_native: Vec<NativeCorrespondence> =
        serde_json::from_value(evidence["fit_native"].clone())?;
    let initial_config = MosaicGeometryConfig {
        role_plan: None,
        ..config.clone()
    };
    let (ancestors, no_query) = staged::audit_attempts(&initial_native, &maps, &initial_config)?;
    ensure!(
        serde_json::to_value(&ancestors)?
            == serde_json::to_value(&frozen.plan.ancestor_footprints)?
            && serde_json::to_value(&ancestors)? == evidence["ancestors"]
            && serde_json::to_value(no_query)? == evidence["geometrically_proved_no_query"],
        "initial attempted ancestry differs"
    );
    let seed_bits: Vec<u64> = serde_json::from_value(evidence["seed_bits"].clone())?;
    ensure!(
        seed_bits == frozen.plan.initial_seed.map(f64::to_bits),
        "initial FIT seed differs"
    );
    let initial_pairs: Vec<PairDiscovery> = read(&previous.join("stage-1/mosaic-candidates.json"))?;
    ensure!(
        initial_pairs.len() == 1
            && initial_pairs[0].seed_a_to_b.map(|x| x.map(f64::to_bits))
                == Some(frozen.plan.initial_seed.map(f64::to_bits)),
        "initial seed artifact differs"
    );
    // Load reconstructs measured maps/reports instead of trusting visibility flags.
    let old = MosaicGeometry::load(
        &prior.join("mosaic-geometry.json"),
        &session,
        &ids,
        &guides,
        &config,
    )?;
    let old_native: Vec<NativeCorrespondence> =
        read(&prior.join("mosaic-native-measurements.json"))?;
    ensure!(
        serde_json::to_value(&old_native)? == serde_json::to_value(&old.report.native_receipts)?,
        "prior native receipt file differs from bound geometry"
    );
    save(&out.join("session.json"), &session)?;
    save(&out.join("source-identities.json"), &ids)?;
    save(&out.join("binding.json"), &bound)?;
    let (candidates, nominations) = nomination::nominate(&guides, &maps, &config)?;
    save(&out.join("fit-nominations.json"), &nominations)?;
    save(&out.join("fit-candidates.json"), &candidates)?;
    save(
        &out.join("read-permission.json"),
        &json!({"schema":"strehl.focus-matched-fit-read-permission.v1","prior_run":previous,
        "prior_geometry_sha256":hash(&prior.join("mosaic-geometry.json"))?,"prior_native_sha256":hash(&prior.join("mosaic-native-measurements.json"))?,
        "prior_source_census_sha256":hash(&previous.join("source-identities.json"))?,"prepared_source_census_sha256":hash(&pilot.join("source-identities.json"))?,"ordered_source_identities_exact":true,
        "initial_fit_evidence_sha256":hash(&evidence_path)?,"all_initial_attempted_ancestors_recomputed":true,"frozen_plan_sha256":frozen.sha256,
        "candidate_sha256":hash(&out.join("fit-candidates.json"))?,"nominations_sha256":hash(&out.join("fit-nominations.json"))?,
        "rule":nomination::RULE,"protocol_sha256":hash_bytes(include_str!("focused-fit-protocol.md").as_bytes()),"workers":4,"work_bytes":WORK_BYTES,"cache_bytes":512usize<<20,
        "nominal_anchors":nominations.len(),"selected_anchors":nominations.iter().filter(|r|!r["selected"].is_null()).count(),"source_pairs":candidates.len(),
        "fresh_native_held_reads":false,"qualification_scope":"development on known scene; reused held observations cannot supply fresh final qualification"}),
    )?;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let mut cache = session_cache::SourceCache::new(cache_root, &session, 512 << 20)?;
    let mut pair = initial_pairs[0].clone();
    pair.correspondences = candidates;
    pair.ordinal_seed = None;
    pair.nomination =
        "frozen focus-matched FIT grid; actual coarse original NCC required; no descriptor claim"
            .into();
    pair.features_a = 0;
    pair.features_b = 0;
    pair.reciprocal_matches = 0;
    pair.directional_ratio_matches = [0, 0];
    pair.fit_inliers = 0;
    pair.seed_semantics =
        "unchanged initial FIT-only seed; untrusted grid search nomination".into();
    let fresh = pool.install(|| {
        session_mosaic_geometry::refine_explicit_correspondences_cached(
            &session,
            &ids,
            &maps,
            &mut cache,
            &guides,
            &[pair.clone()],
            &config,
            WORK_BYTES,
        )
    })?;
    ensure!(
        fresh
            .iter()
            .all(|n| n.candidate.role == MatchRole::Fit && n.candidate.grid_nomination),
        "new candidates bypassed FIT/coarse policy"
    );
    save(&out.join("new-native-measurements.json"), &fresh)?;
    let old_held: Vec<_> = old_native
        .iter()
        .filter(|n| n.candidate.role == MatchRole::Heldout)
        .cloned()
        .collect();
    let mut summaries = Vec::new();
    for name in ["mixed-control", "focused-only", "augmented"] {
        let directory = out.join(name);
        std::fs::create_dir(&directory)?;
        let native = match name {
            "mixed-control" => old_native.clone(),
            "focused-only" => fresh.iter().chain(&old_held).cloned().collect(),
            _ => old_native.iter().chain(&fresh).cloned().collect(),
        };
        save(&directory.join("native-measurements.json"), &native)?;
        let discovery = if name == "mixed-control" {
            old.report.discovery.clone()
        } else {
            vec![pair.clone()]
        };
        match session_mosaic_geometry::solve_geometry(
            &session, &ids, &guides, &discovery, &native, &config, WORK_BYTES,
        ) {
            Ok(result) => {
                if name == "mixed-control" {
                    ensure!(
                        serde_json::to_value(&result.report)? == serde_json::to_value(&old.report)?,
                        "mixed control changed"
                    );
                }
                result.save(&directory.join("geometry.json"), &session)?;
                save(&directory.join("report.json"), &result.report)?;
                summaries.push(json!({"arm":name,"fit":result.report.fit_observations,"held":result.report.heldout_observations,"fit_rms_quad":result.report.fit_rms_quad,
                    "maximum_heldout_error_quad":result.report.maximum_heldout_error_quad,"qualified_cells":result.report.qualified_join_cells,"scope":"known-scene diagnostic only"}));
            }
            Err(error) => {
                let result = json!({"arm":name,"refusal":format!("{error:#}")});
                save(&directory.join("refusal.json"), &result)?;
                summaries.push(result);
            }
        }
    }
    ensure!(
        session
            .spec
            .resolve_from(&session.passes[0].directories[0])?
            .frames
            == session.frames,
        "source census changed during replay"
    );
    for id in &ids {
        id.check_unchanged()?;
    }
    let stats = cache.stats();
    ensure!(
        stats.decodes == 0,
        "cached replay unexpectedly decoded a RAW"
    );
    save(
        &out.join("outcome.json"),
        &json!({"elapsed_seconds":started.elapsed().as_secs_f64(),"new_attempts":fresh.len(),"new_native_accepted":fresh.iter().filter(|n|n.accepted).count(),"arms":summaries,"raw_decodes":stats.decodes,"peak_resident_cfa_bytes":stats.peak_resident_cfa_bytes,"disk_hits":stats.disk_hits,"memory_hits":stats.memory_hits,"photograph_rendered":false}),
    )?;
    Ok(())
}
fn main() -> Result<()> {
    let args: Vec<PathBuf> = std::env::args_os().skip(1).map(PathBuf::from).collect();
    ensure!(
        args.len() == 5,
        "focus-fit-replay PREPARED COMPACT_GUIDES CACHE PREVIOUS_ISLAND_RUN FRESH_OUTPUT"
    );
    run(&args[0], &args[1], &args[2], &args[3], &args[4])
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn source_identity_binding_ignores_json_whitespace_but_not_order_or_fields() {
        let a = vec![
            session_input::SourceIdentity {
                path: PathBuf::from("a.raw"),
                bytes: 101,
                modified_unix_nanos: Some(17),
                sha256: "a".repeat(64),
            },
            session_input::SourceIdentity {
                path: PathBuf::from("b.raw"),
                bytes: 102,
                modified_unix_nanos: None,
                sha256: "b".repeat(64),
            },
        ];
        let compact = serde_json::to_string(&a).unwrap();
        let pretty = serde_json::to_string_pretty(&a).unwrap();
        assert_ne!(compact, pretty);
        let parsed: Vec<session_input::SourceIdentity> = serde_json::from_str(&pretty).unwrap();
        require_same_sources(&a, &parsed).unwrap();
        let mut changed = a.clone();
        changed.reverse();
        assert!(require_same_sources(&a, &changed).is_err());
        for field in 0..4 {
            let mut changed = a.clone();
            match field {
                0 => changed[0].path = PathBuf::from("other.raw"),
                1 => changed[0].bytes += 1,
                2 => changed[0].modified_unix_nanos = None,
                _ => changed[0].sha256 = "c".repeat(64),
            };
            assert!(require_same_sources(&a, &changed).is_err());
        }
        assert!(require_same_sources(&a, &a[..1]).is_err());
    }
}
