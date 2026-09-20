// Feature-gated prescribed-source counterfactual, not a production selector.
use super::{AdmissionMode, BandMerge, BaseBand, Fallback, Hull, LevelSize,
    Pyramid, SelectMode, Workspace};

fn supported(merge:&BandMerge) {
    assert!(merge.frames>0 && merge.planes==4);
    assert!(merge.cfg.select==SelectMode::SoftPower && merge.cfg.fallback==Fallback::Mean
        && merge.cfg.base==BaseBand::Mean && merge.cfg.hull==Hull::InputRange
        && merge.cfg.admission==AdmissionMode::HardFloor && merge.cfg.mean_coarse==0,
        "donor diagnostic requires the held baseline modes");
}

include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/donor-consistency/core-attribution.rs"));
include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/donor-consistency/spatial-donor.rs"));
/// The actual default BandMerge denominator/fallback resolution, before collapse.
/// Public only under the experiment feature so controls can compare coefficients.
pub fn resolved_coefficients(merge:&BandMerge)->Vec<Pyramid> {
    supported(merge);
    let inv_n=1.0/merge.frames as f32;
    (0..merge.planes).map(|c|{
        let mut out=Pyramid::zeros(&merge.sizes);
        for k in 0..merge.sizes.len() {
            let i=k*merge.planes+c;
            for (j,v) in out.level_mut(k).iter_mut().enumerate() {
                *v=if merge.den[k][j]>0.0 {merge.num[i][j]/merge.den[k][j]}
                    else {merge.usum[i][j]*inv_n};
            }
        }
        out
    }).collect()
}

pub struct DonorBlend {
    sizes:Vec<LevelSize>,
    planes:usize,
    masks:Vec<Pyramid>,
    coverage:Pyramid,
    sums:Vec<Pyramid>,
    seen:Vec<bool>,
    overlap:Vec<usize>,
    normalized:Vec<usize>,
}
impl DonorBlend {
    pub fn new(sizes:&[LevelSize],planes:usize,masks0:&[Vec<f32>])->Self {
        assert!(sizes.len()>=2 && planes==4 && masks0.len()<=8);
        let mut ws=Workspace::new(sizes);
        let mut masks=masks0.iter().map(|src|{
            assert_eq!(src.len(),sizes[0].pixels());
            assert!(src.iter().all(|v|v.is_finite() && (0.0..=1.0).contains(v)));
            let mut p=Pyramid::zeros(sizes);p.build_gaussian(src,&mut ws);p
        }).collect::<Vec<_>>();
        let mut coverage=Pyramid::zeros(sizes);
        let mut overlap=vec![0;sizes.len()];let mut normalized=vec![0;sizes.len()];
        for k in 0..sizes.len() {for j in 0..sizes[k].pixels() {
            let total=masks.iter().map(|m|m.level(k)[j]).sum::<f32>();
            let members=masks.iter().filter(|m|m.level(k)[j]>0.0).count();
            overlap[k]+=usize::from(members>1);
            if total>1.0 {
                normalized[k]+=1;
                for m in &mut masks {m.level_mut(k)[j]/=total;}
            }
            // Same divisor for every region, preserving relative membership.
            coverage.level_mut(k)[j]=if total>1.0 {1.0} else {total};
        }}
        Self{sizes:sizes.to_vec(),planes,masks,coverage,
            sums:(0..planes).map(|_|Pyramid::zeros(sizes)).collect(),
            seen:vec![false;masks0.len()],overlap,normalized}
    }
    pub fn masks(&self)->&[Pyramid] {&self.masks}
    pub fn coverage(&self)->&Pyramid {&self.coverage}
    pub fn raw_overlap_counts(&self)->&[usize] {&self.overlap}
    pub fn normalized_counts(&self)->&[usize] {&self.normalized}
    /// Accumulate one currently gathered source into its prescribed regions.
    /// No donor source image or N-source coefficient volume is retained.
    pub fn add_source(&mut self,mask_indices:&[usize],planes:&[Vec<f32>]) {
        assert_eq!(planes.len(),self.planes);
        assert!(!mask_indices.is_empty());
        for (i,&r) in mask_indices.iter().enumerate() {
            assert!(r<self.masks.len() && !self.seen[r] && !mask_indices[..i].contains(&r),
                "duplicate or invalid prescribed donor region");
        }
        let mut ws=Workspace::new(&self.sizes);
        let mut donor=Pyramid::zeros(&self.sizes);
        for (c,source) in planes.iter().enumerate() {
            assert_eq!(source.len(),self.sizes[0].pixels());
            assert!(source.iter().all(|v|v.is_finite()));
            donor.build(source,&mut ws);
            for k in 0..self.sizes.len()-1 {for &r in mask_indices {
                for ((sum,&m),&v) in self.sums[c].level_mut(k).iter_mut()
                    .zip(self.masks[r].level(k)).zip(donor.level(k)) {
                    if m>0.0 {*sum+=m*v;}
                }
            }}
        }
        for &r in mask_indices {self.seen[r]=true;}
    }
    fn check(&self,merge:&BandMerge) {
        supported(merge);assert_eq!(merge.sizes,self.sizes);assert_eq!(merge.planes,self.planes);
        for (r,m) in self.masks.iter().enumerate() {
            let active=(0..self.sizes.len()-1).any(|k|m.level(k).iter().any(|&v|v>0.0));
            assert!(!active || self.seen[r],"prescribed region has no actual donor");
        }
    }
    pub fn mixed_coefficients(&self,merge:&BandMerge)->Vec<Pyramid> {
        self.check(merge);
        let mut result=resolved_coefficients(merge);
        for (c,p) in result.iter_mut().enumerate() {for k in 0..self.sizes.len()-1 {
            for ((v,&m),&donor) in p.level_mut(k).iter_mut()
                .zip(self.coverage.level(k)).zip(self.sums[c].level(k)) {
                if m==1.0 {*v=donor;}
                else if m>0.0 {*v=(1.0-m)* *v+donor;}
                // Exactly zero means no new arithmetic on the baseline value.
                assert!(v.is_finite());
            }
        }}
        result
    }
    pub fn finish(&self,merge:&BandMerge,ws:&mut Workspace)->Vec<Vec<f32>> {
        self.check(merge);
        if (0..self.sizes.len()-1).all(|k|self.coverage.level(k).iter().all(|&v|v==0.0)) {
            return merge.finish(ws);
        }
        self.mixed_coefficients(merge).into_iter().enumerate().map(|(c,p)|{
            let mut out=p.collapse(ws);
            for ((v,&lo),&hi) in out.iter_mut().zip(&merge.lo[c]).zip(&merge.hi[c]) {
                *v=v.clamp(lo,hi);
            }
            assert!(out.iter().all(|v|v.is_finite()));out
        }).collect()
    }
}
