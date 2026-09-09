// Test-only original-CFA consumer; root executes, author does not.
use super::*;
use super::super::*;
use strehl_core::pyramid::correction_variance_diagnostic as kernel;
use strehl_core::warpmap::Provenance as WarpProvenance;
use sha2::{Digest, Sha256};

struct Source(Frame);
impl PyramidFrameSource for Source {
    fn len(&self) -> usize { 1 }
    fn decode(&self, index: usize) -> Result<Frame> {
        assert_eq!(index, 0);
        Ok(self.0.clone())
    }
}
fn fixture() -> Frame { super::m194c_independent_tests::green_fixture(274,190,1,1) }
fn domain(frame: &Frame) -> PyramidDomain {
    PyramidDomain::cropped(frame.geometry(), super::m194c_independent_tests::variance_crop()).unwrap()
}
fn warpmap(frame: &Frame, t: Similarity) -> WarpMap {
    let path = frame.path.to_string_lossy();
    WarpMap::new(WarpProvenance {
        stack: StackIdentity::from_entries("correction variance original-CFA fixture", &[(path,frame.allocated_bytes() as u64)]),
        strategy: "fixed existing M194c warp".into(), heldout_px: None, cycle_floor_px: None,
        reference: 0, note: "test-only transfer; no alignment truth claim".into(),
    }, frame.geometry(), Resampler::CatmullRom, vec![FrameWarp::Placed(t)])
}
fn prepare(frame: &Frame, t: Similarity, defect: Option<&crate::stack::DefectPlan>, measure: bool)
    -> (Vec<Vec<f32>>, Vec<f32>, Vec<f32>) {
    let domain = domain(frame);
    let n = domain.analysis().pixels();
    let mut planes = vec![vec![0.0; n]; 4];
    let mut luma = vec![0.0; n];
    let mut probe = Probe::new(domain,3);
    let tally = crate::stack::DefectTally::default();
    assert!(load_frame(&Source(frame.clone()),0,domain,frame.levels,Some(&warpmap(frame,t)),
        defect.map(|p| (p,&tally)),&mut WarpScratch::new(domain.full),measure.then_some(&mut probe),
        &mut planes,&mut luma).unwrap());
    (planes,luma,probe.last().to_vec())
}
fn hash(values: &[f32]) -> String {
    let mut digest = Sha256::new();
    for value in values { digest.update(value.to_bits().to_le_bytes()); }
    digest.finalize().iter().map(|v| format!("{v:02x}")).collect()
}
#[test]
#[ignore = "root-owned bounded source-transfer diagnostic"]
fn correction_variance_smoke() {
    let frame = fixture();
    assert!(!frame.path.exists());
    let sizes = level_sizes(domain(&frame).analysis().width,domain(&frame).analysis().height,3);
    for t in [Similarity::IDENTITY,super::m194c_independent_tests::variance_warp()] {
        let (planes,luma,beta) = prepare(&frame,t,None,true);
        assert_eq!(planes.len(),4);
        assert!(beta.len() >= 2 && beta[..2].iter().all(|v| v.is_finite()));
        let bands = kernel::laplacian(&luma,&sizes);
        let energy = kernel::energy(&bands[0],sizes[0]);
        assert_eq!(energy.len(),luma.len());
        println!("CORRECTION_VARIANCE_SMOKE luma={} energy={} beta={:?}",hash(&luma),hash(&energy),beta);
    }
}
