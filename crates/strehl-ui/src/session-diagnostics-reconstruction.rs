//! Saved original-CFA outcome and receipt-bound local support. No reconstruction runs here.
use super::*;
use sha2::{Digest, Sha256};
use std::{collections::BTreeMap, io::Read};

#[derive(Clone, Debug, Deserialize, serde::Serialize)]
pub(crate) struct Outcome {
    pub requested: bool,
    pub enabled: bool,
    pub total_rgb_pixels: u64,
    pub replaced_rgb_pixels: u64,
    pub native_fallback_pixels: u64,
    pub registration_supported_tiles: u64,
    pub reason_counts: BTreeMap<String, u64>,
    pub limitations: Vec<String>,
}

pub(super) fn outcome(render: &Value, dimensions: [u32; 2]) -> Result<Option<Outcome>> {
    let Some(value) = render.get("reconstruction").filter(|v| !v.is_null()) else {
        return Ok(None);
    };
    let result: Outcome = serde_json::from_value(value.clone())?;
    ensure!(
        result.total_rgb_pixels == u64::from(dimensions[0]) * u64::from(dimensions[1])
            && result
                .replaced_rgb_pixels
                .checked_add(result.native_fallback_pixels)
                == Some(result.total_rgb_pixels)
            && (result.enabled || result.replaced_rgb_pixels == 0)
            && (result.requested || !result.enabled),
        "Reconstruction outcome census differs from the photograph"
    );
    ensure!(
        result.reason_counts.len() <= 128
            && result
                .reason_counts
                .keys()
                .all(|k| !k.is_empty() && k.len() <= 160)
            && result.limitations.len() <= 64
            && result.limitations.iter().all(|s| s.len() <= 2048),
        "Reconstruction outcome exceeds the inspection budget"
    );
    Ok(Some(result))
}

pub(super) fn maps(folder: &Path, render: &Value, dimensions: [u32; 2]) -> Result<Vec<Map>> {
    let expected = render["reconstruction"]["geometry_sha256"]
        .as_str()
        .context("Reconstruction geometry checksum missing")?;
    ensure!(
        expected.len() == 64 && expected.bytes().all(|b| b.is_ascii_hexdigit()),
        "Invalid reconstruction geometry checksum"
    );
    let dir = folder.join("reconstruction");
    let mut bytes = Vec::new();
    std::fs::File::open(dir.join("geometry.json"))?
        .take(MAX_REPORT + 1)
        .read_to_end(&mut bytes)?;
    ensure!(
        bytes.len() as u64 <= MAX_REPORT,
        "Reconstruction geometry exceeds inspection budget"
    );
    let actual = Sha256::digest(&bytes)
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect::<String>();
    ensure!(
        actual.eq_ignore_ascii_case(expected),
        "Reconstruction geometry checksum differs"
    );
    let geometry: Value = serde_json::from_slice(&bytes)?;
    ensure!(
        geometry["schema"] == "strehl.original-cfa-reconstruction.v1",
        "Unknown reconstruction geometry schema"
    );
    let canvas: [u32; 4] = serde_json::from_value(render["canvas"].clone())
        .context("Reconstruction photograph canvas missing")?;
    let full: [u32; 2] = serde_json::from_value(geometry["full_quad_geometry"].clone())?;
    let origin: [u32; 2] = serde_json::from_value(geometry["origin_sensor"].clone())?;
    let step: [u32; 2] = serde_json::from_value(geometry["step_sensor"].clone())?;
    let d = size(&geometry["dimensions"])?;
    ensure!(
        d == dimensions
            && step == [1, 1]
            && (0..2).all(|c| canvas[c].checked_mul(2) == Some(origin[c])
                && canvas[c + 2].checked_mul(2) == Some(d[c])
                && canvas[c]
                    .checked_add(canvas[c + 2])
                    .is_some_and(|end| end <= full[c])),
        "Reconstruction map differs from the native photograph canvas"
    );
    let reasons: BTreeMap<u32, String> =
        serde_json::from_value(geometry["fallback_reasons"].clone())?;
    ensure!(
        !reasons.is_empty()
            && reasons.len() <= 128
            && reasons.iter().all(|(code, label)| *code <= 16_777_216
                && !label.is_empty()
                && label.len() <= 160),
        "Invalid reconstruction fallback labels"
    );
    let receipts = geometry["files"]
        .as_array()
        .context("Reconstruction map receipts missing")?;
    ensure!(
        receipts.len() == 2,
        "Reconstruction requires exactly support and fallback maps"
    );
    let mut adapted = Vec::new();
    let mut names = std::collections::BTreeSet::new();
    for receipt in receipts {
        let name = filename(&receipt["path"])?;
        ensure!(
            matches!(name, "support.tiff" | "fallback-reason.tiff") && names.insert(name),
            "Unknown or repeated reconstruction map"
        );
        ensure!(
            receipt["bytes"].as_u64() == Some(std::fs::metadata(dir.join(name))?.len()),
            "Reconstruction map byte count differs"
        );
        adapted.push(serde_json::json!({"file":name,"sha256":receipt["sha256"]}));
    }
    let mut result = Vec::new();
    files(
        &mut result,
        &dir,
        &serde_json::json!({"files":adapted}),
        "Original-CFA",
        (d, [1.; 2]),
        "Conditional local reconstruction support. All RGB channels are replaced together where qualified; other pixels retain the native result. Same output dimensions; support does not prove a resolution increase.",
        None,
    )?;
    for map in &mut result {
        if map.name == "support" {
            map.scale = Scale::Binary;
            map.value_labels = Some(Arc::new(BTreeMap::from([
                (0, "Native result retained".into()),
                (1, "All RGB channels reconstructed".into()),
            ])));
        } else {
            map.scale = Scale::Category;
            map.value_labels = Some(Arc::new(reasons.clone()));
        }
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn digest(bytes: &[u8]) -> String {
        Sha256::digest(bytes)
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect::<String>()
    }
    fn fixture() -> (tempfile::TempDir, Value, Value) {
        let root = tempfile::tempdir().unwrap();
        let dir = root.path().join("reconstruction");
        std::fs::create_dir(&dir).unwrap();
        let mut receipts = Vec::new();
        for name in ["support.tiff", "fallback-reason.tiff"] {
            let values = (0..64).map(|i| u8::from(i < 16)).collect::<Vec<_>>();
            image::GrayImage::from_raw(8, 8, values)
                .unwrap()
                .save(dir.join(name))
                .unwrap();
            let bytes = std::fs::read(dir.join(name)).unwrap();
            receipts
                .push(serde_json::json!({"path":name,"bytes":bytes.len(),"sha256":digest(&bytes)}));
        }
        let geometry = serde_json::json!({"schema":"strehl.original-cfa-reconstruction.v1",
            "full_quad_geometry":[20,20],"origin_sensor":[6,8],"dimensions":[8,8],"step_sensor":[1,1],
            "files":receipts,"fallback_reasons":{"0":"Native retained","1":"Reconstructed"}});
        let report = serde_json::json!({"canvas":[3,4,4,4],"reconstruction":{
            "requested":true,"enabled":true,"total_rgb_pixels":64,"replaced_rgb_pixels":16,
            "native_fallback_pixels":48,"registration_supported_tiles":2,
            "reason_counts":{"native":48},"limitations":["Conditional support, no resolution certificate"]}});
        (root, report, geometry)
    }
    fn publish(root: &Path, report: &mut Value, geometry: &Value) {
        let bytes = serde_json::to_vec(geometry).unwrap();
        std::fs::write(root.join("reconstruction/geometry.json"), &bytes).unwrap();
        report["reconstruction"]["geometry_sha256"] = digest(&bytes).into();
    }
    #[test]
    fn saved_reconstruction_binds_geometry_payload_categories_and_native_fallback() {
        let (root, mut report, geometry) = fixture();
        publish(root.path(), &mut report, &geometry);
        let summary = outcome(&report, [8, 8]).unwrap().unwrap();
        assert_eq!(summary.native_fallback_pixels, 48);
        let actual = maps(root.path(), &report, [8, 8]).unwrap();
        assert_eq!(actual.len(), 2);
        let support = &actual[0];
        assert_eq!(support.value_label(0.), "Native result retained");
        assert_eq!(support.value_label(1.), "All RGB channels reconstructed");
        let cancel = std::sync::atomic::AtomicBool::new(false);
        let loaded = load(support, &cancel).unwrap();
        assert_eq!(loaded.values.iter().filter(|&&v| v == 1.).count(), 16);
        std::fs::write(&support.path, b"tampered").unwrap();
        assert!(load(support, &cancel).is_err());
        assert!(maps(root.path(), &report, [8, 8]).is_err());
    }
    #[test]
    fn saved_reconstruction_refuses_wrong_gauge_hash_schema_and_census() {
        let (root, mut report, geometry) = fixture();
        publish(root.path(), &mut report, &geometry);
        for (key, value) in [
            ("origin_sensor", serde_json::json!([0, 0])),
            ("dimensions", serde_json::json!([4, 4])),
            ("step_sensor", serde_json::json!([2, 2])),
            ("full_quad_geometry", serde_json::json!([4, 4])),
            ("schema", serde_json::json!("unknown")),
        ] {
            let mut changed = geometry.clone();
            changed[key] = value;
            publish(root.path(), &mut report, &changed);
            assert!(maps(root.path(), &report, [8, 8]).is_err(), "{key}");
        }
        publish(root.path(), &mut report, &geometry);
        report["reconstruction"]["geometry_sha256"] = "0".repeat(64).into();
        assert!(maps(root.path(), &report, [8, 8]).is_err());
        report["reconstruction"]["native_fallback_pixels"] = 47.into();
        assert!(outcome(&report, [8, 8]).is_err());
        report["reconstruction"]["native_fallback_pixels"] = 48.into();
        report["reconstruction"]["enabled"] = false.into();
        assert!(outcome(&report, [8, 8]).is_err());
        report["reconstruction"]["replaced_rgb_pixels"] = 0.into();
        report["reconstruction"]["native_fallback_pixels"] = 64.into();
        assert!(!outcome(&report, [8, 8]).unwrap().unwrap().enabled);
    }
}
