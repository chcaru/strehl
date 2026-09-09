// Feature-gated timing only. No pixels or numerical configuration enter this module.
use anyhow::{Context, Result, ensure};
use std::sync::{
    Mutex, OnceLock,
    atomic::{AtomicU8, Ordering},
};
use std::time::Instant;

const ENV: &str = "STREHL_PYRAMID_PROFILE";
const OUTPUT: &str = "STREHL_PYRAMID_PROFILE_OUTPUT";
const NAMES: [&str; 7] = [
    "decode-validate",
    "defect",
    "gather",
    "probe",
    "extract-luma",
    "variance",
    "pyramid-add",
];
pub(super) const DECODE: usize = 0;
pub(super) const DEFECT: usize = 1;
pub(super) const GATHER: usize = 2;
pub(super) const PROBE: usize = 3;
pub(super) const EXTRACT: usize = 4;
pub(super) const VARIANCE: usize = 5;
pub(super) const ADD: usize = 6;
static MODE: AtomicU8 = AtomicU8::new(0);
static EPOCH: OnceLock<Instant> = OnceLock::new();
#[derive(Clone, Copy)]
struct Count {
    calls: u64,
    nanos: u64,
}
static COUNTS: Mutex<[Count; 7]> = Mutex::new([Count { calls: 0, nanos: 0 }; 7]);
#[cfg(test)]
static TRACE: Mutex<Vec<serde_json::Value>> = Mutex::new(Vec::new());

pub(super) fn begin(require_output: bool) -> Result<()> {
    let mode = match std::env::var(ENV) {
        Err(std::env::VarError::NotPresent) => 0,
        Ok(v) if v == "off" => 0,
        Ok(v) if v == "on" => 1,
        Ok(v) if v == "placebo" => 2,
        _ => anyhow::bail!("{ENV} must be unset, off, on, or placebo"),
    };
    // Default/off must remain reusable by existing prepared-source callers.
    if mode == 0 {
        MODE.store(0, Ordering::Relaxed);
        return Ok(());
    }
    if require_output {
        let path = std::env::var_os(OUTPUT).context("profile output path required")?;
        ensure!(
            !std::path::Path::new(&path).exists(),
            "profile output must be fresh"
        );
    }
    ensure!(
        EPOCH.set(Instant::now()).is_ok(),
        "one profile session per process"
    );
    MODE.store(mode, Ordering::Relaxed);
    Ok(())
}

pub(super) struct Span {
    phase: usize,
    mode: u8,
    start: Option<u64>,
}

pub(super) fn start(phase: usize) -> Span {
    let mode = MODE.load(Ordering::Relaxed);
    let start = (mode == 1).then(|| EPOCH.get().unwrap().elapsed().as_nanos() as u64);
    Span { phase, mode, start }
}

impl Drop for Span {
    fn drop(&mut self) {
        if self.mode == 0 {
            return;
        }
        let end = self
            .start
            .map(|_| EPOCH.get().unwrap().elapsed().as_nanos() as u64);
        let elapsed = self.start.zip(end).map_or(0, |(a, b)| b - a);
        let mut counts = COUNTS.lock().unwrap();
        counts[self.phase].calls += 1;
        counts[self.phase].nanos += elapsed;
        drop(counts);
        #[cfg(test)]
        {
            // Only tiny ignored controls are commissioned for this trace.
            let mut trace = TRACE.lock().unwrap();
            assert!(trace.len() < 64, "tiny profile trace capacity");
            trace.push(serde_json::json!({
                "phase": NAMES[self.phase], "start_ns": self.start, "end_ns": end
            }));
        }
    }
}

fn snapshot() -> serde_json::Value {
    let mode = MODE.load(Ordering::Relaxed);
    let counts = *COUNTS.lock().unwrap();
    let rows: Vec<_> = NAMES
        .iter()
        .zip(counts)
        .map(|(name, c)| {
            serde_json::json!({
                "phase": name, "calls": c.calls,
                "wall_nanoseconds": if mode == 1 { Some(c.nanos) } else { None },
                "wall_seconds": if mode == 1 { Some(c.nanos as f64 * 1e-9) } else { None }
            })
        })
        .collect();
    let mut value = serde_json::json!({
        "schema": "native-pyramid-phase-profile-v1",
        "mode": (["off","on","placebo"][mode as usize]),
        "phases": rows,
        "summed_phase_wall_seconds": if mode == 1 {
            Some(counts.iter().map(|c| c.nanos as f64 * 1e-9).sum::<f64>())
        } else { None },
        "scope": "Wall intervals only, not CPU. Decode/extract phases cover load_frame consumers including optional confidence passes. Variance/add cover BandWorker folds. No startup, plan/worker allocation, reduction/absorb, beta bookkeeping or final publication in leaf sum. Current canonical fold is serial; concurrency would make a leaf sum worker-time rather than elapsed pipeline time."
    });
    #[cfg(test)]
    {
        value["trace"] = serde_json::json!(*TRACE.lock().unwrap());
    }
    #[cfg(not(test))]
    {
        let _ = &mut value;
    }
    value
}

pub(super) fn publish(outer: serde_json::Value) -> Result<()> {
    use std::io::Write;
    if MODE.load(Ordering::Relaxed) == 0 {
        return Ok(());
    }
    let path = std::env::var_os(OUTPUT).context("profile output path required")?;
    let mut value = snapshot();
    value["outer"] = outer;
    let raw = serde_json::to_vec_pretty(&value)?;
    ensure!(raw.len() < 32 * 1024, "profile receipt bound");
    let mut file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?;
    file.write_all(&raw)?;
    file.write_all(b"\n")?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::super::*;
    use std::fs::{self, OpenOptions};
    use std::io::Write;
    use strehl_core::noise::{PlaneNoise, Provenance};
    use strehl_raw::Region;

    struct Source {
        calls: [AtomicUsize; 3],
        delay_calls: AtomicUsize,
        delay: bool,
    }
    impl PyramidFrameSource for Source {
        fn len(&self) -> usize {
            3
        }
        fn decode(&self, frame: usize) -> Result<Frame> {
            ensure!(frame < 3, "fixed tiny source index");
            self.calls[frame].fetch_add(1, Ordering::SeqCst);
            if self.delay {
                self.delay_calls.fetch_add(1, Ordering::SeqCst);
                std::thread::sleep(std::time::Duration::from_millis(25));
            }
            let (width, height, ax, ay, stride, rows) = (128, 96, 2, 4, 135, 103);
            let mut data = vec![65000_u16; stride * rows];
            for y in 0..height {
                for x in 0..width {
                    let structure = 12 * (((x / 8 + y / 8) % 2) as i32);
                    data[(ay + y) * stride + ax + x] =
                        (512 + 20 + structure + [-2, 0, 2][frame]) as u16;
                }
            }
            Ok(Frame {
                data,
                stride,
                buffer_height: rows,
                active: Region {
                    x: ax,
                    y: ay,
                    width,
                    height,
                },
                levels: Levels {
                    black: 512.0,
                    white: 15360.0,
                },
                iso: Some(160.0),
                wb_coeffs: [1.0, 1.0, 1.0, f32::NAN],
                xyz_to_cam_rgbe: [[0.0; 3]; 4],
                color_matrices: Vec::new(),
                camera: "phase timer software control".into(),
                path: PathBuf::from(format!("PHASE-PROFILE-NO-RAW-{frame}.ARW")),
            })
        }
    }

    fn hash(bytes: &[u8]) -> String {
        use sha2::{Digest, Sha256};
        let digest = Sha256::digest(bytes);
        let mut text = String::with_capacity(64);
        let bytes: &[u8] = digest.as_ref();
        for b in bytes {
            use std::fmt::Write as _;
            write!(&mut text, "{b:02x}").unwrap();
        }
        text
    }

    #[test]
    #[ignore = "root releases off/on/placebo/on-with-known-delay once each"]
    fn phase_timer_smoke() -> Result<()> {
        ensure!(
            !cfg!(feature = "native-signed-black"),
            "signed-black feature must be disabled"
        );
        let delay = match std::env::var("STREHL_PYRAMID_PROFILE_DELAY") {
            Err(std::env::VarError::NotPresent) => false,
            Ok(v) if v == "1" => true,
            _ => anyhow::bail!("tiny delay must be unset or1"),
        };
        super::begin(false)?;
        // The off control uses an independent envelope clock; production off is inert.
        super::EPOCH.get_or_init(Instant::now);
        let mode = super::MODE.load(Ordering::Relaxed);
        ensure!(!delay || mode == 1, "delay control requires on");
        let label = if delay {
            "delay"
        } else {
            ["off", "on", "placebo"][mode as usize]
        };
        let out = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../experiments/native-pyramid-profile")
            .canonicalize()?
            .join(format!("smoke-{label}"));
        fs::create_dir(&out)?;
        let source = Source {
            calls: std::array::from_fn(|_| AtomicUsize::new(0)),
            delay_calls: AtomicUsize::new(0),
            delay,
        };
        let levels = Levels {
            black: 512.0,
            white: 15360.0,
        };
        let pn = PlaneNoise {
            gain_dn_per_e: 1.0,
            read_noise_e: 4.0,
            levels,
        };
        let noise = NoiseModel::new([pn; 4], 160.0, Provenance::Fallback);
        let geom = PlaneGeometry {
            width: 64,
            height: 48,
        };
        let domain = PyramidDomain::whole(geom);
        let cfg = MergeConfig::default();
        let sizes = level_sizes(64, 48, cfg.bands);
        let consumer_start_ns = super::EPOCH.get().unwrap().elapsed().as_nanos() as u64;
        let whole = Instant::now();
        let mut worker = BandWorker::new(domain, cfg);
        for i in 0..3 {
            assert!(worker.fold(&source, i, levels, &noise, None, None)?);
        }
        let planes = worker.merge.finish(&mut Workspace::new(&sizes));
        assert!(planes.iter().flatten().all(|v| v.is_finite()));
        let raw: Vec<u8> = planes
            .iter()
            .flatten()
            .flat_map(|v| v.to_le_bytes())
            .collect();
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(out.join("output.f32"))?;
        file.write_all(&raw)?;
        drop(file);
        let tiff = out.join("output.tiff");
        write_merged(
            Merged::Bands {
                domain,
                planes: &planes,
            },
            levels,
            Some([1.0; 3]),
            None,
            image_out::OutputSpace::CameraLinear,
            true,
            Exposure::None,
            None,
            &tiff,
        )?;
        let whole_seconds = whole.elapsed().as_secs_f64();
        let consumer_end_ns = super::EPOCH.get().unwrap().elapsed().as_nanos() as u64;
        let tiff_bytes = fs::read(&tiff)?;
        assert!(tiff_bytes.len() <= 256 * 1024);
        let profile = super::snapshot();
        let counts = *super::COUNTS.lock().unwrap();
        for (phase, c) in counts.iter().enumerate() {
            assert_eq!(
                c.calls,
                if mode != 0 && [0, 4, 5, 6].contains(&phase) {
                    3
                } else {
                    0
                }
            );
        }
        if delay {
            assert!(
                counts[super::DECODE].nanos >= 75_000_000,
                "delay missed decode interval"
            );
        }
        let calls = source.calls.each_ref().map(|n| n.load(Ordering::SeqCst));
        assert_eq!(calls, [1, 1, 1]);
        assert_eq!(
            source.delay_calls.load(Ordering::SeqCst),
            if delay { 3 } else { 0 }
        );
        let result = serde_json::json!({
            "schema":"native-pyramid-profile-smoke-v1","label":label,
            "source_calls":calls,"folds":3,"requested_delay_ms_per_decode":if delay {25} else {0},
            "actual_delay_calls":source.delay_calls.load(Ordering::SeqCst),
            "configured_bands":cfg.bands,"level_count":sizes.len(),
            "whole_consumer_wall_seconds":whole_seconds,
            "consumer_start_ns":consumer_start_ns,"consumer_end_ns":consumer_end_ns,"profile":profile,
            "f32":{"path":out.join("output.f32"),"bytes":raw.len(),"sha256":hash(&raw)},
            "tiff":{"path":tiff,"bytes":tiff_bytes.len(),"sha256":hash(&tiff_bytes)},
            "scope":"No-map generated-frame timing/byte-identity control; no RAW decode or native throughput claim. Unused defect/gather/probe are not powered by this fixture."
        });
        let bytes = serde_json::to_vec_pretty(&result)?;
        assert!(bytes.len() < 32 * 1024);
        let mut f = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(out.join("result.json"))?;
        f.write_all(&bytes)?;
        f.write_all(b"\n")?;
        Ok(())
    }
}
