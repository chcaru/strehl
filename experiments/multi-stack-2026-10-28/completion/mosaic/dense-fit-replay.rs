//! Saved-measurement research only: no source decode and no image output.
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    time::Instant,
};
use strehl_cli::{session_cache, session_focus, session_input, session_sampling};
use strehl_core::{align::Similarity, warpmap::WarpMap};
#[path = "geometry-replay.rs"]
mod common;
pub(crate) use common::session_mosaic_geometry;
use common::{guide, hash, read, save};
use session_mosaic_geometry::{
    MatchRole, MosaicBinding, MosaicGeometry, MosaicGuide, NativeCorrespondence,
};
#[path = "dense-fit-math.rs"]
mod math;
#[cfg(test)]
#[path = "dense-fit-tests.rs"]
mod tests;

fn rows(native: &[NativeCorrespondence], role: MatchRole) -> Result<Vec<math::Row>> {
    let mut rows = Vec::new();
    for n in native
        .iter()
        .filter(|n| n.accepted && n.candidate.role == role)
    {
        ensure!(
            n.candidate.pass_a == 0 && n.candidate.pass_b == 1,
            "unexpected pass direction"
        );
        let f = n
            .forward_rms_quad
            .context("accepted forward residual absent")?;
        let r = n
            .reverse_rms_quad
            .context("accepted reverse residual absent")?;
        ensure!(
            f.is_finite()
                && r.is_finite()
                && f <= 0.5
                && r <= 0.5
                && n.reciprocal_error_quad
                    .is_some_and(|v| v.is_finite() && v <= 0.5),
            "accepted observation exceeds fixed native bars"
        );
        rows.push(math::Row {
            id: n.candidate.id.clone(),
            a: n.candidate.point_a_quad,
            b: n.refined_b_quad.context("accepted point absent")?,
            bounds: n.support_bounds_quad.context("accepted support absent")?,
            priority: f64::from(f.max(r)),
        });
    }
    ensure!(rows.len() <= 4096, "saved-row working bound exceeded");
    Ok(rows)
}
fn run(pilot: &Path, compact: &Path, previous: &Path, out: &Path) -> Result<()> {
    let started = Instant::now();
    let session: session_input::ResolvedSession = read(&pilot.join("session.json"))?;
    let ids: Vec<session_input::SourceIdentity> = read(&pilot.join("source-identities.json"))?;
    let bound: MosaicBinding = read(&previous.join("binding.json"))?;
    ensure!(bound.sources == ids, "saved source identity differs");
    let guides = (0..2)
        .map(|pass| guide(compact, pilot, pass, &session))
        .collect::<Result<Vec<_>>>()?;
    ensure!(
        serde_json::to_value(session_mosaic_geometry::binding(
            &session,
            &ids,
            &guides,
            &bound.config
        )?)? == serde_json::to_value(&bound)?,
        "saved algorithm/config/maps/guides binding differs"
    );
    let out = session.ensure_output_outside_sources(out)?;
    std::fs::create_dir(&out)?;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    save(
        &out.join("binding.json"),
        &json!({"schema":"strehl.dense-fit-model-development.v1","previous":previous,"previous_binding_sha256":hash(&previous.join("binding.json"))?,"protocol_sha256":common::hash_bytes(include_str!("dense-fit-protocol.md").as_bytes()),"workers":4,"max_work_bytes":4usize<<30,"raw_reads":false,"known_scene_only":true,"models":{"spacing_quad":[512,256,128],"smoothness":[2.0,0.2,0.02],"tether":0.01,"huber":0.5,"irls":6},"upstream_condition":"frozen original per-pass maps, source nominations, accepted native receipts and focus evidence; not photon-blind assessment of upstream estimators"}),
    )?;
    let mut outcomes = Vec::new();
    for name in ["mixed-control", "focused-only", "augmented"] {
        let prior = previous.join(name);
        let directory = out.join(name);
        std::fs::create_dir(&directory)?;
        let geometry = MosaicGeometry::load(
            &prior.join("geometry.json"),
            &session,
            &ids,
            &guides,
            &bound.config,
        )?;
        let native: Vec<NativeCorrespondence> = read(&prior.join("native-measurements.json"))?;
        ensure!(
            serde_json::to_value(&native)?
                == serde_json::to_value(&geometry.report.native_receipts)?,
            "native file differs from reconstructed bound geometry"
        );
        let independent = session_mosaic_geometry::independent_native_constraints(&native, 2, 0.5)?;
        let independent_held: Vec<_> = independent
            .receipt_indices
            .iter()
            .filter(|&&i| native[i].candidate.role == MatchRole::Heldout)
            .map(|&i| native[i].clone())
            .collect();
        let fit = rows(&native, MatchRole::Fit)?;
        let held = rows(&independent_held, MatchRole::Heldout)?;
        ensure!(
            fit.iter()
                .all(|r| held.iter().all(|h| !math::overlap(r, h))),
            "dense training overlaps prior held support"
        );
        save(
            &directory.join("input.json"),
            &json!({"geometry_sha256":hash(&prior.join("geometry.json"))?,"native_sha256":hash(&prior.join("native-measurements.json"))?,"accepted_fit_rows":fit.len(),"independent_fit_control":geometry.report.fit_observations,"independent_held":held.len(),"all_dense_fit_support_disjoint_from_external_held":true}),
        )?;
        let (selection, cv) = pool.install(|| math::cv(&fit, &guides));
        save(&directory.join("fit-only-cv.json"), &cv)?;
        let Some((spacing, smoothness)) = selection else {
            let outcome = json!({"arm":name,"refusal":"no model completed every predefined FIT fold","models_retained":cv.len()});
            save(&directory.join("outcome.json"), &outcome)?;
            outcomes.push(outcome);
            continue;
        };
        // Selection is frozen before the external held values enter any error.
        save(
            &directory.join("selection.json"),
            &json!({"spacing_quad":spacing,"smoothness":smoothness,"fit_cv_sha256":hash(&directory.join("fit-only-cv.json"))?,"external_held_consulted":false}),
        )?;
        let evaluated = (|| -> Result<Value> {
            let train = math::training(&fit)?;
            let model = math::fit(&train, &guides, spacing, smoothness)?;
            let train_errors = math::errors(&model, &train.rows)?;
            let held_errors = math::errors(&model, &held)?;
            save(&directory.join("training.json"), &train.receipt)?;
            save(&directory.join("held-errors.json"),&held.iter().zip(&held_errors).map(|(r,e)|json!({"id":r.id,"point_a_quad":r.a,"point_b_quad":r.b,"symmetric_native_error_quad":e[0],"common_gauge_error_quad":e[1]})).collect::<Vec<_>>())?;
            save(&directory.join("diagnostic-vertices.json"),&model.meshes.iter().map(|m|json!({"source_quad":[m.source.width,m.source.height],"columns":m.columns,"rows":m.rows,"vertices_quad":m.vertices,"join_certificate":"none"})).collect::<Vec<_>>())?;
            Ok(
                json!({"arm":name,"spacing_quad":spacing,"smoothness":smoothness,"coherent_fit_rows":train.rows.len(),"independent_fit_count":train.independent,"train":math::summary(&train_errors,&train.weights),"held":math::summary(&held_errors,&vec![1.;held.len()]),"core_fit_rms_quad":model.fit_rms,"maximum_displacement_quad":model.maximum_displacement,"scope":"known-scene diagnostic; no new join qualification or photographic claim"}),
            )
        })();
        let outcome = match evaluated {
            Ok(v) => v,
            Err(e) => {
                json!({"arm":name,"selected_spacing_quad":spacing,"selected_smoothness":smoothness,"refusal":format!("{e:#}")})
            }
        };
        save(&directory.join("outcome.json"), &outcome)?;
        outcomes.push(outcome);
    }
    save(
        &out.join("outcome.json"),
        &json!({"elapsed_seconds":started.elapsed().as_secs_f64(),"arms":outcomes,"source_reads":0,"photograph_rendered":false}),
    )?;
    Ok(())
}
fn main() -> Result<()> {
    let args: Vec<PathBuf> = std::env::args_os().skip(1).map(PathBuf::from).collect();
    ensure!(
        args.len() == 4,
        "dense-fit-replay PREPARED COMPACT_GUIDES FOCUSED_FIT_RUN FRESH_OUTPUT"
    );
    run(&args[0], &args[1], &args[2], &args[3])
}
