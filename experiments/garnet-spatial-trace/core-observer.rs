// Read-only finish census. Included as pyramid::garnet_spatial_trace under
// native-correction-variance; inactive unless the exact explicit env is set.
// No serde dependency, image changes, source/gather pass or alternate merge.
use super::BandMerge;

pub const ENV: &str = "STREHL_GARNET_NUMERATOR_CENSUS";
const ISLAND: [usize; 4] = [2334, 929, 192, 192];

pub struct Observer {
    before: Vec<Option<Vec<f32>>>,
    completed: usize,
    expected: usize,
    island: Option<[usize; 4]>,
}

fn finite_json(v: f32) -> String {
    if v.is_finite() { v.to_string() } else { "null".into() }
}
fn kind(v: f32) -> u8 {
    if v.is_nan() { 3 } else if v == f32::INFINITY { 1 }
    else if v == f32::NEG_INFINITY { 2 } else { 0 }
}
fn scan(values: &[f32], width: usize) -> String {
    let (mut nan,mut positive,mut negative,mut zero) = (0usize,0usize,0usize,0usize);
    let (mut low,mut high) = (f32::INFINITY,f32::NEG_INFINITY);
    let mut first = Vec::new();
    for (i,&v) in values.iter().enumerate() {
        match kind(v) {
            0 => { low=low.min(v);high=high.max(v);zero+=usize::from(v==0.0); }
            1 => positive+=1,
            2 => negative+=1,
            _ => nan+=1,
        }
        if !v.is_finite() && first.len()<64 {
            first.push(format!("[{}, {}, {}]",i%width,i/width,v.to_bits()));
        }
    }
    format!("{{\"samples\":{},\"nan\":{},\"positive_infinity\":{},\"negative_infinity\":{},\"zero\":{},\"finite_min\":{},\"finite_max\":{},\"first_nonfinite_xy_bits\":[{}],\"first_limit\":64}}",
        values.len(),nan,positive,negative,zero,finite_json(low),finite_json(high),first.join(","))
}

// Exact row-major run lengths; [start,length,kind], kind0 omitted.
// kind1=+inf, kind2=-inf, kind3=NaN for the nonfinite masks. Binary masks use1.
fn runs(values: impl IntoIterator<Item=u8>) -> String {
    let mut result=Vec::new(); let mut current=0u8; let mut start=0usize; let mut count=0usize;
    for (i,value) in values.into_iter().enumerate() {
        if value!=current {
            if current!=0 {result.push(format!("[{start},{count},{current}]"));}
            current=value;start=i;count=0;
        }
        count+=1;
    }
    if current!=0 {result.push(format!("[{start},{count},{current}]"));}
    format!("[{}]",result.join(","))
}
fn crop(values:&[f32],width:usize,rect:[usize;4])->Vec<f32> {
    let [x,y,w,h]=rect;let mut output=Vec::with_capacity(w*h);
    for row in y..y+h {output.extend_from_slice(&values[row*width+x..row*width+x+w]);}
    output
}
fn rect_json(rect:[usize;4])->String {format!("[{},{},{},{}]",rect[0],rect[1],rect[2],rect[3])}
fn emit(stage:&str,plane:usize,band:Option<usize>,width:usize,values:&[f32],extra:&str) {
    eprintln!("GARNET_NUMERATOR_CENSUS {{\"stage\":\"{}\",\"plane\":{},\"band\":{},\"width\":{},\"scan\":{}{} }}",
        stage,plane,band.map(|x|x.to_string()).unwrap_or_else(||"null".into()),width,scan(values,width),extra);
}

/// Root keeps normal canonical chunks and calls this only at actual finish.
/// No state crosses finish calls; each record names the real merged frame count.
pub fn start(merge:&BandMerge)->Option<Observer> {
    match std::env::var(ENV) {
        Err(std::env::VarError::NotPresent)=>return None,
        Ok(v) if v=="1"=>{},
        _=>panic!("{ENV} must be absent or exactly1"),
    }
    assert_eq!(merge.planes,4,"garnet census expects all four CFA planes");
    let sizes=merge.sizes.iter().map(|s|format!("[{},{}]",s.width,s.height)).collect::<Vec<_>>().join(",");
    let island=([merge.sizes[0].width,merge.sizes[0].height]==[3262,2174]
        &&merge.frames==183).then_some(ISLAND);
    eprintln!("GARNET_NUMERATOR_CENSUS {{\"stage\":\"begin\",\"frames\":{},\"planes\":{},\"sizes\":[{}],\"admission\":\"{:?}\",\"select\":\"{:?}\",\"hull\":\"{:?}\",\"island_output_quad_xywh\":{},\"mask_encoding\":\"row-major RLE [start,length,kind]; omitted kind0; nonfinite kind1 +inf,2 -inf,3 NaN\"}}",
        merge.frames,merge.planes,sizes,merge.cfg.admission,merge.cfg.select,merge.cfg.hull,
        island.map(rect_json).unwrap_or_else(||"null".into()));
    Some(Observer{before:(0..merge.planes).map(|_|None).collect(),completed:0,expected:merge.planes,island})
}

/// Called after actual SoftPower/mean-fallback resolution, before collapse.
/// Snapshot the actual accumulators; never recompute weights or a coefficient.
pub fn resolved(observer:Option<&mut Observer>,merge:&BandMerge,c:usize,k:usize,out:&[f32]) {
    let Some(observer)=observer else{return};
    let size=merge.sizes[k];let index=k*merge.planes+c;
    emit("numerator",c,Some(k),size.width,&merge.num[index],"");
    if c==0 {
        let fallback=merge.den[k].iter().filter(|&&v|v<=0.0).count();
        let extra=format!(",\"fallback_coefficients\":{fallback}");
        emit("denominator",c,Some(k),size.width,&merge.den[k],&extra);
    }
    emit("unweighted_sum",c,Some(k),size.width,&merge.usum[index],"");
    let extra=if let Some([x,y,w,h])=observer.island {
        let stride=1usize<<k;
        let rect=[x/stride,y/stride,(x+w).div_ceil(stride)-x/stride,(y+h).div_ceil(stride)-y/stride];
        let part=crop(out,size.width,rect);let den=crop(&merge.den[k],size.width,rect);
        format!(",\"island_nominal_grid_rect\":{},\"island_nonfinite_runs\":{},\"island_fallback_runs\":{},\"grid_note\":\"nominal decimated coordinates, not full filter support\"",
            rect_json(rect),runs(part.into_iter().map(kind)),runs(den.into_iter().map(|v|u8::from(v<=0.0))))
    }else{String::new()};
    emit("resolved",c,Some(k),size.width,out,&extra);
}

/// Called on actual reconstructed full-context values immediately before the
/// existing final InputRange clamp. Store ONLY the frozen192x192 ROI per plane.
pub fn pre_hull(observer:Option<&mut Observer>,merge:&BandMerge,c:usize,image:&[f32]) {
    let Some(observer)=observer else{return};
    let extra=if let Some(rect)=observer.island {
        let part=crop(image,merge.sizes[0].width,rect);
        let extra=format!(",\"island_output_quad_xywh\":{},\"island_nonfinite_runs\":{}",
            rect_json(rect),runs(part.iter().copied().map(kind)));
        assert!(observer.before[c].replace(part).is_none(),"duplicate pre-hull plane");
        extra
    }else{String::new()};
    emit("pre_hull",c,None,merge.sizes[0].width,image,&extra);
}

/// Called on the very same actual image after the final bound. Exact masks
/// allow matching the former infinities to finite lower/upper-bound rectangles.
pub fn post_hull(observer:Option<&mut Observer>,merge:&BandMerge,c:usize,image:&[f32]) {
    let Some(observer)=observer else{return};
    let extra=if let Some(rect)=observer.island {
        let after=crop(image,merge.sizes[0].width,rect);
        let before=observer.before[c].take().expect("post-hull without pre-hull");
        let mut extra=format!(",\"island_output_quad_xywh\":{},\"island_nonfinite_runs\":{},\"island_changed_runs\":{}",
            rect_json(rect),runs(after.iter().copied().map(kind)),
            runs(before.iter().zip(&after).map(|(a,b)|u8::from(a.to_bits()!=b.to_bits()))));
        if merge.cfg.hull.bounds() {
            let low=crop(&merge.lo[c],merge.sizes[0].width,rect);
            let high=crop(&merge.hi[c],merge.sizes[0].width,rect);
            extra.push_str(&format!(",\"previous_nonfinite_now_equal_lower_runs\":{},\"previous_nonfinite_now_equal_upper_runs\":{}",
                runs(before.iter().zip(&after).zip(&low).map(|((a,b),l)|u8::from(!a.is_finite()&&b.to_bits()==l.to_bits()))),
                runs(before.iter().zip(&after).zip(&high).map(|((a,b),h)|u8::from(!a.is_finite()&&b.to_bits()==h.to_bits())))));
        }
        extra
    }else{String::new()};
    emit("post_hull",c,None,merge.sizes[0].width,image,&extra);
    observer.completed+=1;
}
impl Drop for Observer {
    fn drop(&mut self) {
        eprintln!("GARNET_NUMERATOR_CENSUS {{\"stage\":\"end\",\"completed_planes\":{},\"expected_planes\":{},\"complete\":{}}}",
            self.completed,self.expected,self.completed==self.expected&&self.before.iter().all(Option::is_none));
    }
}
