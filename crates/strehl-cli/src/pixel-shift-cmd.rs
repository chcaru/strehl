//! `strehl pixel-shift <run>`: discover four-shot groups from a capture run's
//! own records and check each one (plan stage D).
//!
//! Authority, in order: the capture journal's per-file bindings
//! (`events.jsonl`, `capture_buffered` / `capture_complete`: plane, group,
//! member index, SHA-256), confirmed by a durable `transfer-receipts.jsonl`
//! entry with the same hash. Groups are never inferred from file counts or
//! timestamps. A group with a missing, undurable or mismatched member is
//! reported incomplete and is never assembled.
// `!(x < limit)` is deliberate throughout: it also rejects NaN.
#![allow(clippy::neg_cmp_op_on_partial_ord)]
use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde_json::{Value, json};
use std::collections::{BTreeMap, HashMap};
use std::path::{Path, PathBuf};
use strehl_core::pixel_shift::{self, MemberView};

#[derive(clap::Args, Debug)]
pub struct PixelShiftArgs {
    /// Capture run folder (with manifest.json, events.jsonl and receipts).
    pub dir: PathBuf,
    /// Write the full per-group report, including tile maps, as JSON here.
    #[arg(long)]
    pub json: Option<PathBuf>,
    /// Check at most this many groups.
    #[arg(long)]
    pub limit: Option<usize>,
    /// Check every group taken, retakes included, not only the group of
    /// each plane the stack uses.
    #[arg(long)]
    pub all_groups: bool,
    /// The subject (a manifest with `plan.subject`, or `strehl subject
    /// --out`): a demoted group is retaken only when the subject's own check
    /// fails (plan S4). Default: the capture manifest's subject, if any.
    #[arg(long)]
    pub subject: Option<PathBuf>,
}

/// The subject note of a group's report line (empty without a subject).
fn subject_note(gate: &Value) -> String {
    let s = &gate["subject"];
    if s.is_null() {
        return String::new();
    }
    format!(
        " | subject: local p99 {:.3} px over {} tiles, {}",
        s["local_px"].as_f64().unwrap_or(f64::NAN),
        s["tiles_measured"],
        if gate["backdrop_only"] == true {
            "backdrop only, no retake"
        } else if gate["retake"] == true {
            "retake"
        } else {
            "no retake"
        }
    )
}

/// One bound RAW member as the journal records it.
#[derive(Clone, Debug)]
pub struct BoundFile {
    pub name: String,
    pub path: PathBuf,
    pub plane: u64,
    pub group_id: String,
    pub member_index: u64,
    pub members: u64,
    pub sha256: String,
    pub durable: bool,
}

/// The exposure tier a group was taken in (plan X3, `impl/tiers.md`): the
/// journal's `tier`, absent meaning [`Tier::Base`]. Only base groups make
/// the stack; a highlight group is a companion of a base group
/// (`highlight_fusion`); any other tier (`shadow`) is recorded and not used.
#[derive(Clone, Debug, Default, PartialEq, Eq, Hash)]
pub enum Tier {
    #[default]
    Base,
    Highlight,
    Other(String),
}

impl Tier {
    fn parse(v: &Value) -> Option<Self> {
        Some(match v.as_str()? {
            "base" => Tier::Base,
            "highlight" => Tier::Highlight,
            other => Tier::Other(other.into()),
        })
    }

    pub fn name(&self) -> &str {
        match self {
            Tier::Base => "base",
            Tier::Highlight => "highlight",
            Tier::Other(s) => s,
        }
    }
}

/// One focal plane's group as recorded.
#[derive(Clone, Debug)]
pub struct RecordedGroup {
    pub plane: u64,
    /// Focus position the controller recorded for this plane, if any.
    pub target: Option<u64>,
    pub group_id: String,
    pub files: Vec<BoundFile>,
    /// All `members` files present, ordered 1..=n, each with a durable receipt
    /// whose hash matches the binding.
    pub complete: bool,
    /// The group's exposure tier (absent in the journal: base).
    pub tier: Tier,
    /// The commanded ShutterSpeed code the journal records for the group
    /// (`data.exposure.shutter`), if any.
    pub shutter: Option<u64>,
}

fn jsonl(path: &Path) -> Result<Vec<Value>> {
    let text = std::fs::read_to_string(path).with_context(|| format!("read {}", path.display()))?;
    // A torn final line (a run still being written) is ignored, not fatal.
    Ok(text
        .lines()
        .filter_map(|l| serde_json::from_str::<Value>(l).ok())
        .collect())
}

/// Durable receipts by logical file name, with their SHA-256.
pub fn receipts(dir: &Path) -> Result<HashMap<String, String>> {
    let path = dir.join("transfer-receipts.jsonl");
    if !path.is_file() {
        return Ok(HashMap::new());
    }
    Ok(jsonl(&path)?
        .into_iter()
        .filter(|r| r["durable"] == true && r["ok"] == true)
        .filter_map(|r| {
            Some((
                r["logical_name"].as_str()?.to_string(),
                r["sha256"].as_str()?.to_string(),
            ))
        })
        .collect())
}

impl RecordedGroup {
    /// The group's identity within its run: the camera's group id, or for a
    /// single-shot file without one, its file name.
    pub fn key(&self) -> String {
        if self.group_id.is_empty() {
            self.files
                .first()
                .map_or_else(String::new, |f| f.name.clone())
        } else {
            self.group_id.clone()
        }
    }
}

/// The run's focal planes, in plane order, each as the group the stack uses:
/// its last complete group, so a retake taken during the capture (error
/// correction) supersedes the group it repeats; or, if no group of the plane
/// is complete, its last group. A run without retakes has one group a plane.
pub fn recorded_groups(dir: &Path) -> Result<Vec<RecordedGroup>> {
    Ok(plane_groups(all_groups(dir)?))
}

/// [`recorded_groups`]'s choice among [`all_groups`]: base groups only, so a
/// highlight group taken at a plane never replaces the plane's group.
pub fn plane_groups(groups: Vec<RecordedGroup>) -> Vec<RecordedGroup> {
    tier_groups(groups, &Tier::Base).into_values().collect()
}

/// The last complete group of each plane in `tier` (or the last group, if
/// none of the plane's is complete), by plane number.
pub fn tier_groups(groups: Vec<RecordedGroup>, tier: &Tier) -> BTreeMap<u64, RecordedGroup> {
    let mut planes: BTreeMap<u64, RecordedGroup> = BTreeMap::new();
    for g in groups.into_iter().filter(|g| &g.tier == tier) {
        match planes.get(&g.plane) {
            Some(kept) if kept.complete && !g.complete => {}
            _ => {
                planes.insert(g.plane, g);
            }
        }
    }
    planes
}

/// The capture's highlight plan (`manifest.json` `plan.highlight`) and the
/// base shutter, as far as the run records them.
#[derive(Clone, Debug, Default)]
pub struct HighlightPlan {
    /// `every`: a highlight group at every plane (1) or every second (2).
    pub every: Option<u64>,
    /// The highlight groups' commanded ShutterSpeed code.
    pub shutter: Option<u64>,
    /// The run's ShutterSpeed code at its start (the base exposure).
    pub base_shutter: Option<u64>,
}

/// [`HighlightPlan`] from `dir/manifest.json` (all fields absent when the
/// manifest or the plan is).
pub fn highlight_plan(dir: &Path) -> HighlightPlan {
    let Ok(text) = std::fs::read_to_string(dir.join("manifest.json")) else {
        return HighlightPlan::default();
    };
    let Ok(m) = serde_json::from_str::<Value>(&text) else {
        return HighlightPlan::default();
    };
    let h = &m["plan"]["highlight"];
    HighlightPlan {
        every: h["every"].as_u64(),
        shutter: h["shutter"].as_u64(),
        base_shutter: m["initial_status"]["properties"]["ShutterSpeed"]["value"].as_u64(),
    }
}

/// Seconds of a Sony ShutterSpeed code (`numerator << 16 | denominator`;
/// as `strehl_capture::timing::shutter_seconds`), `None` for bulb or an
/// unknown code.
pub fn shutter_seconds(code: u64) -> Option<f64> {
    if code == 0 || code >= u64::from(u32::MAX) {
        return None;
    }
    let (n, d) = (code >> 16, code & 0xffff);
    (n > 0 && d > 0).then(|| n as f64 / d as f64)
}

/// Every group the run recorded, retakes included, in recording order.
pub fn all_groups(dir: &Path) -> Result<Vec<RecordedGroup>> {
    let events = dir.join("events.jsonl");
    ensure!(
        events.is_file(),
        "{} has no capture journal (events.jsonl); pixel-shift groups are only taken from the capture's own records, never inferred",
        dir.display()
    );
    let durable = receipts(dir)?;
    let mut groups: Vec<RecordedGroup> = Vec::new();
    let mut index: HashMap<(u64, String), usize> = HashMap::new();
    for e in jsonl(&events)? {
        if !matches!(
            e["event"].as_str(),
            Some("capture_buffered" | "capture_complete")
        ) {
            continue;
        }
        let Some(files) = e["data"]["response"]["files"].as_array() else {
            continue;
        };
        let target = e["data"]["target"].as_u64();
        // The exposure tier (plan X3): per file, else the event's; absent
        // means base, as every run before tiers.
        let event_tier = Tier::parse(&e["data"]["tier"]).unwrap_or_default();
        let shutter = e["data"]["exposure"]["shutter"].as_u64();
        for f in files {
            let tier = Tier::parse(&f["tier"]).unwrap_or_else(|| event_tier.clone());
            let (Some(name), Some(plane), Some(sha)) = (
                f["name"].as_str(),
                f["plane"].as_u64(),
                f["sha256"].as_str(),
            ) else {
                continue;
            };
            let archived = dir.join(format!("{name}.straw"));
            let path = if archived.is_file() {
                archived
            } else {
                dir.join(name)
            };
            let bound = BoundFile {
                name: name.into(),
                durable: durable.get(name).is_some_and(|h| h == sha) && path.is_file(),
                path,
                plane,
                group_id: f["group_id"].as_str().unwrap_or("").into(),
                member_index: f["member_index"].as_u64().unwrap_or(1),
                members: f["members"].as_u64().unwrap_or(1),
                sha256: sha.into(),
            };
            // Members of one exposure group share its id; a single-shot file
            // without one is a group of its own.
            let key = if bound.group_id.is_empty() && bound.members == 1 {
                bound.name.clone()
            } else {
                bound.group_id.clone()
            };
            let at = *index.entry((plane, key)).or_insert_with(|| {
                groups.push(RecordedGroup {
                    plane,
                    target,
                    group_id: bound.group_id.clone(),
                    files: Vec::new(),
                    complete: false,
                    tier: tier.clone(),
                    shutter,
                });
                groups.len() - 1
            });
            groups[at].files.push(bound);
        }
    }
    for g in &mut groups {
        g.files.sort_by_key(|f| f.member_index);
        let n = g.files.first().map_or(0, |f| f.members) as usize;
        g.complete = n > 0
            && g.files.len() == n
            && g.files.iter().enumerate().all(|(i, f)| {
                f.member_index == i as u64 + 1
                    && f.members == n as u64
                    && f.group_id == g.group_id
                    && f.durable
            });
    }
    Ok(groups)
}

/// Measured geometry and photometry of one four-member group.
#[derive(Clone, Debug)]
pub struct GroupCheck {
    pub offsets: [(isize, isize); 4],
    /// Structure factor of each member's fit (1 = scene dominates noise).
    pub precision: [f64; 4],
    pub residual: [[f64; 2]; 4],
    pub gains: [f64; 4],
    pub parities: bool,
}

pub fn views(frames: &[strehl_raw::Frame]) -> [MemberView<'_>; 4] {
    std::array::from_fn(|k| {
        let f = &frames[k];
        MemberView {
            data: &f.data,
            stride: f.stride,
            buffer_height: f.buffer_height,
            active: [f.active.x, f.active.y, f.active.width, f.active.height],
            black: f.levels.black,
            white: f.levels.white,
        }
    })
}

pub fn check_group(m: &[MemberView<'_>; 4]) -> GroupCheck {
    let mut c = GroupCheck {
        offsets: [(0, 0); 4],
        precision: [1.0; 4],
        residual: [[0.0; 2]; 4],
        gains: [1.0; 4],
        parities: false,
    };
    // One reference integral for the three fits, which run side by side
    // (each fit is a pure function of its two members).
    let reference = pixel_shift::Reference::new(&m[0], 2);
    let fits: Vec<pixel_shift::Fit> = m[1..]
        .par_iter()
        .map(|member| reference.register(member, 2))
        .collect();
    for (k, fit) in (1..4).zip(fits) {
        c.offsets[k] = fit.offset;
        c.precision[k] = fit.structure;
        c.residual[k] = fit.residual;
        c.gains[k] = fit.gain;
    }
    c.parities = pixel_shift::covers_all_parities(&c.offsets);
    c
}

fn quantiles(v: &[f32]) -> Value {
    let mut s: Vec<f32> = v.iter().copied().filter(|x| x.is_finite()).collect();
    s.sort_by(f32::total_cmp);
    let q = |p: f64| s.get(((s.len().max(1) - 1) as f64 * p) as usize).copied();
    json!({"p50":q(0.5),"p90":q(0.9),"p99":q(0.99),"max":s.last(),"over_2":s.iter().filter(|x| **x > 2.0).count(),"tiles":s.len()})
}

pub fn run(args: &PixelShiftArgs) -> Result<()> {
    let mut groups = if args.all_groups {
        all_groups(&args.dir)?
    } else {
        recorded_groups(&args.dir)?
    };
    if let Some(n) = args.limit {
        groups.truncate(n);
    }
    let four: Vec<&RecordedGroup> = groups
        .iter()
        .filter(|g| g.files.len() == 4 || g.files.first().is_some_and(|f| f.members == 4))
        .collect();
    println!("run             : {}", args.dir.display());
    println!(
        "groups          : {} recorded planes, {} four-shot, {} complete",
        groups.len(),
        four.len(),
        four.iter().filter(|g| g.complete).count()
    );
    ensure!(!four.is_empty(), "no four-shot groups recorded in this run");
    let subject = crate::subject_use::resolve(&args.dir, args.subject.as_deref())?;
    let mut region = None;
    if let Some(s) = &subject {
        println!(
            "subject         : {} ({} ring(s)); a demoted group is retaken only when the subject's tiles fail",
            s.origin.as_str(),
            s.rings.len()
        );
    }
    let residual = ResidualMode::from_env()?;
    // Pass 1: geometry, gains and photon-transfer bins under the injected model.
    let mut reports = Vec::new();
    let mut ptc = Vec::new();
    let mut model = None;
    let mut checked = Vec::new();
    for g in &four {
        if !g.complete {
            reports.push(json!({"plane":g.plane,"group_id":g.group_id,"verdict":"incomplete",
                "members":g.files.iter().map(|f| json!({"name":f.name,"durable":f.durable,"member_index":f.member_index})).collect::<Vec<_>>()}));
            continue;
        }
        let frames: Vec<strehl_raw::Frame> = g
            .files
            .par_iter()
            .map(|f| strehl_raw::decode(&f.path).with_context(|| f.path.display().to_string()))
            .collect::<Result<_>>()?;
        let noise = model.get_or_insert_with(|| {
            strehl_core::profile::noise_model_for(
                &frames[0].camera,
                frames[0].iso,
                strehl_core::noise::Levels {
                    black: frames[0].levels.black,
                    white: frames[0].levels.white,
                },
            )
        });
        // The stack's own measurement and gate, under the injected model.
        let (gm, w) = measure_with_witness([&frames[0], &frames[1], &frames[2], &frames[3]], noise);
        let gate = judge(&gm, residual);
        let mut gate_json = json!({"reason":gate,"retake":retake_helps(&gm, residual),
            "local_px":gm.witness.as_ref().map(|s| s.local_px),"local_tolerance_px":LOCAL_TOLERANCE_PX,
            "residual_mode":format!("{residual:?}")});
        if let Some(s) = &subject {
            let r = region
                .get_or_insert_with(|| s.region([frames[0].active.width, frames[0].active.height]));
            let sub = crate::subject_use::check_subject(
                [&frames[0], &frames[1], &frames[2], &frames[3]],
                noise,
                r,
                s.scale_at(g.target.map(|t| t as f64)),
                &gm,
                w.as_ref(),
                residual,
            );
            let weighted = crate::subject_use::weigh(gate.is_some(), &sub);
            gate_json["retake_without_subject"] = gate_json["retake"].clone();
            gate_json["retake"] = json!(weighted.retake);
            gate_json["backdrop_only"] = json!(weighted.backdrop_only);
            gate_json["subject"] = crate::subject_use::check_json(&sub, &gm);
        }
        let c = gm.check.clone();
        let Some(w) = w.filter(|_| c.parities) else {
            println!(
                "plane {:>4}      : offsets {:?} structure {:.3} {:.3} {:.3} | demote: offsets do not cover the four CFA parities | gate: {}{}",
                g.plane,
                &c.offsets[1..],
                c.precision[1],
                c.precision[2],
                c.precision[3],
                gate.as_deref().unwrap_or("pass"),
                subject_note(&gate_json)
            );
            reports.push(json!({"plane":g.plane,"group_id":g.group_id,
                "verdict":"demote: offsets do not cover the four CFA parities","gate":gate_json,
                "offsets":c.offsets,"structure":&c.precision[1..],"residual_px":c.residual,"gains":c.gains}));
            continue;
        };
        // Pool photon transfer only from groups whose witness agrees with
        // itself everywhere (scale-free, so the uncalibrated model cancels);
        // a moved or mismatched member would inflate the fitted noise.
        let t = quantiles(&w.tile_z2);
        if t["p99"]
            .as_f64()
            .zip(t["p50"].as_f64())
            .is_some_and(|(a, b)| a / b < TILE_RATIO_TOLERANCE)
        {
            ptc.extend(w.ptc.iter().copied());
        }
        checked.push((g, c, w.mean_z2, gate_json, w.tile_local_px));
    }
    let fit = pixel_shift::fit_photon_transfer(&ptc);
    let provenance = model.as_ref().map(|m| format!("{:?}", m.provenance));
    println!(
        "noise           : injected {} ; witness photon transfer {}",
        provenance.as_deref().unwrap_or("none"),
        fit.map_or("not fitted".into(), |(g, r)| format!(
            "gain {g:.4} DN/e-, read noise {r:.3} DN (MEASURED from this run's green witness; self-fitted, so z below tests registration, not the model)"
        ))
    );
    // Pass 2: witness tile maps under the fitted model.
    for (g, c, injected_z2, gate, local) in checked {
        let frames: Vec<strehl_raw::Frame> = g
            .files
            .par_iter()
            .map(|f| strehl_raw::decode(&f.path).with_context(|| f.path.display().to_string()))
            .collect::<Result<_>>()?;
        let m = views(&frames);
        let (gain, read) = fit.unwrap_or((1.0, 4.0));
        let model = |s: f32| (read * read) as f32 + gain as f32 * s.max(0.0);
        let w = pixel_shift::witness(&m, &c.offsets, &c.gains, model, 64);
        let max_residual = w
            .pair_shift
            .iter()
            .map(|d| d[0].hypot(d[1]))
            .fold(0.0, f64::max);
        let tiles = quantiles(&w.tile_z2);
        let verdict = if !c.parities {
            "demote: offsets do not cover the four CFA parities"
        } else if !(max_residual < PAIR_SHIFT_TOLERANCE_PX) {
            "demote: witness pairs misregistered beyond tolerance"
        } else if tiles["p99"]
            .as_f64()
            .zip(tiles["p50"].as_f64())
            .is_none_or(|(a, b)| !(a / b < TILE_RATIO_TOLERANCE))
        {
            "demote: witness tiles disagree locally"
        } else {
            "pass"
        };
        println!(
            "plane {:>4}      : offsets {:?} witness shift max {:.3} px gains {:.4} {:.4} {:.4} | z2 mean {:.2} tiles p50 {:.2} p99 {:.2} | {} | local p99 {:.3} px | gate: {}{}",
            g.plane,
            &c.offsets[1..],
            max_residual,
            c.gains[1],
            c.gains[2],
            c.gains[3],
            w.mean_z2,
            tiles["p50"].as_f64().unwrap_or(f64::NAN),
            tiles["p99"].as_f64().unwrap_or(f64::NAN),
            verdict,
            gate["local_px"].as_f64().unwrap_or(f64::NAN),
            gate["reason"].as_str().unwrap_or("pass"),
            subject_note(&gate)
        );
        reports.push(json!({"plane":g.plane,"group_id":g.group_id,"verdict":verdict,"gate":gate,
            "tile_local_px":quantiles(&local),"tile_local_map":local,
            "offsets":c.offsets,"structure":&c.precision[1..],"residual_px":c.residual,"gains":c.gains,
            "witness_pair_shift_px":w.pair_shift,"witness_pair_shift_quadrants_px":w.pair_shift_quadrants,"witness_pairs":w.pair_members,"mean_z2_fitted":w.mean_z2,"mean_z2_injected":injected_z2,"tile_z2":tiles,
            "tile":w.tile,"tile_grid":w.tiles,"tile_map":w.tile_z2}));
    }
    if let Some(path) = &args.json {
        let mut doc = json!({"run":args.dir,"injected_noise":provenance,
            "witness_ptc":fit.map(|(g,r)| json!({"gain_dn_per_e":g,"read_noise_dn":r})),
            "ptc_bins":ptc,"groups":reports});
        if let Some(s) = &subject {
            doc["subject"] = json!(s.origin.as_str());
        }
        std::fs::write(path, serde_json::to_string_pretty(&doc)? + "\n")?;
        println!("report          : {}", path.display());
    }
    Ok(())
}

/// Largest whole-frame witness pair misregistration a group may have, in
/// photosites. Sixteen static A7CR groups (capture 2, 2026-11-14, 0.6 and
/// 1.6 s) measured 0.046-0.127: a systematic part of about 0.05 that repeats
/// in every group, group-to-group scatter of 0.02-0.05 (two to four times the
/// estimator's 0.012, so real member motion) and a reproducible rotation of
/// about 1e-5 rad. 0.2 passes every static group; provisional until a group
/// disturbed on purpose shows where real failures sit.
pub const PAIR_SHIFT_TOLERANCE_PX: f64 = 0.2;
/// `STREHL_PIXEL_SHIFT_RESIDUAL`: `compensate` (the default) corrects each
/// member's measured sub-photosite displacement at the assembly
/// (`pixel_shift::compensate_rows`) and gates on the witness misregistration
/// that compensation leaves; `negate` applies it reversed (the placebo,
/// gated the same way); `off` assembles at the integer offsets and gates on
/// the raw witness, as before 2026-11-16.
///
/// MEASURED on the A7CR scarab four-shot run (2026-11-16, odd/even halves
/// with `STREHL_CARRY_RGB=on`): `off` demoted 13 groups at 0.20-0.29
/// photosite (and one for local motion); `compensate` assembles all but the
/// local-motion one, for 1.43x the fine-detail signal-to-noise (17.3 / 18.2
/// / 17.4 against 12.1 / 12.9 / 11.9). Assembling them uncompensated
/// (`remosaic-ungated`) reads the same, so at this N_eff (~12) a 0.1-0.3
/// photosite residual costs nothing measurable; doubling it (`negate`) costs
/// 10 %. The compensation keeps the gate meaningful where the lens is
/// sharper. It costs about 9 % of fold time.
pub const RESIDUAL_ENV: &str = "STREHL_PIXEL_SHIFT_RESIDUAL";

/// How the assembly treats the members' measured residual displacement.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum ResidualMode {
    Off,
    #[default]
    Compensate,
    Negate,
}

impl ResidualMode {
    pub fn from_env() -> Result<Self> {
        match std::env::var(RESIDUAL_ENV).ok().as_deref().map(str::trim) {
            None | Some("") | Some("compensate") => Ok(Self::Compensate),
            Some("off") => Ok(Self::Off),
            Some("negate") => Ok(Self::Negate),
            Some(other) => {
                anyhow::bail!("{RESIDUAL_ENV}: expected off, compensate or negate, got {other:?}")
            }
        }
    }

    /// The sign the gather applies the residuals with, if at all.
    pub fn sign(self) -> Option<f32> {
        match self {
            Self::Off => None,
            Self::Compensate => Some(1.0),
            Self::Negate => Some(-1.0),
        }
    }
}

/// Largest witness tile p99/median `z^2` the check judged until 2026-11-23.
/// Static groups measured 1.09-1.37; a member from a neighbouring focal
/// plane measured 4.20. No longer judged: it measures how statistically
/// clear a mismatch is, which grows with light (MEASURED on the close tile:
/// the same offset failed at 0.26 px at 1 s and 0.59 px at 1/4 s).
/// Reported only.
pub const TILE_RATIO_TOLERANCE: f64 = 2.5;

/// The lens's blur width on the A7CR rig, photosites: the full width at half
/// maximum of the diffraction core, `1.03 / cutoff`, at the green cutoff the
/// restoration fits (0.588 cycles/px on the close tile, 0.616 on the scarab;
/// N_eff 11 to 13). Other blur only widens it.
pub const BLUR_WIDTH_PX: f64 = 1.7;

/// Fraction of [`BLUR_WIDTH_PX`] by which the shots may disagree in places
/// once each pair's whole-group shift is taken out
/// ([`WitnessSummary::local_px`]): 0.51 px.
///
/// MEASURED on the close tile (2026-11-23, every group of the 1/4 s and the
/// stopped 1 s capture): groups with no fault read 0.20 px at p99 at small
/// offsets at either exposure, rising to about 0.3 px at 0.4-0.7 px offsets
/// and 0.5-0.6 px at 0.8-1.0 px (first-order removal of the pair's shift).
/// Planted on real groups: a 768 px patch of one shot moved 1 px reads
/// 1.01-1.19 px, moved 2 px 2.14-2.37 px; one shot from the next focal
/// plane 1.10-1.68 px. ARGUED: whole-frame misregistration of 0.1-0.3 px
/// cost nothing measurable on the scarab and 0.2-0.6 px cost 10 % of the
/// fine detail (see [`RESIDUAL_ENV`]), so harm begins near a third of the
/// blur width; the limit sits there, above the fault-free population and
/// half of the smallest planted fault.
pub const LOCAL_FRACTION: f64 = 0.3;

/// [`LOCAL_FRACTION`] of the blur width, photosites.
pub const LOCAL_TOLERANCE_PX: f64 = LOCAL_FRACTION * BLUR_WIDTH_PX;

/// How a [`StackGroups`] stack treats its four-shot groups.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum GroupMode {
    /// Assemble groups that pass every check; fold the rest as member 1.
    Remosaic,
    /// Comparison arm: assemble every group whose offsets are measured and
    /// cover the four CFA parities, ignoring the witness tolerances.
    Ungated,
    /// Comparison arm: fold every group as its member 1 (the same frames,
    /// demosaiced), so a pixel-shift arm can be compared on identical inputs.
    Member1,
}

/// `STREHL_PIXEL_SHIFT`: `off` (default; every RAW is an ordinary frame) or
/// `remosaic` (plan stage E: one frame per focal plane, measured channels at
/// the gather, the rest of the merge unchanged).
pub const PIXEL_SHIFT_ENV: &str = "STREHL_PIXEL_SHIFT";

/// Whether this render assembles four-shot groups from measured channels
/// (`STREHL_PIXEL_SHIFT=remosaic` or `remosaic-ungated`): the stacks on which
/// colour carry and optical restoration are on by default.
pub fn assembly_requested() -> bool {
    matches!(
        std::env::var(PIXEL_SHIFT_ENV)
            .ok()
            .as_deref()
            .map(str::trim),
        Some("remosaic") | Some("remosaic-ungated")
    )
}

/// `STREHL_GROUP_JOURNAL`: `on` (the default) keeps every group measurement
/// in a journal beside the warp maps (`cache_root()/groups/`), shared by
/// renders and `strehl follow`, so a group is measured once, ever; `off`
/// neither reads nor writes it. A record is used only for the same code
/// version ([`GROUP_CHECK_VERSION`]), the same four files (each archive's
/// declared SHA-256, which its full decode verifies) and the same noise
/// model; its numbers are stored as exact bits, so a journaled measurement
/// is the measurement. On the A7CR scarab four-shot run a measurement is
/// 0.1-0.2 s of the whole machine per group (37 s for 196 groups).
pub const GROUP_JOURNAL_ENV: &str = "STREHL_GROUP_JOURNAL";

fn journal_enabled() -> Result<bool> {
    match std::env::var(GROUP_JOURNAL_ENV) {
        Err(std::env::VarError::NotPresent) => Ok(true),
        Err(e) => Err(e).context(GROUP_JOURNAL_ENV),
        Ok(v) => match v.trim() {
            "" | "on" | "1" => Ok(true),
            "off" | "0" => Ok(false),
            other => anyhow::bail!("{GROUP_JOURNAL_ENV}={other:?} is not on or off"),
        },
    }
}

/// A journal record's key: each member's archive SHA-256 and the noise
/// model's identity.
type JournalKey = ([String; 4], String);

/// The group-measurement journal of one capture folder.
pub struct GroupJournal {
    path: PathBuf,
    records: std::sync::Mutex<HashMap<JournalKey, GroupMeasurement>>,
    /// Records written, and records used, this process.
    written: std::sync::atomic::AtomicUsize,
    used: std::sync::atomic::AtomicUsize,
}

/// A stable identity of the injected noise model (SHA-256 of its `Debug`,
/// which prints every float round-trip exactly).
fn noise_identity(noise: &strehl_core::noise::NoiseModel) -> String {
    use sha2::Digest;
    hex(&sha2::Sha256::digest(format!("{noise:?}").as_bytes()))
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn bits(v: f64) -> String {
    format!("{:016x}", v.to_bits())
}

fn unbits(v: &Value) -> Option<f64> {
    u64::from_str_radix(v.as_str()?, 16)
        .ok()
        .map(f64::from_bits)
}

/// A measurement as a journal value: every float as its exact bits.
fn measurement_json(m: &GroupMeasurement) -> Value {
    let c = &m.check;
    json!({
        "offsets": c.offsets.map(|(x, y)| [x as i64, y as i64]),
        "precision": c.precision.map(bits),
        "residual": c.residual.map(|r| r.map(bits)),
        "gains": c.gains.map(bits),
        "parities": c.parities,
        "witness": m.witness.as_ref().map(|w| json!({
            "pair_shift": w.pair_shift.map(|p| p.map(bits)),
            "pair_members": w.pair_members,
            "tile_ratio": bits(w.tile_ratio),
            "local_px": bits(w.local_px),
        })),
        "margins": m.margins,
        "levels_agree": m.levels_agree,
    })
}

fn measurement_from_json(v: &Value) -> Option<GroupMeasurement> {
    let arr4 = |v: &Value| -> Option<[f64; 4]> {
        let a = v.as_array()?;
        (a.len() == 4).then_some(())?;
        Some([
            unbits(&a[0])?,
            unbits(&a[1])?,
            unbits(&a[2])?,
            unbits(&a[3])?,
        ])
    };
    let pair = |v: &Value| -> Option<[f64; 2]> {
        let a = v.as_array()?;
        (a.len() == 2).then_some(())?;
        Some([unbits(&a[0])?, unbits(&a[1])?])
    };
    let offsets: Vec<(isize, isize)> = v["offsets"]
        .as_array()?
        .iter()
        .map(|o| Some((o[0].as_i64()? as isize, o[1].as_i64()? as isize)))
        .collect::<Option<_>>()?;
    let residual: Vec<[f64; 2]> = v["residual"]
        .as_array()?
        .iter()
        .map(pair)
        .collect::<Option<_>>()?;
    let witness = match &v["witness"] {
        Value::Null => None,
        w => {
            let shift: Vec<[f64; 2]> = w["pair_shift"]
                .as_array()?
                .iter()
                .map(pair)
                .collect::<Option<_>>()?;
            let members: Vec<[usize; 2]> = w["pair_members"]
                .as_array()?
                .iter()
                .map(|p| Some([p[0].as_u64()? as usize, p[1].as_u64()? as usize]))
                .collect::<Option<_>>()?;
            Some(WitnessSummary {
                pair_shift: shift.try_into().ok()?,
                pair_members: members.try_into().ok()?,
                tile_ratio: unbits(&w["tile_ratio"])?,
                local_px: unbits(&w["local_px"])?,
            })
        }
    };
    let margins: Vec<usize> = v["margins"]
        .as_array()?
        .iter()
        .map(|m| m.as_u64().map(|m| m as usize))
        .collect::<Option<_>>()?;
    Some(GroupMeasurement {
        check: GroupCheck {
            offsets: offsets.try_into().ok()?,
            precision: arr4(&v["precision"])?,
            residual: residual.try_into().ok()?,
            gains: arr4(&v["gains"])?,
            parities: v["parities"].as_bool()?,
        },
        witness,
        margins: margins.try_into().ok()?,
        levels_agree: v["levels_agree"].as_bool()?,
    })
}

impl GroupJournal {
    /// The journal of the capture folder `dir`, with its readable records
    /// of this code version (a torn or foreign line is skipped), or `None`
    /// under `STREHL_GROUP_JOURNAL=off`.
    pub fn open(dir: &Path) -> Result<Option<Self>> {
        if !journal_enabled()? {
            return Ok(None);
        }
        use sha2::Digest;
        let canonical = std::fs::canonicalize(dir).unwrap_or_else(|_| dir.to_path_buf());
        let digest = sha2::Sha256::digest(canonical.to_string_lossy().as_bytes());
        let leaf = dir
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_else(|| "stack".into());
        let path = crate::align_cmd::cache_root()
            .join("groups")
            .join(format!("{leaf}-{}.jsonl", &hex(&digest)[..16]));
        let mut records = HashMap::new();
        if let Ok(text) = std::fs::read_to_string(&path) {
            for line in text.lines() {
                let Ok(r) = serde_json::from_str::<Value>(line) else {
                    continue;
                };
                if r["v"].as_u64() != Some(u64::from(GROUP_CHECK_VERSION)) {
                    continue;
                }
                let (Some(shas), Some(noise), Some(m)) = (
                    r["sha256"].as_array().and_then(|a| {
                        a.iter()
                            .map(|s| s.as_str().map(str::to_string))
                            .collect::<Option<Vec<String>>>()?
                            .try_into()
                            .ok()
                    }),
                    r["noise"].as_str(),
                    measurement_from_json(&r["m"]),
                ) else {
                    continue;
                };
                records.insert((shas, noise.to_string()), m);
            }
        }
        Ok(Some(Self {
            path,
            records: std::sync::Mutex::new(records),
            written: Default::default(),
            used: Default::default(),
        }))
    }

    /// The four members' archive SHA-256, if every one is an archive.
    fn key(members: [&Path; 4], noise: &strehl_core::noise::NoiseModel) -> Option<JournalKey> {
        let shas: Vec<String> = members
            .iter()
            .map(|p| strehl_raw::archive_sha256(p))
            .collect::<Option<_>>()?;
        Some((shas.try_into().ok()?, noise_identity(noise)))
    }

    fn get(&self, key: &JournalKey) -> Option<GroupMeasurement> {
        let m = self.records.lock().unwrap().get(key).cloned();
        if m.is_some() {
            self.used.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        }
        m
    }

    /// Append one record (one line, flushed); a failure to write costs only
    /// the next render a measurement, so it is reported, not fatal.
    pub fn append(&self, key: JournalKey, plane: usize, m: &GroupMeasurement) {
        use std::io::Write;
        let line = json!({
            "v": GROUP_CHECK_VERSION,
            "sha256": key.0,
            "noise": key.1,
            "plane": plane,
            "m": measurement_json(m),
        })
        .to_string();
        let mut records = self.records.lock().unwrap();
        let written = self
            .path
            .parent()
            .map_or(Ok(()), std::fs::create_dir_all)
            .and_then(|()| {
                let mut f = std::fs::OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(&self.path)?;
                writeln!(f, "{line}")?;
                f.flush()
            });
        match written {
            Ok(()) => {
                self.written
                    .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                records.insert(key, m.clone());
            }
            Err(e) => eprintln!(
                "pixel shift     : could not journal a group measurement in {}: {e}",
                self.path.display()
            ),
        }
    }

    /// Records used and written by this process so far.
    pub fn counts(&self) -> (usize, usize) {
        (
            self.used.load(std::sync::atomic::Ordering::Relaxed),
            self.written.load(std::sync::atomic::Ordering::Relaxed),
        )
    }
}

/// Measure a group, or take its measurement from `journal`, and journal a
/// fresh one: what `strehl follow` shares with the render. The whole
/// witness comes back only when the group was measured here.
pub fn measure_journaled(
    journal: Option<&GroupJournal>,
    paths: [&Path; 4],
    frames: [&strehl_raw::Frame; 4],
    noise: &strehl_core::noise::NoiseModel,
    plane: usize,
) -> (GroupMeasurement, Option<pixel_shift::Witness>) {
    let key = journal.and_then(|_| GroupJournal::key(paths, noise));
    if let (Some(j), Some(k)) = (journal, key.as_ref())
        && let Some(m) = j.get(k)
    {
        return (m, None);
    }
    let (m, witness) = measure_with_witness(frames, noise);
    if let (Some(j), Some(k)) = (journal, key) {
        j.append(k, plane, &m);
    }
    (m, witness)
}

/// [`measure`] of one group through this process's measurements and then
/// `journal`, journaling a fresh one: for a highlight companion
/// (`highlight_fusion`), measured as the stack measures its own groups.
pub(crate) fn measure_cached(
    journal: Option<&GroupJournal>,
    paths: [&Path; 4],
    frames: [&strehl_raw::Frame; 4],
    noise: &strehl_core::noise::NoiseModel,
    plane: usize,
) -> std::sync::Arc<GroupMeasurement> {
    let key = MeasurementKey {
        members: paths.map(Path::to_path_buf),
        noise: format!("{noise:?}"),
    };
    if let Some(m) = measured_groups().lock().unwrap().get(&key).cloned() {
        return m;
    }
    let journal_key = journal.and_then(|_| GroupJournal::key(paths, noise));
    let known = match (journal, journal_key.as_ref()) {
        (Some(j), Some(k)) => j.get(k),
        _ => None,
    };
    let m = match known {
        Some(m) => m,
        None => {
            let m = measure(frames, noise);
            if let (Some(j), Some(k)) = (journal, journal_key) {
                j.append(k, plane, &m);
            }
            m
        }
    };
    let m = std::sync::Arc::new(m);
    measured_groups()
        .lock()
        .unwrap()
        .insert(key, std::sync::Arc::clone(&m));
    m
}

/// A group's identity for [`measured_groups`]: its four files and the noise
/// model the witness was measured under.
#[derive(Clone, PartialEq, Eq, Hash)]
struct MeasurementKey {
    members: [PathBuf; 4],
    /// `Debug` of the injected model; Rust prints every float in it
    /// round-trip exactly.
    noise: String,
}

type MeasuredGroups = std::sync::Mutex<HashMap<MeasurementKey, std::sync::Arc<GroupMeasurement>>>;

/// Every group measured in this process. A render builds one [`StackGroups`]
/// per pass (the lateral-colour preview, then the render with its depth
/// measurement and fold), and each pass decodes the same groups.
fn measured_groups() -> &'static MeasuredGroups {
    static GROUPS: std::sync::OnceLock<MeasuredGroups> = std::sync::OnceLock::new();
    GROUPS.get_or_init(Default::default)
}

/// Whether this is the first time this process reports on the group `key`
/// (its demotion is said once, not once per pass).
fn first_report(key: &MeasurementKey) -> bool {
    static SEEN: std::sync::OnceLock<std::sync::Mutex<std::collections::HashSet<MeasurementKey>>> =
        std::sync::OnceLock::new();
    SEEN.get_or_init(Default::default)
        .lock()
        .unwrap()
        .insert(key.clone())
}

fn take_member_buffer() -> Option<Vec<u16>> {
    crate::align_cmd::take_member_buffer()
}

/// Return a group's member buffers to the pool once nothing reads them.
pub(crate) fn recycle_members(members: [strehl_raw::Frame; 3]) {
    crate::align_cmd::recycle_members(members);
}

/// A pixel-shift stack's focal planes and their groups' other members.
pub struct StackGroups {
    /// The stack's injected noise model, for the witness's gradient test.
    noise: std::sync::OnceLock<strehl_core::noise::NoiseModel>,
    /// One path per focal plane: member 1 of a four-shot group, or the single
    /// RAW of a one-shot plane.
    pub planes: Vec<PathBuf>,
    members: HashMap<PathBuf, [PathBuf; 3]>,
    parked: std::sync::Mutex<HashMap<usize, crate::align_cmd::MeasuredGroup>>,
    demoted: std::sync::Mutex<Vec<(usize, String)>>,
    recorded: (usize, usize, usize),
    mode: GroupMode,
    residual: ResidualMode,
    /// `STREHL_GROUP_JOURNAL`: measurements kept across processes.
    journal: Option<std::sync::Arc<GroupJournal>>,
    /// Plan X4: the banner's line about the capture's highlight companions
    /// (installed for the render by `highlight_fusion::companions`).
    companion_line: Option<String>,
}

fn views_of<'a>(frames: [&'a strehl_raw::Frame; 4]) -> [MemberView<'a>; 4] {
    frames.map(|f| MemberView {
        data: &f.data,
        stride: f.stride,
        buffer_height: f.buffer_height,
        active: [f.active.x, f.active.y, f.active.width, f.active.height],
        black: f.levels.black,
        white: f.levels.white,
    })
}

/// Check one complete four-member group as the stack would: geometry,
/// structure, colour-exact witness registration, margins and levels.
/// Returns the measured group and `None` when it passes, else a reason.
pub fn verdict(
    frames: [&strehl_raw::Frame; 4],
    noise: &strehl_core::noise::NoiseModel,
) -> (GroupCheck, Option<pixel_shift::Witness>, Option<String>) {
    verdict_with(frames, noise, ResidualMode::Off)
}

/// [`verdict`], gating on the witness misregistration the residual
/// compensation leaves when `residual` compensates (or is its placebo): each
/// witness pair's measured shift minus what the members' registration
/// residuals predict for it (`r_b - r_a`). On the A7CR scarab four-shot run
/// the prediction tracked the witness with correlation 0.91-0.98 and slope
/// 0.86-1.00 over 196 groups.
pub fn verdict_with(
    frames: [&strehl_raw::Frame; 4],
    noise: &strehl_core::noise::NoiseModel,
    residual: ResidualMode,
) -> (GroupCheck, Option<pixel_shift::Witness>, Option<String>) {
    let (m, witness) = measure_with_witness(frames, noise);
    let reason = judge(&m, residual);
    (m.check, witness, reason)
}

/// What the witness contributes to a group's verdict.
#[derive(Clone, Copy, Debug)]
pub struct WitnessSummary {
    /// [`pixel_shift::Witness::pair_shift`] and `pair_members`.
    pub pair_shift: [[f64; 2]; 2],
    pub pair_members: [[usize; 2]; 2],
    /// Scale-free tile outlier ratio, p99 / median of the finite tile `z^2`.
    /// Reported, no longer judged: it grows with exposure.
    pub tile_ratio: f64,
    /// p99 over the measured tiles of [`pixel_shift::Witness::tile_local_px`]:
    /// how far, in photosites, the shots disagree in places once each
    /// witness pair's whole-group shift is taken out. `NaN` when no tile has
    /// enough structure.
    pub local_px: f64,
}

/// Everything the group checks compute from a group's four members: a pure
/// function of the samples, the injected noise model and this code
/// ([`GROUP_CHECK_VERSION`]). [`judge`] turns it into a verdict.
#[derive(Clone, Debug)]
pub struct GroupMeasurement {
    pub check: GroupCheck,
    /// `None` when the offsets do not cover the lattice (no witness is run).
    pub witness: Option<WitnessSummary>,
    /// Member 1's buffer margins around its active area: left, top, right,
    /// bottom.
    pub margins: [usize; 4],
    /// Whether members 2-4 have member 1's black and white levels.
    pub levels_agree: bool,
}

/// Version of [`measure`]'s output. Bump it with any change to what
/// `pixel_shift::register`, `pixel_shift::witness`, `pixel_shift::balance`
/// or [`measure`] compute (the pinned-bits test says when): journaled
/// measurements of another version are measured again.
pub const GROUP_CHECK_VERSION: u32 = 2;

/// Run `f` on a rayon pool of one thread kept by the calling thread, so its
/// parallel loops run in turn there rather than on the shared pool.
fn on_one_thread<R: Send>(f: impl FnOnce() -> R + Send) -> R {
    thread_local! {
        static ONE: Option<rayon::ThreadPool> =
            rayon::ThreadPoolBuilder::new().num_threads(1).build().ok();
    }
    let mut f = Some(f);
    let pooled = ONE.with(|pool| pool.as_ref().map(|p| p.install(f.take().expect("once"))));
    match pooled {
        Some(r) => r,
        None => (f.take().expect("not run"))(),
    }
}

/// Measure one complete four-member group (see [`GroupMeasurement`]).
pub fn measure(
    frames: [&strehl_raw::Frame; 4],
    noise: &strehl_core::noise::NoiseModel,
) -> GroupMeasurement {
    // The witness's photon-transfer bins are for reports only.
    measure_impl(frames, noise, false).0
}

/// [`measure`], also returning the whole witness for reports.
pub fn measure_with_witness(
    frames: [&strehl_raw::Frame; 4],
    noise: &strehl_core::noise::NoiseModel,
) -> (GroupMeasurement, Option<pixel_shift::Witness>) {
    measure_impl(frames, noise, true)
}

/// [`measure`], also returning the witness without its photon-transfer bins:
/// its tile map and pair shifts, from the same sums as the group check. The
/// desktop's plane view draws them on the picture.
pub fn measure_with_tiles(
    frames: [&strehl_raw::Frame; 4],
    noise: &strehl_core::noise::NoiseModel,
) -> (GroupMeasurement, Option<pixel_shift::Witness>) {
    measure_impl(frames, noise, false)
}

fn measure_impl(
    frames: [&strehl_raw::Frame; 4],
    noise: &strehl_core::noise::NoiseModel,
    ptc: bool,
) -> (GroupMeasurement, Option<pixel_shift::Witness>) {
    let first = frames[0];
    let m = views_of(frames);
    let c = check_group(&m);
    let witness = c.parities.then(|| {
        let variance = |s| noise.variance(strehl_core::CfaPlane::G1, s);
        if ptc {
            pixel_shift::witness(&m, &c.offsets, &c.gains, variance, 64)
        } else {
            pixel_shift::witness_without_ptc(&m, &c.offsets, &c.gains, variance, 64)
        }
    });
    // Scale-free tile outlier ratio: an uncalibrated model scales every tile
    // alike and cancels; motion, a focus slip or a wrong member does not.
    let summary = witness.as_ref().map(|w| {
        let mut t: Vec<f32> = w
            .tile_z2
            .iter()
            .copied()
            .filter(|v| v.is_finite())
            .collect();
        t.sort_by(f32::total_cmp);
        let q = |p: f64| {
            f64::from(
                t.get(((t.len().max(1) - 1) as f64 * p) as usize)
                    .copied()
                    .unwrap_or(f32::NAN),
            )
        };
        WitnessSummary {
            pair_shift: w.pair_shift,
            pair_members: w.pair_members,
            tile_ratio: q(0.99) / q(0.5),
            local_px: local_p99(&w.tile_local_px),
        }
    });
    let a = first.active;
    let margins = [
        a.x,
        a.y,
        first.stride - a.x - a.width,
        first.buffer_height - a.y - a.height,
    ];
    let levels_agree = frames[1..].iter().all(|f| f.levels == first.levels);
    (
        GroupMeasurement {
            check: c,
            witness: summary,
            margins,
            levels_agree,
        },
        witness,
    )
}

/// p99 of the finite tile values (`NaN` when there are none).
fn local_p99(tiles: &[f32]) -> f64 {
    let mut t: Vec<f32> = tiles.iter().copied().filter(|v| v.is_finite()).collect();
    if t.is_empty() {
        return f64::NAN;
    }
    t.sort_by(f32::total_cmp);
    f64::from(t[((t.len() - 1) as f64 * 0.99) as usize])
}

/// The verdict on a measured group: `None` when it may be assembled, else
/// the reason it is demoted. Cheap; `residual` decides whether the witness
/// gate judges what residual compensation leaves.
pub fn judge(m: &GroupMeasurement, residual: ResidualMode) -> Option<String> {
    demotion(m, residual).map(|(reason, _)| reason)
}

/// Whether taking the group again could make it pass: only when something
/// changed between its exposures (motion, a focus slip, a level change).
/// Too little scene structure, a wrong shift pattern or photosites leaving
/// the sensor are properties of the plane or the camera mode, and a retake
/// would fail the same way.
pub fn retake_helps(m: &GroupMeasurement, residual: ResidualMode) -> bool {
    demotion(m, residual).is_some_and(|(_, retake)| retake)
}

/// The reason a group whose shots disagree in places is demoted.
fn local_reason(local: f64) -> String {
    format!(
        "witness tiles disagree locally by {local:.2} px at p99 (limit {LOCAL_TOLERANCE_PX:.2}): motion, a focus slip or a wrong member"
    )
}

/// [`judge`]'s reason, and whether a retake could help ([`retake_helps`]).
pub(crate) fn demotion(m: &GroupMeasurement, residual: ResidualMode) -> Option<(String, bool)> {
    let c = &m.check;
    // No tile with enough structure to judge reads NaN, and there is
    // nothing there to disagree: the whole-group gate still judges.
    let local = m.witness.as_ref().map_or(f64::NAN, |w| w.local_px).max(0.0);
    let misregistration = |residual: ResidualMode| {
        m.witness.as_ref().map_or(f64::INFINITY, |w| {
            w.pair_shift
                .iter()
                .zip(&w.pair_members)
                .map(|(d, &[a, b])| {
                    let (px, py) = if residual == ResidualMode::Off {
                        (0.0, 0.0)
                    } else {
                        (
                            c.residual[b][0] - c.residual[a][0],
                            c.residual[b][1] - c.residual[a][1],
                        )
                    };
                    (d[0] - px).hypot(d[1] - py)
                })
                .fold(0.0, f64::max)
        })
    };
    let max_residual = misregistration(residual);
    let reach = c
        .offsets
        .iter()
        .map(|o| o.0.unsigned_abs().max(o.1.unsigned_abs()))
        .max()
        .unwrap_or(0);
    let margins = m.margins;
    let measurable = c.precision[1..].iter().all(|r| *r > 0.8);
    // A shot that slipped by a whole photosite lands on another shot's
    // colour site (MEASURED on the close tile: 40 of 95 groups at 1 s, 27 of
    // 190 at 1/4 s, from a sway of up to 1.8 px); another try can land
    // right. A slip past the search window reads as no structure for that
    // shot only, so it is enough that one shot registers on the scene and
    // that the camera shifted at all.
    let slipped =
        c.precision[1..].iter().any(|r| *r > 0.8) && c.offsets[1..].iter().any(|o| *o != (0, 0));
    if !c.parities {
        Some((
            format!(
                "offsets {:?} do not cover the four CFA parities{}",
                &c.offsets[1..],
                if slipped {
                    ": a shot slipped by a whole photosite"
                } else {
                    ""
                }
            ),
            slipped,
        ))
    } else if !measurable && !(local < LOCAL_TOLERANCE_PX) {
        // A shot that moved in one part of the frame also spoils its
        // whole-frame fit, which then reads as too little structure; the
        // tiles say it moved (MEASURED on the close tile: a 768 px patch of
        // one shot moved 2 px). A plane without structure has no measured
        // tile and reads NaN here, so it is not mistaken for this.
        Some((local_reason(local), true))
    } else if !measurable {
        Some((
            "offsets unmeasurable (too little scene structure)".into(),
            false,
        ))
    } else if !(max_residual < PAIR_SHIFT_TOLERANCE_PX) {
        // MEASURED (2026-11-20, a pencil and a printed part on the studio
        // rig): every group's witness pairs agreed to 0.05-0.15 photosite,
        // but the residuals measured from that plain scene were off by about
        // 0.4, so compensating with them misregistered every group. That is
        // the scene's measurement, not the exposures: a retake would fail
        // the same way. Only a misregistration the exposures show themselves
        // is worth one.
        Some((
            format!(
                "witness pairs misregistered by {max_residual:.3} photosite{}",
                if residual == ResidualMode::Off {
                    ""
                } else {
                    " after residual compensation"
                }
            ),
            !(misregistration(ResidualMode::Off) < PAIR_SHIFT_TOLERANCE_PX),
        ))
    } else if !(local < LOCAL_TOLERANCE_PX) {
        // Judged in photosites against the blur width, with each pair's
        // whole-group shift taken out (the assembly lines the shots up to
        // it), so the same disagreement gets the same verdict at any
        // exposure.
        Some((local_reason(local), true))
    } else if margins.iter().any(|m| *m < reach) {
        Some(("shifted photosites leave the sensor buffer".into(), false))
    } else if !m.levels_agree {
        Some(("members disagree in black or white level".into(), true))
    } else {
        None
    }
}

/// A capture's focal planes as `remosaic` stacks them, with members 2-4 of
/// each complete four-shot group.
struct PlaneList {
    planes: Vec<PathBuf>,
    members: HashMap<PathBuf, [PathBuf; 3]>,
    four: usize,
    single: usize,
    incomplete: usize,
}

fn plane_list(groups: &[RecordedGroup]) -> PlaneList {
    let mut list = PlaneList {
        planes: Vec::new(),
        members: HashMap::new(),
        four: 0,
        single: 0,
        incomplete: 0,
    };
    for g in groups {
        match (g.complete, g.files.len()) {
            (true, 4) => {
                list.planes.push(g.files[0].path.clone());
                list.members.insert(
                    g.files[0].path.clone(),
                    [1, 2, 3].map(|k| g.files[k].path.clone()),
                );
                list.four += 1;
            }
            (true, 1) => {
                list.planes.push(g.files[0].path.clone());
                list.single += 1;
            }
            _ => {
                // An incomplete group contributes its first durable member
                // as an ordinary frame, and says so; never silently dropped.
                if let Some(f) = g.files.iter().find(|f| f.durable) {
                    list.planes.push(f.path.clone());
                }
                list.incomplete += 1;
            }
        }
    }
    list
}

/// The frames a four-shot capture folder stacks as under `remosaic`: one
/// path per focal plane, in the order the stack numbers them (member 1 of a
/// four-shot group, the RAW of a single-shot plane, the first durable member
/// of an incomplete group). `None` when the folder records no complete
/// four-shot group, or has no capture journal at all: such a folder stacks
/// as ordinary frames. For callers that must agree with the stack about
/// frame indices, such as the desktop's capture timeline.
pub fn four_shot_planes(dir: &Path) -> Result<Option<Vec<PathBuf>>> {
    if !dir.join("events.jsonl").is_file() {
        return Ok(None);
    }
    let list = plane_list(&recorded_groups(dir)?);
    Ok((list.four > 0 && !list.planes.is_empty()).then_some(list.planes))
}

impl StackGroups {
    pub fn from_env(dir: &Path, limit: Option<usize>) -> Result<Option<Self>> {
        match std::env::var(PIXEL_SHIFT_ENV)
            .ok()
            .as_deref()
            .map(str::trim)
        {
            None | Some("") | Some("off") => Ok(None),
            Some("remosaic") => Self::discover(dir, limit, GroupMode::Remosaic).map(Some),
            Some("remosaic-ungated") => Self::discover(dir, limit, GroupMode::Ungated).map(Some),
            Some("member1") => Self::discover(dir, limit, GroupMode::Member1).map(Some),
            Some(other) => anyhow::bail!(
                "{PIXEL_SHIFT_ENV}: expected off, remosaic, remosaic-ungated or member1, got {other:?}"
            ),
        }
    }

    pub fn discover(dir: &Path, limit: Option<usize>, mode: GroupMode) -> Result<Self> {
        let all = all_groups(dir)?;
        let base = plane_groups(all.clone());
        let PlaneList {
            mut planes,
            members,
            four,
            single,
            incomplete,
        } = plane_list(&base);
        if let Some(n) = limit {
            planes.truncate(n);
        }
        ensure!(
            four > 0,
            "{PIXEL_SHIFT_ENV}=remosaic: no complete four-shot group is recorded in {}",
            dir.display()
        );
        ensure!(!planes.is_empty(), "no focal planes to stack");
        let journal = match mode {
            GroupMode::Member1 => None,
            _ => GroupJournal::open(dir)?.map(std::sync::Arc::new),
        };
        let residual = ResidualMode::from_env()?;
        // Plan X4: each base plane's highlight companion, installed for the
        // render by member-1 path (none in the member-1 comparison arm).
        let companion_line = match mode {
            GroupMode::Member1 => None,
            _ => crate::highlight_fusion::companions(
                dir,
                &all,
                &base,
                &planes,
                journal.clone(),
                residual,
            )?,
        };
        Ok(Self {
            noise: Default::default(),
            planes,
            members,
            parked: Default::default(),
            demoted: Default::default(),
            recorded: (four, single, incomplete),
            mode,
            residual,
            journal,
            companion_line,
        })
    }

    /// What this pass took from and gave to the group journal.
    pub fn journal_line(&self) -> Option<String> {
        let j = self.journal.as_ref()?;
        let (used, written) = j.counts();
        Some(format!(
            "group journal   : {used} measurements reused, {written} measured and kept ({GROUP_JOURNAL_ENV}; {})",
            j.path.display()
        ))
    }

    /// Whether this mode assembles measured channels (and so parks each
    /// group between its decode and its gather), as opposed to `member1`.
    pub fn assembles(&self) -> bool {
        !matches!(self.mode, GroupMode::Member1)
    }

    pub fn banner(&self) -> String {
        let (four, single, incomplete) = self.recorded;
        format!(
            "pixel shift     : {} ({PIXEL_SHIFT_ENV}) -- {} focal planes: {four} four-shot groups assembled from measured channels at the gather, {single} single-shot, {incomplete} incomplete (first durable member as an ordinary frame). Each group's offsets are measured; a group that fails is folded as its member 1 and reported.",
            match self.mode {
                GroupMode::Remosaic => "REMOSAIC",
                GroupMode::Ungated =>
                    "REMOSAIC-UNGATED (comparison arm: witness tolerances ignored)",
                GroupMode::Member1 => "MEMBER1 (comparison arm: every group folded as member 1)",
            },
            self.planes.len()
        ) + match self.residual {
            ResidualMode::Off => "",
            ResidualMode::Compensate => "
                  members' measured sub-photosite residuals COMPENSATED at the assembly (first order); the witness gate judges what compensation leaves (STREHL_PIXEL_SHIFT_RESIDUAL=compensate)",
            ResidualMode::Negate => "
                  members' residuals applied REVERSED: placebo arm (STREHL_PIXEL_SHIFT_RESIDUAL=negate)",
        } + &self
            .companion_line
            .as_ref()
            .map(|l| format!("\n{l}"))
            .unwrap_or_default()
    }

    /// Decode and check frame `index`'s other members; park a passing group.
    pub fn prepare(&self, index: usize, path: &Path, first: &strehl_raw::Frame) -> Result<()> {
        self.prepare_with(index, path, first, false)
    }

    /// [`Self::prepare`]; `serial` decodes the members one after another on
    /// the calling thread (a decode-ahead thread among many) instead of side
    /// by side on the shared pool.
    pub fn prepare_with(
        &self,
        index: usize,
        path: &Path,
        first: &strehl_raw::Frame,
        serial: bool,
    ) -> Result<()> {
        let Some(others) = self.members.get(path) else {
            return Ok(());
        };
        if self.mode == GroupMode::Member1 {
            self.demoted
                .lock()
                .unwrap()
                .push((index, "member1 comparison arm".into()));
            return Ok(());
        }
        let noise = self.noise.get_or_init(|| {
            strehl_core::profile::noise_model_for(
                &first.camera,
                first.iso,
                strehl_core::noise::Levels {
                    black: first.levels.black,
                    white: first.levels.white,
                },
            )
        });
        // A group is measured once per process: the preview, the depth pass
        // and the fold each decode it, and the measurement is a pure function
        // of the four files and the noise model (`measure`).
        let key = MeasurementKey {
            members: [
                path.to_path_buf(),
                others[0].clone(),
                others[1].clone(),
                others[2].clone(),
            ],
            noise: format!("{noise:?}"),
        };
        let mut known = measured_groups().lock().unwrap().get(&key).cloned();
        // Then the journal: measured by an earlier render or `strehl follow`.
        let journal_key = self
            .journal
            .as_ref()
            .and_then(|_| GroupJournal::key([path, &others[0], &others[1], &others[2]], noise));
        if known.is_none()
            && let (Some(j), Some(k)) = (self.journal.as_ref(), journal_key.as_ref())
            && let Some(m) = j.get(k)
        {
            let m = std::sync::Arc::new(m);
            measured_groups()
                .lock()
                .unwrap()
                .insert(key.clone(), std::sync::Arc::clone(&m));
            known = Some(m);
        }
        let report = first_report(&key);
        if let Some(m) = &known
            && let Some(reason) = self.gate(index, m, report)
        {
            // Demoted: the other members are not needed at all.
            self.demoted.lock().unwrap().push((index, reason));
            return Ok(());
        }
        // Each member decoded on one thread, cache-resident; the three side by
        // side on the shared pool, or in turn on this thread.
        let decode = |p: &PathBuf| {
            strehl_raw::decode_serial(p, take_member_buffer())
                .with_context(|| p.display().to_string())
        };
        let frames: Vec<strehl_raw::Frame> = if serial {
            others.iter().map(decode).collect::<Result<_>>()?
        } else {
            others.par_iter().map(decode).collect::<Result<_>>()?
        };
        let members: [strehl_raw::Frame; 3] = frames
            .try_into()
            .map_err(|_| anyhow::anyhow!("group size changed"))?;
        let (m, reason) = match known {
            // Judged above: it passes.
            Some(m) => (m, None),
            None => {
                let frames = [first, &members[0], &members[1], &members[2]];
                // Under decode-ahead every decoding thread checks its own
                // groups: on a pool of one thread each, not the shared pool
                // the sixteen decoders' checks would contend for (MEASURED,
                // round-2 plan section 3.7: 1.36 core-seconds a group on one
                // thread, about 4.4 CPU-seconds through the shared pool). The
                // sums are added in row order whatever the pool
                // (`a_group_measures_the_same_bits_on_any_pool`).
                let m = std::sync::Arc::new(if serial {
                    on_one_thread(|| measure(frames, noise))
                } else {
                    measure(frames, noise)
                });
                if let (Some(j), Some(k)) = (self.journal.as_ref(), journal_key) {
                    j.append(k, index, &m);
                }
                measured_groups()
                    .lock()
                    .unwrap()
                    .insert(key, std::sync::Arc::clone(&m));
                let reason = self.gate(index, &m, report);
                (m, reason)
            }
        };
        match reason {
            Some(reason) => {
                recycle_members(members);
                self.demoted.lock().unwrap().push((index, reason));
            }
            None => {
                let c = &m.check;
                self.parked.lock().unwrap().insert(
                    index,
                    crate::align_cmd::MeasuredGroup {
                        members,
                        offsets: c.offsets,
                        gains: c.gains,
                        residuals: self.residual.sign().map(|s| (c.residual, s)),
                        keep: false,
                    },
                );
            }
        }
        Ok(())
    }

    /// [`Self::prepare`] for a member 1 decoded in part
    /// (`strehl_raw::decode_rows`): only for a group this process has
    /// already measured (a measurement needs whole members), whose members
    /// are then decoded over the same `rows`. Returns the buffer rows every
    /// member holds (`None`: every row). An unmeasured group is an error, so
    /// the caller decodes the frame in full instead.
    pub fn prepare_rows(
        &self,
        index: usize,
        path: &Path,
        first: &strehl_raw::Frame,
        rows: &[bool],
    ) -> Result<Option<Vec<bool>>> {
        let Some(others) = self.members.get(path) else {
            return Ok(None);
        };
        if self.mode == GroupMode::Member1 {
            self.demoted
                .lock()
                .unwrap()
                .push((index, "member1 comparison arm".into()));
            return Ok(None);
        }
        let noise = self.noise.get_or_init(|| {
            strehl_core::profile::noise_model_for(
                &first.camera,
                first.iso,
                strehl_core::noise::Levels {
                    black: first.levels.black,
                    white: first.levels.white,
                },
            )
        });
        let key = MeasurementKey {
            members: [
                path.to_path_buf(),
                others[0].clone(),
                others[1].clone(),
                others[2].clone(),
            ],
            noise: format!("{noise:?}"),
        };
        let m = measured_groups()
            .lock()
            .unwrap()
            .get(&key)
            .cloned()
            .with_context(|| format!("frame {index}: group not measured in this process"))?;
        if let Some(reason) = self.gate(index, &m, false) {
            self.demoted.lock().unwrap().push((index, reason));
            return Ok(None);
        }
        let decoded: Vec<(strehl_raw::Frame, Option<Vec<bool>>)> = others
            .par_iter()
            .map(|p| {
                strehl_raw::decode_rows(p, rows, take_member_buffer())
                    .with_context(|| p.display().to_string())
            })
            .collect::<Result<_>>()?;
        let mut valid: Option<Vec<bool>> = None;
        let mut frames = Vec::with_capacity(3);
        for (frame, rows) in decoded {
            if let Some(r) = rows {
                valid = Some(match valid {
                    Some(v) => v.iter().zip(&r).map(|(a, b)| *a && *b).collect(),
                    None => r,
                });
            }
            frames.push(frame);
        }
        let members: [strehl_raw::Frame; 3] = frames
            .try_into()
            .map_err(|_| anyhow::anyhow!("group size changed"))?;
        let c = &m.check;
        self.parked.lock().unwrap().insert(
            index,
            crate::align_cmd::MeasuredGroup {
                members,
                offsets: c.offsets,
                gains: c.gains,
                residuals: self.residual.sign().map(|s| (c.residual, s)),
                keep: false,
            },
        );
        Ok(valid)
    }

    /// The verdict this stack's mode gives frame `index`'s measured group,
    /// reported on stderr when `report` (once per group and process).
    fn gate(&self, index: usize, m: &GroupMeasurement, report: bool) -> Option<String> {
        let c = &m.check;
        // The ungated arm keeps only the structural refusals: offsets that do
        // not cover the lattice or cannot be measured.
        match (self.mode, judge(m, self.residual)) {
            (GroupMode::Ungated, Some(r))
                if c.parities && c.precision[1..].iter().all(|p| *p > 0.8) =>
            {
                if report {
                    eprintln!("pixel shift     : frame {index} assembled despite: {r}");
                }
                None
            }
            (_, Some(r)) => {
                if report {
                    eprintln!("pixel shift     : frame {index} demoted to member 1: {r}");
                }
                Some(r)
            }
            (_, None) => None,
        }
    }

    /// The other three members of the group whose member 1 is `path`.
    pub fn members_of(&self, path: &Path) -> Option<&[PathBuf; 3]> {
        self.members.get(path)
    }

    pub(crate) fn take(&self, index: usize) -> Option<crate::align_cmd::MeasuredGroup> {
        self.parked.lock().unwrap().remove(&index)
    }

    /// Each demoted frame once, in frame order. A frame can be decoded more
    /// than once in a render (`STREHL_AXIAL_CA` gathers red and blue a second
    /// time), and each decode records its demotion.
    pub fn demoted(&self) -> Vec<(usize, String)> {
        let mut d = self.demoted.lock().unwrap().clone();
        d.sort_by_key(|(i, _)| *i);
        d.dedup_by_key(|(i, _)| *i);
        d
    }
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;

    /// A four-member group of a smooth, textured scene: member `k` sees the
    /// scene shifted by `shifts[k]` photosites, at exposure `gains[k]`, in a
    /// buffer with a margin around the active area.
    pub(crate) fn synthetic_group(
        shifts: [(isize, isize); 4],
        gains: [f32; 4],
    ) -> [strehl_raw::Frame; 4] {
        let (aw, ah) = (320usize, 224usize);
        let (ox, oy) = (8usize, 6usize);
        let (stride, bh) = (aw + 2 * ox, ah + 2 * oy);
        // Triangle waves: only correctly rounded operations, so the samples
        // (and the pinned measurement) are the same on every platform.
        let tri = |t: f32| ((t.rem_euclid(2.0)) - 1.0).abs();
        let scene = |c: usize, x: isize, y: isize| -> f32 {
            let (xf, yf) = (x as f32, y as f32);
            let base = 900.0 + 400.0 * (tri(xf * 0.07) * tri(yf * 0.053));
            let tex = 300.0 * (((x * 7 + y * 13).rem_euclid(17)) as f32 / 17.0);
            [1.0, 1.6, 0.8][c] * (base + tex)
        };
        std::array::from_fn(|k| {
            let mut data = vec![0u16; stride * bh];
            for by in 0..bh {
                for bx in 0..stride {
                    let (ax, ay) = (bx as isize - ox as isize, by as isize - oy as isize);
                    let c = pixel_shift::cfa_colour(ax, ay);
                    // A little deterministic noise, so the witness has some.
                    let n = ((bx * 31 + by * 17 + k * 7) % 11) as f32 - 5.0;
                    let v = 512.0 + gains[k] * scene(c, ax - shifts[k].0, ay - shifts[k].1) + n;
                    data[by * stride + bx] = v.round() as u16;
                }
            }
            strehl_raw::Frame {
                data,
                stride,
                buffer_height: bh,
                active: strehl_raw::Region {
                    x: ox,
                    y: oy,
                    width: aw,
                    height: ah,
                },
                levels: strehl_core::noise::Levels {
                    black: 512.0,
                    white: 15360.0,
                },
                iso: Some(100.0),
                wb_coeffs: [2.0, 1.0, 1.5, f32::NAN],
                xyz_to_cam_rgbe: [[0.0; 3]; 4],
                color_matrices: Vec::new(),
                camera: "synthetic".into(),
                path: PathBuf::from(format!("synthetic-{k}")),
            }
        })
    }

    pub(crate) fn synthetic_noise() -> strehl_core::noise::NoiseModel {
        strehl_core::profile::noise_model_for(
            "synthetic",
            Some(100.0),
            strehl_core::noise::Levels {
                black: 512.0,
                white: 15360.0,
            },
        )
    }

    /// Every number in a measurement, as bits.
    fn bits(m: &GroupMeasurement) -> Vec<u64> {
        let c = &m.check;
        let mut v: Vec<u64> = Vec::new();
        for o in c.offsets {
            v.extend([o.0 as u64, o.1 as u64]);
        }
        v.extend(c.precision.map(f64::to_bits));
        v.extend(c.residual.iter().flatten().map(|x| x.to_bits()));
        v.extend(c.gains.map(f64::to_bits));
        v.push(u64::from(c.parities));
        if let Some(w) = &m.witness {
            v.extend(w.pair_shift.iter().flatten().map(|x| x.to_bits()));
            v.extend(w.pair_members.iter().flatten().map(|x| *x as u64));
            v.push(w.tile_ratio.to_bits());
            v.push(w.local_px.to_bits());
        }
        v.extend(m.margins.map(|x| x as u64));
        v.push(u64::from(m.levels_agree));
        v
    }

    /// A journal record holds the measurement exactly: written and read
    /// back, every number has the same bits, for a passing group and for one
    /// whose offsets do not cover the lattice (no witness).
    #[test]
    fn journal_records_round_trip_exactly() {
        let noise = synthetic_noise();
        for shifts in [
            [(0, 0), (1, 0), (1, 1), (0, 1)],
            [(0, 0), (1, 0), (0, 0), (0, 1)],
        ] {
            let frames = synthetic_group(shifts, [1.0, 1.004, 0.997, 1.0]);
            let m = measure([&frames[0], &frames[1], &frames[2], &frames[3]], &noise);
            let line = measurement_json(&m).to_string();
            let back =
                measurement_from_json(&serde_json::from_str(&line).unwrap()).expect("parses");
            assert_eq!(bits(&m), bits(&back), "{shifts:?}");
            assert_eq!(m.witness.is_some(), back.witness.is_some());
        }
        // A torn or foreign value is refused, not half-read.
        assert!(measurement_from_json(&json!({"offsets": [[0, 0]]})).is_none());
    }

    /// Pins `measure`'s output on a synthetic group. If this fails, what
    /// `measure` computes changed: bump `GROUP_CHECK_VERSION` (journaled
    /// measurements of the old code must not be reused), then update the
    /// digest here.
    #[test]
    fn measurement_bits_are_pinned_to_the_check_version() {
        use sha2::Digest;
        let frames = synthetic_group([(0, 0), (1, 0), (1, 1), (0, 1)], [1.0, 1.004, 0.997, 1.0]);
        let m = measure(
            [&frames[0], &frames[1], &frames[2], &frames[3]],
            &synthetic_noise(),
        );
        let bytes: Vec<u8> = bits(&m).iter().flat_map(|v| v.to_le_bytes()).collect();
        let digest = hex(&sha2::Sha256::digest(&bytes));
        assert_eq!(
            (GROUP_CHECK_VERSION, digest.as_str()),
            (
                2,
                "1842f805740b56fe8d6a714aee51ddfbd9efe5b032201b8d8646704923bcff47"
            ),
            "measure's output changed: bump GROUP_CHECK_VERSION and update this digest"
        );
    }

    /// The measurement is a pure function of the samples: the same bits on a
    /// pool of one thread and of eight (P1b caches it on that basis).
    #[test]
    fn a_group_measures_the_same_bits_on_any_pool() {
        let frames = synthetic_group([(0, 0), (1, 0), (1, 1), (0, 1)], [1.0, 1.004, 0.997, 1.0]);
        let noise = synthetic_noise();
        let on = |threads: usize| {
            rayon::ThreadPoolBuilder::new()
                .num_threads(threads)
                .build()
                .unwrap()
                .install(|| measure([&frames[0], &frames[1], &frames[2], &frames[3]], &noise))
        };
        let (a, b) = (on(1), on(8));
        assert!(a.witness.is_some(), "the planted group covers the lattice");
        assert_eq!(bits(&a), bits(&b));
        assert_eq!(judge(&a, ResidualMode::Compensate), None, "{:?}", a);
    }

    /// Writes a capture folder: one `capture_buffered` event per group
    /// `(plane, group id, first frame number, members durable)`, four
    /// members each, with receipts for the durable ones.
    fn capture_folder(name: &str, groups: &[(u64, &str, usize, usize)]) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("strehl-retake-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let (mut events, mut receipts) = (String::new(), String::new());
        for &(plane, group, first, durable) in groups {
            let files: Vec<Value> = (0..4)
                .map(|k| {
                    let name = format!("frame-{:06}.ARW", first + k);
                    let sha = format!("{:064x}", first + k);
                    std::fs::write(dir.join(&name), b"raw").unwrap();
                    if k < durable {
                        receipts.push_str(&json!({"logical_name":name,"sha256":sha,"durable":true,"ok":true}).to_string());
                        receipts.push('\n');
                    }
                    json!({"name":name,"plane":plane,"sha256":sha,"group_id":group,"member_index":k+1,"members":4})
                })
                .collect();
            events.push_str(
                &json!({"event":"capture_buffered","data":{"target":100+plane,"response":{"files":files}}})
                    .to_string(),
            );
            events.push('\n');
        }
        std::fs::write(dir.join("events.jsonl"), events).unwrap();
        std::fs::write(dir.join("transfer-receipts.jsonl"), receipts).unwrap();
        dir
    }

    /// A plane retaken during the capture keeps its last complete group; a
    /// run without retakes reads exactly as before.
    #[test]
    fn a_retaken_plane_uses_its_last_complete_group() {
        let plain = capture_folder("plain", &[(1, "g1", 1, 4), (2, "g2", 5, 4)]);
        let groups = recorded_groups(&plain).unwrap();
        assert_eq!(groups.len(), 2);
        assert!(groups.iter().all(|g| g.complete && g.files.len() == 4));
        assert_eq!(all_groups(&plain).unwrap().len(), 2);

        // Plane 2 failed its check and was retaken as g2b; plane 3's retake
        // g3b never completed, so plane 3 keeps its complete first group.
        let dir = capture_folder(
            "retaken",
            &[
                (1, "g1", 1, 4),
                (2, "g2", 5, 4),
                (2, "g2b", 9, 4),
                (3, "g3", 13, 4),
                (3, "g3b", 17, 2),
            ],
        );
        assert_eq!(all_groups(&dir).unwrap().len(), 5);
        let groups = recorded_groups(&dir).unwrap();
        let chosen: Vec<(u64, &str, bool)> = groups
            .iter()
            .map(|g| (g.plane, g.group_id.as_str(), g.complete))
            .collect();
        assert_eq!(chosen, [(1, "g1", true), (2, "g2b", true), (3, "g3", true)]);
        assert_eq!(groups[1].files[0].name, "frame-000009.ARW");
        assert_eq!(groups[1].key(), "g2b");
        let _ = std::fs::remove_dir_all(&plain);
        let _ = std::fs::remove_dir_all(&dir);
    }

    /// Plan X3/X4: a highlight group under its base group's plane number is
    /// neither a retake nor the plane's group; the tier is read per file,
    /// else per event, and absent means base.
    #[test]
    fn a_highlight_group_never_replaces_its_plane() {
        let dir = capture_folder(
            "tiers",
            &[
                (1, "b1", 1, 4),
                (1, "h1", 5, 4),
                (2, "b2", 9, 4),
                (2, "h2", 13, 4),
                (3, "s3", 17, 4),
            ],
        );
        // Tag the groups as the Pi does: h1 per file, h2 per event only.
        let text = std::fs::read_to_string(dir.join("events.jsonl")).unwrap();
        let lines: Vec<String> = text
            .lines()
            .map(|l| {
                let mut v: Value = serde_json::from_str(l).unwrap();
                let id = v["data"]["response"]["files"][0]["group_id"]
                    .as_str()
                    .unwrap()
                    .to_string();
                match id.as_str() {
                    "h1" => {
                        for f in v["data"]["response"]["files"].as_array_mut().unwrap() {
                            f["tier"] = json!("highlight");
                        }
                        v["data"]["exposure"] = json!({"iso": 100, "shutter": 65540});
                    }
                    "h2" => {
                        v["data"]["tier"] = json!("highlight");
                        v["data"]["exposure"] = json!({"iso": 100, "shutter": 65540});
                    }
                    "s3" => v["data"]["tier"] = json!("shadow"),
                    "b1" => {
                        v["data"]["tier"] = json!("base");
                        v["data"]["exposure"] = json!({"iso": 100, "shutter": 1310730});
                    }
                    _ => {}
                }
                v.to_string()
            })
            .collect();
        std::fs::write(dir.join("events.jsonl"), lines.join("\n") + "\n").unwrap();
        let all = all_groups(&dir).unwrap();
        let tiers: Vec<(&str, Tier, Option<u64>)> = all
            .iter()
            .map(|g| (g.group_id.as_str(), g.tier.clone(), g.shutter))
            .collect();
        assert_eq!(
            tiers,
            [
                ("b1", Tier::Base, Some(1310730)),
                ("h1", Tier::Highlight, Some(65540)),
                ("b2", Tier::Base, None),
                ("h2", Tier::Highlight, Some(65540)),
                ("s3", Tier::Other("shadow".into()), None),
            ]
        );
        let planes: Vec<(u64, String)> = recorded_groups(&dir)
            .unwrap()
            .iter()
            .map(|g| (g.plane, g.group_id.clone()))
            .collect();
        assert_eq!(planes, [(1, "b1".into()), (2, "b2".into())]);
        let highlights = tier_groups(all, &Tier::Highlight);
        assert_eq!(highlights.keys().copied().collect::<Vec<_>>(), [1, 2]);
        assert_eq!(shutter_seconds(1310730), Some(2.0));
        assert_eq!(shutter_seconds(65540), Some(0.25));
        assert_eq!(shutter_seconds(0), None);
        let _ = std::fs::remove_dir_all(&dir);
    }

    /// h-retake: a retake the user asked for after the capture ended is
    /// recorded after its `finished` event, in the same journal, under its
    /// plane's number; it is the plane's last complete group, so the stack
    /// uses it. The checker keeps the run open until the retakes end.
    #[test]
    fn a_retake_after_the_capture_is_the_group_the_stack_uses() {
        let dir = capture_folder(
            "followup",
            &[
                (1, "g1", 1, 4),
                (2, "g2", 5, 4),
                (3, "g3", 9, 4),
                (2, "g2m", 13, 4),
            ],
        );
        // The capture's end, then the retakes' start, between groups 3 and
        // the manual retake of plane 2, as the host writes them.
        let text = std::fs::read_to_string(dir.join("events.jsonl")).unwrap();
        let mut lines: Vec<&str> = text.lines().collect();
        let finished = json!({"event":"finished","data":{"outcome":"complete"}}).to_string();
        let started =
            json!({"event":"followup_started","data":{"planes":[2],"manual":true}}).to_string();
        lines.insert(3, &started);
        lines.insert(3, &finished);
        std::fs::write(dir.join("events.jsonl"), lines.join("\n") + "\n").unwrap();
        std::fs::write(dir.join("result.json"), "{}").unwrap();
        let groups = recorded_groups(&dir).unwrap();
        let chosen: Vec<(u64, &str)> = groups
            .iter()
            .map(|g| (g.plane, g.group_id.as_str()))
            .collect();
        assert_eq!(chosen, [(1, "g1"), (2, "g2m"), (3, "g3")]);
        assert!(crate::follow_cmd::followup_open(&dir));
        let mut text = std::fs::read_to_string(dir.join("events.jsonl")).unwrap();
        text.push_str(
            &(json!({"event":"followup_finished","data":{"outcome":"complete","taken":1,"skipped":0}})
                .to_string()
                + "\n"),
        );
        std::fs::write(dir.join("events.jsonl"), text).unwrap();
        assert!(!crate::follow_cmd::followup_open(&dir));
        let _ = std::fs::remove_dir_all(&dir);
    }

    /// A retake is suggested only for a fault of the exposures, never for a
    /// plane a retake would fail the same way.
    #[test]
    fn only_exposure_faults_are_worth_a_retake() {
        let frames = synthetic_group([(0, 0), (1, 0), (1, 1), (0, 1)], [1.0, 1.004, 0.997, 1.0]);
        let good = measure(
            [&frames[0], &frames[1], &frames[2], &frames[3]],
            &synthetic_noise(),
        );
        let r = ResidualMode::Compensate;
        assert!(!retake_helps(&good, r), "a passing group needs no retake");
        let mut flat = good.clone();
        flat.check.precision[2] = 0.3;
        assert!(
            judge(&flat, r)
                .unwrap()
                .contains("too little scene structure")
        );
        assert!(!retake_helps(&flat, r));
        let mut moved = good.clone();
        moved.witness.as_mut().unwrap().local_px = LOCAL_TOLERANCE_PX * 2.0;
        assert!(judge(&moved, r).unwrap().contains("witness tiles disagree"));
        assert!(retake_helps(&moved, r));
        let mut flicker = good.clone();
        flicker.levels_agree = false;
        assert!(judge(&flicker, r).unwrap().contains("black or white level"));
        assert!(retake_helps(&flicker, r));
        let mut edge = good.clone();
        edge.margins = [0; 4];
        assert!(judge(&edge, r).unwrap().contains("leave the sensor buffer"));
        assert!(!retake_helps(&edge, r));
        // Misregistered only once the measured residuals are applied: the
        // exposures agree and the residual estimate is what fails.
        let mut estimate = good.clone();
        let w = estimate.witness.as_mut().unwrap();
        let [a, b] = w.pair_members[0];
        w.pair_shift[0] = [0.05, 0.0];
        estimate.check.residual[b] = [
            estimate.check.residual[a][0] + 0.45,
            estimate.check.residual[a][1],
        ];
        assert!(
            judge(&estimate, r)
                .unwrap()
                .contains("after residual compensation")
        );
        assert!(!retake_helps(&estimate, r));
        // A tile map with nothing measurable judges nothing locally.
        let mut quiet = good.clone();
        quiet.witness.as_mut().unwrap().local_px = f64::NAN;
        assert_eq!(judge(&quiet, r), None);
        // Misregistered in the exposures themselves: worth a retake.
        let mut shaken = good;
        let w = shaken.witness.as_mut().unwrap();
        let [a, b] = w.pair_members[0];
        w.pair_shift[0] = [0.45, 0.0];
        shaken.check.residual[b] = shaken.check.residual[a];
        assert!(judge(&shaken, r).unwrap().contains("misregistered"));
        assert!(retake_helps(&shaken, r));
    }

    /// A group of a continuous scene: a smooth background and, inside a
    /// central oval (the subject), detail from about 16 to 4 photosites a
    /// cycle. Member `k` sees it shifted by `shifts[k]` photosites
    /// (fractions allowed), at `exposure` times a base light of 1000 DN in
    /// green, with noise drawn to the injected (fallback, 1 DN/e) model: at
    /// `exposure` 1 about the close tile's 1/4 s signal-to-noise. `moved`:
    /// one member's patch `[x, y, w, h]` (active coordinates) shifted by a
    /// further `(dx, dy)`.
    fn exposed_group(
        shifts: [(f32, f32); 4],
        exposure: f32,
        moved: Option<(usize, [isize; 4], (f32, f32))>,
    ) -> [strehl_raw::Frame; 4] {
        let (aw, ah) = (512usize, 384usize);
        let (ox, oy) = (8usize, 8usize);
        let (stride, bh) = (aw + 2 * ox, ah + 2 * oy);
        let noise = synthetic_noise();
        let scene = |x: f32, y: f32| -> f32 {
            let w =
                |fx: f32, fy: f32, p: f32| (std::f32::consts::TAU * (fx * x + fy * y) + p).sin();
            let r = ((x - 256.0) / 170.0).powi(2) + ((y - 192.0) / 130.0).powi(2);
            let subject = (1.0 - (r - 1.0) * 4.0).clamp(0.0, 1.0);
            1.2 + 0.35 * w(0.021, 0.013, 0.3) * w(-0.008, 0.019, 1.1)
                + subject
                    * (0.25 * w(0.061, 0.037, 2.0)
                        + 0.20 * w(-0.043, 0.088, 0.7)
                        + 0.15 * w(0.14, -0.09, 1.9)
                        + 0.10 * w(0.05, 0.21, 0.4))
        };
        let mut seed = 0x9E37_79B9_7F4A_7C15u64 ^ u64::from(exposure.to_bits());
        let mut uniform = move || {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            ((seed >> 11) as f64 + 0.5) / (1u64 << 53) as f64
        };
        std::array::from_fn(|k| {
            let mut data = vec![0u16; stride * bh];
            for by in 0..bh {
                for bx in 0..stride {
                    let (ax, ay) = (bx as isize - ox as isize, by as isize - oy as isize);
                    let (mut sx, mut sy) = shifts[k];
                    if let Some((m, [px, py, pw, ph], (dx, dy))) = moved
                        && m == k
                        && (px..px + pw).contains(&ax)
                        && (py..py + ph).contains(&ay)
                    {
                        sx += dx;
                        sy += dy;
                    }
                    let c = pixel_shift::cfa_colour(ax, ay);
                    let s = exposure
                        * 1000.0
                        * [0.7, 1.0, 0.5][c]
                        * scene(ax as f32 - sx, ay as f32 - sy);
                    let sigma = noise.variance(strehl_core::CfaPlane::G1, s).sqrt();
                    let gauss =
                        (-2.0 * uniform().ln()).sqrt() * (std::f64::consts::TAU * uniform()).cos();
                    let v = 512.0 + s + sigma * gauss as f32;
                    data[by * stride + bx] = v.round().clamp(0.0, 16383.0) as u16;
                }
            }
            strehl_raw::Frame {
                data,
                stride,
                buffer_height: bh,
                active: strehl_raw::Region {
                    x: ox,
                    y: oy,
                    width: aw,
                    height: ah,
                },
                levels: strehl_core::noise::Levels {
                    black: 512.0,
                    white: 15360.0,
                },
                iso: Some(100.0),
                wb_coeffs: [2.0, 1.0, 1.5, f32::NAN],
                xyz_to_cam_rgbe: [[0.0; 3]; 4],
                color_matrices: Vec::new(),
                camera: "synthetic".into(),
                path: PathBuf::from(format!("exposed-{k}")),
            }
        })
    }

    fn measure_group(frames: &[strehl_raw::Frame; 4]) -> GroupMeasurement {
        measure(
            [&frames[0], &frames[1], &frames[2], &frames[3]],
            &synthetic_noise(),
        )
    }

    /// Plan Q5: the same offset between the shots gets the same verdict at
    /// the close tile's 1/4 s light and at four times it. The rig's sway
    /// moves whole shots by 0.2 to 0.5 px; the assembly lines them up to
    /// their measured offsets, so the check judges what is left, in
    /// photosites. The old tile ratio, on the same groups, grows with the
    /// light (the fault this replaces).
    #[test]
    fn the_same_offset_gets_the_same_verdict_at_any_exposure() {
        let r = ResidualMode::Compensate;
        // Members 2 and 3 swayed 0.4 px along y, member 4 0.25 px along x.
        let shifts = [(0.0, 0.0), (1.0, 0.4), (1.0, 1.4), (0.25, 1.0)];
        let dim = measure_group(&exposed_group(shifts, 1.0, None));
        let bright = measure_group(&exposed_group(shifts, 4.0, None));
        let (wd, wb) = (
            dim.witness.as_ref().unwrap(),
            bright.witness.as_ref().unwrap(),
        );
        eprintln!(
            "dim: local {:.3} px, ratio {:.2}, verdict {:?}; bright: local {:.3} px, ratio {:.2}, verdict {:?}",
            wd.local_px,
            wd.tile_ratio,
            judge(&dim, r),
            wb.local_px,
            wb.tile_ratio,
            judge(&bright, r)
        );
        assert_eq!(judge(&dim, r), None, "{dim:?}");
        assert_eq!(judge(&bright, r), None, "{bright:?}");
        assert!((wd.local_px - wb.local_px).abs() < 0.1, "{wd:?} {wb:?}");
        // The statistic the check no longer judges grows with the light, and
        // on these groups it would have passed the dim one and failed the
        // bright one.
        assert!(wb.tile_ratio > 1.5 * wd.tile_ratio, "{wd:?} {wb:?}");
        assert!(
            wd.tile_ratio < TILE_RATIO_TOLERANCE && wb.tile_ratio >= TILE_RATIO_TOLERANCE,
            "{wd:?} {wb:?}"
        );
        // With no sway at all, the same verdict too.
        let still = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)];
        for exposure in [1.0, 4.0] {
            let m = measure_group(&exposed_group(still, exposure, None));
            assert_eq!(judge(&m, r), None, "{m:?}");
        }
    }

    /// Motion in one part of the frame still fails, at either exposure,
    /// and asks for a retake: a 96 px patch of one shot moved 1 px.
    #[test]
    fn motion_in_one_part_of_the_frame_fails_at_any_exposure() {
        let r = ResidualMode::Compensate;
        let shifts = [(0.0, 0.0), (1.0, 0.3), (1.0, 1.3), (0.0, 1.3)];
        for exposure in [1.0, 4.0] {
            let m = measure_group(&exposed_group(
                shifts,
                exposure,
                Some((2, [300, 150, 96, 96], (0.0, 1.0))),
            ));
            let reason = judge(&m, r).unwrap_or_default();
            assert!(
                reason.contains("witness tiles disagree locally"),
                "{exposure}: {m:?}"
            );
            assert!(retake_helps(&m, r));
        }
    }

    /// A shot that slipped by a whole photosite fails, and asks for a
    /// retake: its offsets land on another shot's colour site.
    #[test]
    fn a_whole_photosite_slip_fails_and_asks_for_a_retake() {
        let r = ResidualMode::Compensate;
        for exposure in [1.0, 4.0] {
            let slipped = [(0.0, 0.0), (1.0, 0.3), (1.0, 2.3), (0.0, 1.3)];
            let m = measure_group(&exposed_group(slipped, exposure, None));
            assert!(!m.check.parities, "{m:?}");
            let reason = judge(&m, r).unwrap();
            assert!(
                reason.contains("do not cover the four CFA parities"),
                "{reason}"
            );
            assert!(reason.contains("slipped by a whole photosite"), "{reason}");
            assert!(retake_helps(&m, r));
        }
        // A slip past the search window: that shot reads no structure, the
        // others do. Still a slip.
        let frames = synthetic_group([(0, 0), (1, 0), (2, 1), (0, 1)], [1.0; 4]);
        let mut m = measure(
            [&frames[0], &frames[1], &frames[2], &frames[3]],
            &synthetic_noise(),
        );
        assert!(!m.check.parities);
        m.check.precision[2] = 0.0;
        assert!(judge(&m, r).unwrap().contains("slipped"));
        assert!(retake_helps(&m, r));
        // A scene without structure, or a camera that did not shift, is not
        // a slip: a retake would fail the same way.
        let mut flat = m.clone();
        flat.check.precision = [1.0, 0.3, 0.0, 0.2];
        assert!(!judge(&flat, r).unwrap().contains("slipped"));
        assert!(!retake_helps(&flat, r));
        let mut still = m;
        still.check.offsets = [(0, 0); 4];
        assert!(!retake_helps(&still, r));
    }

    /// Plants on real groups (plan Q5's gate), read-only:
    /// `STREHL_PLANECHECK_FIXTURES="<run dir>|<plane>;..."`. For each plane's
    /// group as the stack uses it: as taken; one shot slipped a whole row; a
    /// patch of one shot moved a whole row (motion in one part); one shot
    /// from the next plane's group (a focus slip or a wrong member).
    /// `cargo test --release -p strehl-cli planted_faults_on_real_groups -- --ignored --nocapture`
    #[test]
    #[ignore = "needs capture folders; set STREHL_PLANECHECK_FIXTURES"]
    fn planted_faults_on_real_groups() {
        let spec = std::env::var("STREHL_PLANECHECK_FIXTURES").expect("STREHL_PLANECHECK_FIXTURES");
        let r = ResidualMode::Compensate;
        let decode = |g: &RecordedGroup| -> Vec<strehl_raw::Frame> {
            g.files
                .iter()
                .map(|f| strehl_raw::decode(&f.path).unwrap())
                .collect()
        };
        let mut failures = Vec::new();
        for item in spec.split(';').filter(|s| !s.trim().is_empty()) {
            let (dir, plane) = item.rsplit_once('|').expect("<dir>|<plane>");
            let plane: u64 = plane.trim().parse().unwrap();
            let groups = recorded_groups(Path::new(dir.trim())).unwrap();
            let at = |p: u64| groups.iter().find(|g| g.plane == p && g.complete).unwrap();
            let mut frames = decode(at(plane));
            let next = decode(at(plane + 1));
            let first = &frames[0];
            let noise = strehl_core::profile::noise_model_for(
                &first.camera,
                first.iso,
                strehl_core::noise::Levels {
                    black: first.levels.black,
                    white: first.levels.white,
                },
            );
            let judge_of = |f: [&strehl_raw::Frame; 4]| {
                let (m, w) = measure_with_tiles(f, &noise);
                (judge(&m, r), retake_helps(&m, r), m, w)
            };
            let (taken, _, m0, w0) = judge_of([&frames[0], &frames[1], &frames[2], &frames[3]]);
            let local0 = m0.witness.as_ref().map_or(f64::NAN, |w| w.local_px);
            // The patch: 768 px square about the median measured tile.
            let w0 = w0.expect("a witness");
            let (mut xs, mut ys) = (Vec::new(), Vec::new());
            for (i, v) in w0.tile_local_px.iter().enumerate() {
                if v.is_finite() {
                    xs.push(i % w0.tiles[0]);
                    ys.push(i / w0.tiles[0]);
                }
            }
            xs.sort_unstable();
            ys.sort_unstable();
            let (cx, cy) = (xs[xs.len() / 2] * w0.tile, ys[ys.len() / 2] * w0.tile);
            let report = |name: &str,
                          (reason, retake, m, _): (
                Option<String>,
                bool,
                GroupMeasurement,
                Option<pixel_shift::Witness>,
            )| {
                eprintln!(
                    "{dir} plane {plane} {name}: local {:.3} px, offsets {:?} structure {:.3?} | {} (retake {retake})",
                    m.witness.as_ref().map_or(f64::NAN, |w| w.local_px),
                    &m.check.offsets[1..],
                    &m.check.precision[1..],
                    reason.as_deref().unwrap_or("pass")
                );
                (reason, retake)
            };
            eprintln!(
                "{dir} plane {plane} as taken: local {local0:.3} px | {}",
                taken.as_deref().unwrap_or("pass")
            );
            // One shot slipped a whole row, up and down.
            let s = frames[2].stride;
            for (name, up) in [
                ("shot 3 slipped one row up", true),
                ("shot 3 slipped one row down", false),
            ] {
                let mut slipped = frames[2].clone();
                if up {
                    slipped.data.rotate_left(s);
                } else {
                    slipped.data.rotate_right(s);
                }
                let (reason, retake) = report(
                    name,
                    judge_of([&frames[0], &frames[1], &slipped, &frames[3]]),
                );
                if !reason
                    .as_deref()
                    .is_some_and(|r| r.contains("slipped by a whole photosite"))
                    || !retake
                {
                    failures.push(format!("{dir} {plane}: {name}: not caught as a slip"));
                }
            }
            // A patch of one shot moved in the scene: by two rows of the
            // mosaic (2 px, each colour onto itself), or by the mean of
            // zero and two rows (1 px, with a little blur).
            let (ax, ay) = (frames[2].active.x + cx, frames[2].active.y + cy);
            let half = 384usize;
            for (name, mix) in [
                ("a 768 px patch of shot 3 moved 2 px", 1.0f32),
                ("a 768 px patch of shot 3 moved 1 px", 0.5),
            ] {
                let mut moved = frames[2].clone();
                for y in ay.saturating_sub(half).max(2)..(ay + half).min(moved.buffer_height) {
                    for x in ax.saturating_sub(half)..(ax + half).min(s) {
                        let (here, above) = (
                            f32::from(frames[2].data[y * s + x]),
                            f32::from(frames[2].data[(y - 2) * s + x]),
                        );
                        moved.data[y * s + x] = (here + mix * (above - here)).round() as u16;
                    }
                }
                let (reason, retake) =
                    report(name, judge_of([&frames[0], &frames[1], &moved, &frames[3]]));
                let caught = reason
                    .as_deref()
                    .is_some_and(|r| r.contains("disagree locally") || r.contains("slipped"));
                if !caught || !retake {
                    failures.push(format!("{dir} {plane}: {name}: not caught"));
                }
            }
            // Shot 4 from the next plane.
            let swapped = frames.pop().unwrap();
            let (reason, _) = report(
                "shot 4 from the next plane",
                judge_of([&frames[0], &frames[1], &frames[2], &next[3]]),
            );
            if reason.is_none() {
                failures.push(format!("{dir} {plane}: next plane's shot passed"));
            }
            drop(swapped);
        }
        assert!(failures.is_empty(), "{failures:#?}");
    }
}
