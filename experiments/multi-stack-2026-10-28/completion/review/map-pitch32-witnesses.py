"""Geometry-only transfer of preregistered focus witnesses; no image reads."""
from pathlib import Path
import ast,hashlib,json,math,struct
R=Path(__file__).resolve().parents[4];C=R/"outputs/multi-stack/completion";P=Path(__file__).resolve().parent
# Reuse the earlier reviewed exact warp parser and owned cover-scale operation.
helper=R/"experiments/multi-stack-2026-10-28/review/map-frozen-rois.py"
tree=ast.parse(helper.read_text());env={'struct':struct}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('warp','cover_scale')],type_ignores=[]),str(helper),'exec'),env)
warp,cover=env['warp'],env['cover_scale']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
old=C/"interleave-02";new=C/"interleave-pitch32-01";dense=C/"interleave-dense-01"
a,b=load(old/"alignment.json"),load(new/"alignment.json")
g,_,ow=warp(a['warpmap']);ng,nref,nw=warp(b['warpmap']);dg,_,dw=warp((dense/'warpmap.txt').read_text())
assert g==ng==dg==(3516,2344)
ni=load(new/'source-identities.json');oi=load(old/'source-identities.json');di=load(dense/'source-identities.json')
identity=ni[nref]['sha256'];oldi=next(i for i,v in enumerate(oi) if v['sha256']==identity);densei=next(i for i,v in enumerate(di) if v['sha256']==identity)
assert sum(v['sha256']==identity for v in oi)==sum(v['sha256']==identity for v in di)==1
oc=load(old/'render-report.json')['canvas'];nc=load(new/'render-report.json')['canvas']
for child in ('independent-pass-01','independent-pass-02'):assert load(new/child/'render-report.json')['canvas']==nc
k=cover(g,dw.values(),3.0);center=complex(g[0]/2,g[1]/2)
def coeff(rows,i):r=rows[i];return complex(r[0],r[1]),complex(r[2],r[3])
oa,ob=coeff(ow,oldi);na,nb=coeff(nw,nref);da,db=coeff(dw,densei)
def native_to_physical(u,canvas,a,b):
    q=(complex(*u)+2*complex(*canvas[:2])-complex(.5,.5))/2-center
    return 2*(a*q+b+center)+complex(.5,.5)
def physical_to_native(p,canvas,a,b):
    q=((p-complex(.5,.5))/2-center-b)/a
    return 2*(q+center)+complex(.5,.5)-2*complex(*canvas[:2])
for u in [(192.5,220.),(3200.,1700.)]:
    p=native_to_physical(u,oc,oa,ob);v=physical_to_native(p,oc,oa,ob)
    assert abs(v-complex(*u))<1e-10
# Known identity / translated controls disambiguate pull vs inverse direction.
u=(500.,600.);p=native_to_physical(u,[0,0],1+0j,3+4j)
assert abs(physical_to_native(p,[0,0],1+0j,0j)-complex(506.,608.))<1e-12
frozen=load(P/'pitch32-focus-witnesses.json');rows=[]
for i,w in enumerate(frozen['witnesses']):
    u=[v+191.5 for v in w['origin_sensor_in_dense_control']]
    physical=native_to_physical(u,oc,oa,ob)
    q=physical_to_native(physical,nc,na,nb)
    legacy=2*((physical/2-center-db)/da/k+center)
    continuous={'combined':[q.real-191.5,q.imag-191.5],'dense':[legacy.real-191.5,legacy.imag-191.5]}
    origins={label:[math.floor(v+.5) for v in p] for label,p in continuous.items()}
    origins['even32']=origins['combined'];origins['offset16']=origins['combined']
    assert all(0<=origins['combined'][j] and origins['combined'][j]+384<=2*nc[j+2] for j in range(2))
    assert all(0<=origins['dense'][j] and origins['dense'][j]+384<=2*g[j] for j in range(2))
    rows.append({'name':f"{w['direction']}-{i%3+1}",'size':384,'origins':origins,'continuous_origins':continuous,'source_witness':w})
receipt={'schema':'strehl.pitch32-native-witnesses.v1','status':'FROZEN before combined or second-half pixels were viewed; first-half locator only.',
 'shared_acquisition':{'sha256':identity,'old_index':oldi,'new_reference_index':nref,'dense_index':densei,'old_placement':ow[oldi],'new_placement':nw[nref],'dense_placement':dw[densei]},
 'old_canvas':oc,'new_canvas':nc,'ordinary_cover_scale':k,'ordinary_cover_scale_f64_hex':k.hex(),'cover_margin_quad':3.0,
 'formula':'Native pixel-center mean origin+191.5 -> (u+2crop-0.5)/2 -> centered old pull -> shared source -> inverse new pull ->2q+0.5-2newcrop. Ordinary inverse uses u/2 convention and exact saved-map cover-scale.',
 'limitations':['Gauge transfer uses saved fitted placements, not new registration validation.','No image matching or candidate fit.','Nearest integer origin floor(x+.5) introduces at most0.5sensor pixel center error.','All slices remain native384; different gauges have different physical scale. No cross-gauge pixelwise error or difference.','Focus width is a local shape descriptor, not confidence.'],
 'bindings':{'old_alignment':sha(old/'alignment.json'),'new_alignment':sha(new/'alignment.json'),'dense_map':sha(dense/'warpmap.txt'),'source_witnesses':sha(P/'pitch32-focus-witnesses.json'),'cover_helper':sha(helper)},'rois':rows}
p=P/'pitch32-rois-frozen.json'
with p.open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps({'receipt':str(p),'sha256':sha(p),'common_source':[oldi,nref,densei],'cover_scale':k,'origins':{v['name']:v['origins']['combined'] for v in rows}},indent=2))
