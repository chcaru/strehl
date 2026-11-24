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
        }
    }
}

impl Plan {
    pub fn validate(&self) -> Result<()> {
        if let Some(subject) = &self.subject {
            subject.validate()?;
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
