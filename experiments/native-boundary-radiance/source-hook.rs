// Feature-only adapter: original CFA observations and the existing collapsed planes.
use super::{band_slot, Frame, Levels, NoiseModel, PyramidDomain, PyramidFrameSource};
use strehl_core::{CfaPlane, align::Similarity, warpmap::{FrameWarp, WarpMap}};
use std::sync::Mutex;

#[derive(Clone, Copy, Debug)]
pub(crate) enum Configuration {
    NoTreatment,
    M194g { boundary_offset: f32 },
}

pub(crate) struct ConfiguredSource<'a, S> {
    source: &'a S,
    configuration: Option<Configuration>,
}
impl<'a, S: PyramidFrameSource> ConfiguredSource<'a, S> {
    pub(crate) fn new(source: &'a S, configuration: Configuration) -> Self {
        Self { source, configuration:Some(configuration) }
    }
    pub(crate) fn optional(source: &'a S, configuration: Option<Configuration>) -> Self {
        Self { source, configuration }
    }
}
impl<S: PyramidFrameSource> PyramidFrameSource for ConfiguredSource<'_, S> {
    fn len(&self) -> usize { self.source.len() }
    fn decode(&self, index: usize) -> Result<Frame> { self.source.decode(index) }
    fn boundary_config(&self) -> Option<Configuration> { self.configuration }
}

struct Target {
    x: usize,
    y: usize,
    plane: usize,
    output_index: usize,
    output_row: [f32; 6],
    system: NormalSystem,
}
struct Accumulator {
    boundary_offset: f32,
    targets: Vec<Target>,
    seen: [bool; 5],
    closed: bool,
}
impl Accumulator {
    fn new(boundary_offset: f32, domain: PyramidDomain, count: usize,
        warps: Option<&WarpMap>) -> Result<Self>
    {
        ensure!(boundary_offset == 142.0 || boundary_offset == 146.0,
            "boundary prototype requires the fixed true or displaced M194g boundary");
        ensure!(count == 5 && domain.full.width == 160 && domain.full.height == 120,
            "boundary prototype requires all five explicitly declared 320x240 M194g frames");
        let map = warps.ok_or_else(|| anyhow::anyhow!("boundary prototype requires supplied identity geometry"))?;
        ensure!(map.warps().len() == 5 && map.warps().iter().all(|w|
            matches!(w, FrameWarp::Placed(t) if *t == Similarity::IDENTITY)),
            "boundary prototype does not support transformed or refused M194g frames");
        let mut targets = Vec::new();
        for y in 2*domain.rect.y..2*(domain.rect.y+domain.rect.height) {
            for x in 2*domain.rect.x..2*(domain.rect.x+domain.rect.width) {
                // The treatment support stays fixed for the displaced-model destroyer.
                if (x as f32 - 0.15*y as f32 - 142.0).abs() > 8.0
                    || x < NEIGHBOUR_RADIUS || y < NEIGHBOUR_RADIUS
                    || x+NEIGHBOUR_RADIUS >= 320 || y+NEIGHBOUR_RADIUS >= 240 { continue; }
                let p = [x as f32,y as f32];
                targets.push(Target { x,y,plane:band_slot(CfaPlane::rggb_at(x,y)),
                    output_index:(y/2-domain.rect.y)*domain.rect.width+x/2-domain.rect.x,
                    output_row:cell_moments([1.0,-0.15],boundary_offset,0.0,0.0,p,p),
                    system:NormalSystem::new() });
            }
        }
        ensure!(!targets.is_empty(), "boundary prototype has no supported target cells");
        Ok(Self { boundary_offset, targets, seen:[false;5], closed:false })
    }

    fn observe(&mut self, index: usize, frame: &Frame, levels: Levels, noise: &NoiseModel) -> Result<()> {
        if self.closed { return Ok(()); }
        ensure!(index < 5 && index == self.seen.iter().filter(|v| **v).count() && !self.seen[index],
            "boundary source frame duplicated or outside fixed original ordering");
        ensure!(frame.active.x == 0 && frame.active.y == 0
            && frame.active.width == 320 && frame.active.height == 240,
            "boundary oracle requires the original M194g native coordinate domain");
        let focus = [0.5,0.625,0.75,0.875,1.0][index];
        let d_f = 12.0*(focus-1.0);
        let d_b = 12.0*(focus-0.5);
        // Only the narrow source strip needed by the fixed radius-two supports
        // is cached, for this frame alone. No image samples or aligned frames persist.
        let rows: Vec<_> = (0..240).map(|y| {
            let centre = 142.0+0.15*y as f32;
            let start = ((centre-11.0).floor() as usize).min(319);
            let end = ((centre+11.0).ceil() as usize).min(319);
            let moments = (start..=end).map(|x| {
                let s = [x as f32,y as f32];
                cell_moments([1.0,-0.15],self.boundary_offset,d_f,d_b,s,s)
            }).collect::<Vec<_>>();
            (start,moments)
        }).collect();
        for target in &mut self.targets {
            let spectral = |p| match p { CfaPlane::R=>0, CfaPlane::B=>2, _=>1 };
            let colour = spectral(CfaPlane::rggb_at(target.x,target.y));
            for y in target.y-NEIGHBOUR_RADIUS..=target.y+NEIGHBOUR_RADIUS {
                for x in target.x-NEIGHBOUR_RADIUS..=target.x+NEIGHBOUR_RADIUS {
                    let plane = CfaPlane::rggb_at(x,y);
                    if spectral(plane) != colour { continue; }
                    let (start,moments) = &rows[y];
                    let mut row = *moments.get(x-*start).ok_or_else(||
                        anyhow::anyhow!("boundary moment strip does not contain declared support"))?;
                    let dx = x as f32-target.x as f32;
                    let dy = y as f32-target.y as f32;
                    row[1] += dx*row[0]; row[2] += dy*row[0];
                    row[4] += dx*row[3]; row[5] += dy*row[3];
                    let value = frame.data[y*frame.stride+x] as f32-levels.black;
                    target.system.add(row,value,noise.variance(plane,value));
                }
            }
        }
        self.seen[index] = true;
        Ok(())
    }

    fn apply(&mut self, planes: &mut [Vec<f32>]) -> Result<()> {
        ensure!(!self.closed && self.seen.iter().all(|v| *v),
            "boundary output requires each original frame exactly once");
        self.closed = true;
        let mut accepted = 0usize;
        let mut refusals = [0usize;5];
        let mut max_residual = 0.0f32;
        let mut max_variance = 0.0f32;
        let mut minimum_pivot = f32::INFINITY;
        for target in &self.targets {
            match target.system.solve(target.output_row) {
                Ok(fit) => {
                    ensure!(apply_estimate(&mut planes[target.plane][target.output_index],Some(&fit)),
                        "boundary solver returned an inapplicable accepted estimate");
                    accepted += 1;
                    max_residual = max_residual.max(fit.normalized_residual);
                    max_variance = max_variance.max(fit.variance);
                    minimum_pivot = minimum_pivot.min(fit.min_pivot);
                }
                Err(reason) => refusals[match reason {
                    Refusal::InsufficientObservations=>0, Refusal::RankDeficient=>1,
                    Refusal::NonFinite=>2, Refusal::NegativeEstimate=>3,
                    Refusal::ExcessVariance=>4 }] += 1,
            }
        }
        eprintln!("boundary radiance: {}",serde_json::json!({
            "configuration":"M194g-oracle-local-affine-v1","boundary_offset":self.boundary_offset,
            "targets":self.targets.len(),"accepted":accepted,"refusals":refusals,
            "refusal_order":["insufficient-observations","rank","nonfinite","negative","variance"],
            "maximum_normalized_residual":max_residual,"maximum_variance_dn2":max_variance,
            "minimum_normalized_schur_pivot":if accepted>0 { Some(minimum_pivot) } else { None },
            "source_frames":self.seen.len(),"radius_native":NEIGHBOUR_RADIUS,
            "residual_rejection":false
        }));
        Ok(())
    }
}

pub(super) struct ObservedSource<'a, S> {
    source: &'a S,
    levels: Levels,
    noise: &'a NoiseModel,
    accumulator: Option<Mutex<Accumulator>>,
    no_treatment: bool,
}
impl<'a, S: PyramidFrameSource> ObservedSource<'a, S> {
    pub(super) fn new(source: &'a S, levels: Levels, noise: &'a NoiseModel,
        domain: PyramidDomain, warps: Option<&WarpMap>) -> Result<Self>
    {
        let configuration = source.boundary_config();
        let accumulator = match configuration {
            Some(Configuration::M194g { boundary_offset }) =>
                Some(Mutex::new(Accumulator::new(boundary_offset,domain,source.len(),warps)?)),
            _ => None,
        };
        Ok(Self { source,levels,noise,accumulator,
            no_treatment:matches!(configuration,Some(Configuration::NoTreatment)) })
    }
    pub(super) fn finish(&self, planes: &mut [Vec<f32>]) -> Result<()> {
        if let Some(accumulator) = &self.accumulator {
            accumulator.lock().map_err(|_| anyhow::anyhow!("boundary accumulator poisoned"))?.apply(planes)?;
        } else if self.no_treatment {
            eprintln!("boundary radiance: {{\"configuration\":\"no-treatment\",\"accepted\":0}}");
        }
        Ok(())
    }
}
impl<S: PyramidFrameSource> PyramidFrameSource for ObservedSource<'_, S> {
    fn len(&self) -> usize { self.source.len() }
    fn decode(&self, index: usize) -> Result<Frame> { self.source.decode(index) }
    fn observe_boundary(&self, index: usize, frame: &Frame) -> Result<()> {
        if let Some(accumulator) = &self.accumulator {
            accumulator.lock().map_err(|_| anyhow::anyhow!("boundary accumulator poisoned"))?
                .observe(index,frame,self.levels,self.noise)?;
        }
        Ok(())
    }
}
