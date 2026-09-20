// Fixed, generated-only scalar support. No frame/source election is implemented.
pub(crate) const BLOCK:usize=8;
pub(crate) const RADIUS:usize=32;
#[derive(Clone,Copy,Debug,PartialEq,Eq,serde::Serialize)]
pub(crate) enum Mode {Off,Affinity,AllAffinity}

#[derive(Clone,Debug,serde::Serialize)]
pub(crate) struct BlockGrid {
    pub width:usize,pub height:usize,pub cols:usize,pub rows:usize,
    pub rects:Vec<[usize;4]>,pub areas:Vec<usize>,
}
impl BlockGrid {
    pub(crate) fn new(width:usize,height:usize)->Result<Self> {
        ensure!(width>0 && height>0 && width<=512 && height<=512,"bounded positive block geometry required");
        let cols=width.div_ceil(BLOCK);let rows=height.div_ceil(BLOCK);
        let rects=(0..rows).flat_map(|by|(0..cols).map(move |bx| {
            let x=BLOCK*bx;let y=BLOCK*by;[x,y,BLOCK.min(width-x),BLOCK.min(height-y)]
        })).collect::<Vec<_>>();
        let areas=rects.iter().map(|r|r[2]*r[3]).collect();
        Ok(Self{width,height,cols,rows,rects,areas})
    }
}
fn grid_values(values:&[f32],grid:&BlockGrid,nonnegative:bool)->Result<()> {
    ensure!(values.len()==grid.width*grid.height && values.iter().all(|v|v.is_finite()
        && (!nonnegative || *v>=0.0)),"invalid block field shape/value");Ok(())
}
fn block_sums(values:&[f32],grid:&BlockGrid)->Vec<f32> {
    grid.rects.iter().map(|&[x,y,w,h]| {
        let mut sum=0.0f32;
        for yy in y..y+h {for xx in x..x+w {sum+=values[yy*grid.width+xx];}}
        sum
    }).collect()
}
pub(crate) fn block_means4(planes:&[Vec<f32>],grid:&BlockGrid)->Result<Vec<[f32;4]>> {
    ensure!(planes.len()==4,"four CFA planes required");
    let mut out=vec![[0.0;4];grid.rects.len()];
    for c in 0..4 {
        grid_values(&planes[c],grid,false)?;
        for ((v,sum),&area) in out.iter_mut().zip(block_sums(&planes[c],grid)).zip(&grid.areas) {
            v[c]=sum/area as f32;ensure!(v[c].is_finite(),"block mean overflow");
        }
    }Ok(out)
}

#[derive(Clone,Debug,serde::Serialize)]
pub(crate) struct Affinity {
    pub grid:BlockGrid,pub neighbors:Vec<Vec<(usize,f32)>>,pub source_count:usize,pub mode:Mode,
}
/// Exact consecutive four-plane block-DN differences; no temporal compression,
/// WB re-scaling, centering of differences, noise fit or cosine cutoff search.
pub(crate) fn build_affinity(grid:&BlockGrid,means:&[Vec<[f32;4]>],mode:Mode)->Result<Affinity> {
    let n=grid.rects.len();
    ensure!(!means.is_empty() && means.len()<=70 && means.iter().all(|f|f.len()==n
        && f.iter().flatten().all(|v|v.is_finite())),"bounded source/block descriptor shape/value");
    let differences=(1..means.len()).map(|k|(0..n).map(|p|
        std::array::from_fn::<_,4,_>(|c|means[k][p][c]-means[k-1][p][c]))
        .collect::<Vec<_>>()).collect::<Vec<_>>();
    ensure!(differences.iter().flatten().flatten().all(|v|v.is_finite()),"temporal difference overflow");
    let mut norms=vec![0.0f32;n];
    for d in &differences {for (norm,tuple) in norms.iter_mut().zip(d) {for v in tuple {*norm+=v*v;}}}
    ensure!(norms.iter().all(|v|v.is_finite()),"temporal norm overflow");
    let mut neighbors=Vec::with_capacity(n);
    for p in 0..n {
        let [x,y,w,h]=grid.rects[p];let centre=[2*x+w-1,2*y+h-1];
        let (bx,by)=(p%grid.cols,p/grid.cols);let mut row=Vec::new();
        for yy in by.saturating_sub(4)..=(by+4).min(grid.rows-1) {
            for xx in bx.saturating_sub(4)..=(bx+4).min(grid.cols-1) {
                let q=yy*grid.cols+xx;let [qx,qy,qw,qh]=grid.rects[q];
                let other=[2*qx+qw-1,2*qy+qh-1];
                if centre[0].abs_diff(other[0])>2*RADIUS || centre[1].abs_diff(other[1])>2*RADIUS {continue;}
                let weight=if p==q {1.0} else if mode==Mode::Off {0.0}
                    else if mode==Mode::AllAffinity {1.0}
                    else if norms[p]==0.0 || norms[q]==0.0 {0.0}
                    else {
                        let mut dot=0.0f32;
                        for d in &differences {for c in 0..4 {dot+=d[p][c]*d[q][c];}}
                        let denominator=norms[p].sqrt()*norms[q].sqrt();
                        ensure!(dot.is_finite() && denominator.is_finite() && denominator>0.0,"affinity arithmetic overflow");
                        // Clamp only roundoff above the Cauchy-Schwarz bound.
                        let cosine=(dot/denominator).clamp(0.0,1.0);cosine*cosine
                    };
                row.push((q,weight));
            }
        }
        ensure!(row.iter().any(|&(q,w)|q==p && w==1.0),"self support missing");neighbors.push(row);
    }
    Ok(Affinity{grid:grid.clone(),neighbors,source_count:means.len(),mode})
}

/// Area-weighted fields over actual clipped blocks, copied to the anchor block.
/// This is a block-centre square neighbourhood, not a per-pixel65x65 box.
pub(crate) fn pool_fields(affinity:&Affinity,energy:&[f32],floor:&[f32])->Result<(Vec<f32>,Vec<f32>)> {
    let g=&affinity.grid;grid_values(energy,g,true)?;grid_values(floor,g,true)?;
    ensure!(affinity.neighbors.len()==g.rects.len(),"affinity grid mismatch");
    let es=block_sums(energy,g);let fs=block_sums(floor,g);
    ensure!(es.iter().chain(&fs).all(|v|v.is_finite()),"block field sum overflow");
    let mut pooled_e=vec![0.0;energy.len()];let mut pooled_f=vec![0.0;floor.len()];
    for (p,row) in affinity.neighbors.iter().enumerate() {
        let mut se=0.0f32;let mut sf=0.0f32;let mut area=0.0f32;
        for &(q,w) in row {
            ensure!(q<g.rects.len() && w.is_finite() && (0.0..=1.0).contains(&w),"invalid affinity entry");
            se+=w*es[q];sf+=w*fs[q];area+=w*g.areas[q] as f32;
        }
        ensure!(area.is_finite() && area>0.0 && se.is_finite() && sf.is_finite(),"invalid pooled field");
        let e=se/area;let f=sf/area;let [x,y,w,h]=g.rects[p];
        for yy in y..y+h {for xx in x..x+w {pooled_e[yy*g.width+xx]=e;pooled_f[yy*g.width+xx]=f;}}
    }Ok((pooled_e,pooled_f))
}
