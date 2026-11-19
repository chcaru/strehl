//! Alignment edges measured once per pair of files (performance plan Q12).
//!
//! # Why
//!
//! A render without a cached warp map decodes every focal plane's alignment
//! plane and measures the edge ladder: 196 planes and 1,412 pairs on the
//! scarab stack, about 5.6 s of a first render. But an edge depends only on
//! its two files and the estimator's configuration: [`align_pair`] reads the
//! two planes, their pyramids and a tile grid fixed by the plane's size, and
//! uses no shared or thread-dependent state. `strehl follow` already decodes
//! every plane's first member while the capture runs, so it can measure each
//! new plane's pairs against the planes before it then, and the closing render
//! reads them here instead of decoding and measuring again.
//!
//! # What makes a record valid
//!
//! A record is keyed by both files' archive SHA-256 (the hash a full decode
//! verifies), in stack order, and by the identity of the estimator: this
//! module's [`EDGE_VERSION`] and the `Debug` of the configuration, which
//! prints every float round-trip exactly. Every float is stored as its bits,
//! so a journalled edge is the measured edge bit for bit. A refused pair is
//! recorded too: the render must not measure it again either. Files that are
//! not archives have no declared hash and are never journalled.
//!
//! `STREHL_EDGE_JOURNAL=off` disables reading and writing.
//!
//! [`align_pair`]: strehl_core::align::align_pair

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::sync::atomic::{AtomicUsize, Ordering};

use anyhow::{Context, Result};
use serde_json::{Value, json};
use strehl_core::align::{AlignConfig, AlignEdge, Cx, Similarity};
use strehl_core::plane::PlaneGeometry;

pub(crate) const EDGE_JOURNAL_ENV: &str = "STREHL_EDGE_JOURNAL";

/// Bump when anything that changes a measured edge changes outside the
/// configuration's `Debug`: the alignment plane's construction, the tile
/// grid, the pair estimator.
const EDGE_VERSION: u32 = 1;

fn enabled() -> Result<bool> {
    match std::env::var(EDGE_JOURNAL_ENV) {
        Err(std::env::VarError::NotPresent) => Ok(true),
        Err(e) => Err(e).context(EDGE_JOURNAL_ENV),
        Ok(v) => match v.trim() {
            "" | "on" | "1" => Ok(true),
            "off" | "0" => Ok(false),
            other => anyhow::bail!("{EDGE_JOURNAL_ENV}={other:?} is not on or off"),
        },
    }
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

/// The estimator's identity: version and configuration.
fn config_identity(cfg: &AlignConfig) -> String {
    use sha2::Digest;
    hex(&sha2::Sha256::digest(
        format!("v{EDGE_VERSION} {cfg:?}").as_bytes(),
    ))
}

/// One pair's measurement, without the stack indices the render gives it.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct Measured {
    pub geom: PlaneGeometry,
    /// `None`: the pair was refused.
    pub fit: Option<Fit>,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct Fit {
    pub t: Similarity,
    pub rms: f64,
    pub used: usize,
    pub lever: f64,
}

impl Fit {
    pub(crate) fn of(e: &AlignEdge) -> Self {
        Self {
            t: e.t,
            rms: e.rms,
            used: e.used,
            lever: e.lever,
        }
    }

    pub(crate) fn edge(&self, i: usize, j: usize) -> AlignEdge {
        AlignEdge {
            i,
            j,
            t: self.t,
            rms: self.rms,
            used: self.used,
            lever: self.lever,
        }
    }
}

fn bits(v: f64) -> String {
    format!("{:016x}", v.to_bits())
}

fn unbits(v: &Value) -> Option<f64> {
    u64::from_str_radix(v.as_str()?, 16)
        .ok()
        .map(f64::from_bits)
}

fn fit_json(f: &Fit) -> Value {
    let t = [f.t.a.re, f.t.a.im, f.t.b.re, f.t.b.im].map(bits);
    json!({
        "t": t,
        "rms": bits(f.rms),
        "used": f.used,
        "lever": bits(f.lever),
    })
}

fn fit_from_json(v: &Value) -> Option<Fit> {
    let t = v["t"].as_array()?;
    (t.len() == 4).then_some(())?;
    Some(Fit {
        t: Similarity {
            a: Cx {
                re: unbits(&t[0])?,
                im: unbits(&t[1])?,
            },
            b: Cx {
                re: unbits(&t[2])?,
                im: unbits(&t[3])?,
            },
        },
        rms: unbits(&v["rms"])?,
        used: v["used"].as_u64()? as usize,
        lever: unbits(&v["lever"])?,
    })
}

type Key = (String, String);

/// The edge journal of one capture folder, for one estimator configuration.
pub(crate) struct EdgeJournal {
    path: PathBuf,
    config: String,
    records: Mutex<HashMap<Key, Measured>>,
    pub(crate) written: AtomicUsize,
    pub(crate) used: AtomicUsize,
}

impl EdgeJournal {
    /// The journal of `dir` (in the cache root, never beside the capture),
    /// with the readable records of this configuration, or `None` under
    /// `STREHL_EDGE_JOURNAL=off`. A torn or foreign line is skipped.
    pub(crate) fn open(dir: &Path, cfg: &AlignConfig) -> Result<Option<Self>> {
        if !enabled()? {
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
            .join("edges")
            .join(format!("{leaf}-{}.jsonl", &hex(&digest)[..16]));
        Ok(Some(Self::load(path, cfg)))
    }

    fn load(path: PathBuf, cfg: &AlignConfig) -> Self {
        let config = config_identity(cfg);
        let mut records = HashMap::new();
        if let Ok(text) = std::fs::read_to_string(&path) {
            for line in text.lines() {
                let Ok(r) = serde_json::from_str::<Value>(line) else {
                    continue;
                };
                if r["cfg"].as_str() != Some(config.as_str()) {
                    continue;
                }
                let (Some(a), Some(b), Some(w), Some(h)) = (
                    r["sha256"][0].as_str(),
                    r["sha256"][1].as_str(),
                    r["geom"][0].as_u64(),
                    r["geom"][1].as_u64(),
                ) else {
                    continue;
                };
                let fit = match &r["fit"] {
                    Value::Null => None,
                    v => match fit_from_json(v) {
                        Some(f) => Some(f),
                        None => continue,
                    },
                };
                let geom = PlaneGeometry {
                    width: w as usize,
                    height: h as usize,
                };
                records.insert((a.to_string(), b.to_string()), Measured { geom, fit });
            }
        }
        Self {
            path,
            config,
            records: Mutex::new(records),
            written: AtomicUsize::new(0),
            used: AtomicUsize::new(0),
        }
    }

    /// Each file's archive SHA-256, `None` for a file that is not an archive.
    pub(crate) fn file_keys(paths: &[PathBuf]) -> Vec<Option<String>> {
        use rayon::prelude::*;
        paths
            .par_iter()
            .map(|p| strehl_raw::archive_sha256(p))
            .collect()
    }

    pub(crate) fn contains(&self, a: &str, b: &str) -> bool {
        self.records
            .lock()
            .unwrap()
            .contains_key(&(a.to_string(), b.to_string()))
    }

    /// The pair `(a, b)`, `a` earlier in the stack, if it was measured.
    pub(crate) fn get(&self, a: &str, b: &str) -> Option<Measured> {
        let m = self
            .records
            .lock()
            .unwrap()
            .get(&(a.to_string(), b.to_string()))
            .copied();
        if m.is_some() {
            self.used.fetch_add(1, Ordering::Relaxed);
        }
        m
    }

    /// Append records (one line each, flushed together). A failure to write
    /// costs only a later render the measurement, so it is reported, not
    /// fatal.
    pub(crate) fn append(&self, entries: &[(String, String, Measured)]) {
        use std::io::Write;
        if entries.is_empty() {
            return;
        }
        let mut text = String::new();
        for (a, b, m) in entries {
            let line = json!({
                "cfg": self.config,
                "sha256": [a, b],
                "geom": [m.geom.width, m.geom.height],
                "fit": m.fit.as_ref().map(fit_json),
            });
            text.push_str(&line.to_string());
            text.push('\n');
        }
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
                f.write_all(text.as_bytes())?;
                f.flush()
            });
        match written {
            Ok(()) => {
                self.written.fetch_add(entries.len(), Ordering::Relaxed);
                for (a, b, m) in entries {
                    records.insert((a.clone(), b.clone()), *m);
                }
            }
            Err(e) => eprintln!(
                "alignment      : could not journal {} edges in {}: {e}",
                entries.len(),
                self.path.display()
            ),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_fit_round_trips_bit_for_bit() {
        let f = Fit {
            t: Similarity {
                a: Cx {
                    re: 1.0 + f64::EPSILON,
                    im: -3.0e-5,
                },
                b: Cx {
                    re: 12.345678901234567,
                    im: -0.1,
                },
            },
            rms: 0.0371,
            used: 61,
            lever: 1234.5,
        };
        let back = fit_from_json(&fit_json(&f)).unwrap();
        assert_eq!(
            [f.t.a.re, f.t.a.im, f.t.b.re, f.t.b.im, f.rms, f.lever].map(f64::to_bits),
            [
                back.t.a.re,
                back.t.a.im,
                back.t.b.re,
                back.t.b.im,
                back.rms,
                back.lever
            ]
            .map(f64::to_bits)
        );
        assert_eq!(f.used, back.used);
    }

    #[test]
    fn records_reload_only_under_their_own_configuration() {
        let root = std::env::temp_dir().join(format!("strehl-edge-journal-{}", std::process::id()));
        let path = root.join("edges").join("stack.jsonl");
        let _ = std::fs::remove_dir_all(&root);
        let cfg = AlignConfig::deep();
        let journal = EdgeJournal::load(path.clone(), &cfg);
        assert!(!journal.contains("a", "b"));
        let geom = PlaneGeometry {
            width: 8,
            height: 4,
        };
        journal.append(&[
            ("a".into(), "b".into(), Measured { geom, fit: None }),
            (
                "b".into(),
                "c".into(),
                Measured {
                    geom,
                    fit: Some(Fit {
                        t: Similarity::IDENTITY,
                        rms: 0.5,
                        used: 3,
                        lever: 2.0,
                    }),
                },
            ),
        ]);
        // A torn final line (a process killed mid-append) is skipped.
        {
            use std::io::Write;
            let mut f = std::fs::OpenOptions::new()
                .append(true)
                .open(&path)
                .unwrap();
            f.write_all(b"{\"cfg\":\"").unwrap();
        }
        let again = EdgeJournal::load(path.clone(), &cfg);
        assert_eq!(again.get("a", "b"), Some(Measured { geom, fit: None }));
        assert_eq!(
            again.get("b", "c").and_then(|m| m.fit).map(|f| f.used),
            Some(3)
        );
        assert_eq!(again.get("b", "a"), None, "a pair is ordered");
        assert_eq!(again.used.load(Ordering::Relaxed), 2);
        let mut other = AlignConfig::deep();
        other.fine_tile += 1;
        let foreign = EdgeJournal::load(path, &other);
        assert!(!foreign.contains("a", "b") && !foreign.contains("b", "c"));
        let _ = std::fs::remove_dir_all(&root);
    }
}
