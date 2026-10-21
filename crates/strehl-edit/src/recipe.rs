use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};

#[path = "spatial.rs"]
mod spatial;
pub use spatial::{AdaptiveParameters, MAX_SPATIAL_TREATMENTS, SpatialTreatment};

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize, Default)]
#[serde(default, deny_unknown_fields)]
pub struct Adjustments {
    /// Stops, -8..8.
    pub exposure: f32,
    /// All remaining controls use -100..100. Zero is neutral.
    pub contrast: f32,
    pub highlights: f32,
    pub shadows: f32,
    pub whites: f32,
    pub blacks: f32,
    pub vibrance: f32,
    pub saturation: f32,
    /// Relative warm/cool correction, not an absolute Kelvin measurement.
    pub temperature: f32,
    pub tint: f32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum RegionShape {
    Ellipse { center: [f32; 2], radius: [f32; 2] },
    Rectangle { min: [f32; 2], max: [f32; 2] },
    Polygon { points: Vec<[f32; 2]> },
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SourceRange {
    /// Inclusive, zero-based indices in the capture's filename order.
    pub first: usize,
    pub last: usize,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RegionAdjustment {
    pub id: String,
    pub name: String,
    #[serde(default)]
    pub note: String,
    pub shape: RegionShape,
    /// Inner feather fraction of the region's radius (0 = hard, 1 = fully feathered).
    pub feather: f32,
    pub enabled: bool,
    #[serde(default)]
    pub adjustments: Adjustments,
    /// Rebuild request, consumed by the stacking engine, never by a tone adjustment.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub source_range: Option<SourceRange>,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct HdrSettings {
    /// 1.0 scene-linear becomes this luminance. BT.2408 reference white is 203 nits.
    pub reference_white_nits: f32,
    pub peak_nits: f32,
    /// 1..100; higher is less AV1 quantization.
    pub quality: u8,
    /// 0..10; larger is faster.
    pub speed: u8,
}

impl Default for HdrSettings {
    fn default() -> Self {
        Self {
            reference_white_nits: 203.0,
            peak_nits: 1000.0,
            quality: 100,
            speed: 6,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct DevelopmentRecipe {
    pub version: u32,
    pub global: Adjustments,
    pub regions: Vec<RegionAdjustment>,
    pub hdr: HdrSettings,
    /// Image-specific curves, separate from portable preset parameters.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub spatial: Vec<SpatialTreatment>,
}

impl Default for DevelopmentRecipe {
    fn default() -> Self {
        Self {
            version: 1,
            global: Adjustments::default(),
            regions: Vec::new(),
            hdr: HdrSettings::default(),
            spatial: Vec::new(),
        }
    }
}

fn bounded(value: f32, min: f32, max: f32, field: &str) -> Result<()> {
    ensure!(
        value.is_finite() && (min..=max).contains(&value),
        "{field} must be finite and in {min}..={max}"
    );
    Ok(())
}

impl Adjustments {
    pub fn validate(&self) -> Result<()> {
        bounded(self.exposure, -8.0, 8.0, "exposure")?;
        for (name, v) in [
            ("contrast", self.contrast),
            ("highlights", self.highlights),
            ("shadows", self.shadows),
            ("whites", self.whites),
            ("blacks", self.blacks),
            ("vibrance", self.vibrance),
            ("saturation", self.saturation),
            ("temperature", self.temperature),
            ("tint", self.tint),
        ] {
            bounded(v, -100.0, 100.0, name)?;
        }
        Ok(())
    }

    /// Linear-light adjustment. No upper clamp: highlight headroom survives.
    pub fn apply(&self, rgb: [f32; 3], amount: f32) -> [f32; 3] {
        if *self == Self::default() || amount <= 0.0 {
            return rgb;
        }
        let a = amount.clamp(0.0, 1.0);
        let gain = (self.exposure * a).exp2();
        let warm = (self.temperature * a * 0.005).exp2();
        let green = (-self.tint * a * 0.005).exp2();
        let mut v = [
            rgb[0] * gain * warm,
            rgb[1] * gain * green,
            rgb[2] * gain / warm,
        ];
        let y = luma(v).max(0.0);
        if y > 1e-12 {
            // Smooth luminance masks, independent of channel hue.
            let t = y / (y + 0.18);
            let stops = a
                * (self.shadows * (1.0 - t).powi(2)
                    + self.highlights * t.powi(2)
                    + self.blacks * (1.0 - t).powi(6)
                    + self.whites * t.powi(6))
                * 0.02;
            let contrast = (self.contrast * a * 0.005).exp2();
            let mapped = 0.18 * (y / 0.18).powf(contrast) * stops.exp2();
            let scale = mapped / y;
            v = v.map(|x| x * scale);
        }
        let y = luma(v);
        let max = v.into_iter().fold(0.0f32, f32::max);
        let min = v.into_iter().fold(f32::MAX, f32::min);
        let chroma = if max > 1e-8 { (max - min) / max } else { 0.0 };
        let sat = (1.0 + self.saturation * a * 0.01).max(0.0)
            * (1.0 + self.vibrance * a * 0.01 * (1.0 - chroma).clamp(0.0, 1.0)).max(0.0);
        v.map(|c| y + (c - y) * sat)
    }
}

pub(crate) fn luma(v: [f32; 3]) -> f32 {
    0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
}

impl RegionShape {
    pub fn bounds(&self) -> ([f32; 2], [f32; 2]) {
        match self {
            Self::Ellipse { center, radius } => (
                [
                    (center[0] - radius[0]).max(0.0),
                    (center[1] - radius[1]).max(0.0),
                ],
                [
                    (center[0] + radius[0]).min(1.0),
                    (center[1] + radius[1]).min(1.0),
                ],
            ),
            Self::Rectangle { min, max } => (*min, *max),
            Self::Polygon { points } => {
                let mut min = [1.0f32; 2];
                let mut max = [0.0f32; 2];
                for p in points {
                    for c in 0..2 {
                        min[c] = min[c].min(p[c]);
                        max[c] = max[c].max(p[c]);
                    }
                }
                (min, max)
            }
        }
    }

    pub fn contains(&self, point: [f32; 2]) -> bool {
        self.weight(point, 0.0) > 0.0
    }

    pub fn validate(&self) -> Result<()> {
        let point = |p: [f32; 2]| -> Result<()> {
            bounded(p[0], 0.0, 1.0, "region x")?;
            bounded(p[1], 0.0, 1.0, "region y")
        };
        match self {
            Self::Ellipse { center, radius } => {
                point(*center)?;
                bounded(radius[0], 0.0001, 1.0, "region radius x")?;
                bounded(radius[1], 0.0001, 1.0, "region radius y")?;
            }
            Self::Rectangle { min, max } => {
                point(*min)?;
                point(*max)?;
                ensure!(
                    max[0] > min[0] && max[1] > min[1],
                    "region rectangle must have positive area"
                );
            }
            Self::Polygon { points } => {
                ensure!(
                    (3..=256).contains(&points.len()),
                    "polygon needs 3..256 points"
                );
                for p in points {
                    point(*p)?;
                }
                let area = points
                    .iter()
                    .zip(points.iter().cycle().skip(1))
                    .map(|(a, b)| a[0] * b[1] - a[1] * b[0])
                    .sum::<f32>()
                    .abs();
                ensure!(area > 1e-8, "polygon must have nonzero area");
            }
        }
        Ok(())
    }

    /// Pixel-centre normalized coordinates; resolution independent.
    pub fn weight(&self, point: [f32; 2], feather: f32) -> f32 {
        let d = match self {
            Self::Ellipse { center, radius } => {
                let x = (point[0] - center[0]) / radius[0];
                let y = (point[1] - center[1]) / radius[1];
                1.0 - x.hypot(y)
            }
            Self::Rectangle { min, max } => {
                let c = [(min[0] + max[0]) * 0.5, (min[1] + max[1]) * 0.5];
                let r = [(max[0] - min[0]) * 0.5, (max[1] - min[1]) * 0.5];
                1.0 - ((point[0] - c[0]) / r[0])
                    .abs()
                    .max(((point[1] - c[1]) / r[1]).abs())
            }
            Self::Polygon { points } => {
                let mut inside = false;
                let mut dist = f32::MAX;
                let mut min = [1.0f32; 2];
                let mut max = [0.0f32; 2];
                for (&a, &b) in points.iter().zip(points.iter().cycle().skip(1)) {
                    min = [min[0].min(a[0]), min[1].min(a[1])];
                    max = [max[0].max(a[0]), max[1].max(a[1])];
                    if (a[1] > point[1]) != (b[1] > point[1])
                        && point[0] < (b[0] - a[0]) * (point[1] - a[1]) / (b[1] - a[1]) + a[0]
                    {
                        inside = !inside;
                    }
                    let dx = b[0] - a[0];
                    let dy = b[1] - a[1];
                    let t = ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy)
                        / (dx * dx + dy * dy).max(1e-20);
                    dist = dist.min(
                        (point[0] - a[0] - t.clamp(0.0, 1.0) * dx)
                            .hypot(point[1] - a[1] - t.clamp(0.0, 1.0) * dy),
                    );
                }
                if !inside {
                    return 0.0;
                }
                dist / ((max[0] - min[0]).min(max[1] - min[1]) * 0.5).max(1e-6)
            }
        };
        if d <= 0.0 {
            return 0.0;
        }
        if feather <= 0.0 {
            return 1.0;
        }
        let t = (d / feather).clamp(0.0, 1.0);
        t * t * (3.0 - 2.0 * t)
    }
}

impl HdrSettings {
    pub fn validate(&self) -> Result<()> {
        bounded(self.reference_white_nits, 80.0, 500.0, "reference white")?;
        bounded(
            self.peak_nits,
            self.reference_white_nits,
            10_000.0,
            "HDR peak",
        )?;
        ensure!((1..=100).contains(&self.quality), "quality must be 1..100");
        ensure!(self.speed <= 10, "speed must be 0..10");
        Ok(())
    }
}

impl DevelopmentRecipe {
    pub fn validate(&self) -> Result<()> {
        ensure!(
            self.version == 1,
            "unsupported development recipe version {}",
            self.version
        );
        self.global.validate()?;
        self.hdr.validate()?;
        ensure!(
            self.spatial.len() <= MAX_SPATIAL_TREATMENTS,
            "at most {MAX_SPATIAL_TREATMENTS} spatial treatments are supported"
        );
        let mut scopes = std::collections::HashSet::new();
        for field in &self.spatial {
            field.validate()?;
            ensure!(
                scopes.insert(field.target_region.as_deref()),
                "spatial treatment scopes must be unique"
            );
        }
        ensure!(
            self.regions.len() <= 128,
            "at most 128 regions are supported"
        );
        let mut ids = std::collections::HashSet::new();
        for r in &self.regions {
            ensure!(
                !r.id.is_empty() && r.id.len() <= 128 && ids.insert(&r.id),
                "region IDs must be unique and 1..128 bytes"
            );
            ensure!(
                r.name.len() <= 256 && r.note.len() <= 4096,
                "region name/note is too long"
            );
            r.shape.validate()?;
            bounded(r.feather, 0.0, 1.0, "feather")?;
            r.adjustments.validate()?;
            if let Some(range) = &r.source_range {
                ensure!(
                    range.first <= range.last && range.last < 1_000_000,
                    "source range must be ordered and use zero-based frame indices"
                );
            }
        }
        for field in &self.spatial {
            ensure!(
                field
                    .target_region
                    .as_ref()
                    .is_none_or(|id| ids.contains(id)),
                "spatial treatment refers to a missing region"
            );
        }
        Ok(())
    }

    pub fn apply_pixel(&self, rgb: [f32; 3], uv: [f32; 2]) -> [f32; 3] {
        let mut v = self.global.apply(rgb, 1.0);
        for region in &self.regions {
            if region.enabled && region.adjustments != Adjustments::default() {
                v = region
                    .adjustments
                    .apply(v, region.shape.weight(uv, region.feather));
            }
        }
        for treatment in &self.spatial {
            let weight = match treatment.target_region.as_deref() {
                None => 1.0,
                Some(id) => self
                    .regions
                    .iter()
                    .find(|r| r.id == id && r.enabled)
                    .map_or(0.0, |r| r.shape.weight(uv, r.feather)),
            };
            v = treatment.apply(v, uv, weight);
        }
        v
    }

    pub fn clear_adaptive_scope(&mut self, target: Option<&str>) {
        self.spatial
            .retain(|field| field.target_region.as_deref() != target);
    }

    pub fn adaptive_scope(&self, target: Option<&str>) -> Option<&SpatialTreatment> {
        self.spatial
            .iter()
            .find(|field| field.target_region.as_deref() == target)
    }

    pub fn has_source_repairs(&self) -> bool {
        self.regions
            .iter()
            .any(|r| r.enabled && r.source_range.is_some())
    }

    /// For a master whose source-range repairs have already been rebuilt.
    /// The caller must retain the original full recipe in the run provenance.
    pub fn without_source_repairs(&self) -> Self {
        let mut recipe = self.clone();
        for region in &mut recipe.regions {
            region.source_range = None;
        }
        recipe
    }
}
