//! Automatic acquisition planning for the default "best result" session mode.
//!
//! The planner turns per-pass evidence into an explicit contribution plan for
//! the existing fusion consumer. It never invents a relationship. Geometry
//! must place a pass consistently; brightness is measured per frame from the
//! alignment overlaps (shutter metadata states intent, not delivered light);
//! a pass whose lighting differs in shape, not only level, is not fused.
//! Everything else falls back to a stated per-pass exclusion instead of
//! failing the whole session.
use anyhow::{Result, ensure};
use serde::Serialize;

pub const SCHEMA: &str = "strehl.session-auto-plan.v2";

/// Largest magnification ratio (either way) fused into the anchor canvas.
/// Beyond it a pass needs close-up detail insertion, which the consumer does
/// not provide yet; resampling it into the canvas would discard or alias detail.
pub const MAX_RELATIVE_SCALE: f64 = 1.5;
/// Largest median spatial spread of block brightness ratios to the anchor
/// (natural log, about 10%): beyond it shading differs, not just level.
pub const MAX_PHOTOMETRIC_SPREAD: f64 = 0.10;
/// Largest median per-edge residual after the per-frame brightness solve.
pub const MAX_PHOTOMETRIC_RESIDUAL: f64 = 0.05;
/// Measured brightness variation (natural log) above which per-frame gains are
/// applied even when every contributing pass shares the anchor's settings.
pub const DRIFT_THRESHOLD: f64 = 0.01;

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
    /// Median remaining displacement (guide px) after placement, when measured.
    pub geometric_residual: Option<f64>,
    /// Median magnification relative to the anchor pass.
    pub relative_scale: Option<f64>,
    /// Every placed frame received a solved per-frame brightness.
    pub brightness_measured: bool,
    pub photometric_spread: Option<f64>,
    pub photometric_residual: Option<f64>,
    /// Solved log brightness range within the pass, relative to the reference.
    pub log_brightness_range: Option<[f64; 2]>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Role {
    /// Framing, colour and signal-unit reference.
    Anchor,
    /// Same acquisition settings as the anchor.
    Combine,
    /// Different shutter time; combined through measured per-frame gains.
    ExposureNormalized,
    /// Geometrically consistent but lit differently (shading, not only level):
    /// merged on its own and blended into the photograph by lighting fusion.
    LightingLayer,
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
    /// Anchor shutter divided by this pass's shutter (intent, not a gain used).
    pub nominal_gain: Option<f64>,
    pub relative_scale: Option<f64>,
    pub cross_support_ratio: Option<f64>,
    pub photometric_spread: Option<f64>,
    pub photometric_residual: Option<f64>,
    pub log_brightness_range: Option<[f64; 2]>,
    pub role: Role,
    pub reason: Option<String>,
}

#[derive(Clone, Debug, Serialize)]
pub struct AutoPlan {
    pub schema: &'static str,
    pub anchor_pass: usize,
    pub anchor_is_primary: bool,
    pub passes: Vec<PassPlan>,
    /// Consumer applies the solved per-frame gains (otherwise unity).
    pub per_frame_gains: bool,
    /// Lighting layers are blended (`--lighting-fusion`); otherwise they are
    /// reported but not consumed. Off by default: on bug-4 no blend tried so
    /// far beat the anchor's developed photograph.
    pub lighting_fusion: bool,
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

fn excluded(reason: String) -> (Role, Option<String>) {
    (Role::Excluded, Some(reason))
}

fn role_for(pass: usize, anchor: usize, f: &PassFacts, lead: &PassFacts) -> (Role, Option<String>) {
    if pass == anchor {
        return (Role::Anchor, None);
    }
    if f.placed == 0 {
        return excluded("no frame joined the anchor's measured alignment".into());
    }
    if !f.geometry_consistent {
        let evidence = match (f.geometric_residual, f.cross_support_ratio) {
            (Some(px), _) => format!(
                "after placement the subject still moves {px:.1} guide px (median) against the anchor"
            ),
            (None, Some(r)) => {
                format!("one 2-D placement matches the anchor only locally (support {r:.2})")
            }
            (None, None) => "one 2-D placement does not match the anchor across the overlap".into(),
        };
        return excluded(format!(
            "{evidence}; the subject's pose or shape likely changed between passes, and fusing would ghost"
        ));
    }
    if let Some(s) = f.relative_scale
        && !(1.0 / MAX_RELATIVE_SCALE..=MAX_RELATIVE_SCALE).contains(&s)
    {
        return excluded(format!(
            "magnification x{s:.2} relative to the anchor needs close-up detail insertion, which is not yet supported"
        ));
    }
    if !f.calibration_matches_anchor {
        return excluded(
            "decoded sensor levels or colour calibration differ from the anchor".into(),
        );
    }
    if f.iso.is_none() || f.iso != lead.iso {
        return excluded(format!(
            "ISO {} differs from the anchor's ISO {}; cross-ISO response and noise are not yet calibrated",
            f.iso.map_or_else(|| "unknown".into(), |v| v.to_string()),
            lead.iso.map_or_else(|| "unknown".into(), |v| v.to_string()),
        ));
    }
    if !same_ratio(f.aperture, lead.aperture) {
        return excluded(format!(
            "aperture {} differs from the anchor's {}; a different PSF and depth of field are not pooled",
            f_number(f.aperture),
            f_number(lead.aperture)
        ));
    }
    if let Some(spread) = f.photometric_spread
        && spread > MAX_PHOTOMETRIC_SPREAD
    {
        return (
            Role::LightingLayer,
            Some(format!(
                "lighting differs in shape from the anchor (brightness ratio varies {:.0}% across the overlap)",
                100.0 * spread
            )),
        );
    }
    if let Some(residual) = f.photometric_residual
        && residual > MAX_PHOTOMETRIC_RESIDUAL
    {
        return (
            Role::LightingLayer,
            Some(format!(
                "brightness relation to the anchor varies across overlaps ({:.0}% residual)",
                100.0 * residual
            )),
        );
    }
    if same_ratio(f.shutter, lead.shutter) {
        return (Role::Combine, None);
    }
    if f.brightness_measured && f.photometric_spread.is_some() {
        (Role::ExposureNormalized, None)
    } else {
        excluded("shutter differs and no overlap with the anchor measured its brightness".into())
    }
}

/// Draw the plan relative to `anchor`. The anchor must be placed and is never
/// excluded: it defines framing and signal units.
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
    let passes: Vec<PassPlan> = facts
        .iter()
        .enumerate()
        .map(|(pass, f)| {
            let (role, reason) = role_for(pass, anchor, f, lead);
            PassPlan {
                pass,
                name: f.name.clone(),
                frames: f.frames,
                placed: f.placed,
                iso: f.iso,
                shutter_seconds: f.shutter.and_then(ratio),
                aperture_f_number: f.aperture.and_then(ratio),
                nominal_gain: match (lead.shutter.and_then(ratio), f.shutter.and_then(ratio)) {
                    (Some(a), Some(s)) => Some(a / s),
                    _ => None,
                },
                relative_scale: f.relative_scale,
                cross_support_ratio: f.cross_support_ratio,
                photometric_spread: f.photometric_spread,
                photometric_residual: f.photometric_residual,
                log_brightness_range: f.log_brightness_range,
                role,
                reason,
            }
        })
        .collect();
    // Per-frame gains whenever exposure differs or measured brightness drifts.
    let (mut lo, mut hi) = (f64::INFINITY, f64::NEG_INFINITY);
    for p in passes.iter().filter(|p| p.role != Role::Excluded) {
        if let Some([a, b]) = p.log_brightness_range {
            lo = lo.min(a);
            hi = hi.max(b);
        }
    }
    let drift = hi - lo;
    let per_frame_gains = passes
        .iter()
        .any(|p| matches!(p.role, Role::ExposureNormalized | Role::LightingLayer))
        || (drift.is_finite() && drift > DRIFT_THRESHOLD);
    Ok(AutoPlan {
        schema: SCHEMA,
        anchor_pass: anchor,
        anchor_is_primary,
        passes,
        per_frame_gains,
        lighting_fusion: false,
        limitations: vec![
            "Equal metadata is evidence for combination, not proof of equal focus, illumination or subject rigidity; the consumer still gates averaging by noise.",
            "Per-frame brightness comes from block-mean ratios over geometry-confirmed overlaps, solved jointly; it is not held out from alignment.",
            "Excluded passes are not consumed by this photograph; they remain available to aligned layers or a later plan.",
        ],
    })
}

impl AutoPlan {
    pub fn with_lighting_fusion(mut self, on: bool) -> Self {
        self.lighting_fusion = on;
        self
    }

    /// Pass masks of lighting groups: group 0 is the anchor with every pass
    /// combined into it; with lighting fusion on, each lighting layer forms
    /// its own group.
    pub fn lighting_groups(&self) -> Vec<Vec<bool>> {
        let mut groups = vec![
            self.passes
                .iter()
                .map(|p| {
                    matches!(
                        p.role,
                        Role::Anchor | Role::Combine | Role::ExposureNormalized
                    )
                })
                .collect::<Vec<_>>(),
        ];
        for p in self
            .passes
            .iter()
            .filter(|p| self.lighting_fusion && p.role == Role::LightingLayer)
        {
            groups.push(self.passes.iter().map(|q| q.pass == p.pass).collect());
        }
        groups
    }

    pub fn excluded(&self) -> Vec<bool> {
        self.passes
            .iter()
            .map(|p| {
                p.role == Role::Excluded || (p.role == Role::LightingLayer && !self.lighting_fusion)
            })
            .collect()
    }

    /// Short human summary for logs and the desktop explanation surface.
    pub fn summary(&self) -> Vec<String> {
        let used = self.excluded().iter().filter(|&&e| !e).count();
        let mut lines = vec![format!(
            "automatic plan: {used} of {} passes contribute; anchor '{}'{}{}",
            self.passes.len(),
            self.passes[self.anchor_pass].name,
            if self.anchor_is_primary {
                " (primary)"
            } else {
                " (geometry reference)"
            },
            if self.per_frame_gains {
                "; measured per-frame brightness applied"
            } else {
                ""
            }
        )];
        for p in &self.passes {
            let range = p.log_brightness_range.map_or_else(String::new, |[a, b]| {
                format!(" (brightness x{:.3}..x{:.3})", a.exp(), b.exp())
            });
            let detail = match p.role {
                Role::Anchor => format!("anchor{range}"),
                Role::Combine => format!("combined at equal settings{range}"),
                Role::ExposureNormalized => format!(
                    "combined through measured brightness{range}; nominal x{:.3}",
                    p.nominal_gain.map_or(f64::NAN, |g| 1.0 / g)
                ),
                Role::LightingLayer if self.lighting_fusion => format!(
                    "lighting layer, adds detail where it agrees with the anchor{range}: {}",
                    p.reason.as_deref().unwrap_or("lighting differs")
                ),
                Role::LightingLayer => format!(
                    "lighting layer, not blended (--lighting-fusion blends it){range}: {}",
                    p.reason.as_deref().unwrap_or("lighting differs")
                ),
                Role::Excluded => {
                    format!("not used: {}", p.reason.as_deref().unwrap_or("unspecified"))
                }
            };
            lines.push(format!("  {}: {detail}", p.name));
        }
        lines
    }
}

#[cfg(test)]
mod tests {
    use super::*;

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
            geometric_residual: None,
            relative_scale: Some(1.0),
            brightness_measured: true,
            photometric_spread: Some(0.01),
            photometric_residual: Some(0.005),
            log_brightness_range: Some([0.0, 0.0]),
        }
    }

    #[test]
    fn auto_plan_normalizes_measured_exposure_and_flags_per_frame_gains() {
        let mut faster = facts("c", [2, 1]);
        faster.log_brightness_range = Some([0.2, 0.25]);
        let plan = plan(&[facts("a", [16, 10]), facts("b", [8, 5]), faster], 0, true).unwrap();
        let roles: Vec<_> = plan.passes.iter().map(|p| p.role).collect();
        assert_eq!(
            roles,
            [Role::Anchor, Role::Combine, Role::ExposureNormalized]
        );
        assert!(plan.per_frame_gains);
        // Equal settings and stable light keep unity gains (bit-identical path).
        let stable = plan_of(&[facts("a", [16, 10]), facts("b", [16, 10])]);
        assert!(!stable.per_frame_gains);
        // Equal settings but a lamp drifting 3%: per-frame gains apply.
        let mut drifting = facts("b", [16, 10]);
        drifting.log_brightness_range = Some([-0.03, 0.0]);
        assert!(plan_of(&[facts("a", [16, 10]), drifting]).per_frame_gains);
    }

    fn plan_of(f: &[PassFacts]) -> AutoPlan {
        plan(f, 0, true).unwrap()
    }

    #[test]
    fn auto_plan_excludes_shading_changes_and_unmeasured_exposure() {
        let mut shaded = facts("shaded", [2, 1]);
        shaded.photometric_spread = Some(0.2);
        let mut inconsistent = facts("inconsistent", [16, 10]);
        inconsistent.photometric_residual = Some(0.09);
        let mut unmeasured = facts("unmeasured", [2, 1]);
        unmeasured.brightness_measured = false;
        unmeasured.photometric_spread = None;
        let mut equal_unmeasured = facts("equal", [16, 10]);
        equal_unmeasured.photometric_spread = None;
        let plan = plan_of(&[
            facts("a", [16, 10]),
            shaded,
            inconsistent,
            unmeasured,
            equal_unmeasured,
        ]);
        assert_eq!(plan.excluded(), [false, true, true, true, false]);
        assert_eq!(plan.lighting_groups().len(), 1);
        let plan = plan.with_lighting_fusion(true);
        assert_eq!(plan.excluded(), [false, false, false, true, false]);
        assert_eq!(plan.passes[1].role, Role::LightingLayer);
        assert_eq!(plan.passes[2].role, Role::LightingLayer);
        assert!(plan.passes[1].reason.as_deref().unwrap().contains("shape"));
        assert!(
            plan.passes[3]
                .reason
                .as_deref()
                .unwrap()
                .contains("brightness")
        );
        let groups = plan.lighting_groups();
        assert_eq!(groups.len(), 3);
        assert_eq!(groups[0], [true, false, false, false, true]);
        assert_eq!(groups[1], [false, true, false, false, false]);
        assert!(plan.per_frame_gains);
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
        unknown.brightness_measured = false;
        unknown.photometric_spread = None;
        let plan = plan_of(&[
            facts("anchor", [16, 10]),
            iso,
            aperture,
            unplaced,
            color,
            unknown,
        ]);
        assert_eq!(plan.excluded(), [false, true, true, true, true, true]);
        assert!(plan.passes[1..].iter().all(|p| p.reason.is_some()));
        assert!(plan.summary()[0].contains("1 of 6 passes"));
    }

    #[test]
    fn auto_plan_excludes_locally_registered_and_strongly_magnified_passes() {
        let mut posed = facts("posed", [16, 10]);
        posed.geometry_consistent = false;
        posed.cross_support_ratio = Some(0.2);
        let mut moved = facts("moved", [16, 10]);
        moved.geometry_consistent = false;
        moved.geometric_residual = Some(4.0);
        let moved_plan = plan_of(&[facts("a", [16, 10]), moved]);
        assert!(
            moved_plan.passes[1]
                .reason
                .as_deref()
                .unwrap()
                .contains("4.0 guide px")
        );
        let mut closeup = facts("closeup", [2, 1]);
        closeup.relative_scale = Some(2.7);
        let mut wider = facts("wider", [16, 10]);
        wider.relative_scale = Some(0.6);
        let mut near = facts("near", [16, 10]);
        near.relative_scale = Some(1.22);
        let plan = plan_of(&[facts("a", [16, 10]), posed, closeup, wider, near]);
        assert_eq!(plan.excluded(), [false, true, true, true, false]);
        assert!(plan.passes[1].reason.as_deref().unwrap().contains("ghost"));
        assert!(plan.passes[2].reason.as_deref().unwrap().contains("x2.70"));
    }

    #[test]
    fn auto_plan_refuses_an_unplaced_anchor() {
        let mut anchor = facts("anchor", [16, 10]);
        anchor.placed = 0;
        assert!(plan(&[anchor, facts("b", [16, 10])], 0, true).is_err());
        assert!(plan(&[facts("a", [16, 10])], 1, true).is_err());
    }
}
