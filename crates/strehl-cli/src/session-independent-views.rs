//! A collection of independently reconstructed viewpoints, never a shared warp.
//! Child renders use the normal native session consumer in their own gauges.
use crate::session_cmd::{StackArgs, reserve_output_directory, write_json_new};
use crate::session_input::{ResolvedSession, SessionMode, SessionSpec, SourceIdentity};
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::io::{BufReader, Read};
use std::path::Path;
use std::time::Instant;

const FOCUS_SEMANTICS: &str = "Acquisition ordinal within this view, not metric depth. Width and nominal prominence are descriptive shape/support, not calibrated depth uncertainty. Different views have independent coordinates and focus scales.";

fn validate_options(args: &StackArgs) -> Result<()> {
    ensure!(!args.binned, "independent views require native-size output");
    ensure!(
        args.alignment.is_none(),
        "independent views need separate alignments; omit --alignment"
    );
    ensure!(
        args.only_pass.is_none(),
        "independent views export every declared pass"
    );
    ensure!(
        !args.precision_weights && !args.reproducibility && !args.original_cfa_reconstruction,
        "independent views do not share precision, reproducibility or reconstruction observations"
    );
    ensure!(
        !args.contribution_maps,
        "independent-view bundles currently export focus evidence; omit --contribution-maps"
    );
    Ok(())
}

fn read(path: &Path) -> Result<Value> {
    let file = std::fs::File::open(path).with_context(|| format!("reading {}", path.display()))?;
    ensure!(
        file.metadata()?.len() <= 64 << 20,
        "view receipt exceeds 64MiB"
    );
    Ok(serde_json::from_reader(BufReader::new(file))?)
}

fn file_binding(path: &Path) -> Result<Value> {
    let file = std::fs::File::open(path)?;
    let bytes = file.metadata()?.len();
    ensure!(bytes > 0, "view output is empty: {}", path.display());
    let mut reader = BufReader::new(file);
    let mut hash = Sha256::new();
    let mut buffer = [0; 65536];
    loop {
        let n = reader.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        hash.update(&buffer[..n]);
    }
    Ok(json!({"bytes":bytes,"sha256":crate::session_input::hex(&hash.finalize())}))
}

fn array<const N: usize>(value: &Value, label: &str) -> Result<[usize; N]> {
    let values = value
        .as_array()
        .with_context(|| format!("missing {label}"))?;
    ensure!(values.len() == N, "invalid {label} length");
    let mut result = [0; N];
    for (out, value) in result.iter_mut().zip(values) {
        *out = value
            .as_u64()
            .and_then(|v| usize::try_from(v).ok())
            .with_context(|| format!("invalid {label} component"))?;
    }
    Ok(result)
}

/// Check both lattices explicitly. Photograph pixels use integer sensor sites;
/// focus cells use green-quad centers at 2*q+0.5, with one cell per CFA quad.
fn gauge(report: &Value, alignment: &Value, focus: &Value, count: usize) -> Result<Value> {
    let [x, y, width, height] = array::<4>(&report["canvas"], "native canvas")?;
    let [full_width, full_height] = array::<2>(
        &alignment["report"]["geometry_plane_pixels"],
        "full quad geometry",
    )?;
    ensure!(
        full_width <= u32::MAX as usize / 2 && full_height <= u32::MAX as usize / 2,
        "view geometry exceeds the native TIFF lattice"
    );
    ensure!(
        width > 0
            && height > 0
            && x.checked_add(width).is_some_and(|end| end <= full_width)
            && y.checked_add(height).is_some_and(|end| end <= full_height),
        "view canvas exceeds its geometry"
    );
    ensure!(
        alignment["report"]["sensor_pixels_per_plane_pixel"] == 2,
        "unknown view sensor lattice"
    );
    ensure!(
        focus["full_quad_geometry"] == json!([full_width, full_height])
            && focus["origin_quad"] == json!([x, y])
            && focus["dimensions"] == json!([width, height])
            && focus["step_quad"] == json!([1, 1])
            && focus["pass"] == 0,
        "view focus gauge differs from its photograph"
    );
    let reference = alignment["report"]["reference_frame"]
        .as_u64()
        .context("missing view reference")?;
    ensure!(
        reference < count as u64
            && report["reference_pass"] == 0
            && report["development_reference_pass"] == 0,
        "view references another acquisition track"
    );
    let mapping = focus["ordinal_mapping"]
        .as_array()
        .context("missing view focus source mapping")?;
    // Unplaced frames retain their original ordinals and unusable evidence;
    // never compact the focus axis or borrow identities from another view.
    ensure!(mapping.len() == count, "view focus census differs");
    let mut seen = BTreeSet::new();
    for row in mapping {
        let ordinal = row["ordinal"].as_u64().context("missing focus ordinal")?;
        let index = row["global_index"]
            .as_u64()
            .context("missing focus source")?;
        ensure!(
            ordinal == index
                && row["acquisition"].as_u64() == Some(index)
                && index < count as u64
                && seen.insert(index),
            "view focus mapping changes original acquisition ordinals"
        );
    }
    ensure!(!seen.is_empty(), "view has no focus acquisition mapping");
    Ok(json!({"full_quad_geometry":[full_width,full_height],
        "origin_sensor":[2*x,2*y],"dimensions":[2*width,2*height],"step_sensor":[1,1],
        "reference_frame":reference,"focus_origin_sensor":[2.0*x as f64+0.5,2.0*y as f64+0.5],
        "focus_dimensions":[width,height],"focus_step_sensor":[2,2],
        "scope":"independent coordinates for this view only"}))
}

fn image_dimensions(path: &Path, expected: [usize; 2]) -> Result<()> {
    let actual =
        tiff::decoder::Decoder::new(BufReader::new(std::fs::File::open(path)?))?.dimensions()?;
    ensure!(
        [actual.0 as usize, actual.1 as usize] == expected,
        "view image dimensions differ from its gauge: {}",
        path.display()
    );
    Ok(())
}

fn child_entry(
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    pass: usize,
    directory: &Path,
) -> Result<Value> {
    let track = &session.passes[pass];
    let child: ResolvedSession = serde_json::from_value(read(&directory.join("session.json"))?)?;
    ensure!(
        child.spec.mode == SessionMode::Combine
            && child.spec.primary_pass.is_none()
            && child.spec.passes == [session.spec.passes[pass].clone()]
            && child.passes.len() == 1,
        "independent view changed its declared input"
    );
    let own: Vec<SourceIdentity> =
        serde_json::from_value(read(&directory.join("source-identities.json"))?)?;
    ensure!(
        own == identities[track.global_range.clone()] && child.len() == own.len(),
        "independent view source identities differ from the parent census"
    );
    for (index, (frame, original)) in child
        .frames
        .iter()
        .zip(&session.frames[track.global_range.clone()])
        .enumerate()
    {
        ensure!(
            frame.global_index == index
                && frame.pass_index == 0
                && frame.pass_frame_index == original.pass_frame_index
                && frame.segment_index == original.segment_index
                && frame.segment_frame_index == original.segment_frame_index
                && frame.path == original.path
                && frame.bytes == original.bytes
                && frame.modified_unix_nanos == original.modified_unix_nanos,
            "independent view changed original frame order or identity"
        );
    }
    let completion = read(&directory.join("completed.json"))?;
    ensure!(
        completion["schema"] == "strehl.session-completion.v1"
            && completion["outputs"] == 1
            && completion["passes"] == 1
            && completion["frames"] == own.len(),
        "independent view is incomplete"
    );
    let report = read(&directory.join("render-report.json"))?;
    ensure!(
        report["mode"] == "combine" && report["invalid_output_pixels"] == 0,
        "independent view did not produce a complete native photograph"
    );
    let alignment = read(&directory.join("alignment.json"))?;
    let focus = read(&directory.join("focus/pass-01/geometry.json"))?;
    let gauge = gauge(&report, &alignment, &focus, own.len())?;
    let focus_evidence = read(&directory.join("focus/focus-evidence.json"))?;
    ensure!(
        focus_evidence["schema"] == "strehl.session-focus.v1"
            && focus_evidence["session"] == serde_json::to_value(&child)?
            && focus_evidence["sources"] == serde_json::to_value(&own)?
            && focus_evidence["alignment_binding"].is_string()
            && focus_evidence["alignment_binding"] == alignment["report"]["binding_sha256"]
            && focus_evidence["passes"]
                .as_array()
                .is_some_and(|passes| passes.len() == 1 && passes[0] == focus),
        "view focus binding differs from its source and geometry evidence"
    );
    for name in ["photograph.tiff", "master.tiff"] {
        image_dimensions(
            &directory.join(name),
            array::<2>(&gauge["dimensions"], "view dimensions")?,
        )?;
    }
    let binding = read(&directory.join("render-completion.json"))?;
    ensure!(
        binding["schema"] == "strehl.session-render-completion.v1"
            && binding["geometry_kind"] == "session-alignment",
        "unknown view render binding"
    );
    let mut files = BTreeMap::new();
    for name in [
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
    ] {
        files.insert(name.to_owned(), file_binding(&directory.join(name))?);
    }
    for name in ["master.tiff", "photograph.tiff", "render-report.json"] {
        ensure!(
            binding["files"][name] == files[name]["sha256"],
            "view image binding differs: {name}"
        );
    }
    for name in ["session.json", "source-identities.json", "alignment.json"] {
        ensure!(
            binding["session_files"][name] == files[name]["sha256"],
            "view geometry binding differs: {name}"
        );
    }
    ensure!(
        completion["render_bindings"]["render-completion.json"]
            == files["render-completion.json"]["sha256"],
        "view completion does not bind its render"
    );
    let receipts = focus["files"]
        .as_array()
        .context("missing view focus files")?;
    ensure!(
        !receipts.is_empty() && receipts.len() <= 64,
        "invalid view focus file count"
    );
    let mut names = BTreeSet::new();
    for receipt in receipts {
        let name = receipt["file"]
            .as_str()
            .context("missing focus file name")?;
        ensure!(
            !name.is_empty()
                && name
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'.')
                && name.ends_with(".tiff")
                && !name.contains("..")
                && names.insert(name),
            "invalid or repeated view focus file name"
        );
        let relative = format!("focus/pass-01/{name}");
        image_dimensions(
            &directory.join(&relative),
            array::<2>(&gauge["focus_dimensions"], "focus dimensions")?,
        )?;
        let actual = file_binding(&directory.join(&relative))?;
        ensure!(
            actual["sha256"] == receipt["sha256"] && actual["bytes"] == receipt["bytes"],
            "view focus binding differs: {name}"
        );
        files.insert(relative, actual);
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
        ensure!(names.contains(required), "view is missing {required}");
    }
    Ok(
        json!({"index":pass,"name":track.name,"directory":format!("view-{:02}",pass+1),
        "source_indices":track.global_range.clone().collect::<Vec<_>>(),
        "source_ids":own.iter().map(|id|&id.sha256).collect::<Vec<_>>(),"source_count":own.len(),
        "render_completion_sha256":files["render-completion.json"]["sha256"],
        "completed_sha256":files["completed.json"]["sha256"],
        "alignment_sha256":files["alignment.json"]["sha256"],
        "gauge":gauge,"focus_semantics":FOCUS_SEMANTICS,"relative_pose":null,"intrinsics":null,
        "files":files}),
    )
}

fn view_progress_context(session: &ResolvedSession, index: usize) -> Value {
    let view = &session.passes[index];
    json!({"schema":"strehl.ui-view-progress.v1", "index":index,
        "count":session.passes.len(), "name":view.name,
        "source_offset":view.global_range.start, "source_count":view.global_range.len(),
        "parent_total":session.len()})
}

pub(super) fn run(args: &StackArgs) -> Result<()> {
    validate_options(args)?;
    let session = SessionSpec::load(&args.manifest)?.resolve(&args.manifest)?;
    ensure!(
        session.spec.mode == SessionMode::IndependentViews,
        "expected independent views"
    );
    let destination = session.ensure_fresh_output(&args.out_dir)?;
    // Validate against every parent's source directory before any child can use
    // the shared original-u16 cache, including directories outside that child.
    let cache = session.ensure_output_outside_sources(
        args.resources
            .cache
            .as_deref()
            .unwrap_or(&destination.join("source-cache")),
    )?;
    let identities = session.hash_sources(true)?;
    let destination = reserve_output_directory(&session, &destination)?;
    let started = Instant::now();
    write_json_new(&destination.join("session.json"), &session)?;
    write_json_new(&destination.join("source-identities.json"), &identities)?;
    let mut views = Vec::with_capacity(session.passes.len());
    for pass in 0..session.passes.len() {
        // Child observers deliberately retain their own acquisition axis. The
        // desktop projects that axis into this explicit parent source census.
        if crate::ui_progress::Progress::new(session.len())
            .observer()
            .is_some()
        {
            eprintln!("STREHL_UI_VIEW {}", view_progress_context(&session, pass));
        }
        eprintln!(
            "session independent view {}/{}: {}",
            pass + 1,
            session.passes.len(),
            session.passes[pass].name
        );
        let spec = SessionSpec {
            mode: SessionMode::Combine,
            passes: vec![session.spec.passes[pass].clone()],
            primary_pass: None,
            ..SessionSpec::default()
        };
        let manifest = destination.join(format!("view-{:02}-input.json", pass + 1));
        write_json_new(&manifest, &spec)?;
        let mut child = args.clone();
        child.manifest = manifest;
        child.out_dir = destination.join(format!("view-{:02}", pass + 1));
        child.resources.cache = Some(cache.clone());
        child.native_single = true;
        child.focus_evidence = true;
        // Independent native processing retains each view's own WB, sensor
        // calibration, focus track and crop. No cross-view fit is attempted.
        super::run(&child)
            .with_context(|| format!("reconstructing independent view {}", pass + 1))?;
        views.push(child_entry(&session, &identities, pass, &child.out_dir)?);
    }
    let current = session
        .spec
        .resolve_from(&session.passes[0].directories[0])?;
    ensure!(
        current.frames == session.frames && current.hash_sources(true)? == identities,
        "independent-view sources changed; bundle completion withheld"
    );
    let bundle = json!({"schema":"strehl.independent-views.v1","views":views,
        "source_count":session.len(),"coordinate_scope":"independent per view",
        "focus_semantics":FOCUS_SEMANTICS,"relative_pose":null,"intrinsics":null,
        "source_identities_sha256":file_binding(&destination.join("source-identities.json"))?["sha256"],
        "session_sha256":file_binding(&destination.join("session.json"))?["sha256"]});
    write_json_new(&destination.join("bundle.json"), &bundle)?;
    let mut recipe = read(&destination.join("view-01/render-report.json"))?["recipe"].clone();
    recipe["focus_evidence"] = json!(true);
    write_json_new(
        &destination.join("render-report.json"),
        &json!({
        "schema":"strehl.session-render.v1","mode":"independent_views","view_bundle":"bundle.json",
        "build":crate::VERSION,"renderer_source_sha256":super::renderer_source_hash(),
        "views":views.len(),"sources":session.len(),"primary_pass":null,
        "recipe":recipe,
        "limitations":[FOCUS_SEMANTICS,"Relative poses, calibrated intrinsics and metric depth are not estimated by this export."]}),
    )?;
    write_json_new(
        &destination.join("completed.json"),
        &json!({
        "schema":"strehl.session-completion.v1","pipeline":"independent-views",
        "elapsed_seconds":started.elapsed().as_secs_f64(),"outputs":views.len(),
        "frames":session.len(),"passes":session.passes.len(),"primary_pass":null,
        "bundle_sha256":file_binding(&destination.join("bundle.json"))?["sha256"],
        "report_sha256":file_binding(&destination.join("render-report.json"))?["sha256"],
        "render_bindings":crate::session_reproducibility::completion_bindings(&destination)?}),
    )
}

#[cfg(test)]
#[path = "session-independent-views-tests.rs"]
mod tests;
