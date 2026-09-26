// Tiny pre-gathered-plane necessary screen. No RAW, warp, MHC or output solver.
use anyhow::{ensure,Result};
use strehl_core::pyramid::{level_sizes,AdmissionMode,BandMerge,BaseBand,Fallback,
    FrameWorkspace,Hull,LevelSize,MergeConfig,Pyramid,SelectMode,Workspace,
    rb_own_guide_diagnostic as canonical,donor_consistency_diagnostic as donor,
    fine_support_candidate};
use crate::operator::{Accumulator,Gradient,forward};

pub struct Comparison {
    pub sizes:Vec<LevelSize>,
    /// Both layouts: channel, level INCLUDING the unchanged terminal mean.
    pub baseline:Vec<Vec<Gradient>>,
    pub candidate:Vec<Vec<Gradient>>,
    /// Actual supplied weight sums at every AC level/site; zero means fallback.
    pub denominator:Vec<Vec<f32>>,
    pub canonical_coefficients:Vec<Pyramid>,
    pub terminal_unchanged:bool,
    pub source_count:usize,
}

pub fn compare(width:usize,height:usize,planes_by_frame:&[Vec<Vec<f32>>],
    guides:&[Vec<f32>],variance:&[Vec<f32>],cfg:MergeConfig)->Result<Comparison> {
    let n=width.checked_mul(height).ok_or_else(||anyhow::anyhow!("extent overflow"))?;
    let count=planes_by_frame.len();
    ensure!(width>0&&height>0&&width<=512&&height<=512&&(1..=70).contains(&count)
        &&guides.len()==count&&variance.len()==count,"bounded generated inputs required");
    ensure!(cfg.select==SelectMode::SoftPower&&cfg.admission==AdmissionMode::HardFloor
        &&cfg.base==BaseBand::Mean&&cfg.fallback==Fallback::Mean&&cfg.hull==Hull::InputRange
        &&cfg.mean_coarse==0&&cfg.significance_scale==0.,"held canonical modes required");
    ensure!(fine_support_candidate::environment_mode()==fine_support_candidate::Mode::Off,"competing fine-support mode must be off");
    let sizes=level_sizes(width,height,cfg.bands);ensure!(sizes.len()>=2,"actual AC levels required");
    let mut merge=BandMerge::new(width,height,4,cfg);let mut frame_ws=FrameWorkspace::new(&sizes,4);
    let mut analysis_ws=Workspace::new(&sizes);
    let mut coefficients=(0..4).map(|_|Pyramid::zeros(&sizes)).collect::<Vec<_>>();
    let mut gradient_sum=Accumulator::new(&sizes,count)?;
    for i in 0..count {
        let planes=&planes_by_frame[i];let guide=&guides[i];let var=&variance[i];
        ensure!(planes.len()==4&&planes.iter().all(|p|p.len()==n&&p.iter().all(|v|v.is_finite()))
            &&guide.len()==n&&guide.iter().all(|v|v.is_finite())
            &&var.len()==n&&var.iter().all(|v|v.is_finite()&&*v>=0.),"invalid injected source/guide/variance");
        frame_ws.next_frame();
        // None beta is the actual core's white-noise route, appropriate only to
        // this generated pre-gather plane scope. No variance estimate is made.
        merge.add_frame(&planes.iter().map(Vec::as_slice).collect::<Vec<_>>(),guide,var,&mut frame_ws);
        let fields=canonical::canonical_fields(&merge,&frame_ws,None);
        for c in 0..4 {coefficients[c].build(&planes[c],&mut analysis_ws);}
        gradient_sum.add(i,&coefficients,&fields.weights)?;
    }
    let canonical_coefficients=donor::resolved_coefficients(&merge);
    let baseline=canonical_coefficients.iter().map(|p|sizes.iter().enumerate()
        .map(|(k,s)|forward(p.level(k),s)).collect::<Result<Vec<_>>>()).collect::<Result<Vec<_>>>()?;
    let target=gradient_sum.finish()?;let mut candidate=target.gradients;
    let terminal=sizes.len()-1;
    for c in 0..4 {candidate[c].push(baseline[c][terminal].clone());}
    // Terminal gradient is copied bit-for-bit; it is not a new gradient target.
    let terminal_unchanged=(0..4).all(|c|baseline[c][terminal].dx.iter().zip(&candidate[c][terminal].dx)
        .chain(baseline[c][terminal].dy.iter().zip(&candidate[c][terminal].dy))
        .all(|(a,b)|a.to_bits()==b.to_bits()));
    ensure!(terminal_unchanged,"terminal target changed");
    Ok(Comparison{sizes,baseline,candidate,denominator:target.denominator,
        canonical_coefficients,terminal_unchanged,source_count:target.source_count})
}
