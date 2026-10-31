//! Automatic acquisition planning for the default "best result" session mode.
//!
//! The planner turns per-pass evidence into an explicit contribution plan for
//! the existing fusion consumer. It never invents a relationship: equal
//! acquisition settings combine as before, a shutter change is admitted only
//! after held-out calibrated photometry, and everything else falls back to a
//! stated per-pass exclusion instead of failing the whole session. Metadata is
//! treated as evidence of what needs measuring, never as proof of equivalence.
use anyhow::{Result, ensure};
use serde::Serialize;

use crate::session_photometry::PhotometryReport;

pub const SCHEMA: &str = "strehl.session-auto-plan.v1";

/// Per-pass facts gathered before the plan is drawn.
#[derive(Clone, Debug, PartialEq)]
pub struct PassFacts {
    pub name: String,
    pub frames: usize,
    /// Frames placed in the anchor's measured alignment component.
    pub placed: usize,
    pub iso: Option<u32>,
    pub shutter: Option<[u32; 2]>,
    pub aperture: Option<[u32; 2]>,
    /// Decoded levels, sensor identity and colour calibration equal the anchor.
    pub calibration_matches_anchor: bool,
    /// Alignment found one 2-D placement consistent across the overlap.
    pub geometry_consistent: bool,
    pub cross_support_ratio: Option<f64>,
    /// Median magnification relative to the anchor pass.
    pub relative_scale: Option<f64>,
}

/// Largest magnification ratio (either way) fused into the anchor canvas.
/// Beyond it a pass needs close-up detail insertion, which the consumer does
/// not provide yet; resampling it into the canvas would discard or alias detail.
pub const MAX_RELATIVE_SCALE: f64 = 1.5;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Role {
    /// Framing, colour and signal-unit reference.
    Anchor,
    /// Same acquisition settings as the anchor; combined without rescaling.
    Combine,
    /// Different shutter time; combined after calibrated exposure correction.
    ExposureNormalized,
    /// Shutter differs and calibrated photometry has not yet run.
    PendingPhotometry,
    /// Retained in the report, not consumed by the photograph.
    Excluded,
}

#[derive(Clone, Debug, Serialize)]
pub struct PassPlan {
    pub pass: usize,
    pub name: String,
    pub frames: usize,
    pub placed: usize,
    pub iso: Option<u32>,
    pub shutter_seconds: Option<f64>,
    pub aperture_f_number: Option<f64>,
    /// Anchor shutter divided by this pass's shutter.
    pub nominal_gain: Option<f64>,
    pub relative_scale: Option<f64>,
    pub cross_support_ratio: Option<f64>,
    pub role: Role,
    /// Signal-unit gain applied by the consumer; `None` when not consumed.
    pub photometric_gain: Option<f32>,
    pub reason: Option<String>,
}

#[derive(Clone, Debug, Serialize)]
pub struct AutoPlan {
    pub schema: &'static str,
    pub anchor_pass: usize,
    pub anchor_is_primary: bool,
    pub passes: Vec<PassPlan>,
    pub limitations: Vec<&'static str>,
}

fn ratio([n, d]: [u32; 2]) -> Option<f64> {
    (n > 0 && d > 0).then(|| f64::from(n) / f64::from(d))
}

fn same_ratio(a: Option<[u32; 2]>, b: Option<[u32; 2]>) -> bool {
    match (a, b) {
        (Some([an, ad]), Some([bn, bd])) => {
            ad > 0 && bd > 0 && u64::from(an) * u64::from(bd) == u64::from(bn) * u64::from(ad)
        }
        _ => false,
    }
}

fn f_number(value: Option<[u32; 2]>) -> String {
    value
        .and_then(ratio)
        .map_or_else(|| "unknown".into(), |f| format!("f/{f:.1}"))
}

/// Draw the header/geometry plan relative to `anchor`. The anchor itself must
/// be placed and is never excluded: it defines framing and signal units.
pub fn plan(facts: &[PassFacts], anchor: usize, anchor_is_primary: bool) -> Result<AutoPlan> {
    ensure!(
        anchor < facts.len(),
        "automatic plan anchor lies outside the session"
    );
    let lead = &facts[anchor];
    ensure!(
        lead.placed > 0,
        "pass '{}' anchors the automatic plan but has no placed frames",
        lead.name
    );
    ensure!(
        lead.calibration_matches_anchor,
        "anchor calibration comparison must be reflexive"
    );
    let passes = facts
        .iter()
        .enumerate()
        .map(|(pass, f)| {
            let nominal_gain = match (lead.shutter.and_then(ratio), f.shutter.and_then(ratio)) {
                (Some(a), Some(s)) => Some(a / s),
                _ => None,
            };
            let (role, reason) = if pass == anchor {
                (Role::Anchor, None)
            } else if f.placed == 0 {
                (
                    Role::Excluded,
                    Some("no frame joined the anchor's measured alignment".to_string()),
                )
            } else if !f.geometry_consistent {
                (
                    Role::Excluded,
                    Some(format!(
                        "one 2-D placement matches the anchor only locally (support {}); the subject's pose or shape likely changed between passes, and fusing would ghost",
                        f.cross_support_ratio.map_or_else(|| "unmeasured".into(), |r| format!("{r:.2}"))
                    )),
                )
            } else if f
                .relative_scale
                .is_some_and(|s| !(1.0 / MAX_RELATIVE_SCALE..=MAX_RELATIVE_SCALE).contains(&s))
            {
                (
                    Role::Excluded,
                    Some(format!(
                        "magnification x{:.2} relative to the anchor needs close-up detail insertion, which is not yet supported",
                        f.relative_scale.unwrap_or(f64::NAN)
                    )),
                )
            } else if !f.calibration_matches_anchor {
                (
                    Role::Excluded,
                    Some(
                        "decoded sensor levels or colour calibration differ from the anchor"
                            .to_string(),
                    ),
                )
            } else if f.iso.is_none() || f.iso != lead.iso {
                (
                    Role::Excluded,
                    Some(format!(
                        "ISO {} differs from the anchor's ISO {}; cross-ISO response and noise are not yet calibrated",
                        f.iso.map_or_else(|| "unknown".into(), |v| v.to_string()),
                        lead.iso.map_or_else(|| "unknown".into(), |v| v.to_string()),
                    )),
                )
            } else if !same_ratio(f.aperture, lead.aperture) {
                (
                    Role::Excluded,
                    Some(format!(
                        "aperture {} differs from the anchor's {}; a different PSF and depth of field are not pooled",
                        f_number(f.aperture),
                        f_number(lead.aperture)
                    )),
                )
            } else if nominal_gain.is_none() {
                (
                    Role::Excluded,
                    Some("shutter time is unknown".to_string()),
                )
            } else if same_ratio(f.shutter, lead.shutter) {
                (Role::Combine, None)
            } else {
                (Role::PendingPhotometry, None)
            };
            PassPlan {
                pass,
                name: f.name.clone(),
                frames: f.frames,
                placed: f.placed,
                iso: f.iso,
                shutter_seconds: f.shutter.and_then(ratio),
                aperture_f_number: f.aperture.and_then(ratio),
                nominal_gain,
                relative_scale: f.relative_scale,
                cross_support_ratio: f.cross_support_ratio,
                photometric_gain: matches!(role, Role::Anchor | Role::Combine).then_some(1.0),
                role,
                reason,
            }
        })
        .collect();
    Ok(AutoPlan {
        schema: SCHEMA,
        anchor_pass: anchor,
        anchor_is_primary,
        passes,
        limitations: vec![
            "Equal metadata is evidence for combination, not proof of equal focus, illumination or subject rigidity; the consumer still gates averaging by noise.",
            "Exposure corrections are fitted and validated on held-out spatial patches against the anchor; they are not independently held out from alignment.",
            "Excluded passes are not consumed by this photograph; they remain available to aligned layers or a later plan.",
        ],
    })
}

impl AutoPlan {
    /// Passes whose calibrated photometry is required before rendering.
    pub fn photometry_selection(&self) -> Vec<bool> {
        self.passes
            .iter()
            .map(|p| p.role == Role::PendingPhotometry)
            .collect()
    }

    /// Resolve pending passes from a calibrated report: accepted passes take
    /// their corrected gain, refused passes are excluded with the refusal.
    /// There is no nominal-ratio fallback.
    pub fn apply_photometry(&mut self, report: &PhotometryReport) -> Result<()> {
        ensure!(
            report.anchor_pass == self.anchor_pass && report.passes.len() == self.passes.len(),
            "photometry report does not match the automatic plan"
        );
        for (plan, measured) in self.passes.iter_mut().zip(&report.passes) {
            if plan.role != Role::PendingPhotometry {
                continue;
            }
            ensure!(measured.pass == plan.pass, "photometry pass order differs");
            match (measured.accepted, measured.corrected_gain) {
                (true, Some(gain)) if gain.is_finite() && gain > 0.0 => {
                    plan.role = Role::ExposureNormalized;
                    plan.photometric_gain = Some(gain);
                }
                _ => {
                    plan.role = Role::Excluded;
                    plan.reason = Some(format!(
                        "shutter {} could not be calibrated against the anchor: {}",
                        seconds_from(plan.shutter_seconds),
                        measured
                            .refusal
                            .as_deref()
                            .unwrap_or("insufficient calibrated overlap")
                    ));
                }
            }
        }
        Ok(())
    }

    /// Consumer gains in pass order; excluded passes are never consumed.
    pub fn gains(&self) -> Result<Vec<f32>> {
        self.passes
            .iter()
            .map(|p| match p.role {
                Role::PendingPhotometry => {
                    anyhow::bail!("pass '{}' still awaits exposure calibration", p.name)
                }
                Role::Excluded => Ok(1.0),
                _ => p
                    .photometric_gain
                    .ok_or_else(|| anyhow::anyhow!("pass '{}' has no gain", p.name)),
            })
            .collect()
    }

    pub fn excluded(&self) -> Vec<bool> {
        self.passes
            .iter()
            .map(|p| p.role == Role::Excluded)
            .collect()
    }

    /// Short human summary for logs and the desktop error/explanation surface.
    pub fn summary(&self) -> Vec<String> {
        let used = self
            .passes
            .iter()
            .filter(|p| p.role != Role::Excluded)
            .count();
        let mut lines = vec![format!(
            "automatic plan: {used} of {} passes contribute; anchor '{}'{}",
            self.passes.len(),
            self.passes[self.anchor_pass].name,
            if self.anchor_is_primary {
                " (primary)"
            } else {
                " (geometry reference)"
            }
        )];
        for p in &self.passes {
            let detail = match p.role {
                Role::Anchor => "anchor".to_string(),
                Role::Combine => "combined at equal settings".to_string(),
                Role::ExposureNormalized => format!(
                    "combined after calibrated exposure correction x{:.4} (nominal x{:.4})",
                    p.photometric_gain.unwrap_or(f32::NAN),
                    p.nominal_gain.unwrap_or(f64::NAN)
                ),
                Role::PendingPhotometry => "awaiting exposure calibration".to_string(),
                Role::Excluded => {
                    format!("not used: {}", p.reason.as_deref().unwrap_or("unspecified"))
                }
            };
            lines.push(format!("  {}: {detail}", p.name));
        }
        lines
    }
}

fn seconds_from(value: Option<f64>) -> String {
    value.map_or_else(|| "unknown".into(), |s| format!("{s} s"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::session_photometry::PassPhotometryReport;

    fn facts(name: &str, shutter: [u32; 2]) -> PassFacts {
        PassFacts {
            name: name.into(),
            frames: 10,
            placed: 10,
            iso: Some(100),
            shutter: Some(shutter),
            aperture: Some([56, 10]),
            calibration_matches_anchor: true,
            geometry_consistent: true,
            cross_support_ratio: Some(1.0),
            relative_scale: Some(1.0),
        }
    }

    #[test]
    fn auto_plan_combines_equal_settings_and_queues_shutter_changes_for_photometry() {
        let plan = plan(
            &[facts("a", [16, 10]), facts("b", [8, 5]), facts("c", [2, 1])],
            0,
            true,
        )
        .unwrap();
        let roles: Vec<_> = plan.passes.iter().map(|p| p.role).collect();
        assert_eq!(
            roles,
            [Role::Anchor, Role::Combine, Role::PendingPhotometry]
        );
        assert_eq!(plan.photometry_selection(), [false, false, true]);
        assert!((plan.passes[2].nominal_gain.unwrap() - 0.8).abs() < 1e-12);
        assert!(plan.gains().is_err(), "pending photometry cannot render");
        assert_eq!(plan.passes[1].photometric_gain, Some(1.0));
    }

    #[test]
    fn auto_plan_excludes_unsupported_relationships_without_failing_the_session() {
        let mut iso = facts("iso", [16, 10]);
        iso.iso = Some(400);
        let mut aperture = facts("aperture", [16, 10]);
        aperture.aperture = Some([8, 1]);
        let mut unplaced = facts("unplaced", [16, 10]);
        unplaced.placed = 0;
        let mut color = facts("color", [16, 10]);
        color.calibration_matches_anchor = false;
        let mut unknown = facts("unknown", [16, 10]);
        unknown.shutter = None;
        let plan = plan(
            &[
                facts("anchor", [16, 10]),
                iso,
                aperture,
                unplaced,
                color,
                unknown,
            ],
            0,
            false,
        )
        .unwrap();
        assert_eq!(plan.excluded(), [false, true, true, true, true, true]);
        assert!(plan.passes[1..].iter().all(|p| p.reason.is_some()));
        assert_eq!(plan.gains().unwrap(), vec![1.0; 6]);
        assert!(plan.summary()[0].contains("1 of 6 passes"));
    }

    fn measured(pass: usize, accepted: bool, gain: Option<f32>) -> PassPhotometryReport {
        PassPhotometryReport {
            pass,
            nominal_gain: 0.8,
            corrected_gain: gain,
            correction_ev: None,
            stability_relative: None,
            anchor_rank_span: None,
            source_rank_span: None,
            validation: None,
            accepted,
            refusal: (!accepted)
                .then(|| "radiometric correction changes across focus ranks".into()),
            pairs: Vec::new(),
        }
    }

    fn report(passes: Vec<PassPhotometryReport>) -> PhotometryReport {
        PhotometryReport {
            generation: crate::session_photometry::GENERATION.into(),
            anchor_pass: 0,
            config: crate::session_photometry::PhotometryConfig::default(),
            patches: Vec::new(),
            workspace_bytes: 0,
            retained_report_bytes: 0,
            passes,
            calibrated_gains: None,
            limitations: Vec::new(),
        }
    }

    #[test]
    fn auto_plan_uses_calibrated_gain_and_excludes_refused_exposure_without_nominal_fallback() {
        let mut plan = plan(
            &[
                facts("a", [16, 10]),
                facts("b", [2, 1]),
                facts("c", [2, 1]),
                facts("d", [16, 10]),
            ],
            0,
            true,
        )
        .unwrap();
        plan.apply_photometry(&report(vec![
            measured(0, true, Some(1.0)),
            measured(1, true, Some(0.81)),
            measured(2, false, None),
            // Unselected passes are reported as not evaluated and must be ignored.
            measured(3, false, None),
        ]))
        .unwrap();
        let roles: Vec<_> = plan.passes.iter().map(|p| p.role).collect();
        assert_eq!(
            roles,
            [
                Role::Anchor,
                Role::ExposureNormalized,
                Role::Excluded,
                Role::Combine
            ]
        );
        assert_eq!(plan.gains().unwrap(), [1.0, 0.81, 1.0, 1.0]);
        assert_eq!(plan.excluded(), [false, false, true, false]);
        assert!(
            plan.passes[2]
                .reason
                .as_deref()
                .unwrap()
                .contains("focus ranks")
        );
        // An accepted report without a finite gain is still a refusal.
        let mut other = plan_for_gain_check();
        other
            .apply_photometry(&report(vec![
                measured(0, true, Some(1.0)),
                measured(1, true, Some(f32::NAN)),
            ]))
            .unwrap();
        assert_eq!(other.passes[1].role, Role::Excluded);
        // A report for another anchor cannot be applied.
        let mut wrong = report(vec![
            measured(0, true, Some(1.0)),
            measured(1, true, Some(0.8)),
        ]);
        wrong.anchor_pass = 1;
        assert!(plan_for_gain_check().apply_photometry(&wrong).is_err());
    }

    fn plan_for_gain_check() -> AutoPlan {
        plan(&[facts("a", [16, 10]), facts("b", [2, 1])], 0, false).unwrap()
    }

    #[test]
    fn auto_plan_excludes_locally_registered_and_strongly_magnified_passes() {
        let mut posed = facts("posed", [16, 10]);
        posed.geometry_consistent = false;
        posed.cross_support_ratio = Some(0.2);
        let mut closeup = facts("closeup", [2, 1]);
        closeup.relative_scale = Some(2.7);
        let mut wider = facts("wider", [16, 10]);
        wider.relative_scale = Some(0.6);
        let mut near = facts("near", [16, 10]);
        near.relative_scale = Some(1.22);
        let plan = plan(
            &[facts("a", [16, 10]), posed, closeup, wider, near],
            0,
            true,
        )
        .unwrap();
        assert_eq!(plan.excluded(), [false, true, true, true, false]);
        assert!(plan.passes[1].reason.as_deref().unwrap().contains("ghost"));
        assert!(plan.passes[2].reason.as_deref().unwrap().contains("x2.70"));
        // A close-up never reaches exposure calibration.
        assert_eq!(plan.photometry_selection(), [false; 5]);
    }

    #[test]
    fn auto_plan_refuses_an_unplaced_anchor() {
        let mut anchor = facts("anchor", [16, 10]);
        anchor.placed = 0;
        assert!(plan(&[anchor, facts("b", [16, 10])], 0, true).is_err());
        assert!(plan(&[facts("a", [16, 10])], 1, true).is_err());
    }
}
