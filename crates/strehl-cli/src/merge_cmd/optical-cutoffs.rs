//! Stored diffraction-cutoff fits (subject, highlights and detail plan Q1).
//!
//! The optical restoration fits one aperture to every four-shot stack it
//! renders. On the A7CR glitter weevil that fit ran to its ceiling and the
//! stack was written unrestored, said only by one log line. The cutoff is a
//! property of the lens, its converter, the aperture and the magnification,
//! not of the subject, so a fit measured on another stack of the same gear at
//! a nearby focus position stands in for it: within about 5 % on the three
//! A7CR stacks that measured it (0.740, 0.768 and 0.776 cycles/px across focus
//! positions 16,120 to 31,741).
//!
//! Every measured fit is kept in a small JSON file in the engine's cache
//! folder ([`store_path`]: `optical-cutoffs.json` beside the warp maps, or in
//! `$STREHL_CACHE_DIR`), one record per capture folder, the newest replacing
//! an older one. [`SEEDS`] carries the fits read from the owner's render logs
//! before the store existed, so a stack that cannot measure its cutoff is
//! restored without first re-rendering another. A stored record for the same
//! capture replaces its seed.
//!
//! A fit is used only for the same body, the same composed optical path
//! (`LensType3`, which names the converter), the same f-number and the same
//! system model (with or without the gather kernel); of those, the nearest in
//! focus position, and only within [`MAX_FOCUS_DISTANCE`].
use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

pub(super) const STORE_FILE: &str = "optical-cutoffs.json";
const SCHEMA: &str = "strehl.optical-cutoffs.v1";

/// Largest focus-position distance (the camera's normalised focus units) at
/// which another stack's fit stands in. ARGUED from four A7CR fits with the
/// 100 mm macro and 2x converter at f/5.6: 0.768 at 16,120, 0.776 at 31,239
/// and 0.740 at 31,741 (15,600 units apart, within 5 %), but 0.588 at 61,812
/// (the lens's closest focus, 2.83x). Wide enough for the first three to
/// stand in for each other, too narrow for the closest-focus fit to stand in
/// for any of them.
pub(super) const MAX_FOCUS_DISTANCE: f64 = 16_000.0;

/// The system model a fit belongs to: the cutoff fitted with the gather
/// kernel divided out reads higher (`STREHL_OPTICAL_RESTORE_GATHER`).
pub(super) fn model_name(gather: bool) -> &'static str {
    if gather {
        "diffraction+gather"
    } else {
        "diffraction"
    }
}

/// What a fit is valid for, from the stack's first frame and its capture
/// manifest.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub(super) struct Gear {
    /// EXIF `Model`, verbatim.
    pub camera: String,
    /// Sony `LensType3`: the composed optical path, converter included.
    pub lens_type3: u16,
    /// EXIF `LensModel`, for people reading the store; not matched.
    pub lens_model: Option<String>,
    /// EXIF `FNumber`.
    pub f_number: f32,
    /// [`model_name`].
    pub model: String,
}

impl Gear {
    fn matches(&self, other: &Gear) -> bool {
        self.camera == other.camera
            && self.lens_type3 == other.lens_type3
            && (self.f_number - other.f_number).abs() < 0.05
            && self.model == other.model
    }
}

/// One stack's measured cutoff.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub(super) struct Fit {
    #[serde(flatten)]
    pub gear: Gear,
    /// Median of the capture's planned focus positions.
    pub focus: f64,
    /// The joint fit's green cutoff, cycles/px.
    pub green: f64,
    /// The joint fit's summed relative residual.
    pub residual: f64,
    /// In-focus tiles the fit used.
    pub tiles: usize,
    /// The capture folder's name.
    pub capture: String,
    /// `measured` (by a render), or where a seed was read.
    pub origin: String,
    /// The engine build that measured it.
    pub build: String,
    pub recorded_unix_ms: u64,
}

#[derive(Serialize, Deserialize)]
struct StoreFile {
    schema: String,
    fits: Vec<Fit>,
}

/// The store's location: `$STREHL_CACHE_DIR/optical-cutoffs.json`, else the
/// engine's default cache folder.
pub(super) fn store_path() -> PathBuf {
    crate::align_cmd::cache_root().join(STORE_FILE)
}

/// The fits stored at `path`; none when the file does not exist. A file that
/// cannot be read as the store is an error (the caller reports it and goes
/// on without the store).
pub(super) fn load(path: &Path) -> Result<Vec<Fit>> {
    let text = match std::fs::read_to_string(path) {
        Ok(t) => t,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
        Err(e) => return Err(e).with_context(|| format!("reading {}", path.display())),
    };
    let file: StoreFile =
        serde_json::from_str(&text).with_context(|| format!("parsing {}", path.display()))?;
    anyhow::ensure!(
        file.schema == SCHEMA,
        "{}: schema {:?}, expected {SCHEMA:?}",
        path.display(),
        file.schema
    );
    Ok(file.fits)
}

/// Add `fit` to the store at `path`, replacing any record for the same
/// capture and system model, and write it atomically (a temporary file
/// renamed over the old one). Two renders finishing at the same instant can
/// lose one record; the next render of that stack writes it again.
pub(super) fn record(path: &Path, fit: Fit) -> Result<()> {
    let mut fits = load(path)?;
    fits.retain(|f| !(f.capture == fit.capture && f.gear.model == fit.gear.model));
    fits.push(fit);
    let dir = path.parent().unwrap_or(Path::new("."));
    std::fs::create_dir_all(dir).with_context(|| format!("creating {}", dir.display()))?;
    let tmp = dir.join(format!(".{STORE_FILE}.{}.tmp", std::process::id()));
    std::fs::write(
        &tmp,
        serde_json::to_string_pretty(&StoreFile {
            schema: SCHEMA.into(),
            fits,
        })?,
    )
    .with_context(|| format!("writing {}", tmp.display()))?;
    if let Err(e) = std::fs::rename(&tmp, path) {
        let _ = std::fs::remove_file(&tmp);
        return Err(e).with_context(|| format!("replacing {}", path.display()));
    }
    Ok(())
}

/// Fits read from the owner's render logs (`C:/Users/chris/Pictures/Strehl/
/// strehl-*/render.log`, the "cutoffs R/G/B" line; MEASURED by those renders,
/// build 0.1.0-alpha.6) before the store existed. A7CR, FE 100mm F2.8 Macro
/// GM OSS + 2X Teleconverter (`LensType3` 33094), f/5.6, gather not in the
/// model. Focus: the median of each capture manifest's planned positions.
pub(super) const SEEDS: [(&str, f64, f64, f64, usize); 4] = [
    // (capture, focus, green cutoff, relative residual, tiles)
    ("stack-1795300522964-6430", 31_741.0, 0.740, 0.0278, 143),
    ("stack-1795371396674-6430", 16_120.5, 0.768, 0.0005, 190),
    ("stack-1795433406862-8651", 31_239.0, 0.776, 0.0003, 178),
    ("stack-1795476520452-8651", 61_812.0, 0.588, 0.0023, 99),
];

fn seeds() -> Vec<Fit> {
    SEEDS
        .iter()
        .map(|&(capture, focus, green, residual, tiles)| Fit {
            gear: Gear {
                camera: "ILCE-7CR".into(),
                lens_type3: 33094,
                lens_model: Some("FE 100mm F2.8 Macro GM OSS + 2X Teleconverter".into()),
                f_number: 5.6,
                model: model_name(false).into(),
            },
            focus,
            green,
            residual,
            tiles,
            capture: capture.into(),
            origin: "seed: the owner's render log of this capture".into(),
            build: "0.1.0-alpha.6".into(),
            recorded_unix_ms: 0,
        })
        .collect()
}

/// The stored fits with the seeds behind them (a stored record of a seed's
/// capture and model replaces the seed).
pub(super) fn candidates(stored: Vec<Fit>) -> Vec<Fit> {
    let mut all = stored;
    for seed in seeds() {
        if !all
            .iter()
            .any(|f| f.capture == seed.capture && f.gear.model == seed.gear.model)
        {
            all.push(seed);
        }
    }
    all
}

/// The fit to stand in for a stack of `gear` at `focus`, measured on another
/// capture (never `capture` itself): the same gear, the nearest focus
/// position within [`MAX_FOCUS_DISTANCE`], the newest on a tie.
pub(super) fn nearest<'a>(
    fits: &'a [Fit],
    gear: &Gear,
    focus: f64,
    capture: &str,
) -> Option<&'a Fit> {
    fits.iter()
        .filter(|f| f.gear.matches(gear) && f.capture != capture && f.green.is_finite())
        .filter(|f| (f.focus - focus).abs() <= MAX_FOCUS_DISTANCE)
        .min_by(|a, b| {
            (a.focus - focus)
                .abs()
                .total_cmp(&(b.focus - focus).abs())
                .then(b.recorded_unix_ms.cmp(&a.recorded_unix_ms))
        })
}

/// The median planned focus position in a capture folder's
/// `manifest.json` (`focus_positions`), if it records any.
pub(super) fn manifest_focus(capture: &Path) -> Option<f64> {
    let text = std::fs::read_to_string(capture.join("manifest.json")).ok()?;
    let v: serde_json::Value = serde_json::from_str(&text).ok()?;
    let mut f: Vec<f64> = v
        .get("focus_positions")?
        .as_array()?
        .iter()
        .filter_map(serde_json::Value::as_f64)
        .collect();
    if f.is_empty() {
        return None;
    }
    f.sort_by(f64::total_cmp);
    let n = f.len();
    Some(if n % 2 == 1 {
        f[n / 2]
    } else {
        0.5 * (f[n / 2 - 1] + f[n / 2])
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn gear() -> Gear {
        Gear {
            camera: "ILCE-7CR".into(),
            lens_type3: 33094,
            lens_model: None,
            f_number: 5.6,
            model: model_name(false).into(),
        }
    }

    fn fit(capture: &str, focus: f64, green: f64) -> Fit {
        Fit {
            gear: gear(),
            focus,
            green,
            residual: 0.001,
            tiles: 100,
            capture: capture.into(),
            origin: "measured".into(),
            build: "test".into(),
            recorded_unix_ms: 1,
        }
    }

    fn scratch(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "strehl-optical-cutoffs-{name}-{}",
            std::process::id()
        ));
        let _ = std::fs::remove_dir_all(&dir);
        dir
    }

    /// The weevil (focus 25,175) takes the lanternfly's fit (31,239), the
    /// nearest of the seeds; the closest-focus fit is out of reach.
    #[test]
    fn the_seeds_give_the_weevil_the_nearest_fit() {
        let all = candidates(Vec::new());
        let got = nearest(&all, &gear(), 25_175.0, "stack-1795460665629-8651").unwrap();
        assert_eq!(got.capture, "stack-1795433406862-8651");
        assert_eq!(got.green, 0.776);
        // A stack at the closest focus finds only its own seed, which it may
        // not use.
        assert!(nearest(&all, &gear(), 61_812.0, "stack-1795476520452-8651").is_none());
    }

    /// Other gear, another aperture or the other system model never match.
    #[test]
    fn only_the_same_gear_stands_in() {
        let all = vec![fit("a", 30_000.0, 0.7)];
        for change in 0..4 {
            let mut g = gear();
            match change {
                0 => g.camera = "ILCE-7CM2".into(),
                1 => g.lens_type3 = 32893,
                2 => g.f_number = 8.0,
                _ => g.model = model_name(true).into(),
            }
            assert!(nearest(&all, &g, 30_000.0, "b").is_none(), "{change}");
        }
        assert!(nearest(&all, &gear(), 30_000.0, "b").is_some());
    }

    /// Stored, reloaded and replaced per capture; the seeds stay behind a
    /// stored record of their capture.
    #[test]
    fn the_store_keeps_one_record_per_capture() {
        let dir = scratch("store");
        let path = dir.join(STORE_FILE);
        assert!(load(&path).unwrap().is_empty());
        record(&path, fit("x", 20_000.0, 0.70)).unwrap();
        record(&path, fit("y", 40_000.0, 0.60)).unwrap();
        record(&path, fit("x", 20_000.0, 0.72)).unwrap();
        let back = load(&path).unwrap();
        assert_eq!(back.len(), 2);
        assert_eq!(back.iter().find(|f| f.capture == "x").unwrap().green, 0.72);
        let leftovers: Vec<_> = std::fs::read_dir(&dir)
            .unwrap()
            .filter_map(|e| e.ok())
            .filter(|e| e.file_name() != STORE_FILE)
            .collect();
        assert!(leftovers.is_empty(), "no temporary left behind");
        let replaced = candidates(vec![fit("stack-1795433406862-8651", 31_239.0, 0.70)]);
        assert_eq!(replaced.len(), SEEDS.len());
        assert_eq!(
            replaced
                .iter()
                .find(|f| f.capture == "stack-1795433406862-8651")
                .unwrap()
                .green,
            0.70
        );
        std::fs::write(&path, "{\"schema\":\"other\",\"fits\":[]}").unwrap();
        assert!(load(&path).is_err());
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn the_manifest_gives_the_median_focus() {
        let dir = scratch("manifest");
        std::fs::create_dir_all(&dir).unwrap();
        assert_eq!(manifest_focus(&dir), None);
        std::fs::write(
            dir.join("manifest.json"),
            "{\"focus_positions\":[10,40,20,30]}",
        )
        .unwrap();
        assert_eq!(manifest_focus(&dir), Some(25.0));
        let _ = std::fs::remove_dir_all(&dir);
    }
}
