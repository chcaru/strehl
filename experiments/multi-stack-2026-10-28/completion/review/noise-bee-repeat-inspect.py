"""Frozen witness export, one common transform from untouched linear masters."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
import tifffile

ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'outputs/multi-stack/completion/noise-bee-repeat-01'
BLACK=0.00033
WHITE=0.38858

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4<<20),b''):h.update(block)
    return h.hexdigest()

def display(x):
    z=np.clip((x.astype(np.float32)-BLACK)/(WHITE-BLACK),0,1)
    z=np.where(z<=0.0031308,12.92*z,1.055*np.power(z,1/2.4)-0.055)
    return np.rint(np.clip(z,0,1)*255).astype(np.uint8)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('arm',choices=['pass-a','pass-b','equal','precision']);args=parser.parse_args()
    arm=BASE/args.arm;out=BASE/'inspection'/args.arm;out.mkdir(parents=True,exist_ok=False)
    protocol=json.loads((BASE/'inputs/protocol.json').read_text(encoding='utf-8'))
    alignment=json.loads((BASE/'alignment.json').read_text(encoding='utf-8'))
    report=json.loads((arm/'render-report.json').read_text(encoding='utf-8'))
    full=alignment['report']['geometry_plane_pixels'];canvas=report['canvas']
    master=tifffile.memmap(arm/'master.tiff');assert master.dtype==np.float32 and master.shape==(2*canvas[3],2*canvas[2],3)
    # A fixed whole-scene reduction is only orientation; native crops below
    # retain exact384displaypixels. Numeric measurements must read float TIFF.
    overview=Image.fromarray(display(master[::4,::4]));overview.thumbnail((1600,1200),Image.Resampling.LANCZOS);overview.save(out/'overview.png')
    rows=[]
    for witness in protocol['witnesses']:
        x,y=[int(np.floor(f*2*n-192)) for f,n in zip(witness['active_fraction_center'],full)]
        x=max(0,min(2*full[0]-384,x));y=max(0,min(2*full[1]-384,y))
        xx,yy=x-2*canvas[0],y-2*canvas[1]
        assert xx>=0 and yy>=0 and xx+384<=master.shape[1] and yy+384<=master.shape[0]
        crop=np.asarray(master[yy:yy+384,xx:xx+384]);assert crop.shape==(384,384,3)
        image_path=out/f'{witness["id"]}.png';Image.fromarray(display(crop)).save(image_path)
        rows.append({'id':witness['id'],'origin_full_sensor':[x,y],'origin_output_sensor':[xx,yy],
                     'dimensions':[384,384],'display_sha256':sha(image_path),
                     'linear_float32_sha256':hashlib.sha256(crop.tobytes()).hexdigest(),
                     'linear_min':float(crop.min()),'linear_max':float(crop.max())})
    receipt={'schema':'strehl.noise-bee-repeat-inspection.v1','arm':args.arm,'source_master':str((arm/'master.tiff').relative_to(ROOT)),
             'source_master_sha256':sha(arm/'master.tiff'),'dimensions':[master.shape[1],master.shape[0]],
             'display':{'source':'float32BT709linear-master','black':BLACK,'white':WHITE,'transfer':'sRGB','origin':'Fixed from passA log before combined outputs; identical for everyarm. No contrast/adaptive/autorange.'},
             'overview':'orientationonly1:4subsample+fit','witnesses':rows,'render_groups':report['proposed_groups'],
             'invalid_output_pixels':report['invalid_output_pixels']}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'arm':args.arm,'groups':len(report['proposed_groups']),'two_source_groups':sum(len(x)==2 for x in report['proposed_groups']),'invalid':report['invalid_output_pixels'],'witnesses':len(rows)}))

if __name__=='__main__':main()
