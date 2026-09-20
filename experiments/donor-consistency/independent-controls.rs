use super::{capsule_at,fixed_masks};
use serde_json::json;
use sha2::{Digest,Sha256};
use strehl_core::pyramid::{level_sizes,BandMerge,FrameWorkspace,Hull,MergeConfig,Pyramid,Workspace};
use strehl_core::pyramid::donor_consistency_diagnostic::{DonorBlend,resolved_coefficients};

mod attribution_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/donor-consistency/independent-attribution-controls.rs"));
}

mod spatial_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/donor-consistency/independent-spatial-controls.rs"));
}

mod spatial_witness_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/donor-consistency/independent-spatial-witness-controls.rs"));
}

const W:usize=89;
const H:usize=73;
fn hash(v:&[f32])->String {
    let mut h=Sha256::new();for x in v {h.update(x.to_bits().to_le_bytes());}
    h.finalize().iter().map(|b|format!("{b:02x}")).collect()
}
fn hashes(v:&[Vec<Vec<f32>>])->Vec<String> {v.iter().flat_map(|f|f.iter().map(|p|hash(p))).collect()}
fn exact(a:&[Vec<f32>],b:&[Vec<f32>]) {
    assert_eq!(a.len(),b.len());for (a,b) in a.iter().zip(b) {assert_eq!(hash(a),hash(b));}
}
fn worst(a:&[f32],b:&[f32])->f32 {
    assert_eq!(a.len(),b.len());a.iter().zip(b).map(|(&a,&b)|{assert!(a.is_finite() && b.is_finite());(a-b).abs()}).fold(0.0,f32::max)
}
fn refused(f:impl FnOnce()) {assert!(std::panic::catch_unwind(std::panic::AssertUnwindSafe(f)).is_err());}
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
        // Match BandWorker's per-source cache boundary. Otherwise PlaneCache
        // silently keeps the first source's decomposition for every fold.
        ws.next_frame();
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
fn analytic_capsule(x:f64,y:f64,a:[f64;2],b:[f64;2])->f64 {
    let dx=b[0]-a[0];let dy=b[1]-a[1];let length=dx*dx+dy*dy;
    let t=if length==0.0 {0.0} else {((x-a[0])*dx+(y-a[1])*dy)/length}.clamp(0.0,1.0);
    let r=(x-a[0]-t*dx).hypot(y-a[1]-t*dy);
    if r<=16.0 {1.0} else if r>=24.0 {0.0} else {let u=(r-16.0)/8.0;1.0-u*u*(3.0-2.0*u)}
}

fn explicit_clamp_witness() {
    // Donor0 is constant. Other sources are brighter except at the one shared
    // centre sample. Positive Gaussian weights make the retained mean base
    // strictly brighter there; zero donor AC cannot cancel that excursion.
    let sizes=level_sizes(W,H,3);let pin=(H/2)*W+W/2;
    let frames=(0..3).map(|s|(0..4).map(|c|(0..W*H).map(|i|{
        let raw=(512+1000+100*c+if s==0 || i==pin {0}else{2000}) as u16;
        f32::from(raw)-512.0
    }).collect::<Vec<_>>()).collect::<Vec<_>>()).collect::<Vec<_>>();
    let base=merge(&frames);let coefficients=resolved_coefficients(&base);let donor=pyramids(&frames[0]);
    let mut expected=donor.clone();
    for c in 0..4 {
        assert!(donor[c].level(0).iter().all(|&v|v==0.0));
        let low=coefficients[c].level(3).iter().copied().fold(f32::INFINITY,f32::min);
        assert!(low>frames[0][c][pin]+1000.0,"explicit mean-base lower bound not exercised: {low}");
        expected[c].level_mut(3).copy_from_slice(coefficients[c].level(3));
    }
    let pre=expected.iter().map(|p|p.collapse(&mut Workspace::new(&sizes))[pin]).collect::<Vec<_>>();
    for c in 0..4 {assert!(pre[c]>frames[0][c][pin]+1000.0);}
    let mut blend=DonorBlend::new(&sizes,4,&[vec![1.0;W*H]]);blend.add_source(&[0],&frames[0]);
    let actual=blend.finish(&base,&mut Workspace::new(&sizes));let (bounded,count)=collapse_hull(&expected,&frames);
    let error=actual.iter().zip(&bounded).map(|(a,b)|worst(a,b)).fold(0.0,f32::max);
    eprintln!("DONOR_EXPLICIT_CLAMP {}",json!({"pre_hull_pin":pre,"post_hull_pin":actual.iter().map(|p|p[pin]).collect::<Vec<_>>(),"excursions":count,"max_error_dn":error}));
    assert!(count>=4);assert!(error<=0.003);
    for c in 0..4 {assert_eq!(actual[c][pin].to_bits(),frames[0][c][pin].to_bits());}
}

#[test]
fn independent_donor_00_native_geometry() {
    let a=[13.0,-7.0];let b=[53.0,-7.0];
    for (p,expected) in [([13.0,-7.0],1.0),([33.0,-7.0],1.0),([53.0,-7.0],1.0),
        ([33.0,9.0],1.0),([33.0,13.0],0.5),([33.0,17.0],0.0),([-7.0,-7.0],0.5),([73.0,-7.0],0.5)] {
        assert!((capsule_at(p[0],p[1],a,b)-expected).abs()<1e-6);
        assert_eq!(capsule_at(p[0],p[1],a,b).to_bits(),capsule_at(p[0],p[1],b,a).to_bits());
    }
    assert_eq!(capsule_at(5.0,29.0,[5.0,9.0],[5.0,9.0]),0.5);
    let segments=[([2624.0,2906.0],[2602.0,2945.0]),([3080.0,2150.0],[3102.0,2203.0]),([3240.0,2070.0],[3240.0,2070.0])];
    let mut max_error=0.0f64;let mut active=0;let mut fractional=0;let mut phase_changed=0;
    for origin in [[2561isize,2853isize],[3011,2089],[3199,2017]] {
        let previous=fixed_masks(W,H,origin);assert_eq!(previous.len(),3);
        for phase in 0..2 {
            let offset=[origin[0]+phase,origin[1]+phase];let fields=fixed_masks(W,H,offset);
            for (r,(a,b)) in segments.iter().enumerate() {for y in 0..H {for x in 0..W {
                let i=y*W+x;let value=fields[r][i];
                assert!((0.0..=1.0).contains(&value));
                let expected=analytic_capsule((2*x) as f64+0.5+offset[0] as f64,(2*y) as f64+0.5+offset[1] as f64,*a,*b);
                let error=(f64::from(value)-expected).abs();max_error=max_error.max(error);assert!(error<1e-4);
                active+=usize::from(value==1.0);fractional+=usize::from(value>0.0 && value<1.0);
                if phase==1 && value.to_bits()!=previous[r][i].to_bits() {phase_changed+=1;}
            }}}
        }
    }
    assert!(active>100 && fractional>100 && phase_changed>100);
    eprintln!("DONOR_GEOMETRY {}",json!({"max_analytic_mask_error":max_error,"full_weight_samples":active,"taper_samples":fractional,"one_native_phase_changed":phase_changed,
        "evaluation":"2*quad+0.5+odd native output offset; three fixed photo masks"}));
}

#[test]
fn independent_donor_10_actual_coefficients_finish_and_placebo() {
    let (raw,frames)=fixtures();let raw_before=raw.clone();let before=hashes(&frames);
    let sizes=level_sizes(W,H,3);let baseline=merge(&frames);let baseline_out=baseline.finish(&mut Workspace::new(&sizes));
    let resolved=resolved_coefficients(&baseline);
    // Independent fresh Pyramid objects for every original source expose a
    // missed FrameWorkspace::next_frame even when finish agrees with itself.
    let originals=frames.iter().map(|f|pyramids(f)).collect::<Vec<_>>();
    let mut mean_base_error=0.0f32;
    for c in 0..4 {
        for source in 1..frames.len() {
            assert!(worst(originals[0][c].level(3),originals[source][c].level(3))>100.0,
                "distinct-source mean-base regression is not exercised");
        }
        let mean=(0..sizes[3].pixels()).map(|i|{
            let mut sum=0.0f32;for source in &originals {sum+=source[c].level(3)[i];}
            sum*(1.0/frames.len() as f32)
        }).collect::<Vec<_>>();
        mean_base_error=mean_base_error.max(worst(resolved[c].level(3),&mean));
        assert_eq!(hash(resolved[c].level(3)),hash(&mean),"terminal base must average all distinct sources");
    }
    let (ordinary,_) =collapse_hull(&resolved,&frames);exact(&ordinary,&baseline_out);
    let off=DonorBlend::new(&sizes,4,&[]);exact(&off.finish(&baseline,&mut Workspace::new(&sizes)),&baseline_out);
    let mut zero=DonorBlend::new(&sizes,4,&[vec![0.0;W*H]]);zero.add_source(&[0],&frames[0]);
    exact(&zero.finish(&baseline,&mut Workspace::new(&sizes)),&baseline_out);
    let source=pyramids(&frames[0]);let mut ones=DonorBlend::new(&sizes,4,&[vec![1.0;W*H]]);ones.add_source(&[0],&frames[0]);
    let mut expected=source.clone();for c in 0..4 {expected[c].level_mut(3).copy_from_slice(resolved[c].level(3));}
    let mixed=ones.mixed_coefficients(&baseline);
    for c in 0..4 {for level in 0..4 {assert_eq!(hash(mixed[c].level(level)),hash(expected[c].level(level)));}}
    let (expected_out,excursions)=collapse_hull(&expected,&frames);let actual=ones.finish(&baseline,&mut Workspace::new(&sizes));
    let ones_error=actual.iter().zip(&expected_out).map(|(a,b)|worst(a,b)).fold(0.0,f32::max);
    let pin=(H/2)*W+W/2;
    eprintln!("DONOR_ONES_DIAGNOSTIC {}",json!({"max_error_dn":ones_error,"excursions":excursions,
        "source_pin":frames.iter().map(|f|f.iter().map(|p|p[pin]).collect::<Vec<_>>()).collect::<Vec<_>>(),
        "pre_hull_pin":expected.iter().map(|p|p.collapse(&mut Workspace::new(&sizes))[pin]).collect::<Vec<_>>(),
        "expected_bounded_pin":expected_out.iter().map(|p|p[pin]).collect::<Vec<_>>(),"actual_pin":actual.iter().map(|p|p[pin]).collect::<Vec<_>>()}));
    assert!(ones_error<=0.003,"all-ones independent finish error {ones_error}");
    assert!(excursions>=4,"original shared-pin clamp witness had only {excursions} excursions");
    explicit_clamp_witness();
    let changed_baseline=actual.iter().zip(&baseline_out).flat_map(|(a,b)|a.iter().zip(b)).filter(|(a,b)|a.to_bits()!=b.to_bits()).count();
    let changed_donor=actual.iter().zip(&frames[0]).flat_map(|(a,b)|a.iter().zip(b)).filter(|(a,b)|a.to_bits()!=b.to_bits()).count();
    assert!(changed_baseline>100 && changed_donor>100);
    let masks=vec![(0..W*H).map(|i|if i%W<W/2 {0.9}else{0.2}).collect::<Vec<_>>(),
        (0..W*H).map(|i|if i/W<H/2 {0.8}else{0.35}).collect::<Vec<_>>()];
    let mut expected_masks=masks.iter().map(|m|{let mut p=Pyramid::zeros(&sizes);p.build_gaussian(m,&mut Workspace::new(&sizes));p}).collect::<Vec<_>>();
    let mut overlap=vec![0usize;sizes.len()];let mut normalized=vec![0usize;sizes.len()];
    for level in 0..sizes.len() {for i in 0..sizes[level].pixels() {
        let a=expected_masks[0].level(level)[i];let b=expected_masks[1].level(level)[i];let sum=a+b;
        if a>0.0 && b>0.0 {overlap[level]+=1;}
        if sum>1.0 {normalized[level]+=1;expected_masks[0].level_mut(level)[i]=a/sum;expected_masks[1].level_mut(level)[i]=b/sum;}
    }}
    assert!(normalized.iter().all(|&n|n>0));
    let mut blend=DonorBlend::new(&sizes,4,&masks);blend.add_source(&[0],&frames[0]);blend.add_source(&[1],&frames[1]);
    assert_eq!(blend.raw_overlap_counts(),overlap.as_slice());assert_eq!(blend.normalized_counts(),normalized.as_slice());
    let mut mask_error=0.0f32;
    for level in 0..sizes.len() {for r in 0..2 {mask_error=mask_error.max(worst(blend.masks()[r].level(level),expected_masks[r].level(level)));}
        for i in 0..sizes[level].pixels() {
            let expected=expected_masks[0].level(level)[i]+expected_masks[1].level(level)[i];
            assert!((blend.coverage().level(level)[i]-expected).abs()<1e-6 && blend.coverage().level(level)[i]<=1.0+1e-6);
        }
    }assert!(mask_error<1e-6);
    let other=pyramids(&frames[1]);let mixed=blend.mixed_coefficients(&baseline);let mut expected=resolved.clone();
    let mut coefficient_error=0.0f32;let mut changed_coefficients=0;
    for c in 0..4 {for level in 0..sizes.len()-1 {for i in 0..sizes[level].pixels() {
        let a=expected_masks[0].level(level)[i];let b=expected_masks[1].level(level)[i];
        let value=(1.0-(a+b))*resolved[c].level(level)[i]+a*source[c].level(level)[i]+b*other[c].level(level)[i];
        expected[c].level_mut(level)[i]=value;
        coefficient_error=coefficient_error.max((mixed[c].level(level)[i]-value).abs());
        changed_coefficients+=usize::from(value.to_bits()!=resolved[c].level(level)[i].to_bits());
    }}assert_eq!(hash(mixed[c].level(3)),hash(resolved[c].level(3)));}
    assert!(coefficient_error<=0.003 && changed_coefficients>100);
    let (expected_out,_) =collapse_hull(&expected,&frames);let actual=blend.finish(&baseline,&mut Workspace::new(&sizes));
    let output_error=actual.iter().zip(&expected_out).map(|(a,b)|worst(a,b)).fold(0.0,f32::max);assert!(output_error<=0.003);
    let mut late=DonorBlend::new(&sizes,4,&masks);late.add_source(&[0,1],&frames[2]);let late_out=late.finish(&baseline,&mut Workspace::new(&sizes));
    let placebo_changes=actual.iter().zip(&late_out).flat_map(|(a,b)|a.iter().zip(b)).filter(|(a,b)|a.to_bits()!=b.to_bits()).count();assert!(placebo_changes>100);
    for arm in [&actual,&late_out] {for c in 0..4 {for i in 0..W*H {
        let lo=frames.iter().map(|f|f[c][i]).fold(f32::INFINITY,f32::min);let hi=frames.iter().map(|f|f[c][i]).fold(f32::NEG_INFINITY,f32::max);
        assert!(arm[c][i].is_finite() && arm[c][i]>=lo && arm[c][i]<=hi);
    }}}
    for bad in [f32::NAN,-0.01,1.01] {refused(||{DonorBlend::new(&sizes,4,&[vec![bad;W*H]]);});}
    refused(||{DonorBlend::new(&sizes,4,&[vec![0.0;W*H-1]]);});
    refused(||{let missing=DonorBlend::new(&sizes,4,&[vec![1.0;W*H]]);missing.finish(&baseline,&mut Workspace::new(&sizes));});
    refused(||{let mut bad=DonorBlend::new(&sizes,4,&[vec![1.0;W*H]]);bad.add_source(&[0],&vec![vec![0.0;W*H-1];4]);});
    refused(||{let mut bad=DonorBlend::new(&sizes,4,&[vec![1.0;W*H]]);let mut f=frames[0].clone();f[2][5]=f32::NAN;bad.add_source(&[0],&f);});
    assert_eq!(raw,raw_before);assert_eq!(hashes(&frames),before);exact(&baseline.finish(&mut Workspace::new(&sizes)),&baseline_out);
    eprintln!("DONOR_CONSUMER {}",json!({"off_zero_finish_bit_exact":true,"baseline_observer_after_bit_exact":true,"terminal_base_bit_exact":true,
        "independent_three_source_mean_base_bit_exact":true,"independent_mean_base_max_error_dn":mean_base_error,
        "ones_output_max_error_dn":ones_error,"ones_pre_hull_excursions":excursions,"ones_changes_baseline":changed_baseline,"ones_differs_from_direct_donor":changed_donor,
        "mask_max_error":mask_error,"raw_overlap_by_level":overlap,"normalized_by_level":normalized,"coefficient_max_error_dn":coefficient_error,
        "output_max_error_dn":output_error,"same_mask_late_placebo_changed_samples":placebo_changes,"source_hashes_before_after":before,
        "scope":"Mechanical actual-consumer controls; generated u16 sources, no photographic quality claim"}));
}
