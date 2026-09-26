// Generated-only guide comparison; all reconstruction remains original linear CFA.
use super::*;
use strehl_core::align::Similarity;
use strehl_core::pyramid::{LevelSize, correction_variance_diagnostic as kernels,
    rb_own_guide_diagnostic as core};
use super::boundary_cfa_wavelet as source_probe;
use super::shared_source_field::{hash16, hash32};

pub(crate) const PROBE_PAIRS: usize = 8;
pub(crate) const REFERENCE_SIGNAL: f32 = 2000.0;
pub(crate) type Bands = Vec<Vec<f32>>;

#[derive(Clone, Copy, Debug, serde::Serialize)]
pub(crate) struct Transform {
    pub a: f32, pub b: f32, pub pedestal: f32,
    pub reference_signal: f32, pub root_reference: f32,
}
impl Transform {
    pub(crate) fn from_noise(noise: &NoiseModel) -> Result<Self> {
        let g1 = noise.plane(CfaPlane::G1); let g2 = noise.plane(CfaPlane::G2);
        let a = 0.25 * (g1.gain_dn_per_e + g2.gain_dn_per_e);
        let r1 = g1.read_floor_dn(); let r2 = g2.read_floor_dn();
        let b = 0.25 * (r1*r1 + r2*r2);
        let pedestal = b + 0.375 * a*a;
        let root_reference = (a*REFERENCE_SIGNAL + pedestal).sqrt();
        ensure!(a.is_finite() && a>0.0 && b.is_finite() && b>=0.0
            && pedestal.is_finite() && pedestal>0.0 && root_reference.is_finite(),
            "invalid injected mean-green transform constants");
        Ok(Self {a,b,pedestal,reference_signal:REFERENCE_SIGNAL,root_reference})
    }
    pub(crate) fn apply(&self, values: &[f32]) -> Result<Vec<f32>> {
        ensure!(values.iter().all(|v|v.is_finite()), "nonfinite input guide");
        let root_pedestal = self.pedestal.sqrt();
        let out = values.iter().map(|&v| {
            let s = v.max(0.0);
            2.0*self.root_reference*s / ((self.a*s+self.pedestal).sqrt()+root_pedestal)
        }).collect::<Vec<_>>();
        ensure!(out.iter().all(|v|v.is_finite() && *v>=0.0), "nonfinite H guide");
        Ok(out)
    }
}

pub(crate) fn guide_bands(known4: &[Vec<f32>], sizes: &[LevelSize], transform: &Transform)
    -> Result<[Bands;2]> {
    ensure!(!sizes.is_empty() && known4.len()==4 && known4.iter().all(|p|
        p.len()==sizes[0].pixels() && p.iter().all(|v|v.is_finite())), "guide shape/values");
    let green = known4[1].iter().zip(&known4[2]).map(|(a,b)|0.5*(a+b)).collect::<Vec<_>>();
    let stabilized = transform.apply(&green)?;
    Ok([kernels::laplacian(&green,sizes), kernels::laplacian(&stabilized,sizes)])
}

pub(crate) struct PairedEnergy { sizes:Vec<LevelSize>, sums:[Bands;2], pairs:usize }
impl PairedEnergy {
    pub(crate) fn new(sizes:&[LevelSize])->Self {
        assert!(sizes.len()>=2);
        Self {sizes:sizes.to_vec(),sums:std::array::from_fn(|_|sizes[..sizes.len()-1]
            .iter().map(|s|vec![0.0;s.pixels()]).collect()),pairs:0}
    }
    pub(crate) fn add_pair(&mut self,a:&[Bands;2],b:&[Bands;2])->Result<()> {
        ensure!(self.pairs<PROBE_PAIRS,"extra probe pair");
        for arm in 0..2 {
            ensure!(a[arm].len()==self.sums[arm].len() && b[arm].len()==self.sums[arm].len(),"probe band count");
            for k in 0..self.sums[arm].len() {
                ensure!(a[arm][k].len()==self.sums[arm][k].len()
                    && b[arm][k].len()==self.sums[arm][k].len(),"probe band shape");
                for ((sum,&av),&bv) in self.sums[arm][k].iter_mut().zip(&a[arm][k]).zip(&b[arm][k]) {
                    ensure!(av.is_finite() && bv.is_finite(),"nonfinite probe coefficient");
                    let d=av-bv; *sum+=d*d;
                }
            }
        }
        self.pairs+=1; Ok(())
    }
    pub(crate) fn finish(mut self)->Result<[Bands;2]> {
        ensure!(self.pairs==PROBE_PAIRS,"exactly eight independent pairs required");
        for arm in 0..2 {for k in 0..self.sums[arm].len() {
            for v in &mut self.sums[arm][k] {*v/=(2*PROBE_PAIRS) as f32;}
            self.sums[arm][k]=kernels::smooth(&self.sums[arm][k],self.sizes[k]);
            ensure!(self.sums[arm][k].iter().all(|v|v.is_finite() && *v>=0.0),"invalid conditional guide variance");
        }}
        Ok(self.sums)
    }
}

#[derive(serde::Serialize)]
pub(crate) struct FieldEvidence {
    pub energy_sha256:Vec<String>, pub floor_sha256:Vec<String>, pub weight_sha256:Vec<String>,
    pub positive_weight_counts:Vec<usize>,
}
#[derive(serde::Serialize)]
pub(crate) struct FrameEvidence {
    pub source_sha256:String, pub active_sha256:String, pub known4_sha256:[String;4],
    pub baseline_guide_sha256:String, pub baseline_variance_sha256:String, pub baseline_beta:Vec<f32>,
    pub probe_seeds:[usize;16], pub canonical_fields:FieldEvidence,
    pub linear_fields:FieldEvidence, pub stabilized_fields:FieldEvidence, pub source_unchanged:bool,
}
pub(crate) struct Arm {
    pub planes4:Vec<Vec<f32>>, pub rgb:Vec<f32>, pub averaged_fraction:Vec<f64>, pub terminal_base_exact:bool,
}
pub(crate) struct Comparison {
    pub canonical:Arm, pub identity:Arm, pub matched_linear:Arm, pub stabilized:Arm,
    pub native_width:usize, pub native_height:usize, pub level_sizes:Vec<[usize;2]>,
    pub transform:Transform, pub frames:Vec<FrameEvidence>,
}
fn same(a:&[f32],b:&[f32])->bool {
    a.len()==b.len() && a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())
}
fn field_evidence(fields:&core::Fields,diagnostics:bool)->FieldEvidence {
    if !diagnostics {return FieldEvidence {energy_sha256:vec![],floor_sha256:vec![],weight_sha256:vec![],positive_weight_counts:vec![]};}
    FieldEvidence {energy_sha256:fields.energy.iter().map(|v|hash32(v)).collect(),
        floor_sha256:fields.floor.iter().map(|v|hash32(v)).collect(),
        weight_sha256:fields.weights.iter().map(|v|hash32(v)).collect(),
        positive_weight_counts:fields.weights.iter().map(|v|v.iter().filter(|&&w|w>0.0).count()).collect()}
}
fn finish(merge:&BandMerge,base:&[Vec<f32>],sizes:&[LevelSize],levels:Levels,wb:[f32;4])->Result<Arm> {
    let planes4=merge.finish(&mut Workspace::new(sizes));
    ensure!(planes4.iter().flatten().all(|v|v.is_finite()),"nonfinite final CFA");
    let terminal=core::terminal_means(merge);
    let terminal_base_exact=terminal.len()==base.len() && terminal.iter().zip(base).all(|(a,b)|same(a,b));
    ensure!(terminal_base_exact,"linear terminal mean changed");
    let rgb=phase_packed_rgb::camera_rgb(&planes4,sizes[0].width,sizes[0].height,levels,wb)?;
    Ok(Arm {planes4,rgb,averaged_fraction:merge.averaged_fraction(),terminal_base_exact})
}
pub(crate) fn compare_generated(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig)->Result<Comparison> {
    compare_generated_with_diagnostics(frames,transforms,crop,noise,cfg,true)
}
pub(crate) fn compare_generated_with_diagnostics(frames:&[Frame],transforms:&[Similarity],crop:align_cmd::CropRect,
    noise:&NoiseModel,cfg:MergeConfig,diagnostics:bool)->Result<Comparison> {
    ensure!(frames.len()>=2 && frames.len()<=16 && frames.len()==transforms.len(),"generated 2..16 source scope");
    let first=&frames[0]; let full=first.geometry(); let wb=first.wb_coeffs;
    ensure!(first.active.width<=512 && first.active.height<=512 && wb[..3].iter().all(|v|v.is_finite() && *v>0.0),
        "bounded generated extent/WB required");
    ensure!(gatefloor::enabled() && strehl_core::pyramid::fine_support_candidate::environment_mode()
        ==strehl_core::pyramid::fine_support_candidate::Mode::Off,"held probe/no competing treatment required");
    ensure!(noise.is_trustworthy() && noise.prnu().is_none(),"injected temporal noise model required");
    for p in [CfaPlane::R,CfaPlane::G1,CfaPlane::G2,CfaPlane::B] {
        ensure!(noise.plane(p).levels==first.levels,"injected source levels differ");
    }
    for (i,f) in frames.iter().enumerate() {
        ensure!(!f.path.exists() && f.geometry()==full && f.active==first.active && f.stride==first.stride
            && f.buffer_height==first.buffer_height && f.levels==first.levels && f.camera==first.camera && f.iso==first.iso
            && f.wb_coeffs[..3]==wb[..3],"generated source metadata differs or original path exists");
        validate_pyramid_frame(f,full,i)?;
        let id=strehl_raw::identity(&f.path);
        ensure!(strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?.is_none(),"generated no-CA scope");
        ensure!(phase_packed_rgb::full_stack::full_source_supported(transforms[i],full,crop,None),"full gather support required");
    }
    let transform=Transform::from_noise(noise)?;
    let sizes=level_sizes(crop.width,crop.height,cfg.bands);
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes() as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance {
        stack:StackIdentity::from_entries("variance-stabilized-guide-generated",&entries),
        strategy:"fixed supplied generated similarities".into(),heldout_px:None,cycle_floor_px:None,reference:0,
        note:"H decision only; original linear CFA reconstruction".into(),
    },full,Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a[Frame]); impl PyramidFrameSource for Source<'_> {
        fn len(&self)->usize{self.0.len()} fn decode(&self,index:usize)->Result<Frame>{Ok(self.0[index].clone())}
    }
    let source=Source(frames);
    let mut baseline=BandWorker::new(PyramidDomain::cropped(full,crop)?,cfg);
    let mut merges:[BandMerge;3]=std::array::from_fn(|_|BandMerge::new(crop.width,crop.height,4,cfg));
    let mut work:[FrameWorkspace;3]=std::array::from_fn(|_|FrameWorkspace::new(&sizes,4));
    let mut evidence=Vec::new();
    for (index,frame) in frames.iter().enumerate() {
        let before=hash16(&frame.data);
        ensure!(baseline.fold(&source,index,first.levels,noise,Some(&map),None)?,"canonical source refused");
        let canonical=core::canonical_fields(&baseline.merge,&baseline.fws,
            (!baseline.beta.is_empty()).then_some(baseline.beta.as_slice()));
        let linear=baseline.planes[1].iter().zip(&baseline.planes[2]).map(|(a,b)|0.5*(a+b)).collect::<Vec<_>>();
        ensure!(same(&linear,&baseline.luma),"actual mean-green guide differs");
        let signal=guide_bands(&baseline.planes,&sizes,&transform)?;
        let active_sha256=super::rb_own_guide::active_hash(frame);
        let seeds=super::rb_own_guide::source_seeds(&active_sha256)?;
        let variance=source_probe::original_variances(frame,noise)?;
        let mut paired=PairedEnergy::new(&sizes);
        for pair in 0..PROBE_PAIRS {
            let member=|draw:usize|->Result<[Bands;2]> {
                let noisy=source_probe::noisy_source(frame,&variance,seeds[draw])?;
                let known4=source_probe::gather_known4(&noisy,transforms[index],crop)?;
                guide_bands(&known4,&sizes,&transform)
            };
            let a=member(2*pair)?; let b=member(2*pair+1)?; paired.add_pair(&a,&b)?;
        }
        let floors=paired.finish()?;
        let fields:[core::Fields;2]=std::array::from_fn(|arm| {
            let energy=signal[arm].iter().enumerate().map(|(k,v)|kernels::energy(v,sizes[k])).collect();
            let floor=floors[arm].iter().map(|v|v.iter().map(|x|cfg.gate*x).collect()).collect();
            core::fields_from_energy(&sizes,cfg,energy,floor)
        });
        let refs=baseline.planes.iter().map(Vec::as_slice).collect::<Vec<_>>();
        for (arm,field) in [&canonical,&fields[0],&fields[1]].into_iter().enumerate() {
            core::add_fields(&mut merges[arm],&refs,field,&mut work[arm]);
        }
        ensure!(hash16(&frame.data)==before,"original source changed");
        if diagnostics {evidence.push(FrameEvidence {
            source_sha256:before,active_sha256,known4_sha256:std::array::from_fn(|c|hash32(&baseline.planes[c])),
            baseline_guide_sha256:hash32(&baseline.luma),baseline_variance_sha256:hash32(&baseline.var),
            baseline_beta:baseline.beta.clone(),probe_seeds:seeds,
            canonical_fields:field_evidence(&canonical,true),linear_fields:field_evidence(&fields[0],true),
            stabilized_fields:field_evidence(&fields[1],true),source_unchanged:true,
        });}
    }
    let base=core::terminal_means(&baseline.merge);
    let canonical=finish(&baseline.merge,&base,&sizes,first.levels,wb)?;
    let identity=finish(&merges[0],&base,&sizes,first.levels,wb)?;
    ensure!(canonical.planes4.iter().zip(&identity.planes4).all(|(a,b)|same(a,b)) && same(&canonical.rgb,&identity.rgb),
        "canonical field replay differs from actual final CFA/MHC");
    Ok(Comparison {canonical,identity,matched_linear:finish(&merges[1],&base,&sizes,first.levels,wb)?,
        stabilized:finish(&merges[2],&base,&sizes,first.levels,wb)?,native_width:2*crop.width,native_height:2*crop.height,
        level_sizes:sizes.iter().map(|s|[s.width,s.height]).collect(),transform,frames:evidence})
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/variance-stabilized-guide/independent-controls.rs"));
}
