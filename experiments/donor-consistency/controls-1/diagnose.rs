use strehl_core::pyramid::{level_sizes,BandMerge,FrameWorkspace,Hull,MergeConfig,Pyramid,Workspace};
use strehl_core::pyramid::donor_consistency_diagnostic::{DonorBlend,resolved_coefficients};
const W:usize=89; const H:usize=73;
fn cfg()->MergeConfig {MergeConfig{bands:3,hull:Hull::InputRange,mean_coarse:0,significance_scale:0.0,..MergeConfig::default()}}
fn fixtures()->(Vec<Vec<u16>>,Vec<Vec<Vec<f32>>>) {
    let mut stored=Vec::new();let mut consumed=Vec::new();
    for source in 0..3 {
        let mut raw=vec![0u16;W*H*4];let mut planes=vec![vec![0.0;W*H];4];
        for c in 0..4 {for y in 0..H {for x in 0..W {
            let phase=x as f64*(c+1) as f64/9.0+y as f64*(4-c) as f64/13.0+source as f64*1.4;
            let value=if x==W/2 && y==H/2 {1800.0+140.0*c as f64} else {
                1000.0+600.0*source as f64+140.0*c as f64+(80.0+23.0*c as f64)*phase.sin()+0.75*x as f64+1.2*y as f64
            };
            let index=y*W+x;raw[4*index+c]=(512.0+value).round() as u16;
            planes[c][index]=f32::from(raw[4*index+c])-512.0;
        }}}
        stored.push(raw);consumed.push(planes);
    }(stored,consumed)
}
fn merge(frames:&[Vec<Vec<f32>>])->BandMerge {
    let sizes=level_sizes(W,H,3);assert_eq!(sizes.len(),4);
    let mut result=BandMerge::new(W,H,4,cfg());let mut ws=FrameWorkspace::new(&sizes,4);
    for frame in frames {
        let guide=frame[1].iter().zip(&frame[2]).map(|(a,b)|0.5*(a+b)).collect::<Vec<_>>();
        let variance=vec![16.0;W*H];let refs=frame.iter().map(Vec::as_slice).collect::<Vec<_>>();
        result.add_frame(&refs,&guide,&variance,&mut ws);
    }result
}
fn pyramids(frame:&[Vec<f32>])->Vec<Pyramid> {
    let sizes=level_sizes(W,H,3);frame.iter().map(|p|{
        let mut q=Pyramid::zeros(&sizes);q.build(p,&mut Workspace::new(&sizes));q
    }).collect()
}
fn collapse_hull(pyr:&[Pyramid],frames:&[Vec<Vec<f32>>])->(Vec<Vec<f32>>,usize) {
    let sizes=level_sizes(W,H,3);let mut excursions=0;
    let out=pyr.iter().enumerate().map(|(c,p)|{
        let mut v=p.collapse(&mut Workspace::new(&sizes));
        for (i,x) in v.iter_mut().enumerate() {
            let lo=frames.iter().map(|f|f[c][i]).fold(f32::INFINITY,f32::min);
            let hi=frames.iter().map(|f|f[c][i]).fold(f32::NEG_INFINITY,f32::max);
            if *x<lo || *x>hi {excursions+=1;}
            *x=x.clamp(lo,hi);
        }v
    }).collect();(out,excursions)
}
fn main(){let (_,frames)=fixtures();let sizes=level_sizes(W,H,3);let baseline=merge(&frames);let resolved=resolved_coefficients(&baseline);let source=pyramids(&frames[0]);let mut expected=source.clone();for c in 0..4{expected[c].level_mut(3).copy_from_slice(resolved[c].level(3));}let mut ones=DonorBlend::new(&sizes,4,&[vec![1.0;W*H]]);ones.add_source(&[0],&frames[0]);let (want,excursions)=collapse_hull(&expected,&frames);let got=ones.finish(&baseline,&mut Workspace::new(&sizes));let pin=(H/2)*W+W/2;println!("excursions {}",excursions);for c in 0..4{let e=want[c].iter().zip(&got[c]).map(|(a,b)|(a-b).abs()).fold(0.0f32,f32::max);let before=expected[c].collapse(&mut Workspace::new(&sizes));println!("plane {} error {} pin pre {} expected {} actual {}",c,e,before[pin],want[c][pin],got[c][pin]);}}
