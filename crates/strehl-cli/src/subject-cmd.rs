//! `strehl subject <run>`: the capture's subject, found automatically
//! (plan S2, `docs/proposals/2026-11-subject-highlights-and-detail-plan.md`).
//!
//! Reads member 1 of each plane's recorded group (four-shot archives decode
//! through the ordinary path), reduces each exposure to 8 px evidence cells
//! with the camera profile's injected noise model, and selects the subject
//! with `strehl_core::subject`. Read-only over the capture; outputs are
//! refused inside the capture folder.
//!
//! The JSON written here ([`SubjectJson`]) is the contract with the capture
//! host and the desktop, which mirror it rather than share a Rust type.

use anyhow::{Context, Result, bail, ensure};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::time::Instant;
use strehl_core::CfaPlane;
use strehl_core::focus_contrast::Tiles;
use strehl_core::noise::Provenance;
use strehl_core::profile;
use strehl_core::subject::{
    CfaView, Evidence, FrameCells, Params, PlaneRef, Registration, Selection, Source,
    ThresholdKind, assemble, quiet, raw_frame_cells, raw_layout, select,
};

use crate::pixel_shift_cmd::recorded_groups;

#[derive(clap::Args, Debug)]
pub struct SubjectArgs {
    /// Capture run folder.
    pub dir: PathBuf,
    /// Use every N-th recorded plane, from the first.
    #[arg(long, conflicts_with = "planes")]
    pub every: Option<usize>,
    /// Use these plane ordinals (comma separated).
    #[arg(long, value_delimiter = ',', conflicts_with = "every")]
    pub planes: Option<Vec<u64>>,
    /// Without --every or --planes: this many planes, evenly spread over
    /// the run (all of them when the run has fewer).
    #[arg(long, default_value_t = 13)]
    pub count: usize,
    /// Threshold in lower-side spreads of the quiet population (x2).
    #[arg(long, default_value_t = 3.0)]
    pub sensitivity: f32,
    /// Hysteresis growth, spreads (0: off).
    #[arg(long, default_value_t = 3.0)]
    pub grow: f32,
    /// Margin around the subject, sensor pixels.
    #[arg(long, default_value_t = 16.0)]
    pub buffer: f32,
    /// Do not register the planes by a magnification rate.
    #[arg(long)]
    pub no_register: bool,
    /// Print the subject JSON on stdout (the report goes to stderr).
    #[arg(long)]
    pub json: bool,
    /// Also write the subject JSON here.
    #[arg(long)]
    pub out: Option<PathBuf>,
    /// Write the mask raster as a PNG, one pixel per 8 px cell (debug).
    #[arg(long)]
    pub mask_png: Option<PathBuf>,
    /// Write the stored evidence (debug): little-endian f32 focus, f32
    /// level and u16 sharpest-plane index per cell, row-major, one after the
    /// other; the grid is the JSON's `grid`.
    #[arg(long, hide = true)]
    pub dump_evidence: Option<PathBuf>,
    /// The sharp width (focus units) the suggested bounds add half of on
    /// each side. Default: the `width` of the run's `focus-step.json`, if
    /// one exists, else 0.
    #[arg(long)]
    pub width: Option<f64>,
}

/// Suggested start and end focus for capturing the same subject again
/// (plan S4): the subject's first and last sharp focus plus half a sharp
/// width on each side, in the run's direction, rounded outward to whole
/// focus units. Offered, not applied (owner's decision 1).
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BoundsJson {
    pub start: f64,
    pub end: f64,
    /// The sharp width used, focus units, and where it came from:
    /// `"given"` (`--width`), `"focus-step"` (the run's `focus-step.json`)
    /// or `"none"` (0).
    pub sharp_width: f64,
    pub width_from: String,
    /// The run as captured: its first and last recorded focus, its planes.
    pub run_start: f64,
    pub run_end: f64,
    pub run_planes: usize,
    /// Recorded planes inside the suggestion, those outside it, and the
    /// suggestion's span over the run's.
    pub planes: usize,
    pub planes_saved: usize,
    pub fraction: f64,
    /// The subject is sharpest at the run's first or last plane: it may
    /// extend beyond what was captured, so that side is a lower bound.
    pub reaches_run_start: bool,
    pub reaches_run_end: bool,
    /// The same from the planes holding the central 99 % of the in-focus
    /// subject cells (`depth.core_*`): robust to the extremes the
    /// three-plane mean puts one survey plane wide.
    pub core: Option<BoundsCore>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BoundsCore {
    pub start: f64,
    pub end: f64,
    pub planes: usize,
    pub planes_saved: usize,
    pub fraction: f64,
}

/// The run's planes (ordinal, recorded focus) in ordinal order, the depth,
/// and a sharp width: [`BoundsJson`], or `None` without recorded positions.
pub fn bounds(
    depth: &DepthJson,
    run: &[(u64, Option<f64>)],
    width: f64,
    width_from: &str,
) -> Option<BoundsJson> {
    let focus_of = |o: u64| run.iter().find(|p| p.0 == o).and_then(|p| p.1);
    let (first, last) = (run.first()?, run.last()?);
    let (run_start, run_end) = (first.1?, last.1?);
    let dir = if run_end < run_start { -1.0 } else { 1.0 };
    let half = 0.5 * width.max(0.0);
    let positions: Vec<f64> = run.iter().filter_map(|p| p.1).collect();
    let span = (run_end - run_start).abs().max(f64::MIN_POSITIVE);
    // Start and end, rounded outward in the run's direction; planes inside.
    let around = |a: f64, b: f64| {
        let (s, e) = (a - dir * half, b + dir * half);
        let (s, e) = if dir > 0.0 {
            (s.floor(), e.ceil())
        } else {
            (s.ceil(), e.floor())
        };
        let (lo, hi) = (s.min(e), s.max(e));
        let planes = positions.iter().filter(|p| (lo..=hi).contains(*p)).count();
        (s, e, planes, (e - s).abs() / span)
    };
    // The in-focus range from contrast when it was read (spec 5.2: the
    // larger of half the width and half the spacing; a side the subject
    // reaches keeps the run's own end); else the earlier rule.
    let contrast = depth.in_focus_first.zip(depth.in_focus_last);
    let (start, end, planes, fraction) = match contrast {
        Some(_) => {
            // `suggested_*` are in increasing focus and absent on a side the
            // subject reaches: there the run's own end stands.
            let low = depth.suggested_start.unwrap_or(run_start.min(run_end));
            let high = depth.suggested_end.unwrap_or(run_start.max(run_end));
            let (s, e) = if dir > 0.0 { (low, high) } else { (high, low) };
            let planes = positions
                .iter()
                .filter(|p| (low..=high).contains(*p))
                .count();
            (s, e, planes, (e - s).abs() / span)
        }
        None => around(depth.first_focus?, depth.last_focus?),
    };
    let core = match (
        focus_of(depth.core_first_plane),
        focus_of(depth.core_last_plane),
    ) {
        (Some(a), Some(b)) => {
            let (start, end, planes, fraction) = around(a, b);
            Some(BoundsCore {
                start,
                end,
                planes,
                planes_saved: positions.len() - planes,
                fraction,
            })
        }
        _ => None,
    };
    Some(BoundsJson {
        start,
        end,
        sharp_width: width.max(0.0),
        width_from: width_from.into(),
        run_start,
        run_end,
        run_planes: positions.len(),
        planes,
        planes_saved: positions.len() - planes,
        fraction,
        reaches_run_start: (if dir > 0.0 {
            depth.reaches_first
        } else {
            depth.reaches_last
        })
        .unwrap_or(depth.first_plane == first.0),
        reaches_run_end: (if dir > 0.0 {
            depth.reaches_last
        } else {
            depth.reaches_first
        })
        .unwrap_or(depth.last_plane == last.0),
        core,
    })
}

/// A run's planes in ordinal order: ordinal, recorded focus position,
/// member-1 file.
pub fn run_planes(dir: &Path) -> Result<Vec<(u64, Option<f64>, PathBuf)>> {
    let mut planes: Vec<(u64, Option<f64>, PathBuf)> = recorded_groups(dir)?
        .into_iter()
        .filter_map(|g| {
            let first = g.files.iter().find(|f| f.durable)?;
            Some((g.plane, g.target.map(|t| t as f64), first.path.clone()))
        })
        .collect();
    planes.sort_by_key(|p| p.0);
    Ok(planes)
}

/// Which planes to use: `planes` by ordinal, every `every`-th, or `count`
/// spread evenly (first and last included).
pub fn choose<T: Clone>(
    all: &[(u64, T)],
    planes: Option<&[u64]>,
    every: Option<usize>,
    count: usize,
) -> Result<Vec<(u64, T)>> {
    if let Some(want) = planes {
        // Focus order is ordinal order; a repeated ordinal counts once.
        let mut want = want.to_vec();
        want.sort_unstable();
        want.dedup();
        return want
            .iter()
            .map(|o| {
                all.iter()
                    .find(|p| p.0 == *o)
                    .cloned()
                    .with_context(|| format!("plane {o} is not recorded in this run"))
            })
            .collect();
    }
    if let Some(n) = every {
        ensure!(n >= 1, "--every must be at least 1");
        return Ok(all.iter().step_by(n).cloned().collect());
    }
    let n = all.len();
    if count == 0 || n <= count {
        return Ok(all.to_vec());
    }
    Ok((0..count)
        .map(|k| all[k * (n - 1) / (count - 1).max(1)].clone())
        .collect())
}

/// Evidence of a run from the chosen planes, how long the decode took, and
/// each plane's contrast tiles ([`crate::depth_contrast::frame_tiles`]) from
/// the same decode.
pub fn run_evidence(
    dir: &Path,
    chosen: &[(u64, (Option<f64>, PathBuf))],
    registration: Registration,
) -> Result<(Evidence, Provenance, f64, Vec<Tiles>)> {
    let t = Instant::now();
    type Decoded = (FrameCells, Provenance, [usize; 2], Tiles);
    let cells: Vec<Decoded> = chosen
        .par_iter()
        .map(|(_, (_, path))| -> Result<Decoded> {
            let f = strehl_raw::decode(path).with_context(|| path.display().to_string())?;
            let noise = profile::noise_model_for(&f.camera, f.iso, f.levels);
            let view = CfaView {
                data: &f.data,
                stride: f.stride,
                x0: f.active.x,
                y0: f.active.y,
                width: f.active.width,
                height: f.active.height,
                black: f.levels.black,
                white: f.levels.white,
            };
            let variance = |s: f32| noise.variance(CfaPlane::G1, s);
            Ok((
                raw_frame_cells(&view, &variance),
                noise.provenance,
                [f.active.width, f.active.height],
                crate::depth_contrast::frame_tiles(&f),
            ))
        })
        .collect::<Result<_>>()?;
    let secs = t.elapsed().as_secs_f64();
    let size = cells[0].2;
    ensure!(
        cells.iter().all(|c| c.2 == size),
        "{}: exposures of different sizes in one run",
        dir.display()
    );
    let provenance = cells[0].1;
    let (frames, tiles): (Vec<FrameCells>, Vec<Tiles>) =
        cells.into_iter().map(|c| (c.0, c.3)).unzip();
    let planes: Vec<PlaneRef> = chosen
        .iter()
        .map(|(o, (pos, _))| PlaneRef {
            ordinal: *o,
            position: *pos,
        })
        .collect();
    Ok((
        assemble(frames, planes, raw_layout(size[0], size[1]), registration),
        provenance,
        secs,
        tiles,
    ))
}

fn refuse_inside(dir: &Path, out: &Path) -> Result<()> {
    let canon = |p: &Path| std::fs::canonicalize(p).unwrap_or_else(|_| p.to_path_buf());
    let parent = out.parent().filter(|p| !p.as_os_str().is_empty());
    let target = parent.map_or_else(|| canon(Path::new(".")), canon);
    if target.starts_with(canon(dir)) {
        bail!(
            "{} is inside the capture folder; capture folders are read-only",
            out.display()
        );
    }
    Ok(())
}

/// The subject JSON: the contract with the capture host and the desktop.
/// `rings`, `cell_px`, `provenance`, `depth`, `area_share` and
/// `reference_focus` are the agreed keys; the rest are extras.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct SubjectJson {
    /// Outer rings and holes, even-odd, each `[x, y]` normalised 0..1 to the
    /// active area, at most 256 points a ring.
    pub rings: Vec<Vec<[f32; 2]>>,
    /// Sensor pixels per raster cell.
    pub cell_px: f32,
    pub provenance: ProvenanceJson,
    /// `null` when nothing was found.
    pub depth: Option<DepthJson>,
    pub area_share: f32,
    /// Focus position of the plane nearest the middle of the planes used:
    /// the rings are in its geometry. `null` when not recorded.
    pub reference_focus: Option<f64>,
    pub reference_plane: u64,
    /// Magnification change per focus unit, ppm; `null` when not registered.
    pub ppm_per_unit: Option<f64>,
    pub active_px: [u32; 2],
    /// The raster grid the rings fill: columns, rows.
    pub grid: [usize; 2],
    pub summary: String,
    /// Suggested bounds for the same subject (plan S4); absent when there is
    /// no depth or the planes have no recorded focus.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub bounds: Option<BoundsJson>,
    /// Per-tile focus over the planes used (spec C2).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub maps: Option<crate::depth_contrast::Maps>,
    /// The in-focus range from contrast (spec 5.2), also when the outline
    /// found nothing and `depth` is `null` (the whole frame is then the
    /// subject).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub in_focus: Option<crate::depth_contrast::InFocus>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ProvenanceJson {
    /// `"auto"`.
    pub kind: String,
    /// `"raw"` or `"live_view"`.
    pub source: String,
    pub sensitivity: f32,
    pub grow: f32,
    pub buffer_px: f32,
    /// Plane ordinals the evidence came from.
    pub planes: Vec<u64>,
    /// `"relative"` or `"absolute"`.
    pub threshold: String,
    /// The injected noise model's provenance (`"profile"`, `"fallback"`,
    /// ...); absent for live view.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub noise_model: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct DepthJson {
    pub first_plane: u64,
    pub last_plane: u64,
    pub first_focus: Option<f64>,
    pub last_focus: Option<f64>,
    /// The planes holding the central 99 % of the in-focus subject cells
    /// (the evidence's three-plane mean can put the extremes one survey
    /// plane wide).
    pub core_first_plane: u64,
    pub core_last_plane: u64,
    /// The in-focus range from contrast (capture calibration spec 5.2):
    /// the first and last focus where the subject is in focus, and whether
    /// it still is at the first or last plane used. The fields above are the
    /// earlier rule, kept for comparison; the bounds come from these.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub in_focus_first: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub in_focus_last: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reaches_first: Option<bool>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reaches_last: Option<bool>,
    /// Subject tiles in focus per plane used: `[focus, tiles]`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub per_position: Option<Vec<[f64; 2]>>,
    /// The in-focus range widened by the larger of half the sharp width and
    /// half the planes' spacing there, in increasing focus; absent on a side
    /// the subject reaches.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub suggested_start: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub suggested_end: Option<f64>,
}

impl SubjectJson {
    pub fn new(e: &Evidence, sel: &Selection, noise: Option<Provenance>) -> Self {
        let reference = e.planes.get(e.reference);
        Self {
            rings: sel.rings.clone(),
            cell_px: e.layout.cell_px,
            provenance: ProvenanceJson {
                kind: "auto".into(),
                source: match e.layout.source {
                    Source::Raw => "raw",
                    Source::LiveView => "live_view",
                }
                .into(),
                sensitivity: sel.params.sensitivity,
                grow: sel.params.grow,
                buffer_px: sel.params.buffer_px,
                planes: e.planes.iter().map(|p| p.ordinal).collect(),
                threshold: match sel.threshold {
                    ThresholdKind::Relative => "relative",
                    ThresholdKind::Absolute => "absolute",
                }
                .into(),
                noise_model: noise.map(|p| format!("{p:?}").to_lowercase()),
            },
            depth: sel.depth.as_ref().map(|d| DepthJson {
                first_plane: e.planes[d.first].ordinal,
                last_plane: e.planes[d.last].ordinal,
                first_focus: e.planes[d.first].position,
                last_focus: e.planes[d.last].position,
                core_first_plane: e.planes[d.core_first].ordinal,
                core_last_plane: e.planes[d.core_last].ordinal,
                in_focus_first: None,
                in_focus_last: None,
                reaches_first: None,
                reaches_last: None,
                per_position: None,
                suggested_start: None,
                suggested_end: None,
            }),
            area_share: sel.area_share,
            reference_focus: reference.and_then(|r| r.position),
            reference_plane: reference.map_or(0, |r| r.ordinal),
            ppm_per_unit: e.registration.map(|r| r.ppm_per_unit),
            active_px: e.layout.active_px,
            grid: [e.cols, e.rows],
            summary: sel.summary.clone(),
            bounds: None,
            maps: None,
            in_focus: None,
        }
    }
}

/// An 8-bit grey PNG, uncompressed (stored deflate blocks): a debug raster
/// needs no encoder dependency.
pub fn write_grey_png(path: &Path, width: usize, height: usize, pixels: &[u8]) -> Result<()> {
    ensure!(pixels.len() == width * height, "raster size");
    let crc_table: Vec<u32> = (0..256u32)
        .map(|n| {
            (0..8).fold(n, |c, _| {
                if c & 1 != 0 {
                    0xedb8_8320 ^ (c >> 1)
                } else {
                    c >> 1
                }
            })
        })
        .collect();
    let crc = |bytes: &[u8]| -> u32 {
        !bytes.iter().fold(!0u32, |c, &b| {
            crc_table[((c ^ u32::from(b)) & 0xff) as usize] ^ (c >> 8)
        })
    };
    let mut raw = Vec::with_capacity((width + 1) * height);
    for row in pixels.chunks(width.max(1)) {
        raw.push(0u8);
        raw.extend_from_slice(row);
    }
    let mut z = vec![0x78u8, 0x01];
    let blocks: Vec<&[u8]> = raw.chunks(65_535).collect();
    for (k, b) in blocks.iter().enumerate() {
        z.push(u8::from(k + 1 == blocks.len()));
        let len = b.len() as u16;
        z.extend_from_slice(&len.to_le_bytes());
        z.extend_from_slice(&(!len).to_le_bytes());
        z.extend_from_slice(b);
    }
    let (mut a, mut b) = (1u32, 0u32);
    for &v in &raw {
        a = (a + u32::from(v)) % 65_521;
        b = (b + a) % 65_521;
    }
    z.extend_from_slice(&((b << 16) | a).to_be_bytes());
    let mut out = vec![0x89u8, b'P', b'N', b'G', 0x0d, 0x0a, 0x1a, 0x0a];
    let mut chunk = |kind: &[u8; 4], data: &[u8]| {
        out.extend_from_slice(&(data.len() as u32).to_be_bytes());
        let mut body = kind.to_vec();
        body.extend_from_slice(data);
        out.extend_from_slice(&body);
        out.extend_from_slice(&crc(&body).to_be_bytes());
    };
    let mut ihdr = Vec::new();
    ihdr.extend_from_slice(&(width as u32).to_be_bytes());
    ihdr.extend_from_slice(&(height as u32).to_be_bytes());
    ihdr.extend_from_slice(&[8, 0, 0, 0, 0]);
    chunk(b"IHDR", &ihdr);
    chunk(b"IDAT", &z);
    chunk(b"IEND", &[]);
    std::fs::write(path, out).with_context(|| format!("write {}", path.display()))
}

pub fn run(args: &SubjectArgs) -> Result<()> {
    for out in [&args.out, &args.mask_png, &args.dump_evidence]
        .into_iter()
        .flatten()
    {
        refuse_inside(&args.dir, out)?;
    }
    let all: Vec<(u64, (Option<f64>, PathBuf))> = run_planes(&args.dir)?
        .into_iter()
        .map(|(o, pos, path)| (o, (pos, path)))
        .collect();
    ensure!(
        !all.is_empty(),
        "{} has no recorded planes",
        args.dir.display()
    );
    let chosen = choose(&all, args.planes.as_deref(), args.every, args.count)?;
    ensure!(!chosen.is_empty(), "no planes chosen");
    let registration = if args.no_register {
        Registration::Off
    } else {
        Registration::Fit
    };
    let t = Instant::now();
    let (e, provenance, decode_secs, contrast) = run_evidence(&args.dir, &chosen, registration)?;
    let evidence_secs = t.elapsed().as_secs_f64();
    let t = Instant::now();
    let q = quiet(&e);
    let params = Params {
        sensitivity: args.sensitivity,
        grow: args.grow,
        buffer_px: args.buffer,
    };
    let sel = select(&e, &q, &params);
    let select_secs = t.elapsed().as_secs_f64();

    let mut report = String::new();
    let mut line = |s: String| {
        report.push_str(&s);
        report.push('\n');
    };
    line(format!("run             : {}", args.dir.display()));
    line(format!(
        "planes          : {} of {} recorded ({})",
        chosen.len(),
        all.len(),
        chosen
            .iter()
            .map(|c| c.0.to_string())
            .collect::<Vec<_>>()
            .join(",")
    ));
    line(format!(
        "grid            : {} x {} cells of {} px over {} x {} active px",
        e.cols, e.rows, e.layout.cell_px, e.layout.active_px[0], e.layout.active_px[1]
    ));
    line(format!("noise model     : {provenance:?}"));
    if provenance != Provenance::Profile {
        line("                  WARNING: no camera profile; the noise floor is a guess and the absolute fallback threshold means little".into());
    }
    match e.registration {
        Some(f) => line(format!(
            "registration    : {:.1} ppm per focus unit{}",
            f.ppm_per_unit,
            match (f.scale, f.correlation) {
                (Some(s), Some(c)) => format!(" (scale {s:.4}, correlation {c:.4})"),
                _ => String::new(),
            }
        )),
        None => line("registration    : none".into()),
    }
    line(format!(
        "quiet cells     : mode {:.2} x the injected noise floor, lower spread {:.3} (log); backdrop {:.1} % of the frame",
        q.mode.exp(),
        q.spread,
        100.0 * q.backdrop_share
    ));
    let s = &sel.stats;
    line(format!(
        "threshold       : {:?}, {:.2} x the noise floor; {} in-focus cells, {} seed cells, {} specks; {} part(s) kept, {} dropped",
        s.threshold, s.cut, s.in_focus_cells, s.seed_cells, s.specks, s.parts, s.dropped_parts
    ));
    let points: Vec<String> = sel.rings.iter().map(|r| r.len().to_string()).collect();
    line(format!(
        "outline         : {} ring(s), points {}",
        sel.rings.len(),
        points.join(",")
    ));
    let mut json = SubjectJson::new(&e, &sel, Some(provenance));
    let (width, from) = match args.width {
        Some(w) => (w, "given"),
        None => std::fs::read_to_string(args.dir.join("focus-step.json"))
            .ok()
            .and_then(|t| serde_json::from_str::<serde_json::Value>(&t).ok())
            .and_then(|v| v["width"].as_f64())
            .map_or((0.0, "none"), |w| (w, "focus-step")),
    };
    // The in-focus range from contrast over the planes used (spec 5.2).
    let known: Vec<(f64, Tiles)> = chosen
        .iter()
        .zip(contrast)
        .filter_map(|((_, (pos, _)), t)| Some(((*pos)?, t)))
        .collect();
    if let Some((_, t0)) = known.first() {
        let subject = crate::depth_contrast::subject_tiles(
            (!sel.rings.is_empty()).then_some(sel.rings.as_slice()),
            t0,
            [
                e.layout.active_px[0] as usize,
                e.layout.active_px[1] as usize,
            ],
        );
        let positions: Vec<f64> = known.iter().map(|k| k.0).collect();
        let tiles: Vec<Tiles> = known.into_iter().map(|k| k.1).collect();
        if let Some((r, maps)) = crate::depth_contrast::in_focus(
            &positions,
            &tiles,
            &subject,
            (width > 0.0).then_some(width),
        ) {
            line(format!(
                "in focus        : {} (contrast over {} planes, {} subject tiles)",
                crate::depth_contrast::describe(&r),
                r.per_position.len(),
                r.subject_tiles
            ));
            if let Some(d) = json.depth.as_mut() {
                d.in_focus_first = r.in_focus_first;
                d.in_focus_last = r.in_focus_last;
                d.reaches_first = Some(r.reaches_first);
                d.reaches_last = Some(r.reaches_last);
                d.per_position = Some(r.per_position.clone());
                d.suggested_start = r.suggested_start;
                d.suggested_end = r.suggested_end;
            }
            json.maps = Some(maps);
            json.in_focus = Some(r);
        }
    }
    if let Some(d) = &json.depth {
        line(format!(
            "depth           : planes {} to {} (focus {:?} to {:?})",
            d.first_plane, d.last_plane, d.first_focus, d.last_focus
        ));
        let run: Vec<(u64, Option<f64>)> = all.iter().map(|(o, (pos, _))| (*o, *pos)).collect();
        json.bounds = bounds(d, &run, width, from);
        if let Some(b) = &json.bounds {
            line(format!(
                "bounds          : start {:.0}, end {:.0} (sharp width {:.0}, {}): {} of {} planes, {} saved, {:.0} % of the range{}{}",
                b.start,
                b.end,
                b.sharp_width,
                b.width_from,
                b.planes,
                b.run_planes,
                b.planes_saved,
                100.0 * b.fraction,
                if b.reaches_run_start {
                    "; still in focus at the first plane: the subject may go on"
                } else {
                    ""
                },
                if b.reaches_run_end {
                    "; still in focus at the last plane: the subject may go on"
                } else {
                    ""
                }
            ));
            if let Some(c) = &b.core {
                line(format!(
                    "bounds (core)   : start {:.0}, end {:.0}: {} planes, {} saved, {:.0} % of the range",
                    c.start,
                    c.end,
                    c.planes,
                    c.planes_saved,
                    100.0 * c.fraction
                ));
            }
        }
    }
    line(format!(
        "area            : {:.2} % of the frame",
        100.0 * sel.area_share
    ));
    line(format!(
        "time            : decode + cells {decode_secs:.2} s, evidence {evidence_secs:.2} s, selection {select_secs:.3} s"
    ));
    line(format!("summary         : {}", sel.summary));

    let text = serde_json::to_string_pretty(&json)?;
    if args.json {
        eprint!("{report}");
        println!("{text}");
    } else {
        print!("{report}");
    }
    if let Some(path) = &args.out {
        std::fs::write(path, &text).with_context(|| format!("write {}", path.display()))?;
    }
    if let Some(path) = &args.mask_png {
        let px: Vec<u8> = sel.mask.iter().map(|&m| if m { 255 } else { 0 }).collect();
        write_grey_png(path, e.cols, e.rows, &px)?;
    }
    if let Some(path) = &args.dump_evidence {
        let mut bytes = Vec::with_capacity(e.focus.len() * 10);
        e.focus
            .iter()
            .chain(&e.level)
            .for_each(|v| bytes.extend_from_slice(&v.to_le_bytes()));
        e.depth
            .iter()
            .for_each(|v| bytes.extend_from_slice(&v.to_le_bytes()));
        std::fs::write(path, bytes).with_context(|| format!("write {}", path.display()))?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn plane_choice() {
        let all: Vec<(u64, ())> = (0..199).map(|o| (o, ())).collect();
        let spread = choose(&all, None, None, 13).unwrap();
        assert_eq!(spread.len(), 13);
        assert_eq!((spread[0].0, spread[12].0), (0, 198));
        let every = choose(&all, None, Some(16), 13).unwrap();
        assert_eq!(every.len(), 13);
        assert_eq!(every[12].0, 192);
        let some = choose(&all, Some(&[5, 3, 5]), None, 13).unwrap();
        assert_eq!(some.iter().map(|p| p.0).collect::<Vec<_>>(), vec![3, 5]);
        assert!(choose(&all, Some(&[500]), None, 13).is_err());
        assert_eq!(choose(&all[..5], None, None, 13).unwrap().len(), 5);
    }

    /// Bounds: half a sharp width each side in the run's direction, rounded
    /// outward, with the planes kept and saved; either direction of focus.
    #[test]
    fn bounds_from_depth() {
        let depth =
            |first: u64, last: u64, core: (u64, u64), focus: &dyn Fn(u64) -> f64| DepthJson {
                first_plane: first,
                last_plane: last,
                first_focus: Some(focus(first)),
                last_focus: Some(focus(last)),
                core_first_plane: core.0,
                core_last_plane: core.1,
                in_focus_first: None,
                in_focus_last: None,
                reaches_first: None,
                reaches_last: None,
                per_position: None,
                suggested_start: None,
                suggested_end: None,
            };
        // 100 planes from 1000, step 10, rising.
        let up = |o: u64| 1000.0 + 10.0 * (o as f64 - 1.0);
        let run: Vec<(u64, Option<f64>)> = (1..=100).map(|o| (o, Some(up(o)))).collect();
        let b = bounds(&depth(21, 70, (25, 66), &up), &run, 25.0, "given").unwrap();
        // Focus 1200 - 12.5 and 1690 + 12.5, outward: 1187 and 1703.
        assert_eq!((b.start, b.end), (1187.0, 1703.0));
        assert_eq!((b.planes, b.planes_saved, b.run_planes), (52, 48, 100));
        assert!((b.fraction - 516.0 / 990.0).abs() < 1e-12);
        assert!(!b.reaches_run_start && !b.reaches_run_end);
        let core = b.core.unwrap();
        assert_eq!((core.start, core.end, core.planes), (1227.0, 1663.0, 44));
        // Falling focus (as the close tile: 62800 down by 13).
        let down = |o: u64| 62800.0 - 13.0 * (o as f64 - 1.0);
        let run: Vec<(u64, Option<f64>)> = (1..=153).map(|o| (o, Some(down(o)))).collect();
        let b = bounds(&depth(1, 120, (5, 110), &down), &run, 0.0, "none").unwrap();
        assert_eq!((b.start, b.end), (62800.0, down(120)));
        assert_eq!((b.planes, b.planes_saved), (120, 33));
        assert!(b.reaches_run_start && !b.reaches_run_end);
        let b = bounds(&depth(1, 120, (5, 110), &down), &run, 13.0, "given").unwrap();
        assert_eq!((b.start, b.end), (62807.0, down(120) - 7.0));
        // With the in-focus range from contrast, its suggestion is the
        // bounds, and a side the subject reaches keeps the run's end.
        let mut d = depth(21, 70, (25, 66), &up);
        d.in_focus_first = Some(1300.0);
        d.in_focus_last = Some(1600.0);
        d.reaches_first = Some(false);
        d.reaches_last = Some(true);
        d.suggested_start = Some(1250.0);
        let run: Vec<(u64, Option<f64>)> = (1..=100).map(|o| (o, Some(up(o)))).collect();
        let b = bounds(&d, &run, 25.0, "given").unwrap();
        assert_eq!((b.start, b.end), (1250.0, up(100)));
        assert!(!b.reaches_run_start && b.reaches_run_end);
        // No recorded focus: no bounds.
        let blind: Vec<(u64, Option<f64>)> = (1..=10).map(|o| (o, None)).collect();
        assert!(bounds(&depth(2, 8, (2, 8), &up), &blind, 10.0, "given").is_none());
    }

    /// The JSON carries the agreed top-level keys, and parses back.
    #[test]
    fn json_contract() {
        let (cols, rows) = (120usize, 80usize);
        let frames: Vec<FrameCells> = (0..9)
            .map(|k| {
                let peak = (-((k as f32 - 4.0).powi(2)) / 2.0).exp();
                let energy = (0..cols * rows)
                    .map(|i| {
                        let (x, y) = ((i % cols) as f32 - 60.0, (i / cols) as f32 - 40.0);
                        let wobble = 1.0 + 0.05 * ((i * 7919 % 13) as f32 / 13.0 - 0.5);
                        if x.hypot(y) < 20.0 {
                            wobble + 30.0 * peak
                        } else {
                            wobble
                        }
                    })
                    .collect();
                FrameCells {
                    cols,
                    rows,
                    energy,
                    level: vec![0.01; cols * rows],
                }
            })
            .collect();
        let planes = (0..9)
            .map(|k| PlaneRef {
                ordinal: 1 + k,
                position: Some(24_000.0 + 7.0 * k as f64),
            })
            .collect();
        let e = assemble(frames, planes, raw_layout(960, 640), Registration::Off);
        let sel = select(&e, &quiet(&e), &Params::default());
        let json = SubjectJson::new(&e, &sel, Some(Provenance::Profile));
        let v: serde_json::Value = serde_json::to_value(&json).unwrap();
        for key in [
            "rings",
            "cell_px",
            "provenance",
            "depth",
            "area_share",
            "reference_focus",
        ] {
            assert!(v.get(key).is_some(), "{key}");
        }
        assert_eq!(v["provenance"]["kind"], "auto");
        assert_eq!(v["provenance"]["threshold"], "relative");
        assert_eq!(v["provenance"]["noise_model"], "profile");
        assert_eq!(v["reference_focus"], 24_028.0);
        assert_eq!(v["depth"]["first_focus"], 24_028.0);
        let ring = v["rings"][0].as_array().unwrap();
        assert!(ring.len() >= 3 && ring.len() <= 256);
        let back: SubjectJson = serde_json::from_value(v).unwrap();
        assert_eq!(back, json);
    }
}
