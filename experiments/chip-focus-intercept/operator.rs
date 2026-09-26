// Experiment-only fixed-front local quadratic intercept. Arithmetic is f32.
// No fitting of the front, width change, ridge, lower-degree fallback or clamp.
// The two-sided and condition limits are frozen before generated measurements.
use anyhow::{ensure, Context, Result};
use rayon::prelude::*;
pub use super::chip_focus_radiance::{Front, Stream as GaussianStream};

pub const CONDITION_LIMIT: f32 = 1e4;
pub const MIN_SIDE_FRACTION: f32 = 0.01;

#[derive(Clone, Default)]
struct Moments {
    m: [f32;5],                 // sum q delta^j, j=0..4
    t: [f32;5],                 // sum q^2 delta^j, j=0..4
    b: [[f32;3];4],             // sum q delta^j radiance_c, j=0..2
    side: [f32;2],              // q mass strictly below / above the fixed front
}

pub struct Stream {
    front: Front,
    centre: Vec<f32>,
    moments: Vec<Moments>,
    next: usize,
}

pub struct Output {
    pub planes: Vec<Vec<f32>>,
    pub centre: Vec<f32>,
    pub mass: Vec<f32>,
    /// Infinity-norm condition estimate of H/M0, using the actual f32 inverse.
    pub condition: Vec<f32>,
    /// Equal, independent unit-variance noise gain: sum of signed h_k squared.
    pub noise_gain: Vec<f32>,
    pub gaussian_noise_gain: Vec<f32>,
    pub left_fraction: Vec<f32>,
    pub right_fraction: Vec<f32>,
    pub source_count: usize,
    front: Front,
    inverse_row: Vec<[f32;3]>,
}

impl Output {
    /// Pure geometry evaluation for independent controls; never stores N images.
    pub fn equivalent_weight(&self,index:usize,site:usize) -> Result<f32> {
        ensure!(site<self.centre.len(),"spatial site out of range");
        let d=(self.front.schedule(index)?-self.centre[site])/self.front.sigma;
        let q=(-0.5*d*d).exp();
        ensure!(q.is_finite(),"nonfinite source weight");
        // Exact f32 Gaussian underflow contributes zero; avoid 0*overflow.
        if q==0. {return Ok(0.);}
        let v=self.inverse_row[site];
        let h=q*(v[0]+v[1]*d+v[2]*d*d);
        ensure!(h.is_finite(),"nonfinite equivalent weight");
        Ok(h)
    }
}

impl Stream {
    pub fn new(width:usize,height:usize,front:Front) -> Result<Self> {
        front.validate()?;
        let n=width.checked_mul(height).context("spatial extent overflow")?;
        ensure!(n>0,"empty spatial extent");
        let centre=(0..n).map(|j|front.centre(j%width,j/width)).collect::<Vec<_>>();
        ensure!(centre.iter().all(|z|z.is_finite()),"nonfinite spatial front");
        Ok(Self{front,centre,moments:vec![Moments::default();n],next:0})
    }
    pub fn add(&mut self,index:usize,planes:&[Vec<f32>]) -> Result<()> {
        ensure!(index==self.next&&index<self.front.frames,"sources must occur once in ascending order");
        ensure!(planes.len()==4&&planes.iter().all(|p|p.len()==self.moments.len())
            &&planes.par_iter().all(|p|p.par_iter().all(|v|v.is_finite())),"invalid consumed CFA planes");
        let t=self.front.schedule(index)?;let sigma=self.front.sigma;
        self.moments.par_iter_mut().enumerate().for_each(|(j,m)|{
            let d=(t-self.centre[j])/sigma;
            let q=(-0.5*d*d).exp();
            if q==0. {return;}
            let mut qd=q;let mut qqd=q*q;
            for k in 0..5 {
                m.m[k]+=qd;m.t[k]+=qqd;
                if k<3 {for c in 0..4 {m.b[c][k]+=qd*planes[c][j];}}
                qd*=d;qqd*=d;
            }
            if d<0. {m.side[0]+=q;}else if d>0. {m.side[1]+=q;}
        });
        self.next+=1;
        Ok(())
    }
    pub fn finish(self) -> Result<Output> {
        ensure!(self.next==self.front.frames,"incomplete source coverage");
        let Self{front,centre,moments,next}=self;
        // Any refused site aborts the entire output. No partial image escapes.
        let solved=moments.into_par_iter().enumerate().map(|(j,m)|
            solve_site(m).with_context(||format!("whole candidate refused at quad {j}")))
            .collect::<Result<Vec<_>>>()?;
        Ok(Output{
            planes:(0..4).map(|c|solved.iter().map(|s|s.radiance[c]).collect()).collect(),
            centre,mass:solved.iter().map(|s|s.mass).collect(),
            condition:solved.iter().map(|s|s.condition).collect(),
            noise_gain:solved.iter().map(|s|s.noise_gain).collect(),
            gaussian_noise_gain:solved.iter().map(|s|s.gaussian_noise_gain).collect(),
            left_fraction:solved.iter().map(|s|s.side[0]).collect(),
            right_fraction:solved.iter().map(|s|s.side[1]).collect(),
            source_count:next,front,inverse_row:solved.iter().map(|s|s.inverse_row).collect(),
        })
    }
}

struct Solved {
    radiance:[f32;4],inverse_row:[f32;3],mass:f32,condition:f32,
    noise_gain:f32,gaussian_noise_gain:f32,side:[f32;2],
}

fn infinity_norm(a:&[[f32;3];3])->f32 {
    a.iter().map(|r|r.iter().map(|v|v.abs()).sum::<f32>()).fold(0.,f32::max)
}

/// Cholesky inversion of the symmetric normalized moment matrix. Positive
/// pivots are required; there is no diagonal perturbation or pivot floor.
fn inverse(a:[[f32;3];3])->Result<[[f32;3];3]> {
    ensure!(a.iter().flatten().all(|v|v.is_finite())&&a[0][0]>0.,"invalid moment matrix");
    let l00=a[0][0].sqrt();let l10=a[1][0]/l00;let l20=a[2][0]/l00;
    let p11=a[1][1]-l10*l10;
    ensure!(p11.is_finite()&&p11>0.,"rank-deficient quadratic support");
    let l11=p11.sqrt();let l21=(a[2][1]-l20*l10)/l11;
    let p22=a[2][2]-l20*l20-l21*l21;
    ensure!(p22.is_finite()&&p22>0.,"rank-deficient quadratic support");
    let l22=p22.sqrt();let mut inv=[[0.;3];3];
    for c in 0..3 {
        let y0=if c==0 {1./l00}else{0.};
        let y1=((if c==1 {1.}else{0.})-l10*y0)/l11;
        let y2=((if c==2 {1.}else{0.})-l20*y0-l21*y1)/l22;
        let x2=y2/l22;let x1=(y1-l21*x2)/l11;let x0=(y0-l10*x1-l20*x2)/l00;
        inv[0][c]=x0;inv[1][c]=x1;inv[2][c]=x2;
    }
    ensure!(inv.iter().flatten().all(|v|v.is_finite()),"nonfinite inverse");
    Ok(inv)
}

fn solve_site(m:Moments)->Result<Solved> {
    ensure!(m.m.iter().chain(&m.t).chain(m.b.iter().flatten()).chain(&m.side)
        .all(|v|v.is_finite()),"nonfinite accumulated moments/radiance");
    let mass=m.m[0];ensure!(mass>0.,"nonpositive weight mass");
    let side=m.side.map(|s|s/mass);
    ensure!(side.iter().all(|s|s.is_finite()&&*s>=MIN_SIDE_FRACTION),"insufficient two-sided support");
    let a=std::array::from_fn(|r|std::array::from_fn(|c|m.m[r+c]/mass));
    let inv=inverse(a)?;
    let condition=infinity_norm(&a)*infinity_norm(&inv);
    ensure!(condition.is_finite()&&condition<=CONDITION_LIMIT,"ill-conditioned quadratic support");
    let v=inv[0].map(|x|x/mass);
    ensure!(v.iter().all(|x|x.is_finite()),"nonfinite intercept kernel");
    let radiance=m.b.map(|b|v[0]*b[0]+v[1]*b[1]+v[2]*b[2]);
    ensure!(radiance.iter().all(|x|x.is_finite()),"nonfinite intercept estimate");
    let mut noise_gain=0.;
    for r in 0..3 {for c in 0..3 {noise_gain+=v[r]*m.t[r+c]*v[c];}}
    let gaussian_noise_gain=(m.t[0]/mass)/mass;
    ensure!(noise_gain.is_finite()&&noise_gain>0.&&gaussian_noise_gain.is_finite()
        &&gaussian_noise_gain>0.,"invalid equal-variance noise propagation");
    Ok(Solved{radiance,inverse_row:v,mass,condition,noise_gain,gaussian_noise_gain,side})
}

#[cfg(test)]
mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/chip-focus-intercept/independent-controls.rs"));
}
