//! Strict import of independent viewpoints: each child keeps its own gauge.
use super::*;

fn pair(value: &Value, label: &str) -> Result<[u64; 2]> {
    let a = value
        .as_array()
        .with_context(|| format!("Missing view {label}"))?;
    ensure!(a.len() == 2, "Invalid view {label}");
    Ok([
        a[0].as_u64().context("Invalid view coordinate")?,
        a[1].as_u64().context("Invalid view coordinate")?,
    ])
}

fn gauge(
    view: &Value,
    report: &Value,
    alignment: &Value,
    focus: &Value,
    count: usize,
) -> Result<()> {
    let g = &view["gauge"];
    let full = pair(&g["full_quad_geometry"], "full geometry")?;
    let origin = pair(&g["origin_sensor"], "origin")?;
    let size = pair(&g["dimensions"], "dimensions")?;
    ensure!(
        full.iter().all(|v| *v > 0 && *v <= 100_000)
            && size.iter().all(|v| *v > 0)
            && origin.iter().chain(&size).all(|v| v.is_multiple_of(2)),
        "Invalid independent view lattice"
    );
    for axis in 0..2 {
        ensure!(
            origin[axis]
                .checked_add(size[axis])
                .is_some_and(|v| v <= 2 * full[axis]),
            "View crop exceeds full geometry"
        );
    }
    let canvas = serde_json::json!([origin[0] / 2, origin[1] / 2, size[0] / 2, size[1] / 2]);
    ensure!(
        report["canvas"] == canvas
            && report["mode"] == "combine"
            && report["reference_pass"] == 0
            && report["development_reference_pass"] == 0
            && report["invalid_output_pixels"] == 0,
        "Independent view render gauge differs"
    );
    ensure!(
        g["step_sensor"] == serde_json::json!([1, 1])
            && g["focus_dimensions"] == serde_json::json!([size[0] / 2, size[1] / 2])
            && g["focus_origin_sensor"]
                == serde_json::json!([origin[0] as f64 + 0.5, origin[1] as f64 + 0.5])
            && g["focus_step_sensor"] == serde_json::json!([2, 2]),
        "View focus and photo lattices differ"
    );
    let reference = g["reference_frame"]
        .as_u64()
        .context("View reference missing")?;
    ensure!(
        reference < count as u64
            && alignment["report"]["reference_frame"] == reference
            && alignment["report"]["geometry_plane_pixels"] == g["full_quad_geometry"]
            && alignment["report"]["sensor_pixels_per_plane_pixel"] == 2,
        "View alignment gauge differs"
    );
    ensure!(
        focus["full_quad_geometry"] == g["full_quad_geometry"]
            && focus["origin_quad"] == serde_json::json!([origin[0] / 2, origin[1] / 2])
            && focus["dimensions"] == g["focus_dimensions"]
            && focus["step_quad"] == serde_json::json!([1, 1])
            && focus["pass"] == 0,
        "View focus coordinates differ"
    );
    let rows = focus["ordinal_mapping"]
        .as_array()
        .context("View focus identity mapping missing")?;
    ensure!(
        !rows.is_empty() && rows.len() == count,
        "Invalid view focus identity count"
    );
    let mut seen = std::collections::BTreeSet::new();
    for row in rows {
        let ordinal = row["ordinal"]
            .as_u64()
            .context("View focus ordinal missing")?;
        ensure!(
            ordinal < count as u64
                && row["global_index"] == ordinal
                && row["acquisition"] == ordinal
                && seen.insert(ordinal),
            "View focus ordinals changed"
        );
    }
    ensure!(
        view.get("relative_pose") == Some(&Value::Null)
            && view.get("intrinsics") == Some(&Value::Null)
            && view["focus_semantics"]
                .as_str()
                .is_some_and(|s| !s.is_empty() && s.len() <= 4096),
        "Unknown independent-view geometry semantics"
    );
    Ok(())
}

pub(super) fn load(
    root: &Path,
    completion: &Value,
    resolved: &Value,
    spec: strehl_cli::session_input::SessionSpec,
    identities: &[strehl_cli::session_input::SourceIdentity],
    mut files: BTreeMap<String, String>,
    cancelled: &AtomicBool,
) -> Result<Run> {
    ensure!(
        completion["pipeline"] == "independent-views" && completion["outputs"] == spec.passes.len(),
        "Independent view completion is incomplete"
    );
    for (name, key) in [
        ("bundle.json", "bundle_sha256"),
        ("render-report.json", "report_sha256"),
    ] {
        bind(
            root,
            name,
            Some(valid_digest(&completion[key])?),
            &mut files,
            cancelled,
        )?;
    }
    let bundle = read(root, "bundle.json", &mut files)?;
    let parent_report = read(root, "render-report.json", &mut files)?;
    ensure!(
        bundle["schema"] == "strehl.independent-views.v1"
            && bundle["source_count"] == identities.len()
            && bundle.get("relative_pose") == Some(&Value::Null)
            && bundle.get("intrinsics") == Some(&Value::Null)
            && parent_report["mode"] == "independent_views"
            && parent_report["view_bundle"] == "bundle.json",
        "Unsupported independent view bundle"
    );
    for (name, key) in [
        ("session.json", "session_sha256"),
        ("source-identities.json", "source_identities_sha256"),
    ] {
        bind(
            root,
            name,
            Some(valid_digest(&bundle[key])?),
            &mut files,
            cancelled,
        )?;
    }
    let views = bundle["views"]
        .as_array()
        .context("Independent views missing")?;
    let render_bindings = completion["render_bindings"]
        .as_object()
        .context("View render bindings missing")?;
    ensure!(
        views.len() == spec.passes.len() && render_bindings.len() == views.len(),
        "Independent view count differs"
    );
    let mut first = None;
    let mut recipe = None;
    let mut offset = 0;
    for (index, (view, pass)) in views.iter().zip(&spec.passes).enumerate() {
        let directory = format!("view-{:02}", index + 1);
        let prefix = format!("{directory}/");
        let child_root = root.join(&directory).canonicalize()?;
        ensure!(
            child_root.starts_with(root) && child_root.is_dir(),
            "View directory escapes its bundle"
        );
        let end = usize::try_from(
            resolved["passes"][index]["global_range"]["end"]
                .as_u64()
                .context("View source end missing")?,
        )?;
        let count = end
            .checked_sub(offset)
            .context("View source range reversed")?;
        ensure!(
            count > 0
                && offset
                    .checked_add(count)
                    .is_some_and(|v| v <= identities.len()),
            "View sources exceed parent"
        );
        let ids = &identities[offset..offset + count];
        ensure!(
            view["index"] == index
                && view["name"] == pass.name
                && view["directory"] == directory
                && view["source_count"] == count
                && view["source_indices"]
                    == serde_json::json!((offset..offset + count).collect::<Vec<_>>())
                && view["source_ids"]
                    == serde_json::json!(ids.iter().map(|v| &v.sha256).collect::<Vec<_>>()),
            "View source membership differs"
        );
        let payload = view["files"]
            .as_object()
            .context("View file bindings missing")?;
        ensure!(
            !payload.is_empty() && payload.len() <= 96,
            "View file census exceeds bound"
        );
        for required in [
            "session.json",
            "source-identities.json",
            "completed.json",
            "render-completion.json",
            "alignment.json",
            "calibration.json",
            "master.tiff",
            "photograph.tiff",
            "render-report.json",
            "focus/focus-evidence.json",
            "focus/pass-01/geometry.json",
            "focus/pass-01/ordinal.tiff",
            "focus/pass-01/width-frames.tiff",
            "focus/pass-01/flags.tiff",
            "focus/pass-01/usable.tiff",
            "focus/pass-01/raw-coverage.tiff",
            "focus/pass-01/focus-coverage.tiff",
            "focus/pass-01/source-rank-1.tiff",
        ] {
            ensure!(
                payload.contains_key(required),
                "View missing required artifact: {required}"
            );
        }
        for (name, binding) in payload {
            let relative = format!("{prefix}{name}");
            // bind validates every relative component and canonical containment before reading.
            bind(
                root,
                &relative,
                Some(valid_digest(&binding["sha256"])?),
                &mut files,
                cancelled,
            )?;
            ensure!(
                binding["bytes"].as_u64() == Some(root.join(&relative).metadata()?.len()),
                "View artifact byte count differs"
            );
        }
        for (name, key) in [
            ("render-completion.json", "render_completion_sha256"),
            ("completed.json", "completed_sha256"),
            ("alignment.json", "alignment_sha256"),
        ] {
            ensure!(
                view[key] == payload[name]["sha256"],
                "View receipt identity differs"
            );
        }
        ensure!(
            render_bindings.get(&format!("{prefix}render-completion.json"))
                == Some(&view["render_completion_sha256"]),
            "Parent omits view render binding"
        );
        let child_resolved = read(root, &format!("{prefix}session.json"), &mut files)?;
        let child_spec: strehl_cli::session_input::SessionSpec =
            serde_json::from_value(child_resolved["spec"].clone())?;
        ensure!(
            child_spec.mode == SessionMode::Combine
                && child_spec.primary_pass.is_none()
                && child_spec.passes == [pass.clone()],
            "View child is not its independent single pass"
        );
        let child_ids: Vec<strehl_cli::session_input::SourceIdentity> = serde_json::from_value(
            read(root, &format!("{prefix}source-identities.json"), &mut files)?,
        )?;
        ensure!(
            child_ids == ids,
            "Child original identities differ from parent"
        );
        let report = read(root, &format!("{prefix}render-report.json"), &mut files)?;
        let alignment = read(root, &format!("{prefix}alignment.json"), &mut files)?;
        let focus = read(
            root,
            &format!("{prefix}focus/pass-01/geometry.json"),
            &mut files,
        )?;
        gauge(view, &report, &alignment, &focus, count)?;
        let summary = read(
            root,
            &format!("{prefix}focus/focus-evidence.json"),
            &mut files,
        )?;
        ensure!(
            summary["schema"] == "strehl.session-focus.v1"
                && summary["session"] == child_resolved
                && summary["sources"] == serde_json::to_value(&child_ids)?
                && summary["alignment_binding"].is_string()
                && summary["alignment_binding"] == alignment["report"]["binding_sha256"]
                && summary["passes"] == serde_json::json!([focus.clone()]),
            "View focus evidence differs from original identities or geometry"
        );
        let maps = focus["files"]
            .as_array()
            .context("View focus maps missing")?;
        ensure!(
            !maps.is_empty() && maps.len() <= 64,
            "View focus maps exceed bound"
        );
        let mut names = std::collections::BTreeSet::new();
        for map in maps {
            let name = map["file"].as_str().context("View focus name missing")?;
            ensure!(
                !name.is_empty()
                    && !name.contains("..")
                    && name.ends_with(".tiff")
                    && name
                        .bytes()
                        .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'.')
                    && names.insert(name),
                "Invalid view focus file name"
            );
            let declared = payload
                .get(&format!("focus/pass-01/{name}"))
                .context("View bundle omits a declared focus map")?;
            ensure!(
                declared["sha256"] == map["sha256"] && declared["bytes"] == map["bytes"],
                "View focus map differs from bundle identity"
            );
        }
        for required in [
            "ordinal.tiff",
            "width-frames.tiff",
            "flags.tiff",
            "usable.tiff",
            "raw-coverage.tiff",
            "focus-coverage.tiff",
            "source-rank-1.tiff",
        ] {
            ensure!(
                names.contains(required),
                "View focus summary omits {required}"
            );
        }
        if let Some(previous) = &recipe {
            ensure!(
                previous == &report["recipe"],
                "Views use different saved merge recipes"
            );
        } else {
            recipe = Some(report["recipe"].clone());
        }
        // Reuse normal completed-single-pass validation, including full TIFFs,
        // original order, render hashes and one scalar diagnostic at a time.
        let child = super::load(&child_root, cancelled)?;
        let provenance = child.imported.as_ref().context("View provenance missing")?;
        ensure!(
            provenance.renderer_bound && provenance.diagnostic_warnings.is_empty(),
            "View is unbound or has unavailable diagnostics"
        );
        for (name, digest) in &provenance.files {
            let key = format!("{prefix}{name}");
            if let Some(previous) = files.insert(key, digest.clone()) {
                ensure!(previous == *digest, "View changed during import");
            }
        }
        if first.is_none() {
            first = Some(child);
        }
        offset += count;
    }
    ensure!(
        offset == identities.len(),
        "Views do not cover original census"
    );
    let mut parent_recipe = recipe.context("View recipe missing")?;
    parent_recipe["focus_evidence"] = serde_json::json!(true);
    ensure!(
        parent_report["recipe"] == parent_recipe,
        "Bundle recipe differs from its views"
    );
    let mut run = first.context("Empty independent view bundle")?;
    let sources = identities
        .iter()
        .map(|id| SourceIdentity {
            path: id.path.clone(),
            bytes: id.bytes,
            modified_ns: id.modified_unix_nanos.map(u128::from),
        })
        .collect::<Vec<_>>();
    let mut draft = run.settings.session.take().context("View recipe missing")?;
    draft.manifest = spec;
    draft.sources = sources.clone();
    draft.normalize_mode_options();
    draft.validate()?;
    run.settings.session = Some(draft);
    let provenance = ImportedSession {
        imported_at: crate::workspace_history::timestamp(),
        renderer_bound: true,
        renderer_build: parent_report["build"].as_str().map(str::to_owned),
        files,
        diagnostic_warnings: Vec::new(),
    };
    verify(root, &provenance, cancelled)?;
    run.directory = root.to_path_buf();
    run.output = root.join("view-01/photograph.tiff");
    run.log = root.join("completed.json");
    run.label = format!(
        "Imported CLI · {}",
        root.file_name().unwrap_or_default().to_string_lossy()
    );
    run.created = provenance.imported_at;
    run.frames = sources.len();
    run.sources = sources;
    run.imported = Some(provenance);
    Ok(run)
}

#[cfg(test)]
#[path = "session-import-views-tests.rs"]
pub(super) mod tests;
