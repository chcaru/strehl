//! Bounded geometry for focus-aware, multi-perspective mosaics.
//!
//! All coordinates are green-quad coordinates: (x,y) denotes active sensor
//! (2*x+0.5,2*y+0.5). A canvas has a signed origin in that same world gauge.
//! This module never owns image samples and never infers physical depth from
//! focus ordinals. Invalid geometry is a mask, never an observed black pixel.

use crate::plane::PlaneGeometry;

pub type Point = [f64; 2];

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MosaicError(pub &'static str);
impl std::fmt::Display for MosaicError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.0)
    }
}
impl std::error::Error for MosaicError {}
type Result<T> = std::result::Result<T, MosaicError>;

fn checked(condition: bool, message: &'static str) -> Result<()> {
    if condition {
        Ok(())
    } else {
        Err(MosaicError(message))
    }
}
fn finite(p: Point) -> bool {
    p.into_iter().all(f64::is_finite)
}
fn sub(a: Point, b: Point) -> Point {
    [a[0] - b[0], a[1] - b[1]]
}
fn cross(a: Point, b: Point) -> f64 {
    a[0] * b[1] - a[1] * b[0]
}
fn norm(a: Point) -> f64 {
    a[0].hypot(a[1])
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Bounds {
    pub min: Point,
    pub max: Point,
}
impl Bounds {
    fn validate(self) -> Result<()> {
        checked(
            finite(self.min)
                && finite(self.max)
                && self.min[0] < self.max[0]
                && self.min[1] < self.max[1],
            "empty or nonfinite mosaic bounds",
        )
    }
    fn contains(self, point: Point) -> bool {
        point[0] >= self.min[0]
            && point[1] >= self.min[1]
            && point[0] <= self.max[0]
            && point[1] <= self.max[1]
    }
}

#[derive(Clone, Copy, Debug)]
pub struct CanvasLimits {
    pub max_side: usize,
    pub max_pixels: usize,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MosaicCanvas {
    pub origin: [i64; 2],
    pub width: usize,
    pub height: usize,
}
impl MosaicCanvas {
    /// Bounds are half-open output extents, not source pixel-centre bounds.
    pub fn from_bounds(bounds: &[Bounds], limits: CanvasLimits) -> Result<Self> {
        checked(!bounds.is_empty(), "no mosaic views")?;
        let mut min = [f64::INFINITY; 2];
        let mut max = [f64::NEG_INFINITY; 2];
        for &b in bounds {
            b.validate()?;
            for axis in 0..2 {
                min[axis] = min[axis].min(b.min[axis]).floor();
                max[axis] = max[axis].max(b.max[axis]).ceil();
            }
        }
        // Keep integer conversion and subsequent subpixel arithmetic exact.
        checked(
            min.iter()
                .chain(&max)
                .all(|x| x.abs() < (1_u64 << 50) as f64),
            "mosaic coordinate exceeds exact integer range",
        )?;
        let width = (max[0] - min[0]) as usize;
        let height = (max[1] - min[1]) as usize;
        checked(
            width <= limits.max_side && height <= limits.max_side,
            "mosaic canvas exceeds side limit",
        )?;
        checked(
            width
                .checked_mul(height)
                .is_some_and(|n| n <= limits.max_pixels),
            "mosaic canvas exceeds pixel limit",
        )?;
        Ok(Self {
            origin: [min[0] as i64, min[1] as i64],
            width,
            height,
        })
    }
    pub fn world(self, x: f64, y: f64) -> Point {
        [self.origin[0] as f64 + x, self.origin[1] as f64 + y]
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PixelRect {
    pub x: usize,
    pub y: usize,
    pub width: usize,
    pub height: usize,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MosaicTile {
    pub core: PixelRect,
    pub work: PixelRect,
}
#[derive(Clone, Debug)]
pub struct MosaicTilePlan {
    pub canvas: MosaicCanvas,
    pub phase: usize,
    pub tiles: Vec<MosaicTile>,
}
impl MosaicTilePlan {
    /// `dependency_halo` includes every consuming filter, not merely the gather
    /// kernel. Work origins have the full canvas's pyramid phase. Trim to core
    /// only after reconstruction; actual canvas edges retain boundary behavior.
    pub fn new(
        canvas: MosaicCanvas,
        core_side: usize,
        reductions: u32,
        dependency_halo: usize,
        max_work_pixels: usize,
        max_tiles: usize,
    ) -> Result<Self> {
        checked(
            canvas.width > 0 && canvas.height > 0 && core_side > 0,
            "empty mosaic tile plan",
        )?;
        let phase = 1_usize
            .checked_shl(reductions)
            .ok_or(MosaicError("pyramid phase overflow"))?;
        let nx = canvas.width.div_ceil(core_side);
        let ny = canvas.height.div_ceil(core_side);
        let count = nx
            .checked_mul(ny)
            .ok_or(MosaicError("tile count overflow"))?;
        checked(count <= max_tiles, "mosaic tile count exceeds limit")?;
        let mut tiles = Vec::with_capacity(count);
        for row in 0..ny {
            for column in 0..nx {
                let x = column * core_side;
                let y = row * core_side;
                let right = x.saturating_add(core_side).min(canvas.width);
                let bottom = y.saturating_add(core_side).min(canvas.height);
                let wx = x.saturating_sub(dependency_halo) / phase * phase;
                let wy = y.saturating_sub(dependency_halo) / phase * phase;
                let wr = right.saturating_add(dependency_halo).min(canvas.width);
                let wb = bottom.saturating_add(dependency_halo).min(canvas.height);
                // Right/bottom rounding preserves reduction sizes at interior
                // boundaries as well as left/top phase.
                let wr = wr.div_ceil(phase).saturating_mul(phase).min(canvas.width);
                let wb = wb.div_ceil(phase).saturating_mul(phase).min(canvas.height);
                checked(
                    (wr - wx)
                        .checked_mul(wb - wy)
                        .is_some_and(|n| n <= max_work_pixels),
                    "mosaic tile workspace exceeds pixel limit",
                )?;
                tiles.push(MosaicTile {
                    core: PixelRect {
                        x,
                        y,
                        width: right - x,
                        height: bottom - y,
                    },
                    work: PixelRect {
                        x: wx,
                        y: wy,
                        width: wr - wx,
                        height: wb - wy,
                    },
                });
            }
        }
        Ok(Self {
            canvas,
            phase,
            tiles,
        })
    }
}

/// A separate status for unsupported geometry; no numeric sentinel is a sample.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Visibility {
    SingleView,
    ValidatedOverlap,
    Unverified,
    AmbiguousFocus,
    Disoccluded,
    HeldoutFailure,
    LoopFailure,
    Fold,
    ExcessiveStretch,
}
impl Visibility {
    pub fn usable(self) -> bool {
        matches!(self, Self::SingleView | Self::ValidatedOverlap)
    }
}

#[derive(Clone, Copy, Debug)]
pub struct FocusEvidence {
    pub ordinal: f32,
    pub width: f32,
    pub usable: bool,
}
#[derive(Clone, Debug)]
pub struct ForwardMesh {
    pub source: PlaneGeometry,
    pub columns: usize,
    pub rows: usize,
    /// Forward vertex locations in signed canvas/world green-quad coordinates.
    pub vertices: Vec<Point>,
    pub visibility: Vec<Visibility>,
    pub focus: Vec<FocusEvidence>,
    /// Measured held-out witness hulls in source-pass green-quad coordinates.
    /// An empty hull never authorizes cross-view blending.
    pub join_hulls: Vec<Vec<Point>>,
}
impl ForwardMesh {
    pub fn validate(&self) -> Result<()> {
        checked(
            self.source.width >= 2
                && self.source.height >= 2
                && self.columns >= 2
                && self.rows >= 2,
            "mosaic mesh must have nonempty two-dimensional cells",
        )?;
        let count = self
            .columns
            .checked_mul(self.rows)
            .ok_or(MosaicError("mesh dimensions overflow"))?;
        checked(
            self.vertices.len() == count
                && self.focus.len() == count
                && self.visibility.len() == (self.columns - 1) * (self.rows - 1)
                && self.join_hulls.len() == self.visibility.len(),
            "mesh buffer size mismatch",
        )?;
        checked(
            self.vertices
                .iter()
                .all(|p| finite(*p) && p.iter().all(|x| x.abs() < (1_u64 << 50) as f64)),
            "nonfinite or unbounded mesh vertex",
        )?;
        for (cell, hull) in self.join_hulls.iter().enumerate() {
            if !hull.is_empty() {
                let (canonical, _, _) = support::hull_metrics(self, cell, hull)?;
                checked(
                    canonical == *hull,
                    "noncanonical or degenerate join witness hull",
                )?;
            }
        }
        checked(
            self.focus.iter().all(|f| {
                !f.usable || (f.ordinal.is_finite() && f.width.is_finite() && f.width >= 0.0)
            }),
            "invalid usable focus evidence",
        )
    }
    pub fn new(
        source: PlaneGeometry,
        columns: usize,
        rows: usize,
        vertices: Vec<Point>,
        visibility: Vec<Visibility>,
        focus: Vec<FocusEvidence>,
    ) -> Result<Self> {
        checked(
            source.width >= 2 && source.height >= 2 && columns >= 2 && rows >= 2,
            "mosaic mesh must have nonempty two-dimensional cells",
        )?;
        let count = columns
            .checked_mul(rows)
            .ok_or(MosaicError("mesh dimensions overflow"))?;
        checked(
            vertices.len() == count
                && focus.len() == count
                && visibility.len() == (columns - 1) * (rows - 1),
            "mesh buffer size mismatch",
        )?;
        checked(
            vertices.iter().copied().all(finite),
            "nonfinite mesh vertex",
        )?;
        checked(
            focus.iter().all(|f| {
                !f.usable || (f.ordinal.is_finite() && f.width.is_finite() && f.width >= 0.0)
            }),
            "invalid usable focus evidence",
        )?;
        let join_hulls = vec![Vec::new(); visibility.len()];
        let mesh = Self {
            source,
            columns,
            rows,
            vertices,
            visibility,
            focus,
            join_hulls,
        };
        mesh.validate()?;
        Ok(mesh)
    }
    pub fn source_vertex(&self, index: usize) -> Point {
        [
            (index % self.columns) as f64 * (self.source.width - 1) as f64
                / (self.columns - 1) as f64,
            (index / self.columns) as f64 * (self.source.height - 1) as f64
                / (self.rows - 1) as f64,
        ]
    }
    fn weights(&self, point: Point) -> Option<([usize; 3], [f64; 3], usize)> {
        if !finite(point)
            || point[0] < 0.0
            || point[1] < 0.0
            || point[0] > (self.source.width - 1) as f64
            || point[1] > (self.source.height - 1) as f64
        {
            return None;
        }
        let gx = point[0] * (self.columns - 1) as f64 / (self.source.width - 1) as f64;
        let gy = point[1] * (self.rows - 1) as f64 / (self.source.height - 1) as f64;
        let x = (gx.floor() as usize).min(self.columns - 2);
        let y = (gy.floor() as usize).min(self.rows - 2);
        let u = gx - x as f64;
        let v = gy - y as f64;
        let a = y * self.columns + x;
        let cell = y * (self.columns - 1) + x;
        if v <= u {
            Some(([a, a + 1, a + self.columns + 1], [1.0 - u, u - v, v], cell))
        } else {
            Some((
                [a, a + self.columns + 1, a + self.columns],
                [1.0 - v, u, v - u],
                cell,
            ))
        }
    }
    pub fn map_source(&self, point: Point) -> Option<Point> {
        let (ids, weights, _) = self.weights(point)?;
        let mut out = [0.0; 2];
        for (id, weight) in ids.into_iter().zip(weights) {
            for (axis, value) in out.iter_mut().enumerate() {
                *value += weight * self.vertices[id][axis];
            }
        }
        Some(out)
    }
    pub fn bounds(&self) -> Bounds {
        let mut out = Bounds {
            min: [f64::INFINITY; 2],
            max: [f64::NEG_INFINITY; 2],
        };
        for p in &self.vertices {
            for (axis, &coordinate) in p.iter().enumerate() {
                out.min[axis] = out.min[axis].min(coordinate);
                out.max[axis] = out.max[axis].max(coordinate);
            }
        }
        out
    }
}

#[derive(Clone, Copy, Debug)]
pub struct MeshValidation {
    pub minimum_determinant: f64,
    pub maximum_stretch: f64,
    pub minimum_heldout: usize,
    pub maximum_heldout_error: f64,
    pub maximum_loop_error: f64,
    /// Predeclared support-shape guards, not a bound on interpolation error.
    pub minimum_hull_area_fraction: f64,
    pub minimum_hull_span_fraction: f64,
}
impl Default for MeshValidation {
    fn default() -> Self {
        Self {
            minimum_determinant: 0.1,
            maximum_stretch: 4.0,
            minimum_heldout: 3,
            maximum_heldout_error: 0.5,
            maximum_loop_error: 0.5,
            minimum_hull_area_fraction: 1.0 / 32.0,
            minimum_hull_span_fraction: 1.0 / 3.0,
        }
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ObservationRole {
    Fit,
    Heldout,
}
#[derive(Clone, Copy, Debug)]
pub struct Correspondence {
    pub pass_a: usize,
    pub point_a: Point,
    pub pass_b: usize,
    pub point_b: Point,
    pub weight: f64,
    pub role: ObservationRole,
}
/// Independent measured loop closure attached to the source cell it traverses.
/// The caller composes *measured edge maps*, not the solved poses (which close
/// by construction). A solved-pose loop is not independent evidence.
#[derive(Clone, Copy, Debug)]
pub struct LoopWitness {
    pub pass: usize,
    pub source: Point,
    pub error: f64,
}
#[derive(Clone, Debug, Default)]
pub struct ValidationReport {
    pub fit_observations: usize,
    pub heldout_observations: usize,
    pub usable_cells: usize,
    pub rejected_cells: usize,
    pub maximum_heldout_error: f64,
    pub maximum_loop_error: f64,
    pub measured_loop_witnesses: usize,
    pub join_support: Vec<CellJoinSupport>,
}

pub fn validate_observations(
    meshes: &mut [ForwardMesh],
    observations: &[Correspondence],
    loops: &[LoopWitness],
    policy: MeshValidation,
) -> Result<ValidationReport> {
    checked(
        policy.minimum_heldout > 0
            && policy.maximum_heldout_error.is_finite()
            && policy.maximum_heldout_error > 0.0
            && policy.maximum_loop_error.is_finite()
            && policy.maximum_loop_error > 0.0
            && policy.minimum_hull_area_fraction.is_finite()
            && (0.0..=1.0).contains(&policy.minimum_hull_area_fraction)
            && policy.minimum_hull_area_fraction > 0.0
            && policy.minimum_hull_span_fraction.is_finite()
            && (0.0..=1.0).contains(&policy.minimum_hull_span_fraction)
            && policy.minimum_hull_span_fraction > 0.0,
        "invalid mosaic evidence policy",
    )?;
    for mesh in meshes.iter() {
        mesh.validate()?;
    }
    let mut counts: Vec<Vec<usize>> = meshes.iter().map(|m| vec![0; m.visibility.len()]).collect();
    let mut witnesses: Vec<Vec<Vec<Point>>> = meshes
        .iter()
        .map(|m| vec![Vec::new(); m.visibility.len()])
        .collect();
    let mut errors: Vec<Vec<f64>> = meshes
        .iter()
        .map(|m| vec![0.0; m.visibility.len()])
        .collect();
    let mut loop_errors = errors.clone();
    let mut report = ValidationReport::default();
    for observation in observations {
        validate_correspondence(meshes, observation)?;
        if observation.role == ObservationRole::Fit {
            report.fit_observations += 1;
            continue;
        }
        report.heldout_observations += 1;
        let a = &meshes[observation.pass_a];
        let b = &meshes[observation.pass_b];
        let pa = a
            .map_source(observation.point_a)
            .ok_or(MosaicError("heldout point outside mesh"))?;
        let pb = b
            .map_source(observation.point_b)
            .ok_or(MosaicError("heldout point outside mesh"))?;
        let error = norm(sub(pa, pb));
        report.maximum_heldout_error = report.maximum_heldout_error.max(error);
        for (pass, point) in [
            (observation.pass_a, observation.point_a),
            (observation.pass_b, observation.point_b),
        ] {
            let (_, _, cell) = meshes[pass]
                .weights(point)
                .ok_or(MosaicError("heldout point outside mesh"))?;
            counts[pass][cell] += 1;
            witnesses[pass][cell].push(point);
            errors[pass][cell] = errors[pass][cell].max(error);
        }
    }
    for witness in loops {
        checked(
            witness.pass < meshes.len() && witness.error.is_finite() && witness.error >= 0.0,
            "invalid measured loop witness",
        )?;
        let (_, _, cell) = meshes[witness.pass]
            .weights(witness.source)
            .ok_or(MosaicError("loop point outside mesh"))?;
        loop_errors[witness.pass][cell] = loop_errors[witness.pass][cell].max(witness.error);
        report.maximum_loop_error = report.maximum_loop_error.max(witness.error);
        report.measured_loop_witnesses += 1;
    }
    for (pass, mesh) in meshes.iter_mut().enumerate() {
        let shapes: Vec<_> = witnesses[pass]
            .iter()
            .enumerate()
            .map(|(cell, points)| support::hull_metrics(mesh, cell, points))
            .collect::<Result<_>>()?;
        mesh.join_hulls.iter_mut().for_each(Vec::clear);
        for (cell, visibility) in mesh.visibility.iter_mut().enumerate() {
            // Explicit occlusion/focus masks cannot be cleared by a good residual.
            if matches!(
                *visibility,
                Visibility::Disoccluded | Visibility::AmbiguousFocus
            ) {
                continue;
            }
            if loop_errors[pass][cell] > policy.maximum_loop_error {
                *visibility = Visibility::LoopFailure;
            } else if errors[pass][cell] > policy.maximum_heldout_error {
                *visibility = Visibility::HeldoutFailure;
            } else if counts[pass][cell] >= policy.minimum_heldout
                && support::shape_supported(shapes[cell].1, shapes[cell].2, policy)
            {
                *visibility = Visibility::ValidatedOverlap;
                mesh.join_hulls[cell] = shapes[cell].0.clone();
            } else if *visibility != Visibility::SingleView {
                *visibility = Visibility::Unverified;
            }
            if counts[pass][cell] > 0 {
                report.join_support.push(CellJoinSupport {
                    pass,
                    cell,
                    witness_count: counts[pass][cell],
                    hull: shapes[cell].0.clone(),
                    area_fraction: shapes[cell].1,
                    span_fraction: shapes[cell].2,
                    qualified: *visibility == Visibility::ValidatedOverlap,
                });
            }
        }
        for visibility in &mesh.visibility {
            if visibility.usable() {
                report.usable_cells += 1;
            } else {
                report.rejected_cells += 1;
            }
        }
    }
    Ok(report)
}

fn validate_correspondence(meshes: &[ForwardMesh], observation: &Correspondence) -> Result<()> {
    checked(
        observation.pass_a < meshes.len()
            && observation.pass_b < meshes.len()
            && observation.pass_a != observation.pass_b
            && observation.weight.is_finite()
            && observation.weight > 0.0,
        "invalid mosaic correspondence",
    )?;
    checked(
        meshes[observation.pass_a]
            .weights(observation.point_a)
            .is_some()
            && meshes[observation.pass_b]
                .weights(observation.point_b)
                .is_some(),
        "mosaic correspondence outside source geometry",
    )
}

#[derive(Clone, Copy, Debug)]
struct Triangle {
    world: [Point; 3],
    source: [Point; 3],
    cell: usize,
    visibility: Visibility,
    bounds: Bounds,
}
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum MappedPoint {
    Supported { source: Point, cell: usize },
    Uncovered,
    Rejected(Visibility),
    Ambiguous,
}
#[derive(Clone, Copy, Debug)]
pub struct IndexLimits {
    pub bin_side: usize,
    pub max_bins: usize,
    pub max_entries: usize,
}
#[derive(Clone, Debug)]
pub struct BackwardMesh {
    triangles: Vec<Triangle>,
    bounds: Bounds,
    bin_side: f64,
    columns: usize,
    rows: usize,
    bins: Vec<Vec<usize>>,
    pub rejected_cells: usize,
    join_hulls: Vec<Vec<Point>>,
}
impl BackwardMesh {
    pub fn new(mesh: &ForwardMesh, policy: MeshValidation, limits: IndexLimits) -> Result<Self> {
        mesh.validate()?;
        checked(
            policy.minimum_determinant.is_finite()
                && policy.minimum_determinant > 0.0
                && policy.maximum_stretch.is_finite()
                && policy.maximum_stretch >= 1.0
                && limits.bin_side > 0,
            "invalid mosaic mesh validation limits",
        )?;
        let bounds = mesh.bounds();
        bounds.validate()?;
        let bin_side = limits.bin_side as f64;
        checked(
            (bounds.max[0] - bounds.min[0]) / bin_side < limits.max_bins as f64
                && (bounds.max[1] - bounds.min[1]) / bin_side < limits.max_bins as f64,
            "mesh index exceeds axis bin limit",
        )?;
        let columns = ((bounds.max[0] - bounds.min[0]) / bin_side).floor() as usize + 1;
        let rows = ((bounds.max[1] - bounds.min[1]) / bin_side).floor() as usize + 1;
        let count = columns
            .checked_mul(rows)
            .ok_or(MosaicError("mesh index overflow"))?;
        checked(count <= limits.max_bins, "mesh index exceeds bin limit")?;
        let triangle_count = mesh
            .visibility
            .len()
            .checked_mul(2)
            .ok_or(MosaicError("mesh triangle count overflow"))?;
        checked(
            triangle_count <= limits.max_entries,
            "mesh triangles exceed entry budget",
        )?;
        let hull_points = mesh
            .join_hulls
            .iter()
            .try_fold(0usize, |n, h| n.checked_add(h.len()))
            .ok_or(MosaicError("join hull point count overflow"))?;
        checked(
            hull_points <= limits.max_entries,
            "join hulls exceed index entry budget",
        )?;
        let mut out = Self {
            triangles: Vec::with_capacity(triangle_count),
            bounds,
            bin_side,
            columns,
            rows,
            bins: vec![Vec::new(); count],
            rejected_cells: 0,
            join_hulls: mesh.join_hulls.clone(),
        };
        let mut entries = 0usize;
        for y in 0..mesh.rows - 1 {
            for x in 0..mesh.columns - 1 {
                let cell = y * (mesh.columns - 1) + x;
                let a = y * mesh.columns + x;
                let triangle_ids = [
                    [a, a + 1, a + mesh.columns + 1],
                    [a, a + mesh.columns + 1, a + mesh.columns],
                ];
                let mut visibility = mesh.visibility[cell];
                if visibility == Visibility::ValidatedOverlap {
                    let (_, area, spans) =
                        support::hull_metrics(mesh, cell, &mesh.join_hulls[cell])?;
                    if !support::shape_supported(area, spans, policy) {
                        visibility = Visibility::SingleView;
                    }
                }
                for ids in triangle_ids {
                    let source = ids.map(|i| mesh.source_vertex(i));
                    let world = ids.map(|i| mesh.vertices[i]);
                    let s1 = sub(source[1], source[0]);
                    let s2 = sub(source[2], source[0]);
                    let w1 = sub(world[1], world[0]);
                    let w2 = sub(world[2], world[0]);
                    let determinant = cross(w1, w2) / cross(s1, s2);
                    if determinant <= policy.minimum_determinant {
                        visibility = Visibility::Fold;
                    } else {
                        // Affine Jacobian = [w1 w2] * inverse([s1 s2]).
                        let denominator = cross(s1, s2);
                        let j = [
                            (w1[0] * s2[1] - w2[0] * s1[1]) / denominator,
                            (-w1[0] * s2[0] + w2[0] * s1[0]) / denominator,
                            (w1[1] * s2[1] - w2[1] * s1[1]) / denominator,
                            (-w1[1] * s2[0] + w2[1] * s1[0]) / denominator,
                        ];
                        let trace = j.iter().map(|v| v * v).sum::<f64>();
                        let largest = ((trace
                            + (trace * trace - 4.0 * determinant * determinant)
                                .max(0.0)
                                .sqrt())
                            * 0.5)
                            .sqrt();
                        let smallest = determinant / largest;
                        if !largest.is_finite()
                            || largest > policy.maximum_stretch
                            || smallest < 1.0 / policy.maximum_stretch
                        {
                            visibility = Visibility::ExcessiveStretch;
                        }
                    }
                }
                if !visibility.usable() {
                    out.rejected_cells += 1;
                }
                for ids in triangle_ids {
                    let source = ids.map(|i| mesh.source_vertex(i));
                    let world = ids.map(|i| mesh.vertices[i]);
                    let mut bounds = Bounds {
                        min: world[0],
                        max: world[0],
                    };
                    for point in &world[1..] {
                        for (axis, &coordinate) in point.iter().enumerate() {
                            bounds.min[axis] = bounds.min[axis].min(coordinate);
                            bounds.max[axis] = bounds.max[axis].max(coordinate);
                        }
                    }
                    let index = out.triangles.len();
                    out.triangles.push(Triangle {
                        world,
                        source,
                        cell,
                        visibility,
                        bounds,
                    });
                    let lo = out.bin(bounds.min);
                    let hi = out.bin(bounds.max);
                    let added = (hi.0 - lo.0 + 1)
                        .checked_mul(hi.1 - lo.1 + 1)
                        .ok_or(MosaicError("mesh index entries overflow"))?;
                    entries = entries
                        .checked_add(added)
                        .ok_or(MosaicError("mesh index entries overflow"))?;
                    checked(
                        entries <= limits.max_entries,
                        "mesh index exceeds entry limit",
                    )?;
                    for by in lo.1..=hi.1 {
                        for bx in lo.0..=hi.0 {
                            out.bins[by * columns + bx].push(index);
                        }
                    }
                }
            }
        }
        Ok(out)
    }
    fn bin(&self, point: Point) -> (usize, usize) {
        (
            ((point[0] - self.bounds.min[0]) / self.bin_side).max(0.0) as usize,
            ((point[1] - self.bounds.min[1]) / self.bin_side).max(0.0) as usize,
        )
    }
    pub fn map(&self, point: Point) -> MappedPoint {
        if !finite(point) || !self.bounds.contains(point) {
            return MappedPoint::Uncovered;
        }
        let (x, y) = self.bin(point);
        if x >= self.columns || y >= self.rows {
            return MappedPoint::Uncovered;
        }
        let mut supported: Option<(Point, usize)> = None;
        let mut rejected = None;
        for &id in &self.bins[y * self.columns + x] {
            let triangle = &self.triangles[id];
            if !triangle.bounds.contains(point) {
                continue;
            }
            let d1 = sub(triangle.world[1], triangle.world[0]);
            let d2 = sub(triangle.world[2], triangle.world[0]);
            let determinant = cross(d1, d2);
            if determinant.abs() < 1e-14 {
                continue;
            }
            let delta = sub(point, triangle.world[0]);
            let u = cross(delta, d2) / determinant;
            let v = cross(d1, delta) / determinant;
            if u < -1e-9 || v < -1e-9 || u + v > 1.0 + 1e-9 {
                continue;
            }
            if !triangle.visibility.usable() {
                rejected = Some(triangle.visibility);
                continue;
            }
            let source = [
                triangle.source[0][0] * (1.0 - u - v)
                    + triangle.source[1][0] * u
                    + triangle.source[2][0] * v,
                triangle.source[0][1] * (1.0 - u - v)
                    + triangle.source[1][1] * u
                    + triangle.source[2][1] * v,
            ];
            if let Some((prior, _)) = supported
                && norm(sub(prior, source)) > 1e-7
            {
                return MappedPoint::Ambiguous;
            }
            supported = Some((source, triangle.cell));
        }
        if let Some((source, cell)) = supported {
            MappedPoint::Supported { source, cell }
        } else if let Some(reason) = rejected {
            MappedPoint::Rejected(reason)
        } else {
            MappedPoint::Uncovered
        }
    }
    pub fn index_entries(&self) -> usize {
        self.bins.iter().map(Vec::len).sum()
    }

    /// The constructor's qualified cell state, including fold/stretch refusal.
    /// Both triangles in a cell always share this state.
    pub fn cell_visibility(&self, cell: usize) -> Option<Visibility> {
        self.triangles
            .get(cell.checked_mul(2)?)
            .map(|triangle| triangle.visibility)
    }
    /// Cross-view qualification is restricted to the measured source hull.
    /// Mapping outside it remains the same continuous single-view placement.
    pub fn join_supported(&self, cell: usize, source: Point) -> bool {
        self.cell_visibility(cell) == Some(Visibility::ValidatedOverlap)
            && self
                .join_hulls
                .get(cell)
                .is_some_and(|h| support::contains(h, source))
    }
}

#[path = "mosaic-support.rs"]
mod support;
pub use support::CellJoinSupport;

#[path = "mosaic-fit.rs"]
mod fit;
pub use fit::{MeshFitOptions, MeshFitReport, fit_meshes};

#[cfg(test)]
#[path = "mosaic-tests.rs"]
mod tests;
