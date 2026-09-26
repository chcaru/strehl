// Fixed pixel-major scalar evidence/cost fields. Never stores aligned images.
pub(crate) const TAU:f32=0.125;
pub(crate) struct CostVolume {width:usize,height:usize,frames:usize,values:Vec<f32>,seen:Vec<bool>}
pub(crate) struct RawCosts {
    pub width:usize,pub height:usize,pub frames:usize,pub costs:Vec<f32>,pub rmax:Vec<f32>,pub spread:Vec<f32>,
}
pub(crate) struct Memberships {
    pub width:usize,pub height:usize,pub frames:usize,pub pixel_major_q:Vec<f32>,pub alpha:Vec<f32>,
}
fn volume_len(width:usize,height:usize,frames:usize)->Result<usize> {
    ensure!(width>0 && height>0 && (1..=299).contains(&frames),"positive bounded source-field extent required");
    let n=width.checked_mul(height).context("source-field image extent overflow")?;
    ensure!(n<=3460*2306,"source-field image exceeds fixed full-domain limit");
    n.checked_mul(frames).context("source-field volume overflow")
}
impl CostVolume {
    pub(crate) fn new(width:usize,height:usize,frames:usize)->Result<Self> {
        let n=volume_len(width,height,frames)?;
        Ok(Self{width,height,frames,values:vec![0.0;n],seen:vec![false;frames]})
    }
    pub(crate) fn set_source(&mut self,index:usize,energy:&[f32],floor:&[f32])->Result<()> {
        ensure!(index<self.frames && !self.seen[index],"duplicate or invalid source evidence");
        ensure!(energy.len()==self.width*self.height && floor.len()==energy.len(),"source evidence shape mismatch");
        for (p,(&e,&f)) in energy.iter().zip(floor).enumerate(){
            ensure!(e.is_finite() && e>=0.0 && f.is_finite() && f>=0.0,"invalid finest energy/floor");
            let r=(e-f).max(0.0)/f.max(1.0);ensure!(r.is_finite() && r>=0.0,"invalid source ratio");
            self.values[p*self.frames+index]=r;
        }self.seen[index]=true;Ok(())
    }
    pub(crate) fn normalize(mut self)->Result<RawCosts> {
        ensure!(self.seen.iter().all(|&v|v),"incomplete source evidence");
        let mut rmax=Vec::with_capacity(self.width*self.height);let mut spread=Vec::with_capacity(rmax.capacity());
        for pixel in self.values.chunks_exact_mut(self.frames){
            let maximum=pixel.iter().copied().fold(0.0,f32::max);rmax.push(maximum);
            for r in pixel.iter_mut(){*r=if maximum>0.0{(1.0-*r/maximum).clamp(0.0,1.0)}else{1.0};}
            let lo=pixel.iter().copied().fold(f32::INFINITY,f32::min);let hi=pixel.iter().copied().fold(f32::NEG_INFINITY,f32::max);
            spread.push(hi-lo);
        }
        Ok(RawCosts{width:self.width,height:self.height,frames:self.frames,costs:self.values,rmax,spread})
    }
}
pub(crate) fn transition(a:f32,b:f32)->f32 {
    let g=(a-b).abs()/(a.abs()+b.abs()+1.0);let x=g/0.05;0.25/(1.0+x*x)
}
pub(crate) fn aggregate_costs(raw:&RawCosts,guide:&[f32])->Result<Vec<f32>> {
    let n=volume_len(raw.width,raw.height,raw.frames)?;
    ensure!(raw.costs.len()==n && guide.len()==raw.width*raw.height
        && raw.costs.iter().all(|v|v.is_finite() && (0.0..=1.0).contains(v))
        && guide.iter().all(|v|v.is_finite()),"invalid raw costs/common guide");
    let mut aggregate=vec![0.0f32;n];let labels=raw.frames;
    // Exactly LR, RL, TD, BU; no direction-volume collection or image wrapping.
    for direction in 0..4 {
        let horizontal=direction<2;let reverse=direction%2==1;
        let lines=if horizontal{raw.height}else{raw.width};let length=if horizontal{raw.width}else{raw.height};
        for line in 0..lines {
            let mut previous=vec![0.0f32;labels];let mut predecessor=0usize;
            for step in 0..length {
                let pos=if reverse{length-1-step}else{step};
                let pixel=if horizontal{line*raw.width+pos}else{pos*raw.width+line};
                let unary=&raw.costs[pixel*labels..(pixel+1)*labels];
                if step==0{previous.copy_from_slice(unary);}else{
                    let minimum=previous.iter().copied().fold(f32::INFINITY,f32::min);
                    let penalty=transition(guide[pixel],guide[predecessor]);
                    for k in 0..labels {previous[k]=unary[k]+previous[k].min(minimum+penalty)-minimum;}
                }
                for k in 0..labels {aggregate[pixel*labels+k]+=previous[k];}predecessor=pixel;
            }
        }
    }
    for (a,&d) in aggregate.iter_mut().zip(&raw.costs){*a-=3.0*d;}
    ensure!(aggregate.iter().all(|v|v.is_finite()),"nonfinite aggregate source cost");Ok(aggregate)
}
pub(crate) fn activation_h(t:f32)->f32 {let u=t.clamp(0.0,1.0);u*u*(3.0-2.0*u)}
pub(crate) fn memberships(mut aggregate:Vec<f32>,raw:&RawCosts)->Result<Memberships> {
    let n=volume_len(raw.width,raw.height,raw.frames)?;let pixels=raw.width*raw.height;
    ensure!(aggregate.len()==n && raw.rmax.len()==pixels && raw.spread.len()==pixels
        && aggregate.iter().all(|v|v.is_finite())
        && raw.rmax.iter().all(|v|v.is_finite() && *v>=0.0)
        && raw.spread.iter().all(|v|v.is_finite() && (0.0..=1.0).contains(v)),"invalid membership inputs");
    let mut alpha=vec![0.0;pixels];
    for (p,pixel) in aggregate.chunks_exact_mut(raw.frames).enumerate(){
        let amin=pixel.iter().copied().fold(f32::INFINITY,f32::min);let mut denominator=0.0;
        for v in pixel.iter_mut(){*v=(1.0-(*v-amin)/TAU).max(0.0);denominator+=*v;}
        ensure!(denominator.is_finite() && denominator>0.0,"empty soft source support");
        alpha[p]=activation_h((raw.rmax[p]-1.0)/3.0)*activation_h((raw.spread[p]-TAU)/TAU);
        for v in pixel.iter_mut(){let w=*v/denominator;*v=alpha[p]*w;}
    }
    Ok(Memberships{width:raw.width,height:raw.height,frames:raw.frames,pixel_major_q:aggregate,alpha})
}
impl Memberships {
    pub(crate) fn source(&self,index:usize)->Vec<f32>{
        assert!(index<self.frames);self.pixel_major_q.chunks_exact(self.frames).map(|p|p[index]).collect()
    }
    pub(crate) fn evidence(&self)->serde_json::Value {
        let mut mass=vec![0.0f64;self.frames];let mut active=vec![0usize;self.frames];let mut multiple=0;
        for pixel in self.pixel_major_q.chunks_exact(self.frames){let mut count=0;
            for(k,&v)in pixel.iter().enumerate(){mass[k]+=v as f64;if v>0.0{active[k]+=1;count+=1;}}
            multiple+=usize::from(count>1);
        }
        serde_json::json!({"alpha_zero":self.alpha.iter().filter(|&&a|a==0.0).count(),
            "alpha_positive":self.alpha.iter().filter(|&&a|a>0.0).count(),
            "alpha_one":self.alpha.iter().filter(|&&a|a==1.0).count(),"multiple_source_pixels":multiple,
            "source_membership_mass":mass,"source_positive_pixels":active})
    }
}
