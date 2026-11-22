use crate::model::Plan;
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs::{File, OpenOptions},
    io::Write,
    path::{Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};

pub fn now_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis()
}
pub struct Journal {
    pub directory: PathBuf,
    stream: File,
    sequence: u64,
    host: bool,
}
fn new_file(path: &Path) -> Result<File> {
    OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(path)
        .with_context(|| format!("Create {}", path.display()))
}
fn write_new(path: &Path, value: &Value) -> Result<()> {
    let mut f = new_file(path)?;
    serde_json::to_writer_pretty(&mut f, value)?;
    f.write_all(b"\n")?;
    f.sync_all()?;
    Ok(())
}
impl Journal {
    pub fn create(
        root: &Path,
        plan: &Plan,
        positions: &[u16],
        kind: &str,
        identity: Value,
        status: Value,
    ) -> Result<Self> {
        plan.validate()?;
        ensure!(!positions.is_empty(), "No focus positions to capture");
        let host = status["capture_destination"] == "host-pc";
        // Top-level fields summarise the run as configured at its start. Per-file
        // bindings in events.jsonl and the in-file camera tags remain authoritative.
        let shots = status["pixel_shift_shots"].as_u64().unwrap_or(1);
        let raw_format = if !host {
            "camera-setting"
        } else if identity["raw_format"] == "uncompressed" {
            "sony-uncompressed"
        } else {
            "sony-lossless-compressed-raw-l"
        };
        std::fs::create_dir_all(root).context("Create capture-journal folder")?;
        let directory = root.join(format!("stack-{}-{}", now_ms(), std::process::id()));
        std::fs::create_dir(&directory)
            .context("Create a fresh stack journal (existing runs are never overwritten)")?;
        write_new(
            &directory.join("manifest.json"),
            &json!({
            "schema":"strehl-capture-v2", "build":env!("CARGO_PKG_VERSION"),
            "executable_sha256":Sha256::digest(std::fs::read(std::env::current_exe()?)?).iter().map(|b|format!("{b:02x}")).collect::<String>(), "started_unix_ms":now_ms(),
                "camera":identity,"initial_status":status,"plan":plan,"capture_kind":kind,"focus_positions":positions,
                "planned_planes":positions.len(),"planned_raws":positions.len() as u64*shots,
                "focus_units":"normalized-uint16-not-metric", "raw_destination":if host {"host-pc"} else {"camera-sd-card"}, "raws_downloaded":host,
                "raw_format":raw_format,
                "pixel_shift_shots":shots,"file_binding":if host {"ordinal-filename-bytes-sha256"} else {"unbound-camera-event-ordinals"}, "preview_saved":false,
                "authority":"Top-level fields summarise the run at its start; per-file bindings in events.jsonl (plane, group_id, member_index, sha256) and in-file camera tags are authoritative.",
                "matching_note":if host {"Each capture_buffered or capture_complete event binds its focus plane to one ordinal filename, byte length and SHA-256. Buffered files are not yet durable; transfer-receipts.jsonl confirms PC delivery. No manual exposures during a run."} else {"Associate ordered RAWs from this run using camera timestamps and count; no filename or checksum binding is claimed. Do not insert manual exposures during a run."}
            }),
        )?;
        let stream = new_file(&directory.join("events.jsonl"))?;
        let mut journal = Self {
            directory,
            stream,
            sequence: 0,
            host,
        };
        journal.record("created", json!({}))?;
        Ok(journal)
    }
    /// An ended run's journal opened again to append to (h-retake: retakes
    /// after the capture). Its events continue the numbering; nothing
    /// already written is changed.
    pub fn reopen(directory: &Path) -> Result<Self> {
        let path = directory.join("events.jsonl");
        let text =
            std::fs::read_to_string(&path).with_context(|| format!("Read {}", path.display()))?;
        let sequence = text
            .lines()
            .rev()
            .find_map(|line| serde_json::from_str::<Value>(line).ok()?["sequence"].as_u64())
            .unwrap_or(0);
        let manifest: Value =
            serde_json::from_slice(&std::fs::read(directory.join("manifest.json"))?)?;
        let stream = OpenOptions::new()
            .append(true)
            .open(&path)
            .with_context(|| format!("Open {} to append", path.display()))?;
        Ok(Self {
            directory: directory.to_owned(),
            stream,
            sequence,
            host: manifest["raw_destination"] == "host-pc",
        })
    }
    pub fn record(&mut self, event: &str, data: Value) -> Result<()> {
        self.sequence += 1;
        serde_json::to_writer(
            &mut self.stream,
            &json!({"sequence":self.sequence,"unix_ms":now_ms(),"event":event,"data":data}),
        )?;
        self.stream.write_all(b"\n")?;
        self.stream
            .sync_all()
            .context("Persist capture journal before continuing")?;
        Ok(())
    }
    pub fn finish(&mut self, outcome: &str, completed: usize, message: &str) -> Result<()> {
        self.record(
            "finished",
            json!({"outcome":outcome,"completed":completed,"message":message}),
        )?;
        write_new(
            &self.directory.join("result.json"),
            &json!({"schema":"strehl-capture-result-v1","outcome":outcome,"completed_camera_events":completed,"finished_unix_ms":now_ms(),"message":message,"raw_file_verification":if self.host && matches!(outcome,"complete"|"stopped") {"pc-durable-sha256"} else if self.host {"partial-see-transfer-receipts"} else {"not-performed"}}),
        )
    }
}

/// Explicit card-reader export. No camera upload, RAW modification or overwrite.
pub fn export(source: &Path, card_folder: &Path) -> Result<PathBuf> {
    ensure!(
        source.join("manifest.json").is_file(),
        "No capture manifest to export"
    );
    ensure!(
        source.join("result.json").is_file(),
        "Finish or stop the run before exporting metadata"
    );
    ensure!(
        card_folder.is_dir(),
        "Choose a mounted card or an existing folder beside its RAWs"
    );
    let root = card_folder.join("STREHL");
    std::fs::create_dir_all(&root)?;
    let destination = root.join(
        source
            .file_name()
            .context("Invalid capture-journal folder")?,
    );
    std::fs::create_dir(&destination).context(
        "Metadata already exists here; choose another destination rather than overwriting",
    )?;
    for name in ["manifest.json", "events.jsonl", "result.json"] {
        let path = source.join(name);
        ensure!(
            std::fs::metadata(&path)?.len() <= 256 * 1024 * 1024,
            "Journal unexpectedly exceeds 256 MiB"
        );
        let mut input = File::open(path)?;
        let mut output = new_file(&destination.join(name))?;
        std::io::copy(&mut input, &mut output)?;
        output.sync_all()?;
    }
    Ok(destination)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn durable_intent_and_export_never_touch_raw_or_overwrite() {
        let temp = tempfile::tempdir().unwrap();
        let card = temp.path().join("card");
        std::fs::create_dir(&card).unwrap();
        let raw = card.join("DSC00001.ARW");
        std::fs::write(&raw, b"untouched").unwrap();
        let plan = Plan {
            start: 500,
            end: 502,
            ..Plan::default()
        };
        let mut journal = Journal::create(
            &temp.path().join("logs"),
            &plan,
            &plan.positions().unwrap(),
            "plan",
            json!({}),
            json!({}),
        )
        .unwrap();
        journal
            .record("capture_intent", json!({"ordinal":0}))
            .unwrap();
        assert!(export(&journal.directory, &card).is_err());
        journal.finish("uncertain", 0, "No retry").unwrap();
        let dest = export(&journal.directory, &card).unwrap();
        let manifest: Value = serde_json::from_slice(
            &std::fs::read(journal.directory.join("manifest.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(manifest["planned_planes"], 3);
        assert_eq!(manifest["pixel_shift_shots"], 1);
        assert_eq!(manifest["raw_format"], "camera-setting");
        assert_eq!(std::fs::read(&raw).unwrap(), b"untouched");
        assert!(export(&journal.directory, &card).is_err());
        assert_eq!(
            std::fs::read(dest.join("events.jsonl")).unwrap(),
            std::fs::read(journal.directory.join("events.jsonl")).unwrap()
        );
    }
}

#[cfg(test)]
mod summary_tests {
    use super::*;
    #[test]
    fn top_level_summary_reports_the_runs_actual_mode_and_format() {
        let temp = tempfile::tempdir().unwrap();
        let plan = Plan {
            start: 500,
            end: 500,
            ..Plan::default()
        };
        let journal = Journal::create(
            temp.path(),
            &plan,
            &[500, 500, 500],
            "positions",
            json!({"raw_format":"uncompressed"}),
            json!({"capture_destination":"host-pc","pixel_shift_shots":4}),
        )
        .unwrap();
        let manifest: Value = serde_json::from_slice(
            &std::fs::read(journal.directory.join("manifest.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(manifest["schema"], "strehl-capture-v2");
        assert_eq!(manifest["pixel_shift_shots"], 4);
        assert_eq!(manifest["raw_format"], "sony-uncompressed");
        assert_eq!(manifest["planned_planes"], 3);
        assert_eq!(manifest["planned_raws"], 12);
        assert_eq!(manifest["capture_kind"], "positions");
        assert_eq!(manifest["focus_positions"], json!([500, 500, 500]));
    }
}
