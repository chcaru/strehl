// Experiment-only access to actual retained finest evidence and whole-AC replay.
use super::{AdmissionMode,BandMerge,BaseBand,Fallback,FrameWorkspace,Hull,LevelSize,
    Pyramid,SelectMode,Workspace};
type Checked<T> = Result<T,String>;
fn require(ok:bool,message:&str)->Checked<()> {if ok{Ok(())}else{Err(message.into())}}
fn supported(merge:&BandMerge)->Checked<()> {
    require(merge.frames>0 && merge.planes==4 && merge.sizes.len()>=2
        && merge.cfg.select==SelectMode::SoftPower && merge.cfg.fallback==Fallback::Mean
        && merge.cfg.base==BaseBand::Mean && merge.cfg.hull==Hull::InputRange
        && merge.cfg.admission==AdmissionMode::HardFloor && merge.cfg.mean_coarse==0
        && merge.cfg.significance_scale==0.0,"held four-plane default merge modes required")
}
pub struct Fields {pub energy:Vec<f32>,pub floor:Vec<f32>}
pub fn finest_evidence(merge:&BandMerge,ws:&FrameWorkspace,frame_beta:Option<&[f32]>)->Checked<Fields> {
    supported(merge)?;let size=merge.sizes[0];
    require(ws.luma.sizes()==merge.sizes.as_slice() && ws.var.sizes()==merge.sizes.as_slice(),"retained evidence geometry mismatch")?;
    let mut energy=ws.luma.level(0).iter().map(|v|v*v).collect::<Vec<_>>();
    super::smooth5(&mut energy,size,&mut vec![0.0;size.pixels()+size.width]);
    let beta=BandMerge::beta_for(&merge.gain,frame_beta,0);
    let floor=ws.var.level(0).iter().map(|v|merge.cfg.gate*beta*v.max(0.0)).collect::<Vec<_>>();
    require(energy.iter().chain(&floor).all(|v|v.is_finite() && *v>=0.0),"invalid actual finest energy/floor")?;
    Ok(Fields{energy,floor})
}

pub struct Replay {
    sizes:Vec<LevelSize>,alpha:Vec<f32>,sums:Vec<Vec<f32>>,coverage:Vec<f32>,sources:usize,
}
impl Replay {
    pub fn new(sizes:&[LevelSize],alpha:&[f32])->Checked<Self> {
        require(sizes.len()>=2 && alpha.len()==sizes[0].pixels()
            && alpha.iter().all(|v|v.is_finite() && (0.0..=1.0).contains(v)),"invalid replay geometry/activation")?;
        Ok(Self{sizes:sizes.to_vec(),alpha:alpha.to_vec(),sums:vec![vec![0.0;alpha.len()];4],
            coverage:vec![0.0;alpha.len()],sources:0})
    }
    pub fn alpha(&self)->&[f32]{&self.alpha}
    pub fn coverage(&self)->&[f32]{&self.coverage}
    pub fn detail_sums(&self)->&[Vec<f32>]{&self.sums}
    pub fn add_source(&mut self,q:&[f32],planes:&[Vec<f32>])->Checked<()> {
        require(self.sources<299 && q.len()==self.alpha.len()
            && q.iter().all(|v|v.is_finite() && (0.0..=1.0).contains(v)),"invalid streamed source membership")?;
        require(planes.len()==4 && planes.iter().all(|p|p.len()==q.len() && p.iter().all(|v|v.is_finite())),
            "invalid gathered four-plane source")?;
        for (total,&v) in self.coverage.iter_mut().zip(q){*total+=v;}
        self.sources+=1;
        if q.iter().all(|&v|v==0.0){return Ok(());}
        let mut ws=Workspace::new(&self.sizes);let mut donor=Pyramid::zeros(&self.sizes);let last=self.sizes.len()-1;
        for (c,source) in planes.iter().enumerate(){
            donor.build(source,&mut ws);donor.level_mut(last).fill(0.0);let ac=donor.collapse(&mut ws);
            for ((sum,&weight),&v) in self.sums[c].iter_mut().zip(q).zip(&ac){if weight>0.0{*sum+=weight*v;}}
        }
        require(self.sums.iter().flatten().all(|v|v.is_finite()),"nonfinite AC accumulation")
    }
    pub fn finish(&self,merge:&BandMerge,ws:&mut Workspace)->Checked<Vec<Vec<f32>>> {
        supported(merge)?;require(merge.sizes==self.sizes,"baseline/replay geometry mismatch")?;
        require(self.coverage.iter().zip(&self.alpha).all(|(&q,&a)|q.is_finite() && (q-a).abs()<=8e-6),
            "streamed memberships do not sum to prescribed activation")?;
        let mut output=merge.finish(ws);
        if self.alpha.iter().all(|&a|a==0.0){return Ok(output);}
        require(self.sources>0,"active replay has no sources")?;
        let last=self.sizes.len()-1;
        for (c,mut p) in super::donor_consistency_diagnostic::resolved_coefficients(merge).into_iter().enumerate(){
            let pre=p.collapse(ws);p.level_mut(last).fill(0.0);let ac=p.collapse(ws);
            for j in 0..self.alpha.len(){
                if self.alpha[j]!=0.0 {
                    let v=pre[j]+(self.sums[c][j]-self.alpha[j]*ac[j]);
                    require(v.is_finite(),"nonfinite reconstructed candidate")?;
                    output[c][j]=v.clamp(merge.lo[c][j],merge.hi[c][j]);
                }
            }
        }Ok(output)
    }
}
