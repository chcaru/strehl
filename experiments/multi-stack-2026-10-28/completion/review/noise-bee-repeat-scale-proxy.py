"""Nomination-only scale uncertainty proxies from the frozen bee native graph."""
import argparse,hashlib,itertools,json,math,struct
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('alignment',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args();assert not a.output.exists()
b=a.alignment.read_bytes();d=json.loads(b);r=d['report'];assert r['frames']==32
f=lambda bits:struct.unpack('<d',struct.pack('<Q',bits))[0]
q=lambda x,p:sorted(x)[max(0,math.ceil(p*len(x))-1)]
edges={};incident=[[]for _ in range(32)];cycles=[[]for _ in range(32)]
for e in r['edges']:
 if e['stage']!='native' or not e['accepted']:continue
 i,j=e['i'],e['j'];assert i<j
 rms,lever=e['rms_plane_px'],e['lever_plane_px'];assert math.isfinite(rms) and math.isfinite(lever) and lever>0
 g=math.log(math.hypot(f(e['transform_bits'][0]),f(e['transform_bits'][1])))
 edges[i,j]={'log_scale':g,'ratio':rms/lever,'rms_plane_px':rms,'lever_plane_px':lever}
 incident[i].append(rms/lever);incident[j].append(rms/lever)
triangles=[]
for i,j,k in itertools.combinations(range(32),3):
 if (i,j) in edges and (j,k) in edges and (i,k) in edges:
  z=abs(edges[i,j]['log_scale']+edges[j,k]['log_scale']-edges[i,k]['log_scale']);triangles.append({'nodes':[i,j,k],'absolute_log_scale_cycle':z})
  for n in [i,j,k]:cycles[n].append(z)
scale={}
for line in d['warpmap'].splitlines():
 s=line.split()
 if len(s)>=6 and s[0].isdigit() and s[1]=='placed':scale[int(s[0])]=math.log(math.hypot(f(int(s[2],16)),f(int(s[3],16))))
rows=[]
for i in range(32):
 valid=len(incident[i])>=3 and len(cycles[i])>=1
 rows.append({'global_index':i,'pass':int(i>=16),'incident_native_edges':len(incident[i]),'incident_triangles':len(cycles[i]),'log_scale':scale[i],'rms_over_lever_q75':q(incident[i],.75) if incident[i] else None,'cycle_log_scale_q95':q(cycles[i],.95) if cycles[i] else None,'proxy':q(incident[i],.75)+q(cycles[i],.95) if valid else None})
old={x['allowed_log_scale_gap']for x in r['focus_candidates']};assert len(old)==1;old=old.pop();nominations=[]
for i in range(16):
 for j in range(16,32):
  radius=max(old,rows[i]['proxy']+rows[j]['proxy']) if rows[i]['proxy'] is not None and rows[j]['proxy'] is not None else None
  gap=abs(scale[i]-scale[j]);direct=(i,j)in edges
  nominations.append({'i':i,'j':j,'scale_gap':gap,'proposal_radius':radius,'within_proxy':radius is not None and gap<=radius,'direct_native_edge_available':direct,'nomination_only':direct and radius is not None and gap<=radius,'cost_fixedpoint':round(1e6*(gap/radius)**2) if radius else None})
a.output.write_text(json.dumps({'schema':'strehl.bee-scale-proxy-nomination.v1','alignment_sha256':hashlib.sha256(b).hexdigest(),'command':['python',__file__,str(a.alignment),str(a.output)],'quantiles':'nearest rank ceil(p*n), no sqrt(edge/tile count)','scope':'Nomination proxy only, NOT calibrated scale uncertainty, consuming geometry certificate, PSF or compatibility. Triangles share edges. No RAW/cache/source pixels read.','old_radius':old,'sources':rows,'triangles':triangles,'nominations':nominations},indent=2)+'\n',encoding='utf-8')
print('available',sum(r['proxy'] is not None for r in rows),'proxy range',min(r['proxy']for r in rows),max(r['proxy']for r in rows),'triangles',len(triangles),'within',sum(x['within_proxy']for x in nominations),'direct nominated',sum(x['nomination_only']for x in nominations))
