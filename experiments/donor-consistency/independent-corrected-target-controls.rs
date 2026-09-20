use super::*;
use super::super::{fixed_masks_for_target,target_segments,target_from_setting};

#[test]
fn independent_corrected_target_geometry_and_scope() {
    let old=[([2624.0f32,2906.0],[2602.0,2945.0]),
        ([3080.0,2150.0],[3102.0,2203.0]),([3240.0,2070.0],[3240.0,2070.0])];
    let revised=[old[0],([3080.0,2150.0],[3080.0,2212.0]),old[2]];
    assert_eq!(target_segments(false),old);assert_eq!(target_segments(true),revised);
    assert!(!target_from_setting(None,false).unwrap());assert!(!target_from_setting(None,true).unwrap());
    assert!(target_from_setting(Some("corrected-dark-tail"),true).unwrap());
    assert!(target_from_setting(Some("corrected-dark-tail"),false).is_err());
    for bad in ["","off","0","1","corrected","corrected-dark-tail ","CORRECTED-DARK-TAIL"] {
        assert!(target_from_setting(Some(bad),true).is_err());
        assert!(target_from_setting(Some(bad),false).is_err());
    }
    let mut error=0.0f64;let mut changed_dark=0;let mut phase_changed=0;let mut unchanged_active=[0usize;2];
    for origin in [[2561isize,2853isize],[3011,2097],[3199,2017]] {
        let wrapper=fixed_masks(W,H,origin);let explicit=fixed_masks_for_target(W,H,origin,false);
        for r in 0..3 {assert_eq!(hash(&wrapper[r]),hash(&explicit[r]));}
        let first=fixed_masks_for_target(W,H,origin,true);
        for phase in 0..2 {
            let offset=[origin[0]+phase,origin[1]+phase];
            let legacy=fixed_masks_for_target(W,H,offset,false);
            let actual=fixed_masks_for_target(W,H,offset,true);
            for (slot,r) in [0usize,2].into_iter().enumerate() {
                assert_eq!(hash(&legacy[r]),hash(&actual[r]));
                unchanged_active[slot]+=actual[r].iter().filter(|&&v|v>0.0).count();
            }
            for r in 0..3 {for y in 0..H {for x in 0..W {
                let i=y*W+x;let (a,b)=revised[r];
                let expected=analytic_capsule(offset[0] as f64+2.0*x as f64+0.5,
                    offset[1] as f64+2.0*y as f64+0.5,a.map(f64::from),b.map(f64::from));
                error=error.max((f64::from(actual[r][i])-expected).abs());
                if r==1 {changed_dark+=usize::from(actual[r][i].to_bits()!=legacy[r][i].to_bits());}
                if phase==1 {phase_changed+=usize::from(actual[r][i].to_bits()!=first[r][i].to_bits());}
            }}}
        }
    }
    assert!(error<0.0001 && changed_dark>100 && phase_changed>100);
    assert!(unchanged_active.iter().all(|&n|n>100));
    let membership=|x:isize,y:isize,corrected:bool|{
        fixed_masks_for_target(1,1,[2*(x/2),2*(y/2)],corrected)[1][0]
    };
    let old_tail=membership(3080,2212,false);let new_tail=membership(3080,2212,true);
    let old_fan=membership(3102,2203,false);let new_fan=membership(3102,2203,true);
    for corrected in [false,true] {assert_eq!(membership(3080,2150,corrected),1.0);}
    assert!((old_tail-0.010998f32).abs()<0.0001);
    let independently_old=analytic_capsule(3080.5,2212.5,[3080.0,2150.0],[3102.0,2203.0]);
    assert!((f64::from(old_tail)-independently_old).abs()<0.0001);
    assert_eq!(new_tail,1.0);assert_eq!(old_fan,1.0);assert_eq!(new_fan,0.09228515625f32);
    eprintln!("DONOR_TARGET {}",json!({"status":"PASS","mask_analytic_max_error":error,
        "changed_dark_samples":changed_dark,"native_phase_changed_samples":phase_changed,
        "unchanged_facet_structure_active_samples":unchanged_active,
        "old_tail_membership":old_tail,"corrected_tail_membership":new_tail,
        "old_frozen_fan_membership":old_fan,"corrected_frozen_fan_membership":new_fan,
        "original_wrapper_exact":true,"other_two_masks_exact":true,"core_membership_exact":true,
        "setting_refusals_checked":true,
        "scope":"Post-failure corrected feature-address geometry; no photographic success claim"}));
}
