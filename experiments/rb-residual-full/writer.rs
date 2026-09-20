use strehl_core::demosaic::{Mosaic,demosaic_malvar_row};

fn normalized_mosaic(planes:&[Vec<f32>],width:usize,height:usize,levels:Levels,wb:[f32;4])->Result<Vec<f32>> {
    ensure!(planes.len()==4 && planes.iter().all(|p|p.len()==width*height
        && p.iter().all(|v|v.is_finite())) && levels.range()>0.0,"writer CFA shape/values");
    ensure!(wb[..3].iter().all(|v|v.is_finite() && *v>0.0),"writer WB");
    let gain=[wb[0]/wb[1],1.0,wb[2]/wb[1]];let nw=2*width;
    let mut mosaic=vec![0.0;4*width*height];
    mosaic.par_chunks_mut(2*nw).enumerate().for_each(|(y,rows)| {
        for (slot,&(dx,dy,ch)) in phase_packed_rgb::SLOTS[..4].iter().enumerate() {
            for x in 0..width {rows[dy*nw+2*x+dx]=planes[slot][y*width+x].max(0.0)*gain[ch]*1.0/levels.range();}
        }
    });
    ensure!(mosaic.iter().all(|v|v.is_finite()),"normalized mosaic nonfinite");Ok(mosaic)
}
/// Full-context MHC, camera-G replacement, same Develop. No CFA re-encoding or second demosaic.
pub(crate) fn guarded_rgb16(baseline:&[Vec<f32>],candidate:&[Vec<f32>],width:usize,height:usize,
    levels:Levels,wb:[f32;4],dev:&image_out::Develop)->Result<(Vec<u16>,serde_json::Value)> {
    let b=normalized_mosaic(baseline,width,height,levels,wb)?;
    let c=normalized_mosaic(candidate,width,height,levels,wb)?;
    let nw=2*width;let nh=2*height;
    let bm=Mosaic{data:&b,width:nw,height:nh};let cm=Mosaic{data:&c,width:nw,height:nh};
    let mut pixels=vec![0u16;3*nw*nh];
    let camera_green_exact=std::sync::atomic::AtomicBool::new(true);
    let finite=std::sync::atomic::AtomicBool::new(true);
    pixels.par_chunks_mut(3*nw).enumerate().for_each(|(y,row)| {
        let mut br=vec![0.0;3*nw];let mut cr=vec![0.0;3*nw];
        demosaic_malvar_row(&bm,y,&mut br);demosaic_malvar_row(&cm,y,&mut cr);
        for ((out,baseline),candidate) in row.chunks_exact_mut(3).zip(br.chunks_exact(3)).zip(cr.chunks_exact(3)) {
            let rgb=[candidate[0],baseline[1],candidate[2]];
            if rgb[1].to_bits()!=baseline[1].to_bits() {camera_green_exact.store(false,Ordering::Relaxed);}
            if !rgb.iter().all(|v|v.is_finite()) {finite.store(false,Ordering::Relaxed);}
            out.copy_from_slice(&image_out::develop_pixel(rgb,dev));
        }
    });
    ensure!(finite.load(Ordering::Relaxed) && camera_green_exact.load(Ordering::Relaxed),"writer camera RGB invalid");
    Ok((pixels,json!({"camera_green_exact":true,"native_dimensions":[nw,nh],
        "path":"full-context MHC -> [candidateR,canonicalG,candidateB] -> unchanged Develop -> RGB16",
        "final_srgb_green_held":false,"second_demosaic":false})))
}
pub(crate) fn write_guarded_rgb(path:&Path,baseline:&[Vec<f32>],candidate:&[Vec<f32>],crop:align_cmd::CropRect,
    levels:Levels,wb:[f32;4],dev:&image_out::Develop)->Result<serde_json::Value> {
    let (pixels,evidence)=guarded_rgb16(baseline,candidate,crop.width,crop.height,levels,wb,dev)?;
    image_out::write_rgb16_described(path,(2*crop.width) as u32,(2*crop.height) as u32,&pixels,dev)?;
    Ok(evidence)
}
