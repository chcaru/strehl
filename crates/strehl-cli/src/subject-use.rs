//! What the subject drives in the engine (plan S4,
//! `docs/proposals/2026-11-subject-highlights-and-detail-plan.md`): the
//! outline read from a capture's manifest (`plan.subject`) or from a file
//! (`strehl subject --out`, or another manifest), and the plane checker's
//! subject arm.
//!
//! The subject arm never changes what a stack renders. The stack's own group
//! measurement (whole frame, journaled, the one the render reads) decides
//! whether a group is assembled. When that measurement demotes a group, the
//! subject arm decides whether a retake is worth asking for: the same
//! measurement is judged again with the local disagreement taken over the
//! witness tiles that touch the subject only, so tiles outside it have no
//! vote. A demotion that then passes was confined to the backdrop: "backdrop
//! only", no retake. Faults of the whole group (a slipped shot, a
//! misregistered pair, levels) keep the stack's retake decision.
//!
//! The members are also registered on the subject's bounding region, and the
//! offsets reported beside the stack's. That registration does not vote: the
//! stack registers on the frame's central half and assembles at those
//! offsets, so a checker that judged its own offsets would pass groups the
//! stack folds to one shot. MEASURED on the close tiles (2026-11-24): the
//! subject's offsets differ from the stack's by one photosite in one member
//! in 10 of 285 groups, both ways (two stack slips cover the four parities
//! on the subject, six groups the stack assembles do not). Registering the
//! stack itself on the subject is a change to the gather's identity, left to
//! that work.

use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde_json::{Value, json};
use std::path::Path;
use strehl_core::pixel_shift::{self, MemberView};
use strehl_core::subject::{Ring, SubjectRegion};

use crate::pixel_shift_cmd::{GroupCheck, GroupMeasurement, ResidualMode};

/// Margin around the outline within which a 64 px tile still counts as the
/// subject's, sensor pixels: half a tile, so a tile the outline's edge
/// crosses always counts.
pub const MARGIN_PX: f64 = 32.0;

/// Witness tile edge, sensor pixels (as the group check).
const WITNESS_TILE: usize = 64;

/// Where the subject came from.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Origin {
    /// The capture's own manifest (`plan.subject`).
    Manifest,
    /// A file named on the command line.
    Given,
}

impl Origin {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Manifest => "manifest",
            Self::Given => "given",
        }
    }
}

/// A subject outline as the engine reads it.
#[derive(Clone, Debug)]
pub struct LoadedSubject {
    /// Normalised to the active area, even-odd.
    pub rings: Vec<Ring>,
    /// The focus position the outline is in the geometry of.
    pub reference_focus: Option<f64>,
    /// Magnification change per focus unit, ppm.
    pub rate_ppm: Option<f64>,
    pub origin: Origin,
}

impl LoadedSubject {
    /// The region over an active area of `active` pixels, grown by
    /// [`MARGIN_PX`].
    pub fn region(&self, active: [usize; 2]) -> SubjectRegion {
        SubjectRegion::new(&self.rings, active, MARGIN_PX)
    }

    /// The magnification of the plane at `focus` against the outline's.
    pub fn scale_at(&self, focus: Option<f64>) -> f64 {
        strehl_core::subject::plane_scale(self.rate_ppm, self.reference_focus, focus)
    }
}

/// Rings, reference focus and rate, as read.
type Parsed = (Vec<Ring>, Option<f64>, Option<f64>);

/// The subject in a manifest (`plan.subject`), a capture `Subject`, or the
/// subject JSON `strehl subject` writes; `None` when a manifest has none.
fn parse(v: &Value) -> Result<Option<Parsed>> {
    let s = if v.get("plan").is_some_and(Value::is_object) {
        &v["plan"]["subject"]
    } else {
        v
    };
    if s.is_null() {
        return Ok(None);
    }
    let rings = s["rings"]
        .as_array()
        .context("a subject has `rings`")?
        .iter()
        .map(|ring| -> Result<Ring> {
            let points = ring.as_array().context("a ring is a list of points")?;
            ensure!(points.len() >= 3, "a ring has at least 3 points");
            points
                .iter()
                .map(|p| -> Result<[f32; 2]> {
                    let (x, y) = (p[0].as_f64(), p[1].as_f64());
                    match (x, y) {
                        (Some(x), Some(y)) if x.is_finite() && y.is_finite() => {
                            Ok([x as f32, y as f32])
                        }
                        _ => anyhow::bail!("a point is [x, y]"),
                    }
                })
                .collect()
        })
        .collect::<Result<Vec<Ring>>>()?;
    let reference = s["reference_focus"].as_f64();
    let rate = s["rate_ppm"]
        .as_f64()
        .or_else(|| s["ppm_per_unit"].as_f64());
    Ok(Some((rings, reference, rate)))
}

fn read(path: &Path) -> Result<Value> {
    let text = std::fs::read_to_string(path).with_context(|| format!("read {}", path.display()))?;
    serde_json::from_str(&text).with_context(|| format!("parse {}", path.display()))
}

/// The subject in `path`: a capture's `manifest.json` (its `plan.subject`)
/// or an outline JSON with `rings`.
pub fn load(path: &Path) -> Result<LoadedSubject> {
    let (rings, reference_focus, rate_ppm) = parse(&read(path)?)
        .with_context(|| path.display().to_string())?
        .with_context(|| format!("{} has no subject (plan.subject)", path.display()))?;
    ensure!(
        !rings.is_empty(),
        "{}: the subject outline is empty",
        path.display()
    );
    Ok(LoadedSubject {
        rings,
        reference_focus,
        rate_ppm,
        origin: Origin::Given,
    })
}

/// The subject recorded in the capture folder's own manifest, if any. An
/// unreadable manifest or one without a subject reads as none.
pub fn from_manifest(dir: &Path) -> Option<LoadedSubject> {
    let v = read(&dir.join("manifest.json")).ok()?;
    let (rings, reference_focus, rate_ppm) = parse(&v).ok()??;
    (!rings.is_empty()).then_some(LoadedSubject {
        rings,
        reference_focus,
        rate_ppm,
        origin: Origin::Manifest,
    })
}

/// `--subject` when given, else the capture's manifest's subject.
pub fn resolve(dir: &Path, given: Option<&Path>) -> Result<Option<LoadedSubject>> {
    match given {
        Some(path) => load(path).map(Some),
        None => Ok(from_manifest(dir)),
    }
}

/// The plane checker's subject arm for one group (see the module notes).
#[derive(Clone, Debug)]
pub struct SubjectCheck {
    /// The plane's magnification against the outline's.
    pub scale: f64,
    /// Witness tiles touching the subject, and those of them measured.
    pub tiles: usize,
    pub tiles_measured: usize,
    /// p99 of the local disagreement (photosites) over the measured subject
    /// tiles, and over the measured tiles outside it (reported; no vote).
    /// `NaN` when there are none.
    pub local_px: f64,
    pub backdrop_local_px: f64,
    /// The stack's measurement judged with `local_px` in place of the whole
    /// frame's: reason, and whether a retake helps.
    pub demotion: Option<(String, bool)>,
    /// Registration on the subject's bounding region (`roi`, active pixels
    /// `[x, y, width, height]`): reported beside the stack's; no vote.
    pub roi: [isize; 4],
    pub registration: GroupCheck,
}

/// The retake decision weighted by the subject.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Weighted {
    pub retake: bool,
    /// The stack demotes the group but passes it on the subject's tiles.
    pub backdrop_only: bool,
}

/// The retake decision for a group the stack's gate demotes (`demoted`) or
/// passes: a passing group needs none; a demoted one that passes on the
/// subject's tiles is "backdrop only", with no retake; otherwise the
/// subject-weighted verdict's retake.
pub fn weigh(demoted: bool, sub: &SubjectCheck) -> Weighted {
    match (&sub.demotion, demoted) {
        (_, false) => Weighted {
            retake: false,
            backdrop_only: false,
        },
        (None, true) => Weighted {
            retake: false,
            backdrop_only: true,
        },
        (Some((_, retake)), true) => Weighted {
            retake: *retake,
            backdrop_only: false,
        },
    }
}

fn view(f: &strehl_raw::Frame) -> MemberView<'_> {
    MemberView {
        data: &f.data,
        stride: f.stride,
        buffer_height: f.buffer_height,
        active: [f.active.x, f.active.y, f.active.width, f.active.height],
        black: f.levels.black,
        white: f.levels.white,
    }
}

fn p99(mut v: Vec<f32>) -> f64 {
    v.retain(|x| x.is_finite());
    if v.is_empty() {
        return f64::NAN;
    }
    v.sort_by(f32::total_cmp);
    f64::from(v[((v.len() - 1) as f64 * 0.99) as usize])
}

/// The registration region on the subject: its bounding box in the plane's
/// geometry, even-aligned, inside the active area with room for the search
/// and block; the stack's central half when the subject is empty.
pub fn registration_roi(region: &SubjectRegion, scale: f64, active: [usize; 2]) -> [isize; 4] {
    let (w, h) = (active[0] as isize, active[1] as isize);
    let central = [w / 4, h / 4, w / 2, h / 2];
    let Some(b) = region.bounds(scale) else {
        return central;
    };
    // The search (2) and the block (8) read past the region's edges.
    const EDGE: isize = 16;
    let x0 = (b[0].floor() as isize).clamp(EDGE, w - EDGE - 64) & !1;
    let y0 = (b[1].floor() as isize).clamp(EDGE, h - EDGE - 64) & !1;
    let x1 = (b[2].ceil() as isize).clamp(x0 + 64, w - EDGE);
    let y1 = (b[3].ceil() as isize).clamp(y0 + 64, h - EDGE);
    [x0, y0, (x1 - x0) & !1, (y1 - y0) & !1]
}

/// Members 2-4 registered against member 1 on `roi`, as the stack's group
/// check does on the central half.
fn register_on(m: &[MemberView<'_>; 4], roi: [isize; 4]) -> GroupCheck {
    let reference = pixel_shift::Reference::new_in(&m[0], 2, roi);
    let fits: Vec<pixel_shift::Fit> = m[1..]
        .par_iter()
        .map(|member| reference.register(member, 2))
        .collect();
    let mut c = GroupCheck {
        offsets: [(0, 0); 4],
        precision: [1.0; 4],
        residual: [[0.0; 2]; 4],
        gains: [1.0; 4],
        parities: false,
    };
    for (k, fit) in (1..4).zip(fits) {
        c.offsets[k] = fit.offset;
        c.precision[k] = fit.structure;
        c.residual[k] = fit.residual;
        c.gains[k] = fit.gain;
    }
    c.parities = pixel_shift::covers_all_parities(&c.offsets);
    c
}

/// The stack's measurement judged with the subject's local disagreement
/// `local_px` (p99 over its tiles) in place of the whole frame's: every
/// other gate reads exactly what the stack read.
pub fn judge_on_subject(
    stack: &GroupMeasurement,
    local_px: f64,
    residual: ResidualMode,
) -> Option<(String, bool)> {
    let mut weighted = stack.clone();
    if let Some(s) = weighted.witness.as_mut() {
        s.local_px = local_px;
    }
    crate::pixel_shift_cmd::demotion(&weighted, residual)
}

/// The subject arm of the plane check for one complete four-member group:
/// `stack` is the stack's own measurement of the same members, and
/// `witness` its witness when the caller has it (it is measured again from
/// the stack's offsets and gains otherwise: the same sums).
#[allow(clippy::too_many_arguments)]
pub fn check_subject(
    frames: [&strehl_raw::Frame; 4],
    noise: &strehl_core::noise::NoiseModel,
    region: &SubjectRegion,
    scale: f64,
    stack: &GroupMeasurement,
    witness: Option<&pixel_shift::Witness>,
    residual: ResidualMode,
) -> SubjectCheck {
    let m = frames.map(view);
    let active = [frames[0].active.width, frames[0].active.height];
    let roi = registration_roi(region, scale, active);
    let registration = register_on(&m, roi);
    let c = &stack.check;
    let measured_here;
    let witness = match witness {
        Some(w) => Some(w),
        None if c.parities => {
            let variance = |s| noise.variance(strehl_core::CfaPlane::G1, s);
            measured_here =
                pixel_shift::witness_without_ptc(&m, &c.offsets, &c.gains, variance, WITNESS_TILE);
            Some(&measured_here)
        }
        None => None,
    };
    let (mut tiles, mut measured, mut local, mut backdrop) = (0, 0, f64::NAN, f64::NAN);
    if let Some(w) = witness {
        let mask = region.tiles(w.tile, w.tiles[0], w.tiles[1], scale);
        tiles = mask.iter().filter(|v| **v).count();
        let pick = |inside: bool| -> Vec<f32> {
            w.tile_local_px
                .iter()
                .zip(&mask)
                .filter(|(_, m)| **m == inside)
                .map(|(v, _)| *v)
                .collect()
        };
        let on = pick(true);
        measured = on.iter().filter(|v| v.is_finite()).count();
        local = p99(on);
        backdrop = p99(pick(false));
    }
    let demotion = judge_on_subject(stack, local, residual);
    SubjectCheck {
        scale,
        tiles,
        tiles_measured: measured,
        local_px: local,
        backdrop_local_px: backdrop,
        demotion,
        roi,
        registration,
    }
}

/// The subject arm as JSON (`subject_check` in `strehl follow`'s plane lines
/// and `gate.subject` in `strehl pixel-shift --json`).
pub fn check_json(sub: &SubjectCheck, stack: &GroupMeasurement) -> Value {
    let r = &sub.registration;
    json!({
        "scale": sub.scale,
        "local_px": sub.local_px,
        "backdrop_local_px": sub.backdrop_local_px,
        "tiles": sub.tiles,
        "tiles_measured": sub.tiles_measured,
        "reason": sub.demotion.as_ref().map(|d| d.0.clone()),
        "retake": sub.demotion.as_ref().is_some_and(|d| d.1),
        "registration": {
            "roi": sub.roi,
            "offsets": r.offsets,
            "structure": &r.precision[1..],
            "parities": r.parities,
            "agrees": r.offsets == stack.check.offsets,
        },
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn dir(name: &str) -> std::path::PathBuf {
        let d =
            std::env::temp_dir().join(format!("strehl-subject-use-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    /// A manifest's `plan.subject`, a subject JSON and a manifest without a
    /// subject all read as they should.
    #[test]
    fn subjects_load_from_a_manifest_or_an_outline() {
        let d = dir("load");
        let ring = json!([[0.2, 0.2], [0.6, 0.2], [0.6, 0.7], [0.2, 0.7]]);
        std::fs::write(
            d.join("manifest.json"),
            json!({"plan":{"start":10,"end":20,"step":1,"subject":{"rings":[ring],"reference_focus":15,"rate_ppm":-13.0}}}).to_string(),
        )
        .unwrap();
        let m = from_manifest(&d).unwrap();
        assert_eq!(m.origin, Origin::Manifest);
        assert_eq!((m.reference_focus, m.rate_ppm), (Some(15.0), Some(-13.0)));
        let outline = d.join("outline.json");
        std::fs::write(
            &outline,
            json!({"rings":[ring],"reference_focus":24000.0,"ppm_per_unit":-15.0,"cell_px":8.0})
                .to_string(),
        )
        .unwrap();
        let g = resolve(&d, Some(&outline)).unwrap().unwrap();
        assert_eq!(g.origin, Origin::Given);
        assert_eq!(
            (g.reference_focus, g.rate_ppm),
            (Some(24000.0), Some(-15.0))
        );
        assert_eq!(g.rings[0].len(), 4);
        let bare = dir("bare");
        std::fs::write(
            bare.join("manifest.json"),
            json!({"plan":{"start":10,"end":20,"step":1}}).to_string(),
        )
        .unwrap();
        assert!(from_manifest(&bare).is_none());
        assert!(resolve(&bare, None).unwrap().is_none());
        assert!(load(&bare.join("manifest.json")).is_err());
        let empty = d.join("empty.json");
        std::fs::write(&empty, json!({"rings":[]}).to_string()).unwrap();
        assert!(load(&empty).is_err());
        let _ = std::fs::remove_dir_all(&d);
        let _ = std::fs::remove_dir_all(&bare);
    }

    fn group(local_px: f64, offsets: [(isize, isize); 4]) -> GroupMeasurement {
        use crate::pixel_shift_cmd::WitnessSummary;
        GroupMeasurement {
            check: GroupCheck {
                offsets,
                precision: [1.0; 4],
                residual: [[0.0; 2]; 4],
                gains: [1.0; 4],
                parities: pixel_shift::covers_all_parities(&offsets),
            },
            witness: Some(WitnessSummary {
                pair_shift: [[0.0; 2]; 2],
                pair_members: [[0, 1], [2, 3]],
                tile_ratio: 1.0,
                local_px,
                local_tiles: 3200,
            }),
            margins: [8; 4],
            levels_agree: true,
        }
    }

    fn arm(stack: &GroupMeasurement, local_px: f64) -> SubjectCheck {
        SubjectCheck {
            scale: 1.0,
            tiles: 10,
            tiles_measured: 10,
            local_px,
            backdrop_local_px: f64::NAN,
            demotion: judge_on_subject(stack, local_px, ResidualMode::Compensate),
            roi: [0, 0, 64, 64],
            registration: stack.check.clone(),
        }
    }

    /// Tiles outside the subject have no vote on a retake: a local fault the
    /// subject's tiles do not share is "backdrop only"; one they share, and
    /// a whole-group fault, keep the stack's retake.
    #[test]
    fn backdrop_faults_ask_no_retake() {
        let r = ResidualMode::Compensate;
        let good = [(0, 0), (1, 0), (0, 1), (1, 1)];
        let moved = group(0.76, good);
        let stack = crate::pixel_shift_cmd::demotion(&moved, r);
        assert!(stack.as_ref().is_some_and(|d| d.1), "{stack:?}");
        let backdrop = weigh(true, &arm(&moved, 0.30));
        assert_eq!(
            backdrop,
            Weighted {
                retake: false,
                backdrop_only: true
            }
        );
        // No measured subject tile: nothing on the subject disagrees.
        assert!(weigh(true, &arm(&moved, f64::NAN)).backdrop_only);
        let subject = weigh(true, &arm(&moved, 0.70));
        assert!(subject.retake && !subject.backdrop_only);
        // A slipped shot is a fault of the whole group: still retaken.
        let slipped = group(0.20, [(0, 0), (1, 0), (1, 0), (1, 1)]);
        let s = weigh(true, &arm(&slipped, 0.10));
        assert!(s.retake && !s.backdrop_only);
        // A passing group needs no retake, whatever the subject reads.
        let fine = group(0.20, good);
        assert!(crate::pixel_shift_cmd::demotion(&fine, r).is_none());
        let f = weigh(false, &arm(&fine, 0.90));
        assert!(!f.retake && !f.backdrop_only);
    }

    /// Plants on real groups (plan S4's checker gate), read-only:
    /// `STREHL_S4_FIXTURES="<run dir>|<plane>|<subject json>;..."`. A
    /// 768 px patch of shot 3 moved 2 px, once where the backdrop has the
    /// most measured witness tiles and no subject tile within a tile of it,
    /// once about the subject's median measured tile.
    /// `cargo test --release -p strehl-cli --lib planted_backdrop -- --ignored --nocapture`
    #[test]
    #[ignore = "needs capture folders; set STREHL_S4_FIXTURES"]
    fn planted_backdrop_and_subject_faults_on_real_groups() {
        use crate::pixel_shift_cmd::{judge, measure_with_tiles, recorded_groups};
        let spec = std::env::var("STREHL_S4_FIXTURES").expect("STREHL_S4_FIXTURES");
        let r = ResidualMode::Compensate;
        let mut failures = Vec::new();
        for item in spec.split(';').filter(|s| !s.trim().is_empty()) {
            let parts: Vec<&str> = item.split('|').map(str::trim).collect();
            let (dir, plane, outline) = (parts[0], parts[1].parse::<u64>().unwrap(), parts[2]);
            let subject = load(Path::new(outline)).unwrap();
            let groups = recorded_groups(Path::new(dir)).unwrap();
            let g = groups
                .iter()
                .find(|g| g.plane == plane && g.complete)
                .unwrap();
            let frames: Vec<strehl_raw::Frame> = g
                .files
                .iter()
                .map(|f| strehl_raw::decode(&f.path).unwrap())
                .collect();
            let first = &frames[0];
            let noise = strehl_core::profile::noise_model_for(
                &first.camera,
                first.iso,
                strehl_core::noise::Levels {
                    black: first.levels.black,
                    white: first.levels.white,
                },
            );
            let region = subject.region([first.active.width, first.active.height]);
            let scale = subject.scale_at(g.target.map(|t| t as f64));
            let check = |f: [&strehl_raw::Frame; 4]| {
                let (m, w) = measure_with_tiles(f, &noise);
                let sub = check_subject(f, &noise, &region, scale, &m, w.as_ref(), r);
                let reason = judge(&m, r);
                (weigh(reason.is_some(), &sub), reason, m, sub, w)
            };
            let (_, taken, m0, _, w0) = check([&frames[0], &frames[1], &frames[2], &frames[3]]);
            let w0 = w0.expect("a witness");
            let (tw, th) = (w0.tiles[0], w0.tiles[1]);
            let mask = region.tiles(w0.tile, tw, th, scale);
            let measured = |i: usize| w0.tile_local_px[i].is_finite();
            // Where to plant: 12 x 12 tiles.
            let window = |cx: usize, cy: usize, grow: usize| {
                let (x0, y0) = (cx.saturating_sub(6 + grow), cy.saturating_sub(6 + grow));
                let (x1, y1) = ((cx + 6 + grow).min(tw), (cy + 6 + grow).min(th));
                (y0..y1).flat_map(move |y| (x0..x1).map(move |x| y * tw + x))
            };
            let backdrop = (0..tw * th)
                .filter(|&i| measured(i) && !mask[i])
                .filter(|&i| !window(i % tw, i / tw, 1).any(|j| mask[j]))
                .max_by_key(|&i| window(i % tw, i / tw, 0).filter(|&j| measured(j)).count());
            let mut on: Vec<usize> = (0..tw * th).filter(|&i| measured(i) && mask[i]).collect();
            on.sort_by_key(|&i| (i / tw, i % tw));
            let subject_tile = on.get(on.len() / 2).copied();
            eprintln!(
                "{dir} plane {plane} as taken: local {:.3} px | {}",
                m0.witness.as_ref().map_or(f64::NAN, |w| w.local_px),
                taken.as_deref().unwrap_or("pass")
            );
            let s = frames[2].stride;
            for (name, at, want_backdrop) in [
                ("backdrop", backdrop, true),
                ("subject", subject_tile, false),
            ] {
                let Some(i) = at else {
                    eprintln!("{dir} plane {plane} {name}: no place to plant");
                    continue;
                };
                let (cx, cy) = ((i % tw) * w0.tile, (i / tw) * w0.tile);
                let (ax, ay) = (frames[2].active.x + cx, frames[2].active.y + cy);
                let mut moved = frames[2].clone();
                for y in ay.saturating_sub(384).max(2)..(ay + 384).min(moved.buffer_height) {
                    for x in ax.saturating_sub(384)..(ax + 384).min(s) {
                        moved.data[y * s + x] = frames[2].data[(y - 2) * s + x];
                    }
                }
                let (wt, reason, m, sub, _) = check([&frames[0], &frames[1], &moved, &frames[3]]);
                eprintln!(
                    "{dir} plane {plane} patch on the {name} at ({cx}, {cy}) px: frame local {:.3} px | {} | subject local {:.3} px over {}/{} tiles, backdrop {:.3} px | retake {} backdrop only {}",
                    m.witness.as_ref().map_or(f64::NAN, |w| w.local_px),
                    reason.as_deref().unwrap_or("pass"),
                    sub.local_px,
                    sub.tiles_measured,
                    sub.tiles,
                    sub.backdrop_local_px,
                    wt.retake,
                    wt.backdrop_only
                );
                if reason.is_none() {
                    eprintln!("  (the stack does not demote it: nothing to weigh)");
                    continue;
                }
                // A large patch can drag a shot's whole-frame fit onto the
                // next photosite (as in plan Q5's plants): a fault of the
                // whole group, which keeps the stack's retake.
                let slipped = reason.as_deref().is_some_and(|r| r.contains("slipped"));
                let ok = if slipped {
                    wt.retake && !wt.backdrop_only
                } else if want_backdrop {
                    wt.backdrop_only && !wt.retake
                } else {
                    wt.retake && !wt.backdrop_only
                };
                if !ok {
                    failures.push(format!("{dir} {plane}: patch on the {name}: {wt:?}"));
                }
            }
        }
        assert!(failures.is_empty(), "{failures:#?}");
    }

    /// The registration region follows the subject's bounding box, stays
    /// inside the frame, and is the stack's central half without a subject.
    #[test]
    fn registration_region_follows_the_subject() {
        let active = [1000, 800];
        let ring: Ring = vec![[0.05, 0.5], [0.3, 0.5], [0.3, 0.9], [0.05, 0.9]];
        let region = SubjectRegion::new(&[ring], active, MARGIN_PX);
        let roi = registration_roi(&region, 1.0, active);
        assert_eq!(roi[0], 16, "clamped clear of the edge");
        assert!(roi[1] >= 360 && roi[1] <= 400, "{roi:?}");
        assert!(roi[0] + roi[2] <= 1000 - 16 && roi[1] + roi[3] <= 800 - 16);
        assert!(roi.iter().all(|v| v % 2 == 0));
        let empty = SubjectRegion::new(&[], active, MARGIN_PX);
        assert_eq!(registration_roi(&empty, 1.0, active), [250, 200, 500, 400]);
    }
}
