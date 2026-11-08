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
        }
    }
}

impl Plan {
    pub fn validate(&self) -> Result<()> {
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
