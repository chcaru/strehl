//! Capture-index topology on its own photographic contact board. These coordinates are
//! frame order, never inferred image placement, optical flow, or pixel warps.
use crate::{
    pipeline::{AlignmentOutcome, AlignmentPhase, FrameObservation, Stage},
    process_space::Input,
    theme::{ACCENT, AMBER, GREEN, INK, LINE, MUTED, PANEL},
};
use eframe::egui::{self, Align2, Color32, FontId, Pos2, Rect, Sense, Stroke, Ui};

const EDGE_CAP: usize = 1024;
const NODE_CAP: usize = 256;
const CONTACT_CAP: usize = 48;

fn radius(rect: Rect) -> f32 {
    let side = rect.width().min(rect.height()).max(0.0);
    // When photographs cannot fit, give their space back to the index graph.
    // Keep the node ring circular in both arrangements.
    (side
        * if side < 196.0 && !compact_contacts_fit(rect) {
            0.44
        } else {
            0.20
        }
        - 3.0)
        .max(6.0)
}

fn compact_contacts_fit(diagram: Rect) -> bool {
    diagram.width() >= 150.0 && diagram.height() >= 116.0
}

pub(crate) fn position(rect: Rect, frame: usize, count: usize) -> Pos2 {
    let angle =
        -std::f32::consts::FRAC_PI_2 + std::f32::consts::TAU * frame as f32 / count.max(1) as f32;
    rect.center() + egui::vec2(angle.cos(), angle.sin()) * radius(rect)
}

pub(crate) fn diagram_rect(rect: Rect) -> Rect {
    Rect::from_min_max(
        rect.min + egui::vec2(5.0, 52.0),
        rect.max - egui::vec2(5.0, 52.0),
    )
}

/// The fixed photo slots that this exact aperture can actually paint. Compact
/// graph-only layouts must not advertise invisible contacts for prefetch.
pub(crate) fn visible_contact_indices(rect: Rect, count: usize) -> Vec<usize> {
    if count < 2 || rect.width() < 160.0 || rect.height() < 100.0 {
        return Vec::new();
    }
    let diagram = diagram_rect(rect);
    if diagram.height() < 40.0 {
        return Vec::new();
    }
    contacts(diagram, count)
        .into_iter()
        .map(|contact| contact.frame)
        .collect()
}

#[derive(Clone, Copy)]
struct Contact {
    frame: usize,
    image: Rect,
    caption: Rect,
    bounds: Rect,
}

#[derive(Clone)]
struct ContactRouting {
    diagram: Rect,
    count: usize,
    paths: Vec<Vec<Pos2>>,
}

/// Route leaders through the empty space between cards. In a wide or tall
/// panel, the extra shelves are beyond the first ring of photographs: a
/// straight node-to-card chord would disappear underneath those inner cards.
/// The small visibility graph is cached for this aperture, so normal progress
/// updates and hover never repeat its construction.
fn contact_routes(diagram: Rect, count: usize, cards: &[Contact]) -> Vec<Vec<Pos2>> {
    let obstacles: Vec<_> = cards.iter().map(|card| card.bounds.expand(2.0)).collect();
    let mut vertices = Vec::with_capacity(cards.len() * 4);
    for card in cards {
        let box_ = card.bounds.expand(3.0);
        vertices.extend([
            box_.left_top(),
            box_.right_top(),
            box_.right_bottom(),
            box_.left_bottom(),
        ]);
    }
    let clear = |a, b| {
        obstacles
            .iter()
            .all(|obstacle| !segment_crosses_box(a, b, *obstacle))
    };
    let mut graph = vec![Vec::<(usize, f32)>::new(); vertices.len()];
    for (a, &from) in vertices.iter().enumerate() {
        for (b, &to) in vertices.iter().enumerate().skip(a + 1) {
            if clear(from, to) {
                let distance = from.distance(to);
                graph[a].push((b, distance));
                graph[b].push((a, distance));
            }
        }
    }
    cards
        .iter()
        .map(|card| {
            let start = position(diagram, card.frame, count);
            let guard = card.bounds.expand(3.0);
            let finish = egui::pos2(
                start.x.clamp(guard.left(), guard.right()),
                start.y.clamp(guard.top(), guard.bottom()),
            );
            let dock = egui::pos2(
                finish.x.clamp(card.bounds.left(), card.bounds.right()),
                finish.y.clamp(card.bounds.top(), card.bounds.bottom()),
            );
            if clear(start, finish) {
                return vec![start, finish, dock];
            }
            let mut distances = vec![f32::INFINITY; vertices.len()];
            let mut previous = vec![None; vertices.len()];
            let mut visited = vec![false; vertices.len()];
            for (index, &at) in vertices.iter().enumerate() {
                if clear(start, at) {
                    distances[index] = start.distance(at);
                }
            }
            let mut best = f32::INFINITY;
            let mut terminal = None;
            while let Some(index) = (0..vertices.len())
                .filter(|&index| !visited[index] && distances[index].is_finite())
                .min_by(|&a, &b| distances[a].total_cmp(&distances[b]))
            {
                if distances[index] >= best {
                    break;
                }
                visited[index] = true;
                if clear(vertices[index], finish) {
                    let cost = distances[index] + vertices[index].distance(finish);
                    if cost < best {
                        best = cost;
                        terminal = Some(index);
                    }
                }
                for &(next, length) in &graph[index] {
                    let distance = distances[index] + length;
                    if distance < distances[next] {
                        distances[next] = distance;
                        previous[next] = Some(index);
                    }
                }
            }
            let Some(mut index) = terminal else {
                // Never replace a missing route with an occluded, misleading
                // chord. Contact placement leaves all corners navigable.
                return Vec::new();
            };
            let mut path = vec![dock, finish, vertices[index]];
            while let Some(parent) = previous[index] {
                index = parent;
                path.push(vertices[index]);
            }
            path.push(start);
            path.reverse();
            path
        })
        .collect()
}

fn segment_crosses_box(from: Pos2, to: Pos2, rect: Rect) -> bool {
    let direction = to - from;
    let mut near = 0.0_f32;
    let mut far = 1.0_f32;
    for (origin, delta, low, high) in [
        (from.x, direction.x, rect.left(), rect.right()),
        (from.y, direction.y, rect.top(), rect.bottom()),
    ] {
        if delta.abs() < 0.0001 {
            if origin < low || origin > high {
                return false;
            }
        } else {
            let a = (low - origin) / delta;
            let b = (high - origin) / delta;
            near = near.max(a.min(b));
            far = far.min(a.max(b));
            if near > far {
                return false;
            }
        }
    }
    near <= far
}

/// A circular index with photographic shelves in the spare aspect-ratio area.
/// Density depends only on the user's aperture, never on cache arrival, stage,
/// or the current pair. The shelves add source context without stretching the
/// graph or shrinking photographs into unreadable dots.
fn contacts(diagram: Rect, count: usize) -> Vec<Contact> {
    let side = diagram.width().min(diagram.height());
    if count < 2 {
        return Vec::new();
    }
    if side < 196.0 {
        if !compact_contacts_fit(diagram) {
            return Vec::new();
        }
        let width = 40.0;
        let height = width * (2.0 / 3.0);
        let block = egui::vec2(width, height + 15.0);
        let inset = diagram.shrink(3.0);
        let origins = [
            inset.left_top(),
            inset.right_top() - egui::vec2(block.x, 0.0),
            inset.right_bottom() - block,
            inset.left_bottom() - egui::vec2(0.0, block.y),
        ];
        let shown = count.min(4);
        return (0..shown)
            .map(|slot| {
                let bounds = Rect::from_min_size(origins[slot * 4 / shown], block);
                let image = Rect::from_min_size(bounds.min, egui::vec2(width, height));
                Contact {
                    frame: slot * count / shown,
                    image,
                    caption: Rect::from_min_max(
                        image.left_bottom() + egui::vec2(0.0, 2.0),
                        bounds.max,
                    ),
                    bounds,
                }
            })
            .collect();
    }
    let width = (side / 4.8).clamp(40.0, 76.0);
    let height = width * (2.0 / 3.0);
    let block = egui::vec2(width, height + 15.0);
    let orbit = side * 0.5 - block.x.max(block.y) * 0.5 - 5.0;
    let mut centers = Vec::new();
    for shown in (2..=count.min(24)).rev() {
        let trial: Vec<_> = (0..shown)
            .map(|slot| {
                let angle = -std::f32::consts::FRAC_PI_2
                    + std::f32::consts::TAU * slot as f32 / shown as f32;
                diagram.center() + egui::vec2(angle.cos(), angle.sin()) * orbit
            })
            .collect();
        if trial.iter().enumerate().all(|(i, center)| {
            let rect = Rect::from_center_size(*center, block).expand(3.0);
            diagram.contains_rect(rect)
                && trial[i + 1..].iter().all(|other| {
                    !rect.intersects(Rect::from_center_size(*other, block).expand(3.0))
                })
        }) {
            centers = trial;
            break;
        }
    }
    let square = Rect::from_center_size(diagram.center(), egui::vec2(side, side));
    let stride = block + egui::vec2(8.0, 8.0);
    let cols = ((diagram.width() - 8.0) / stride.x).floor().max(0.0) as usize;
    let rows = ((diagram.height() - 8.0) / stride.y).floor().max(0.0) as usize;
    let mut spare = Vec::new();
    for row in 0..rows {
        for col in 0..cols {
            let center = diagram.center()
                + egui::vec2(
                    (col as f32 - (cols as f32 - 1.0) * 0.5) * stride.x,
                    (row as f32 - (rows as f32 - 1.0) * 0.5) * stride.y,
                );
            let bounds = Rect::from_center_size(center, block);
            if !bounds.expand(4.0).intersects(square) && diagram.contains_rect(bounds.expand(3.0)) {
                spare.push(center);
            }
        }
    }
    let extra = count
        .saturating_sub(centers.len())
        .min(CONTACT_CAP.saturating_sub(centers.len()))
        .min(spare.len());
    for slot in 0..extra {
        centers.push(spare[slot * spare.len() / extra]);
    }
    centers.sort_by(|a, b| {
        let angle = |p: Pos2| {
            ((p.y - diagram.center().y).atan2(p.x - diagram.center().x)
                + std::f32::consts::FRAC_PI_2)
                .rem_euclid(std::f32::consts::TAU)
        };
        angle(*a).total_cmp(&angle(*b))
    });
    centers
        .iter()
        .enumerate()
        .map(|(slot, &center)| {
            let frame = slot * count / centers.len();
            let bounds = Rect::from_center_size(center, block);
            let image = Rect::from_min_size(bounds.min, egui::vec2(width, height));
            Contact {
                frame,
                image,
                caption: Rect::from_min_max(image.left_bottom() + egui::vec2(0.0, 2.0), bounds.max),
                bounds,
            }
        })
        .collect()
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Pick {
    Frame(usize),
    Pair([usize; 2]),
}

fn nodes(count: usize) -> Vec<usize> {
    let shown = count.min(NODE_CAP);
    if shown < 2 {
        return (0..shown).collect();
    }
    (0..shown)
        .map(|index| index * (count - 1) / (shown - 1))
        .collect()
}

#[derive(Default)]
struct Links {
    accepted: usize,
    refused: usize,
    unknown: usize,
}

fn links(input: &Input<'_>, frame: usize) -> Links {
    let mut result = Links::default();
    for edge in &input.progress.alignment_edge_observations {
        if edge.pair[0] >= edge.pair[1]
            || edge.pair[1] >= input.frame_count
            || !edge.pair.contains(&frame)
        {
            continue;
        }
        match edge.outcome {
            AlignmentOutcome::Accepted => result.accepted += 1,
            AlignmentOutcome::Refused => result.refused += 1,
            AlignmentOutcome::Unknown => result.unknown += 1,
        }
    }
    result
}

fn frame_at(diagram: Rect, pointer: Pos2, count: usize) -> usize {
    let offset = pointer - diagram.center();
    let angle =
        (offset.y.atan2(offset.x) + std::f32::consts::FRAC_PI_2).rem_euclid(std::f32::consts::TAU);
    ((angle / std::f32::consts::TAU * count as f32).round() as usize) % count.max(1)
}

fn ring_hit(diagram: Rect, pointer: Pos2) -> bool {
    (pointer.distance(diagram.center()) - radius(diagram)).abs() <= 8.0
}

fn folded(input: &Input<'_>, frame: usize) -> Option<(usize, usize)> {
    let bands = input.progress.bands?.min(64);
    if bands == 0 {
        return None;
    }
    let observation = input.progress.merge_frame_observations.get(&frame)?;
    let mask = u64::MAX >> (64 - bands);
    Some((
        (observation.fold_finished & mask).count_ones() as usize,
        bands,
    ))
}

fn photo_hint(input: &Input<'_>, frame: usize) -> String {
    let evidence = links(input, frame);
    let prepared = input
        .progress
        .alignment_pyramid_observations
        .contains(&frame);
    let read = input.progress.alignment_plane_observations.contains(&frame);
    let merge = folded(input, frame).map_or_else(
        || "No detail-fold observations".to_owned(),
        |(done, total)| format!("{done}/{total} detail sizes folded"),
    );
    format!(
        "Capture {:03}\n{} · {}\n{} accepted / {} refused / {} unknown observed direct fits\n{merge}\n{} · drag the index ring to scrub · arrows to step",
        frame + 1,
        if read {
            "RAW read"
        } else {
            "RAW read unobserved"
        },
        if prepared {
            "scales ready"
        } else {
            "scales unobserved"
        },
        evidence.accepted,
        evidence.refused,
        evidence.unknown,
        if input.output.is_some() {
            "Click to highlight contribution"
        } else {
            "Click to inspect capture"
        }
    )
}

/// Explicit selection links the board to the rest of the workspace. Hover only
/// traces incident comparisons locally; a ring drag can reach every capture,
/// including identities whose photograph is not sampled on the contact board.
pub(crate) fn show(ui: &mut Ui, rect: Rect, input: &Input<'_>) -> Option<Pick> {
    let count = input.frame_count;
    if count < 2 || rect.width() < 160.0 || rect.height() < 100.0 {
        return None;
    }
    let alignment = matches!(input.progress.stage, Stage::Preparing | Stage::Alignment);
    let visibility = ui.ctx().animate_bool_with_time(
        ui.id().with(("capture-network-visibility", input.epoch)),
        alignment,
        0.45,
    );
    let p = ui.painter_at(rect);
    p.rect_filled(rect, 0.0, PANEL);
    p.text(
        rect.left_top() + egui::vec2(8.0, 6.0),
        Align2::LEFT_TOP,
        "CAPTURES / DIRECT FITS",
        FontId::proportional(11.0),
        INK,
    );
    let edges = &input.progress.alignment_edge_observations;
    let total = input.progress.alignment_pairs.map_or_else(
        || format!("{} OBSERVED", edges.len()),
        |(done, accepted, planned)| format!("{done}/{planned} PAIRS · {accepted} FITS"),
    );
    p.text(
        rect.left_top() + egui::vec2(8.0, 24.0),
        Align2::LEFT_TOP,
        total,
        FontId::monospace(8.5),
        MUTED,
    );
    let diagram = diagram_rect(rect);
    if diagram.height() < 40.0 {
        return None;
    }
    let graph_hit = ui.interact(
        diagram,
        ui.id().with("network-observed-edge"),
        Sense::click_and_drag(),
    );
    let released = ui.input(|i| i.pointer.button_released(egui::PointerButton::Primary));
    let contacts = contacts(diagram, count);
    let pointer = ui
        .input(|i| i.pointer.hover_pos())
        .filter(|p| diagram.contains(*p));
    let hovered = pointer.and_then(|point| {
        contacts
            .iter()
            .find(|c| c.bounds.contains(point))
            .map(|c| c.frame)
            .or_else(|| ring_hit(diagram, point).then(|| frame_at(diagram, point, count)))
    });
    let inspected = hovered.unwrap_or(input.selected.min(count - 1));
    let focus_links = links(input, inspected);
    let fold = folded(input, inspected).map_or(String::new(), |(done, total)| {
        format!(" · {done}/{total} sizes")
    });
    p.text(
        rect.left_top() + egui::vec2(8.0, 38.0),
        Align2::LEFT_TOP,
        format!(
            "{:03} · {} fit / {} refused{fold}",
            inspected + 1,
            focus_links.accepted,
            focus_links.refused
        ),
        FontId::monospace(7.0),
        if hovered.is_some() { ACCENT } else { MUTED },
    );
    // This fixed orbit describes every capture in source order. Read and scale
    // preparation marks are keyed by actual identities, not a count prefix.
    let orbit: Vec<_> = (0..=96)
        .map(|index| {
            let angle = -std::f32::consts::FRAC_PI_2 + std::f32::consts::TAU * index as f32 / 96.0;
            diagram.center() + egui::vec2(angle.cos(), angle.sin()) * radius(diagram)
        })
        .collect();
    p.add(egui::Shape::line(
        orbit,
        Stroke::new(
            0.8_f32,
            Color32::from_white_alpha((14.0 + 34.0 * visibility).round() as u8),
        ),
    ));
    let route_id = ui.id().with("network-contact-routes");
    let mut routing = ui.data(|data| data.get_temp::<ContactRouting>(route_id));
    if routing
        .as_ref()
        .is_none_or(|routing| routing.diagram != diagram || routing.count != count)
    {
        routing = Some(ContactRouting {
            diagram,
            count,
            paths: contact_routes(diagram, count, &contacts),
        });
        ui.data_mut(|data| data.insert_temp(route_id, routing.clone().unwrap()));
    }
    for (contact, path) in contacts.iter().zip(&routing.as_ref().unwrap().paths) {
        let color = if contact.frame == inspected {
            ACCENT.gamma_multiply(0.75)
        } else {
            LINE
        };
        for pair in path.windows(2) {
            p.line_segment([pair[0], pair[1]], Stroke::new(0.7_f32, color));
        }
    }

    let valid = |pair: [usize; 2]| pair[0] < pair[1] && pair[1] < count;
    let mut shown = 0;
    for edge in edges.iter().take(EDGE_CAP) {
        if !valid(edge.pair) {
            continue;
        }
        let base = match edge.outcome {
            AlignmentOutcome::Accepted => GREEN,
            AlignmentOutcome::Refused => AMBER,
            AlignmentOutcome::Unknown => MUTED,
        };
        let incident = edge.pair.contains(&inspected);
        let alpha = if hovered.is_some() && !incident {
            14
        } else if incident {
            (80.0 + 76.0 * visibility).round() as u8
        } else {
            (35.0 + 28.0 * visibility).round() as u8
        };
        let color = Color32::from_rgba_unmultiplied(base.r(), base.g(), base.b(), alpha);
        p.line_segment(
            [
                position(diagram, edge.pair[0], count),
                position(diagram, edge.pair[1], count),
            ],
            Stroke::new(if incident { 1.25_f32 } else { 0.8_f32 }, color),
        );
        shown += 1;
    }
    let displayed_nodes = nodes(count);
    let mut chosen = None;
    for frame in displayed_nodes {
        let at = position(diagram, frame, count);
        let read = input.progress.alignment_plane_observations.contains(&frame);
        let scales = input
            .progress
            .alignment_pyramid_observations
            .contains(&frame);
        let color = if scales {
            GREEN
        } else if read {
            ACCENT
        } else {
            MUTED
        };
        let alpha = if scales || read {
            200
        } else {
            (35.0 + 25.0 * visibility).round() as u8
        };
        p.circle_filled(
            at,
            if scales || read { 2.0 } else { 1.2 },
            Color32::from_rgba_unmultiplied(color.r(), color.g(), color.b(), alpha),
        );
        if scales {
            p.circle_stroke(
                at,
                3.2,
                Stroke::new(
                    0.7_f32,
                    Color32::from_rgba_unmultiplied(GREEN.r(), GREEN.g(), GREEN.b(), 130),
                ),
            );
        }
        if let Some((done, total)) = folded(input, frame) {
            let offset = (at - diagram.center()).normalized();
            let start = at + offset * 6.0;
            p.line_segment([start, start + offset * 6.0], Stroke::new(1.0_f32, LINE));
            if done > 0 {
                p.line_segment(
                    [start, start + offset * (6.0 * done as f32 / total as f32)],
                    Stroke::new(1.4_f32, GREEN),
                );
            }
        } else if input.progress.frame_observations.get(&frame)
            == Some(&FrameObservation::Processed)
        {
            // A whole-frame receipt does not invent any absent per-band receipts.
            p.circle_filled(at + (at - diagram.center()).normalized() * 8.0, 1.2, GREEN);
        }
        if frame == inspected {
            p.circle_stroke(at, 5.5, Stroke::new(1.0_f32, ACCENT));
        }
    }
    let selected_pair = input
        .inspected_pair
        .or(input.progress.alignment_current_pair)
        .or(input.progress.alignment_latest_pair)
        .filter(|pair| valid(*pair));
    if let Some(pair) = selected_pair {
        let current = input.progress.stage == Stage::Alignment
            && input.progress.alignment_phase == Some(AlignmentPhase::Pairs)
            && input.inspected_pair.is_none()
            && input.progress.alignment_current_pair == Some(pair);
        let color = Color32::from_rgba_unmultiplied(
            ACCENT.r(),
            ACCENT.g(),
            ACCENT.b(),
            (38.0 + 187.0 * visibility).round() as u8,
        );
        let points = pair.map(|frame| position(diagram, frame, count));
        p.line_segment(points, Stroke::new(0.8 + visibility, color));
        for (slot, (&frame, at)) in pair.iter().zip(points).enumerate() {
            p.circle_stroke(at, 5.0, Stroke::new(1.3_f32, color));
            p.circle_filled(at, 2.2, color);
            let label = format!("{} {:03}", if slot == 0 { "A" } else { "B" }, frame + 1);
            let label_rect = Rect::from_min_size(
                egui::pos2(
                    rect.left() + 8.0 + slot as f32 * (rect.width() - 16.0) * 0.5,
                    rect.bottom() - 49.0,
                ),
                egui::vec2((rect.width() - 16.0) * 0.5, 13.0),
            );
            p.text(
                label_rect.left_top(),
                Align2::LEFT_TOP,
                label,
                FontId::monospace(9.0),
                if current || input.inspected_pair.is_some() {
                    ACCENT
                } else {
                    MUTED
                },
            );
            let hit = ui.interact(
                label_rect,
                ui.id().with(("network-endpoint", slot)),
                Sense::click(),
            );
            if hit.clicked() && released {
                chosen = Some(Pick::Frame(frame));
                graph_hit.request_focus();
            }
            hit.on_hover_text(format!(
                "Capture {} / {}",
                frame + 1,
                if input.output.is_some() {
                    "click to highlight its contribution on the photograph"
                } else {
                    "click to inspect its actual camera preview"
                }
            ));
        }
        let observed = edges
            .iter()
            .find(|edge| edge.pair == pair)
            .map(|edge| match edge.outcome {
                AlignmentOutcome::Accepted => "ACCEPTED",
                AlignmentOutcome::Refused => "REFUSED",
                AlignmentOutcome::Unknown => "OUTCOME UNKNOWN",
            });
        p.text(
            egui::pos2(rect.left() + 8.0, rect.bottom() - 33.0),
            Align2::LEFT_TOP,
            if input.inspected_pair.is_some() {
                "INSPECTED DIRECT PAIR"
            } else if current {
                "DIRECT COMPARISON IN PROGRESS"
            } else {
                "LAST OBSERVED DIRECT PAIR"
            },
            FontId::monospace(7.0),
            MUTED,
        );
        if rect.width() >= 280.0 {
            p.text(
                egui::pos2(rect.right() - 8.0, rect.bottom() - 49.0),
                Align2::RIGHT_TOP,
                format!("SPAN {}", pair[1] - pair[0]),
                FontId::monospace(7.0),
                MUTED,
            );
        }
        if let Some(outcome) = observed.filter(|_| count <= NODE_CAP) {
            p.text(
                egui::pos2(rect.left() + 8.0, rect.bottom() - 23.0),
                Align2::LEFT_TOP,
                outcome,
                FontId::monospace(7.0),
                if outcome == "ACCEPTED" { GREEN } else { AMBER },
            );
        }
    }
    if edges.len() > EDGE_CAP || input.progress.alignment_edge_history_omitted > 0 {
        let omitted = input.progress.alignment_edge_history_omitted;
        let disclosure = if omitted > 0 {
            format!(
                "{shown}/{} EDGES SHOWN · +{omitted} HISTORY OMITTED",
                edges.len()
            )
        } else {
            format!("{shown}/{} OBSERVED EDGES SHOWN", edges.len())
        };
        p.text(
            rect.left_bottom() + egui::vec2(8.0, if count > NODE_CAP { -13.0 } else { -5.0 }),
            Align2::LEFT_BOTTOM,
            disclosure,
            FontId::monospace(6.5),
            MUTED,
        );
    } else {
        p.text(
            rect.left_bottom() + egui::vec2(8.0, if count > NODE_CAP { -13.0 } else { -5.0 }),
            Align2::LEFT_BOTTOM,
            "READ / SCALES / FOLD · DRAG RING",
            FontId::monospace(7.0),
            MUTED,
        );
    }
    if count > NODE_CAP {
        p.text(
            rect.left_bottom() + egui::vec2(8.0, -3.0),
            Align2::LEFT_BOTTOM,
            format!("{NODE_CAP}/{count} NODE MARKERS"),
            FontId::monospace(7.0),
            MUTED,
        );
    }
    // Fixed, equally spaced display slots prevent rounded-down sampled indices
    // from clustering adjacent photographs. Leaders carry their real identity.
    for contact in &contacts {
        let frame = contact.frame;
        let card = contact.image;
        let paired = selected_pair.is_some_and(|pair| pair.contains(&frame));
        let focused = frame == inspected;
        p.rect_filled(card.expand(2.0), 0.0, PANEL);
        if let Some(photo) = input
            .photos
            .iter()
            .find(|photo| photo.epoch == input.epoch && photo.index == frame)
        {
            let size = photo.texture.size_vec2();
            let aspect = card.aspect_ratio();
            let uv = if size.x / size.y > aspect {
                let inset = (1.0 - aspect * size.y / size.x) * 0.5;
                Rect::from_min_max(egui::pos2(inset, 0.0), egui::pos2(1.0 - inset, 1.0))
            } else {
                let inset = (1.0 - size.x / (size.y * aspect)) * 0.5;
                Rect::from_min_max(egui::pos2(0.0, inset), egui::pos2(1.0, 1.0 - inset))
            };
            p.image(photo.texture.id(), card, uv, Color32::WHITE);
        }
        p.rect_stroke(
            card,
            0.0,
            Stroke::new(1.0_f32, if paired || focused { ACCENT } else { LINE }),
            egui::StrokeKind::Inside,
        );
        if input.progress.alignment_plane_observations.contains(&frame) {
            p.line_segment(
                [card.left_top(), card.left_top() + egui::vec2(12.0, 0.0)],
                Stroke::new(1.0_f32, ACCENT),
            );
        }
        if input
            .progress
            .alignment_pyramid_observations
            .contains(&frame)
        {
            p.line_segment(
                [card.left_top(), card.left_bottom()],
                Stroke::new(1.0_f32, GREEN),
            );
        }
        p.text(
            contact.caption.left_top(),
            Align2::LEFT_TOP,
            format!("{:03}", frame + 1),
            FontId::monospace(7.5),
            if paired || focused { ACCENT } else { MUTED },
        );
        if let Some((done, total)) = folded(input, frame) {
            let track = Rect::from_min_size(
                contact.bounds.left_bottom() - egui::vec2(0.0, 2.0),
                egui::vec2(card.width(), 1.5),
            );
            p.rect_filled(track, 0.0, LINE);
            if done > 0 {
                p.rect_filled(
                    Rect::from_min_size(
                        track.min,
                        egui::vec2(track.width() * done as f32 / total as f32, track.height()),
                    ),
                    0.0,
                    GREEN,
                );
            }
        }
        let contact_hit = ui
            .interact(
                contact.bounds,
                ui.id().with(("network-contact", frame)),
                Sense::click(),
            )
            .on_hover_cursor(egui::CursorIcon::PointingHand);
        if contact_hit.hovered() {
            contact_hit.clone().on_hover_text(photo_hint(input, frame));
        }
        if contact_hit.clicked() && released {
            chosen = Some(Pick::Frame(frame));
            graph_hit.request_focus();
        }
        contact_hit.context_menu(|ui| {
            ui.label(format!("Capture {:03}", frame + 1));
            if ui
                .button(if input.output.is_some() {
                    "Highlight capture contribution"
                } else {
                    "Show in viewer"
                })
                .clicked()
            {
                chosen = Some(Pick::Frame(frame));
                ui.close();
            }
            let incident: Vec<_> = edges
                .iter()
                .filter(|edge| valid(edge.pair) && edge.pair.contains(&frame))
                .collect();
            if !incident.is_empty() {
                ui.separator();
                ui.label("Observed direct comparisons");
                for edge in incident.iter().take(6) {
                    let status = match edge.outcome {
                        AlignmentOutcome::Accepted => "fit",
                        AlignmentOutcome::Refused => "refused",
                        AlignmentOutcome::Unknown => "unknown",
                    };
                    if ui
                        .button(format!(
                            "{:03} / {:03}  {status}",
                            edge.pair[0] + 1,
                            edge.pair[1] + 1
                        ))
                        .clicked()
                    {
                        chosen = Some(Pick::Pair(edge.pair));
                        ui.close();
                    }
                }
                if incident.len() > 6 {
                    ui.label(format!("{} more in the network", incident.len() - 6));
                }
            }
        });
    }
    if chosen.is_none()
        && graph_hit.clicked()
        && released
        && let Some(pointer) = graph_hit.interact_pointer_pos()
    {
        let frame = frame_at(diagram, pointer, count);
        if position(diagram, frame, count).distance(pointer) <= 5.0 {
            chosen = Some(Pick::Frame(frame));
        }
        let distance = |pair: [usize; 2]| {
            let [a, b] = pair.map(|frame| position(diagram, frame, count));
            let ab = b - a;
            let t = ((pointer - a).dot(ab) / ab.length_sq().max(0.001)).clamp(0.0, 1.0);
            pointer.distance(a + t * ab)
        };
        if chosen.is_none()
            && let Some(edge) = edges
                .iter()
                .take(EDGE_CAP)
                .filter(|edge| valid(edge.pair) && distance(edge.pair) < 4.0)
                .min_by(|a, b| distance(a.pair).total_cmp(&distance(b.pair)))
        {
            chosen = Some(Pick::Pair(edge.pair));
        }
        if chosen.is_none() && ring_hit(diagram, pointer) {
            chosen = Some(Pick::Frame(frame));
        }
    }
    if graph_hit.dragged()
        && ui
            .input(|i| i.pointer.press_origin())
            .is_some_and(|point| ring_hit(diagram, point))
        && let Some(pointer) = graph_hit.interact_pointer_pos()
        && pointer.distance(diagram.center()) > 12.0
    {
        let frame = frame_at(diagram, pointer, count);
        if frame != input.selected {
            chosen = Some(Pick::Frame(frame));
        }
        graph_hit.request_focus();
    }
    if graph_hit.has_focus() && ui.is_enabled() {
        let step = ui.input_mut(|i| {
            if i.consume_key(egui::Modifiers::NONE, egui::Key::Home) {
                Some(0)
            } else if i.consume_key(egui::Modifiers::NONE, egui::Key::End) {
                Some(count - 1)
            } else if i.consume_key(egui::Modifiers::NONE, egui::Key::ArrowRight) {
                Some((input.selected + 1).min(count - 1))
            } else if i.consume_key(egui::Modifiers::NONE, egui::Key::ArrowLeft) {
                Some(input.selected.saturating_sub(1))
            } else {
                None
            }
        });
        if let Some(frame) = step {
            chosen = Some(Pick::Frame(frame));
        }
    }
    if hovered.is_some() {
        graph_hit.clone().on_hover_cursor(egui::CursorIcon::Grab);
    }
    ui.interact(rect, ui.id().with("network-space-tooltip"), Sense::hover()).on_hover_text(
        "Capture-index network: nodes follow source frame order. Lines are actual observed direct comparisons: green accepted, amber refused, grey unknown. Node fill marks observed RAW reads; outer rings mark observed scale preparation. These positions do not represent fitted image transforms.");
    chosen
}

#[cfg(test)]
#[path = "process-network-tests.rs"]
mod tests;
