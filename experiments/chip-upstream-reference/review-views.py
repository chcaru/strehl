"""Whole-first independent viewing; integer semantic counterparts, no registration."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import tifffile
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
CURRENT=ROOT/'experiments/chip-focus-intercept/native-full-1/output/baseline.tiff'
TARGETS=ROOT/'experiments/chip-stock-selectivity/targets.json'


def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def ref(p):
    p=Path(p).resolve()
    with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
    return dict(path=str(p),bytes=p.stat().st_size,sha256=h)


def completed(run):
    data=read(run/'output.json');process=read(run/'process.json')
    assert data['complete_299_source_reference'] and data['prepared_inputs_unchanged']
    assert process['exit_code']==0 and process['error'] is None and process['terminal_job_accounting'] and not process['cleanup_errors']
    for key in ('master','native_whole','overview'):
        row=data['views'][key];assert ref(row['path'])==row
    return data


def load(path,expected_dtype):
    with tifffile.TiffFile(path) as f:
        assert len(f.pages)==1
        page=f.pages[0];pixels=page.asarray()
        assert pixels.ndim==3 and pixels.shape[2]==3 and pixels.dtype==expected_dtype
        profile=bytes(page.tags[34675].value) if 34675 in page.tags else None
    display=((pixels.astype(np.uint32)+128)//257).astype(np.uint8) if pixels.dtype==np.uint16 else pixels
    return display,profile


def whole(run,out):
    stock=completed(run)  # Never inspect an in-progress candidate.
    out.mkdir(exist_ok=False)
    current,icc=load(CURRENT,np.uint16);assert current.shape==(4332,6500,3) and icc
    image=Image.fromarray(current,'RGB');image.save(out/'current-whole.png',icc_profile=icc)
    image.thumbnail((1800,1800),Image.Resampling.LANCZOS);image.save(out/'current-overview.png',icc_profile=icc)
    save(out/'whole-receipt.json',dict(current=ref(CURRENT),stock_output=ref(run/'output.json'),
        targets=ref(TARGETS),current_whole=ref(out/'current-whole.png'),current_overview=ref(out/'current-overview.png'),
        stock_views=stock['views'],viewer=ref(__file__),
        scope='Whole workflow comparison; stock8bit independent geometry versus Current16bit native RAW; no tone/colour matching'))
    (out/'images.md').write_text('\n\n'.join([
        '# Complete chip photographs',
        f'[Current RGB16 TIFF]({CURRENT.as_posix()})',
        f'[Current complete native PNG]({(out/"current-whole.png").as_posix()})',
        f'![Current whole photograph]({(out/"current-overview.png").as_posix()})',
        f'[Stock upstream8bit TIFF]({Path(stock["views"]["master"]["path"]).as_posix()})',
        f'[Stock complete native PNG]({Path(stock["views"]["native_whole"]["path"]).as_posix()})',
        f'![Stock whole photograph]({Path(stock["views"]["overview"]["path"]).as_posix()})',
        'Current display is rounded RGB16/257 with its embedded ICC. Stock pixels are unchanged8bit and remain untagged if its TIFF omits ICC. Only overviews are resized.'])+'\n',encoding='utf-8')


def tiles(run,out,coordinates):
    stock=completed(run);whole_receipt=read(out/'whole-receipt.json')
    assert whole_receipt['current']==ref(CURRENT) and whole_receipt['targets']==ref(TARGETS)
    assert whole_receipt['stock_output']==ref(run/'output.json')
    plan=read(coordinates);targets=read(TARGETS)['regions']
    assert plan['chosen_from_whole_views_before_native_inspection'] is True
    assert [r['name'] for r in plan['regions']]==[r['name'] for r in targets]
    stage=out/'native';stage.mkdir(exist_ok=False)
    current,cicc=load(CURRENT,np.uint16);candidate,sicc=load(stock['views']['master']['path'],np.uint8)
    records=[]
    for target,selected in zip(targets,plan['regions']):
        name=target['name'];x,y,w,h=target['native_xywh'];assert w==h and w in (384,512)
        origin=selected['stock_region_xy'];assert selected['correspondence_note']
        if origin is not None:assert len(origin)==2 and all(isinstance(v,int) for v in origin)
        edge=384 if w==384 else 256
        offsets=[(0,0)] if w==384 else [(0,0),(256,0),(0,256),(256,256)]
        cb=Image.new('RGB',(w,h));sb=Image.new('RGB',(w,h))
        for number,(dx,dy) in enumerate(offsets):
            c=current[y+dy:y+dy+edge,x+dx:x+dx+edge];assert c.shape==(edge,edge,3)
            cp=stage/f'current-{name}-{number}.png';ci=Image.fromarray(c,'RGB');ci.save(cp,icc_profile=cicc);cb.paste(ci,(dx,dy))
            row=dict(name=name,tile=number,current_xywh=[x+dx,y+dy,edge,edge],current=ref(cp),stock=None)
            if origin is not None:
                sx,sy=origin[0]+dx,origin[1]+dy
                assert 0<=sx and 0<=sy and sx+edge<=candidate.shape[1] and sy+edge<=candidate.shape[0]
                s=candidate[sy:sy+edge,sx:sx+edge]
                sp=stage/f'stock-{name}-{number}.png';si=Image.fromarray(s,'RGB');si.save(sp,**({'icc_profile':sicc} if sicc else {}));sb.paste(si,(dx,dy))
                row.update(stock_xywh=[sx,sy,edge,edge],stock=ref(sp))
            records.append(row)
        cb.save(stage/f'current-{name}-board.png',icc_profile=cicc)
        if origin is not None:sb.save(stage/f'stock-{name}-board.png',**({'icc_profile':sicc} if sicc else {}))
    save(stage/'receipt.json',dict(coordinates=ref(coordinates),whole_receipt=ref(out/'whole-receipt.json'),
        viewer=ref(__file__),tiles=records,regions=len(targets),resampling=False,
        scope='Manual semantic counterpart origins; no pixel correspondence, automatic registration or scalar quality metric'))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=('whole','tiles'))
    p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--coordinates',type=Path)
    a=p.parse_args();run=a.run.resolve();out=a.out.resolve();assert run.parent==HERE and out.parent==HERE
    if a.phase=='whole':whole(run,out)
    else:
        assert a.coordinates is not None
        tiles(run,out,a.coordinates.resolve())


if __name__=='__main__':main()
