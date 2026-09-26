// Compact actual-source observations. Included only in the CLI test binary.
use super::*;
use serde_json::json;
use std::{collections::BTreeSet, fs::File, io::{BufWriter, Write}};
use strehl_core::pyramid::{real_source_contributions as bridge,
    rb_own_guide_diagnostic::Fields, LevelSize};

const LINES: [(&str, [usize; 2], usize); 5] = [
    ("near-hair", [3510,3262], 1),
    ("far-hair", [3508,3170], 0),
    ("fan-haze-context", [3310,3120], 0),
    ("rim-hair-control", [1596,1796], 0),
    ("inner-bud-control", [4512,1732], 0),
];
const OFFSETS: [isize; 5] = [-8,-4,0,4,8];

fn sites() -> Vec<[usize; 2]> {
    LINES.iter().flat_map(|(_,xy,axis)| OFFSETS.map(|d| {
        let mut p = *xy; p[*axis] = (p[*axis] as isize + d) as usize;
        assert!(p.iter().all(|v| v % 2 == 0)); [p[0]/2,p[1]/2]
    })).collect()
}
fn children(x: usize, n: usize) -> Vec<usize> {
    let c = x / 2;
    if x % 2 == 0 {vec![c.saturating_sub(1),c,(c+1).min(n-1)]}
    else {vec![c,(c+1).min(n-1)]}
}
fn closure(sizes: &[LevelSize], xy: &[[usize; 2]]) -> Vec<Vec<usize>> {
    let mut nodes = vec![xy.iter().map(|p| {
        assert!(p[0] < sizes[0].width && p[1] < sizes[0].height);
        p[1]*sizes[0].width+p[0]
    }).collect::<BTreeSet<_>>().into_iter().collect::<Vec<_>>()];
    for k in 1..sizes.len() {
        let mut next = BTreeSet::new();
        for &j in &nodes[k-1] {
            for y in children(j/sizes[k-1].width,sizes[k].height) {
                for x in children(j%sizes[k-1].width,sizes[k].width) { next.insert(y*sizes[k].width+x); }
            }
        }
        nodes.push(next.into_iter().collect());
    }
    nodes
}
fn bits_equal(a: &[f32], b: &[f32]) -> bool {
    a.len()==b.len() && a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())
}
fn write_floats(out: &mut impl Write, values: &[f32]) -> Result<()> {
    ensure!(values.iter().all(|v|v.is_finite()),"nonfinite trace input");
    for v in values {out.write_all(&v.to_bits().to_le_bytes())?;} Ok(())
}
fn save(path: &Path, value: &serde_json::Value) -> Result<()> {
    let mut out=std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut out,value)?;writeln!(out)?;Ok(())
}

/// Literal production expand tap association, applied only at the dependency
/// closure; commissioned against the full production Pyramid::collapse.
fn sparse_collapse(sizes: &[LevelSize], nodes: &[Vec<usize>], bands: &[Vec<f32>]) -> Vec<f32> {
    assert_eq!(sizes.len(),nodes.len());assert_eq!(nodes.len(),bands.len());
    let mut acc=bands.last().unwrap().clone();
    for k in (0..sizes.len()-1).rev() {
        let parent=sizes[k+1];
        let at=|x:usize,y:usize| acc[nodes[k+1].binary_search(&(y*parent.width+x)).unwrap()];
        let horizontal=|x:usize,y:usize| {
            let c=x/2;
            if x%2==0 {0.125*at(c.saturating_sub(1),y)+0.75*at(c,y)+0.125*at((c+1).min(parent.width-1),y)}
            else {0.5*(at(c,y)+at((c+1).min(parent.width-1),y))}
        };
        let out=nodes[k].iter().enumerate().map(|(q,&j)| {
            let (x,y)=(j%sizes[k].width,j/sizes[k].width);let c=y/2;
            let v=if y%2==0 {0.125*horizontal(x,c.saturating_sub(1))+0.75*horizontal(x,c)
                +0.125*horizontal(x,(c+1).min(parent.height-1))}
                else {0.5*(horizontal(x,c)+horizontal(x,(c+1).min(parent.height-1)))};
            v+bands[k][q]
        }).collect();
        acc=out;
    }
    acc
}

pub(crate) struct Session {
    dir:PathBuf, sizes:Vec<LevelSize>, nodes:Vec<Vec<usize>>, xy:Vec<[usize;2]>,
    out:BufWriter<File>, chunk:Vec<Vec<[f32;9]>>, total:Option<Vec<Vec<[f32;9]>>>,
    seen:usize, count:usize, per_chunk:usize,
}
impl Session {
    pub(crate) fn start(dir:&Path,sizes:&[LevelSize],count:usize,per_chunk:usize)->Result<Option<Self>> {
        let mode=std::env::var("STREHL_REAL_SOURCE_TRACE").ok();
        ensure!(mode.as_deref().is_none_or(|s|s=="on"||s=="off"),"invalid real trace switch");
        if mode.as_deref()!=Some("on") {return Ok(None);}
        ensure!(sizes==level_sizes(3134,2088,7).as_slice()&&count==488&&per_chunk==122,"fixed complete marigold scope differs");
        let dir=dir.join("source-trace");std::fs::create_dir(&dir)?;
        let xy=sites();let nodes=closure(sizes,&xy);
        let chunk=nodes.iter().map(|v|vec![[0.0;9];v.len()]).collect();
        let out=BufWriter::new(std::fs::OpenOptions::new().write(true).create_new(true).open(dir.join("sources.f32"))?);
        let s=Self{dir,sizes:sizes.to_vec(),nodes,xy,out,chunk,total:None,seen:0,count,per_chunk};
        save(&s.dir.join("layout.json"),&json!({"schema":1,"count":count,"per_chunk":per_chunk,
            "numerator_scale":bridge::NUMERATOR_SCALE,"plane_order":["R","G1","G2","B"],
            "sizes":sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),"nodes":s.nodes,"quad_sites":s.xy,
            "native_lines":LINES.iter().map(|(name,xy,axis)|json!({"name":name,"centre":xy,"axis":axis})).collect::<Vec<_>>(),
            "native_offsets":OFFSETS,"source_layout":"frame-major: gathered4 per site; then level-major/node-major [weight,energy,floor,R,G1,G2,B]; base energy/floor/weight are exact zero sentinels",
            "final_layout":"level-major/node-major [den,scaled-num4,unweighted-sum4,resolved4]",
            "source_record_floats":s.xy.len()*4+s.nodes.iter().map(Vec::len).sum::<usize>()*7,
            "temporal_groups_inclusive":[[0,79],[80,168],[169,319],[320,400],[401,487]],
            "scope":"Read-only actual-consumer attribution. Neither weight nor absolute contribution is a quality metric."}))?;
        Ok(Some(s))
    }
    pub(crate) fn source(&mut self,index:usize,merge:&BandMerge,ws:&FrameWorkspace,
        fields:&Fields,planes:&[Vec<f32>])->Result<()> {
        ensure!(index==self.seen&&index<self.count&&planes.len()==4,"trace source order/count differs");
        for &[x,y] in &self.xy {
            let j=y*self.sizes[0].width+x;
            write_floats(&mut self.out,&std::array::from_fn::<_,4,_>(|c|planes[c][j]))?;
        }
        for k in 0..self.sizes.len() {
            let coeff=bridge::coefficients(ws,k);
            for(q,&j)in self.nodes[k].iter().enumerate() {
                let (w,e,f)=if k+1<self.sizes.len(){(fields.weights[k][j],fields.energy[k][j],fields.floor[k][j])}else{(0.,0.,0.)};
                let row=[w,e,f,coeff[0][j],coeff[1][j],coeff[2][j],coeff[3][j]];
                write_floats(&mut self.out,&row)?;
                let acc=&mut self.chunk[k][q];acc[0]+=w;
                for c in 0..4 {acc[1+c]+=w*(row[3+c]/bridge::NUMERATOR_SCALE);acc[5+c]+=row[3+c];}
                ensure!(bits_equal(acc,&bridge::state(merge,k,j)[..9]),"actual chunk attribution mismatch source{index}/band{k}/node{j}");
            }
        }
        self.seen+=1;
        if self.seen%self.per_chunk==0||self.seen==self.count {
            if let Some(total)=&mut self.total {
                for (dst,src) in total.iter_mut().flatten().zip(self.chunk.iter().flatten()) {
                    for(a,b)in dst.iter_mut().zip(src){*a+=*b;}
                }
            }else{self.total=Some(self.chunk.clone());}
            for a in self.chunk.iter_mut().flatten(){a.fill(0.0);}
        }
        Ok(())
    }
    pub(crate) fn finish(mut self,merge:&BandMerge,output:&[Vec<f32>])->Result<()> {
        ensure!(self.seen==self.count&&merge.frames()as usize==self.count&&output.len()==4,"incomplete source trace");
        self.out.flush()?;
        let mut states=BufWriter::new(std::fs::OpenOptions::new().write(true).create_new(true).open(self.dir.join("final-states.f32"))?);
        let total=self.total.as_ref().context("missing trace accumulation")?;
        let mut bands:[Vec<Vec<f32>>;4]=std::array::from_fn(|_|self.nodes.iter().map(|v|vec![0.;v.len()]).collect());
        for k in 0..self.sizes.len(){for(q,&j)in self.nodes[k].iter().enumerate(){
            let row=bridge::state(merge,k,j);
            ensure!(bits_equal(&total[k][q],&row[..9]),"canonical chunk absorb differs");
            write_floats(&mut states,&row)?;
            for c in 0..4{bands[c][k][q]=row[9+c];}
        }}states.flush()?;
        let collapsed:[Vec<f32>;4]=std::array::from_fn(|c|sparse_collapse(&self.sizes,&self.nodes,&bands[c]));
        let mut sites=Vec::new();
        for &[x,y]in &self.xy {
            let j=y*self.sizes[0].width+x;let q=self.nodes[0].binary_search(&j).unwrap();
            let bounds=bridge::hull(merge,j);let pre=std::array::from_fn::<_,4,_>(|c|collapsed[c][q]);
            let post=std::array::from_fn::<_,4,_>(|c|output[c][j]);
            ensure!((0..4).all(|c|pre[c].clamp(bounds[c][0],bounds[c][1]).to_bits()==post[c].to_bits()),"sparse final CFA differs at{x},{y}");
            sites.push(json!({"quad":[x,y],"pre_hull":pre,"post_hull":post,"bounds":bounds,"pre_hull_bits":pre.map(f32::to_bits),"post_hull_bits":post.map(f32::to_bits)}));
        }
        save(&self.dir.join("receipt.json"),&json!({"schema":1,"sources":self.seen,
            "all_sampled_chunk_accumulators_bit_exact":true,"all_final_accumulators_bit_exact":true,
            "all_sampled_final_cfa_bit_exact":true,"sites":sites,
            "scope":"Finite-sample accounting only; observer identity and interpretation require independent complete-output comparison."}))?;
        Ok(())
    }
}

#[test]
fn sparse_footprint_controls()->Result<()> {
    use strehl_core::pyramid::Pyramid;
    // Both parity phases, all four replicated borders, odd extents and seven bands.
    let sizes=level_sizes(1031,1029,7);
    assert_eq!(sizes.len(),8,"fixture did not reach seven AC bands plus base");
    let xy=vec![[0,0],[1,1],[2,3],[1030,1028],[1029,1027],[510,511],[511,512]];
    let nodes=closure(&sizes,&xy);let mut p=Pyramid::zeros(&sizes);
    for(k,s)in sizes.iter().enumerate(){for(j,v)in p.level_mut(k).iter_mut().enumerate(){
        let x=j%s.width;let y=j/s.width;*v=((x*37+y*19+k*53)%1021)as f32*0.125-60.0;
    }}
    let bands=nodes.iter().enumerate().map(|(k,v)|v.iter().map(|&j|p.level(k)[j]).collect::<Vec<_>>()).collect::<Vec<_>>();
    let a=sparse_collapse(&sizes,&nodes,&bands);let full=p.collapse(&mut Workspace::new(&sizes));
    ensure!(a.iter().zip(&nodes[0]).all(|(a,&j)|a.to_bits()==full[j].to_bits()),"sparse production collapse differs");
    let mut altered=bands.clone();let last=altered.len()-1;altered[last].fill(0.0);
    let broken=sparse_collapse(&sizes,&nodes,&altered);
    ensure!(broken.iter().zip(&a).any(|(x,y)|(x-y).abs()>0.1),"missing coarse term destroyer unexercised");
    // Constant per-band bases retain exact total DC, including replicated borders.
    let constant=nodes.iter().enumerate().map(|(k,v)|vec![k as f32+1.;v.len()]).collect::<Vec<_>>();
    let expected=(1..=sizes.len()).sum::<usize>()as f32;
    ensure!(sparse_collapse(&sizes,&nodes,&constant).iter().all(|&v|v==expected),"DC accounting differs");
    Ok(())
}

#[cfg(test)]
mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/real-source-contributions/independent-controls.rs"));
}
