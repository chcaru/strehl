use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};

/// Normalized camera commands, not lens encoder counts or metric distances.
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct Plan {
    pub start: u16,
    pub end: u16,
    pub step: u16,
    pub settle_ms: u32,
    pub approach: u16,
    pub capture_timeout_s: u32,
    /// The subject's outline (plan S1), written into each capture's
    /// manifest with the plan. Omitted when none was given, so older
    /// desktops and manifests read as before.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub subject: Option<Subject>,
    /// Highlight groups (plan X3): a shorter group after the base group at
    /// chosen planes, for the highlights the base exposure pins. Omitted
    /// when off.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub highlight: Option<Highlight>,
}

/// The lens's travel as found: the ends it stopped at when sent past them,
/// widened when it later lands beyond one (another lens, or a stall taken
/// for an end). `None` where an end has not been met; the camera's own
/// property admits 0 to 65535 whatever the lens (MEASURED 2026-11-24: the
/// owner's lens travels 1509 to 63487).
#[derive(Clone, Copy, Debug, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct LensTravel {
    /// The lowest focus number the lens reaches (the rail's Near end).
    pub near: Option<u16>,
    /// The highest (the rail's Far end).
    pub far: Option<u16>,
}

impl LensTravel {
    /// A manual move stopped short at `at` going towards Far (or Near):
    /// that end. True when it changed.
    pub fn stopped(&mut self, towards_far: bool, at: u16) -> bool {
        let end = if towards_far {
            &mut self.far
        } else {
            &mut self.near
        };
        let changed = *end != Some(at);
        *end = Some(at);
        changed
    }
    /// The lens landed at `p`: an end it is beyond moves out to it. True
    /// when it changed.
    pub fn landed(&mut self, p: u16) -> bool {
        let mut changed = false;
        if self.far.is_some_and(|f| p > f) {
            self.far = Some(p);
            changed = true;
        }
        if self.near.is_some_and(|n| p < n) {
            self.near = Some(p);
            changed = true;
        }
        changed
    }
    /// A manual move's target from `from`: kept at an end it would cross
    /// from inside the travel. From the end itself the move goes to the lens
    /// as asked, so a lens that travels further (another one) is found.
    pub fn keep_inside(&self, from: u16, target: u16) -> u16 {
        match (self.near, self.far) {
            (_, Some(far)) if from < far && target > far => far,
            (Some(near), _) if from > near && target < near => near,
            _ => target,
        }
    }
    /// The first position past an end, if any, with that end's name.
    pub fn outside(
        &self,
        positions: impl IntoIterator<Item = u16>,
    ) -> Option<(u16, &'static str, u16)> {
        positions
            .into_iter()
            .find_map(|p| match (self.near, self.far) {
                (_, Some(far)) if p > far => Some((p, "far", far)),
                (Some(near), _) if p < near => Some((p, "near", near)),
                _ => None,
            })
    }
    /// From a file the controller keeps (`lens-travel.json`); none when it
    /// is missing or unreadable.
    pub fn load(path: &std::path::Path) -> Self {
        std::fs::read(path)
            .ok()
            .and_then(|b| serde_json::from_slice(&b).ok())
            .unwrap_or_default()
    }
    pub fn save(&self, path: &std::path::Path) -> Result<()> {
        let temp = path.with_extension("json.tmp");
        std::fs::write(&temp, serde_json::to_vec_pretty(self)?)?;
        std::fs::rename(&temp, path)?;
        Ok(())
    }
}

/// Where and how highlight groups are taken (plan X3; the format in
/// `experiments/subject-highlights-detail-2026-11-23/impl/tiers.md`).
#[derive(Clone, Copy, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct Highlight {
    /// The camera's ShutterSpeed property value for the highlight groups.
    pub shutter: u64,
    /// A highlight group at every plane (1) or every second (2), and so on,
    /// counted from `first_plane`.
    pub every: u16,
    /// Plane numbers (as files carry them, 1-based) the groups span.
    pub first_plane: u32,
    pub last_plane: u32,
    /// RAWs a highlight group: 4 (the owner's decision) or 1.
    pub shots: u8,
}

impl Highlight {
    pub fn validate(&self) -> Result<()> {
        ensure!(
            (1..=16).contains(&self.every),
            "Highlight groups come every 1 to 16 planes"
        );
        ensure!(
            self.first_plane >= 1 && self.last_plane >= self.first_plane,
            "Highlight groups need a first and last plane"
        );
        ensure!(
            matches!(self.shots, 1 | 4),
            "A highlight group is one or four RAWs"
        );
        ensure!(self.shutter != 0, "Choose the highlight groups' shutter");
        Ok(())
    }
    /// Whether plane `plane` (1-based) takes a highlight group.
    pub fn applies(&self, plane: u64) -> bool {
        let (first, last) = (u64::from(self.first_plane), u64::from(self.last_plane));
        (first..=last).contains(&plane) && (plane - first).is_multiple_of(u64::from(self.every))
    }
}

/// The subject: outer rings and holes (even-odd), normalised to the
/// sensor's active area (live view shows that same area), at most
/// [`Subject::MAX_POINTS`] points a ring (`strehl_edit`'s polygon limit),
/// with where it was drawn and how it was made.
#[derive(Clone, Debug, Default, Serialize, Deserialize, PartialEq)]
pub struct Subject {
    pub rings: Vec<Vec<[f32; 2]>>,
    /// The focus position the outline was drawn or found at.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reference_focus: Option<u16>,
    /// Magnification change per focus unit, in parts per million, to map
    /// the outline to other planes (the weevil reads about -13).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rate_ppm: Option<f32>,
    /// "manual", "box" or "auto", with the automatic settings and strokes.
    #[serde(default)]
    pub provenance: serde_json::Value,
}

impl Subject {
    pub const MAX_RINGS: usize = 64;
    pub const MAX_POINTS: usize = 256;

    pub fn validate(&self) -> Result<()> {
        ensure!(
            (1..=Self::MAX_RINGS).contains(&self.rings.len()),
            "A subject has 1 to {} rings",
            Self::MAX_RINGS
        );
        for ring in &self.rings {
            ensure!(
                (3..=Self::MAX_POINTS).contains(&ring.len()),
                "A subject's ring has 3 to {} points",
                Self::MAX_POINTS
            );
            ensure!(
                ring.iter()
                    .flatten()
                    .all(|v| v.is_finite() && (-0.001..=1.001).contains(v)),
                "A subject's points lie within the frame"
            );
        }
        if let Some(rate) = self.rate_ppm {
            ensure!(
                rate.is_finite() && rate.abs() <= 10_000.0,
                "Invalid magnification rate"
            );
        }
        Ok(())
    }

    /// The rectangle around every ring, at least 5 % a side: the subject
    /// box older clients and the camera's magnifier use.
    pub fn bounding_box(&self) -> Roi {
        let (mut x0, mut y0, mut x1, mut y1) = (1.0f32, 1.0f32, 0.0f32, 0.0f32);
        for [x, y] in self.rings.iter().flatten() {
            x0 = x0.min(*x);
            y0 = y0.min(*y);
            x1 = x1.max(*x);
            y1 = y1.max(*y);
        }
        let (x0, y0) = (x0.clamp(0.0, 0.95), y0.clamp(0.0, 0.95));
        let width = (x1.clamp(0.0, 1.0) - x0).max(0.05).min(1.0 - x0);
        let height = (y1.clamp(0.0, 1.0) - y0).max(0.05).min(1.0 - y0);
        Roi {
            x: x0,
            y: y0,
            width,
            height,
        }
    }
}

impl Default for Plan {
    fn default() -> Self {
        Self {
            start: 0,
            end: 0,
            step: 1,
            settle_ms: 500,
            approach: 128,
            capture_timeout_s: 120,
            subject: None,
            highlight: None,
        }
    }
}

impl Plan {
    pub fn validate(&self) -> Result<()> {
        if let Some(subject) = &self.subject {
            subject.validate()?;
        }
        if let Some(highlight) = &self.highlight {
            highlight.validate()?;
        }
        ensure!(
            self.step > 0,
            "Step must be at least one camera command unit"
        );
        ensure!(
            (100..=30000).contains(&self.settle_ms),
            "Settle time must be 100–30000 ms"
        );
        ensure!(
            (5..=3600).contains(&self.capture_timeout_s),
            "Exposure timeout must be 5–3600 seconds"
        );
        ensure!(
            (1..=4096).contains(&self.approach),
            "Approach must be 1–4096 units"
        );
        self.prestart()?;
        Ok(())
    }
    pub fn direction(&self) -> i32 {
        if self.end >= self.start { 1 } else { -1 }
    }
    pub fn prestart(&self) -> Result<u16> {
        let target = i32::from(self.start) - self.direction() * i32::from(self.approach);
        ensure!(
            (0..=65535).contains(&target),
            "Start is too close to the lens limit for the approach distance; shorten Approach or move the start mark"
        );
        Ok(target as u16)
    }
    pub fn positions(&self) -> Result<Vec<u16>> {
        self.validate()?;
        let distance = self.start.abs_diff(self.end) as u32;
        let mut positions = Vec::with_capacity((distance / u32::from(self.step) + 2) as usize);
        let mut offset = 0u32;
        while offset < distance {
            positions.push((i32::from(self.start) + self.direction() * offset as i32) as u16);
            offset += u32::from(self.step);
        }
        positions.push(self.end);
        Ok(positions)
    }
}

#[derive(Clone, Copy, Debug, Default, Serialize, Deserialize, PartialEq)]
pub struct Roi {
    pub x: f32,
    pub y: f32,
    pub width: f32,
    pub height: f32,
}
impl Roi {
    pub fn subject() -> Self {
        Self {
            x: 0.1,
            y: 0.1,
            width: 0.8,
            height: 0.8,
        }
    }
    pub fn valid(self) -> bool {
        [self.x, self.y, self.width, self.height]
            .iter()
            .all(|v| v.is_finite())
            && self.x >= 0.0
            && self.y >= 0.0
            && self.width >= 0.05
            && self.height >= 0.05
            && self.x + self.width <= 1.001
            && self.y + self.height <= 1.001
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Phase {
    Disconnected,
    Connecting,
    Ready,
    Moving,
    Scanning,
    Capturing,
    Paused,
    Complete,
    Stopped,
    Fault,
    Recovering,
    Disconnecting,
}
impl Phase {
    pub fn active(&self) -> bool {
        matches!(
            self,
            Self::Connecting
                | Self::Moving
                | Self::Scanning
                | Self::Capturing
                | Self::Paused
                | Self::Disconnecting
                | Self::Recovering
        )
    }
    pub fn can_edit(&self) -> bool {
        matches!(self, Self::Ready | Self::Complete | Self::Stopped)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn directional_endpoints_and_short_last_interval() {
        let mut p = Plan {
            start: 60000,
            end: 60010,
            step: 3,
            ..Plan::default()
        };
        assert_eq!(p.positions().unwrap(), [60000, 60003, 60006, 60009, 60010]);
        p.start = 60010;
        p.end = 60000;
        assert_eq!(p.positions().unwrap(), [60010, 60007, 60004, 60001, 60000]);
        assert_eq!(p.prestart().unwrap(), 60138);
    }
    #[test]
    fn no_clamping_overflow_or_zero_steps() {
        let mut p = Plan {
            start: 300,
            end: 300,
            ..Plan::default()
        };
        assert_eq!(p.positions().unwrap(), [300]);
        p.step = 0;
        assert!(p.positions().is_err());
        p.step = 1;
        p.start = 0;
        assert!(p.positions().is_err());
        p.start = 65535;
        p.end = 65530;
        assert!(p.positions().is_err());
        p.approach = 0;
        assert!(p.positions().is_err());
    }
}
