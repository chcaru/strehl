// Fixed generated-only topology experiment. No ownership correctness claim.
use std::collections::{BTreeMap,BTreeSet};
pub(crate) const FIELD_FLOOR:f32=5.0;
pub(crate) const PEAK_MIN:f32=8.0;
pub(crate) const PROMINENCE_MIN:f32=3.0;
pub(crate) const MIN_NODES:usize=3;
pub(crate) const MIN_CORE:usize=2;
const NONE:usize=usize::MAX;

#[derive(Clone)]
pub(crate) struct Branch {
    pub cells:Vec<usize>,pub core:Vec<usize>,pub peak:f32,pub saddle:f32,
    pub clipped:bool,pub source_edge:bool,pub alias:bool,
}
pub(crate) struct Analysis {
    pub branches:Vec<Branch>,pub field_hash:String,pub clipped_stencil_cells:usize,
}
fn neighbours(p:usize,w:usize,h:usize)->impl Iterator<Item=usize> {
    let x=p%w;let y=p/w;
    (-1isize..=1).flat_map(move |dy|(-1isize..=1).filter_map(move |dx| {
        let xx=x as isize+dx;let yy=y as isize+dy;
        if (dx!=0 || dy!=0) && xx>=0 && yy>=0 && xx<w as isize && yy<h as isize {
            Some(yy as usize*w+xx as usize)
        }else{None}
    }))
}
fn root(parent:&mut[usize],mut p:usize)->usize {
    while parent[p]!=p {let next=parent[p];parent[p]=parent[next];p=parent[p];}p
}
fn unite(parent:&mut[usize],a:usize,b:usize) {
    let a=root(parent,a);let b=root(parent,b);if a!=b {let (lo,hi)=if a<b{(a,b)}else{(b,a)};parent[hi]=lo;}
}
struct Leaf {cells:Vec<usize>,peak:f32,saddle:f32}

/// Equal-valued plateaus enter together, avoiding raster-order peak creation.
pub(crate) fn component_tree(field:&[f32],w:usize,h:usize)->Result<Vec<Branch>> {
    ensure!(field.len()==w*h && field.iter().all(|v|v.is_finite() && *v>=0.0),"invalid topology field");
    let mut order=(0..field.len()).filter(|&p|field[p]>FIELD_FLOOR).collect::<Vec<_>>();
    order.sort_unstable_by(|&a,&b|field[b].total_cmp(&field[a]).then(a.cmp(&b)));
    let mut parent=vec![NONE;field.len()];let mut owner=vec![NONE;field.len()];
    let mut leaves:Vec<Leaf>=Vec::new();let mut start=0;
    while start<order.len() {
        let level=field[order[start]];let mut end=start+1;
        while end<order.len() && field[order[end]].to_bits()==level.to_bits(){end+=1;}
        let batch=&order[start..end];let mut old_edges=Vec::new();
        for &p in batch {for q in neighbours(p,w,h){if parent[q]!=NONE {
            let r=root(&mut parent,q);old_edges.push((p,r,owner[r]));
        }}}
        for &p in batch{parent[p]=p;}
        for &p in batch{for q in neighbours(p,w,h){if parent[q]!=NONE{unite(&mut parent,p,q);}}}
        let mut groups:BTreeMap<usize,(Vec<usize>,BTreeSet<usize>)>=BTreeMap::new();
        for &p in batch{let r=root(&mut parent,p);groups.entry(r).or_default().0.push(p);}
        for (p,_,old_owner) in old_edges{let r=root(&mut parent,p);groups.get_mut(&r).unwrap().1.insert(old_owner);}
        for (r,(cells,previous)) in groups {
            let label=if previous.is_empty(){
                let id=leaves.len();leaves.push(Leaf{cells:Vec::new(),peak:level,saddle:FIELD_FLOOR});id
            }else if previous.len()==1 && !previous.contains(&NONE){*previous.first().unwrap()}
            else {
                for &id in &previous {if id!=NONE {leaves[id].saddle=leaves[id].saddle.max(level);}}
                NONE
            };
            owner[r]=label;if label!=NONE {leaves[label].cells.extend(cells);}
        }
        start=end;
    }
    Ok(leaves.into_iter().map(|mut leaf|{
        leaf.cells.sort_unstable();let cutoff=0.5*(leaf.peak+leaf.saddle);
        let core=leaf.cells.iter().copied().filter(|&p|field[p]>=cutoff).collect();
        Branch{cells:leaf.cells,core,peak:leaf.peak,saddle:leaf.saddle,clipped:false,source_edge:false,alias:false}
    }).collect())
}

/// Exact original-u16 contrast variance; no assertion about gathered covariance.
pub(crate) fn analyse_source(frame:&Frame,warp:Similarity,crop:align_cmd::CropRect,noise:&NoiseModel)->Result<Analysis> {
    let full=frame.geometry();let w=full.width;let h=full.height;
    ensure!(w>=5 && h>=5,"original topology support too small");
    let mut field=vec![0.0f32;w*h];let mut clipped=vec![false;w*h];
    let taps=[1.0f32/16.0,4.0/16.0,6.0/16.0,4.0/16.0,1.0/16.0];
    let planes=[CfaPlane::R,CfaPlane::G1,CfaPlane::G2,CfaPlane::B];
    for (c,plane) in planes.into_iter().enumerate(){
        let ox=c%2;let oy=c/2;let mut signal=vec![0.0;w*h];let mut variance=vec![0.0;w*h];let mut pinned=vec![false;w*h];
        for y in 0..h {for x in 0..w {
            let raw=frame.active_row(2*y+oy)[2*x+ox];let v=raw as f32-frame.levels.black;let p=y*w+x;
            signal[p]=v;variance[p]=noise.variance(plane,v);pinned[p]=raw as f32>=frame.levels.white;
            ensure!(variance[p].is_finite() && variance[p]>=0.0,"invalid injected original variance");
        }}
        for y in 2..h-2 {for x in 2..w-2 {
            let p=y*w+x;let mut smooth=0.0;let mut var=0.0;let mut pin=false;
            for dy in 0..5 {for dx in 0..5 {
                let q=(y+dy-2)*w+x+dx-2;let k=taps[dy]*taps[dx];
                smooth+=k*signal[q];let a=if dx==2 && dy==2{1.0-k}else{-k};
                var+=a*a*variance[q];pin|=pinned[q];
            }}
            let z=if var>0.0{((signal[p]-smooth)/var.sqrt()).max(0.0)}else{0.0};
            ensure!(z.is_finite(),"nonfinite original contrast");field[p]=field[p].max(z);clipped[p]|=pin;
        }}
    }
    let field_hash=hash32(&field);let clipped_stencil_cells=clipped.iter().filter(|&&b|b).count();
    let inverse=warp.invert().ok_or_else(||anyhow::anyhow!("singular fixed source map"))?;
    let map=|p:usize|->Option<usize>{
        let (x,y)=inverse.apply_at((p%w) as f64+0.25,(p/w) as f64+0.25,w as f64/2.0,h as f64/2.0);
        let x=x-crop.x as f64;let y=y-crop.y as f64;
        (x>=0.0 && y>=0.0 && x<crop.width as f64 && y<crop.height as f64)
            .then_some(y.floor() as usize*crop.width+x.floor() as usize)
    };
    let mut branches=component_tree(&field,w,h)?;
    for branch in &mut branches {
        branch.clipped=branch.cells.iter().any(|&p|clipped[p]);
        branch.source_edge=branch.cells.iter().any(|&p|p%w<=2 || p%w+3>=w || p/w<=2 || p/w+3>=h);
        branch.cells=branch.cells.iter().filter_map(|&p|map(p)).collect();branch.cells.sort_unstable();branch.cells.dedup();
        branch.core=branch.core.iter().filter_map(|&p|map(p)).collect();branch.core.sort_unstable();branch.core.dedup();
    }
    branches.retain(|b|!b.cells.is_empty());let mut raster=vec![NONE;crop.width*crop.height];let mut aliased=BTreeSet::new();
    for (id,b) in branches.iter().enumerate(){for &p in &b.cells{
        if raster[p]!=NONE && raster[p]!=id {aliased.insert(id);aliased.insert(raster[p]);}else{raster[p]=id;}
    }}
    for id in aliased{branches[id].alias=true;}
    Ok(Analysis{branches,field_hash,clipped_stencil_cells})
}

struct Node {frame:usize,core:Vec<(usize,f32)>}
struct Track {nodes:Vec<Node>,union:BTreeSet<usize>,common:BTreeSet<usize>,bad:BTreeSet<&'static str>}
pub(crate) struct Tracker {
    w:usize,h:usize,n:usize,tracks:Vec<Track>,previous:Vec<(Branch,usize)>,
    pub field_hashes:Vec<String>,pub clipped_stencil_counts:Vec<usize>,branch_counts:Vec<usize>,
}
pub(crate) struct Membership {pub alpha:Vec<f32>,pub pixel_major_q:Vec<f32>,pub evidence:serde_json::Value}
impl Tracker {
    pub(crate) fn new(w:usize,h:usize,n:usize)->Self {
        Self{w,h,n,tracks:Vec::new(),previous:Vec::new(),field_hashes:Vec::new(),clipped_stencil_counts:Vec::new(),branch_counts:Vec::new()}
    }
    pub(crate) fn push(&mut self,frame:usize,analysis:Analysis,weights:&[f32])->Result<()> {
        ensure!(frame==self.branch_counts.len() && frame<self.n && weights.len()==self.w*self.h
            && weights.iter().all(|v|v.is_finite() && *v>=0.0),"invalid ordered lineage source");
        self.field_hashes.push(analysis.field_hash);self.clipped_stencil_counts.push(analysis.clipped_stencil_cells);
        self.branch_counts.push(analysis.branches.len());let mut old_at=vec![Vec::new();self.w*self.h];
        for (id,(b,_)) in self.previous.iter().enumerate(){for &p in &b.cells{old_at[p].push(id);}}
        let links=analysis.branches.iter().map(|b|b.cells.iter().flat_map(|&p|old_at[p].iter().copied()).collect::<BTreeSet<_>>()).collect::<Vec<_>>();
        let mut degree=vec![0usize;self.previous.len()];for l in &links{for &i in l{degree[i]+=1;}}
        for (i,&d) in degree.iter().enumerate(){if d>1 {let id=self.previous[i].1;self.tracks[id].bad.insert("split-or-merge");}}
        let mut next=Vec::new();
        for (index,b) in analysis.branches.into_iter().enumerate(){
            let link=&links[index];let unique=link.len()==1 && degree[*link.first().unwrap()]==1;
            let id=if unique {self.previous[*link.first().unwrap()].1}else{
                let mut bad=BTreeSet::new();if !link.is_empty(){bad.insert("split-or-merge");
                    for &old in link {self.tracks[self.previous[old].1].bad.insert("split-or-merge");}}
                let id=self.tracks.len();self.tracks.push(Track{nodes:Vec::new(),union:BTreeSet::new(),common:b.core.iter().copied().collect(),bad});id
            };
            let t=&mut self.tracks[id];
            if b.clipped{t.bad.insert("original-clipping-stencil");}if b.source_edge{t.bad.insert("original-support-edge");}
            if b.alias{t.bad.insert("reference-cell-alias");}
            if b.peak<PEAK_MIN || b.peak-b.saddle<PROMINENCE_MIN{t.bad.insert("weak-branch");}
            let current=b.core.iter().copied().collect::<BTreeSet<_>>();t.common.retain(|p|current.contains(p));
            t.union.extend(b.cells.iter().copied());
            t.nodes.push(Node{frame,core:b.core.iter().map(|&p|(p,weights[p])).collect()});
            next.push((b,id));
        }
        self.previous=next;Ok(())
    }
    pub(crate) fn finish(mut self)->Result<Membership> {
        ensure!(self.branch_counts.len()==self.n,"lineage source sequence incomplete");
        let pixels=self.w*self.h;let mut owner=vec![NONE;pixels];let mut contested=vec![false;pixels];
        for (id,t) in self.tracks.iter().enumerate(){for &p in &t.union{
            if owner[p]!=NONE && owner[p]!=id{contested[p]=true;}else{owner[p]=id;}
        }}
        let mut alpha=vec![0.0;pixels];let mut q=vec![0.0;pixels*self.n];let mut reports=Vec::new();
        for (id,t) in self.tracks.iter_mut().enumerate(){
            if t.nodes.len()<MIN_NODES{t.bad.insert("short-lineage");}if t.common.len()<MIN_CORE{t.bad.insert("small-or-hot-core");}
            let mut half=[vec![0.0f32;self.n],vec![0.0;self.n]];let mut counts=[0usize;2];
            for &p in &t.common{counts[(p%self.w+p/self.w)%2]+=1;}
            if counts.contains(&0){t.bad.insert("empty-core-subset");}
            if counts.iter().all(|&v|v>0){for node in &t.nodes{for &(p,w) in &node.core{if t.common.contains(&p){
                let h=(p%self.w+p/self.w)%2;half[h][node.frame]+=w/counts[h] as f32;
            }}}}
            let maxima=[half[0].iter().copied().fold(0.0f32,f32::max),half[1].iter().copied().fold(0.0f32,f32::max)];
            if maxima.contains(&0.0){t.bad.insert("no-core-detail-weight");}
            if !(0..self.n).any(|k|half[0][k]>=0.9*maxima[0] && half[1][k]>=0.9*maxima[1] && maxima[0]>0.0 && maxima[1]>0.0){
                t.bad.insert("core-subsets-disagree");
            }
            let total=counts[0]+counts[1];
            let shares=if total>0{[counts[0] as f32/total as f32,counts[1] as f32/total as f32]}else{[0.0,0.0]};
            // Count-weighted whole-core mean; normalize counts before multiplying
            // exp80-limited production weights so the intermediate cannot overflow.
            let mut weights=(0..self.n).map(|k|shares[0]*half[0][k]+shares[1]*half[1][k]).collect::<Vec<_>>();
            let max=weights.iter().copied().fold(0.0f32,f32::max);
            let min=t.nodes.iter().map(|n|weights[n.frame]).fold(f32::INFINITY,f32::min);
            if max<=0.0 || max-min<0.25*max{t.bad.insert("no-through-focus-weight-spread");}
            if max>0.0{for w in &mut weights{*w/=max;}let sum: f32=weights.iter().sum();for w in &mut weights{*w/=sum;}}
            let mut activated=0;
            if t.bad.is_empty(){
                let support=t.union.iter().filter(|&&p|!contested[p]).copied().collect::<BTreeSet<_>>();
                for &p in &support{
                    let inside=1+neighbours(p,self.w,self.h).filter(|p|support.contains(p)).count();
                    let a=inside as f32/9.0;alpha[p]=a;for k in 0..self.n{q[p*self.n+k]=a*weights[k];}activated+=1;
                }
            }
            reports.push(serde_json::json!({"track":id,"frames":t.nodes.iter().map(|n|n.frame).collect::<Vec<_>>(),
                "core_cells":t.common.len(),"subset_counts":counts,"footprint_cells":t.union.len(),
                "refusals":t.bad.iter().copied().collect::<Vec<_>>(),"source_weights":weights,"active_cells":activated}));
        }
        ensure!(q.iter().all(|v|v.is_finite() && *v>=0.0) && alpha.iter().all(|v|v.is_finite() && (0.0..=1.0).contains(v)),"invalid lineage memberships");
        Ok(Membership{alpha,pixel_major_q:q,evidence:serde_json::json!({"branch_counts":self.branch_counts,
            "field_hashes":self.field_hashes,"clipped_stencil_counts":self.clipped_stencil_counts,
            "contested_cells":contested.iter().filter(|&&v|v).count(),"tracks":reports,
            "field":"original four-plane positive binomial5 contrast / exact injected contrast sigma",
            "source_choice":"existing finest SoftPower averaged on disjoint persistent-core subsets",
            "confidence":"heuristic eligibility, not calibrated probability"})})
    }
}
