//! Spatial support of independently measured held-out geometry witnesses.
//! Shape guards are not error bounds; cross-view use stays inside this hull.
use super::*;

#[derive(Clone, Debug)]
pub struct CellJoinSupport {
    pub pass: usize,
    pub cell: usize,
    pub witness_count: usize,
    /// Counterclockwise source-pass green-quad coordinates.
    pub hull: Vec<Point>,
    pub area_fraction: f64,
    pub span_fraction: Point,
    pub qualified: bool,
}

pub(super) fn cell_bounds(mesh: &ForwardMesh, cell: usize) -> Result<Bounds> {
    checked(cell < mesh.visibility.len(), "join cell outside mesh")?;
    let x = cell % (mesh.columns - 1);
    let y = cell / (mesh.columns - 1);
    Ok(Bounds {
        min: mesh.source_vertex(y * mesh.columns + x),
        max: mesh.source_vertex((y + 1) * mesh.columns + x + 1),
    })
}

pub(super) fn hull_metrics(
    mesh: &ForwardMesh,
    cell: usize,
    points: &[Point],
) -> Result<(Vec<Point>, f64, Point)> {
    let bounds = cell_bounds(mesh, cell)?;
    checked(
        points.iter().all(|p| finite(*p) && bounds.contains(*p)),
        "held support outside physical cell",
    )?;
    let mut points = points.to_vec();
    points.sort_by(|a, b| a[0].total_cmp(&b[0]).then(a[1].total_cmp(&b[1])));
    points.dedup();
    if points.len() < 3 {
        return Ok((Vec::new(), 0., [0.; 2]));
    }
    let mut hull = Vec::with_capacity(2 * points.len());
    for p in &points {
        while hull.len() >= 2
            && cross(
                sub(hull[hull.len() - 1], hull[hull.len() - 2]),
                sub(*p, hull[hull.len() - 1]),
            ) <= 0.
        {
            hull.pop();
        }
        hull.push(*p);
    }
    let lower = hull.len();
    for p in points[..points.len() - 1].iter().rev() {
        while hull.len() > lower
            && cross(
                sub(hull[hull.len() - 1], hull[hull.len() - 2]),
                sub(*p, hull[hull.len() - 1]),
            ) <= 0.
        {
            hull.pop();
        }
        hull.push(*p);
    }
    hull.pop();
    if hull.len() < 3 {
        return Ok((Vec::new(), 0., [0.; 2]));
    }
    let mut twice_area = 0.;
    let mut low = [f64::INFINITY; 2];
    let mut high = [f64::NEG_INFINITY; 2];
    for (index, p) in hull.iter().enumerate() {
        twice_area += cross(
            sub(*p, bounds.min),
            sub(hull[(index + 1) % hull.len()], bounds.min),
        );
        for axis in 0..2 {
            low[axis] = low[axis].min(p[axis]);
            high[axis] = high[axis].max(p[axis]);
        }
    }
    let size = sub(bounds.max, bounds.min);
    let spans = [0, 1].map(|axis| (high[axis] - low[axis]) / size[axis]);
    Ok((hull, 0.5 * twice_area.abs() / (size[0] * size[1]), spans))
}

pub(super) fn contains(hull: &[Point], point: Point) -> bool {
    if hull.len() < 3 || !finite(point) {
        return false;
    }
    hull.iter().enumerate().all(|(i, &a)| {
        let edge = sub(hull[(i + 1) % hull.len()], a);
        // Include the measured boundary; tolerance is a billionth of a quad,
        // not an extrapolation neighborhood or an image-size-scaled margin.
        cross(edge, sub(point, a)) >= -1e-9 * norm(edge).max(1.)
    })
}

pub(super) fn shape_supported(area: f64, spans: Point, policy: MeshValidation) -> bool {
    area >= policy.minimum_hull_area_fraction
        && spans
            .into_iter()
            .all(|s| s >= policy.minimum_hull_span_fraction)
}

#[cfg(test)]
#[path = "mosaic-support-tests.rs"]
mod tests;
