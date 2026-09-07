"""Independent actual TIFF metadata mutations; no production/scorer edits."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

HERE=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def add_tag(blob,tag,type_,count,value):
    order='<' if blob[:2]==b'II' else '>' if blob[:2]==b'MM' else None
    if order is None or struct.unpack_from(order+'H',blob,2)[0]!=42:
        raise ValueError('expected classic TIFF')
    offset=struct.unpack_from(order+'I',blob,4)[0]
    n=struct.unpack_from(order+'H',blob,offset)[0]
    entries=[blob[offset+2+12*i:offset+14+12*i] for i in range(n)]
    if any(struct.unpack_from(order+'H',e)[0]==tag for e in entries):
        raise ValueError('tag already present; do not silently replace it')
    if struct.unpack_from(order+'I',blob,offset+2+12*n)[0]!=0:
        raise ValueError('more than one IFD')
    value_field=(struct.pack(order+'H',value)+b'\0\0') if type_==3 else value
    if len(value_field)!=4:
        raise ValueError('inline value required')
    entries.append(struct.pack(order+'HHI',tag,type_,count)+value_field)
    entries.sort(key=lambda e:struct.unpack_from(order+'H',e)[0])
    result=bytearray(blob)
    if len(result)%2:
        result+=b'\0'
    new_offset=len(result)
    result+=struct.pack(order+'H',len(entries))+b''.join(entries)+struct.pack(order+'I',0)
    struct.pack_into(order+'I',result,4,new_offset)
    return bytes(result)


def replace_description(blob):
    order='<' if blob[:2]==b'II' else '>'
    offset=struct.unpack_from(order+'I',blob,4)[0]
    n=struct.unpack_from(order+'H',blob,offset)[0]
    for i in range(n):
        pos=offset+2+12*i
        tag,type_,count,value=struct.unpack_from(order+'HHII',blob,pos)
        if tag==270:
            replacement=b'Standard sRGB encoded image. No white balance applied.\0'
            if type_!=2 or count<len(replacement) or count<=4:
                raise ValueError('unexpected original description layout')
            result=bytearray(blob)
            result[value:value+count]=replacement+b'\0'*(count-len(replacement))
            return bytes(result)
    raise ValueError('original writer description missing')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--receipt',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    receipt=json.loads(args.receipt.read_text())
    original=Path(receipt['output']['path'])
    if sha(original)!=receipt['output']['sha256']:
        raise ValueError('actual consumer TIFF binding changed')
    before=sha(original)
    spec=importlib.util.spec_from_file_location('root_score',HERE/'score.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    args.out.mkdir(parents=True,exist_ok=False)
    original_pixels,_=module.read_tiff(original)
    payload=original.read_bytes()
    rows=[]
    for name,blob in [('unchanged-copy',payload),('orientation-eight',add_tag(payload,274,3,1,8)),
                      ('unexpected-icc',add_tag(payload,34675,7,4,b'BAD!')),
                      ('wrong-color-description',replace_description(payload))]:
        file=args.out/(name+'.tif')
        file.write_bytes(blob)
        try:
            pixels,info=module.read_tiff(file)
            row={'name':name,'admitted':True,'same_numerical_pixels':bool((pixels==original_pixels).all()),
                 'sha256':sha(file),'reader_metadata':info}
        except Exception as exc:
            row={'name':name,'admitted':False,'exception':repr(exc),'sha256':sha(file)}
        row['expected_admitted']=name=='unchanged-copy'
        row['correct_disposition']=row['admitted']==row['expected_admitted']
        rows.append(row)
    result={'scope':'actual TIFF reader orientation/profile admission; no benchmark launched',
        'reader_sha256':sha(HERE/'score.py'),'receipt_sha256':sha(args.receipt),
        'source_tiff_sha256':before,'source_unchanged':sha(original)==before,'cases':rows,
        'pass':all(r['correct_disposition'] for r in rows)}
    (args.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
