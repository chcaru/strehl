//! Frozen expected-signal guide from an acquisition outside the current group.
//! This removes direct same-photon precision weighting within that group. It
//! does not establish equal focus, nor independence of the final adaptive merge.
use super::*;
use strehl_core::boxfilter::box_mean;
use strehl_core::plane::PlaneGeometry;
use strehl_core::pyramid::session_fusion::FrozenPrediction;

const RADIUS: usize = 8;
pub(super) struct Guide {
    sampler: NativeSampler,
    common: [Vec<f32>; 4],
    source_signal: [Vec<f32>; 4],
    support: Vec<bool>,
    scratch: Vec<f32>,
    mask_scratch: Vec<u32>,
    acquisition: Option<usize>,
}
impl Guide {
    pub(super) fn reservation_bytes(domain: SamplingDomain) -> Result<usize> {
        sampling_bytes(domain)?
            .checked_add(
                domain
                    .pixels()
                    .checked_mul(41)
                    .context("guide size overflow")?,
            )
            .context("guide reservation overflow")
    }
    pub(super) fn new(domain: SamplingDomain) -> Result<Self> {
        Self::reservation_bytes(domain)?;
        let n = domain.pixels();
        Ok(Self {
            sampler: NativeSampler::new(domain)?,
            common: std::array::from_fn(|_| vec![0.0; n]),
            source_signal: std::array::from_fn(|_| vec![0.0; n]),
            support: vec![false; n],
            scratch: vec![0.0; n],
            mask_scratch: vec![0; n],
            acquisition: None,
        })
    }
    #[allow(clippy::too_many_arguments)]
    pub(super) fn prepare(
        &mut self,
        members: &[usize],
        session: &ResolvedSession,
        identities: &[SourceIdentity],
        alignment: &SessionAlignment,
        cache: &mut SourceCache,
        calibrations: &[Calibration],
        gains: &[f32],
    ) -> Result<Option<serde_json::Value>> {
        self.acquisition = None;
        self.support.fill(false);
        if members.len() < 2 {
            return Ok(None);
        }
        let target = members
            .iter()
            .filter_map(|&i| alignment.map.warps()[i].placed().map(|p| p.a.abs().ln()))
            .sum::<f64>()
            / members.len() as f64;
        let selected = (0..session.len())
            .filter(|i| !members.contains(i))
            .filter_map(|i| {
                alignment.map.warps()[i]
                    .placed()
                    .map(|p| (i, (p.a.abs().ln() - target).abs()))
            })
            .filter(|(_, d)| d.is_finite())
            .min_by(|(ia, a), (ib, b)| a.total_cmp(b).then_with(|| ia.cmp(ib)));
        let Some((index, gap)) = selected else {
            return Ok(None);
        };
        let domain = self.sampler.domain();
        let geom = PlaneGeometry {
            width: domain.width,
            height: domain.height,
        };
        let pass = session.frames[index].pass_index;
        let c = &calibrations[pass];
        let source = cache.load_or_decode(&session.frames[index], &identities[index])?;
        check_source(&source, c, domain.full)?;
        let sampled = self.sampler.gather(
            source.as_ref(),
            source.levels(),
            alignment.map.warps()[index]
                .placed()
                .context("unplaced precision guide")?,
            c.profile,
            alignment.map.resampler(),
        )?;
        crate::session_focus::complete_support(
            &sampled.support,
            geom,
            RADIUS,
            &mut self.mask_scratch,
            &mut self.support,
        )?;
        for channel in 0..4 {
            box_mean(
                &sampled.planes[channel],
                geom,
                RADIUS,
                &mut self.scratch,
                &mut self.common[channel],
            );
            for value in &mut self.common[channel] {
                *value *= gains[pass];
            }
        }
        self.acquisition = Some(index);
        Ok(Some(
            json!({"acquisition":index,"pass":pass,"log_scale_gap":gap,"members":members,"spatial_prediction_radius_quad":RADIUS,"supported_pixels":self.support.iter().filter(|&&v|v).count(),"selection":"nearest measured log scale outside every group member; not proof of matching focus","variance_scope":"conditional on frozen excluded-acquisition guide and adaptive eligibility; reuse in other groups is not independent"}),
        ))
    }
    pub(super) fn prediction(&mut self, source_gain: f32) -> Result<Option<FrozenPrediction<'_>>> {
        let Some(index) = self.acquisition else {
            return Ok(None);
        };
        ensure!(
            source_gain.is_finite() && source_gain > 0.0,
            "invalid precision source gain"
        );
        for c in 0..4 {
            for (i, value) in self.source_signal[c].iter_mut().enumerate() {
                *value = self.common[c][i] / source_gain;
            }
        }
        Ok(Some(FrozenPrediction {
            acquisition: index as u64,
            signal: std::array::from_fn(|c| self.source_signal[c].as_slice()),
            support: &self.support,
        }))
    }
}
