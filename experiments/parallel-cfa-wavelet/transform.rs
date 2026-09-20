// Parallel disjoint-output execution of the commissioned rectangular transform.
use rayon::prelude::*;
// Six-tap arithmetic/order from complete-cfa-wavelet, (c)2019 Petteri Aimonen;
// full upstream notice/pins remain in complex-wavelet-merge/licence.txt.
#[derive(Clone, Debug)]
pub(crate) struct BoundaryPlan {
    pub input_width:usize, pub input_height:usize,
    pub padded_width:usize, pub padded_height:usize, pub left:usize, pub top:usize,
    pub x_indices:Vec<usize>, pub y_indices:Vec<usize>,
}
pub(crate) fn reflect_index(index:isize,length:usize)->usize {
    assert!(length>0);let u=index.rem_euclid((2*length) as isize) as usize;
    if u<length {u} else {2*length-1-u}
}
impl BoundaryPlan {
    pub(crate) fn new(w:usize,h:usize)->Result<Self> {
        ensure!(w>0 && h>0 && w<=512 && h<=512,"bounded positive boundary dimensions");
        Ok(Self::extent(w,h))
    }
    pub(crate) fn full_vitamin_c()->Self {Self::extent(3460,2306)}
    fn extent(w:usize,h:usize)->Self {
        let (pw,ph)=(w.next_power_of_two(),h.next_power_of_two());
        let (left,top)=((pw-w)/2,(ph-h)/2);
        Self{input_width:w,input_height:h,padded_width:pw,padded_height:ph,left,top,
            x_indices:(0..pw).map(|x|reflect_index(x as isize-left as isize,w)).collect(),
            y_indices:(0..ph).map(|y|reflect_index(y as isize-top as isize,h)).collect()}
    }
    pub(crate) fn depth(&self)->usize {self.padded_width.max(self.padded_height).ilog2() as usize}
}
pub(crate) fn extend_plane(input:&[f32],p:&BoundaryPlan)->Result<Vec<f32>> {
    ensure!(input.len()==p.input_width*p.input_height && input.iter().all(|v|v.is_finite()),"invalid boundary input");
    Ok(p.y_indices.iter().flat_map(|&y|p.x_indices.iter().map(move|&x|input[y*p.input_width+x])).collect())
}
pub(crate) fn extend_four(input:&[Vec<f32>],p:&BoundaryPlan)->Result<Vec<Vec<f32>>> {
    ensure!(input.len()==4,"four CFA planes required");input.iter().map(|v|extend_plane(v,p)).collect()
}
pub(crate) fn crop_four(input:&[Vec<f32>],p:&BoundaryPlan)->Result<Vec<Vec<f32>>> {
    ensure!(input.len()==4 && input.iter().all(|v|v.len()==p.padded_width*p.padded_height
        && v.iter().all(|x|x.is_finite())),"invalid extended CFA planes");
    Ok(input.iter().map(|v|(p.top..p.top+p.input_height).flat_map(|y|
        v[y*p.padded_width+p.left..y*p.padded_width+p.left+p.input_width].iter().copied()).collect()).collect())
}
fn dimensions(w:usize,h:usize,n:usize)->Result<()> {
    dimensions_scoped(w,h,n,false)
}
fn dimensions_scoped(w:usize,h:usize,n:usize,full:bool)->Result<()> {
    ensure!(w>0 && h>0 && w.is_power_of_two() && h.is_power_of_two()
        && w.checked_mul(h)==Some(n) && n<=if full{4096*4096}else{512*512},"bounded dyadic rectangle required");Ok(())
}
fn location(line:usize,pos:usize,w:usize,vertical:bool)->usize {if vertical {pos*w+line} else {line*w+pos}}
fn analysis_1d(src:&[Complex],w:usize,h:usize,vertical:bool)->Vec<Complex> {
    let length=if vertical {h}else{w};
    if length==1{return src.to_vec();}
    let (low,high)=(analysis_taps(false),analysis_taps(true));
    let calculate=|line:usize,y:usize|{
        let (mut lo,mut hi)=(Complex::default(),Complex::default());
        for j in 0..6 {
            let pos=(y as isize+j as isize-3).rem_euclid(length as isize) as usize;
            let value=src[location(line,pos,w,vertical)];
            lo.re+=value.re*low[j].re-value.im*low[j].im;
            lo.im+=value.im*low[j].re+value.re*low[j].im;
            hi.re+=value.re*high[j].re-value.im*high[j].im;
            hi.im+=value.im*high[j].re+value.re*high[j].im;
        }(lo,hi)
    };
    let mut dst=vec![Complex::default();src.len()];
    if vertical {
        let (lo,hi)=dst.split_at_mut(w*h/2);
        lo.par_chunks_mut(w).zip(hi.par_chunks_mut(w)).enumerate().for_each(|(pair,(lo,hi))|{
            for x in 0..w{let(a,b)=calculate(x,2*pair);lo[x]=a;hi[x]=b;}
        });
    }else{
        dst.par_chunks_mut(w).enumerate().for_each(|(line,row)|{
            for y in (0..w).step_by(2){let(a,b)=calculate(line,y);row[y/2]=a;row[y/2+w/2]=b;}
        });
    }dst
}
fn synthesis_1d(src:&[Complex],w:usize,h:usize,vertical:bool)->Vec<Complex> {
    let length=if vertical {h}else{w};
    if length==1{return src.to_vec();}
    let (low,high)=(analysis_taps(false),analysis_taps(true));
    let calculate=|line:usize,y:usize|{
        let mut value=Complex::default();
        for j in ((y+3)%2..6).step_by(2) {
            let pos=((y as isize-j as isize+3)/2).rem_euclid((length/2) as isize) as usize;
            let lo=src[location(line,pos,w,vertical)];let hi=src[location(line,pos+length/2,w,vertical)];
            value.re+=lo.re*low[j].re+hi.re*high[j].re;
            value.re+=lo.im*low[j].im+hi.im*high[j].im;
            value.im+=lo.im*low[j].re+hi.im*high[j].re;
            value.im-=lo.re*low[j].im+hi.re*high[j].im;
        }value
    };
    let mut dst=vec![Complex::default();src.len()];
    dst.par_chunks_mut(w).enumerate().for_each(|(y,row)|{
        for x in 0..w{row[x]=if vertical{calculate(x,y)}else{calculate(y,x)};}
    });dst
}
pub(crate) fn transform_one(input:&[Complex],w:usize,h:usize)->Result<Vec<Complex>> {
    transform_one_scoped(input,w,h,false)
}
fn transform_one_scoped(input:&[Complex],w:usize,h:usize,full:bool)->Result<Vec<Complex>> {
    dimensions_scoped(w,h,input.len(),full)?;ensure!(input.iter().all(|v|v.re.is_finite() && v.im.is_finite()),"nonfinite transform input");
    Ok(analysis_1d(&analysis_1d(input,w,h,true),w,h,false))
}
pub(crate) fn inverse_one(input:&[Complex],w:usize,h:usize)->Result<Vec<Complex>> {
    inverse_one_scoped(input,w,h,false)
}
fn inverse_one_scoped(input:&[Complex],w:usize,h:usize,full:bool)->Result<Vec<Complex>> {
    dimensions_scoped(w,h,input.len(),full)?;ensure!(input.iter().all(|v|v.re.is_finite() && v.im.is_finite()),"nonfinite inverse input");
    Ok(synthesis_1d(&synthesis_1d(input,w,h,true),w,h,false))
}
pub(crate) fn level_rectangles(w:usize,h:usize)->Result<Vec<[usize;2]>> {
    level_rectangles_scoped(w,h,false)
}
fn level_rectangles_scoped(w:usize,h:usize,full:bool)->Result<Vec<[usize;2]>> {
    dimensions_scoped(w,h,w*h,full)?;let(mut cw,mut ch)=(w,h);let mut out=Vec::new();
    while cw>1 || ch>1 {out.push([cw,ch]);cw=(cw/2).max(1);ch=(ch/2).max(1);}Ok(out)
}
fn transform_all(input:&[Complex],w:usize,h:usize,inverse:bool,full:bool)->Result<Vec<Complex>> {
    dimensions_scoped(w,h,input.len(),full)?;let mut sizes=level_rectangles_scoped(w,h,full)?;
    if inverse{sizes.reverse();}let mut out=input.to_vec();
    for [cw,ch] in sizes {
        let rect=(0..ch).flat_map(|y|out[y*w..y*w+cw].iter().copied()).collect::<Vec<_>>();
        let inner=if inverse{inverse_one_scoped(&rect,cw,ch,full)?}else{transform_one_scoped(&rect,cw,ch,full)?};
        for y in 0..ch {out[y*w..y*w+cw].copy_from_slice(&inner[y*cw..(y+1)*cw]);}
    }
    ensure!(out.iter().all(|v|v.re.is_finite() && v.im.is_finite()),"nonfinite complete transform");Ok(out)
}
pub(crate) fn transform_complete(input:&[Complex],w:usize,h:usize)->Result<Vec<Complex>> {transform_all(input,w,h,false,false)}
pub(crate) fn forward_real(input:&[f32],w:usize,h:usize)->Result<Vec<Complex>> {
    transform_complete(&input.iter().map(|&re|Complex{re,im:0.0}).collect::<Vec<_>>(),w,h)
}
pub(crate) fn inverse_complete(input:&[Complex],w:usize,h:usize)->Result<Vec<Complex>> {transform_all(input,w,h,true,false)}
fn forward_real_scoped(input:&[f32],w:usize,h:usize,full:bool)->Result<Vec<Complex>> {
    transform_all(&input.iter().map(|&re|Complex{re,im:0.0}).collect::<Vec<_>>(),w,h,false,full)
}

#[derive(Clone,Debug)]
pub(crate) struct Subband {pub level:usize,pub direction:usize,pub width:usize,pub height:usize,pub positions:Vec<usize>}
pub(crate) fn subbands(w:usize,h:usize)->Result<Vec<Subband>> {
    subbands_scoped(w,h,false)
}
fn subbands_scoped(w:usize,h:usize,full:bool)->Result<Vec<Subband>> {
    let mut out=Vec::new();
    for (level,[cw,ch]) in level_rectangles_scoped(w,h,full)?.into_iter().enumerate() {
        let(bw,bh)=((cw/2).max(1),(ch/2).max(1));
        for (direction,bx,by) in [(0,1,0),(1,1,1),(2,0,1)] {
            if (bx==1 && cw==1) || (by==1 && ch==1){continue;}
            let positions=(0..bh).flat_map(|y|(0..bw).map(move|x|(by*bh+y)*w+bx*bw+x)).collect();
            out.push(Subband{level,direction,width:bw,height:bh,positions});
        }
    }Ok(out)
}
