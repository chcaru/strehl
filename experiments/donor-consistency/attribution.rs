// Artifact sink only. The optional core observer borrows finished state immutably.
use super::*;
use strehl_core::pyramid::LevelSize;
use strehl_core::pyramid::donor_consistency_diagnostic::{
    observe_attribution, AttributionField, AttributionWindow,
};

const REGIONS: [(&str, [usize; 4]); 2] = [
    ("facet-edges", [2500, 2700, 384, 384]),
    ("dark-inclusion", [3050, 1850, 384, 384]),
];

pub(super) struct Observer {
    directory: PathBuf,
    output: PathBuf,
    arms: Vec<serde_json::Value>,
}

fn key(field: AttributionField) -> (&'static str, Option<usize>) {
    match field {
        AttributionField::BaselineAc(k) => ("baseline-ac", Some(k)),
        AttributionField::RetainedAc(k) => ("retained-ac", Some(k)),
        AttributionField::DonorAc(k) => ("donor-ac", Some(k)),
        AttributionField::Base => ("base", None),
        AttributionField::BaselinePreHull => ("baseline-pre-hull", None),
        AttributionField::BaselinePostHull => ("baseline-post-hull", None),
        AttributionField::BaselineHullCorrection => ("baseline-hull-correction", None),
        AttributionField::PreHull => ("pre-hull", None),
        AttributionField::PostHull => ("post-hull", None),
        AttributionField::HullCorrection => ("hull-correction", None),
    }
}

impl Observer {
    pub(super) fn from_env(workspace: &Path, output: &Path) -> Result<Option<Self>> {
        let Some(directory) = std::env::var_os("STREHL_DONOR_ATTRIBUTION_DIR") else { return Ok(None); };
        let directory = PathBuf::from(directory);
        ensure!(directory.is_absolute() && !directory.exists(), "attribution directory must be new and absolute");
        ensure!(directory.parent().context("attribution parent")?.canonicalize()?
            .starts_with(workspace.join("experiments").canonicalize()?), "attribution must be below workspace experiments");
        std::fs::create_dir(&directory)?;
        Ok(Some(Self { directory, output: output.to_path_buf(), arms: Vec::new() }))
    }

    pub(super) fn record(&mut self, arm: &str, merge: &BandMerge, blend: &DonorBlend,
        sizes: &[LevelSize], delivered: &[Vec<f32>]) -> Result<()> {
        ensure!(matches!(arm, "candidate" | "late"), "unknown attribution arm");
        ensure!(delivered.len() == 4 && delivered.iter().all(|p| p.len() == sizes[0].pixels()),
            "attribution delivered shape differs");
        let arm_dir = self.directory.join(arm);
        std::fs::create_dir(&arm_dir)?;
        let windows = REGIONS.iter().map(|(_, r)| AttributionWindow {
            x: r[0] / 2, y: r[1] / 2, width: r[2] / 2, height: r[3] / 2,
        }).collect::<Vec<_>>();
        let mut artifacts = Vec::<serde_json::Value>::new();
        let mut failure = None;
        let summary = observe_attribution(merge, blend, &windows, &mut Workspace::new(sizes),
            |field, plane, region, values| {
                if failure.is_some() { return; }
                let result = (|| -> Result<()> {
                    let (name, level) = key(field);
                    let suffix = level.map_or_else(String::new, |k| format!("-{k}"));
                    let filename = format!("{}-{name}{suffix}.f32", REGIONS[region].0);
                    let path = arm_dir.join(&filename);
                    let mut file = if plane == 0 {
                        std::fs::OpenOptions::new().write(true).create_new(true).open(&path)?
                    } else {
                        let file = std::fs::OpenOptions::new().append(true).open(&path)?;
                        ensure!(file.metadata()?.len() == (plane * values.len() * 4) as u64,
                            "attribution plane order/length differs");
                        file
                    };
                    let mut bytes = Vec::with_capacity(values.len() * 4);
                    for &v in values { bytes.extend_from_slice(&v.to_bits().to_le_bytes()); }
                    file.write_all(&bytes)?;
                    drop(file);
                    if field == AttributionField::PostHull {
                        let w = windows[region];
                        for y in 0..w.height { for x in 0..w.width {
                            ensure!(values[y * w.width + x].to_bits()
                                == delivered[plane][(w.y + y) * sizes[0].width + w.x + x].to_bits(),
                                "observer post-hull window differs from actual delivered image");
                        }}
                    }
                    if plane == 3 {
                        artifacts.push(json!({"region":REGIONS[region].0,"field":name,"level":level,
                            "path":format!("{arm}/{filename}"),"shape":[4,windows[region].height,windows[region].width],
                            "sha256":file_hash(&path)?}));
                    }
                    Ok(())
                })();
                if let Err(error) = result { failure = Some(error); }
            });
        if let Some(error) = failure { return Err(error); }
        // Fixed pre-run arithmetic tolerance. This is not a photographic gate.
        ensure!(summary.baseline_sum_max_abs.iter().chain(&summary.mixed_sum_max_abs)
            .chain(&summary.baseline_hull_sum_max_abs).chain(&summary.mixed_hull_sum_max_abs)
            .all(|&v| v.is_finite() && v <= 0.02), "attribution reconstruction exceeds 0.02 source DN");
        self.arms.push(json!({"arm":arm,"summary":{
            "baseline_sum_max_abs":summary.baseline_sum_max_abs,
            "mixed_sum_max_abs":summary.mixed_sum_max_abs,
            "baseline_hull_sum_max_abs":summary.baseline_hull_sum_max_abs,
            "mixed_hull_sum_max_abs":summary.mixed_hull_sum_max_abs},
            "actual_delivered_windows_bit_exact":true,"artifacts":artifacts}));
        Ok(())
    }

    pub(super) fn finish(self, sizes: &[LevelSize]) -> Result<()> {
        ensure!(self.arms.len() == 2, "both prescribed and late arms required");
        write_json(&self.directory.join("receipt.json"), &json!({"schema":1,
            "source_output":self.output,"units":"signed black-subtracted source DN",
            "plane_order":["R","G1","G2","B"],"layout":"planar-y-x-f32le",
            "native_dimensions":[2*sizes[0].width,2*sizes[0].height],
            "level_sizes":sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),
            "windows":REGIONS.iter().map(|(name,r)|json!({"name":name,"native_xywh":r,
                "quad_xywh":[r[0]/2,r[1]/2,r[2]/2,r[3]/2]})).collect::<Vec<_>>(),
            "reconstruction_absolute_tolerance_dn":0.02,
            "scope":"actual full-context coefficient collapse then window extraction; before MHC, WB, tone and RGB development; signed terms are not ownership probabilities",
            "arms":self.arms}))
    }
}
