// Same original-source injected noise and actual GPU route as the frozen boundary probe.
pub(crate) const PROBE_PAIRS: usize = 8;
pub(crate) type GuideBands = [Vec<Vec<f32>>;3]; // R, (G1+G2)/2, B; AC only.

pub(crate) fn guide_laplacians(known4: &[Vec<f32>], sizes: &[LevelSize]) -> Result<GuideBands> {
    ensure!(sizes.len()>=2 && known4.len()==4 && known4.iter().all(|p|
        p.len()==sizes[0].pixels() && p.iter().all(|v|v.is_finite())),"guide shape/values");
    let green=known4[1].iter().zip(&known4[2]).map(|(a,b)|0.5*(a+b)).collect::<Vec<_>>();
    Ok([&known4[0],&green,&known4[3]].map(|p| kernels::laplacian(p,sizes)))
}
pub(crate) struct NoiseEnergy { sizes:Vec<LevelSize>, sums:GuideBands, pairs:usize }
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
    /// Per-coefficient variance followed by the actual energy support, without gate.
    pub(crate) fn finish(mut self)->Result<GuideBands> {
        ensure!(self.pairs==PROBE_PAIRS,"exactly eight independent pairs required");
        for c in 0..3 {for k in 0..self.sums[c].len() {
            for v in &mut self.sums[c][k] {*v/=(2*PROBE_PAIRS) as f32;}
            self.sums[c][k]=kernels::smooth(&self.sums[c][k],self.sizes[k]);
            ensure!(self.sums[c][k].iter().all(|v|v.is_finite() && *v>=0.0),"probe energy invalid");
        }}Ok(self.sums)
    }
}
pub(crate) struct ProbeEvidence {
    pub energy3:GuideBands,
    pub seeds:[usize;16],
    pub active_sha256:String,
    pub pair_band_means3:Vec<Vec<[f64;3]>>,
}
pub(crate) fn active_hash(frame:&Frame)->String {
    let mut h=Sha256::new();
    for y in 0..frame.active.height {
        let mut bytes=Vec::with_capacity(frame.active.width*2);
        for v in frame.active_row(y) {bytes.extend_from_slice(&v.to_le_bytes());}
        h.update(&bytes);
    }
    h.finalize().iter().map(|b|format!("{b:02x}")).collect()
}
/// Content-derived source identity; frame order, filename and warp do not choose the draws.
pub(crate) fn source_seeds(active_sha256:&str)->Result<[usize;16]> {
    ensure!(active_sha256.len()==64 && active_sha256.bytes().all(|b|b.is_ascii_hexdigit()),"source SHA256 required");
    let seeds=std::array::from_fn(|draw| {
        let mut h=Sha256::new();h.update(b"strehl-rb-own-guide-probe-v1\0");
        h.update(active_sha256.as_bytes());h.update((draw as u64).to_le_bytes());
        let digest=h.finalize();let mut bytes=[0u8;8];bytes.copy_from_slice(&digest[..8]);
        (u64::from_le_bytes(bytes)&0x7fff_ffff_ffff_ffff) as usize
    });
    ensure!((0..16).all(|i|!seeds[..i].contains(&seeds[i])),"probe seed collision");Ok(seeds)
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
        let a=member(2*pair)?;let b=member(2*pair+1)?;
        energy.add_pair(&a,&b)?;
        if diagnostics {
            pair_band_means3.push((0..sizes.len()-1).map(|k|std::array::from_fn(|c|
                a[c][k].iter().zip(&b[c][k]).map(|(&x,&y)| {
                    let d=x as f64-y as f64;0.5*d*d
                }).sum::<f64>()/a[c][k].len() as f64)).collect());
        }
    }
    Ok(ProbeEvidence {energy3:energy.finish()?,seeds,active_sha256,pair_band_means3})
}
