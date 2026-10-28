"""Copy frozen native crops from the released common-display PNG; no resampling."""
import hashlib,json,sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
label=sys.argv[1] if len(sys.argv)>1 else 'insect-repeat-4'
source=Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/'outputs/multi-stack/independent-review'/label
mapping=HERE/'roi-mapped-frozen.json'
roi=json.loads(mapping.read_text())
readback=json.loads((source/'readback.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(source/'complete-fixed-display.png')==readback['complete_display_sha256']
assert readback['transform_file_sha256']==sha(ROOT/'outputs/multi-stack/independent-review/fixed-transform.json')
canvas=json.loads((ROOT/'outputs/multi-stack'/label/'render-report.json').read_text())['canvas']
alignment=json.loads((ROOT/'outputs/multi-stack'/label/'alignment.json').read_text())
assert canvas==roi['candidate_canvas_plane_pixels']
assert hashlib.sha256(alignment['warpmap'].encode()).hexdigest()==roi['candidate_warpmap_sha256']
dest=HERE/'native-crops'/label
dest.mkdir(parents=True,exist_ok=True)
records=[]
with Image.open(source/'complete-fixed-display.png') as image:
    image.load()
    assert list(image.size)==roi['candidate_native_dimensions'] and image.mode=='RGB'
    icc=image.info.get('icc_profile')
    assert hashlib.sha256(icc).hexdigest()=='238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b'
    for item in roi['rois']:
        x,y=item['origins']['shared-candidate-gauge']; n=item['size']
        crop=image.crop((x,y,x+n,y+n))
        output=dest/(item['name']+'.png')
        crop.save(output,icc_profile=icc)
        with Image.open(output) as check:
            assert check.size==(n,n) and check.tobytes()==crop.tobytes()
        records.append({'name':item['name'],'origin':[x,y],'size':[n,n],'file':str(output),'sha256':sha(output),'pixel_sha256':hashlib.sha256(crop.tobytes()).hexdigest()})
receipt={'schema':'strehl.independent-native-crops.v1','command':sys.argv,'helper_sha256':sha(Path(__file__)),'mapping_sha256':sha(mapping),'source_complete_png_sha256':sha(source/'complete-fixed-display.png'),'transform_file_sha256':readback['transform_file_sha256'],'canvas_verified':canvas,'warpmap_sha256_verified':roi['candidate_warpmap_sha256'],'operation':'Integer native PNG pixel slices only; no resizing or tone edits; complete PNG was produced with baseline-frozen transform. Readback pixels exact.','crops':records}
(dest/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'label':label,'crops':len(records),'destination':str(dest),'receipt_sha256':sha(dest/'receipt.json')},indent=2))
