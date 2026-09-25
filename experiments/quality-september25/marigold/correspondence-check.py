"""Small witness-correspondence diagnostic, not a placement-truth metric."""
from pathlib import Path
import hashlib, json
import numpy as np
import cv2

OUT=Path(__file__).resolve().parent
SRC=OUT/'adjacent'
REGIONS={'fan':(60,115,155,110),'rim':(60,80,180,160)}
def hp(a):
 return cv2.GaussianBlur(a,(0,0),.8)-cv2.GaussianBlur(a,(0,0),8)
def locate(a,b,rect):
 x,y,w,h=rect; t=hp(a)[y:y+h,x:x+w]; v=hp(b)
 if np.std(t)<1e-3 or np.std(v)<1e-3:return {'valid':False}
 corr=cv2.matchTemplate(v,t,cv2.TM_CCOEFF_NORMED)
 _,score,_,pos=cv2.minMaxLoc(corr)
 return {'valid':True,'ncc':score,'quad_shift':[pos[0]-x,pos[1]-y]}

results={'command':'python -I -B -X faulthandler experiments/quality-september25/marigold/correspondence-check.py',
 'reference_original':112,'render_reference':244,'units':'CFA-plane pixels in existing reference244 map gauge',
 'rejecting_inputs':'Flat input must be invalid; known translation must be recovered. Disagreement under blur exposes defocus bias. This is correspondence, not ground-truth registration: defocus, shape change, and multiple hairs can shift or invalidate the match.',
 'template_choice':'Fixed rectangles selected on original112, not independently fitted for each pair. These cover hair groups that remain recognizable through the five adjacent sampled originals.',
 'controls':{},'regions':{},'inputs':[]}
for name,rect in REGIONS.items():
 a=np.load(SRC/f'source-112-{name}-gr.npy')
 shifted=cv2.warpAffine(a,np.float32([[1,0,6],[0,1,-4]]),(a.shape[1],a.shape[0]),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
 flat=np.full_like(a,2000)
 zero=locate(a,a,rect);plant=locate(a,shifted,rect);null=locate(flat,flat,rect)
 blur=locate(a,cv2.GaussianBlur(a,(0,0),1.5),rect)
 assert zero['quad_shift']==[0,0] and zero['ncc']>.999
 assert plant['quad_shift']==[6,-4] and plant['ncc']>.99
 assert not null['valid']
 results['controls'][name]={'identity':zero,'known_translation':plant,'flat':null,'synthetic_blur':blur}
 results['regions'][name]={'template_rect_quad_within_crop':rect,'measurements':[]}
 for idx in [104,108,112,116,120]:
  p=SRC/f'source-{idx:03}-{name}-gr.npy'; b=np.load(p)
  results['regions'][name]['measurements'].append({'index':idx,**locate(a,b,rect)})
  results['inputs'].append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(OUT/'correspondence-check.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({k:results[k] for k in ['controls','regions']},indent=2))
