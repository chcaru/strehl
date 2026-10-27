//! Generated metadata-only files exercise the real explicit-map resolver.
//! Subprocesses isolate the process-global alignment environment from tests.
use super::*;
use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering as AtomicOrdering};

const CHILD_CASE: &str = "STREHL_V_OVERRIDE_CHILD_CASE";
const CHILD_ROOT: &str = "STREHL_V_OVERRIDE_CHILD_ROOT";
const CURRENT_STRATEGY: &str = "S3-ba-unit-measured-component-v1";
static NEXT_FIXTURE: AtomicU64 = AtomicU64::new(0);

struct Fixture {
    root: PathBuf,
    files: Vec<PathBuf>,
}

impl Fixture {
    fn new(case: &str) -> Self {
        let nonce = NEXT_FIXTURE.fetch_add(1, AtomicOrdering::Relaxed);
        let ticks = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!(
            "strehl-v-override-{}-{ticks}-{nonce}",
            std::process::id()
        ));
        std::fs::create_dir(&root).unwrap();
        let mut files = Vec::new();
        for index in 0..3 {
            let path = root.join(format!("generated-{index}.arw"));
            // Deliberately not valid RAW data: this path may stat the files,
            // but any unintended decode/re-solve must fail the test.
            std::fs::write(
                &path,
                format!("V generated placeholder {index}; no camera data"),
            )
            .unwrap();
            files.push(path);
        }
        let identity =
            StackIdentity::from_paths(root.file_name().unwrap().to_str().unwrap(), &files).unwrap();
        let strategy = match case {
            "current" => CURRENT_STRATEGY,
            "planted" => "V-planted-identity-control",
            "research" => "research-lens-direct-global-f32-v1",
            _ => "S3-ba-unit",
        };
        let map = WarpMap::new(
            strehl_core::warpmap::Provenance {
                stack: identity,
                strategy: strategy.into(),
                heldout_px: None,
                cycle_floor_px: None,
                reference: 1,
                note: "generated explicit-map route; provenance is not measured-edge proof".into(),
            },
            PlaneGeometry {
                width: 40,
                height: 32,
            },
            Resampler::CatmullRom,
            vec![FrameWarp::Placed(strehl_core::align::Similarity::IDENTITY); 3],
        );
        let sidecar = root.join("requested-map.txt");
        map.save(&sidecar).unwrap();
        files.push(sidecar);
        Self { root, files }
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        // Preserve all evidence if a child or parent assertion fails.
        if std::thread::panicking() {
            eprintln!("V_OVERRIDE_RETAINED fixture_root={:?}", self.root);
            return;
        }
        // Delete only files this fixture explicitly created, then its empty
        // directory. Leave unexpected artifacts for diagnosis; no recursion.
        for path in &self.files {
            let _ = std::fs::remove_file(path);
        }
        let _ = std::fs::remove_dir(&self.root);
    }
}

fn snapshot(root: &Path) -> Vec<(String, Vec<u8>)> {
    let mut files: Vec<_> = std::fs::read_dir(root)
        .unwrap()
        .map(|entry| {
            let entry = entry.unwrap();
            (
                entry.file_name().to_string_lossy().into_owned(),
                std::fs::read(entry.path()).unwrap(),
            )
        })
        .collect();
    files.sort_by(|a, b| a.0.cmp(&b.0));
    files
}

fn child(case: &str, mode: &str) {
    let root = PathBuf::from(std::env::var_os(CHILD_ROOT).unwrap());
    let paths: Vec<_> = (0..3)
        .map(|i| root.join(format!("generated-{i}.arw")))
        .collect();
    let before = snapshot(&root);
    let saved = WarpMap::load(root.join("requested-map.txt")).unwrap();
    let (progress, lines) = crate::ui_progress::Progress::captured(paths.len());
    let actual = alignment_for_observed(&root, &paths, Resampler::Bilinear, Some(&progress));
    assert_eq!(
        snapshot(&root),
        before,
        "explicit resolver wrote or altered fixture artifacts"
    );
    let lines = lines.lock().unwrap();
    let returned_override = lines.iter().any(|line| line.contains("source=override"));
    if case == "off" {
        assert!(
            actual.unwrap().is_none(),
            "STREHL_ALIGN=0 must precede explicit-map policy"
        );
        assert!(!returned_override);
        assert!(lines.iter().any(|line| line.contains("source=off")));
    } else if case == "legacy" && mode != "witness" {
        assert!(
            actual.is_err(),
            "legacy ordinary explicit map bypassed the measured-component policy"
        );
        let error = format!("{:#}", actual.unwrap_err());
        assert!(
            error.contains("legacy ordinary alignment"),
            "wrong refusal: {error}"
        );
        assert!(error.contains(WARPMAP_ENV));
        assert!(error.contains("requested-map.txt"));
        assert!(error.contains("no replacement was written"));
        assert!(
            !returned_override,
            "refused sidecar was reported as consumed"
        );
    } else {
        let (map, how) = actual.unwrap().expect("explicit map should be consumed");
        assert_eq!(map, saved, "explicit map was silently replaced or changed");
        assert_eq!(how, "sidecar-override");
        assert_eq!(
            map.resampler(),
            Resampler::CatmullRom,
            "named sidecar kernel still wins"
        );
        assert!(returned_override, "missing explicit-map observer event");
    }
    println!("V_OVERRIDE case={case} mode={mode} input_and_map_bytes_unchanged=true");
}

pub(super) fn run(full_test_name: &str, mode: &str) {
    if let Ok(case) = std::env::var(CHILD_CASE) {
        child(&case, mode);
        return;
    }
    let cases: &[&str] = if mode == "candidate" {
        &["legacy", "current", "planted", "research", "off"]
    } else {
        &["legacy"]
    };
    for &case in cases {
        let fixture = Fixture::new(case);
        println!(
            "V_OVERRIDE_FIXTURE {}",
            serde_json::json!({
                "case": case, "mode": mode,
                "root": fixture.root.to_string_lossy(),
                "sidecar": fixture.root.join("requested-map.txt").to_string_lossy(),
            })
        );
        let output = Command::new(std::env::current_exe().unwrap())
            .args(["--exact", full_test_name, "--nocapture", "--test-threads=1"])
            .env(CHILD_CASE, case)
            .env(CHILD_ROOT, &fixture.root)
            .env(WARPMAP_ENV, fixture.root.join("requested-map.txt"))
            .env("STREHL_ALIGN", if case == "off" { "0" } else { "1" })
            .output()
            .expect("start isolated explicit-map child");
        print!("{}", String::from_utf8_lossy(&output.stdout));
        eprint!("{}", String::from_utf8_lossy(&output.stderr));
        assert!(
            output.status.success(),
            "explicit-map child failed: case={case}, status={}",
            output.status
        );
        assert!(
            String::from_utf8_lossy(&output.stdout).contains(&format!("V_OVERRIDE case={case}")),
            "child did not execute the requested fixture"
        );
    }
}
