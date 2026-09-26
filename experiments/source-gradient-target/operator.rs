// Targets only: origin-weighted source coefficient differences. No integration.
use anyhow::{ensure, Result};
use strehl_core::pyramid::{LevelSize,Pyramid};

// Same guard scale and division order as the current SoftPower numerator.
const NUMERATOR_SCALE:f32=65536.;

#[derive(Clone,Debug)]
pub struct Gradient {pub dx:Vec<f32>,pub dy:Vec<f32>}

pub fn edge_masks(size:&LevelSize)->[Vec<bool>;2] {
    [(0..size.pixels()).map(|j|j%size.width+1<size.width).collect(),
     (0..size.pixels()).map(|j|j/size.width+1<size.height).collect()]
}
pub fn forward(values:&[f32],size:&LevelSize)->Result<Gradient> {
    ensure!(size.width>0&&size.height>0&&values.len()==size.pixels()
        &&values.iter().all(|v|v.is_finite()),"invalid coefficient field");
    let mut out=Gradient{dx:vec![0.;values.len()],dy:vec![0.;values.len()]};
    for y in 0..size.height {for x in 0..size.width {
        let j=y*size.width+x;
        if x+1<size.width {out.dx[j]=values[j+1]-values[j];}
        if y+1<size.height {out.dy[j]=values[j+size.width]-values[j];}
    }}
    ensure!(out.dx.iter().chain(&out.dy).all(|v|v.is_finite()),"coefficient difference overflow");
    Ok(out)
}
fn zeros(sizes:&[LevelSize])->Vec<Vec<Gradient>> {
    (0..4).map(|_|sizes[..sizes.len()-1].iter().map(|s|
        Gradient{dx:vec![0.;s.pixels()],dy:vec![0.;s.pixels()]}).collect()).collect()
}
pub struct Target {
    /// channel, AC level. Terminal target is supplied unchanged by the consumer.
    pub gradients:Vec<Vec<Gradient>>,
    pub denominator:Vec<Vec<f32>>,
    pub source_count:usize,
}
pub struct Accumulator {
    sizes:Vec<LevelSize>,frames:usize,next:usize,
    denominator:Vec<Vec<f32>>,
    weighted:Vec<Vec<Gradient>>,unweighted:Vec<Vec<Gradient>>,
}
impl Accumulator {
    pub fn new(sizes:&[LevelSize],frames:usize)->Result<Self> {
        ensure!(sizes.len()>=2&&frames>0&&sizes.iter().all(|s|s.width>0&&s.height>0),"empty target geometry/sources");
        Ok(Self{sizes:sizes.to_vec(),frames,next:0,
            denominator:sizes[..sizes.len()-1].iter().map(|s|vec![0.;s.pixels()]).collect(),
            weighted:zeros(sizes),unweighted:zeros(sizes)})
    }
    pub fn add(&mut self,index:usize,coefficients:&[Pyramid],weights:&[Vec<f32>])->Result<()> {
        ensure!(index==self.next&&index<self.frames,"sources must occur once in ascending order");
        let nb=self.sizes.len()-1;
        ensure!(coefficients.len()==4&&coefficients.iter().all(|p|p.levels()==self.sizes.len())
            &&weights.len()==nb,"invalid source target shape");
        for k in 0..nb {
            let size=&self.sizes[k];let w=&weights[k];
            ensure!(w.len()==size.pixels()&&w.iter().all(|v|v.is_finite()&&*v>=0.),"invalid canonical weights");
            for (d,w) in self.denominator[k].iter_mut().zip(w) {*d+=*w;}
            for c in 0..4 {
                let source=forward(coefficients[c].level(k),size)?;
                let num=&mut self.weighted[c][k];let mean=&mut self.unweighted[c][k];
                for j in 0..size.pixels() {
                    // Weight at edge origin, never an endpoint-averaged variant.
                    num.dx[j]+=w[j]*(source.dx[j]/NUMERATOR_SCALE);
                    num.dy[j]+=w[j]*(source.dy[j]/NUMERATOR_SCALE);
                    mean.dx[j]+=source.dx[j];mean.dy[j]+=source.dy[j];
                }
                ensure!(num.dx.iter().chain(&num.dy).chain(&mean.dx).chain(&mean.dy).all(|v|v.is_finite()),
                    "source-gradient accumulation overflow");
            }
            ensure!(self.denominator[k].iter().all(|v|v.is_finite()),"weight denominator overflow");
        }
        self.next+=1;Ok(())
    }
    pub fn finish(mut self)->Result<Target> {
        ensure!(self.next==self.frames,"incomplete source coverage");let inv=1./self.frames as f32;
        for c in 0..4 {for k in 0..self.sizes.len()-1 {
            let num=&mut self.weighted[c][k];let mean=&self.unweighted[c][k];
            for j in 0..self.sizes[k].pixels() {
                let d=self.denominator[k][j];
                num.dx[j]=if d>0. {(num.dx[j]/d)*NUMERATOR_SCALE}else{mean.dx[j]*inv};
                num.dy[j]=if d>0. {(num.dy[j]/d)*NUMERATOR_SCALE}else{mean.dy[j]*inv};
            }
            ensure!(num.dx.iter().chain(&num.dy).all(|v|v.is_finite()),"nonfinite resolved source-gradient target");
        }}
        Ok(Target{gradients:self.weighted,denominator:self.denominator,source_count:self.next})
    }
}
