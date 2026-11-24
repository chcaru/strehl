//! `strehl follow <run>`: check a capture run while it is being captured
//! (plan stage S1, first cut).
//!
//! The engine polls the run's own records and admits a focal plane only when
//! every bound member has a durable receipt with the bound SHA-256. It never
//! reads a file without its receipt and never writes inside the capture
//! folder. Each admitted plane is decoded once (archives verify their whole
//! SHA-256 on decode) and, for a four-shot group, checked exactly as
//! `STREHL_PIXEL_SHIFT=remosaic` will check it in the stack: geometry,
//! structure, the colour-exact green witness, margins and levels. One JSON
//! line per plane goes to a journal under the cache root; a restarted engine
//! replays it and resumes.
//!
//! When the run's `result.json` appears and every recorded plane is checked,
//! the engine prints the planes to retake (failed groups, with the focus
//! position the controller recorded) as a `capture_positions` command, and,
//! with `--out`, runs the ordinary `stack` on the folder. The closing
//! photograph is therefore the offline result by construction (plan decision
//! 6). Not yet built: live alignment pair measurement, the provisional
//! preview, and resource throttling beyond one plane at a time.
use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde_json::{Value, json};
use std::collections::BTreeMap;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

#[derive(clap::Args, Debug)]
pub struct FollowArgs {
    /// Capture run folder (manifest.json, events.jsonl, transfer-receipts.jsonl).
    pub dir: PathBuf,
    /// Poll interval in milliseconds.
    #[arg(long, default_value_t = 1000)]
    pub interval_ms: u64,
    /// Give up if nothing new is admitted for this many seconds (0 = never).
    #[arg(long, default_value_t = 0)]
    pub idle_timeout_s: u64,
    /// At the end, stack the run to this TIFF (four-shot runs use
    /// STREHL_PIXEL_SHIFT=remosaic). Extra `stack` arguments follow `--`.
    #[arg(long)]
    pub out: Option<PathBuf>,
    /// The subject (a manifest with `plan.subject`, or `strehl subject
    /// --out`): a demoted group asks for a retake only when the subject's own
    /// check fails (plan S4). Default: the run manifest's subject, if any.
    #[arg(long)]
    pub subject: Option<PathBuf>,
    /// Arguments passed to the closing `stack` after the folder and --out.
    #[arg(last = true)]
    pub stack_args: Vec<String>,
}

/// The capture host is taking retakes the user asked for after the capture
/// ended (h-retake): its journal has a `followup_started` with no
/// `followup_finished` after it. Such a run is not finished although its
/// `result.json` exists.
pub(crate) fn followup_open(dir: &Path) -> bool {
    let Ok(text) = std::fs::read_to_string(dir.join("events.jsonl")) else {
        return false;
    };
    let mut open = false;
    for line in text.lines().filter(|l| l.contains("\"followup_")) {
        if let Ok(v) = serde_json::from_str::<Value>(line) {
            match v["event"].as_str() {
                Some("followup_started") => open = true,
                Some("followup_finished") => open = false,
                _ => {}
            }
        }
    }
    open
}

fn journal_path(dir: &Path) -> Result<PathBuf> {
    journal_in(&crate::align_cmd::cache_root(), dir)
}

/// The run's plane journal under the cache root `root`: one JSON line per
/// checked plane, which the desktop reads to show progress.
pub(crate) fn journal_in(root: &Path, dir: &Path) -> Result<PathBuf> {
    let canonical = dir
        .canonicalize()
        .with_context(|| format!("resolve {}", dir.display()))?;
    let name = canonical
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("run")
        .to_string();
    let digest = {
        use std::hash::{Hash, Hasher};
        let mut h = std::collections::hash_map::DefaultHasher::new();
        canonical.to_string_lossy().to_lowercase().hash(&mut h);
        h.finish()
    };
    let root = root.join("follow");
    std::fs::create_dir_all(&root)?;
    Ok(root.join(format!("{name}-{digest:016x}.jsonl")))
}

/// `STREHL_FOLLOW_RETAKE_PLANES`: planes whose first checked group is
/// reported as needing a retake whatever its measurements, to exercise error
/// correction on the rig. Diagnostic; never set by the desktop.
fn forced_retakes() -> Result<Vec<u64>> {
    match std::env::var("STREHL_FOLLOW_RETAKE_PLANES") {
        Err(std::env::VarError::NotPresent) => Ok(Vec::new()),
        Err(e) => Err(e).context("STREHL_FOLLOW_RETAKE_PLANES"),
        Ok(v) => v
            .split(',')
            .filter(|p| !p.trim().is_empty())
            .map(|p| {
                p.trim().parse().with_context(|| {
                    format!("STREHL_FOLLOW_RETAKE_PLANES={v:?}: {p:?} is not a plane number")
                })
            })
            .collect(),
    }
}

/// The run's subject and its region, built at the first decoded group.
type SubjectState = (
    crate::subject_use::LoadedSubject,
    Option<strehl_core::subject::SubjectRegion>,
);

fn check_plane(
    g: &crate::pixel_shift_cmd::RecordedGroup,
    noise: &mut Option<strehl_core::noise::NoiseModel>,
    journal: Option<&crate::pixel_shift_cmd::GroupJournal>,
    ladder: Option<&mut crate::align_cmd::LiveLadder>,
    subject: Option<&mut SubjectState>,
) -> Value {
    let started = Instant::now();
    let frames: Result<Vec<strehl_raw::Frame>> = g
        .files
        .par_iter()
        .map(|f| strehl_raw::decode(&f.path).with_context(|| f.name.clone()))
        .collect();
    let frames = match frames {
        Ok(f) => f,
        Err(e) => {
            return json!({"plane":g.plane,"target":g.target,"group_id":g.key(),"verdict":"failed","reason":format!("decode: {e:#}"),"retake":true});
        }
    };
    let first = &frames[0];
    let noise = noise.get_or_insert_with(|| {
        strehl_core::profile::noise_model_for(
            &first.camera,
            first.iso,
            strehl_core::noise::Levels {
                black: first.levels.black,
                white: first.levels.white,
            },
        )
    });
    let mut out = json!({"plane":g.plane,"target":g.target,"group_id":g.key(),"members":frames.len(),
        "names":g.files.iter().map(|f| f.name.clone()).collect::<Vec<_>>()});
    // The render's alignment plane is the group's first member: measure its
    // ladder pairs now, into the edge journal the closing render reads.
    if let Some(ladder) = ladder {
        let t = Instant::now();
        match ladder.push(&g.files[0].path, first) {
            Ok(pairs) => {
                out["align_pairs"] = json!(pairs);
                out["align_seconds"] = json!(t.elapsed().as_secs_f64());
            }
            Err(e) => out["align_error"] = json!(format!("{e:#}")),
        }
    }
    if frames.len() == 4 {
        // The stack's own gate, so a group the stack will assemble is not
        // flagged for a retake. The measurement goes to the group journal
        // (`STREHL_GROUP_JOURNAL`) the render reads, so the closing render
        // measures no group this has.
        let paths: Vec<&Path> = g.files.iter().map(|f| f.path.as_path()).collect();
        let (m, w) = crate::pixel_shift_cmd::measure_journaled(
            journal,
            [paths[0], paths[1], paths[2], paths[3]],
            [&frames[0], &frames[1], &frames[2], &frames[3]],
            noise,
            g.plane as usize,
        );
        let residual = crate::pixel_shift_cmd::ResidualMode::from_env().unwrap_or_default();
        let reason = crate::pixel_shift_cmd::judge(&m, residual);
        let c = &m.check;
        out["offsets"] = json!(c.offsets);
        out["structure"] = json!(c.precision);
        out["gains"] = json!(c.gains);
        match (&w, &m.witness) {
            (Some(w), _) => {
                out["witness_pair_shift_px"] = json!(w.pair_shift);
                out["witness_mean_z2_injected"] = json!(w.mean_z2);
            }
            (None, Some(s)) => out["witness_pair_shift_px"] = json!(s.pair_shift),
            (None, None) => {}
        }
        out["verdict"] = json!(if reason.is_some() { "demote" } else { "pass" });
        out["reason"] = json!(reason);
        // Only a fault of the exposures is worth a retake; a plane with too
        // little structure would be demoted again.
        out["retake"] = json!(crate::pixel_shift_cmd::retake_helps(&m, residual));
        // With a subject, a demoted group is retaken only when the
        // subject's own check fails (plan S4); the verdict stays the
        // stack's, which decides what the render assembles.
        if let Some((s, region)) = subject {
            out["subject"] = json!(s.origin.as_str());
            if let Some(reason) = &reason {
                let r = region.get_or_insert_with(|| {
                    s.region([frames[0].active.width, frames[0].active.height])
                });
                let sub = crate::subject_use::check_subject(
                    [&frames[0], &frames[1], &frames[2], &frames[3]],
                    noise,
                    r,
                    s.scale_at(g.target.map(|t| t as f64)),
                    &m,
                    w.as_ref(),
                    residual,
                );
                let weighted = crate::subject_use::weigh(true, &sub);
                out["retake"] = json!(weighted.retake);
                out["backdrop_only"] = json!(weighted.backdrop_only);
                out["subject_check"] = crate::subject_use::check_json(&sub, &m);
                if weighted.backdrop_only {
                    out["reason"] = json!(format!("{reason}; backdrop only, no retake"));
                }
            }
        }
    } else {
        out["verdict"] = json!("decoded");
        out["retake"] = json!(false);
    }
    out["seconds"] = json!(started.elapsed().as_secs_f64());
    out
}

pub fn run(args: &FollowArgs) -> Result<()> {
    // A run registered a moment ago may not have its journal yet: wait for
    // it (bounded) rather than fail.
    let wait = Duration::from_secs(args.idle_timeout_s.max(30));
    let started = Instant::now();
    while !args.dir.join("events.jsonl").is_file() {
        ensure!(
            started.elapsed() < wait,
            "{} is not a capture run (no events.jsonl after {} s)",
            args.dir.display(),
            wait.as_secs()
        );
        std::thread::sleep(Duration::from_millis(args.interval_ms));
    }
    let journal = journal_path(&args.dir)?;
    // One checker per run: a second would measure every plane again. The
    // lock is the operating system's, so it ends with this process however
    // it ends; the desktop reads it to show another checker's progress.
    let lock_path = crate::follow_lock_path(&journal);
    let _lock = {
        let file = std::fs::OpenOptions::new()
            .create(true)
            .truncate(false)
            .write(true)
            .open(&lock_path)
            .with_context(|| format!("open {}", lock_path.display()))?;
        match file.try_lock() {
            Ok(()) => file,
            Err(std::fs::TryLockError::WouldBlock) => anyhow::bail!(
                "{} is already being followed by another process ({} is locked)",
                args.dir.display(),
                lock_path.display()
            ),
            Err(std::fs::TryLockError::Error(e)) => {
                return Err(e).with_context(|| format!("lock {}", lock_path.display()));
            }
        }
    };
    // Resume: groups already checked in an earlier session, by group (a
    // plane retaken during the capture has more than one). A line from
    // before groups were recorded names only its plane and is checked again.
    let mut done: BTreeMap<String, Value> = BTreeMap::new();
    if let Ok(text) = std::fs::read_to_string(&journal) {
        for line in text.lines() {
            if let Ok(v) = serde_json::from_str::<Value>(line)
                && let Some(key) = v["group_id"].as_str()
            {
                done.insert(key.to_string(), v);
            }
        }
    }
    println!("run             : {}", args.dir.display());
    println!(
        "journal         : {} ({} planes already checked)",
        journal.display(),
        done.len()
    );
    let mut sink = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&journal)?;
    let mut noise = None;
    // The render's group journal: every group measured here is measured
    // once, ever (`STREHL_GROUP_JOURNAL`).
    let groups_journal = crate::pixel_shift_cmd::GroupJournal::open(&args.dir)?;
    // And its alignment pairs (`STREHL_EDGE_JOURNAL`, `STREHL_FOLLOW_ALIGN_MB`).
    let mut ladder = crate::align_cmd::LiveLadder::open(&args.dir)?;
    println!(
        "alignment pairs : {}",
        if ladder.is_some() {
            "measured as planes arrive (edge journal)"
        } else {
            "left to the render"
        }
    );
    // The subject: given, or the run manifest's, read once the manifest
    // exists.
    let mut subject: Option<SubjectState> = None;
    let mut subject_read = false;
    let mut read_subject = |subject: &mut Option<SubjectState>| -> Result<()> {
        if subject_read || (args.subject.is_none() && !args.dir.join("manifest.json").is_file()) {
            return Ok(());
        }
        subject_read = true;
        *subject =
            crate::subject_use::resolve(&args.dir, args.subject.as_deref())?.map(|s| (s, None));
        if let Some((s, _)) = subject {
            println!(
                "subject         : {} ({} ring(s)); a demoted group asks for a retake only when the subject's tiles fail",
                s.origin.as_str(),
                s.rings.len()
            );
        }
        Ok(())
    };
    let forced = forced_retakes()?;
    // A forced plane's first group only, also across a resumed session.
    let mut forced_done: std::collections::HashSet<u64> =
        done.values().filter_map(|v| v["plane"].as_u64()).collect();
    if !forced.is_empty() {
        println!("forced retakes  : planes {forced:?} (STREHL_FOLLOW_RETAKE_PLANES)");
    }
    let mut last_progress = Instant::now();
    let mut planes;
    let mut recorded;
    loop {
        // Every group is checked, a retake included; the plane's last
        // complete group is the one the stack uses.
        read_subject(&mut subject)?;
        let all = crate::pixel_shift_cmd::all_groups(&args.dir)?;
        recorded = all.len();
        planes = crate::pixel_shift_cmd::plane_groups(all.clone());
        let groups = &planes;
        let mut admitted = 0;
        let fresh: Vec<&crate::pixel_shift_cmd::RecordedGroup> = all
            .iter()
            .filter(|g| g.complete && !done.contains_key(&g.key()))
            .collect();
        for g in fresh {
            let mut v = check_plane(
                g,
                &mut noise,
                groups_journal.as_ref(),
                ladder.as_mut(),
                subject.as_mut(),
            );
            if forced.contains(&g.plane) && forced_done.insert(g.plane) {
                v["verdict"] = json!("demote");
                v["reason"] = json!("forced retake (STREHL_FOLLOW_RETAKE_PLANES)");
                v["retake"] = json!(true);
            }
            println!(
                "plane {:>4}      : {} {}{}{}",
                g.plane,
                v["verdict"].as_str().unwrap_or("?"),
                v["reason"].as_str().unwrap_or(""),
                v["seconds"]
                    .as_f64()
                    .map(|s| format!(" ({s:.2} s)"))
                    .unwrap_or_default(),
                match (v["align_pairs"].as_u64(), v["align_error"].as_str()) {
                    (Some(p), _) => format!(", {p} alignment pairs"),
                    (None, Some(e)) => format!(", alignment pairs failed: {e}"),
                    _ => String::new(),
                }
            );
            writeln!(sink, "{v}")?;
            sink.flush()?;
            done.insert(g.key(), v);
            admitted += 1;
            last_progress = Instant::now();
        }
        // Retakes the user asked for after the capture ended go into the
        // same run (h-retake): until they end, it is not finished.
        let finished = args.dir.join("result.json").is_file() && !followup_open(&args.dir);
        let pending = groups
            .iter()
            .filter(|g| !done.contains_key(&g.key()))
            .count();
        if finished && groups.iter().all(|g| g.complete) && pending == 0 {
            break;
        }
        if finished && admitted == 0 && pending > 0 {
            // Finished but some planes can never complete (missing or
            // undurable members): report and stop rather than wait forever.
            for g in groups.iter().filter(|g| !g.complete) {
                let v = json!({"plane":g.plane,"target":g.target,"group_id":g.key(),"verdict":"incomplete","retake":true,
                    "reason":"a bound member has no durable receipt with its hash"});
                println!("plane {:>4}      : incomplete", g.plane);
                writeln!(sink, "{v}")?;
                done.insert(g.key(), v);
            }
            break;
        }
        if args.idle_timeout_s > 0
            && last_progress.elapsed() > Duration::from_secs(args.idle_timeout_s)
        {
            anyhow::bail!(
                "no plane admitted for {} s; the journal keeps progress",
                args.idle_timeout_s
            );
        }
        std::thread::sleep(Duration::from_millis(args.interval_ms));
    }
    // The verdicts of the groups the stack uses, one a plane.
    let used: Vec<&Value> = planes.iter().filter_map(|g| done.get(&g.key())).collect();
    let retakes: Vec<u64> = used
        .iter()
        .filter(|v| v["retake"] == true)
        .filter_map(|v| v["target"].as_u64())
        .collect();
    let passed = used.iter().filter(|v| v["verdict"] == "pass").count();
    let demoted = used
        .iter()
        .filter(|v| v["verdict"] != "pass" && v["verdict"] != "decoded")
        .count();
    println!(
        "checked         : {} planes, {passed} four-shot groups pass, {demoted} need attention",
        used.len()
    );
    if recorded > planes.len() {
        println!(
            "retaken         : {} groups superseded by a retake during the capture",
            recorded - planes.len()
        );
    }
    if let Some(ladder) = &ladder {
        let pairs: u64 = done
            .values()
            .filter_map(|v| v["align_pairs"].as_u64())
            .sum();
        println!(
            "alignment pairs : {pairs} measured this session, window {} planes",
            ladder.capacity()
        );
    }
    if !retakes.is_empty() {
        let mut positions = retakes.clone();
        positions.sort_unstable();
        println!(
            "retake          : {}",
            json!({"op":"capture_positions","positions":positions})
        );
    }
    if let Some(out) = &args.out {
        let four = used.iter().any(|v| v["members"] == 4);
        let exe = std::env::current_exe()?;
        let mut cmd = std::process::Command::new(exe);
        cmd.arg("stack").arg(&args.dir).arg("--out").arg(out);
        cmd.args(&args.stack_args);
        if four {
            cmd.env(crate::pixel_shift_cmd::PIXEL_SHIFT_ENV, "remosaic");
        }
        println!(
            "closing stack   : {}{}",
            if four {
                "STREHL_PIXEL_SHIFT=remosaic "
            } else {
                ""
            },
            out.display()
        );
        let status = cmd.status().context("run the closing stack")?;
        ensure!(status.success(), "closing stack failed: {status}");
    }
    Ok(())
}
