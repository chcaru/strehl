// Independent small-domain controls for the new delivered-RGB path; no RAW reads.
use super::*;

fn pixels(path:&Path,width:u32,height:u32)->Result<(Vec<u16>,Vec<u8>)> {
    let mut d=tiff::decoder::Decoder::new(std::fs::File::open(path)?)?;
    ensure!(d.dimensions()?==(width,height) && d.colortype()?==tiff::ColorType::RGB(16),"TIFF geometry/type");
    let icc=d.get_tag_u8_vec(tiff::tags::Tag::IccProfile)?;
    let tiff::decoder::DecodingResult::U16(values)=d.read_image()? else {anyhow::bail!("not RGB16")};
    ensure!(values.len()==3*width as usize*height as usize && !d.more_images(),"TIFF samples/pages");
    Ok((values,icc))
}

#[test]
fn independent_rb_residual_full_mechanical()->Result<()> {
    let out=PathBuf::from(std::env::var_os("STREHL_RB_RESIDUAL_GUARD_OUT").context("mechanical output required")?);
    std::fs::create_dir_all(&out)?;
    let crop=align_cmd::CropRect{x:3,y:5,width:31,height:23};
    let (w,h)=(crop.width,crop.height);let levels=Levels{black:512.0,white:15360.0};
    let gains=[f32::from_bits(1070374912),1.0,f32::from_bits(1076715520)];
    let wb=[gains[0],1.0,gains[2],f32::NAN];
    let base=(0..4).map(|c|(0..w*h).map(|j| {
        let (x,y)=(j%w,j/w);1800.0+((x*37+y*83+c*211)%3000) as f32
    }).collect::<Vec<_>>()).collect::<Vec<_>>();
    let mut changed=base.clone();
    for j in 0..w*h {
        changed[0][j]+=if (j%w+2*(j/w))%5<2 {700.0}else{-450.0};
        changed[3][j]+=if (2*(j%w)+j/w)%7<3 {-500.0}else{900.0};
    }
    assert_eq!(changed[1],base[1]);assert_eq!(changed[2],base[2]);
    let before=base.iter().chain(&changed).map(|p|hash32(p)).collect::<Vec<_>>();
    let matrix=color::camera_to_srgb([[0.746,-0.2365,-0.0588],[-0.5687,1.3442,0.2474],[-0.0624,0.1156,0.6584]])
        .context("held camera matrix")?.with_saturation(levels,gains,1.0);
    let mut dev=image_out::OutputSpace::Srgb.develop(Some(matrix));
    dev.tone=Some(image_out::Tone{black:0.090420,white:0.914606,contrast:0.55});dev.exposure_gain=1.0;
    // Independent established whole-mosaic implementation, rather than the new row writer.
    let b=phase_packed_rgb::camera_rgb(&base,w,h,levels,wb)?;
    let c=phase_packed_rgb::camera_rgb(&changed,w,h,levels,wb)?;
    let green_changes=b.chunks_exact(3).zip(c.chunks_exact(3)).filter(|(a,z)|a[1].to_bits()!=z[1].to_bits()).count();
    assert!(green_changes>100,"fixture must expose MHC green coupling despite unchanged CFA greens");
    let reference=b.chunks_exact(3).map(|p|image_out::develop_pixel([p[0],p[1],p[2]],&dev)).flatten().collect::<Vec<_>>();
    let expected=b.chunks_exact(3).zip(c.chunks_exact(3)).flat_map(|(b,c)|image_out::develop_pixel([c[0],b[1],c[2]],&dev)).collect::<Vec<_>>();
    let wrong=c.chunks_exact(3).flat_map(|p|image_out::develop_pixel([p[0],p[1],p[2]],&dev)).collect::<Vec<_>>();
    let no_green_copy_differences=expected.iter().zip(&wrong).filter(|(a,b)|a!=b).count();
    let live=expected.iter().zip(&reference).filter(|(a,b)|a!=b).count();
    assert!(no_green_copy_differences>100 && live>100,"green authority and R/B update must survive actual development");
    let (identity,_)=guarded_rgb16(&base,&base,w,h,levels,wb,&dev)?;assert_eq!(identity,reference);
    let (actual,evidence)=guarded_rgb16(&base,&changed,w,h,levels,wb,&dev)?;assert_eq!(actual,expected);
    let legacy=out.join("legacy-identity.tiff");let identical=out.join("guarded-identity.tiff");let candidate=out.join("guarded-live.tiff");
    phase_packed_rgb::full_stack::write_planes(&legacy,&base,crop,levels,wb,&dev)?;
    write_guarded_rgb(&identical,&base,&base,crop,levels,wb,&dev)?;
    write_guarded_rgb(&candidate,&base,&changed,crop,levels,wb,&dev)?;
    let old=pixels(&legacy,(2*w) as u32,(2*h) as u32)?;
    let same=pixels(&identical,(2*w) as u32,(2*h) as u32)?;
    let new=pixels(&candidate,(2*w) as u32,(2*h) as u32)?;
    assert_eq!(old.0,reference);assert_eq!(same.0,old.0);assert_eq!(new.0,expected);
    assert!(!old.1.is_empty());assert_eq!(old.1,same.1);assert_eq!(old.1,new.1);
    assert_eq!(before,base.iter().chain(&changed).map(|p|hash32(p)).collect::<Vec<_>>());
    let mut invalid=changed.clone();invalid[0][0]=f32::NAN;
    assert!(guarded_rgb16(&base,&invalid,w,h,levels,wb,&dev).is_err());
    assert!(guarded_rgb16(&base,&changed,w,h,levels,[0.0,1.0,1.0,1.0],&dev).is_err());
    // Independent SciPy reference from the frozen scalar-tail control, not a population-one cost threshold.
    let q=threshold(70,7)?;assert!((q-221.6844284406637).abs()<1e-8);
    assert_eq!(threshold_f32(70,7)?.to_bits(),(q as f32).to_bits()+u32::from((q as f32 as f64)<q));
    let receipt=json!({"schema":1,"writer":evidence,"samples":actual.len(),"mhc_camera_green_changed_pixels":green_changes,
        "missing_green_copy_wrong_samples":no_green_copy_differences,"live_output_samples":live,
        "old_writer_identity_exact":true,"independent_camera_rgb_oracle_exact":true,"icc_exact":true,
        "source_arrays_unchanged":true,"threshold_population":70,"threshold":q,
        "original_generated_admission":false,"quality_claim":false});
    std::fs::write(out.join("mechanical.json"),serde_json::to_vec_pretty(&receipt)?)?;
    eprintln!("RB_RESIDUAL_FULL_MECHANICAL {receipt}");Ok(())
}
