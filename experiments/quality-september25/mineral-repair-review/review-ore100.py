"""Independent delivery/source-binding audit and fixed native views; no RAW access."""
from pathlib import Path
import hashlib,json,re
import numpy as np
import tifffile
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def ref(p):
    with p.open('rb') as f:return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def rgb(p):
    with tifffile.TiffFile(p) as f:
        assert len(f.pages)==1
        v=f.asarray();icc=bytes(f.pages[0].tags[34675].value)
    assert v.dtype==np.uint16 and v.ndim==3 and v.shape[2]==3 and icc
    return v,icc
def effective(command):
    args=command[3:];keep={};i=0
    while i<len(args):
        item=args[i]
        if item in ('--srgb','--demosaic'):keep[item]=True;i+=1
        elif item.startswith('--exposure='):keep['--exposure']=float(item.split('=',1)[1]);i+=1
        else:
            value=args[i+1];i+=2
            if item!='--out':keep[item]=float(value) if item=='--exposure' else value
    keep.setdefault('--exposure',0.0)
    return keep
def main():
    out=HERE/'ore100-views-1';assert not out.exists();out.mkdir()
    inventory=ROOT/'experiments/quality-september25/minerals/inventory.json'
    frozen=ROOT/'experiments/quality-september25/minerals/native-tiles.json'
    results=[]
    for code,name,old_base,variant in [
        ('100','ore-100','outputs/peacock-ore/100msdcf','')]:
        old=next(r for r in read(inventory) if r['code']==code)
        before_path=Path(old['master']);assert ref(before_path)['sha256']==old['sha256']
        delivery=ROOT/'outputs/quality-september25'/name;done=read(delivery/'completion.json')
        after_path=delivery/'stack-master.tiff';assert ref(after_path)==done['master']
        base=ROOT/old_base;historical=base/variant
        historic_done=read(historical/'completion.json');assert ref(before_path)['sha256']==historic_done['master']['sha256']
        old_order=read(base/'input-order.json');new_order=read(delivery/'input-order.json')
        ordered=lambda rows:[(r['index'],Path(r['path']).name,r['bytes'],r['sha256']) for r in rows]
        assert ordered(old_order)==ordered(new_order) and len(new_order)==old['frames']==done['frames']
        assert [r['index'] for r in new_order]==list(range(old['frames']))
        inv=read(delivery/'invocation.json');old_inv=read(historical/'invocation.json')
        old_command=old_inv['command'] if 'command' in old_inv else next(v for k,v in old_inv['commands'] if k=='render')
        new_command=next(v for k,v in inv['commands'] if k=='render')
        assert effective(old_command)==effective(new_command)
        held_env={k:v for k,v in old_inv['environment'].items() if k!='STREHL_GPU_GATHER_LOG'}
        assert all(inv['environment'][k]==v for k,v in held_env.items())
        extras={k:v for k,v in inv['environment'].items() if k not in old_inv['environment']}
        assert extras=={'STREHL_FINE_SUPPORT':'off','STREHL_CA_BEFORE_MHC':'off'}
        assert inv['executable']==done['executable']==ref(Path(done['executable']['path']))
        assert done['executable']['sha256']=='bec4c357836ad1383800a6c933460ee7ef072c525b5957a6f5deb5194b203314'
        warp=Path(inv['environment']['STREHL_WARPMAP']);assert ref(warp)==done['warp_map']==inv['existing_map']
        lines=warp.read_text().splitlines();rows=[s.split() for s in lines if s and s.split()[0].isdigit()]
        assert len(rows)==old['frames'] and all(r[1]=='placed' for r in rows)
        reference=int(next(s.split()[1] for s in lines if s.startswith('reference ')))
        assert reference==old['frames']//2
        before,icc=rgb(before_path);after,after_icc=rgb(after_path)
        assert before.shape==after.shape==tuple(old['output_shape']) and icc==after_icc
        assert done['crop_quad_xywh']==old['crop_quad_xywh'] and done['native_dimensions']==[before.shape[1],before.shape[0]]
        process=read(delivery/'render-process.json')
        assert process['exit_code']==0 and process['error'] is None and process['terminal_job_accounting'] and not process['cleanup_errors']
        assert done['original_bytes_and_metadata_unchanged'] and historic_done['source_metadata_and_content_unchanged']
        root_run=ROOT/'experiments/garnet-spatial-trace'/'ore100-delivery-1'
        root_compare=read(root_run/'comparison.json')
        targets=[dict(name='largest-change',roi=root_compare['diagnostic_crop_native_xywh'],independently_selected=False)]
        for record in read(frozen):
            if Path(record['path']).name.startswith(code+'-'):
                assert ref(Path(record['path']))['sha256']==record['sha256']
                targets.append(dict(name=Path(record['path']).stem.removeprefix(code+'-').removesuffix('-native384'),
                    roi=record['output_native_xywh'],independently_selected=True,witness=record['path']))
        view_rows=[]
        for target in targets:
            x,y,w,h=target['roi'];assert w==h==384
            for arm,data in [('before',before),('corrected',after)]:
                patch=((data[y:y+h,x:x+w].astype(np.uint32)+128)//257).astype(np.uint8)
                dest=out/f'{code}-{arm}-{target["name"]}.png';Image.fromarray(patch).save(dest,icc_profile=icc)
                if target['name']=='largest-change':
                    with Image.open(root_run/f'{arm}-largest-change-native.png') as known:assert np.array_equal(np.array(known),patch)
                elif arm=='before':
                    with Image.open(target['witness']) as known:assert np.array_equal(np.array(known),patch)
                view_rows.append(dict(arm=arm,target=target['name'],native_xywh=target['roi'],file=ref(dest),independent_target=target['independently_selected']))
        tone=[]
        for folder in (historical,delivery):
            text=(folder/'render.log').read_text(encoding='utf-8',errors='replace')
            match=re.findall(r'^tone\s*:\s*(.*)$',text,re.M);assert len(match)==1;tone.append(match[0])
        results.append(dict(code=code,frames=old['frames'],ordered_source_name_bytes_hashes_exact=True,
            source_reads=0,original_hash_scope='Prior and new producer manifests compared; reviewer opened no RAW files.',
            old_root_path_changed=any(a['path']!=b['path'] for a,b in zip(old_order,new_order)),
            effective_command_settings=effective(new_command),held_environment_exact=True,explicit_new_off_fields=extras,
            gpu_log_change=[old_inv['environment']['STREHL_GPU_GATHER_LOG'],inv['environment']['STREHL_GPU_GATHER_LOG']],
            crop=done['crop_quad_xywh'],reference=reference,warp=ref(warp),master_before=ref(before_path),master_after=ref(after_path),
            exact_dimensions_and_icc=True,icc_sha256=hashlib.sha256(icc).hexdigest(),tone_log_before_after=tone,
            inputs=[ref(inventory),ref(frozen),ref(base/'input-order.json'),ref(delivery/'input-order.json'),ref(historical/'invocation.json'),
                    ref(delivery/'invocation.json'),ref(delivery/'completion.json'),ref(historical/'completion.json'),ref(root_run/'comparison.json')],
            views=view_rows,quality_verdict=None))
    (HERE/'ore100-evidence.json').write_text(json.dumps(dict(script=ref(Path(__file__).resolve()),results=results),indent=2)+'\n',encoding='utf-8')
    print('Independent delivery bindings and6 native views verified; no RAW sources opened.')
if __name__=='__main__':main()
