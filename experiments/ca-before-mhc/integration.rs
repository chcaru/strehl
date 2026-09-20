// Child of native_gpu_integration. Explicit test scope follows synchronous
// BandWorker actual and probe calls without changing process environment.
use super::*;
use anyhow::ensure;
use strehl_native_gpu_gather::ca_before_mhc::Order;
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(crate) enum Mode { Current, Before, StagedAfter }
fn parsed(value:Option<&str>)->Result<Mode>{match value{
    None|Some("off")=>Ok(Mode::Current),Some("before")=>Ok(Mode::Before),Some("staged-after")=>Ok(Mode::StagedAfter),
    other=>bail!("STREHL_CA_BEFORE_MHC expected off, before, staged-after; got {other:?}")}}
#[cfg(test)]
thread_local!{static EXPLICIT:std::cell::Cell<Option<(Mode,[Similarity;3])>>=const{std::cell::Cell::new(None)};}
pub(crate) fn mode()->Result<Mode>{
    #[cfg(test)] if let Some((mode,_))=EXPLICIT.with(|v|v.get()){return Ok(mode);}
    match std::env::var("STREHL_CA_BEFORE_MHC"){
        Ok(v)=>parsed(Some(&v)),Err(std::env::VarError::NotPresent)=>parsed(None),Err(e)=>bail!("CA mode: {e}")}
}
pub(super) fn validate(enabled:bool)->Result<()>{
    if mode()?!=Mode::Current {
        #[cfg(not(feature="native-direct-planes"))]
        bail!("CA stage requires native-direct-planes build feature");
        #[cfg(feature="native-direct-planes")]
        ensure!(enabled && fullres_gather_enabled() && direct_plane_mode()?==DirectPlaneMode::Rounded,
            "CA stage requires GPU fullres rounded direct planes");
        ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none(),"CA stage excludes local placement");
        ensure!(!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional")),"CA stage requires Malvar");
    }Ok(())
}
pub(super) fn inputs(t:Similarity,ca:Option<&strehl_core::optics::OpticalProfile>)->Result<(Mode,[Similarity;3],[Similarity;3])>{
    #[cfg(test)] if let Some((mode,ca_pulls))=EXPLICIT.with(|v|v.get()){
        let pulls=ca_pulls.map(|c|if c==Similarity::IDENTITY{t}else{Similarity{a:c.a*t.a,b:c.a*t.b+c.b}});
        return Ok((mode,ca_pulls,pulls));
    }
    let channels=[(0,0),(1,0),(1,1)].map(|(x,y)|strehl_core::optics::cfa_site_channel(x,y));
    Ok((mode()?,channels.map(|c|strehl_core::optics::OpticalProfile::compose(ca,c,Similarity::IDENTITY)),
        channels.map(|c|strehl_core::optics::OpticalProfile::compose(ca,c,t))))
}
pub(super) fn execute(gpu:&mut GpuGather,input:&Input<'_>,common:Similarity,mode:Mode,ca:[Similarity;3])->Result<Output>{
    match mode{Mode::Current=>gpu.run(input),Mode::Before=>gpu.run_ca_stage(input,common,ca,Order::Before),
        Mode::StagedAfter=>gpu.run_ca_stage(input,common,ca,Order::StagedAfter)}.map_err(anyhow::Error::msg)
}
pub(super) fn require_coverage(output:&Output,crop:CropRect,offsets:&[(usize,usize)])->Result<()>{
    // Also used in generated Current controls so comparison never scores black fill.
    let mut unsupported=0usize;
    for &(dx,dy) in offsets {for y in 0..crop.height{let row=(2*(crop.y+y)+dy)*(output.width/2)+crop.x;
        for x in 0..crop.width{unsupported+=usize::from((output.coverage[row+x]&(1<<dx))==0);}}}
    ensure!(unsupported==0,"CA stage crop contains {unsupported} unsupported consumed sites");Ok(())
}
#[cfg(test)]
pub(crate) fn with_explicit<T>(mode:Mode,pulls:[Similarity;3],f:impl FnOnce()->Result<T>)->Result<T>{
    ensure!(pulls[1]==Similarity::IDENTITY && pulls.iter().all(|t|[t.a.re,t.a.im,t.b.re,t.b.im].iter().all(|v|v.is_finite())),"invalid explicit CA pull");
    ensure!(EXPLICIT.with(|v|v.get().is_none()),"nested explicit CA scope");
    struct Clear;impl Drop for Clear{fn drop(&mut self){EXPLICIT.with(|v|v.set(None));}}
    EXPLICIT.with(|v|v.set(Some((mode,pulls))));let _clear=Clear;f()
}
#[cfg(test)]
pub(super) fn explicit()->bool{EXPLICIT.with(|v|v.get().is_some())}
