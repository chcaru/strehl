use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};

#[path = "spatial.rs"]
mod spatial;
pub use spatial::{
    AdaptiveParameters, AdaptiveToneRange, MAX_SPATIAL_TREATMENTS, SpatialTreatment,
};

#[path = "recipe-finishing.rs"]
mod finishing;
pub use finishing::{
    Backdrop, BackdropKey, Crop, Heal, MAX_HEALS, ScaleBar, ScaleBarCorner, ScaleBarStyle,
};

#[path = "recipe-prepared.rs"]
mod prepared;
pub(crate) use prepared::{PixelRecipe, feathered as feathered_weight};
pub use prepared::{PreparedRecipe, PreparedShape};

/// Points in one depth-brush stroke, after simplification.
pub const MAX_STROKE_POINTS: usize = 1024;
/// Stroke points in one recipe, keeping it far below the engine's 1 MiB cap.
pub const MAX_RECIPE_STROKE_POINTS: usize = 4096;

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
    Ellipse {
        center: [f32; 2],
        radius: [f32; 2],
    },
    Rectangle {
        min: [f32; 2],
        max: [f32; 2],
    },
    Polygon {
        points: Vec<[f32; 2]>,
    },
    /// A brush stroke: every point within `radius` of the polyline, with the
    /// region's feather as a fraction of the radius. Radii are per axis like
    /// an ellipse's, so a brush round in pixels has `rx * width == ry * height`.
    /// This is the depth brush's mask; with `source_range` it is a repair.
    Stroke {
        points: Vec<[f32; 2]>,
        radius: [f32; 2],
    },
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
    // Macro finishing (P7). Each is omitted when unused, so a recipe without
    // them serializes byte-identically to earlier builds, which read it.
    /// Crop and straighten; applied by export through mapped coordinates.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub crop: Option<Crop>,
    /// Scale bar design; its calibration comes from the subject's lens.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub scale_bar: Option<ScaleBar>,
    /// Neighbourhood stage before `apply_pixel`: heals, then backdrop.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub heals: Vec<Heal>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub backdrop: Option<Backdrop>,
    /// Tone application order of region ids. Regions not listed follow in
    /// list order. The list order stays the engine's repair-blend order, so
    /// reordering layers never invalidates a rebuilt master.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub layers_order: Vec<String>,
}

impl Default for DevelopmentRecipe {
    fn default() -> Self {
        Self {
            version: 1,
            global: Adjustments::default(),
            regions: Vec::new(),
            hdr: HdrSettings::default(),
            spatial: Vec::new(),
            crop: None,
            scale_bar: None,
            heals: Vec::new(),
            backdrop: None,
            layers_order: Vec::new(),
        }
    }
}

pub(crate) fn bounded(value: f32, min: f32, max: f32, field: &str) -> Result<()> {
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
            Self::Stroke { points, radius } => {
                let mut min = [1.0f32; 2];
                let mut max = [0.0f32; 2];
                for p in points {
                    for c in 0..2 {
                        min[c] = min[c].min((p[c] - radius[c]).max(0.0));
                        max[c] = max[c].max((p[c] + radius[c]).min(1.0));
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
            Self::Stroke { points, radius } => {
                ensure!(
                    (1..=MAX_STROKE_POINTS).contains(&points.len()),
                    "a stroke needs 1..{MAX_STROKE_POINTS} points; simplify it with stroke_from_path"
                );
                for p in points {
                    point(*p)?;
                }
                bounded(radius[0], 0.0001, 0.5, "stroke radius x")?;
                bounded(radius[1], 0.0001, 0.5, "stroke radius y")?;
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
            Self::Stroke { points, radius } => {
                1.0 - prepared::stroke_distance(points, *radius, point)
            }
        };
        prepared::feathered(d, feather)
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
        let stroke_points: usize = self
            .regions
            .iter()
            .map(|r| match &r.shape {
                RegionShape::Stroke { points, .. } => points.len(),
                _ => 0,
            })
            .sum();
        ensure!(
            stroke_points <= MAX_RECIPE_STROKE_POINTS,
            "at most {MAX_RECIPE_STROKE_POINTS} stroke points are supported in one recipe"
        );
        let mut listed = std::collections::HashSet::new();
        for id in &self.layers_order {
            ensure!(
                ids.contains(id) && listed.insert(id),
                "layer order must list existing region IDs at most once"
            );
        }
        if let Some(crop) = &self.crop {
            crop.validate()?;
        }
        if let Some(bar) = &self.scale_bar {
            bar.validate()?;
        }
        ensure!(
            self.heals.len() <= MAX_HEALS,
            "at most {MAX_HEALS} heals are supported"
        );
        for heal in &self.heals {
            heal.validate()?;
        }
        if let Some(backdrop) = &self.backdrop {
            backdrop.validate()?;
        }
        Ok(())
    }

    /// Prefer `prepare` in any loop: with an explicit layer order, or with
    /// polygon and stroke regions, this per-call form repeats that work.
    pub fn apply_pixel(&self, rgb: [f32; 3], uv: [f32; 2]) -> [f32; 3] {
        if !self.layers_order.is_empty() {
            return self.prepare().apply_pixel(rgb, uv);
        }
        let mut v = self.global.apply(rgb, 1.0);
        for region in &self.regions {
            // Rejection is exact: outside its box a region's weight is 0, at
            // which `Adjustments::apply` returns its input unchanged.
            if region.enabled
                && region.adjustments != Adjustments::default()
                && !region.shape.cheap_reject(uv)
            {
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

    /// Culling boxes and layer order, computed once for a render loop.
    pub fn prepare(&self) -> PreparedRecipe<'_> {
        PreparedRecipe::new(self)
    }

    /// Indices into `regions` in tone application order: `layers_order`
    /// first, then unlisted regions in list order.
    pub fn application_order(&self) -> Vec<usize> {
        if self.layers_order.is_empty() {
            return (0..self.regions.len()).collect();
        }
        let mut order: Vec<usize> = self
            .layers_order
            .iter()
            .filter_map(|id| self.regions.iter().position(|r| &r.id == id))
            .collect();
        let listed: std::collections::HashSet<usize> = order.iter().copied().collect();
        order.extend((0..self.regions.len()).filter(|i| !listed.contains(i)));
        order
    }

    /// Move a layer to `index` in the application order, making the full
    /// order explicit. Repair-blend (list) order is unchanged.
    pub fn move_layer(&mut self, id: &str, index: usize) -> Result<()> {
        let mut order: Vec<String> = self
            .application_order()
            .into_iter()
            .map(|i| self.regions[i].id.clone())
            .collect();
        let from = order
            .iter()
            .position(|x| x == id)
            .ok_or_else(|| anyhow::anyhow!("no region {id:?}"))?;
        let moved = order.remove(from);
        order.insert(index.min(order.len()), moved);
        let list_order = order.iter().zip(&self.regions).all(|(a, r)| a == &r.id);
        self.layers_order = if list_order { Vec::new() } else { order };
        Ok(())
    }

    /// The recipe an existing master exports while a repair waits for its
    /// re-stack: tone as it is now, with exactly the source-range repairs the
    /// master holds (`baked`). Pending repairs keep their tone and lose their
    /// range; a baked repair the recipe disabled or deleted comes back as a
    /// neutral region, because its pixels cannot be unbaked. Tone order is
    /// kept through `layers_order` when the repairs have to move in the list.
    pub fn with_baked_repairs(&self, baked: Option<&DevelopmentRecipe>) -> Self {
        let held: Vec<&RegionAdjustment> = baked
            .map(|b| {
                b.regions
                    .iter()
                    .filter(|r| r.enabled && r.source_range.is_some())
                    .collect()
            })
            .unwrap_or_default();
        let order: Vec<String> = self
            .application_order()
            .into_iter()
            .map(|i| self.regions[i].id.clone())
            .collect();
        let mut recipe = self.clone();
        for region in &mut recipe.regions {
            match held.iter().find(|b| b.id == region.id) {
                Some(b) => {
                    if !region.enabled {
                        region.adjustments = Adjustments::default();
                    }
                    region.enabled = true;
                    region.shape = b.shape.clone();
                    region.feather = b.feather;
                    region.source_range = b.source_range.clone();
                }
                None => region.source_range = None,
            }
        }
        for b in &held {
            if !recipe.regions.iter().any(|r| r.id == b.id) {
                recipe.regions.push(RegionAdjustment {
                    adjustments: Adjustments::default(),
                    note: String::new(),
                    ..(*b).clone()
                });
            }
        }
        // The engine's equality key compares repairs among themselves in list
        // order: reorder them within their own slots, leaving the rest alone.
        let rank = |r: &RegionAdjustment| held.iter().position(|b| b.id == r.id);
        let slots: Vec<usize> = (0..recipe.regions.len())
            .filter(|&i| rank(&recipe.regions[i]).is_some())
            .collect();
        let mut repairs: Vec<RegionAdjustment> =
            slots.iter().map(|&i| recipe.regions[i].clone()).collect();
        repairs.sort_by_key(|r| rank(r));
        for (slot, region) in slots.into_iter().zip(repairs) {
            recipe.regions[slot] = region;
        }
        let listed = recipe.regions.iter().map(|r| &r.id);
        if !recipe.layers_order.is_empty() || !listed.eq(order.iter()) {
            recipe.layers_order = order;
        }
        recipe
    }

    /// Remove a region with its layer entry and any Adaptive scope on it.
    pub fn remove_region(&mut self, id: &str) -> Option<RegionAdjustment> {
        let index = self.regions.iter().position(|r| r.id == id)?;
        self.layers_order.retain(|x| x != id);
        self.clear_adaptive_scope(Some(id));
        Some(self.regions.remove(index))
    }

    /// True when the recipe uses a field earlier builds cannot read: they
    /// refuse such a file and fall back to the master's baked recipe.
    pub fn uses_finishing(&self) -> bool {
        self.crop.is_some()
            || self.scale_bar.is_some()
            || !self.heals.is_empty()
            || self.backdrop.is_some()
            || !self.layers_order.is_empty()
            || self
                .regions
                .iter()
                .any(|r| matches!(r.shape, RegionShape::Stroke { .. }))
    }

    /// The neighbourhood stage (heals, backdrop) has work to do. It runs on
    /// the photograph's samples, so `apply_pixel` never applies it; the image
    /// renderers and the export do.
    pub fn has_neighbourhood(&self) -> bool {
        self.heals.iter().any(|h| h.enabled) || self.backdrop.is_some_and(|b| b.enabled)
    }

    /// For samples that have already been through the neighbourhood stage.
    pub fn without_neighbourhood(&self) -> Self {
        let mut recipe = self.clone();
        recipe.heals.clear();
        recipe.backdrop = None;
        recipe
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
