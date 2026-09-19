// Test-only intervention: preserve eight missing-colour planes through the
// existing quad-grid merge. No new focus decision, noise model or RAW decoder.
use super::*;
use sha2::{Digest, Sha256};
use strehl_core::align::Similarity;
use strehl_core::demosaic::{Mosaic, demosaic_malvar_row};
use strehl_core::optics::{Channel, OpticalProfile};

/// The first four slots are the existing consumer's CFA slots, unchanged.
/// Remaining slots are missing colours in site-major, channel-major order.
pub(crate) const SLOTS: [(usize, usize, usize); 12] = [
    (0,0,0), (1,0,1), (0,1,1), (1,1,2),
    (0,0,1), (0,0,2), (1,0,0), (1,0,2),
    (0,1,0), (0,1,2), (1,1,0), (1,1,1),
];

pub(crate) struct CfaPatch {
    pub data: Vec<u16>,
    pub origin_native: [usize; 2],
    pub width: usize,
    pub height: usize,
    pub levels: Levels,
    pub wb_coeffs: [f32; 4],
}

impl CfaPatch {
    pub(crate) fn from_frame(frame: &Frame) -> Self {
        let mut data = Vec::with_capacity(frame.active.width * frame.active.height);
        for y in 0..frame.active.height { data.extend_from_slice(frame.active_row(y)); }
        Self { data, origin_native: [0,0], width: frame.active.width, height: frame.active.height,
            levels: frame.levels, wb_coeffs: frame.wb_coeffs }
    }
}

fn gains(wb: [f32; 4]) -> Result<[f32; 3]> {
    ensure!(wb[..3].iter().all(|v| v.is_finite() && *v > 0.0), "invalid phase-packed WB");
    // Same expression as align_cmd::wb_gains, with its invalid-input fallback
    // explicitly refused by this bounded adapter.
    Ok([wb[0]/wb[1],1.0,wb[2]/wb[1]])
}

/// Gather one bounded original-CFA patch directly into twelve consumed planes.
/// Every source MHC/Catmull stencil must be present; there is no filler, edge
/// extension at a retained-patch boundary, or second geometric resampling.
pub(crate) fn gather_patch(patch: &CfaPatch, pull: Similarity, full: PlaneGeometry,
    crop: align_cmd::CropRect, ca: Option<&OpticalProfile>) -> Result<Vec<Vec<f32>>> {
    ensure!(patch.width >= 8 && patch.height >= 8
        && patch.width.checked_mul(patch.height) == Some(patch.data.len())
        && patch.data.len() <= 1024 * 1024
        && patch.origin_native.iter().all(|v| v % 2 == 0)
        && patch.origin_native[0].checked_add(patch.width).is_some_and(|x| x <= 2 * full.width)
        && patch.origin_native[1].checked_add(patch.height).is_some_and(|y| y <= 2 * full.height),
        "phase-packed patch is unsupported or exceeds the bounded adapter");
    ensure!(crop.width > 0 && crop.height > 0 && crop.width * crop.height <= 512 * 512
        && crop.x.checked_add(crop.width).is_some_and(|x| x <= full.width)
        && crop.y.checked_add(crop.height).is_some_and(|y| y <= full.height),
        "phase-packed destination crop is unsupported");
    let gain = gains(patch.wb_coeffs)?;
    let black = patch.levels.black;
    ensure!(black.is_finite() && patch.levels.range().is_finite() && patch.levels.range() > 0.0,
        "phase-packed levels are invalid");
    let mut mosaic = vec![0.0f32; patch.data.len()];
    for y in 0..patch.height { for x in 0..patch.width {
        let ch = if y % 2 == 0 && x % 2 == 0 {0} else if y % 2 == 1 && x % 2 == 1 {2} else {1};
        mosaic[y * patch.width + x] = (patch.data[y * patch.width + x] as f32 - black) * gain[ch];
    }}
    let m = Mosaic { data: &mosaic, width: patch.width, height: patch.height };
    let mut channels: [Vec<f32>; 3] = std::array::from_fn(|_| vec![0.0; patch.data.len()]);
    let mut row = vec![0.0; patch.width * 3];
    for y in 0..patch.height {
        demosaic_malvar_row(&m,y,&mut row);
        for x in 0..patch.width { for ch in 0..3 { channels[ch][y * patch.width + x] = row[3*x+ch]; }}
    }
    drop(mosaic);
    let source_geometry = PlaneGeometry { width: patch.width, height: patch.height };
    let refs = channels.iter().map(|p| strehl_core::align::PlaneRef::from_geometry(p,source_geometry).unwrap()).collect::<Vec<_>>();
    let pulls = [Channel::Red,Channel::Green,Channel::Blue].map(|ch| OpticalProfile::compose(ca,ch,pull));
    let mut result = Vec::with_capacity(12);
    for (dx,dy,ch) in SLOTS {
        let mut plane = vec![0.0; crop.width * crop.height];
        for y in 0..crop.height { for x in 0..crop.width {
            let (sx,sy) = pulls[ch].apply_at((crop.x+x) as f64+dx as f64*0.5,
                (crop.y+y) as f64+dy as f64*0.5,full.width as f64*0.5,full.height as f64*0.5);
            let source = [2.0*sx,2.0*sy];
            for axis in 0..2 {
                let size = [patch.width,patch.height][axis];
                ensure!(source[axis].is_finite()
                    && source[axis].floor()-3.0 >= patch.origin_native[axis] as f64
                    && source[axis].floor()+4.0 < (patch.origin_native[axis]+size) as f64,
                    "phase-packed MHC/Catmull source support is incomplete");
            }
            let value = strehl_core::align::sample_catmull_rom(refs[ch],
                source[0]-patch.origin_native[0] as f64,source[1]-patch.origin_native[1] as f64);
            ensure!(value.is_finite(), "phase-packed reconstruction was nonfinite");
            plane[y * crop.width+x] = align_cmd::consumed_fullres_value(value,true,1.0/gain[ch],black,
                align_cmd::DirectPlaneMode::Rounded);
        }}
        result.push(plane);
    }
    Ok(result)
}

pub(crate) struct FrameEvidence {
    pub source_sha256: String,
    pub guide_sha256: String,
    pub variance_sha256: String,
    pub beta: Vec<f32>,
}

pub(crate) struct Comparison {
    pub baseline_planes4: Vec<Vec<f32>>,
    pub packed_planes12: Vec<Vec<f32>>,
    /// Interleaved native camera RGB, WB/range normalized, before development.
    pub baseline_rgb: Vec<f32>,
    pub candidate_rgb: Vec<f32>,
    pub native_width: usize,
    pub native_height: usize,
    pub level_sizes: Vec<[usize; 2]>,
    pub frames: Vec<FrameEvidence>,
    pub averaged_fraction: Vec<f64>,
}

fn hash(bytes: impl IntoIterator<Item=u8>) -> String {
    let mut h = Sha256::new();
    // Bounded fixture inputs; do not introduce an original-file read here.
    for chunk in bytes.into_iter().collect::<Vec<_>>().chunks(65536) { h.update(chunk); }
    h.finalize().iter().map(|b|format!("{b:02x}")).collect()
}

pub(crate) fn camera_rgb(planes: &[Vec<f32>], width: usize, height: usize,
    levels: Levels, wb: [f32;4]) -> Result<Vec<f32>> {
    ensure!((planes.len()==4 || planes.len()==12)
        && planes.iter().all(|p|p.len()==width*height),"phase-packed output geometry");
    let gain=gains(wb)?;
    let native_width=2*width;
    let native_height=2*height;
    let norm=|value:f32,ch:usize| value.max(0.0)*gain[ch]*1.0/levels.range();
    if planes.len()==4 {
        let mut mosaic=vec![0.0;native_width*native_height];
        for (slot,&(dx,dy,ch)) in SLOTS[..4].iter().enumerate() {
            for y in 0..height {for x in 0..width {
                mosaic[(2*y+dy)*native_width+2*x+dx]=norm(planes[slot][y*width+x],ch);
            }}
        }
        let m=Mosaic{data:&mosaic,width:native_width,height:native_height};
        let mut rgb=vec![0.0;mosaic.len()*3];
        for y in 0..native_height {demosaic_malvar_row(&m,y,&mut rgb[y*native_width*3..(y+1)*native_width*3]);}
        Ok(rgb)
    } else {
        let mut rgb=vec![0.0;native_width*native_height*3];
        for (slot,&(dx,dy,ch)) in SLOTS.iter().enumerate() {
            for y in 0..height {for x in 0..width {
                rgb[((2*y+dy)*native_width+2*x+dx)*3+ch]=norm(planes[slot][y*width+x],ch);
            }}
        }
        Ok(rgb)
    }
}

/// Paired generated stack. The baseline is the actual BandWorker; the candidate
/// borrows its exact guide, injected variance and measured probe for each frame.
/// This small screen deliberately uses one arithmetic chunk in both arms.
pub(crate) fn compare_generated(frames: &[Frame], transforms: &[Similarity],
    crop: align_cmd::CropRect, noise: &NoiseModel, cfg: MergeConfig) -> Result<Comparison> {
    ensure!(!frames.is_empty() && frames.len()<=32 && frames.len()==transforms.len(),"bounded frame count");
    let full=frames[0].geometry();
    ensure!(full.width<=512 && full.height<=512
        && frames.iter().all(|f|f.geometry()==full && f.levels==frames[0].levels && !f.path.exists()),
        "generated bounded frames only; no RAW input path may exist");
    ensure!(frames.iter().all(|f|f.wb_coeffs[..3]==frames[0].wb_coeffs[..3]),"one stack WB required");
    ensure!(align_cmd::fullres_gather_enabled(),"phase-packed screen requires fullres gather");
    ensure!(!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV)
        .is_ok_and(|v|v.eq_ignore_ascii_case("directional")),"phase-packed screen requires Malvar");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none(),"phase-packed screen excludes local-placement intervention");
    ensure!(gatefloor::enabled(),"phase-packed screen requires the actual measured probe");
    let domain=PyramidDomain::cropped(full,crop)?;
    let sizes=level_sizes(crop.width,crop.height,cfg.bands);
    let entries=frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes() as u64)).collect::<Vec<_>>();
    let map=WarpMap::new(strehl_core::warpmap::Provenance{
        stack:StackIdentity::from_entries("phase-packed-generated",&entries),strategy:"supplied independent truth geometry".into(),
        heldout_px:None,cycle_floor_px:None,reference:0,note:"bounded generated consumer; no fitted geometry".into()},
        full,Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a [Frame]);
    impl PyramidFrameSource for Source<'_> {
        fn len(&self)->usize{self.0.len()}
        fn decode(&self,index:usize)->Result<Frame>{Ok(self.0[index].clone())}
    }
    let source=Source(frames);
    let mut baseline=BandWorker::new(domain,cfg);
    let mut candidate=BandMerge::new(crop.width,crop.height,12,cfg);
    let mut workspace=FrameWorkspace::new(&sizes,12);
    let mut evidence=Vec::new();
    for (index,frame) in frames.iter().enumerate() {
        let before=hash(frame.data.iter().flat_map(|v|v.to_le_bytes()));
        ensure!(baseline.fold(&source,index,frame.levels,noise,Some(&map),None)?,"generated frame refused");
        let packed=gather_patch(&CfaPatch::from_frame(frame),transforms[index],full,crop,None)?;
        for c in 0..4 {
            ensure!(packed[c].iter().zip(&baseline.planes[c]).all(|(a,b)|a.to_bits()==b.to_bits()),
                "phase-packed slot {c} disagrees with actual gathered CFA at frame {index}");
        }
        let refs=packed.iter().map(Vec::as_slice).collect::<Vec<_>>();
        workspace.next_frame();
        let beta=(!baseline.beta.is_empty()).then_some(baseline.beta.as_slice());
        candidate.add_frame_with_gain(&refs,&baseline.luma,&baseline.var,beta,&mut workspace);
        ensure!(before==hash(frame.data.iter().flat_map(|v|v.to_le_bytes())),"original generated CFA changed");
        evidence.push(FrameEvidence{source_sha256:before,
            guide_sha256:hash(baseline.luma.iter().flat_map(|v|v.to_bits().to_le_bytes())),
            variance_sha256:hash(baseline.var.iter().flat_map(|v|v.to_bits().to_le_bytes())),beta:baseline.beta.clone()});
    }
    let averaged_fraction=baseline.merge.averaged_fraction();
    ensure!(averaged_fraction.iter().zip(candidate.averaged_fraction()).all(|(a,b)|a.to_bits()==b.to_bits()),
        "phase-packed admission differs");
    let baseline_planes4=baseline.merge.finish(&mut Workspace::new(&sizes));
    let packed_planes12=candidate.finish(&mut Workspace::new(&sizes));
    for c in 0..4 {
        ensure!(baseline_planes4[c].iter().zip(&packed_planes12[c]).all(|(a,b)|a.to_bits()==b.to_bits()),
            "phase-packed collapsed CFA slot {c} differs");
    }
    let baseline_rgb=camera_rgb(&baseline_planes4,crop.width,crop.height,frames[0].levels,frames[0].wb_coeffs)?;
    let candidate_rgb=camera_rgb(&packed_planes12,crop.width,crop.height,frames[0].levels,frames[0].wb_coeffs)?;
    Ok(Comparison{baseline_planes4,packed_planes12,baseline_rgb,candidate_rgb,native_width:2*crop.width,
        native_height:2*crop.height,level_sizes:sizes.iter().map(|s|[s.width,s.height]).collect(),
        frames:evidence,averaged_fraction})
}

#[cfg(feature = "native-gpu-gather")]
mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/phase-packed-rgb/independent-controls.rs"));
}

pub(crate) mod full_stack {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/phase-packed-rgb/full-stack.rs"));
}
