// Original spatial CFA cue. Feature-gated, with an injected noise model.
use crate::{CfaPlane, noise::{Levels, NoiseModel}, plane::QuadSource};
use crate::align::{PlaneRef, Resampler, Similarity};
use rayon::prelude::*;

#[derive(Default, Debug)]
pub struct Cue {
    pub energy: Vec<f32>,
    pub variance: Vec<f32>,
    pub valid: Vec<bool>,
}
const H: [(isize,isize,f32);5] = [(0,0,1.0),(-1,0,-0.25),(1,0,-0.25),(0,-1,-0.25),(0,1,-0.25)];
fn response<S: QuadSource + ?Sized>(src: &S, levels: Levels, noise: &NoiseModel,
    x: usize, y: usize, shift: usize) -> Option<(f32,f32)> {
    let (mut response,mut variance) = (0.0,0.0);
    for (dx,dy,c) in H {
        let sx = (x as isize+dx) as usize;
        let sy = (y as isize+dy) as usize;
        let (row0,row1) = src.quad_rows(sy);
        let g1 = row0[2*sx+1] as f32;
        let g2 = row1[2*(sx+shift)] as f32;
        if g1 >= levels.white || g2 >= levels.white { return None; }
        let (s1,s2) = (g1-levels.black,g2-levels.black);
        response += c*(s1-s2);
        // Each of these ten original sensels occurs once in this filter.
        // Shared sensels across the three squared responses contribute to
        // each expectation; the responses are not independent observations.
        variance += c*c*(noise.variance(CfaPlane::G1,s1)+noise.variance(CfaPlane::G2,s2));
    }
    (response.is_finite() && variance.is_finite() && variance >= 0.0)
        .then_some((response,variance))
}
/// Source quad-centred energy and exact independent-sensel noise expectation.
/// Signed black subtraction is retained; no G1/G2 signal is labelled noise.
pub fn source_at<S: QuadSource + ?Sized>(src: &S, levels: Levels, noise: &NoiseModel,
    x: usize, y: usize) -> Option<(f32,f32)> {
    let geom = src.geometry();
    if x < 2 || y < 1 || x.checked_add(2)? >= geom.width || y.checked_add(1)? >= geom.height {
        return None;
    }
    let (cm,vm) = response(src,levels,noise,x,y,0)?;
    let (cp,vp) = response(src,levels,noise,x,y,1)?;
    let (cl,vl) = response(src,levels,noise,x-1,y,1)?;
    let energy = cm*cm+0.5*(cp*cp+cl*cl);
    let variance = vm+0.5*(vp+vl);
    (energy.is_finite() && variance.is_finite()).then_some((energy,variance))
}
/// A single source frame's cue, pulled into the compact reference domain.
/// Original source fields are dropped before the real image gather begins.
pub fn prepare<S: QuadSource + Sync + ?Sized>(src: &S, levels: Levels, noise: &NoiseModel,
    pull: Similarity, crop: [usize;4]) -> Cue {
    let geom = src.geometry();
    let [left,top,width,height] = crop;
    assert!(width > 0 && height > 0 && left+width <= geom.width && top+height <= geom.height);
    let mut source_energy = vec![f32::NAN;geom.pixels()];
    let mut source_variance = vec![f32::NAN;geom.pixels()];
    source_energy.par_chunks_mut(geom.width).zip(source_variance.par_chunks_mut(geom.width))
        .enumerate().for_each(|(y,(er,vr))| {
            for x in 0..geom.width {
                if let Some((e,v)) = source_at(src,levels,noise,x,y) { er[x]=e; vr[x]=v; }
            }
        });
    let ep = PlaneRef::from_geometry(&source_energy,geom).unwrap();
    let vp = PlaneRef::from_geometry(&source_variance,geom).unwrap();
    let n = width*height;
    let mut cue = Cue {energy:vec![0.0;n],variance:vec![0.0;n],valid:vec![false;n]};
    let (cx,cy) = (0.5*geom.width as f64,0.5*geom.height as f64);
    cue.energy.par_chunks_mut(width).zip(cue.variance.par_chunks_mut(width))
        .zip(cue.valid.par_chunks_mut(width)).enumerate().for_each(|(y,((er,vr),valid))| {
            for x in 0..width {
                // Native quad centre is (2*qx+.5,2*qy+.5).
                let (sx,sy) = pull.apply_at((left+x) as f64+0.25,(top+y) as f64+0.25,cx,cy);
                let e = Resampler::Bilinear.sample_checked(ep,sx-0.25,sy-0.25);
                let v = Resampler::Bilinear.sample_checked(vp,sx-0.25,sy-0.25);
                if let (Some(e),Some(v)) = (e,v) {
                    if e.is_finite() && v.is_finite() && e >= 0.0 && v >= 0.0 {
                        er[x]=e; vr[x]=v; valid[x]=true;
                    }
                }
            }
        });
    drop(source_energy); drop(source_variance);
    let before = cue.valid.clone();
    cue.valid.par_chunks_mut(width).enumerate().for_each(|(y,row)| {
        for (x,v) in row.iter_mut().enumerate() {
            *v = x >= 2 && y >= 2 && x+2 < width && y+2 < height
                && (y-2..=y+2).all(|sy| (x-2..=x+2).all(|sx| before[sy*width+sx]));
        }
    });
    let size = super::LevelSize {width,height};
    let mut scratch = vec![0.0;n+width];
    super::smooth5(&mut cue.energy,size,&mut scratch);
    super::smooth5(&mut cue.variance,size,&mut scratch);
    cue
}
