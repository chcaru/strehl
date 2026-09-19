// Test-only complete photograph replay. No production dispatch or RAW writes.
use super::*;
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::{fs::File, io::{Read, Write}};

/// All colour/site pulls are affine, so extrema on the destination rectangle
/// occur at its four corners. Bounds exactly match Catmull sample_checked.
pub(crate) fn full_source_supported(pull: Similarity, full: PlaneGeometry,
    crop: align_cmd::CropRect, ca: Option<&OpticalProfile>) -> bool {
    if full.width < 4 || full.height < 4 || crop.width == 0 || crop.height == 0
        || crop.x.checked_add(crop.width).is_none_or(|v|v>full.width)
        || crop.y.checked_add(crop.height).is_none_or(|v|v>full.height) {return false;}
    let pulls=[Channel::Red,Channel::Green,Channel::Blue].map(|ch|OpticalProfile::compose(ca,ch,pull));
    let support=Resampler::CatmullRom.support();
    SLOTS.iter().all(|&(dx,dy,ch)| {
        [crop.x,crop.x+crop.width-1].into_iter().all(|x| {
            [crop.y,crop.y+crop.height-1].into_iter().all(|y| {
                let (sx,sy)=pulls[ch].apply_at(x as f64+dx as f64*0.5,y as f64+dy as f64*0.5,
                    full.width as f64*0.5,full.height as f64*0.5);
                [(2.0*sx,2*full.width),(2.0*sy,2*full.height)].into_iter().all(|(v,n)|
                    v.is_finite() && v>=support-0.5 && v<=n as f64-0.5-support)
            })
        })
    })
}

/// Unlike retained-patch gathering, this owns the complete real active source:
/// MHC reflects at that physical boundary exactly as the existing CPU consumer.
/// No unsupported sample can be returned, including at the eight missing sites.
pub(crate) fn gather_full_source(frame: &Frame, pull: Similarity, full: PlaneGeometry,
    crop: align_cmd::CropRect, ca: Option<&OpticalProfile>, first_slot: usize) -> Result<Vec<Vec<f32>>> {
    ensure!(first_slot==0 || first_slot==4,"full-source slot start must be zero or four");
    ensure!(frame.geometry()==full && frame.active.width==2*full.width && frame.active.height==2*full.height
        && frame.active.x.checked_add(frame.active.width).is_some_and(|v|v<=frame.stride)
        && frame.active.y.checked_add(frame.active.height).and_then(|v|v.checked_mul(frame.stride)).is_some_and(|v|v<=frame.data.len()),
        "full-source active extent is invalid");
    ensure!(full_source_supported(pull,full,crop,ca),"full-source twelve-pull crop is unsupported");
    let gain=gains(frame.wb_coeffs)?;
    let black=frame.levels.black;
    ensure!(black.is_finite() && frame.levels.range().is_finite() && frame.levels.range()>0.0,"invalid full-source levels");
    let (fw,fh)=(2*full.width,2*full.height);
    let mut mosaic=vec![0.0f32;fw*fh];
    mosaic.par_chunks_mut(fw).enumerate().for_each(|(y,row)| {
        for (x,v) in row.iter_mut().enumerate() {
            let ch=match(y&1,x&1){(0,0)=>0,(1,1)=>2,_=>1};
            *v=(frame.active_row(y)[x] as f32-black)*gain[ch];
        }
    });
    let mut red=vec![0.0f32;fw*fh];
    let mut green=vec![0.0f32;fw*fh];
    let mut blue=vec![0.0f32;fw*fh];
    let m=Mosaic{data:&mosaic,width:fw,height:fh};
    red.par_chunks_mut(fw).zip(green.par_chunks_mut(fw)).zip(blue.par_chunks_mut(fw)).enumerate()
        .for_each_init(||vec![0.0f32;fw*3],|row,(y,((r,g),b))| {
            demosaic_malvar_row(&m,y,row);
            for x in 0..fw {r[x]=row[3*x];g[x]=row[3*x+1];b[x]=row[3*x+2];}
        });
    drop(mosaic);
    let geometry=PlaneGeometry{width:fw,height:fh};
    let refs=[&red,&green,&blue].map(|p|strehl_core::align::PlaneRef::from_geometry(p,geometry).unwrap());
    let pulls=[Channel::Red,Channel::Green,Channel::Blue].map(|ch|OpticalProfile::compose(ca,ch,pull));
    let bad=AtomicUsize::new(0);
    let output=SLOTS[first_slot..].par_iter().map(|&(dx,dy,ch)| {
        let mut plane=vec![0.0f32;crop.width*crop.height];
        plane.par_chunks_mut(crop.width).enumerate().for_each(|(y,row)| {
            for (x,v) in row.iter_mut().enumerate() {
                let (sx,sy)=pulls[ch].apply_at((crop.x+x) as f64+dx as f64*0.5,
                    (crop.y+y) as f64+dy as f64*0.5,full.width as f64*0.5,full.height as f64*0.5);
                match Resampler::CatmullRom.sample_checked(refs[ch],2.0*sx,2.0*sy) {
                    Some(value) if value.is_finite()=>*v=align_cmd::consumed_fullres_value(value,true,1.0/gain[ch],black,align_cmd::DirectPlaneMode::Rounded),
                    _=>{bad.fetch_add(1,Ordering::Relaxed);}
                }
            }
        });
        plane
    }).collect();
    ensure!(bad.load(Ordering::Relaxed)==0,"full-source gather refused {} unsupported/nonfinite samples",bad.load(Ordering::Relaxed));
    Ok(output)
}

#[derive(Debug, Clone, Copy, Serialize)]
pub(crate) struct ChunkPlan {pub planning_bytes:usize,pub canonical_chunks:usize,pub per_chunk:usize}
/// Intentionally budget the canonical FOUR-plane product, not the candidate.
pub(crate) fn chunk_plan(full:PlaneGeometry,frame_bytes:usize,frames:usize,cfg:MergeConfig)->ChunkPlan {
    let sizes=level_sizes(full.width,full.height,cfg.bands);
    let acc=BandMerge::planning_accumulator_floats(full.width,full.height,4,cfg);
    let ws=FrameWorkspace::planning_floats(&sizes,4);
    let planning_bytes=4*(acc+ws+6*full.pixels())+frame_bytes;
    let canonical_chunks=canonical_band_chunks(planning_bytes,frames);
    ChunkPlan{planning_bytes,canonical_chunks,per_chunk:frames.div_ceil(canonical_chunks)}
}

/// Same first-move/subsequent-left-absorb sequence as run_pyramid_prepared.
/// The caller resets scratch before the next chunk, never between its frames.
pub(crate) fn absorb_chunk(retained:&mut Option<BandMerge>,scratch:&mut BandMerge,
    width:usize,height:usize,planes:usize,cfg:MergeConfig) {
    match retained.as_mut() {
        Some(acc)=>acc.absorb(scratch),
        None=>*retained=Some(std::mem::replace(scratch,BandMerge::new(width,height,planes,cfg))),
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema:u32,source_dir:PathBuf,warp_map:PathBuf,warp_map_sha256:String,out_dir:PathBuf,
    expected_crop:[usize;4],expected_xyz_to_cam:[[f32;3];3],tone:[f32;3],max_extra_inset_quads:usize,
}
fn file_hash(path:&Path)->Result<String> {
    let mut input=File::open(path)?;let mut h=Sha256::new();let mut buf=vec![0u8;1<<20];
    loop {let n=input.read(&mut buf)?;if n==0{break;}h.update(&buf[..n]);}
    Ok(h.finalize().iter().map(|v|format!("{v:02x}")).collect())
}
fn write_json(path:&Path,value:&serde_json::Value)->Result<()> {
    let mut f=std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut f,value)?;writeln!(f)?;Ok(())
}
struct OneFrame<'a>{frame:&'a Frame,index:usize,count:usize}
impl PyramidFrameSource for OneFrame<'_> {
    fn len(&self)->usize{self.count}
    fn decode(&self,index:usize)->Result<Frame>{ensure!(index==self.index,"one-frame source index");Ok(self.frame.clone())}
}

pub(crate) fn write_planes(path:&Path,planes:&[Vec<f32>],crop:align_cmd::CropRect,
    levels:Levels,wb:[f32;4],dev:&image_out::Develop)->Result<()> {
    if planes.len()==4 {
        ensure!(planes.iter().all(|p|p.len()==crop.width*crop.height),"baseline write extent");
        let gain=gains(wb)?;
        let width=2*crop.width;let height=2*crop.height;
        let mut mosaic=vec![0.0f32;width*height];
        mosaic.par_chunks_mut(width*2).enumerate().for_each(|(y,rows)| {
            for (slot,&(dx,dy,ch)) in SLOTS[..4].iter().enumerate() {
                for x in 0..crop.width {rows[dy*width+2*x+dx]=planes[slot][y*crop.width+x].max(0.0)*gain[ch]*1.0/levels.range();}
            }
        });
        ensure!(mosaic.par_iter().all(|v|v.is_finite()),"collapsed CFA is nonfinite");
        return image_out::write_demosaiced(path,width,height,&mosaic,dev);
    }
    let rgb=camera_rgb(planes,crop.width,crop.height,levels,wb)?;
    ensure!(rgb.par_iter().all(|v|v.is_finite()),"collapsed camera RGB is nonfinite");
    let mut developed=vec![0u16;rgb.len()];
    developed.par_chunks_mut(3).zip(rgb.par_chunks(3)).for_each(|(out,input)|
        out.copy_from_slice(&image_out::develop_pixel([input[0],input[1],input[2]],dev)));
    image_out::write_rgb16_described(path,(2*crop.width) as u32,(2*crop.height) as u32,&developed,dev)
}

#[test]
#[ignore="explicit complete photograph replay; root bounds resources and freezes config"]
fn vitamin_c_complete_pair()->Result<()> {
    let started=Instant::now();
    let config_path=PathBuf::from(std::env::var_os("STREHL_PHASE_PACKED_FULL_CONFIG").context("STREHL_PHASE_PACKED_FULL_CONFIG required")?);
    let cfg:Config=serde_json::from_slice(&std::fs::read(&config_path)?)?;
    ensure!(cfg.schema==1 && cfg.max_extra_inset_quads<=8,"unsupported full-pair configuration");
    ensure!(cfg.tone.map(f32::to_bits)==[0.090420f32,0.914606,0.55].map(f32::to_bits),"held tone differs");
    ensure!(cfg.expected_xyz_to_cam.iter().flatten().all(|v|v.is_finite()),"nonfinite held matrix");
    ensure!(cfg.source_dir.is_absolute() && cfg.source_dir.file_name().and_then(|v|v.to_str())==Some("crystalized-vitamin-c-cpl"),"wrong source scope");
    ensure!(align_cmd::fullres_gather_enabled() && gatefloor::enabled(),"actual fullres gather and measured probe required");
    ensure!(align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded,"rounded direct planes required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none(),"local placement excluded");
    ensure!(!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional")),"Malvar required");
    ensure!(file_hash(&cfg.warp_map)?==cfg.warp_map_sha256,"held warp map changed");
    let paths=crate::raw_paths(&cfg.source_dir,None)?;
    ensure!(paths.len()==70 && paths.iter().enumerate().all(|(i,p)|p.file_name().and_then(|s|s.to_str())==Some(format!("DSC{:05}.ARW",i+94).as_str())),"complete fixed seventy-frame sequence required");
    let original_map=WarpMap::load(&cfg.warp_map)?;
    original_map.check_stack(&StackIdentity::from_paths("crystalized-vitamin-c-cpl",&paths)?)?;
    ensure!(original_map.resampler()==Resampler::CatmullRom && original_map.len()==70 && original_map.placed_count()==70,"held map does not place all seventy frames");
    let (map,fit)=align_cmd::cover_or_explain(original_map,align_cmd::CoverMode::Crop);
    let initial=fit.rect().context("held map has no crop")?;
    ensure!([initial.x,initial.y,initial.width,initial.height]==cfg.expected_crop,"held baseline crop changed");
    let full=map.geometry();
    ensure!(full==PlaneGeometry{width:3516,height:2344},"unexpected full geometry");
    let identities=paths.iter().map(|p|strehl_raw::identity(p)).collect::<Vec<_>>();
    let profiles=identities.iter().map(|i|strehl_core::optics::profile_for_capture_env(i.model.as_deref(),i.lens_type3)).collect::<std::result::Result<Vec<_>,_>>()?;
    ensure!(profiles.iter().all(|p|p.is_some_and(|p|p.key=="a7c2-fe100gm-2xtc-x4cpl")),"held CA profile differs");
    let crop=(0..=cfg.max_extra_inset_quads).find_map(|inset| {
        let r=align_cmd::CropRect{x:initial.x+inset,y:initial.y+inset,width:initial.width-2*inset,height:initial.height-2*inset};
        (0..70).all(|i|full_source_supported(map.placement(i).unwrap(),full,r,profiles[i])).then_some(r)
    }).context("all twelve pulls lack common supported crop within bounded inset")?;
    let workspace=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize()?;
    ensure!(!cfg.out_dir.exists(),"output directory already exists");
    let parent=cfg.out_dir.parent().context("output parent")?.canonicalize()?;
    ensure!(parent.starts_with(workspace.join("experiments").canonicalize()?),"output must be below workspace experiments");
    let first=strehl_raw::decode(&paths[0])?;
    let levels=first.levels;let wb=first.wb_coeffs;let wb_bits=gains(wb)?.map(f32::to_bits);
    ensure!(first.camera=="ILCE-7CM2" && first.iso==Some(100.0) && levels==Levels{black:512.0,white:15360.0}
        && first.geometry()==full && first.xyz_to_cam_rgb()==Some(cfg.expected_xyz_to_cam),"first-frame held metadata changed");
    let active=first.active;let stride=first.stride;let buffer_height=first.buffer_height;
    let merge_cfg=MergeConfig::default();ensure!(merge_cfg.bands==7,"held seven-band default changed");
    let plan=chunk_plan(full,first.allocated_bytes(),70,merge_cfg);
    let workers=band_workers(plan.planning_bytes,70)?;
    let pool=ThreadPoolBuilder::new().num_threads(workers).build()?;
    let domain=PyramidDomain::cropped(full,crop)?;
    let sizes=level_sizes(crop.width,crop.height,merge_cfg.bands);
    let noise=profile::noise_model_for(&first.camera,first.iso,levels);
    let matrix=color::camera_to_srgb(cfg.expected_xyz_to_cam).context("held matrix singular")?.with_saturation(levels,gains(wb)?,1.0);
    let mut dev=image_out::OutputSpace::Srgb.develop(Some(matrix));
    dev.tone=Some(image_out::Tone{black:cfg.tone[0],white:cfg.tone[1],contrast:cfg.tone[2]});dev.exposure_gain=1.0;
    std::fs::create_dir(&cfg.out_dir)?;
    write_json(&cfg.out_dir.join("started.json"),&json!({"schema":1,"source_dir":cfg.source_dir,"map_sha256":cfg.warp_map_sha256,
        "original_crop":cfg.expected_crop,"effective_crop":[crop.x,crop.y,crop.width,crop.height],"plan":plan,"execution_threads":workers,
        "wb_bits":wb_bits,"tone_bits":cfg.tone.map(f32::to_bits),"matrix":cfg.expected_xyz_to_cam,
        "level_sizes":sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),"config_sha256":file_hash(&config_path)?}))?;
    let mut first=Some(first);
    let mut base=BandWorker::new(domain,merge_cfg);
    let mut packed=BandMerge::new(crop.width,crop.height,12,merge_cfg);
    let mut packed_ws=FrameWorkspace::new(&sizes,12);
    let (mut base_total,mut packed_total)=(None,None);
    let mut evidence=Vec::new();
    pool.install(||->Result<()> {
        let mut chunks=paths.chunks(plan.per_chunk).enumerate().peekable();
        while let Some((chunk_index,chunk))=chunks.next() {
            for (offset,path) in chunk.iter().enumerate() {
                let index=chunk_index*plan.per_chunk+offset;let frame_start=Instant::now();
                let before=std::fs::metadata(path)?;
                let frame=match first.take(){Some(f)=>f,None=>strehl_raw::decode(path)?};
                ensure!(frame.levels==levels && frame.camera=="ILCE-7CM2" && frame.iso==Some(100.0)
                    && frame.active==active && frame.stride==stride && frame.buffer_height==buffer_height
                    && gains(frame.wb_coeffs)?.map(f32::to_bits)==wb_bits && frame.xyz_to_cam_rgb()==Some(cfg.expected_xyz_to_cam),"frame {index} metadata drift");
                let source=OneFrame{frame:&frame,index,count:70};
                ensure!(base.fold(&source,index,levels,&noise,Some(&map),None)?,"frame {index} refused by actual consumer");
                let extra=gather_full_source(&frame,map.placement(index)?,full,crop,profiles[index],4)?;
                let refs=base.planes.iter().chain(extra.iter()).map(Vec::as_slice).collect::<Vec<_>>();
                packed_ws.next_frame();
                packed.add_frame_with_gain(&refs,&base.luma,&base.var,(!base.beta.is_empty()).then_some(base.beta.as_slice()),&mut packed_ws);
                let after=std::fs::metadata(path)?;
                ensure!(before.len()==after.len() && before.modified()?==after.modified()?,"original metadata changed");
                evidence.push(json!({"index":index,"file":path.file_name().map(|v|v.to_string_lossy()),"beta":base.beta,"seconds":frame_start.elapsed().as_secs_f64(),"unsupported_samples":0}));
                eprintln!("phase-packed full {}/70: {:.2}s, total {:.1}s",index+1,frame_start.elapsed().as_secs_f64(),started.elapsed().as_secs_f64());
            }
            absorb_chunk(&mut base_total,&mut base.merge,crop.width,crop.height,4,merge_cfg);
            absorb_chunk(&mut packed_total,&mut packed,crop.width,crop.height,12,merge_cfg);
            if chunks.peek().is_some(){base.reset_chunk();packed.reset_for_reuse();}
        }
        Ok(())
    })?;
    drop(base);drop(packed);drop(packed_ws);
    let base_total=base_total.context("no baseline accumulator")?;
    let packed_total=packed_total.context("no candidate accumulator")?;
    let averaged=base_total.averaged_fraction();
    ensure!(averaged.iter().zip(packed_total.averaged_fraction()).all(|(a,b)|a.to_bits()==b.to_bits()),"admission differs after chunks");
    let baseline=pool.install(||base_total.finish(&mut Workspace::new(&sizes)));drop(base_total);
    let candidate=pool.install(||packed_total.finish(&mut Workspace::new(&sizes)));drop(packed_total);
    for c in 0..4 {ensure!(baseline[c].par_iter().zip(&candidate[c]).all(|(a,b)|a.to_bits()==b.to_bits()),"collapsed known plane {c} differs");}
    let base_path=cfg.out_dir.join("baseline.tiff");let candidate_path=cfg.out_dir.join("candidate.tiff");
    pool.install(||write_planes(&base_path,&baseline,crop,levels,wb,&dev))?;drop(baseline);
    pool.install(||write_planes(&candidate_path,&candidate,crop,levels,wb,&dev))?;drop(candidate);
    write_json(&cfg.out_dir.join("receipt.json"),&json!({"schema":1,"frames":70,"known4_after_finish":"BIT_EXACT",
        "admission":"BIT_EXACT","averaged_fraction":averaged,"unsupported_samples":0,"plan":plan,"frame_evidence":evidence,
        "native_dimensions":[2*crop.width,2*crop.height],"effective_crop":[crop.x,crop.y,crop.width,crop.height],
        "baseline_sha256":file_hash(&base_path)?,"candidate_sha256":file_hash(&candidate_path)?,"seconds":started.elapsed().as_secs_f64()}))?;
    Ok(())
}
