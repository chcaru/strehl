"""Prospective geometry-only square-distance-map counts; no radiance evaluated."""
from pathlib import Path
import sys
import time

import numpy as np

from model import primary_scene, primary_frames, sha256, write_json
from render import gauss, native_mask, triangle_area, triangle_rule, integrator_for, cell_triangles


def polygons(xy, n, offset, radius):
    x, y = xy
    pieces = [[(np.array(q), frozenset()) for q in ((x-.5,y-.5),(x+.5,y-.5),(x+.5,y+.5),(x-.5,y+.5))]]
    cuts = [(offset, "focus")]
    if radius:
        cuts.extend(((offset-radius, "minus"), (offset+radius, "plus")))
    for cut, label in sorted(cuts):
        next_pieces = []
        for poly in pieces:
            poly = [(q, tags | {label} if np.dot(q,n)-cut == 0 else tags) for q,tags in poly]
            distances = [np.dot(q,n)-cut for q,_ in poly]
            if not min(distances) < 0 < max(distances):
                next_pieces.append(poly)
                continue
            for positive in (True, False):
                child=[]
                for (a,ta),(b,tb) in zip(poly,poly[1:]+poly[:1]):
                    ha,hb=np.dot(a,n)-cut,np.dot(b,n)-cut
                    ia,ib=(ha>=0,hb>=0) if positive else (ha<=0,hb<=0)
                    if ia: child.append((a,ta))
                    if ia!=ib: child.append((a+(b-a)*(ha/(ha-hb)),(ta&tb)|{label}))
                next_pieces.append(child)
        pieces=next_pieces
    return pieces


def provenance_classified_triangles(xy,n,offset,radius):
    result=[]
    for poly in polygons(xy,n,offset,radius):
        for i in range(1,len(poly)-1):
            items=(poly[0],poly[i],poly[i+1])
            triangle=np.array([q for q,_ in items])
            if triangle_area(triangle)==0: continue
            labels=set().union(*(tags for _,tags in items)) & {"minus","plus"}
            assert len(labels)<=1
            indices=[] if not labels else [j for j,(_,tags) in enumerate(items) if next(iter(labels)) in tags]
            assert len(indices)<3
            result.append((triangle,indices))
    return result


def classified_triangles(xy,n,offset,radius):
    result=[]
    for triangle in cell_triangles(scene,frame,xy):
        indices=[]
        if radius:
            h=triangle@n-offset
            tau=64*np.finfo(float).eps*(abs(n[0]*triangle[:,0])+abs(n[1]*triangle[:,1])+abs(offset)+radius)
            alternatives=[]
            for sign in (-1,1):
                distances=abs(h-sign*radius)
                candidates=[j for j in range(3) if distances[j]<=tau[j]]
                if candidates:
                    ranked=sorted(candidates,key=lambda j:(distances[j],tuple(triangle[j])))
                    alternatives.append((float(distances[ranked[0]]),sign,ranked[:2]))
            if alternatives:
                indices=min(alternatives,key=lambda value:(value[0],value[1]))[2]
        result.append((triangle,indices))
    return result


def points(triangle,indices,order):
    if not indices: return triangle_rule(triangle,order)[0]
    nodes,_=gauss(order)
    t,u=np.meshgrid(nodes,nodes,indexing="ij")
    r=t*t
    if len(indices)==2:
        a,b=sorted((triangle[j] for j in indices),key=lambda p:tuple(p))
        c=triangle[next(j for j in range(3) if j not in indices)]
        return ((1-r)[...,None]*((1-u)[...,None]*a+u[...,None]*b)+r[...,None]*c).reshape(-1,2)
    c=triangle[indices[0]]
    a,b=sorted((triangle[j] for j in range(3) if j not in indices),key=lambda p:tuple(p))
    return ((1-r)[...,None]*c+r[...,None]*((1-u)[...,None]*a+u[...,None]*b)).reshape(-1,2)


out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
scene=primary_scene();records=[];started=time.monotonic()
for arm in ("primary","angle-refined","cell-refined"):
    config=integrator_for(arm)
    for frame in primary_frames():
        n,offset=native_mask(scene,frame)
        radius=abs(frame.defocus(scene)[0])*np.linalg.norm(n)
        point_count=interval_count=max_intervals=0
        kinds={"none":0,"vertex":0,"edge":0}
        for y in range(48):
            for x in range(64):
                for tri,indices in classified_triangles((x,y),n,offset,radius):
                    kinds[("none","vertex","edge")[len(indices)]]+=1
                    for order in (config.cell_low,config.cell_high):
                        xy=points(tri,indices,order)
                        q=frame.forward_similarity.inverse(xy)
                        h=np.abs(q[:,0]*scene.mask_normal[0]+q[:,1]*scene.mask_normal[1]-scene.mask_offset)
                        partial=h<radius if radius else np.zeros(len(h),dtype=bool)
                        counts=np.where(partial&(h>0),4,np.where(partial,2,1))
                        if radius:
                            eta=h/radius
                            for j in range(1,33): counts+=2*((eta>0)&(eta<2.**-j))
                        point_count+=len(h);interval_count+=int(counts.sum());max_intervals=max(max_intervals,int(counts.max()))
        nodes=interval_count*(config.angle_low+config.angle_high)
        item=dict(arm=arm,frame=frame.index,triangle_kinds=kinds,nominal_point_calls=point_count,
                  nominal_intervals=interval_count,max_intervals_per_point=max_intervals,nominal_angular_nodes=nodes,
                  angular_ceiling_remaining=600_000_000-nodes)
        records.append(item);print(item,flush=True)
write_json(out/'result.json',dict(schema="m194e-prospective-cell-work-v1",status="DERIVED_GEOMETRY_ONLY",classification="bounded-predicate",argv=sys.argv,records=records,
           calculation_wall_seconds=time.monotonic()-started,sources={name:sha256(Path(__file__).parent/name) for name in ('model.py','render.py','cell-amendment-work-count.py')}))
