"""Geometry-only frozen witness mapping. Does not open images or RAW files."""
import hashlib, json, math, struct, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'outputs/multi-stack/baseline/bug-3-106'
CAND = ROOT / 'outputs/multi-stack/insect-repeat-4'
FROZEN = ROOT / 'outputs/multi-stack/independent-review/roi-frozen.json'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))
def warp(text):
    geom = ref = None
    rows = {}
    for line in text.splitlines():
        s = line.split()
        if not s: continue
        if s[0] == 'plane': geom = tuple(map(int, s[1].split('x')))
        if s[0] == 'reference': ref = int(s[1])
        if len(s) >= 6 and s[0].isdigit() and s[1] == 'placed':
            rows[int(s[0])] = tuple(struct.unpack('>d', bytes.fromhex(t))[0] for t in s[2:6])
    assert geom and ref is not None and rows
    return geom, ref, rows

def cover_scale(geom, rows, margin):
    # Same f64 operation order as Similarity::from_params/then/apply_at.
    w,h = geom
    cx,cy = w*.5,h*.5
    def covers(k):
        k = 1.0 + (k-1.0)
        for ar,ai,br,bi in rows:
            ar,ai = k*ar - 0.0*ai, k*ai + 0.0*ar
            for x,y in [(0.,0.),(w-1.,0.),(0.,h-1.),(w-1.,h-1.)]:
                px,py = x-cx,y-cy
                sx = (ar*px-ai*py)+br+cx
                sy = (ar*py+ai*px)+bi+cy
                if not (sx >= margin and sy >= margin and sx <= w-1.-margin and sy <= h-1.-margin): return False
        return True
    if covers(1.): return 1.
    lo,hi=0.,1.
    for _ in range(60):
        mid=.5*(lo+hi)
        if covers(mid): lo=mid
        else: hi=mid
    assert lo>0
    return lo

def rect(geom,k):
    axes=[]
    for n in geom:
        lo=.5*n*(1.-k)
        hi=lo+k*(n-1.)
        start=math.ceil(lo)
        end=max(start,min(n-1,math.floor(hi)))
        axes.append((start,end-start+1))
    return [axes[0][0],axes[1][0],axes[0][1],axes[1][1]]

def mapped_origin(origin,size,k,center,crop):
    # Coordinates name pixel centers; mean of N centers is origin+(N-1)/2.
    half=(size-1)*.5
    continuous=[center[d]+k*(origin[d]+half-center[d])-2*crop[d]-half for d in range(2)]
    rounded=[math.floor(v+.5) for v in continuous]  # nearest; ties toward +infinity
    return continuous,rounded

baseline_map=BASE/'warpmap.txt'
g,ref,brows=warp(baseline_map.read_text())
alignment=load(CAND/'alignment.json')
g2,ref2,crows=warp(alignment['warpmap'])
assert g==g2==(3516,2344) and ref==ref2==149
assert all(abs(v-e)<1e-12 for row in (brows[ref],crows[ref2]) for v,e in zip(row,(1.,0.,0.,0.)))
meta=load(BASE/'sensor.tiff.json')
identities=load(CAND/'source-identities.json')
assert meta['sources'][ref]['sha256']==identities[ref2]['sha256']
assert meta['sources'][ref]['path']==identities[ref2]['path']
assert meta['process']['cover_requested']=='Scale'
assert meta['process']['full_resolution_gather'] is True
saved_k=float(meta['process']['cover_applied'].removeprefix('Scaled(').removesuffix(')'))
k=cover_scale(g,brows.values(),3.0)
assert k.hex()==saved_k.hex(),(k,saved_k)
# Check implementation identity against the actual baseline source revision.
source=ROOT/'crates/strehl-cli/src/align_cmd.rs'
old=subprocess.run(['git','-C',str(ROOT),'--work-tree='+str(ROOT),'show','c149e52834fc1c86c2af0fe022713c39fa25f33c:crates/strehl-cli/src/align_cmd.rs'],check=True,capture_output=True,text=True).stdout
current=source.read_text()
for name,end in [('cover_scale','\n#[cfg(test)]'),('cover_rect','\n/// Reusable buffers')]:
    marker='pub fn '+name+'('
    def extract(text): return text.split(marker,1)[1].split(end,1)[0]
    assert extract(old)==extract(current),name
assert 'pub const COVER_MARGIN_PX: f64 = 3.0;' in old
# Independently rebuild native domain from first-pass placements, optical profile,
# CFA offsets and the session's selected reference pass. No image-content fit.
assert alignment['binding']['session']['primary_pass'] is None
assert alignment['report']['reference_pass']==0
cal=load(CAND/'calibration.json')[0]['optical_profile']
assert 'translation: (0.0, 0.0)' in cal['applied_record']
transformed=[]
for index in range(299):
    ar,ai,br,bi=crows[index]
    for dx,dy,eps in [(0,0,cal['eps_r']),(1,0,0.),(0,1,0.),(1,1,cal['eps_b'])]:
        s=1.+eps
        a,b,c,d=ar*s,ai*s,br*s,bi*s
        ox,oy=dx*.5-.25,dy*.5-.25
        c=c+(a*ox-b*oy)-ox
        d=d+(a*oy+b*ox)-oy
        transformed.append((a,b,c,d))
ck=cover_scale(g,transformed,3.0)
canvas=rect(g,ck)
assert canvas==load(CAND/'render-report.json')['canvas']==[38,26,3440,2292]
# Causal mechanical controls: identity preserves exact origins; crop shifts by
# exactly twice plane origin; wrong margin changes baseline scale.
for origin in [[5750,600],[0,0],[3100,2050]]:
    assert mapped_origin(origin,384,1.,g,[0,0])[1]==origin
    assert mapped_origin(origin,384,1.,g,[38,26])[1]==[origin[0]-76,origin[1]-52]
assert cover_scale(g,brows.values(),4.0).hex()!=k.hex()
frozen=load(FROZEN)
entries=[]
for roi in frozen['rois']:
    origin=roi['origins']['bug-3-106']; size=roi['size']
    nominal_continuous,nominal_out=mapped_origin(origin,size,k,g,canvas[:2])
    half=(size-1)*.5
    # Exact anchor transport, preserving tiny non-identity solve roundoff.
    # Legacy full-res gather: sensor u -> plane u/2. Native CFA guide:
    # sensor u -> plane (u-0.5)/2; apply inverse candidate anchor, then undo.
    q=complex((origin[0]+half)/2-g[0]/2,(origin[1]+half)/2-g[1]/2)*k
    ba=complex(*brows[ref][:2]); bb=complex(*brows[ref][2:])
    ca=complex(*crows[ref2][:2]); cb=complex(*crows[ref2][2:])
    physical=(ba*q+bb+complex(g[0]/2,g[1]/2))*2
    candidate_q=((physical-complex(.5,.5))/2-complex(g[0]/2,g[1]/2)-cb)/ca
    native=(candidate_q+complex(g[0]/2,g[1]/2))*2+complex(.5,.5)
    continuous=[native.real-2*canvas[0]-half,native.imag-2*canvas[1]-half]
    out=[math.floor(v+.5) for v in continuous]
    assert out==nominal_out
    assert max(abs(continuous[d]-nominal_continuous[d]) for d in range(2))<1e-10
    assert all(0<=out[d] and out[d]+size<=2*canvas[d+2] for d in range(2))
    entries.append({**roi,'origins':{'bug-3-106':origin,'insect-repeat-4':out,'shared-candidate-gauge':out},'baseline_center':[v+(size-1)*.5 for v in origin],'mapped_center':[continuous[d]+(size-1)*.5 for d in range(2)],'continuous_origin':continuous,'rounding_error_pixels':[out[d]-continuous[d] for d in range(2)]})
receipt={'schema':'strehl.independent-review-mapped-rois.v1','status':'FROZEN from saved geometry before viewing candidate photographic content','helper_sha256':sha(Path(__file__)),'source_roi_sha256':sha(FROZEN),'baseline_warpmap_sha256':sha(baseline_map),'baseline_sensor_metadata_sha256':sha(BASE/'sensor.tiff.json'),'candidate_alignment_file_sha256':sha(CAND/'alignment.json'),'candidate_warpmap_sha256':hashlib.sha256(alignment['warpmap'].encode()).hexdigest(),'candidate_calibration_sha256':sha(CAND/'calibration.json'),'align_source_sha256':sha(source),'common_reference':{'frame_index':ref,'path':identities[ref]['path'],'sha256':identities[ref]['sha256'],'legacy_placement_f64':brows[ref],'candidate_placement_f64':crows[ref2],'placements':'numerical identity; exact coefficients transported and same integer origins verified'},'baseline_cover_scale':k,'baseline_cover_scale_f64_hex':k.hex(),'baseline_saved_cover_applied':meta['process']['cover_applied'],'cover_margin_plane_pixels':3.,'candidate_cover_scale':ck,'candidate_canvas_plane_pixels':canvas,'candidate_native_dimensions':[2*canvas[2],2*canvas[3]],'formula':'Transport legacy scaled pixel centers through exact legacy reference placement and inverse candidate reference placement, accounting for legacy u/2 versus native (u-0.5)/2 guide conventions. This agrees below1e-10px with u_candidate=C+k_legacy*(u_legacy-C)-2*crop; C=(3516,2344).','center_convention':'Mean of integer pixel-center coordinates in each384 square: origin+191.5. Round mapped continuous origin to nearest integer via floor(x+0.5).','size':384,'maximum_abs_rounding_pixels':max(abs(v) for e in entries for v in e['rounding_error_pixels']),'limitations':['Geometry-only landmark mapping; no candidate image used for fitting or witness choice.','Same physical reference fixes coordinate gauge, not physical placement truth for every frame.','Legacy scaled/demosaic gather and native same-color CFA sampling differ; no pixelwise cross-path differences are licensed.','Same384 native output pixels cover different scene extents: legacy reference extent is384*k while candidate extent is384.','Color-specific optical pull and guide versus photosite-center conventions mean reconstructed color detail is not one exact image warp.','Baseline107 uses a different reference acquisition; its same frozen origins are landmark context, not an exact mapped coordinate correspondence.','Candidate pooled/only-pass controls must verify identical598 warpmap and canvas before reusing these origins.'],'rois':entries}
out=HERE/'roi-mapped-frozen.json'
out.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'baseline_k':k,'candidate_k':ck,'canvas':canvas,'max_rounding_error':receipt['maximum_abs_rounding_pixels'],'mapped_origins':{e['name']:e['origins']['insect-repeat-4'] for e in entries},'receipt':str(out),'receipt_sha256':sha(out)},indent=2))
