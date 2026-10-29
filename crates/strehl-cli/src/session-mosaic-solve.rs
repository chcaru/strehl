use super::{
    MatchRole, MosaicBinding, MosaicGeometryConfig, MosaicGuide, NativeCorrespondence,
    PairDiscovery, binding, load_bound, save_bound,
};
use crate::session_input::{ResolvedSession, SourceIdentity};
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;
use strehl_core::align::{AlignEdge, Cx, GlobalOptions, Similarity, solve_global_in_component};
use strehl_core::mosaic::{
    BackwardMesh, Bounds, CanvasLimits, Correspondence, FocusEvidence, ForwardMesh, IndexLimits,
    LoopWitness, MeshFitOptions, MeshValidation, MosaicCanvas, ObservationRole, Visibility,
    fit_meshes, validate_observations,
};
use strehl_core::plane::PlaneGeometry;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MosaicGeometryReport {
    pub coordinate_gauge: String,
    pub geometry_reference_pass: usize,
    pub primary_policy: String,
    pub pass_count: usize,
    pub measured_pass_edges: usize,
    pub pass_cycle_rank: usize,
    pub candidate_count: usize,
    pub native_accepted: usize,
    /// Exact receipts retained after same-site agreement and physical support
    /// independence, in the same order as the consuming sparse equations.
    #[serde(default)]
    pub independent_site_ids: Vec<String>,
    pub fit_observations: usize,
    pub heldout_observations: usize,
    pub independently_measured_reciprocal_loops: usize,
    pub maximum_heldout_error_quad: f64,
    pub maximum_reciprocal_loop_error_quad: f64,
    pub fit_rms_quad: f64,
    pub maximum_local_displacement_quad: f64,
    pub fit_reservation_bytes: usize,
    pub canvas_origin_quad: [i64; 2],
    pub canvas_size_quad: [usize; 2],
    pub pass_cell_status: Vec<Vec<String>>,
    pub qualified_join_cells: Vec<usize>,
    #[serde(default)]
    pub join_support: Vec<JoinSupportRecord>,
    pub discovery: Vec<PairDiscovery>,
    pub native_receipts: Vec<NativeCorrespondence>,
    pub visibility_contract: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct JoinSupportRecord {
    pub pass: usize,
    pub cell: usize,
    pub witness_count: usize,
    pub hull_quad: Vec<[f64; 2]>,
    pub area_fraction: f64,
    pub span_fraction: [f64; 2],
    pub qualified: bool,
}

pub struct MosaicGeometry {
    pub canvas: MosaicCanvas,
    /// Measured/fitted view geometry. Only ValidatedOverlap cells may support
    /// cross-view averaging; SingleView is explicitly not a join certificate.
    pub meshes: Vec<ForwardMesh>,
    /// Complete measured global geometry for explicit original-view comparison
    /// arms. A consumer must certify transition boundaries or exclude them before
    /// substituting this for local geometry. It is not a primary fallback.
    pub original_view_meshes: Vec<ForwardMesh>,
    pub report: MosaicGeometryReport,
    pub binding: MosaicBinding,
}

fn point(t: Similarity, p: [f64; 2], g: PlaneGeometry) -> [f64; 2] {
    let p = t.apply_at(p[0], p[1], g.width as f64 * 0.5, g.height as f64 * 0.5);
    [p.0, p.1]
}
fn name(status: Visibility) -> &'static str {
    match status {
        Visibility::SingleView => "single_view",
        Visibility::ValidatedOverlap => "validated_overlap",
        Visibility::Unverified => "unverified",
        Visibility::AmbiguousFocus => "ambiguous_focus",
        Visibility::Disoccluded => "disoccluded",
        Visibility::HeldoutFailure => "heldout_failure",
        Visibility::LoopFailure => "loop_failure",
        Visibility::Fold => "fold",
        Visibility::ExcessiveStretch => "excessive_stretch",
    }
}
fn visibility(name: &str) -> Result<Visibility> {
    Ok(match name {
        "single_view" => Visibility::SingleView,
        "validated_overlap" => Visibility::ValidatedOverlap,
        "unverified" => Visibility::Unverified,
        "ambiguous_focus" => Visibility::AmbiguousFocus,
        "disoccluded" => Visibility::Disoccluded,
        "heldout_failure" => Visibility::HeldoutFailure,
        "loop_failure" => Visibility::LoopFailure,
        "fold" => Visibility::Fold,
        "excessive_stretch" => Visibility::ExcessiveStretch,
        _ => anyhow::bail!("unknown mosaic cell visibility"),
    })
}

pub struct NativeConstraintSet {
    pub observations: Vec<Correspondence>,
    pub loops: Vec<LoopWitness>,
    /// Indices in the caller's complete native receipt list, including refusals.
    pub receipt_indices: Vec<usize>,
}

/// Reuse the production physical-support and same-site selection for audits.
/// This does not remeasure images or upgrade a refused native correspondence.
pub fn independent_native_constraints(
    native: &[NativeCorrespondence],
    passes: usize,
    agreement_bar: f64,
) -> Result<NativeConstraintSet> {
    let mut observations = Vec::new();
    let mut loops = Vec::new();
    let mut supports = Vec::new();
    let mut priorities = Vec::new();
    let mut receipt_indices = Vec::new();
    let mut ids = BTreeSet::new();
    for (receipt_index, receipt) in native.iter().enumerate() {
        let c = &receipt.candidate;
        ensure!(
            ids.insert(&c.id)
                && c.pass_a < passes
                && c.pass_b < passes
                && c.pass_a != c.pass_b
                && c.point_a_quad
                    .into_iter()
                    .chain(c.point_b_quad)
                    .all(f64::is_finite),
            "invalid/duplicate native mosaic correspondence identity"
        );
        if !receipt.accepted {
            continue;
        }
        let b = receipt
            .refined_b_quad
            .context("accepted native correspondence lacks point")?;
        ensure!(
            b.into_iter().all(f64::is_finite)
                && receipt.refusal.is_none()
                && receipt.forward_tiles >= 6
                && receipt.reverse_tiles >= 6
                && receipt.reserved_dependency_checked
                && c.spatial_roles_match,
            "malformed accepted native mosaic correspondence"
        );
        let reciprocal = receipt
            .reciprocal_error_quad
            .context("native correspondence lacks reciprocal evidence")?;
        ensure!(
            reciprocal.is_finite() && reciprocal >= 0.0,
            "invalid native reciprocal error"
        );
        let bounds = receipt
            .support_bounds_quad
            .context("accepted native correspondence lacks actual support bounds")?;
        ensure!(
            bounds
                .iter()
                .all(|b| b.iter().flatten().all(|v| v.is_finite())
                    && b[0][0] <= b[1][0]
                    && b[0][1] <= b[1][1]),
            "invalid native support bounds"
        );
        supports.push(bounds);
        receipt_indices.push(receipt_index);
        priorities.push(
            receipt
                .forward_rms_quad
                .unwrap_or(f32::INFINITY)
                .max(receipt.reverse_rms_quad.unwrap_or(f32::INFINITY)),
        );
        observations.push(Correspondence {
            pass_a: c.pass_a,
            point_a: c.point_a_quad,
            pass_b: c.pass_b,
            point_b: b,
            weight: 1.0,
            role: if c.role == MatchRole::Fit {
                ObservationRole::Fit
            } else {
                ObservationRole::Heldout
            },
        });
        loops.push(LoopWitness {
            pass: c.pass_a,
            source: c.point_a_quad,
            error: reciprocal,
        });
        loops.push(LoopWitness {
            pass: c.pass_b,
            source: b,
            error: reciprocal,
        });
    }
    // Alternative originals at one nominated site are repeated evidence, not
    // additional geometric locations. Conflicting accepted alternatives leave
    // the site unsupported; agreeing alternatives contribute only once.
    let mut groups: BTreeMap<(usize, usize, [u64; 2]), Vec<usize>> = BTreeMap::new();
    for (i, o) in observations.iter().enumerate() {
        groups
            .entry((o.pass_a, o.pass_b, o.point_a.map(f64::to_bits)))
            .or_default()
            .push(i);
    }
    let mut keep = BTreeSet::new();
    for indices in groups.values() {
        let coherent = indices.iter().all(|&i| {
            indices.iter().all(|&j| {
                let a = &observations[i];
                let b = &observations[j];
                a.role == b.role
                    && (a.point_b[0] - b.point_b[0]).hypot(a.point_b[1] - b.point_b[1])
                        <= agreement_bar
            })
        });
        if coherent {
            keep.insert(indices[0]);
        }
    }
    // A nearby feature or another focus original is not an independent physical
    // patch. Select a deterministic nonoverlapping subset in both pass gauges.
    // FIT evidence takes precedence; heldout selection never changes the fit.
    let mut ordered: Vec<_> = keep.iter().copied().collect();
    ordered.sort_by(|&a, &b| {
        usize::from(observations[a].role == ObservationRole::Heldout)
            .cmp(&usize::from(
                observations[b].role == ObservationRole::Heldout,
            ))
            .then(priorities[a].total_cmp(&priorities[b]))
            .then(a.cmp(&b))
    });
    keep.clear();
    for index in ordered {
        let overlaps = keep.iter().any(|&previous| {
            let a = &observations[index];
            let b = &observations[previous];
            a.pass_a == b.pass_a
                && a.pass_b == b.pass_b
                && (0..2).any(|pass| {
                    let x = supports[index][pass];
                    let y = supports[previous][pass];
                    x[0][0] <= y[1][0]
                        && y[0][0] <= x[1][0]
                        && x[0][1] <= y[1][1]
                        && y[0][1] <= x[1][1]
                })
        });
        if !overlaps {
            keep.insert(index);
        }
    }
    Ok(NativeConstraintSet {
        observations: observations
            .into_iter()
            .enumerate()
            .filter_map(|(i, o)| keep.contains(&i).then_some(o))
            .collect(),
        loops: loops
            .into_iter()
            .enumerate()
            .filter_map(|(i, l)| keep.contains(&(i / 2)).then_some(l))
            .collect(),
        receipt_indices: receipt_indices
            .into_iter()
            .enumerate()
            .filter_map(|(i, index)| keep.contains(&i).then_some(index))
            .collect(),
    })
}

fn seed_mesh(
    guide: &MosaicGuide,
    pose: Similarity,
    config: &MosaicGeometryConfig,
) -> Result<ForwardMesh> {
    let source = guide.source_geometry;
    let columns = source.width.div_ceil(config.mesh_cell_quad_pixels) + 1;
    let rows = source.height.div_ceil(config.mesh_cell_quad_pixels) + 1;
    let forward = pose.invert().context("singular mosaic pass pose")?;
    let mut vertices = Vec::with_capacity(columns * rows);
    let mut focus = Vec::with_capacity(columns * rows);
    for y in 0..rows {
        for x in 0..columns {
            let p = [
                (source.width - 1) as f64 * x as f64 / (columns - 1) as f64,
                (source.height - 1) as f64 * y as f64 / (rows - 1) as f64,
            ];
            vertices.push(point(forward, p, source));
            let gx = ((p[0] - guide.origin[0]) / guide.step as f64).round();
            let gy = ((p[1] - guide.origin[1]) / guide.step as f64).round();
            if gx >= 0.0
                && gy >= 0.0
                && gx < guide.geometry.width as f64
                && gy < guide.geometry.height as f64
            {
                let i = gy as usize * guide.geometry.width + gx as usize;
                focus.push(FocusEvidence {
                    ordinal: guide.focus_ordinal[i],
                    width: guide.focus_width[i],
                    usable: guide.usable_focus[i],
                });
            } else {
                focus.push(FocusEvidence {
                    ordinal: 0.0,
                    width: 0.0,
                    usable: false,
                });
            }
        }
    }
    Ok(ForwardMesh::new(
        source,
        columns,
        rows,
        vertices,
        vec![Visibility::SingleView; (columns - 1) * (rows - 1)],
        focus,
    )?)
}

fn solve_unbound(
    guides: &[MosaicGuide],
    discovery: &[PairDiscovery],
    native: &[NativeCorrespondence],
    config: &MosaicGeometryConfig,
    budget: usize,
) -> Result<(
    MosaicCanvas,
    Vec<ForwardMesh>,
    Vec<ForwardMesh>,
    MosaicGeometryReport,
)> {
    let role_bytes = config.role_work_bytes()?;
    let fit_budget = budget
        .checked_sub(role_bytes)
        .context("frozen role plan exceeds mesh budget")?;
    config.validate()?;
    ensure!(guides.len() >= 2, "mosaic solve needs two passes");
    let g = guides[0].source_geometry;
    for (pass, guide) in guides.iter().enumerate() {
        guide.validate()?;
        ensure!(
            guide.pass == pass && guide.source_geometry == g,
            "mosaic solve pass gauge differs"
        );
    }
    let NativeConstraintSet {
        observations,
        loops,
        receipt_indices,
    } = independent_native_constraints(native, guides.len(), config.maximum_reciprocal_error)?;
    type PairPoints = BTreeMap<(usize, usize), Vec<([f64; 2], [f64; 2])>>;
    let mut by_pair: PairPoints = BTreeMap::new();
    for observation in &observations {
        if observation.role == ObservationRole::Fit {
            by_pair
                .entry((observation.pass_a, observation.pass_b))
                .or_default()
                .push((observation.point_a, observation.point_b));
        }
    }
    let mut edges = Vec::new();
    for ((a, b), points) in by_pair {
        if points.len() < config.minimum_pair_matches {
            continue;
        }
        let Some(model) = super::matching::fit_similarity(&points) else {
            continue;
        };
        let centre = [g.width as f64 * 0.5, g.height as f64 * 0.5];
        let t = Similarity {
            a: Cx::new(model[0], model[1]),
            b: Cx::new(
                model[2] + model[0] * centre[0] - model[1] * centre[1] - centre[0],
                model[3] + model[1] * centre[0] + model[0] * centre[1] - centre[1],
            ),
        };
        let rms = (points
            .iter()
            .map(|&(p, q)| {
                let predicted = point(t, p, g);
                (predicted[0] - q[0]).powi(2) + (predicted[1] - q[1]).powi(2)
            })
            .sum::<f64>()
            / points.len() as f64)
            .sqrt();
        edges.push(AlignEdge {
            i: a,
            j: b,
            t,
            rms,
            used: points.len(),
            lever: 0.25 * (g.width as f64).hypot(g.height as f64),
        });
    }
    let poses = solve_global_in_component(&edges, guides.len(), &GlobalOptions::new(g), 0)
        .context("mosaic global measured graph is singular")?;
    ensure!(
        poses.iter().all(Option::is_some),
        "mosaic measured pass graph is disconnected; retain separate layers"
    );
    let seeds: Vec<_> = guides
        .iter()
        .zip(poses)
        .map(|(guide, pose)| seed_mesh(guide, pose.expect("checked"), config))
        .collect::<Result<_>>()?;
    let options = MeshFitOptions {
        max_work_bytes: fit_budget,
        ..MeshFitOptions::default()
    };
    let (mut meshes, fit) = fit_meshes(&seeds, &observations, options)?;
    let policy = MeshValidation {
        maximum_heldout_error: config.maximum_native_residual,
        maximum_loop_error: config.maximum_reciprocal_error,
        ..MeshValidation::default()
    };
    let validation = validate_observations(&mut meshes, &observations, &loops, policy)?;
    for mesh in &mut meshes {
        let backward = BackwardMesh::new(
            mesh,
            policy,
            IndexLimits {
                bin_side: 64,
                max_bins: config.max_canvas_pixels / 4096 + config.max_canvas_side * 2,
                max_entries: 10_000_000,
            },
        )?;
        for (cell, visibility) in mesh.visibility.iter_mut().enumerate() {
            *visibility = backward
                .cell_visibility(cell)
                .context("compiled mosaic cell missing")?;
        }
    }
    let bounds: Vec<_> = meshes
        .iter()
        .chain(&seeds)
        .map(|mesh| {
            let b = mesh.bounds();
            Bounds {
                min: b.min,
                max: [b.max[0] + 1.0, b.max[1] + 1.0],
            }
        })
        .collect();
    let canvas = MosaicCanvas::from_bounds(
        &bounds,
        CanvasLimits {
            max_side: config.max_canvas_side,
            max_pixels: config.max_canvas_pixels,
        },
    )?;
    let report = MosaicGeometryReport { coordinate_gauge: "signed canvas origin; native green-quad pixels; sensor pixels = 2*quad; guide centres at active sensor (2x+.5,2y+.5)".into(),
        geometry_reference_pass: 0, primary_policy: "none; geometry gauge is not appearance or fallback preference".into(),
        pass_count: guides.len(), measured_pass_edges: edges.len(), pass_cycle_rank: edges.len() + 1 - guides.len(),
        candidate_count: native.len(), native_accepted: observations.len(), fit_observations: validation.fit_observations,
        independent_site_ids: receipt_indices.iter().map(|&i| native[i].candidate.id.clone()).collect(),
        heldout_observations: validation.heldout_observations,
        independently_measured_reciprocal_loops: loops.len() / 2,
        maximum_heldout_error_quad: validation.maximum_heldout_error,
        maximum_reciprocal_loop_error_quad: validation.maximum_loop_error, fit_rms_quad: fit.fit_rms,
        maximum_local_displacement_quad: fit.maximum_displacement, fit_reservation_bytes: fit.reserved_work_bytes.checked_add(role_bytes).context("mesh role reservation overflow")?,
        canvas_origin_quad: canvas.origin, canvas_size_quad: [canvas.width, canvas.height],
        pass_cell_status: meshes.iter().map(|m| m.visibility.iter().map(|&s| name(s).into()).collect()).collect(),
        qualified_join_cells: meshes.iter().map(|m| m.visibility.iter().filter(|&&s| s == Visibility::ValidatedOverlap).count()).collect(),
        join_support: validation.join_support.iter().map(|s|JoinSupportRecord { pass:s.pass,cell:s.cell,witness_count:s.witness_count,
            hull_quad:s.hull.clone(),area_fraction:s.area_fraction,span_fraction:s.span_fraction,
            qualified:s.qualified && meshes[s.pass].visibility[s.cell] == Visibility::ValidatedOverlap }).collect(),
        discovery: discovery.to_vec(), native_receipts: native.to_vec(),
        visibility_contract: "Only the measured source-coordinate witness hull inside a qualified cell may be averaged across views; cell status alone is insufficient. Hull area must cover at least1/32 cell and both spans at least1/3 physical cell dimensions. These are support-shape guards, not interpolation error bounds. Positive SingleView areas retain continuous regularized placement. Failed cells remain excluded. Zero storage is not observed black. No primary preference.".into() };
    Ok((canvas, meshes, seeds, report))
}

#[allow(clippy::too_many_arguments)]
pub fn solve_geometry(
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    guides: &[MosaicGuide],
    discovery: &[PairDiscovery],
    native: &[NativeCorrespondence],
    config: &MosaicGeometryConfig,
    budget: usize,
) -> Result<MosaicGeometry> {
    let binding = binding(session, identities, guides, config)?;
    for receipt in native {
        let c = &receipt.candidate;
        ensure!(
            session
                .passes
                .get(c.pass_a)
                .is_some_and(|p| p.global_range.contains(&c.source_a))
                && session
                    .passes
                    .get(c.pass_b)
                    .is_some_and(|p| p.global_range.contains(&c.source_b)),
            "mosaic native receipt source outside declared pass"
        );
    }
    let (canvas, meshes, original_view_meshes, report) =
        solve_unbound(guides, discovery, native, config, budget)?;
    Ok(MosaicGeometry {
        canvas,
        meshes,
        original_view_meshes,
        report,
        binding,
    })
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct MeshRecord {
    source: [usize; 2],
    columns: usize,
    rows: usize,
    vertices: Vec<[f64; 2]>,
    focus: Vec<Option<[f32; 2]>>,
    visibility: Vec<String>,
    #[serde(default)]
    join_hulls: Vec<Vec<[f64; 2]>>,
}
impl MeshRecord {
    fn from_mesh(mesh: &ForwardMesh) -> Self {
        Self {
            source: [mesh.source.width, mesh.source.height],
            columns: mesh.columns,
            rows: mesh.rows,
            vertices: mesh.vertices.clone(),
            focus: mesh
                .focus
                .iter()
                .map(|f| f.usable.then_some([f.ordinal, f.width]))
                .collect(),
            visibility: mesh.visibility.iter().map(|&s| name(s).into()).collect(),
            join_hulls: mesh.join_hulls.clone(),
        }
    }
    fn into_mesh(self) -> Result<ForwardMesh> {
        let focus = self
            .focus
            .into_iter()
            .map(|f| {
                f.map_or(
                    FocusEvidence {
                        ordinal: 0.0,
                        width: 0.0,
                        usable: false,
                    },
                    |f| FocusEvidence {
                        ordinal: f[0],
                        width: f[1],
                        usable: true,
                    },
                )
            })
            .collect();
        let visibility = self
            .visibility
            .iter()
            .map(|s| visibility(s))
            .collect::<Result<_>>()?;
        let mut mesh = ForwardMesh::new(
            PlaneGeometry {
                width: self.source[0],
                height: self.source[1],
            },
            self.columns,
            self.rows,
            self.vertices,
            visibility,
            focus,
        )?;
        if !self.join_hulls.is_empty() {
            mesh.join_hulls = self.join_hulls;
        }
        mesh.validate()?;
        Ok(mesh)
    }
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Payload {
    meshes: Vec<MeshRecord>,
    original_view_meshes: Vec<MeshRecord>,
    report: MosaicGeometryReport,
}
impl MosaicGeometry {
    pub fn save(&self, path: &Path, session: &ResolvedSession) -> Result<()> {
        let payload = Payload {
            meshes: self.meshes.iter().map(MeshRecord::from_mesh).collect(),
            original_view_meshes: self
                .original_view_meshes
                .iter()
                .map(MeshRecord::from_mesh)
                .collect(),
            report: self.report.clone(),
        };
        save_bound(path, session, &self.binding, &payload)
    }
    pub fn load(
        path: &Path,
        session: &ResolvedSession,
        identities: &[SourceIdentity],
        guides: &[MosaicGuide],
        config: &MosaicGeometryConfig,
    ) -> Result<Self> {
        let binding = binding(session, identities, guides, config)?;
        let payload: Payload = load_bound(path, &binding)?;
        ensure!(
            payload.meshes.len() == guides.len()
                && payload.original_view_meshes.len() == guides.len()
                && payload.report.pass_count == guides.len(),
            "saved mosaic topology has wrong pass count"
        );
        let meshes = payload
            .meshes
            .into_iter()
            .map(MeshRecord::into_mesh)
            .collect::<Result<Vec<_>>>()?;
        let original_view_meshes = payload
            .original_view_meshes
            .into_iter()
            .map(MeshRecord::into_mesh)
            .collect::<Result<Vec<_>>>()?;
        for ((mesh, original), guide) in meshes.iter().zip(&original_view_meshes).zip(guides) {
            ensure!(
                mesh.source == guide.source_geometry
                    && original.source == guide.source_geometry
                    && mesh.columns == original.columns
                    && mesh.rows == original.rows,
                "saved mosaic geometry differs from source/topology"
            );
        }
        // Reconstruct from source-bound measured receipts rather than trusting
        // serialized status counters or triangle visibility flags. This small
        // sparse solve is cheap relative to native matching and prevents stale
        // report fields silently authorizing a saved unsupported join.
        let reconstructed = solve_geometry(
            session,
            identities,
            guides,
            &payload.report.discovery,
            &payload.report.native_receipts,
            config,
            usize::MAX,
        )?;
        ensure!(
            meshes
                .iter()
                .zip(&reconstructed.meshes)
                .all(|(a, b)| a.vertices == b.vertices && a.visibility == b.visibility)
                && original_view_meshes
                    .iter()
                    .zip(&reconstructed.original_view_meshes)
                    .all(|(a, b)| a.vertices == b.vertices),
            "saved mosaic map differs from measured receipt reconstruction"
        );
        ensure!(
            serde_json::to_value(&payload.report)? == serde_json::to_value(&reconstructed.report)?,
            "saved mosaic report differs from validated measurements"
        );
        Ok(reconstructed)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::session_mosaic_geometry::{CoarseCorrespondence, GuideReceipt};
    fn guide(pass: usize) -> MosaicGuide {
        let g = PlaneGeometry {
            width: 101,
            height: 81,
        };
        let n = g.pixels();
        MosaicGuide {
            pass,
            source_geometry: g,
            geometry: g,
            origin: [0.0, 0.0],
            step: 1,
            intensity: vec![100.0; n],
            covered: vec![true; n],
            focus_ordinal: vec![3.0; n],
            focus_width: vec![1.0; n],
            usable_focus: vec![true; n],
            source_indices: vec![[pass, usize::MAX, usize::MAX, usize::MAX]; n],
            receipt: GuideReceipt {
                pass,
                source_geometry: [101, 81],
                guide_geometry: [101, 81],
                origin_quad_pixels: [0.0, 0.0],
                step_quad_pixels: 1,
                alignment_sha256: "control".into(),
                focus_evidence_sha256: "control".into(),
                guide_sha256: "control".into(),
                covered_pixels: n,
                usable_focus_pixels: n,
                source_contributions: vec![(pass, n)],
                reserved_work_bytes: 0,
                construction: "synthetic geometry control".into(),
            },
        }
    }
    #[test]
    fn measured_mosaic_topology_extends_union_and_retains_qualified_join() {
        let guides = [guide(0), guide(1)];
        let mut native = Vec::new();
        for y in 1..8 {
            for x in 3..10 {
                let a = [f64::from(x) * 10.0, f64::from(y) * 10.0];
                let b = [a[0] - 21.0, a[1]];
                let role = if (x + y) % 3 == 0 {
                    MatchRole::Heldout
                } else {
                    MatchRole::Fit
                };
                native.push(NativeCorrespondence {
                    nomination_policy: "synthetic measured topology control".into(),
                    support_bounds_quad: Some([
                        [[a[0] - 1.0, a[1] - 1.0], [a[0] + 1.0, a[1] + 1.0]],
                        [[b[0] - 1.0, b[1] - 1.0], [b[0] + 1.0, b[1] + 1.0]],
                    ]),
                    candidate: CoarseCorrespondence {
                        id: format!("{x}-{y}"),
                        pass_a: 0,
                        pass_b: 1,
                        point_a_quad: a,
                        point_b_quad: b,
                        source_a: 0,
                        source_b: 1,
                        focus_a: Some([3.0, 1.0]),
                        focus_b: Some([3.0, 1.0]),
                        role,
                        spatial_blocks: [[x as usize, y as usize]; 2],
                        descriptor_distance: 0.0,
                        seed_residual_quad: 0.0,
                        within_seed_support: true,
                        grid_nomination: false,
                        spatial_roles_match: true,
                    },
                    accepted: true,
                    refined_b_quad: Some(b),
                    forward_rms_quad: Some(0.0),
                    reverse_rms_quad: Some(0.0),
                    reciprocal_error_quad: Some(0.0),
                    mean_peak: Some(1.0),
                    forward_tiles: 9,
                    reverse_tiles: 9,
                    refusal: None,
                    reserved_dependency_checked: true,
                    measurements: Vec::new(),
                });
            }
        }
        assert!(
            solve_unbound(
                &guides,
                &[],
                &native[..3],
                &MosaicGeometryConfig::default(),
                10_000_000
            )
            .is_err(),
            "three even-perfect native observations cannot certify a view edge"
        );
        let mut repeated: Vec<_> = (0..12)
            .map(|i| {
                let mut r = native[0].clone();
                r.candidate.id = format!("alternative-{i}");
                r.candidate.source_b = i + 1;
                r
            })
            .collect();
        let unique = independent_native_constraints(&repeated, 2, 0.5).unwrap();
        assert_eq!(
            unique.observations.len(),
            1,
            "alternative originals cannot manufacture independent locations"
        );
        assert_eq!(unique.loops.len(), 2);
        assert_eq!(unique.receipt_indices, vec![0]);
        let mut refused_first = repeated[0].clone();
        refused_first.candidate.id = "refused-before-kept-site".into();
        refused_first.accepted = false;
        refused_first.refusal = Some("planted native refusal".into());
        let mut offset_receipts = vec![refused_first];
        offset_receipts.extend(repeated.iter().cloned());
        let offset = independent_native_constraints(&offset_receipts, 2, 0.5).unwrap();
        assert_eq!(offset.receipt_indices, vec![1]);
        assert_eq!(
            offset.observations[0].point_a,
            unique.observations[0].point_a
        );
        assert_eq!(offset.loops.len(), unique.loops.len());
        // Distinct descriptor coordinates on overlapping original footprints
        // cannot supply more heldout votes, even from different focus frames.
        let mut nearby = native[0].clone();
        nearby.candidate.id = "nearby-independent-name".into();
        nearby.candidate.point_a_quad[0] += 0.75;
        nearby.candidate.point_b_quad[0] += 0.75;
        nearby.refined_b_quad.as_mut().unwrap()[0] += 0.75;
        nearby.candidate.source_a += 20;
        let nearby_pair = [native[0].clone(), nearby];
        assert_eq!(
            independent_native_constraints(&nearby_pair, 2, 0.5)
                .unwrap()
                .observations
                .len(),
            1
        );
        assert!(
            solve_unbound(
                &guides,
                &[],
                &repeated,
                &MosaicGeometryConfig::default(),
                10_000_000
            )
            .is_err()
        );
        repeated[0].refined_b_quad.as_mut().unwrap()[0] += 1.0;
        assert!(
            independent_native_constraints(&repeated, 2, 0.5)
                .unwrap()
                .observations
                .is_empty(),
            "disagreeing alternatives leave an unsupported site"
        );
        let (canvas, meshes, _, report) = solve_unbound(
            &guides,
            &[],
            &native,
            &MosaicGeometryConfig::default(),
            10_000_000,
        )
        .unwrap();
        assert!(
            canvas.width >= 122,
            "must retain a union wider than either 101-pixel view"
        );
        assert_eq!(report.native_accepted, native.len());
        assert_eq!(
            report.independent_site_ids,
            native
                .iter()
                .map(|r| r.candidate.id.clone())
                .collect::<Vec<_>>()
        );
        assert!(report.heldout_observations >= 3);
        assert!(report.maximum_heldout_error_quad < 1e-6);
        assert_eq!(report.qualified_join_cells, vec![1, 1]);
        let a = meshes[0].map_source([50.0, 40.0]).unwrap();
        let b = meshes[1].map_source([29.0, 40.0]).unwrap();
        assert!((a[0] - b[0]).hypot(a[1] - b[1]) < 1e-6);
        let mut broken = native;
        for receipt in &mut broken {
            if receipt.candidate.role == MatchRole::Heldout {
                receipt.refined_b_quad.as_mut().unwrap()[1] += 4.0;
            }
        }
        let (_, meshes, original, report) = solve_unbound(
            &guides,
            &[],
            &broken,
            &MosaicGeometryConfig::default(),
            10_000_000,
        )
        .unwrap();
        assert_eq!(report.qualified_join_cells, vec![0, 0]);
        assert!(
            meshes
                .iter()
                .all(|m| m.visibility[0] == Visibility::HeldoutFailure)
        );
        assert!(
            original
                .iter()
                .all(|m| m.visibility[0] == Visibility::SingleView)
        );
    }
}
