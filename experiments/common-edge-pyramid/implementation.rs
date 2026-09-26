// Test-only common spatial basis; old Gaussian admission remains unchanged.
use super::*;
use strehl_core::align::Similarity;
use strehl_core::pyramid::{LevelSize, Hull, Fallback,
    rb_own_guide_diagnostic as canonical, real_source_contributions as retained};
use super::shared_source_field::{hash16, hash32};

pub(crate) type Bands = Vec<Vec<f32>>;
const BINOMIAL: [f32; 5] = [1.0/16.0,4.0/16.0,6.0/16.0,4.0/16.0,1.0/16.0];
pub(crate) const NUMERATOR_SCALE: f32 = 65536.0;

pub(crate) fn noise_proxy(noise: &NoiseModel, value: f32) -> f32 {
    let a=noise.plane(CfaPlane::G1).variance(value).sqrt();
    let b=noise.plane(CfaPlane::G2).variance(value).sqrt();
    0.25*(a+b)*(a+b)
}
pub(crate) fn conductance(a:f32,b:f32,va:f32,vb:f32)->f32 {
    let delta=a-b; 1.0/(1.0+delta*delta/(va+vb))
}
fn clamped(i:isize,n:usize)->usize {i.clamp(0,n as isize-1) as usize}
fn expansion_axis(x:usize,n:usize)->[(usize,f32);3] {
    let c=x/2;
    if x%2==0 {[(clamped(c as isize-1,n),0.125),(c,0.75),(clamped(c as isize+1,n),0.125)]}
    else {[(c,0.5),(clamped(c as isize+1,n),0.5),(c,0.0)]}
}
fn finite(values:&[f32])->bool {values.iter().all(|v|v.is_finite())}
fn same(a:&[f32],b:&[f32])->bool {a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())}
fn same4(a:&[Vec<f32>],b:&[Vec<f32>])->bool {a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|same(a,b))}
fn hashes(a:&[Vec<f32>])->Vec<String>{a.iter().map(|v|hash32(v)).collect()}

pub(crate) struct EdgePyramid {
    pub sizes:Vec<LevelSize>, pub guides:Bands,
    pub restriction:Vec<Vec<[f32;25]>>, pub expansion:Vec<Vec<[f32;9]>>,
}
impl EdgePyramid {
    pub(crate) fn new(sizes:&[LevelSize],guide:&[f32],noise:&NoiseModel)->Result<Self> {
        ensure!(sizes.len()>=2&&sizes.len()<=8&&sizes[0].width>0&&sizes[0].height>0
            &&guide.len()==sizes[0].pixels()&&finite(guide),"guide shape/finite");
        ensure!(sizes.windows(2).all(|s|s[0].reduced()==s[1]),"level geometry");
        ensure!(noise.is_trustworthy()&&noise.prnu().is_none(),"injected temporal model required");
        let mut out=Self{sizes:sizes.to_vec(),guides:vec![guide.to_vec()],restriction:vec![],expansion:vec![]};
        for k in 0..sizes.len()-1 {
            let s=sizes[k];let d=sizes[k+1];let g=&out.guides[k];
            let variance=g.iter().map(|&v|noise_proxy(noise,v)).collect::<Vec<_>>();
            ensure!(variance.iter().all(|v|v.is_finite()&&*v>0.0),"invalid injected guide proxy");
            let rows=(0..d.pixels()).into_par_iter().map(|j|->Result<[f32;25]>{
                let x=2*(j%d.width);let y=2*(j/d.width);let centre=y*s.width+x;
                let mut row=[0.0;25];let mut mass=0.0;
                for ty in 0..5 {for tx in 0..5 {
                    let p=clamped(y as isize+ty as isize-2,s.height)*s.width
                        +clamped(x as isize+tx as isize-2,s.width);
                    let w=BINOMIAL[ty]*BINOMIAL[tx]*conductance(g[centre],g[p],variance[centre],variance[p]);
                    ensure!(w.is_finite()&&w>=0.0,"restriction conductance");row[ty*5+tx]=w;mass+=w;
                }}
                ensure!(mass.is_finite()&&mass>0.0,"restriction mass");for w in &mut row{*w/=mass;}Ok(row)
            }).collect::<Result<Vec<_>>>()?;
            out.restriction.push(rows);
            let coarse=out.reduce(k,&out.guides[k])?;
            let cv=coarse.iter().map(|&v|noise_proxy(noise,v)).collect::<Vec<_>>();
            ensure!(cv.iter().all(|v|v.is_finite()&&*v>0.0),"invalid coarse proxy");
            let g=&out.guides[k];
            let rows=(0..s.pixels()).into_par_iter().map(|j|->Result<[f32;9]>{
                let xx=expansion_axis(j%s.width,d.width);let yy=expansion_axis(j/s.width,d.height);
                let mut row=[0.0;9];let mut mass=0.0;
                for(ty,&(y,wy))in yy.iter().enumerate(){for(tx,&(x,wx))in xx.iter().enumerate(){
                    let p=y*d.width+x;
                    let w=wx*wy*conductance(g[j],coarse[p],variance[j],cv[p]);
                    ensure!(w.is_finite()&&w>=0.0,"expansion conductance");row[ty*3+tx]=w;mass+=w;
                }}
                ensure!(mass.is_finite()&&mass>0.0,"expansion mass");for w in &mut row{*w/=mass;}Ok(row)
            }).collect::<Result<Vec<_>>>()?;
            out.expansion.push(rows);out.guides.push(coarse);
        }Ok(out)
    }
    pub(crate) fn stencil_bytes(&self)->usize {
        self.restriction.iter().map(|r|r.len()*25*4).sum::<usize>()
            +self.expansion.iter().map(|r|r.len()*9*4).sum::<usize>()
    }
    pub(crate) fn reduce(&self,k:usize,src:&[f32])->Result<Vec<f32>> {
        ensure!(k<self.restriction.len(),"restriction level");let s=self.sizes[k];let d=self.sizes[k+1];
        ensure!(src.len()==s.pixels()&&finite(src),"restriction input");
        let out=self.restriction[k].par_iter().enumerate().map(|(j,row)|{
            let x=2*(j%d.width);let y=2*(j/d.width);let mut value=0.0;
            for ty in 0..5 {for tx in 0..5 {
                let p=clamped(y as isize+ty as isize-2,s.height)*s.width+clamped(x as isize+tx as isize-2,s.width);
                value+=row[ty*5+tx]*src[p];
            }}value
        }).collect::<Vec<_>>();ensure!(finite(&out),"restriction overflow");Ok(out)
    }
    pub(crate) fn expand(&self,k:usize,src:&[f32])->Result<Vec<f32>> {
        ensure!(k<self.expansion.len(),"expansion level");let s=self.sizes[k];let d=self.sizes[k+1];
        ensure!(src.len()==d.pixels()&&finite(src),"expansion input");
        let out=self.expansion[k].par_iter().enumerate().map(|(j,row)|{
            let xx=expansion_axis(j%s.width,d.width);let yy=expansion_axis(j/s.width,d.height);let mut value=0.0;
            for(ty,&(y,_))in yy.iter().enumerate(){for(tx,&(x,_))in xx.iter().enumerate(){value+=row[ty*3+tx]*src[y*d.width+x];}}
            value
        }).collect::<Vec<_>>();ensure!(finite(&out),"expansion overflow");Ok(out)
    }
    pub(crate) fn analyze(&self,src:&[f32])->Result<Bands> {
        ensure!(src.len()==self.sizes[0].pixels()&&finite(src),"analysis input");
        let mut bands=vec![src.to_vec()];for k in 0..self.sizes.len()-1{bands.push(self.reduce(k,&bands[k])?);}
        for k in 0..self.sizes.len()-1{let expanded=self.expand(k,&bands[k+1])?;
            bands[k].par_iter_mut().zip(expanded).for_each(|(v,e)|*v-=e);}
        ensure!(bands.iter().all(|v|finite(v)),"analysis overflow");Ok(bands)
    }
    pub(crate) fn synthesize(&self,bands:&[Vec<f32>])->Result<Vec<f32>> {
        ensure!(bands.len()==self.sizes.len()&&bands.iter().zip(&self.sizes).all(|(v,s)|v.len()==s.pixels()&&finite(v)),"synthesis input");
        let mut out=bands.last().unwrap().clone();for k in (0..self.sizes.len()-1).rev(){
            out=self.expand(k,&out)?;out.par_iter_mut().zip(&bands[k]).for_each(|(v,l)|*v+=l);
        }ensure!(finite(&out),"synthesis overflow");Ok(out)
    }
}

pub(crate) struct EdgeMerge {
    sizes:Vec<LevelSize>, expected:usize, count:usize,
    numerator:Vec<Bands>, unweighted:Vec<Bands>, denominator:Bands,
}
pub(crate) struct Merged {pub planes4:Vec<Vec<f32>>,pub terminal4:Vec<Vec<f32>>}
impl EdgeMerge {
    pub(crate) fn new(sizes:&[LevelSize],count:usize)->Self {
        assert!(count>0&&!sizes.is_empty());let zero=||sizes.iter().map(|s|vec![0.0;s.pixels()]).collect::<Bands>();
        Self{sizes:sizes.to_vec(),expected:count,count:0,numerator:(0..4).map(|_|zero()).collect(),
            unweighted:(0..4).map(|_|zero()).collect(),denominator:zero()}
    }
    pub(crate) fn add(&mut self,index:usize,planes:&[Vec<f32>],weights:&[Vec<f32>],transform:&EdgePyramid)->Result<()> {
        ensure!(index==self.count&&index<self.expected&&self.sizes==transform.sizes,"source order/transform shape");
        let nb=self.sizes.len()-1;ensure!(planes.len()==4&&weights.len()==nb,"merge channels/bands");
        for(k,w)in weights.iter().enumerate(){ensure!(w.len()==self.sizes[k].pixels()&&w.iter().all(|v|v.is_finite()&&*v>=0.0),"merge weight");
            self.denominator[k].par_iter_mut().zip(w).for_each(|(d,w)|*d+=w);}
        for(c,plane)in planes.iter().enumerate(){let bands=transform.analyze(plane)?;
            for(k,band)in bands.iter().enumerate(){
                self.unweighted[c][k].par_iter_mut().zip(band).for_each(|(u,v)|*u+=v);
                if k<nb {self.numerator[c][k].par_iter_mut().zip(band).zip(&weights[k])
                    .for_each(|((n,v),w)|*n+=w*(*v/NUMERATOR_SCALE));}
            }}
        ensure!(self.denominator.iter().all(|v|finite(v))&&self.numerator.iter().chain(&self.unweighted).all(|p|p.iter().all(|v|finite(v))),"merge accumulator overflow");
        self.count+=1;Ok(())
    }
    pub(crate) fn finish(&self,transform:&EdgePyramid)->Result<Merged> {
        ensure!(self.count==self.expected&&self.sizes==transform.sizes,"incomplete merge/transform");
        let inv=1.0/self.count as f32;let nb=self.sizes.len()-1;let mut planes4=Vec::new();let mut terminal4=Vec::new();
        for c in 0..4 {let mut bands=self.unweighted[c].clone();
            for(k,band)in bands.iter_mut().enumerate(){for(j,v)in band.iter_mut().enumerate(){
                *v=if k<nb&&self.denominator[k][j]>0.0 {(self.numerator[c][k][j]/self.denominator[k][j])*NUMERATOR_SCALE}else{*v*inv};
            }}
            terminal4.push(bands[nb].clone());planes4.push(transform.synthesize(&bands)?);
        }Ok(Merged{planes4,terminal4})
    }
}

pub(crate) struct Arm {
    pub name:String,pub planes4:Vec<Vec<f32>>,pub pre_hull4:Vec<Vec<f32>>,pub rgb:Vec<f32>,
    pub terminal4:Vec<Vec<f32>>,pub guide:Vec<f32>,pub guide_level_sha256:Vec<String>,pub stencil_bytes:usize,
}
#[derive(serde::Serialize)]
pub(crate) struct FrameEvidence {
    pub source_sha256:String,pub active_sha256:String,pub known4_sha256:[String;4],
    pub guide_sha256:String,pub variance_sha256:String,pub beta:Vec<f32>,
    pub weight_sha256:Vec<String>,pub energy_sha256:Vec<String>,pub floor_sha256:Vec<String>,pub replay_exact:bool,
}
pub(crate) struct Comparison {
    pub canonical:Arm,pub uniform:Arm,pub arms:Vec<Arm>,pub frames:Vec<FrameEvidence>,
    pub level_sizes:Vec<[usize;2]>,pub native_width:usize,pub native_height:usize,pub canonical_replay_exact:bool,
}
fn hull(planes:&mut[Vec<f32>],reference:&BandMerge)->Result<()> {
    ensure!(planes.len()==4&&planes.iter().all(|v|v.len()==planes[0].len()&&finite(v)),"hull input");
    for j in 0..planes[0].len(){for(c,[lo,hi])in retained::hull(reference,j).into_iter().enumerate(){
        ensure!(lo.is_finite()&&hi.is_finite()&&lo<=hi,"held hull invalid");planes[c][j]=planes[c][j].clamp(lo,hi);
    }}Ok(())
}
fn native_arm(name:&str,merge:&BandMerge,sizes:&[LevelSize],levels:Levels,wb:[f32;4])->Result<Arm> {
    let planes4=merge.finish(&mut Workspace::new(sizes));
    let coeff=strehl_core::pyramid::donor_consistency_diagnostic::resolved_coefficients(merge);
    let pre_hull4=coeff.iter().map(|p|p.collapse(&mut Workspace::new(sizes))).collect::<Vec<_>>();
    let mut check=pre_hull4.clone();hull(&mut check,merge)?;
    ensure!(same4(&check,&planes4),"actual Gaussian pre-hull/finish mismatch");
    let rgb=phase_packed_rgb::camera_rgb(&planes4,sizes[0].width,sizes[0].height,levels,wb)?;
    ensure!(finite(&rgb),"nonfinite actual MHC");
    Ok(Arm{name:name.into(),planes4,pre_hull4,rgb,terminal4:canonical::terminal_means(merge),
        guide:vec![],guide_level_sha256:vec![],stencil_bytes:0})
}
fn frame_evidence(frame:&Frame,worker:&BandWorker,fields:&canonical::Fields)->FrameEvidence {
    FrameEvidence{source_sha256:hash16(&frame.data),active_sha256:super::rb_own_guide::active_hash(frame),
        known4_sha256:std::array::from_fn(|c|hash32(&worker.planes[c])),guide_sha256:hash32(&worker.luma),
        variance_sha256:hash32(&worker.var),beta:worker.beta.clone(),weight_sha256:hashes(&fields.weights),
        energy_sha256:hashes(&fields.energy),floor_sha256:hashes(&fields.floor),replay_exact:false}
}

/// Source u16 fixtures are retained by the caller; no gathered frame survives a
/// loop iteration. Old Gaussian weights, gather, probes, bounds and MHC are held.
pub(crate) fn compare_generated(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,true_guide:Option<&[f32]>,diagnostics:bool)->Result<Comparison> {
    ensure!((1..=17).contains(&frames.len())&&frames.len()==transforms.len(),"bounded generated source count");
    ensure!([3,7].contains(&cfg.bands)&&cfg.select==SelectMode::SoftPower&&cfg.admission==AdmissionMode::HardFloor
        &&cfg.base==BaseBand::Mean&&cfg.fallback==Fallback::Mean&&cfg.hull==Hull::InputRange
        &&cfg.mean_coarse==0&&cfg.significance_scale==0.0,"held Gaussian decision/reconstruction recipe");
    ensure!(align_cmd::fullres_gather_enabled()&&gatefloor::enabled()
        &&align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded
        &&align_cmd::native_gpu_integration::gpu_gather_enabled()?,"actual rounded GPU/probe path required");
    ensure!(strehl_core::pyramid::fine_support_candidate::environment_mode()==strehl_core::pyramid::fine_support_candidate::Mode::Off
        &&align_cmd::native_gpu_integration::ca_stage::mode()?==align_cmd::native_gpu_integration::ca_stage::Mode::Current,
        "competing experiment enabled");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()
        &&!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional")),"held geometry/MHC required");
    let first=&frames[0];let full=first.geometry();let wb=first.wb_coeffs;let count=frames.len();
    ensure!(first.active.width<=2110&&first.active.height<=2110&&noise.is_trustworthy()&&noise.prnu().is_none()
        &&wb[..3].iter().all(|v|v.is_finite()&&*v>0.0),"generated extent/injected noise/WB");
    for c in [CfaPlane::R,CfaPlane::G1,CfaPlane::G2,CfaPlane::B]{ensure!(noise.plane(c).levels==first.levels,"injected source levels");}
    for(i,frame)in frames.iter().enumerate(){
        ensure!(!frame.path.exists()&&frame.geometry()==full&&frame.active==first.active&&frame.stride==first.stride
            &&frame.buffer_height==first.buffer_height&&frame.levels==first.levels&&frame.camera==first.camera
            &&frame.iso==first.iso&&frame.wb_coeffs[..3]==wb[..3],"generated metadata/original path");
        validate_pyramid_frame(frame,full,i)?;let id=strehl_raw::identity(&frame.path);
        ensure!(strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?.is_none(),"generated no-CA scope");
        ensure!(phase_packed_rgb::full_stack::full_source_supported(transforms[i],full,crop,None),"full source stencil support");
    }
    let sizes=level_sizes(crop.width,crop.height,cfg.bands);
    ensure!(sizes.len()==cfg.bands+1,"requested decomposition not exercised");
    if let Some(g)=true_guide {ensure!(g.len()==sizes[0].pixels()&&finite(g),"supplied true-guide shape/finite");}
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes()as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance{
        stack:StackIdentity::from_entries("common-edge-generated",&entries),strategy:"supplied generated direct geometry".into(),
        heldout_px:None,cycle_floor_px:None,reference:0,note:"common guide transform; old Gaussian admission held".into(),
    },full,Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a[Frame]);impl PyramidFrameSource for Source<'_>{
        fn len(&self)->usize{self.0.len()}fn decode(&self,i:usize)->Result<Frame>{Ok(self.0[i].clone())}
    }
    let source=Source(frames);let domain=PyramidDomain::cropped(full,crop)?;
    let mut base=BandWorker::new(domain,cfg);let mut evidence=Vec::new();let mut temporal=vec![0.0;sizes[0].pixels()];
    for(i,frame)in frames.iter().enumerate(){let before=hash16(&frame.data);
        ensure!(base.fold(&source,i,first.levels,noise,Some(&map),None)?,"canonical source refused");
        let fields=canonical::canonical_fields(&base.merge,&base.fws,(!base.beta.is_empty()).then_some(base.beta.as_slice()));
        temporal.par_iter_mut().zip(&base.luma).for_each(|(v,l)|*v+=l);
        let ev=frame_evidence(frame,&base,&fields);ensure!(before==ev.source_sha256,"canonical source modified");evidence.push(ev);
    }
    let canonical_arm=native_arm("canonical",&base.merge,&sizes,first.levels,wb)?;
    let guide=canonical_arm.planes4[1].iter().zip(&canonical_arm.planes4[2]).map(|(a,b)|0.5*(a+b)).collect::<Vec<_>>();
    let inv=1.0/count as f32;temporal.par_iter_mut().for_each(|v|*v*=inv);
    // Scalar scene mean specifies the constant-guide nuisance only; never a noise estimate.
    let scalar=(guide.iter().map(|v|*v as f64).sum::<f64>()/guide.len()as f64)as f32;
    let displaced=(0..guide.len()).map(|j|guide[clamped((j/crop.width)as isize-5,crop.height)*crop.width
        +clamped((j%crop.width)as isize+7,crop.width)]).collect::<Vec<_>>();
    let mut guides=vec![("common-canonical",guide),("constant",vec![scalar;sizes[0].pixels()]),
        ("displaced",displaced),("temporal-mean",temporal)];
    if let Some(g)=true_guide{guides.push(("true",g.to_vec()));}
    let transforms=guides.iter().map(|(_,g)|EdgePyramid::new(&sizes,g,noise)).collect::<Result<Vec<_>>>()?;
    let mut merges=guides.iter().map(|_|EdgeMerge::new(&sizes,count)).collect::<Vec<_>>();
    let mut replay=BandWorker::new(domain,cfg);let mut uniform=BandMerge::new(crop.width,crop.height,4,cfg);
    let mut uniform_ws=FrameWorkspace::new(&sizes,4);
    let unit=canonical::Fields{energy:vec![],floor:vec![],weights:sizes[..sizes.len()-1].iter().map(|s|vec![1.0;s.pixels()]).collect()};
    for(i,frame)in frames.iter().enumerate(){
        ensure!(replay.fold(&source,i,first.levels,noise,Some(&map),None)?,"replay source refused");
        let fields=canonical::canonical_fields(&replay.merge,&replay.fws,(!replay.beta.is_empty()).then_some(replay.beta.as_slice()));
        let ev=frame_evidence(frame,&replay,&fields);let old=&mut evidence[i];
        ensure!(ev.source_sha256==old.source_sha256&&ev.active_sha256==old.active_sha256&&ev.known4_sha256==old.known4_sha256
            &&ev.guide_sha256==old.guide_sha256&&ev.variance_sha256==old.variance_sha256&&same(&ev.beta,&old.beta)
            &&ev.weight_sha256==old.weight_sha256&&ev.energy_sha256==old.energy_sha256&&ev.floor_sha256==old.floor_sha256,"source/gather/old decision changed");
        old.replay_exact=true;
        let refs=replay.planes.iter().map(Vec::as_slice).collect::<Vec<_>>();canonical::add_fields(&mut uniform,&refs,&unit,&mut uniform_ws);
        for(m,t)in merges.iter_mut().zip(&transforms){m.add(i,&replay.planes,&fields.weights,t)?;}
        ensure!(hash16(&frame.data)==old.source_sha256,"candidate source modified");
    }
    let replay_arm=native_arm("replay",&replay.merge,&sizes,first.levels,wb)?;
    let canonical_replay_exact=same4(&canonical_arm.planes4,&replay_arm.planes4)&&same(&canonical_arm.rgb,&replay_arm.rgb);
    ensure!(canonical_replay_exact,"canonical complete CFA/MHC replay differs");
    let uniform_arm=native_arm("uniform",&uniform,&sizes,first.levels,wb)?;let mut arms=Vec::new();
    for(((name,g),t),m)in guides.into_iter().zip(transforms).zip(merges){let merged=m.finish(&t)?;
        let pre_hull4=merged.planes4;let mut planes4=pre_hull4.clone();hull(&mut planes4,&base.merge)?;
        let rgb=phase_packed_rgb::camera_rgb(&planes4,crop.width,crop.height,first.levels,wb)?;ensure!(finite(&rgb),"candidate MHC finite");
        let guide_level_sha256=if diagnostics{hashes(&t.guides)}else{vec![]};
        arms.push(Arm{name:name.into(),planes4,pre_hull4,rgb,terminal4:merged.terminal4,guide:g,
            guide_level_sha256,stencil_bytes:t.stencil_bytes()});
    }
    if !diagnostics{evidence.clear();}
    Ok(Comparison{canonical:canonical_arm,uniform:uniform_arm,arms,frames:evidence,
        level_sizes:sizes.iter().map(|s|[s.width,s.height]).collect(),native_width:2*crop.width,native_height:2*crop.height,canonical_replay_exact})
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/common-edge-pyramid/independent-controls.rs"));
}
