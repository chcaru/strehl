// Same frozen source draws / guide transforms, now retaining pre-smoothing variance.
pub(crate) const PROBE_PAIRS:usize=8;
pub(crate) struct NoiseResult {pub coefficient_variance3:GuideBands,pub energy3:GuideBands}
pub(crate) struct NoiseEnergy {sizes:Vec<LevelSize>,sums:GuideBands,pairs:usize}
impl NoiseEnergy {
    pub(crate) fn new(sizes:&[LevelSize])->Self {
        assert!(sizes.len()>=2);
        Self {sizes:sizes.to_vec(),sums:std::array::from_fn(|_|sizes[..sizes.len()-1]
            .iter().map(|s|vec![0.0;s.pixels()]).collect()),pairs:0}
    }
    pub(crate) fn add_pair(&mut self,a:&GuideBands,b:&GuideBands)->Result<()> {
        ensure!(self.pairs<PROBE_PAIRS,"too many independent probe pairs");
        for c in 0..3 {
            ensure!(a[c].len()==self.sums[c].len() && b[c].len()==self.sums[c].len(),"probe bands");
            for k in 0..self.sums[c].len() {
                ensure!(a[c][k].len()==self.sums[c][k].len() && b[c][k].len()==self.sums[c][k].len(),"probe band shape");
                for ((sum,&av),&bv) in self.sums[c][k].iter_mut().zip(&a[c][k]).zip(&b[c][k]) {
                    ensure!(av.is_finite() && bv.is_finite(),"probe nonfinite coefficient");
                    let d=av-bv;*sum+=d*d;
                }
            }
        }
        self.pairs+=1;Ok(())
    }
    pub(crate) fn finish(mut self)->Result<NoiseResult> {
        ensure!(self.pairs==PROBE_PAIRS,"exactly eight independent pairs required");
        for c in 0..3 {for k in 0..self.sums[c].len() {
            for v in &mut self.sums[c][k] {*v/=(2*PROBE_PAIRS) as f32;}
            ensure!(self.sums[c][k].iter().all(|v|v.is_finite() && *v>=0.0),"coefficient variance invalid");
        }}
        let energy3=std::array::from_fn(|c|self.sums[c].iter().enumerate()
            .map(|(k,v)|kernels::smooth(v,self.sizes[k])).collect());
        Ok(NoiseResult {coefficient_variance3:self.sums,energy3})
    }
}
pub(crate) struct ProbeEvidence {
    pub coefficient_variance3:GuideBands,pub energy3:GuideBands,pub seeds:[usize;16],
    pub active_sha256:String,pub pair_band_means3:Vec<Vec<[f64;3]>>,
}
pub(crate) fn probe_noise(frame:&Frame,warp:Similarity,crop:align_cmd::CropRect,noise:&NoiseModel,
    sizes:&[LevelSize],diagnostics:bool)->Result<ProbeEvidence> {
    let active_sha256=active_hash(frame);let seeds=source_seeds(&active_sha256)?;
    let variance=source_probe::original_variances(frame,noise)?;
    let mut energy=NoiseEnergy::new(sizes);let mut pair_band_means3=Vec::new();
    for pair in 0..PROBE_PAIRS {
        let member=|draw:usize|->Result<GuideBands> {
            let noisy=source_probe::noisy_source(frame,&variance,seeds[draw])?;
            let known4=source_probe::gather_known4(&noisy,warp,crop)?;
            guide_laplacians(&known4,sizes)
        };
        let a=member(2*pair)?;let b=member(2*pair+1)?;energy.add_pair(&a,&b)?;
        if diagnostics {pair_band_means3.push((0..sizes.len()-1).map(|k|std::array::from_fn(|c|
            a[c][k].iter().zip(&b[c][k]).map(|(&x,&y)| {
                let d=x as f64-y as f64;0.5*d*d
            }).sum::<f64>()/a[c][k].len() as f64)).collect());}
    }
    let result=energy.finish()?;
    Ok(ProbeEvidence {coefficient_variance3:result.coefficient_variance3,energy3:result.energy3,
        seeds,active_sha256,pair_band_means3})
}
