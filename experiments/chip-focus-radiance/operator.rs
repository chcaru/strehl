// Experiment-only full-radiance average. No pyramid weights, source election or fit.
use anyhow::{ensure, Context, Result};
use rayon::prelude::*;
use serde::Serialize;

#[derive(Clone, Debug, Serialize)]
pub struct Front {
    pub frames: usize,
    pub xy_center: [f32; 2],
    pub xy_scale: [f32; 2],
    pub plane: [f32; 3],
    pub schedule_knots: Vec<f32>,
    pub schedule_values: Vec<f32>,
    pub sigma: f32,
}
impl Front {
    pub fn from_model(v: &serde_json::Value) -> Result<Self> {
        ensure!(v["schema"] == 1 && v["status"] == "fit_completed"
            && v["fit"]["converged"] == true, "model is not the completed fixed fit");
        let widths: [f32; 2] = serde_json::from_value(v["widths"].clone())?;
        let front = Self {
            frames: serde_json::from_value(v["frames"].clone())?,
            xy_center: serde_json::from_value(v["xy_center"].clone())?,
            xy_scale: serde_json::from_value(v["xy_scale"].clone())?,
            plane: serde_json::from_value(v["plane"].clone())?,
            schedule_knots: serde_json::from_value(v["schedule_knots"].clone())?,
            schedule_values: serde_json::from_value(v["schedule_values"].clone())?,
            sigma: widths[0],
        };
        front.validate()?;
        Ok(front)
    }
    pub fn validate(&self) -> Result<()> {
        ensure!(self.frames >= 2 && self.frames <= 299, "invalid source count");
        ensure!(self.xy_center.iter().chain(&self.plane).all(|v| v.is_finite())
            && self.xy_scale.iter().all(|v| v.is_finite() && *v > 0.)
            && self.sigma.is_finite() && self.sigma > 0., "invalid spatial front/width");
        ensure!(self.schedule_knots.len() >= 2
            && self.schedule_knots.len() == self.schedule_values.len(), "invalid schedule shape");
        for v in [&self.schedule_knots, &self.schedule_values] {
            ensure!(v.iter().all(|x| x.is_finite()) && v.windows(2).all(|p| p[1] > p[0])
                && v[0] == 0. && v[v.len()-1] == 1., "schedule must increase from zero to one");
        }
        Ok(())
    }
    pub fn schedule(&self, index: usize) -> Result<f32> {
        ensure!(index < self.frames, "source index out of range");
        if index + 1 == self.frames { return Ok(1.); }
        let u = index as f32 / (self.frames - 1) as f32;
        let right = self.schedule_knots.partition_point(|x| *x <= u).min(self.schedule_knots.len()-1);
        let left = right - 1;
        let fraction = (u-self.schedule_knots[left]) / (self.schedule_knots[right]-self.schedule_knots[left]);
        Ok(self.schedule_values[left] + fraction*(self.schedule_values[right]-self.schedule_values[left]))
    }
    pub fn centre(&self, qx: usize, qy: usize) -> f32 {
        let x = (2.*qx as f32 + 0.5 - self.xy_center[0]) / self.xy_scale[0];
        let y = (2.*qy as f32 + 0.5 - self.xy_center[1]) / self.xy_scale[1];
        x*self.plane[0] + y*self.plane[1] + self.plane[2]
    }
    pub fn weight(&self, index: usize, qx: usize, qy: usize) -> Result<f32> {
        let d = (self.schedule(index)? - self.centre(qx,qy)) / self.sigma;
        let q = (-0.5*d*d).exp();
        ensure!(q.is_finite(), "nonfinite source weight");
        Ok(q)
    }
}

pub struct Output {
    pub planes: Vec<Vec<f32>>,
    pub mass: Vec<f32>,
    pub centre: Vec<f32>,
    pub source_count: usize,
}
pub struct Stream {
    front: Front,
    centre: Vec<f32>,
    sums: [Vec<f32>;4],
    mass: Vec<f32>,
    next: usize,
}
impl Stream {
    pub fn new(width:usize,height:usize,front:Front) -> Result<Self> {
        front.validate()?;
        let n = width.checked_mul(height).context("spatial extent overflow")?;
        ensure!(n > 0, "empty spatial extent");
        let centre = (0..n).map(|j| front.centre(j%width,j/width)).collect::<Vec<_>>();
        ensure!(centre.iter().all(|z| z.is_finite()), "nonfinite spatial front");
        Ok(Self {front,centre,sums:std::array::from_fn(|_|vec![0.;n]),mass:vec![0.;n],next:0})
    }
    pub fn add(&mut self,index:usize,planes:&[Vec<f32>]) -> Result<()> {
        ensure!(index == self.next && index < self.front.frames, "sources must occur once in ascending order");
        ensure!(planes.len()==4 && planes.iter().all(|p|p.len()==self.mass.len())
            && planes.par_iter().all(|p|p.par_iter().all(|v|v.is_finite())), "invalid consumed CFA planes");
        let t=self.front.schedule(index)?;
        let sigma=self.front.sigma;
        let [r,g1,g2,b]=&mut self.sums;
        r.par_chunks_mut(4096).zip(g1.par_chunks_mut(4096)).zip(g2.par_chunks_mut(4096))
            .zip(b.par_chunks_mut(4096)).zip(self.mass.par_chunks_mut(4096)).enumerate()
            .for_each(|(chunk,((((r,g1),g2),b),mass))| {
                for j in 0..mass.len() {
                    let p=chunk*4096+j;
                    let d=(t-self.centre[p])/sigma;
                    let q=(-0.5*d*d).exp();
                    mass[j]+=q;
                    r[j]+=q*planes[0][p];g1[j]+=q*planes[1][p];
                    g2[j]+=q*planes[2][p];b[j]+=q*planes[3][p];
                }
            });
        self.next+=1;
        Ok(())
    }
    pub fn finish(mut self) -> Result<Output> {
        ensure!(self.next==self.front.frames, "incomplete source coverage");
        ensure!(self.mass.par_iter().all(|d|d.is_finite()&&*d>0.)
            && self.sums.par_iter().all(|p|p.par_iter().all(|v|v.is_finite())),
            "whole candidate refused: nonpositive/nonfinite mass or nonfinite radiance sum");
        self.sums.par_iter_mut().for_each(|p|p.par_iter_mut().zip(&self.mass).for_each(|(v,d)|*v/=*d));
        ensure!(self.sums.par_iter().all(|p|p.par_iter().all(|v|v.is_finite())),
            "whole candidate refused: nonfinite normalized radiance");
        Ok(Output {planes:self.sums.into_iter().collect(),mass:self.mass,centre:self.centre,source_count:self.next})
    }
}

#[cfg(test)]
mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/chip-focus-radiance/independent-controls.rs"));
}
