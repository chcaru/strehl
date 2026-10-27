use super::*;

// Generated metadata-only TIFF with intentionally undecodable pixel bytes.
// Focus EXIF is absent while the independent optical RAW directory is present.
fn optical_fixture(bad_table: bool) -> Vec<u8> {
    fn word(out: &mut [u8], at: usize, value: u16) {
        out[at..at + 2].copy_from_slice(&value.to_le_bytes());
    }
    fn long(out: &mut [u8], at: usize, value: u32) {
        out[at..at + 4].copy_from_slice(&value.to_le_bytes());
    }
    fn entry(out: &mut [u8], at: usize, tag: u16, kind: u16, count: u32, data: u32) {
        word(out, at, tag);
        word(out, at + 2, kind);
        long(out, at + 4, count);
        long(out, at + 8, data);
    }
    let mut out = vec![0; 1024];
    out[..4].copy_from_slice(b"II*\0");
    long(&mut out, 4, 8);
    word(&mut out, 8, 4);
    entry(&mut out, 10, 0x010f, 2, 5, 200);
    entry(&mut out, 22, 0x0110, 2, 11, 208);
    entry(&mut out, 34, 0x0131, 2, 17, 224);
    entry(&mut out, 46, 0x014a, 4, 1, 256);
    out[200..205].copy_from_slice(b"SONY\0");
    out[208..219].copy_from_slice(b"ILCE-7CM2\0\0");
    out[224..241].copy_from_slice(b"ILCE-7CM2 v2.00\0\0");
    word(&mut out, 256, 8);
    entry(&mut out, 258, 0x0100, 4, 1, 7168);
    entry(&mut out, 270, 0x0101, 4, 1, 5120);
    entry(&mut out, 282, 0x0106, 3, 1, 32803);
    entry(&mut out, 294, 0x0111, 4, 1, 900);
    entry(&mut out, 306, 0x0117, 4, 1, 4);
    entry(&mut out, 318, 0x7036, 3, 1, 0);
    entry(
        &mut out,
        330,
        0x7037,
        8,
        if bad_table { 16 } else { 17 },
        400,
    );
    entry(&mut out, 342, 0xc61d, 4, 1, 16383);
    word(&mut out, 400, 16);
    for i in 0..16 {
        word(&mut out, 402 + 2 * i, (-(i as i16)) as u16);
    }
    out[900..904].copy_from_slice(b"FAIL");
    out
}

struct FixtureDirectory(PathBuf);
impl FixtureDirectory {
    fn new() -> Self {
        static NEXT: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
        let root = std::env::temp_dir().join(format!(
            "strehl-optical-inspect-{}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos(),
            NEXT.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
        ));
        std::fs::create_dir(&root).unwrap();
        eprintln!("OPTICAL_INSPECT_FIXTURE {}", root.display());
        Self(root)
    }
}
impl Drop for FixtureDirectory {
    fn drop(&mut self) {
        if std::thread::panicking() {
            return;
        }
        // Only these known generated files are ours; never recurse into a path.
        for name in ["source.ARW", "report.json", "report.html"] {
            let _ = std::fs::remove_file(self.0.join(name));
        }
        let _ = std::fs::remove_dir(&self.0);
    }
}

#[test]
fn optical_inspect_actual_run_exports_independent_facts_without_focus_or_pixels() {
    let directory = FixtureDirectory::new();
    let input = directory.0.join("source.ARW");
    let bytes = optical_fixture(false);
    std::fs::write(&input, &bytes).unwrap();
    let paths = vec![input.clone()];
    let ordinary = serde_json::to_value(audit_paths(&paths, false)).unwrap();
    assert!(ordinary["frames"][0].get("optical").is_none());
    let args = InspectArgs {
        input: input.clone(),
        limit: None,
        records: false,
        optical: true,
        out: Some(directory.0.join("report.json")),
        html: Some(directory.0.join("report.html")),
    };
    run(&args).unwrap();
    let result: serde_json::Value =
        serde_json::from_slice(&std::fs::read(args.out.as_ref().unwrap()).unwrap()).unwrap();
    let frame = &result["frames"][0];
    assert_eq!(frame["status"], "absent");
    assert_eq!(frame["optical"]["status"], "present");
    let facts = &frame["optical"]["facts"];
    assert_eq!(facts["distortion"]["setting"]["value"], 0);
    assert_eq!(facts["distortion"]["table"]["samples"][15], -15);
    assert_eq!(facts["distortion"]["table"]["source"]["value_offset"], 400);
    assert_eq!(facts["distortion"]["table"]["source"]["tiff_type"], 8);
    assert_eq!(facts["header_white"]["value"], 16383);
    assert!(facts["maker_distortion_setting"].is_null());
    assert!(facts["geometry"]["active_area"].is_null());
    assert!(result["scalar_b_segments"].as_array().unwrap().is_empty());
    let html = std::fs::read_to_string(args.html.as_ref().unwrap()).unwrap();
    assert!(html.contains("optical-facts"));
    assert!(html.contains("strehl-sony-optical-facts-v1"));
    assert_eq!(std::fs::read(&input).unwrap(), bytes);
}

#[test]
fn optical_inspect_actual_malformed_table_is_not_absence_or_focus_failure() {
    let directory = FixtureDirectory::new();
    let input = directory.0.join("source.ARW");
    let bytes = optical_fixture(true);
    std::fs::write(&input, &bytes).unwrap();
    let result = audit_paths_with_optical(std::slice::from_ref(&input), false, true);
    let result = serde_json::to_value(result).unwrap();
    assert_eq!(result["frames"][0]["status"], "absent");
    assert_eq!(result["frames"][0]["optical"]["status"], "malformed");
    assert!(result["frames"][0]["optical"].get("facts").is_none());
    assert!(
        result["frames"][0]["optical"]["reason"]
            .as_str()
            .unwrap()
            .contains("0x7037")
    );
    assert_eq!(std::fs::read(&input).unwrap(), bytes);
}
