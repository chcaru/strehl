"""Sparse, read-only inspection of six preselected output-native points.

No RAW or TIFF pixels are read. Selection weights are not radiance ownership.
Potential MHC/collapse ancestry is reported before the nonlinear final hull.
Points were fixed by root before the observer result; no point search follows.
"""
import collections
import hashlib
import json
from pathlib import Path
import struct

HERE=Path(__file__).resolve().parent
TRACE=HERE.parent/'vitamin-c-weight-trace-1'
POINTS={'facet-core':(2624,2906),'facet-fan':(2602,2945),'facet-rim':(2760,2998),
        'dark-core':(3080,2150),'dark-fan':(3102,2203),'dark-structure':(3240,2070)}
FG=[(0,0,4),(-1,0,2),(1,0,2),(0,-1,2),(0,1,2),(-2,0,-1),(2,0,-1),(0,-2,-1),(0,2,-1)]
FH=[(0,0,5),(-1,0,4),(1,0,4),(-2,0,-1),(2,0,-1),(-1,-1,-1),(1,-1,-1),(-1,1,-1),(1,1,-1),(0,-2,.5),(0,2,.5)]
FV=[(dy,dx,w) for dx,dy,w in FH]
FX=[(0,0,6),(-1,-1,2),(1,-1,2),(-1,1,2),(1,1,2),(-2,0,-1.5),(2,0,-1.5),(0,-2,-1.5),(0,2,-1.5)]
KNOWN=[(0,0,8)]

def ancestry(x,extents,k):
    result={x:1.0}
    for level in range(1,k+1):
        out=collections.defaultdict(float)
        for p,w in result.items():
            c=p//2
            taps=[(c-1,.125),(c,.75),(c+1,.125)] if p%2==0 else [(c,.5),(c+1,.5)]
            for j,v in taps:out[max(0,min(j,extents[level]-1))]+=w*v
        result=dict(out)
    assert sum(result.values())==1.0
    return result

def stencil(x,y):
    phase=(y%2)*2+x%2
    return [[KNOWN,FG,FX],[FH,KNOWN,FV],[FV,KNOWN,FH],[FX,FG,KNOWN]][phase]

def commission():
    # Forward expansion, independently iterated over every output element.
    extents=[17,9,5,3]
    for k in range(1,4):
        for impulse in range(extents[k]):
            a=[float(i==impulse) for i in range(extents[k])]
            for level in range(k-1,-1,-1):
                b=[]
                for x in range(extents[level]):
                    c=x//2
                    if x&1:b.append((a[c]+a[min(c+1,len(a)-1)])/2)
                    else:b.append(a[max(c-1,0)]/8+3*a[c]/4+a[min(c+1,len(a)-1)]/8)
                a=b
            for x,v in enumerate(a):assert ancestry(x,extents,k).get(impulse,0.0)==v
    assert ancestry(3,extents,1)=={1:.5,2:.5}
    assert ancestry(3,extents,1)!={1:1.0},'nearest-coefficient destroyer escaped'
    assert all(sum(w for _,_,w in f)==8 for f in [FG,FH,FV,FX,KNOWN])

def main():
    commission()
    receipt=json.loads((TRACE/'completion.json').read_text())
    assert receipt['observer_output_bit_exact']
    dims=json.loads((TRACE/'weights-dims.json').read_text())
    assert dims['frames']==70
    bands=dims['bands'];assert (bands[0]['w'],bands[0]['h'])==(3460,2306)
    widths=[b['w'] for b in bands];heights=[b['h'] for b in bands]
    records={}
    for name,(x,y) in POINTS.items():
        # Union includes the known channel and both interpolated channels.
        native={(x+dx,y+dy) for f in stencil(x,y) for dx,dy,_ in f}
        native_taps={c:[{'native':[x+dx,y+dy],'mhc_weight':w/8,
                         'cfa_plane':((y+dy)%2)*2+(x+dx)%2} for dx,dy,w in f]
                     for c,f in zip('RGB',stencil(x,y))}
        rows=[]
        for k,b in enumerate(bands):
            union=set()
            for nx,ny in native:
                union.update((xx,yy) for xx in ancestry(nx//2,widths,k) for yy in ancestry(ny//2,heights,k))
            centre={(xx,yy):wx*wy for xx,wx in ancestry(x//2,widths,k).items()
                    for yy,wy in ancestry(y//2,heights,k).items()}
            handles={key:(TRACE/f'weights-b{k}-{suffix}').open('rb')
                     for key,suffix in [('arg','arg.i32'),('conc','conc.f32'),('neff','neff.f32')]}
            values=[]
            for xx,yy in sorted(union,key=lambda p:(p[1],p[0])):
                item={'xy':[xx,yy],'centre_expansion_weight':centre.get((xx,yy),0.0)}
                for key,h in handles.items():
                    h.seek((yy*b['w']+xx)*4)
                    value=struct.unpack('<i' if key=='arg' else '<f',h.read(4))[0]
                    item[key]=value if key=='arg' or value==value else None
                assert -1<=item['arg']<70
                assert (item['arg']==-1)==(item['conc'] is None)
                values.append(item)
            for h in handles.values():h.close()
            votes=collections.defaultdict(float)
            cmean=neffmean=late_lo=late_hi=0.0
            for item in values:
                w=item['centre_expansion_weight'];arg=item['arg']
                votes[arg]+=w
                if arg<0:
                    cmean+=w/70;neffmean+=w*70;late_lo+=w*20/70;late_hi+=w*20/70
                else:
                    c=item['conc'];cmean+=w*c;neffmean+=w*item['neff']
                    late_lo+=w*(c if arg>=50 else 0)
                    late_hi+=w*(1 if arg>=50 else 1-c)
            rows.append({'band':k,'support_union_count':len(union),'centre_ancestry_count':len(centre),
                'centre_dominant_index_geometry_mass':dict(sorted(votes.items())),
                'centre_geometry_weighted_conc':cmean,'centre_geometry_weighted_neff':neffmean,
                'centre_geometry_weighted_late_50_69_weight_bounds':[late_lo,late_hi],
                'potential_coefficients':values})
            shown=','.join(f'{i}:{w:.3f}' for i,w in sorted(votes.items(),key=lambda p:-p[1]) if w>0)
            print(f'{name:14s} b{k} support={len(union):2d} dominant-index geometry {shown}; conc={cmean:.3f} neff={neffmean:.2f}; late-weight=[{late_lo:.3f},{late_hi:.3f}]')
        records[name]={'output_native':[x,y],'native_mhc_taps':native_taps,'bands':rows}
    output={'status':'MEASURED_DIAGNOSTIC_NOT_QUALITY','observer_tiff_sha256':receipt['image']['sha256'],
        'coordinates':'cropped output native; no active-origin offset added',
        'conventions':'exact pre-hull collapse ancestry; even 1/8,3/4,1/8; odd 1/2,1/2; MHC potential union',
        'limitations':'darg is largest weight, not exclusive source. Geometry-weighted summaries do not include signed band coefficient values, WB, final hull derivative or tone. They are not pixel radiance fractions. Base mean is reported as arg -1, not absent data.',
        'descriptive_late_group':'indices50..69, fixed before reading sparse diagnostic samples; not a quality threshold',
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'points':records}
    with (HERE/'result.json').open('x') as f:json.dump(output,f,indent=2,allow_nan=False)

if __name__=='__main__':main()
