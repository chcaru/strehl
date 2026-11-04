//! Frozen native validation reservations for the second mosaic fitting stage.
//! All coordinates are green-quad pixel centres in independent pass gauges.
//! A plan is geometry/provenance only; it never reads an image or a residual.
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;

#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Rectangle {
    pub low: [f64; 2],
    pub high: [f64; 2],
}
impl Rectangle {
    pub fn around(point: [f64; 2], radius: f64) -> Result<Self> {
        ensure!(
            radius.is_finite() && radius >= 0.0,
            "invalid reservation radius"
        );
        let result = Self {
            low: point.map(|v| v - radius),
            high: point.map(|v| v + radius),
        };
        result.validate()?;
        Ok(result)
    }
    fn validate(self) -> Result<()> {
        ensure!(
            self.low.into_iter().chain(self.high).all(f64::is_finite)
                && (0..2).all(|axis| self.low[axis] <= self.high[axis]),
            "invalid reservation rectangle"
        );
        Ok(())
    }
    fn contains(self, other: Self) -> bool {
        (0..2).all(|axis| self.low[axis] <= other.low[axis] && other.high[axis] <= self.high[axis])
    }
    fn intersects(self, other: Self) -> bool {
        (0..2).all(|axis| self.low[axis] <= other.high[axis] && other.low[axis] <= self.high[axis])
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AnchorGrid {
    pub source_size_quad: [usize; 2],
    pub guide_origin_quad: [f64; 2],
    pub guide_step_quad: usize,
    pub initial_block_guide_pixels: usize,
    pub global_source_range: [usize; 2],
}
impl AnchorGrid {
    fn validate(&self) -> Result<()> {
        ensure!(
            self.source_size_quad
                .into_iter()
                .all(|v| (64..=32768).contains(&v))
                && self
                    .guide_origin_quad
                    .into_iter()
                    .all(|v| v.is_finite() && v >= 0.0 && v <= self.guide_step_quad as f64)
                && (1..=64).contains(&self.guide_step_quad)
                && (1..=2048).contains(&self.initial_block_guide_pixels)
                && self.global_source_range[0] < self.global_source_range[1],
            "invalid frozen pass grid"
        );
        Ok(())
    }
    fn inside(&self, bounds: Rectangle) -> bool {
        (0..2).all(|axis| {
            bounds.low[axis] >= 0.0 && bounds.high[axis] < self.source_size_quad[axis] as f64
        })
    }
    /// Whole inclusive physical rectangle, including the original box/filter
    /// and interpolation extent already supplied by the calling observer.
    fn initial_role(&self, bounds: Rectangle) -> Option<bool> {
        if bounds.validate().is_err() || !self.inside(bounds) {
            return None;
        }
        let side = (self.guide_step_quad * self.initial_block_guide_pixels) as f64;
        let low = [0, 1].map(|a| (bounds.low[a] - self.guide_origin_quad[a]) / side);
        let high = [0, 1].map(|a| (bounds.high[a] - self.guide_origin_quad[a]) / side);
        if low.into_iter().any(|v| v < 0.0) {
            return None;
        }
        let low = low.map(|v| v.floor() as usize);
        let high = high.map(|v| v.floor() as usize);
        let heldout = (low[0] + low[1]).is_multiple_of(3);
        for y in low[1]..=high[1] {
            for x in low[0]..=high[0] {
                if (x + y).is_multiple_of(3) != heldout {
                    return None;
                }
            }
        }
        Some(heldout)
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AncestorFootprint {
    pub pass: usize,
    pub source: usize,
    /// Includes refused attempts; only accepted pairs would omit dependencies.
    pub measurement_id: String,
    pub bounds: Rectangle,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct IslandProposal {
    pub id: String,
    pub cell: [usize; 2],
    pub reference_center_quad: [f64; 2],
    /// Actual original identities nominated from the frozen upstream evidence.
    /// These are search witnesses, never merge weights or metric depth.
    pub original_witnesses: [Vec<usize>; 2],
    /// Native query bounds lifted through the nominated originals' fixed poses.
    /// Late observed footprints still have to fit, regardless of this estimate.
    pub query_radius_quad: [f64; 2],
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ValidationIsland {
    pub proposal: IslandProposal,
    pub nominated_moving_center_quad: [f64; 2],
    pub reservations: [Rectangle; 2],
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RefusedIsland {
    pub proposal: IslandProposal,
    pub reason: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RolePlan {
    pub schema: String,
    /// Hashes bind complete source census, upstream maps/focus/calibration and
    /// exact FIT-only seed/ancestor artifacts. No heldout residual is an input.
    pub upstream_binding_sha256: String,
    pub initial_fit_evidence_sha256: String,
    pub grids: [AnchorGrid; 2],
    /// Centred A-to-B similarity, frozen before second-stage signals are read.
    pub initial_seed: [f64; 4],
    pub nomination_envelope_quad: f64,
    pub ancestor_footprints: Vec<AncestorFootprint>,
    pub islands: Vec<ValidationIsland>,
    pub refused: Vec<RefusedIsland>,
    pub dependency_contract: String,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SpatialRole {
    Fit,
    Heldout(usize),
}

fn hash_valid(value: &str) -> bool {
    value.len() == 64 && value.bytes().all(|v| v.is_ascii_hexdigit())
}

impl RolePlan {
    /// Includes four simultaneous owned copies/serialization buffers during
    /// validation and per-role configuration, without an image-volume term.
    pub fn working_reservation_bytes(&self) -> Result<usize> {
        let mut bytes = std::mem::size_of::<Self>()
            .checked_add(
                self.ancestor_footprints
                    .len()
                    .checked_mul(std::mem::size_of::<AncestorFootprint>())
                    .context("ancestor reservation overflow")?,
            )
            .context("role reservation overflow")?;
        for footprint in &self.ancestor_footprints {
            bytes = bytes
                .checked_add(footprint.measurement_id.len())
                .context("role reservation overflow")?;
        }
        for proposal in self
            .islands
            .iter()
            .map(|i| &i.proposal)
            .chain(self.refused.iter().map(|i| &i.proposal))
        {
            let witnesses = proposal
                .original_witnesses
                .iter()
                .map(Vec::len)
                .sum::<usize>();
            bytes = bytes
                .checked_add(std::mem::size_of::<ValidationIsland>())
                .and_then(|v| v.checked_add(proposal.id.len()))
                .and_then(|v| v.checked_add(witnesses.checked_mul(std::mem::size_of::<usize>())?))
                .context("role reservation overflow")?;
        }
        for text in [
            &self.schema,
            &self.upstream_binding_sha256,
            &self.initial_fit_evidence_sha256,
            &self.dependency_contract,
        ]
        .into_iter()
        .chain(self.refused.iter().map(|r| &r.reason))
        {
            bytes = bytes
                .checked_add(text.len())
                .context("role reservation overflow")?;
        }
        bytes
            .checked_mul(8)
            .and_then(|v| v.checked_add(65536))
            .context("role reservation overflow")
    }

    #[allow(clippy::too_many_arguments)]
    pub fn build(
        upstream_binding_sha256: String,
        initial_fit_evidence_sha256: String,
        grids: [AnchorGrid; 2],
        initial_seed: [f64; 4],
        nomination_envelope_quad: f64,
        ancestor_footprints: Vec<AncestorFootprint>,
        proposals: Vec<IslandProposal>,
    ) -> Result<Self> {
        for grid in &grids {
            grid.validate()?;
        }
        ensure!(
            grids[0].source_size_quad == grids[1].source_size_quad,
            "initial two-view role plan needs equal sensor geometry"
        );
        ensure!(
            grids[0].global_source_range[1] <= grids[1].global_source_range[0]
                || grids[1].global_source_range[1] <= grids[0].global_source_range[0],
            "validation pass source ranges overlap"
        );
        ensure!(
            hash_valid(&upstream_binding_sha256) && hash_valid(&initial_fit_evidence_sha256),
            "role plan needs complete bound upstream/FIT evidence"
        );
        ensure!(
            initial_seed.into_iter().all(f64::is_finite)
                && (0.5..=2.0).contains(&initial_seed[0].hypot(initial_seed[1]))
                && nomination_envelope_quad.is_finite()
                && (0.0..=128.0).contains(&nomination_envelope_quad)
                && proposals.len() <= 512
                && ancestor_footprints.len() <= 65536,
            "invalid/unbounded role plan input"
        );
        for footprint in &ancestor_footprints {
            ensure!(footprint.pass < 2, "ancestor pass outside plan");
            footprint.bounds.validate()?;
            let grid = &grids[footprint.pass];
            ensure!(
                !footprint.measurement_id.is_empty()
                    && footprint.measurement_id.len() <= 256
                    && (grid.global_source_range[0]..grid.global_source_range[1])
                        .contains(&footprint.source),
                "initial FIT ancestor has wrong identity"
            );
        }
        let mut plan = Self {
            schema: "strehl.mosaic-native-validation-islands.v1".into(),
            upstream_binding_sha256, initial_fit_evidence_sha256, grids, initial_seed,
            nomination_envelope_quad, ancestor_footprints, islands: Vec::new(), refused: Vec::new(),
            dependency_contract: "Conditional on bound within-pass maps/focus/source nominations/calibration. Initial normalization, eligibility and descriptors lie wholly in initial FIT roles; every accepted or refused native attempt is included in the ancestor union. Islands lie in initial heldout regions and exclude that entire union. Second-stage normalization and all attempted support exclude these frozen islands. A planned island is not a measurement or a join certificate.".into(),
        };
        let mut ids = BTreeSet::new();
        for proposal in proposals {
            ensure!(
                ids.insert(proposal.id.clone())
                    && !proposal.id.is_empty()
                    && proposal.id.len() <= 256,
                "duplicate/empty validation island ID"
            );
            match plan.reservation(&proposal) {
                Ok(island) => plan.islands.push(island),
                Err(error) => plan.refused.push(RefusedIsland {
                    proposal,
                    reason: error.to_string(),
                }),
            }
        }
        Ok(plan)
    }

    fn reservation(&self, proposal: &IslandProposal) -> Result<ValidationIsland> {
        for pass in 0..2 {
            let witnesses = &proposal.original_witnesses[pass];
            let range = self.grids[pass].global_source_range;
            ensure!(
                !witnesses.is_empty()
                    && witnesses.len() <= 4
                    && witnesses.iter().all(|i| (range[0]..range[1]).contains(i))
                    && witnesses.iter().collect::<BTreeSet<_>>().len() == witnesses.len(),
                "invalid frozen original witnesses"
            );
            ensure!(
                (1.0..=512.0).contains(&proposal.query_radius_quad[pass]),
                "invalid declared query radius"
            );
        }
        let p = proposal.reference_center_quad;
        let center = self.grids[0].source_size_quad.map(|v| v as f64 * 0.5);
        let [a, b, tx, ty] = self.initial_seed;
        let q = [
            center[0] + a * (p[0] - center[0]) - b * (p[1] - center[1]) + tx,
            center[1] + b * (p[0] - center[0]) + a * (p[1] - center[1]) + ty,
        ];
        let reservations = [
            Rectangle::around(p, proposal.query_radius_quad[0])?,
            Rectangle::around(
                q,
                proposal.query_radius_quad[1] + self.nomination_envelope_quad,
            )?,
        ];
        for (pass, bounds) in reservations.iter().enumerate() {
            ensure!(
                self.grids[pass].initial_role(*bounds) == Some(true),
                "projected reservation reaches initial FIT or missing source support"
            );
            ensure!(
                !self
                    .ancestor_footprints
                    .iter()
                    .any(|old| old.pass == pass && old.bounds.intersects(*bounds)),
                "reservation overlaps an initial FIT attempt"
            );
            ensure!(
                !self
                    .islands
                    .iter()
                    .any(|old| old.reservations[pass].intersects(*bounds)),
                "validation islands do not have distinct physical support"
            );
        }
        Ok(ValidationIsland {
            proposal: proposal.clone(),
            nominated_moving_center_quad: q,
            reservations,
        })
    }

    pub fn classify(&self, pass: usize, bounds: Rectangle) -> Option<SpatialRole> {
        if pass >= 2 || bounds.validate().is_err() || !self.grids[pass].inside(bounds) {
            return None;
        }
        for (i, island) in self.islands.iter().enumerate() {
            let reserved = island.reservations[pass];
            if reserved.contains(bounds) {
                return Some(SpatialRole::Heldout(i));
            }
            if reserved.intersects(bounds) {
                return None;
            }
        }
        Some(SpatialRole::Fit)
    }

    pub fn witness_allowed(&self, island: usize, pass: usize, source: usize) -> bool {
        pass < 2
            && self
                .islands
                .get(island)
                .is_some_and(|i| i.proposal.original_witnesses[pass].contains(&source))
    }

    pub fn check_fit_attempt(&self, footprint: &AncestorFootprint) -> Result<()> {
        let grid = self
            .grids
            .get(footprint.pass)
            .context("FIT attempt pass outside plan")?;
        ensure!(
            (grid.global_source_range[0]..grid.global_source_range[1]).contains(&footprint.source)
                && self.classify(footprint.pass, footprint.bounds) == Some(SpatialRole::Fit),
            "FIT attempt consumes frozen validation support or wrong original"
        );
        Ok(())
    }

    pub fn freeze(&self) -> Result<FrozenRolePlan> {
        let mut proposals: Vec<_> = self.islands.iter().map(|i| i.proposal.clone()).collect();
        proposals.extend(self.refused.iter().map(|i| i.proposal.clone()));
        // Rebuild accepted reservations independently of any stored rectangle.
        let rebuilt = Self::build(
            self.upstream_binding_sha256.clone(),
            self.initial_fit_evidence_sha256.clone(),
            self.grids.clone(),
            self.initial_seed,
            self.nomination_envelope_quad,
            self.ancestor_footprints.clone(),
            proposals,
        )?;
        ensure!(
            rebuilt.islands == self.islands
                && rebuilt.refused == self.refused
                && rebuilt.schema == self.schema
                && rebuilt.dependency_contract == self.dependency_contract,
            "role plan reservations or contract changed"
        );
        let hash = Sha256::digest(serde_json::to_vec(self)?);
        Ok(FrozenRolePlan {
            plan: self.clone(),
            sha256: hash.iter().map(|b| format!("{b:02x}")).collect(),
        })
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FrozenRolePlan {
    pub plan: RolePlan,
    pub sha256: String,
}
impl FrozenRolePlan {
    pub fn verify(&self) -> Result<()> {
        ensure!(
            self.plan.freeze()?.sha256 == self.sha256,
            "frozen role plan checksum differs"
        );
        Ok(())
    }
}

#[cfg(test)]
#[path = "session-mosaic-roles-tests.rs"]
mod tests;
