//! Saved geometry and scalar evidence, loaded once on a background worker.
use anyhow::{Context, Result, ensure};
use serde::Deserialize;
use serde_json::Value;
use std::{
    path::{Path, PathBuf},
    sync::Arc,
};

#[path = "session-diagnostics-reconstruction.rs"]
mod reconstruction;

const MAX_REPORT: u64 = 64 * 1024 * 1024;
pub(super) const MAX_MAP_PIXELS: usize = 40_000_000;
#[derive(Clone, Copy, Debug)]
pub(super) enum Scale {
    Unit,
    Correlation,
    Binary,
    Category,
    Flags,
    Positive,
}
#[derive(Clone)]
pub(super) struct Map {
    pub path: PathBuf,
    pub label: String,
    pub name: String,
    pub size: [u32; 2],
    pub extent: [f32; 2],
    pub sha256: Option<String>,
    pub scale: Scale,
    pub scope: String,
    pub repro: Option<Arc<Repro>>,
    pub value_labels: Option<Arc<std::collections::BTreeMap<u32, String>>>,
}
pub(super) struct Catalog {
    pub maps: Vec<Map>,
    pub warnings: Vec<String>,
    pub reconstruction: Option<reconstruction::Outcome>,
}
pub(super) struct LoadedMap {
    pub values: Vec<f32>,
    pub range: [f32; 2],
    pub image: eframe::egui::ColorImage,
}

#[derive(Clone, Deserialize)]
pub(super) struct Ring {
    pub frequency: f32,
    pub power_first: f32,
    pub power_second: f32,
    pub correlation: Option<f32>,
}
#[derive(Clone, Deserialize)]
pub(super) struct Tile {
    pub tile: [usize; 2],
    pub origin_sensor: [usize; 2],
    pub qualification: u8,
    pub band_correlation: Option<f32>,
    pub relative_rms_difference: Option<f32>,
    pub band_amplitude_ratio: Option<f32>,
    pub rings: Vec<Ring>,
}
#[derive(Clone, Deserialize)]
pub(super) struct Repro {
    pub tile_dimensions: [usize; 2],
    pub tile_step_sensor: usize,
    pub sensor_dimensions: [usize; 2],
    pub tiles: Vec<Tile>,
}
pub(super) fn read(path: &Path) -> Result<Value> {
    let file = std::fs::File::open(path).with_context(|| format!("Reading {}", path.display()))?;
    ensure!(
        file.metadata()?.len() <= MAX_REPORT,
        "Saved report exceeds 64 MiB"
    );
    Ok(serde_json::from_reader(std::io::BufReader::new(file))?)
}
fn size(value: &Value) -> Result<[u32; 2]> {
    let d: [u32; 2] = serde_json::from_value(value.clone()).context("Missing map dimensions")?;
    ensure!(
        d.iter().all(|&n| n > 0 && n <= 32_768) && d[0] as usize * d[1] as usize <= MAX_MAP_PIXELS,
        "Saved map exceeds the inspection budget"
    );
    Ok(d)
}
fn filename(value: &Value) -> Result<&str> {
    let name = value.as_str().context("Saved map filename is not text")?;
    ensure!(
        !name.is_empty()
            && name.len() < 128
            && !name.contains(['/', '\\', ':'])
            && name.ends_with(".tiff"),
        "Invalid saved map filename"
    );
    Ok(name)
}
fn files(
    maps: &mut Vec<Map>,
    folder: &Path,
    report: &Value,
    label: &str,
    geometry: ([u32; 2], [f32; 2]),
    scope: &str,
    repro: Option<Arc<Repro>>,
) -> Result<()> {
    let (d, extent) = geometry;
    ensure!(
        extent
            .iter()
            .all(|v| v.is_finite() && *v > 0.0 && *v <= 2.0),
        "Invalid saved map extent"
    );
    for receipt in report["files"]
        .as_array()
        .context("Missing saved map receipts")?
    {
        let name = filename(&receipt["file"])?;
        let checksum = receipt["sha256"]
            .as_str()
            .context("Missing saved map checksum")?;
        ensure!(
            checksum.len() == 64 && checksum.bytes().all(|b| b.is_ascii_hexdigit()),
            "Invalid saved map checksum"
        );
        let stem = name.trim_end_matches(".tiff");
        let scale = if stem == "correlation" {
            Scale::Correlation
        } else if stem.ends_with("fraction") {
            Scale::Unit
        } else if matches!(stem, "raw-coverage" | "focus-coverage" | "usable")
            || stem.ends_with("-boundary")
        {
            Scale::Binary
        } else if stem == "flags" {
            Scale::Flags
        } else if matches!(
            stem,
            "kind" | "qualification" | "dominant-source" | "dominant-group"
        ) || stem.starts_with("source-rank-")
        {
            Scale::Category
        } else {
            Scale::Positive
        };
        ensure!(maps.len() < 4096, "Too many saved diagnostic maps");
        maps.push(Map {
            path: folder.join(name),
            label: format!("{label} · {}", stem.replace('-', " ")),
            name: stem.into(),
            size: d,
            extent,
            sha256: Some(checksum.into()),
            scale,
            scope: scope.into(),
            repro: repro.clone(),
            value_labels: None,
        });
    }
    Ok(())
}

pub(super) fn catalog(output: &Path) -> Result<Catalog> {
    let folder = output.parent().context("Photograph directory missing")?;
    let root = if folder
        .file_name()
        .is_some_and(|n| n.to_string_lossy().starts_with("layer-"))
    {
        folder.parent().context("Layer parent missing")?
    } else {
        folder
    };
    let dimensions = image::ImageReader::open(output)?
        .with_guessed_format()?
        .into_dimensions()?;
    ensure!(
        dimensions.0 > 0 && dimensions.1 > 0,
        "Photograph has no pixels"
    );
    let render = read(&folder.join("render-report.json")).ok();
    let canvas = render
        .as_ref()
        .and_then(|v| v["canvas"].as_array())
        .filter(|v| v.len() == 4);
    if let Some(c) = canvas {
        ensure!(
            c[2].as_u64()
                .is_some_and(|v| v.checked_mul(2) == Some(u64::from(dimensions.0)))
                && c[3]
                    .as_u64()
                    .is_some_and(|v| v.checked_mul(2) == Some(u64::from(dimensions.1))),
            "Saved canvas dimensions differ from the photograph"
        );
    }
    let mut result = Catalog {
        maps: Vec::new(),
        warnings: Vec::new(),
        reconstruction: None,
    };
    if let Some(render) = &render {
        match reconstruction::outcome(render, [dimensions.0, dimensions.1]) {
            Ok(outcome) => result.reconstruction = outcome,
            Err(error) => result
                .warnings
                .push(format!("Reconstruction outcome: {error:#}")),
        }
    }
    let mut load_part = |name: &str, f: &mut dyn FnMut(&mut Vec<Map>) -> Result<()>| {
        if let Err(error) = f(&mut result.maps) {
            result.warnings.push(format!("{name}: {error:#}"));
        }
    };
    if let Some(render) = &render
        && render["reconstruction"]["requested"] == true
    {
        load_part("Original-CFA reconstruction", &mut |maps| {
            maps.extend(reconstruction::maps(
                folder,
                render,
                [dimensions.0, dimensions.1],
            )?);
            Ok(())
        });
    }
    if folder.join("contributions/index.json").is_file() {
        load_part("Contributions", &mut |maps| {
            let dir = folder.join("contributions");
            let report = read(&dir.join("index.json"))?;
            ensure!(
                report["schema"] == "strehl.session-contributions.v1",
                "Unknown contribution schema"
            );
            let domain = report["domain_quad"]
                .as_array()
                .context("Contribution domain missing")?;
            ensure!(
                Some(domain) == canvas,
                "Contribution maps differ from the photograph canvas"
            );
            for band in report["bands"]
                .as_array()
                .context("Contribution bands missing")?
            {
                let k = band["band"].as_u64().context("Band index missing")?;
                ensure!(k <= 16, "Band index exceeds supported range");
                let d = size(&band["dimensions"])?;
                let step = band["step_quad"].as_u64().context("Band step missing")?;
                ensure!(
                    step == 1u64 << k && band["origin_quad"] == Value::Array(domain[..2].to_vec()),
                    "Contribution grid differs"
                );
                let extent = [
                    d[0] as f32 * step as f32 * 2.0 / dimensions.0 as f32,
                    d[1] as f32 * step as f32 * 2.0 / dimensions.1 as f32,
                ];
                files(
                    maps,
                    &dir.join(format!("band-{k:02}")),
                    band,
                    &format!("Band {k}"),
                    (d, extent),
                    "Band coefficients before collapse/demosaic. Conditional variance excludes adaptive selection, shared guides and cross-band covariance; it is not final-pixel uncertainty.",
                    None,
                )?;
            }
            Ok(())
        });
    }
    if root.join("focus/focus-evidence.json").is_file() {
        load_part("Focus", &mut |maps| {
            let dir = root.join("focus");
            let report = read(&dir.join("focus-evidence.json"))?;
            ensure!(
                report["schema"] == "strehl.session-focus.v1",
                "Unknown focus schema"
            );
            for (index, pass) in report["passes"]
                .as_array()
                .context("Focus passes missing")?
                .iter()
                .enumerate()
            {
                ensure!(index < 64, "Too many focus passes");
                let d = size(&pass["dimensions"])?;
                let origin = pass["origin_quad"]
                    .as_array()
                    .context("Focus origin missing")?;
                let c = canvas.context("Photograph canvas missing for focus overlay")?;
                ensure!(
                    origin.as_slice() == &c[..2]
                        && u64::from(d[0]) * 2 == u64::from(dimensions.0)
                        && u64::from(d[1]) * 2 == u64::from(dimensions.1),
                    "Focus map differs from the photograph canvas"
                );
                files(
                    maps,
                    &dir.join(format!("pass-{:02}", index + 1)),
                    pass,
                    &format!("Pass {} focus", index + 1),
                    (d, [1.0; 2]),
                    "Acquisition ordinal and local response shape, not metric depth or calibrated confidence. Check usable and flags before interpreting a peak.",
                    None,
                )?;
            }
            Ok(())
        });
    }
    if root.join("reproducibility/reproducibility.json").is_file() {
        load_part("Reproducibility", &mut |maps| {
            let dir = root.join("reproducibility");
            let report = read(&dir.join("reproducibility.json"))?;
            ensure!(
                report["schema"] == "strehl.session-reproducibility.v1",
                "Unknown reproducibility schema"
            );
            let repro: Repro = serde_json::from_value(report.clone())?;
            repro.validate()?;
            ensure!(
                repro.sensor_dimensions == [dimensions.0 as usize, dimensions.1 as usize]
                    && report["canvas_quad"].as_array() == canvas,
                "Comparison differs from the photograph canvas"
            );
            let d = size(&report["tile_dimensions"])?;
            let extent = [
                d[0] as f32 * repro.tile_step_sensor as f32 / dimensions.0 as f32,
                d[1] as f32 * repro.tile_step_sensor as f32 / dimensions.1 as f32,
            ];
            files(
                maps,
                &dir,
                &report,
                "First two passes",
                (d, extent),
                "Descriptive repeat structure. Common blur, shared processing and fixed pattern can correlate without true detail. No resolution cutoff or calibration is inferred. Border remainder strips have no result.",
                Some(Arc::new(repro)),
            )?;
            Ok(())
        });
    }
    let completion = read(&root.join("completed.json"))?;
    if completion["mode"] == "mosaic" {
        for (name, label, scale, d) in [
            (
                "coverage",
                "Mosaic · final coverage",
                Scale::Binary,
                [dimensions.0, dimensions.1],
            ),
            (
                "join-confidence",
                "Mosaic · join status",
                Scale::Category,
                [dimensions.0 / 2, dimensions.1 / 2],
            ),
            (
                "view-owner",
                "Mosaic · view owner",
                Scale::Category,
                [dimensions.0 / 2, dimensions.1 / 2],
            ),
        ] {
            ensure!(
                d[0] as usize * d[1] as usize <= MAX_MAP_PIXELS,
                "Mosaic diagnostic exceeds the inspection budget"
            );
            let checksum = completion[format!("{}_sha256", name.replace('-', "_"))]
                .as_str()
                .map(str::to_owned);
            ensure!(
                checksum
                    .as_ref()
                    .is_some_and(|v| v.len() == 64 && v.bytes().all(|b| b.is_ascii_hexdigit())),
                "Mosaic map checksum missing"
            );
            result.maps.push(Map{path:root.join(format!("{name}.tiff")),label:label.into(),name:name.into(),size:d,extent:[1.0;2],sha256:checksum,scale,scope:if name=="join-confidence" {"0 uncovered; 1 one view; 2 qualified compatible blend; 3 overlap retained from one view. These are categories, not probabilities."}else{"Final mosaic coverage and declared-view ownership; zero is unsupported. No primary pass."}.into(),repro:None,value_labels:None});
        }
    }
    Ok(result)
}
impl Repro {
    fn validate(&self) -> Result<()> {
        let [w, h] = self.tile_dimensions;
        ensure!(
            w > 0
                && h > 0
                && w.checked_mul(h) == Some(self.tiles.len())
                && self.tiles.len() <= 262_144,
            "Invalid comparison tile count"
        );
        ensure!(
            self.tile_step_sensor > 0 && self.tile_step_sensor <= 512,
            "Invalid comparison tile step"
        );
        ensure!(
            w.checked_mul(self.tile_step_sensor)
                .is_some_and(|n| n <= self.sensor_dimensions[0])
                && h.checked_mul(self.tile_step_sensor)
                    .is_some_and(|n| n <= self.sensor_dimensions[1]),
            "Comparison tiles exceed the photograph"
        );
        for (i, tile) in self.tiles.iter().enumerate() {
            ensure!(
                tile.tile == [i % w, i / w]
                    && tile.origin_sensor
                        == [i % w * self.tile_step_sensor, i / w * self.tile_step_sensor]
                    && (1..=4).contains(&tile.qualification)
                    && tile.rings.len() <= 512,
                "Invalid comparison tile geometry or qualification"
            );
            ensure!(
                [
                    tile.band_correlation,
                    tile.relative_rms_difference,
                    tile.band_amplitude_ratio
                ]
                .into_iter()
                .flatten()
                .all(f32::is_finite),
                "Nonfinite comparison statistic"
            );
            ensure!(
                tile.rings.iter().all(|r| r.frequency.is_finite()
                    && r.frequency >= 0.0
                    && r.frequency <= 1.0
                    && r.power_first.is_finite()
                    && r.power_first >= 0.0
                    && r.power_second.is_finite()
                    && r.power_second >= 0.0
                    && r.correlation
                        .is_none_or(|v| v.is_finite() && (-1.001..=1.001).contains(&v))),
                "Invalid comparison spectrum"
            );
        }
        Ok(())
    }
}
pub(super) fn qualification(code: u8) -> &'static str {
    match code {
        1 => "Both passes have an unambiguous interior focus peak",
        2 => "Missing coverage",
        3 => "Focus compatibility unverified",
        4 => "No spectral structure",
        _ => "Qualification unavailable",
    }
}
impl Map {
    pub fn index(&self, uv: [f32; 2]) -> Option<usize> {
        if uv.iter().any(|v| !v.is_finite())
            || (0..2).any(|c| uv[c] < 0.0 || uv[c] >= self.extent[c])
        {
            return None;
        }
        let p = [0, 1].map(|c| (uv[c] / self.extent[c] * self.size[c] as f32).floor() as usize);
        Some(p[1] * self.size[0] as usize + p[0])
    }
    pub fn value_label(&self, v: f32) -> String {
        if !v.is_finite() {
            return "Unavailable · not zero".into();
        }
        if let Some(labels) = &self.value_labels {
            return labels
                .get(&(v as u32))
                .cloned()
                .unwrap_or_else(|| "Unknown saved category".into());
        }
        if self.name == "qualification" {
            return qualification(v as u8).into();
        }
        if self.name == "kind" {
            return match v as u8 {
                0 => "Uncovered",
                1 => "Focus weighted",
                2 => "Plain mean fallback",
                3 => "Saturated display mean · statistics unavailable",
                4 => "Saturated primary display · statistics unavailable",
                _ => "Unknown kind",
            }
            .into();
        }
        if self.name == "join-confidence" {
            return match v as u8 {
                0 => "Uncovered",
                1 => "Single view",
                2 => "Qualified compatible blend",
                3 => "Unmerged overlap · one view",
                _ => "Unknown join category",
            }
            .into();
        }
        if self.name == "flags" {
            let labels = [
                (1, "boundary"),
                (2, "scale disagreement"),
                (4, "competing mode"),
                (8, "weak response"),
                (16, "no local fit"),
                (32, "missing coverage"),
                (64, "unresolved mode"),
            ];
            let set = labels
                .into_iter()
                .filter(|(bit, _)| (v as u8) & bit != 0)
                .map(|(_, name)| name)
                .collect::<Vec<_>>();
            return if set.is_empty() {
                "No refusal flags".into()
            } else {
                set.join(", ")
            };
        }
        format!("{v:.6}")
    }
}
pub(super) fn load(map: &Map, cancelled: &std::sync::atomic::AtomicBool) -> Result<LoadedMap> {
    static DECODER: std::sync::Mutex<()> = std::sync::Mutex::new(());
    let _lane = DECODER
        .lock()
        .map_err(|_| anyhow::anyhow!("Diagnostic decoder lane failed"))?;
    ensure!(
        !cancelled.load(std::sync::atomic::Ordering::Relaxed),
        "Map loading cancelled"
    );
    let image = strehl_edit::read_scalar_tiff(
        &map.path,
        map.size,
        MAX_MAP_PIXELS * 4,
        map.sha256.as_deref(),
    )?;
    let values = image.samples.into_f32();
    ensure!(
        !cancelled.load(std::sync::atomic::Ordering::Relaxed),
        "Map loading cancelled"
    );
    ensure!(
        values
            .iter()
            .copied()
            .filter(|v| v.is_finite())
            .all(|v| match map.scale {
                Scale::Unit => (-0.0001..=1.0001).contains(&v),
                Scale::Correlation => (-1.001..=1.001).contains(&v),
                Scale::Binary => v == 0.0 || v == 1.0 || v == 255.0,
                Scale::Category | Scale::Flags =>
                    (0.0..=16_777_216.0).contains(&v) && v.fract() == 0.0,
                Scale::Positive => v >= 0.0,
            }),
        "Saved diagnostic values violate their declared scale"
    );
    ensure!(
        map.value_labels.as_ref().is_none_or(|labels| values
            .iter()
            .filter(|v| v.is_finite())
            .all(|v| labels.contains_key(&(*v as u32)))),
        "Unknown reconstruction map category"
    );
    let range = match map.scale {
        Scale::Unit | Scale::Binary => [0.0, 1.0],
        Scale::Correlation => [-1.0, 1.0],
        _ => [
            0.0,
            values
                .iter()
                .copied()
                .filter(|v| v.is_finite())
                .fold(1.0f32, f32::max),
        ],
    };
    let stride = map.size[0].max(map.size[1]).div_ceil(1600).max(1);
    let size = map.size.map(|v| v.div_ceil(stride) as usize);
    let mut pixels = Vec::with_capacity(size[0] * size[1]);
    for y in 0..size[1] {
        for x in 0..size[0] {
            pixels.push(color(
                values[(y * stride as usize) * map.size[0] as usize + x * stride as usize],
                map.scale,
                range,
            ));
        }
    }
    Ok(LoadedMap {
        values,
        range,
        image: eframe::egui::ColorImage::new(size, pixels),
    })
}
pub(super) fn color(value: f32, scale: Scale, range: [f32; 2]) -> eframe::egui::Color32 {
    use eframe::egui::Color32;
    if !value.is_finite() {
        return Color32::TRANSPARENT;
    }
    if matches!(scale, Scale::Category | Scale::Flags) {
        if value == 0.0 {
            return Color32::from_rgb(70, 70, 70);
        }
        let colors = [
            [64, 170, 180],
            [235, 177, 65],
            [195, 94, 172],
            [120, 180, 85],
            [220, 100, 70],
            [80, 125, 220],
            [180, 165, 120],
        ];
        let c = colors[(value as usize - 1) % colors.len()];
        return Color32::from_rgb(c[0], c[1], c[2]);
    }
    let t = if matches!(scale, Scale::Binary) {
        if value > 0.0 { 1.0 } else { 0.0 }
    } else {
        ((value - range[0]) / (range[1] - range[0]).max(f32::EPSILON)).clamp(0.0, 1.0)
    };
    Color32::from_rgb(
        (35.0 + 210.0 * t) as u8,
        (65.0 + 120.0 * (1.0 - (2.0 * t - 1.0).abs())) as u8,
        (220.0 - 180.0 * t) as u8,
    )
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn traversal_and_incomplete_comparison_margins_never_become_samples() {
        for name in ["../x.tiff", "C:\\x.tiff", "a/b.tiff"] {
            assert!(filename(&Value::String(name.into())).is_err());
        }
        let map = Map {
            path: "unused".into(),
            label: "test".into(),
            name: "correlation".into(),
            size: [2, 1],
            extent: [0.8, 0.5],
            sha256: None,
            scale: Scale::Correlation,
            scope: String::new(),
            repro: None,
            value_labels: None,
        };
        assert_eq!(map.index([0.79, 0.49]), Some(1));
        assert_eq!(map.index([0.81, 0.1]), None);
        assert_eq!(map.index([0.1, 0.6]), None);
        assert_eq!(map.index([f32::NAN, 0.0]), None);
        assert_eq!(
            color(f32::NAN, Scale::Positive, [0., 1.]),
            eframe::egui::Color32::TRANSPARENT
        );
        assert_ne!(
            color(0., Scale::Positive, [0., 1.]),
            eframe::egui::Color32::TRANSPARENT
        );
        assert!(qualification(3).contains("unverified"));
    }

    #[test]
    fn saved_map_catalog_binds_canvas_receipts_and_refuses_tampered_payload() {
        use sha2::{Digest, Sha256};
        let root = tempfile::tempdir().unwrap();
        let output = root.path().join("photograph.tiff");
        image::RgbImage::new(8, 8).save(&output).unwrap();
        let dir = root.path().join("contributions/band-00");
        std::fs::create_dir_all(&dir).unwrap();
        let map = dir.join("effective-sources.tiff");
        image::GrayImage::from_raw(4, 4, vec![2; 16])
            .unwrap()
            .save(&map)
            .unwrap();
        let hash = Sha256::digest(std::fs::read(&map).unwrap())
            .iter()
            .map(|v| format!("{v:02x}"))
            .collect::<String>();
        let save = |name: &str, value: Value| {
            std::fs::write(root.path().join(name), serde_json::to_vec(&value).unwrap()).unwrap()
        };
        save(
            "render-report.json",
            serde_json::json!({"canvas":[10,20,4,4]}),
        );
        save(
            "completed.json",
            serde_json::json!({"schema":"strehl.session-completion.v1"}),
        );
        save(
            "contributions/index.json",
            serde_json::json!({"schema":"strehl.session-contributions.v1","domain_quad":[10,20,4,4],"bands":[{"band":0,"dimensions":[4,4],"origin_quad":[10,20],"step_quad":1,"files":[{"file":"effective-sources.tiff","sha256":hash}]}]}),
        );
        let catalog = catalog(&output).unwrap();
        assert_eq!(catalog.maps.len(), 1);
        assert!(catalog.warnings.is_empty());
        let cancel = std::sync::atomic::AtomicBool::new(false);
        let loaded = load(&catalog.maps[0], &cancel).unwrap();
        assert_eq!(loaded.values, vec![2.; 16]);
        image::GrayImage::from_raw(4, 4, vec![3; 16])
            .unwrap()
            .save(&map)
            .unwrap();
        assert!(load(&catalog.maps[0], &cancel).is_err());
        save(
            "render-report.json",
            serde_json::json!({"canvas":[10,20,8,4]}),
        );
        assert!(super::catalog(&output).is_err());
    }
    #[test]
    fn saved_reproducibility_requires_ordered_cells_and_retains_unverified_qualification() {
        let tile = Tile {
            tile: [0, 0],
            origin_sensor: [0, 0],
            qualification: 3,
            band_correlation: Some(0.99),
            relative_rms_difference: Some(0.1),
            band_amplitude_ratio: Some(1.0),
            rings: vec![Ring {
                frequency: 0.25,
                power_first: 2.,
                power_second: 2.,
                correlation: Some(0.99),
            }],
        };
        let mut report = Repro {
            tile_dimensions: [1, 1],
            tile_step_sensor: 64,
            sensor_dimensions: [65, 65],
            tiles: vec![tile],
        };
        report.validate().unwrap();
        assert_eq!(report.tiles[0].qualification, 3);
        report.tiles[0].origin_sensor = [1, 0];
        assert!(report.validate().is_err());
        report.tiles[0].origin_sensor = [0, 0];
        report.tiles[0].rings[0].power_first = f32::NAN;
        assert!(report.validate().is_err());
    }
}
