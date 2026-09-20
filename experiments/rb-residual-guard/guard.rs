// F(1,8) scalar model, not an empirically calibrated camera false-alarm guarantee.
pub(crate) fn f1_8_tail(t:f64)->Result<f64> {
    ensure!(!t.is_nan() && t>=0.0,"invalid F statistic");
    if t==f64::INFINITY {return Ok(0.0);}
    // Integrate (1-u^2)^3 from sqrt(t/(8+t)) to1. Factored near1 to avoid cancellation.
    let r=8.0/(8.0+t);let z=r/(1.0+(t/(8.0+t)).sqrt());
    Ok((35.0/16.0)*z.powi(4)*(2.0-2.4*z+z*z-z*z*z/7.0))
}
pub(crate) fn f1_8_quantile_tail(p:f64)->Result<f64> {
    ensure!(p.is_finite() && p>0.0 && p<=1.0,"tail probability outside(0,1]");
    if p==1.0 {return Ok(0.0);}
    let mut lo=0.0;let mut hi=1.0;
    while f1_8_tail(hi)?>p {hi*=2.0;ensure!(hi.is_finite(),"F threshold overflow");}
    for _ in 0..100 {let mid=lo+0.5*(hi-lo);if f1_8_tail(mid)?>p {lo=mid;}else{hi=mid;}}
    Ok(lo+0.5*(hi-lo))
}
pub(crate) fn threshold(n:usize,nb:usize)->Result<f64> {
    ensure!(n>=2 && nb>0,"source/band count required");
    let tests=2usize.checked_mul(n).and_then(|v|v.checked_mul(nb)).and_then(|v|v.checked_mul(25))
        .ok_or_else(||anyhow::anyhow!("multiplicity overflow"))?;
    f1_8_quantile_tail(0.01/tests as f64)
}
pub(crate) fn threshold_f32(n:usize,nb:usize)->Result<f32> {
    let q=threshold(n,nb)?;let mut value=q as f32;
    ensure!(value.is_finite() && value>0.0,"f32 threshold overflow");
    if (value as f64)<q {value=f32::from_bits(value.to_bits()+1);}
    ensure!(value.is_finite(),"upward threshold overflow");Ok(value)
}
pub(crate) struct Activation {
    sizes:Vec<LevelSize>,n:usize,q:f32,masks:[Vec<Vec<f32>>;2],
    source_triggers:Vec<[Vec<usize>;2]>,
}
impl Activation {
    pub(crate) fn new(sizes:&[LevelSize],n:usize,q:f64)->Result<Self> {
        ensure!(n>=2 && n<=16,"bounded activation source count required");
        ensure!(sizes.len()>=2 && sizes.iter().all(|s|s.width>0 && s.height>0),"invalid band sizes");
        ensure!(q.is_finite() && q>0.0 && q.to_bits()==threshold(n,sizes.len()-1)?.to_bits(),"fixed threshold differs");
        Ok(Self {sizes:sizes.to_vec(),n,q:threshold_f32(n,sizes.len()-1)?,masks:std::array::from_fn(|_|sizes[..sizes.len()-1]
            .iter().map(|s|vec![0.0;s.pixels()]).collect()),source_triggers:vec![]})
    }
    pub(crate) fn add_source(&mut self,signal:&GuideBands,variance:&GuideBands)->Result<()> {
        ensure!(self.source_triggers.len()<self.n,"too many activation sources");let nb=self.sizes.len()-1;
        for c in 0..3 {
            ensure!(signal[c].len()==nb && variance[c].len()==nb,"activation band count");
            for k in 0..nb {
                ensure!(signal[c][k].len()==self.sizes[k].pixels() && variance[c][k].len()==self.sizes[k].pixels(),"activation shape");
                ensure!(signal[c][k].iter().all(|v|v.is_finite()) && variance[c][k].iter().all(|v|v.is_finite() && *v>=0.0),"invalid activation values");
            }
        }
        let mut counts:[Vec<usize>;2]=std::array::from_fn(|_|vec![0;nb]);
        for (i,c) in [0,2].into_iter().enumerate() {for k in 0..nb {
            let size=self.sizes[k];let mut hits=vec![false;size.pixels()];
            for j in 0..hits.len() {
                let v=variance[c][k][j];
                let l=signal[c][k][j];let power=l*l;let bound=self.q*v;
                ensure!(power.is_finite() && bound.is_finite(),"activation product overflow");
                hits[j]=v>0.0 && power>bound;counts[i][k]+=usize::from(hits[j]);
            }
            for y in 0..size.height {for x in 0..size.width {
                if self.masks[i][k][y*size.width+x]!=0.0 {continue;}
                let any=(0..5).any(|dy| {
                    let yy=(y+dy).saturating_sub(2).min(size.height-1);
                    (0..5).any(|dx| {
                        let xx=(x+dx).saturating_sub(2).min(size.width-1);hits[yy*size.width+xx]
                    })
                });
                if any {self.masks[i][k][y*size.width+x]=1.0;}
            }}
        }}
        self.source_triggers.push(counts);Ok(())
    }
    pub(crate) fn source_trigger_counts_rb(&self)->&Vec<[Vec<usize>;2]> {&self.source_triggers}
    pub(crate) fn finish(self)->Result<[Vec<Vec<f32>>;2]> {
        ensure!(self.source_triggers.len()==self.n,"missing activation source");Ok(self.masks)
    }
}
