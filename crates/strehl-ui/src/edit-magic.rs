//! Bounded, image-guided enclosure refinement; this is not semantic/AI selection.
use super::*;
use std::sync::atomic::{AtomicBool, Ordering};

const MAX_SIDE: usize = 384;
const MAX_COMPONENTS: usize = 8;

#[derive(Default)]
pub(super) struct MagicState {
    pending: Option<Pending>,
    pub(super) outline: Option<RegionShape>,
    status: Option<String>,
    generation: u64,
}
struct Pending {
    image: Arc<LinearImage>,
    revision: u64,
    before: bool,
    task: Task<Selection>,
}
struct Selection {
    shapes: Vec<RegionShape>,
    skipped_holes: usize,
    closed_gaps: usize,
    omitted_components: usize,
    core_refinements: usize,
    #[cfg(test)]
    sampling_grid: [usize; 2],
    #[cfg(test)]
    sampled_pixels: usize,
}

struct CoherentContour {
    points: Vec<[f32; 2]>,
    closed_gaps: usize,
    refined: bool,
}

impl EditorState {
    pub fn magic_pending(&self) -> bool {
        self.magic.pending.is_some()
    }
    pub fn magic_generation(&self) -> u64 {
        self.magic.generation
    }
    pub fn magic_status(&self) -> Option<&str> {
        self.magic.status.as_deref()
    }
    pub(super) fn cancel_magic(&mut self) {
        if self.magic.pending.take().is_some() {
            self.magic.status = Some("Selection cancelled".into());
        }
        self.magic.outline = None;
    }
    pub(crate) fn start_magic(&mut self, enclosure: RegionShape, ctx: &egui::Context) {
        self.cancel_magic();
        let Some(loaded) = &self.loaded else { return };
        self.magic.generation = self.magic.generation.wrapping_add(1);
        let image = loaded.image.clone();
        let worker_image = image.clone();
        let shape = enclosure.clone();
        let recipe = if self.before {
            DevelopmentRecipe::default()
        } else {
            self.recipe.clone()
        };
        let wake = ctx.clone();
        self.magic.pending = Some(Pending {
            image,
            revision: self.revision,
            before: self.before,
            task: crate::jobs::spawn_notifying_task(
                "strehl-magic-lasso",
                move |cancelled| segment(&worker_image, &recipe, &shape, &cancelled),
                move || wake.request_repaint(),
            ),
        });
        self.magic.outline = Some(enclosure);
        self.magic.status = Some("Finding enclosed detail · Esc cancels".into());
    }
    pub(super) fn poll_magic(&mut self, ctx: &egui::Context) {
        let Some(pending) = &self.magic.pending else {
            return;
        };
        let text_focused = self.text_owns_geometry_input(ctx);
        if pending.revision != self.revision
            || pending.before != self.before
            || self.tool != DrawingTool::MagicLasso
            || self
                .loaded
                .as_ref()
                .is_none_or(|loaded| !Arc::ptr_eq(&loaded.image, &pending.image))
            || (!text_focused && ctx.input(|i| i.key_pressed(egui::Key::Escape)))
        {
            self.cancel_magic();
            return;
        }
        let result = match pending.task.receiver.try_recv() {
            Ok(result) => result,
            Err(std::sync::mpsc::TryRecvError::Empty) => return,
            Err(std::sync::mpsc::TryRecvError::Disconnected) => {
                Err("Selection worker stopped".into())
            }
        };
        self.magic.pending = None;
        self.magic.outline = None;
        match result {
            Ok(selection) if !selection.shapes.is_empty() => {
                let mut recipe = self.recipe.clone();
                let count = selection.shapes.len();
                let mut selected = None;
                for shape in selection.shapes {
                    let mut id = format!(
                        "magic-{}-{}",
                        std::process::id(),
                        crate::workspace_history::timestamp()
                    );
                    while recipe.regions.iter().any(|r| r.id == id) {
                        id.push('x');
                    }
                    selected.get_or_insert_with(|| id.clone());
                    recipe.regions.push(RegionAdjustment {
                        id,
                        name: format!("Detail {}", recipe.regions.len() + 1),
                        note: "Magic lasso · image contrast inside a drawn enclosure".into(),
                        shape,
                        feather: 0.15,
                        enabled: true,
                        adjustments: Adjustments::default(),
                        source_range: None,
                    });
                }
                match self.replace(recipe) {
                    Ok(()) => {
                        self.selected = selected;
                        self.set_tool(DrawingTool::Select);
                        self.show_regions = true;
                        self.magic.status = Some(format!(
                            "{count} detail region{} · drag points to refine{}{}{}{}",
                            if count == 1 { "" } else { "s" },
                            if selection.skipped_holes > 0 {
                                " · shapes with holes skipped"
                            } else {
                                ""
                            },
                            if selection.closed_gaps > 0 {
                                " · small gaps closed"
                            } else {
                                ""
                            },
                            if selection.omitted_components > 0 {
                                format!(
                                    " · {} smaller regions left unselected",
                                    selection.omitted_components
                                )
                            } else {
                                String::new()
                            },
                            if selection.core_refinements > 0 {
                                " · high-contrast core"
                            } else {
                                ""
                            }
                        ));
                    }
                    Err(error) => {
                        self.magic.status = Some(format!("Selection could not be added: {error}"))
                    }
                }
            }
            Ok(selection) => {
                self.magic.status = Some(if selection.skipped_holes > 0 {
                    "Enclosed detail has holes; use Lasso for an explicit boundary".into()
                } else {
                    "No separated detail found · draw tighter with a little background, or use Lasso".into()
                })
            }
            Err(error) => self.magic.status = Some(error),
        }
    }
}

fn check_cancel(cancel: &AtomicBool) -> anyhow::Result<()> {
    anyhow::ensure!(!cancel.load(Ordering::Relaxed), "Selection cancelled");
    Ok(())
}
fn distance(a: [f32; 3], b: [f32; 3]) -> f32 {
    a.iter()
        .zip(b)
        .map(|(x, y)| (x - y).powi(2))
        .sum::<f32>()
        .sqrt()
}
fn background_distance(value: [f32; 3], centers: &[[f32; 3]]) -> f32 {
    let mut best = f32::INFINITY;
    for (i, a) in centers.iter().enumerate() {
        best = best.min(distance(value, *a));
        for b in &centers[i + 1..] {
            let d = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
            let length = d.iter().map(|v| v * v).sum::<f32>();
            if length > 1e-10 {
                let t = ((0..3).map(|c| (value[c] - a[c]) * d[c]).sum::<f32>() / length)
                    .clamp(0.0, 1.0);
                best = best.min(distance(value, std::array::from_fn(|c| a[c] + d[c] * t)));
            }
        }
    }
    best
}
fn background_model(border: &[[f32; 3]]) -> Vec<[f32; 3]> {
    // Sparse bright outliers must not seed a background cluster and thereby hide
    // the very bright defect being enclosed. Seed only supported color bins.
    let mut bins = BTreeMap::<[u8; 3], (usize, [f32; 3])>::new();
    for value in border {
        let bin = bins.entry(value.map(|v| (v * 24.0) as u8)).or_default();
        bin.0 += 1;
        for (sum, v) in bin.1.iter_mut().zip(value) {
            *sum += v;
        }
    }
    let support = (border.len() / 100).max(2);
    let mut candidates = bins
        .values()
        .filter(|(count, _)| *count >= support)
        .map(|(count, sum)| (*count, sum.map(|v| v / *count as f32)))
        .collect::<Vec<_>>();
    candidates.sort_by_key(|v| std::cmp::Reverse(v.0));
    if candidates.is_empty() {
        return vec![std::array::from_fn(|c| {
            border.iter().map(|v| v[c]).sum::<f32>() / border.len() as f32
        })];
    }
    let mut centers = vec![candidates[0].1];
    for _ in 1..4 {
        let Some((_, next)) = candidates.iter().max_by(|a, b| {
            background_distance(a.1, &centers).total_cmp(&background_distance(b.1, &centers))
        }) else {
            break;
        };
        if background_distance(*next, &centers) < 0.025 {
            break;
        }
        centers.push(*next);
    }
    for _ in 0..6 {
        let mut sums = vec![[0.0f32; 3]; centers.len()];
        let mut counts = vec![0usize; centers.len()];
        for value in border {
            let index = centers
                .iter()
                .enumerate()
                .min_by(|a, b| distance(*value, *a.1).total_cmp(&distance(*value, *b.1)))
                .unwrap()
                .0;
            // Do not drag centers toward isolated outliers after robust seeding.
            if distance(*value, centers[index]) > 0.12 {
                continue;
            }
            counts[index] += 1;
            for (sum, v) in sums[index].iter_mut().zip(value) {
                *sum += v;
            }
        }
        for i in 0..centers.len() {
            if counts[i] > 0 {
                centers[i] = sums[i].map(|v| v / counts[i] as f32);
            }
        }
    }
    centers
}

fn segment(
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    enclosure: &RegionShape,
    cancel: &AtomicBool,
) -> anyhow::Result<Selection> {
    enclosure.validate()?;
    recipe.validate()?;
    anyhow::ensure!(
        image.width > 0
            && image.height > 0
            && image.pixels.len() == image.width as usize * image.height as usize * 3,
        "Invalid photograph dimensions"
    );
    check_cancel(cancel)?;
    let (min, max) = enclosure.bounds();
    let source = [
        (max[0] - min[0]) * image.width as f32,
        (max[1] - min[1]) * image.height as f32,
    ];
    let scale = (MAX_SIDE as f32 / source[0].max(source[1]).max(1.0)).min(1.0);
    let w = (source[0] * scale).ceil().max(1.0) as usize;
    let h = (source[1] * scale).ceil().max(1.0) as usize;
    let step = [(max[0] - min[0]) / w as f32, (max[1] - min[1]) / h as f32];
    let mut colors = vec![[0.0; 3]; w * h];
    let mut inside = vec![false; w * h];
    let mut boundary = vec![false; w * h];
    let mut border = Vec::new();
    for y in 0..h {
        check_cancel(cancel)?;
        for x in 0..w {
            let at = [
                min[0] + (x as f32 + 0.5) * step[0],
                min[1] + (y as f32 + 0.5) * step[1],
            ];
            let i = y * w + x;
            if !enclosure.contains(at) {
                continue;
            }
            inside[i] = true;
            // Four samples per bounded cell suppress isolated source pixels;
            // sampling/development never traverses a full-resolution photograph.
            let mut color = [0.0f32; 3];
            for dy in [-0.25, 0.25] {
                for dx in [-0.25, 0.25] {
                    let px = ((at[0] + dx * step[0]) * image.width as f32)
                        .floor()
                        .clamp(0.0, image.width as f32 - 1.0) as usize;
                    let py = ((at[1] + dy * step[1]) * image.height as f32)
                        .floor()
                        .clamp(0.0, image.height as f32 - 1.0)
                        as usize;
                    let index = py * image.width as usize + px;
                    let scene = image.origin == strehl_edit::ImageOrigin::SceneLinear;
                    let pixel = if scene {
                        image.developed_pixel(index, recipe)
                    } else {
                        image.display_pixel(index, recipe)
                    };
                    anyhow::ensure!(
                        pixel.iter().all(|v| v.is_finite()),
                        "Non-finite pixel in the selected area"
                    );
                    for c in 0..3 {
                        let v = pixel[c].max(0.0);
                        let compressed = v / (1.0 + v);
                        color[c] += if scene {
                            compressed.sqrt() * 0.25
                        } else {
                            compressed * 0.25
                        };
                    }
                }
            }
            colors[i] = color;
            // A missing outside-image neighbor is NOT evidence of background.
            boundary[i] = [(-1.0, 0.0), (1.0, 0.0), (0.0, -1.0), (0.0, 1.0)]
                .iter()
                .any(|(dx, dy)| {
                    let p = [at[0] + dx * step[0] * 1.5, at[1] + dy * step[1] * 1.5];
                    p.iter().all(|v| (0.0..=1.0).contains(v)) && !enclosure.contains(p)
                });
            if boundary[i] {
                border.push(color);
            }
        }
    }
    let empty = || Selection {
        shapes: Vec::new(),
        skipped_holes: 0,
        closed_gaps: 0,
        omitted_components: 0,
        core_refinements: 0,
        #[cfg(test)]
        sampling_grid: [w, h],
        #[cfg(test)]
        sampled_pixels: inside.iter().filter(|v| **v).count() * 4,
    };
    if border.len() < 12 || inside.iter().filter(|v| **v).count() < 24 {
        return Ok(empty());
    }
    let centers = background_model(&border);
    let mut residual = border
        .iter()
        .map(|v| background_distance(*v, &centers))
        .collect::<Vec<_>>();
    residual.sort_by(f32::total_cmp);
    // Contrast and boundary scatter, not a claim of probability or image quality.
    let threshold = (residual[residual.len() * 9 / 10] * 2.5).max(0.028);
    let mut distances = vec![0.0; w * h];
    let mut raw = vec![false; w * h];
    for y in 0..h {
        check_cancel(cancel)?;
        for x in 0..w {
            let i = y * w + x;
            distances[i] = background_distance(colors[i], &centers);
            raw[i] = inside[i] && distances[i] > threshold;
        }
    }
    let mut mask = vec![false; w * h];
    for y in 0..h {
        check_cancel(cancel)?;
        for x in 0..w {
            let mut count = 0;
            for yy in y.saturating_sub(1)..=(y + 1).min(h - 1) {
                for xx in x.saturating_sub(1)..=(x + 1).min(w - 1) {
                    count += usize::from(raw[yy * w + xx]);
                }
            }
            // Cleanup may remove sparse differences; it must never bridge a
            // real dark/colored gap between separately enclosed structures.
            mask[y * w + x] = raw[y * w + x] && count >= 5;
        }
    }
    let inside_count = inside.iter().filter(|v| **v).count();
    if mask.iter().filter(|v| **v).count() * 100 > inside_count * 85 {
        return Ok(empty());
    }
    let minimum = (inside_count / 1000).max(10);
    let mut seen = vec![false; w * h];
    let mut components = Vec::new();
    for i in 0..w * h {
        if !mask[i] || seen[i] {
            continue;
        }
        check_cancel(cancel)?;
        let mut cells = vec![i];
        seen[i] = true;
        let mut head = 0;
        while head < cells.len() {
            let p = cells[head];
            head += 1;
            for n in neighbors(p, w, h) {
                if mask[n] && !seen[n] {
                    seen[n] = true;
                    cells.push(n);
                }
            }
            if head % 1024 == 0 {
                check_cancel(cancel)?;
            }
        }
        // A component cut by the drawn boundary is not an enclosed object.
        // Missing neighbors beyond the photograph were excluded from boundary.
        if cells.len() >= minimum && !cells.iter().any(|i| boundary[*i]) {
            components.push(cells);
        }
    }
    components.sort_by_key(|cells| std::cmp::Reverse(cells.len()));
    #[cfg(test)]
    if let Some(directory) = std::env::var_os("STREHL_MAGIC_TRACE") {
        let directory = PathBuf::from(directory);
        let _ = std::fs::create_dir_all(&directory);
        let mut preview = image::RgbImage::new(w as u32, h as u32);
        let mut scores = Vec::new();
        for y in 0..h {
            for x in 0..w {
                let i = y * w + x;
                let d = background_distance(colors[i], &centers);
                if inside[i] {
                    scores.push(d);
                }
                preview.put_pixel(
                    x as u32,
                    y as u32,
                    image::Rgb(if mask[i] {
                        [230, 220, 100]
                    } else {
                        colors[i].map(|v| (v * 255.0) as u8)
                    }),
                );
            }
        }
        scores.sort_by(f32::total_cmp);
        let _ = preview.save(directory.join("candidate-mask.png"));
        let quantiles = [50, 70, 80, 90, 95, 99, 100].map(|q| scores[(scores.len() - 1) * q / 100]);
        let _=std::fs::write(directory.join("candidate.json"),serde_json::to_vec_pretty(&serde_json::json!({"threshold":threshold,"centers":centers,"component_areas":components.iter().map(Vec::len).collect::<Vec<_>>(),"score_quantiles":quantiles})).unwrap());
    }
    let mut result = empty();
    result.omitted_components = components.len().saturating_sub(MAX_COMPONENTS);
    for cells in components.iter().take(MAX_COMPONENTS) {
        check_cancel(cancel)?;
        let Some(contour) = coherent_contour(cells, &distances, w, h, threshold, cancel)? else {
            result.skipped_holes += 1;
            continue;
        };
        let points = contour
            .points
            .iter()
            .map(|p| [min[0] + p[0] * step[0], min[1] + p[1] * step[1]])
            .collect::<Vec<_>>();
        let rect =
            egui::Rect::from_min_size(egui::Pos2::ZERO, egui::vec2(1.0 / step[0], 1.0 / step[1]));
        let points = super::regions::simplify_lasso(&points, rect);
        let shape = RegionShape::Polygon { points };
        // Simplification must not cut across a concave enclosure and acquire
        // unrelated image area. Permit at most one raster-cell edge discrepancy.
        let mut escaped = 0;
        for y in 0..h {
            check_cancel(cancel)?;
            for x in 0..w {
                if !inside[y * w + x]
                    && shape.contains([
                        min[0] + (x as f32 + 0.5) * step[0],
                        min[1] + (y as f32 + 0.5) * step[1],
                    ])
                {
                    escaped += 1;
                    if escaped > 1 {
                        break;
                    }
                }
            }
            if escaped > 1 {
                break;
            }
        }
        if escaped <= 1 && shape.validate().is_ok() {
            result.closed_gaps += contour.closed_gaps;
            result.core_refinements += usize::from(contour.refined);
            result.shapes.push(shape);
        }
    }
    Ok(result)
}

/// A hole-bearing candidate can have a solid, more distinctive core. Retrying
/// stronger *background difference* is symmetric for dark, bright and colored
/// objects. Never expand the candidate, bridge components or select tiny peaks.
fn coherent_contour(
    cells: &[usize],
    scores: &[f32],
    w: usize,
    h: usize,
    threshold: f32,
    cancel: &AtomicBool,
) -> anyhow::Result<Option<CoherentContour>> {
    let peak = cells.iter().map(|i| scores[*i]).fold(threshold, f32::max);
    for (attempt, fraction) in [0.0, 0.5, 0.75, 0.9].into_iter().enumerate() {
        check_cancel(cancel)?;
        let selected = if attempt == 0 {
            cells.to_vec()
        } else {
            let cutoff = threshold + (peak - threshold) * fraction;
            let mut raw = vec![false; w * h];
            for i in cells {
                raw[*i] = scores[*i] > cutoff;
            }
            let mut mask = vec![false; w * h];
            for i in cells {
                let x = i % w;
                let y = i / w;
                let mut count = 0;
                for yy in y.saturating_sub(1)..=(y + 1).min(h - 1) {
                    for xx in x.saturating_sub(1)..=(x + 1).min(w - 1) {
                        count += usize::from(raw[yy * w + xx]);
                    }
                }
                mask[*i] = raw[*i] && count >= 5;
            }
            let mut largest = Vec::new();
            for i in cells {
                if !mask[*i] {
                    continue;
                }
                let mut component = vec![*i];
                mask[*i] = false;
                let mut head = 0;
                while head < component.len() {
                    let p = component[head];
                    head += 1;
                    for next in neighbors(p, w, h) {
                        if mask[next] {
                            mask[next] = false;
                            component.push(next);
                        }
                    }
                    if head % 1024 == 0 {
                        check_cancel(cancel)?;
                    }
                }
                if component.len() > largest.len() {
                    largest = component;
                }
            }
            // A few isolated highlights are not a replacement for the object.
            if largest.len() * 5 < cells.len() * 2 {
                continue;
            }
            largest
        };
        let loops = contours(&selected, w, h);
        let Some(outer) = loops
            .iter()
            .max_by(|a, b| polygon_area(a).abs().total_cmp(&polygon_area(b).abs()))
        else {
            continue;
        };
        let holes = loops
            .iter()
            .filter(|path| !std::ptr::eq(*path, outer))
            .map(|path| polygon_area(path).abs())
            .collect::<Vec<_>>();
        // Explicit approximation budget: total enclosed gaps <=2% of selected
        // support (or two raster cells). Larger holes are never silently filled.
        if holes.iter().sum::<f32>() <= (selected.len() as f32 * 0.02).max(2.0) {
            return Ok(Some(CoherentContour {
                points: outer.clone(),
                closed_gaps: holes.len(),
                refined: attempt > 0,
            }));
        }
    }
    Ok(None)
}
fn neighbors(i: usize, w: usize, h: usize) -> impl Iterator<Item = usize> {
    [
        i.checked_sub(w),
        (i / w + 1 < h).then_some(i + w),
        (!i.is_multiple_of(w)).then(|| i - 1),
        (i % w + 1 < w).then_some(i + 1),
    ]
    .into_iter()
    .flatten()
}
fn polygon_area(path: &[[f32; 2]]) -> f32 {
    path.iter()
        .zip(path.iter().cycle().skip(1))
        .map(|(a, b)| a[0] * b[1] - b[0] * a[1])
        .sum::<f32>()
        * 0.5
}
fn contours(cells: &[usize], w: usize, h: usize) -> Vec<Vec<[f32; 2]>> {
    let mut mask = vec![false; w * h];
    for i in cells {
        mask[*i] = true;
    }
    let stride = w + 1;
    let mut edges = vec![Vec::<(usize, usize)>::new(); stride * (h + 1)];
    for i in cells {
        let x = i % w;
        let y = i / w;
        let a = y * stride + x;
        if y == 0 || !mask[i - w] {
            edges[a].push((a + 1, 0));
        }
        if x + 1 == w || !mask[i + 1] {
            edges[a + 1].push((a + stride + 1, 1));
        }
        if y + 1 == h || !mask[i + w] {
            edges[a + stride + 1].push((a + stride, 2));
        }
        if x == 0 || !mask[i - 1] {
            edges[a + stride].push((a, 3));
        }
    }
    let mut loops = Vec::new();
    for start in 0..edges.len() {
        while !edges[start].is_empty() {
            let mut at = start;
            let mut direction = 0;
            let mut path = Vec::new();
            loop {
                path.push([(at % stride) as f32, (at / stride) as f32]);
                let next = edges[at]
                    .iter()
                    .enumerate()
                    .min_by_key(|(_, (_, d))| match (*d + 4 - direction) % 4 {
                        1 => 0,
                        0 => 1,
                        3 => 2,
                        _ => 3,
                    })
                    .map(|(i, _)| i);
                let Some(next) = next else { break };
                let (target, d) = edges[at].swap_remove(next);
                at = target;
                direction = d;
                if at == start {
                    if path.len() >= 3 {
                        loops.push(path);
                    }
                    break;
                }
            }
        }
    }
    loops
}

#[cfg(test)]
#[path = "edit-magic-tests.rs"]
mod tests;
