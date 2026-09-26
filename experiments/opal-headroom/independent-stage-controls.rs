// Child module of stage-observer.rs; independently selected boundary/phase cases.
use super::*;

#[test]
fn independent_pin_predicate_differs_from_changed_count_and_support_obeys_phase()->Result<()> {
    let dev = Develop {
        matrix: Some(color::Render::new([[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]).with_ceiling([1.;3])),
        srgb: true, tone: Some(Tone {black:0.,white:1.,contrast:0.55}),
        wants_tone:true, exposure_gain:1.,
    };
    let at = observe_pixel([1.,0.2,0.1],&dev)?;
    ensure!(at.pin==1 && same(at.camera,at.clipped),
        "equality pin must be counted even when the clip changes no channel");
    let below = observe_pixel([f32::from_bits(1.0f32.to_bits()-1),0.2,0.1],&dev)?;
    let above = observe_pixel([f32::from_bits(1.0f32.to_bits()+1),0.2,0.1],&dev)?;
    ensure!(below.pin==0 && same(below.camera,below.clipped),"one-ULP below ceiling unexpectedly pinned");
    ensure!(above.pin==1 && !same(above.camera,above.clipped),"one-ULP crossing control unexercised");
    let mut counts=Counts::default();
    for p in [&below,&at,&above] {counts.add(p);}
    ensure!(counts.pixels==3 && counts.pin_pixels==2 && counts.clip_changed==1,
        "pin predicate was conflated with changed-pixel count");

    let ceiling=[2.,1.,3.];
    let mut data=vec![0.;81];
    for y in 0..9 {for x in 0..9 {
        // Fixed literal RGGB tile, independently specified rather than using
        // the observer's phase branch to generate the test data.
        data[y*9+x]=if y%2==0 {if x%2==0{1.0}else{0.5}}
            else {if x%2==0{0.5}else{1.5}};
    }}
    for (x,y,limit) in [(4,4,2.),(5,4,1.),(4,5,1.),(5,5,3.)] {
        let m=Mosaic{data:&data,width:9,height:9};
        let (_,below,fraction)=support(&m,x,y,ceiling)?;
        ensure!(below && fraction==0.5,"unequal-channel support used the wrong CFA ceiling");
        let mut pinned=data.clone();pinned[y*9+x]=limit;
        let m=Mosaic{data:&pinned,width:9,height:9};
        let (_,below,fraction)=support(&m,x,y,ceiling)?;
        ensure!(!below && fraction==1.,"own-phase equality failed to invalidate strict-below support");
        pinned[y*9+x]=f32::from_bits(limit.to_bits()-1);
        let m=Mosaic{data:&pinned,width:9,height:9};
        let (_,below,fraction)=support(&m,x,y,ceiling)?;
        ensure!(below && fraction<1.,"own-phase below-ceiling sample was falsely classified");
    }
    Ok(())
}
