"""Author cross-check of saved native mosaic geometry and simpler fitted foils.

No pixel resampling, RAW decoding, admission change or quality certification.
Translation fits use fit-role observations only; heldouts never fit a foil.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "4"
import numpy as np

def location(mesh, point):
    w,h=mesh["source"];cols,rows=mesh["columns"],mesh["rows"]
    x,y=point
    if not (0<=x<=w-1 and 0<=y<=h-1):
        raise ValueError("observation outside source geometry")
    gx=x*(cols-1)/(w-1);gy=y*(rows-1)/(h-1)
    cx=min(math.floor(gx),cols-2);cy=min(math.floor(gy),rows-2)
    u=gx-cx;v=gy-cy;a=cy*cols+cx
    if v<=u: ids,weights=[a,a+1,a+cols+1],[1-u,u-v,v]
    else: ids,weights=[a,a+cols+1,a+cols],[1-v,u,v-u]
    return cy*(cols-1)+cx,ids,weights

def mapped(mesh, point):
    cell,ids,weights=location(mesh,point)
    return np.array(weights)@np.array(mesh["vertices"])[ids],cell

def determinants(mesh):
    w,h=mesh["source"];cols,rows=mesh["columns"],mesh["rows"]
    vertices=np.array(mesh["vertices"])
    area=(w-1)*(h-1)/((cols-1)*(rows-1))
    result=[]
    for y in range(rows-1):
        for x in range(cols-1):
            a=y*cols+x
            for ids in ([a,a+1,a+cols+1],[a,a+cols+1,a+cols]):
                origin,b,c=vertices[ids]
                left,right=b-origin,c-origin
                result.append(float((left[0]*right[1]-left[1]*right[0])/area))
    return result

def statistics(values):
    if not values: return {"count":0,"rms_quad":None,"maximum_quad":None}
    return {"count":len(values),"rms_quad":float(np.sqrt(np.mean(np.array(values)**2))),"maximum_quad":max(values)}

def self_test():
    mesh={"source":[101,81],"columns":3,"rows":3,
          "vertices":[[x*50-13,y*40+7] for y in range(3) for x in range(3)]}
    for point in ([0,0],[100,80],[12.5,73],[60,23],[50,40]):
        found,_=mapped(mesh,point)
        assert np.max(np.abs(found-(np.array(point)+[-13,7])))<1e-12
    assert determinants(mesh)==[1.0]*8
    folded=dict(mesh,vertices=[v[:] for v in mesh["vertices"]])
    folded["vertices"][1]=[-90,7]
    assert min(determinants(folded))<0

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("geometry",type=Path,nargs="?")
    parser.add_argument("--out",type=Path)
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    self_test()
    if args.self_test:
        print("geometry observer: shifted-border/interior/triangle and folded-Jacobian controls passed")
        if args.geometry is None:return
    if args.geometry is None or args.out is None:parser.error("geometry and --out required")
    raw=args.geometry.read_bytes();envelope=json.loads(raw)
    payload=envelope["payload"];report=payload["report"]
    meshes=payload["meshes"];global_meshes=payload["original_view_meshes"]
    count=len(meshes);assert count==report["pass_count"]==len(global_meshes)
    accepted=[r for r in report["native_receipts"] if r["accepted"]]
    fits=[r for r in accepted if r["candidate"]["role"]=="fit"]
    matrix=[];rhs=[]
    for r in fits:
        c=r["candidate"];row=np.zeros(count-1)
        if c["pass_a"]:row[c["pass_a"]-1]-=1
        if c["pass_b"]:row[c["pass_b"]-1]+=1
        matrix.append(row);rhs.append(np.array(c["point_a_quad"])-r["refined_b_quad"])
    matrix=np.array(matrix);rhs=np.array(rhs)
    assert len(matrix)>=count-1 and np.linalg.matrix_rank(matrix)==count-1
    offsets=np.vstack(([0.,0.],np.linalg.lstsq(matrix,rhs,rcond=None)[0]))
    details=[]
    for r in accepted:
        c=r["candidate"];a,b=c["pass_a"],c["pass_b"]
        pa,pb=np.array(c["point_a_quad"]),np.array(r["refined_b_quad"])
        ma,cell_a=mapped(meshes[a],pa);mb,cell_b=mapped(meshes[b],pb)
        ga,_=mapped(global_meshes[a],pa);gb,_=mapped(global_meshes[b],pb)
        qualified=all(meshes[p]["visibility"][cell]=="validated_overlap" for p,cell in ((a,cell_a),(b,cell_b)))
        details.append({"id":c["id"],"role":c["role"],"passes":[a,b],"sources":[c["source_a"],c["source_b"]],"cells":[cell_a,cell_b],"qualified_both":qualified,
                        "local_mesh_error_quad":float(np.linalg.norm(ma-mb)),"global_similarity_error_quad":float(np.linalg.norm(ga-gb)),"translation_error_quad":float(np.linalg.norm(pa+offsets[a]-pb-offsets[b]))})
    summaries={}
    for role in ("fit","heldout"):
        for scope in ("all","qualified_both"):
            rows=[r for r in details if r["role"]==role and (scope=="all" or r["qualified_both"])]
            summaries[role+"_"+scope]={name:statistics([r[name+"_error_quad"] for r in rows]) for name in ("local_mesh","global_similarity","translation")}
    per_pass=[]
    for i,mesh in enumerate(meshes):
        dets=determinants(mesh);census=Counter(mesh["visibility"])
        assert census["validated_overlap"]==report["qualified_join_cells"][i]
        per_pass.append({"pass":i,"source_quad":mesh["source"],"visibility":dict(census),"minimum_jacobian":min(dets),"nonpositive_triangles":sum(v<=0 for v in dets),"vertices":len(mesh["vertices"]),"triangles":len(dets)})
    w,h=report["canvas_size_quad"]
    output={"schema":"strehl.mosaic-author-geometry-crosscheck.v1","input_sha256":hashlib.sha256(raw).hexdigest(),"payload_binding":envelope["payload_sha256"],"coordinate_gauge":"pass-zero anchor, native green-quad pixels; multiply errors by2 for sensor pixels","canvas_origin_quad":report["canvas_origin_quad"],"canvas_size_quad":[w,h],"canvas_area_over_largest_source":w*h/max(m["source"][0]*m["source"][1] for m in meshes),"translation_offsets_quad":offsets.tolist(),"per_pass":per_pass,"errors":summaries,"observations":details,"limits":"Author arithmetic cross-check, not independent research review. Local fitted error can be lowered by flexibility; heldouts and spatial qualification must be read separately. Union canvas area alone does not establish observed extended coverage. Constant translation is one pass pose, not a per-frame error truth. No pixel/color/sharpness quality inferred."}
    with args.out.open("x") as stream:json.dump(output,stream,indent=2);stream.write("\n")
    print(json.dumps({"per_pass":per_pass,"errors":summaries},indent=2))

if __name__=="__main__":main()
