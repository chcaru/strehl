"""Independent saved native Crop consumer, source-only until explicit root release.
No producer functions are imported. Entry-point transport uses existing bounded
saved stage records; independent modules own all decode/arithmetic/choice logic.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import sys
import time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
SIDES=(128,64,32,16,8)
NONE=2**32-1
COUNTS=(5,22,5,5,2,2,2,5,2)
MODES=('on','on','off','placebo','on','off','placebo','absent','absent')
BASES=(0,5,0,0,5,5,5,0,5)
ORIGINALS=tuple('D:/personal/macro/requests/10-paper-iso-var/DSC%05d.ARW'%i for i in range(235,240))+tuple(
    'D:/personal/macro/requests/6-11-extended-dark-frames/DSC%05d.ARW'%i for i in range(872,894))
UNSET=('STREHL_GATE_FLOOR','STREHL_GATE_FLOOR_SCALE','STREHL_PYRAMID_MEAN_COARSE',
       'STREHL_PYRAMID_SIGNIFICANCE','STREHL_PYRAMID_WEIGHT_DUMP','STREHL_HULL',
       'STREHL_FIX_CA','STREHL_DEFECT','STREHL_DEFECT_MAP','STREHL_DEFECT_ARM','STREHL_DEFECT_HOT_FLOOR',
       'STREHL_RESTORE','STREHL_CONFIDENCE_DEBUG')
PROTOCOL_SHA='e3c527d2d012e56877dd1b5992237191fb988eed957234664a37fab781585ec4'
DESIGN_SHA='a68987a11679835034699454e8c5bf669b8c4da336b9e1685feb057aa810e6f0'


def need(test,reason):
    if not test:
        raise ValueError(reason)


def integer(value,low,high,reason):
    need(type(value) is int and low<=value<=high,reason)
    return value


def finite(value,reason):
    need(type(value) in (int,float) and math.isfinite(value),reason)
    return float(value)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value,reason='SHA256 string'):
    need(type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None,reason)
    return value


def closed(value,keys,reason):
    need(type(value) is dict and set(value)==set(keys),reason)
    return value


def metadata_json(raw):
    def pairs(items):
        out={}
        for key,value in items:
            need(key not in out,'duplicate JSON key'); out[key]=value
        return out
    return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,
                      parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite JSON constant')))


def canonical_path(value):
    need(type(value) is str and value and len(value)<=512 and value.isascii() and
         not any(ord(c)<32 for c in value),'local path spelling')
    # Only ordinary local drive and their exact verbatim drive equivalent are admitted.
    original=value
    value=value.replace('/',chr(92))
    if value.startswith(chr(92)*2+'?'+chr(92)):
        value=value[4:]
    elif re.match(r'^[A-Za-z]:',value) is None:
        need(not value.startswith(chr(92)), 'relative repository artifact path')
        pieces=value.split(chr(92))
        need(all(p and p not in ('.','..') and ':' not in p and not p.endswith((' ','.')) for p in pieces),
             'unsupported local path component')
        value=str(REPO.joinpath(*pieces))
    need(re.match(r'^[A-Za-z]:',value) is not None and len(value)>3 and value[2]==chr(92), 'local drive path required')
    tail=value[3:].split(chr(92))
    need(all(p and p not in ('.','..') and ':' not in p and not p.endswith((' ','.')) for p in tail),
         'unsupported local path component')
    return os.path.normcase(value)


def ref_shape(ref,*,empty=False):
    closed(ref,('path','bytes','sha256'),'FileRef keys')
    canonical_path(ref['path'])
    integer(ref['bytes'],0 if empty else 1,2**40,'FileRef extent')
    digest(ref['sha256'])
    return ref


def same_ref(left,right,*,empty=False):
    ref_shape(left,empty=empty); ref_shape(right,empty=empty)
    need(canonical_path(left['path'])==canonical_path(right['path']) and
         left['bytes']==right['bytes'] and left['sha256']==right['sha256'], 'FileRef association')
    return True


def role_ref(ref,path,empty=False):
    ref_shape(ref,empty=empty)
    need(canonical_path(ref['path'])==canonical_path(str(path)),'fixed saved artifact role path')
    return ref


def source_model(metadata,n):
    need(metadata['camera']=='ILCE-7CM2' and type(metadata['iso_bits']) is int and
         metadata['iso_bits']==n.bits(160),'native camera ISO')
    need(metadata['buffer']==[7168,5120] and metadata['active']==[0,0,7032,4688] and
         all(type(x) is int for x in metadata['buffer']+metadata['active']),'native active raw domain')
    need(metadata['model']=='profile::noise_model_for','native model constructor')
    levels=metadata['levels_bits']; models=metadata['model_planes']
    need(type(levels) is list and len(levels)==2 and type(models) is list and len(models)==4,
         'native model record shape')
    black,white=[n.from_bits(v) for v in levels]
    need(math.isfinite(black) and 0<=black<white and white==15360,'native black white')
    need(all(type(row) is list and len(row)==4 and row[2:]==levels for row in models),'per-plane levels association')
    gains=[n.from_bits(row[0]) for row in models]; rn=[n.from_bits(row[1]) for row in models]
    n.model_admit(gains,rn)
    need(type(metadata['wb_coeff_bits']) is list and len(metadata['wb_coeff_bits'])==4,'native WB four words')
    for v in metadata['wb_coeff_bits']: integer(v,0,2**32-1,'native WB word')
    return black,white,gains,rn


def frame_identity(row,invocation,index,route):
    expected={'schema':'native-sensor-transfer-frame-v1','invocation':invocation,'index':index,
              'original_ordinal':BASES[invocation]+index,'route':route,'observer':MODES[invocation],
              'folded':True,'feature':invocation<7}
    for key,value in expected.items():
        need(type(row.get(key)) is type(value) and row[key]==value,'fixed native frame identity')
    need(row['floor_array']=='not-stored; threshold derived from exact operands' and
         row['scalar_context_provenance']=='DERIVED_FROM_ACTUAL_CONFIG_AND_PREFIX','derived floor/scalar label')
    return True


def tiff_dimensions(raw):
    need(type(raw) is bytes and 8<=len(raw)<=512*1024,'native TIFF extent')
    need(raw[:2] in (b'II',b'MM'),'native TIFF byte order')
    endian='<' if raw[:2]==b'II' else '>'
    u16=lambda at:struct.unpack_from(endian+'H',raw,at)[0]
    u32=lambda at:struct.unpack_from(endian+'I',raw,at)[0]
    need(u16(2)==42,'native classic TIFF')
    start=u32(4); need(8<=start<=len(raw)-2,'native TIFF IFD offset')
    count=u16(start); need(1<=count<=64 and start+2+12*count+4<=len(raw),'native TIFF IFD extent')
    fields={}
    for i in range(count):
        at=start+2+12*i; tag=u16(at); kind=u16(at+2); n=u32(at+4)
        need(tag not in fields,'native TIFF duplicate tag')
        if tag in (256,257,258,259,262,273,277,278,279,284,339):
            need(kind in (3,4) and 1<=n<=256,'native TIFF integer tag shape')
            size=n*(2 if kind==3 else 4); offset=at+8 if size<=4 else u32(at+8)
            need(0<=offset<=len(raw)-size,'native TIFF integer tag range')
            fields[tag]=list(struct.unpack_from(endian+str(n)+('H' if kind==3 else 'I'),raw,offset))
    need(u32(start+2+12*count)==0,'native TIFF multiple pages')
    need(fields.get(256)==[256] and fields.get(257)==[256] and fields.get(258)==[16,16,16] and
         fields.get(259)==[1] and fields.get(262)==[2] and fields.get(277)==[3] and
         fields.get(284,[1])==[1] and fields.get(339,[1,1,1])==[1,1,1], 'native TIFF RGB16 shape')
    offsets,extents=fields.get(273),fields.get(279)
    need(type(offsets) is list and type(extents) is list and len(offsets)==len(extents) and
         all(0<e<=len(raw) and 0<=o<=len(raw)-e for o,e in zip(offsets,extents)) and
         sum(extents)==256*256*6,'native TIFF strip extents')
    spans=sorted(zip(offsets,extents))
    need(all(a+an<=b for (a,an),(b,_) in zip(spans,spans[1:])),'native TIFF overlapping strips')
    return {'width':256,'height':256,'channels':3,'bits':16,'strips':len(offsets),
            'scope':'independent container/address extent; actual writer source and whole-byte witnesses separately bound'}


class Consumer:
    def __init__(self,np,n,d,io,original_refs):
        self.np,self.n,self.d,self.io=np,n,d,io
        self.original_refs=original_refs
        self.originals={}; self.primary={}; self.on={}; self.frames=[]; self.outputs={}
        self.first_actual_weight=None

    def catalog(self,traversals):
        # Metadata only. Authenticate every actual immutable frame record before RAW controls/decode.
        self.traversals=traversals
        for invocation,t in enumerate(traversals):
            count=COUNTS[invocation]
            need(t['schema']=='native-sensor-transfer-traversal-v1' and t['status']=='COMPLETE_NATIVE_CROP_TRAVERSAL',
                 'native traversal completion')
            for key,value in (('invocation',invocation),('observer',MODES[invocation]),('feature',invocation<7),
                              ('native_decodes',count),('source_handoffs',2*count),('folds',2*count),
                              ('expected_real_fullres_warps',count),('expected_synthetic_probe_warps',count),
                              ('retained_map_record_count',8*count if MODES[invocation] in ('on','placebo') else 0),
                              ('expected_map_callback_visits',8*count if invocation<7 else 0),
                              ('configured_bands',7)):
                need(type(t[key]) is type(value) and t[key]==value,'fixed traversal population')
            need(t['shape']==[128,128] and t['crop']==[1694,1108,128,128] and t['actual_sides']==list(SIDES),
                 'fixed native Crop geometry')
            partition=t['partition']; need(type(partition) is list and len(partition)==4,'native partition tuple')
            for p in partition:integer(p,1,2**40,'native partition integer')
            _,chunks,per_chunk,execution=partition
            need(chunks<=count and per_chunk==(count+chunks-1)//chunks and execution<=min(4,count),'native chunk topology')
            env=t['environment']
            need(env=={'unset':list(UNSET),'fullres':'current-default-on',
                       'execution_threads':{'name':'STREHL_PYRAMID_WORKERS','value':'4'},
                       'defect':'current-default-none','ca':'current-default-gear-guarded','restoration':False},
                 'native environment declaration')
            need(type(t['frames']) is list and len(t['frames'])==2*count and len(t['outputs'])==2,'native record population')
            for index in range(count):
                for route in range(2):
                    ref=t['frames'][2*index+route]
                    role_ref(ref,HERE/f'native-run-{invocation}'/f'frame-{index:02}-route-{route}.json')
                    row=self.io.json(ref,64*1024)
                    frame_identity(row,invocation,index,route)
                    metadata=row['source_metadata']; original=BASES[invocation]+index
                    same_ref(metadata['source'],self.original_refs[original])
                    need(canonical_path(metadata['path'])==canonical_path(ORIGINALS[original]),'native original path')
                    source_model(metadata,self.n)
                    need(type(metadata['original_rows_sha256']) is list and len(metadata['original_rows_sha256'])==256,
                         'native original row population')
                    for h in metadata['original_rows_sha256']:digest(h)
                    original_ref=metadata['original_roi'];role_ref(original_ref,HERE/f'native-run-{invocation}'/f'frame-{index:02}-original.u16')
                    need(original_ref['bytes']==131072,'original ROI extent')
                    if original not in self.primary:
                        self.primary[original]=metadata
                    else:
                        baseline=self.primary[original]
                        for key in ('source','original_rows_sha256','camera','iso_bits','buffer','active','levels_bits',
                                    'wb_coeff_bits','model','model_planes'):
                            if key=='source':same_ref(metadata[key],baseline[key])
                            else:need(metadata[key]==baseline[key],'repeated original metadata changed')
                        need(original_ref['bytes']==baseline['original_roi']['bytes'] and
                             original_ref['sha256']==baseline['original_roi']['sha256'],'repeated original ROI changed')
                    self.frames.append((ref,row,per_chunk))
        need(set(self.primary)==set(range(27)),'all27 original metadata')
        return {'invocations':9,'native_decodes':50,'folds':100,'real_warps_source_expected':50,
                'probe_warps_source_expected':50,'compact_white_pyramids_source_expected':288,
                'scope':'warp/startup counts derived from source and completed traversal; not independent call timers'}

    def independent_decode(self,rawpy):
        observations=[];self.decode_observations=observations;self.decode_attempts=0
        for ordinal,ref in enumerate(self.original_refs):
            self.io.tick()
            encoded=self.io.read(ref,38825984)
            self.decode_attempts+=1
            owned,observation=self.d.decode_snapshot(encoded,rawpy,self.np,self.primary[ordinal],self.n)
            del encoded
            source=self.primary[ordinal]
            native=self.io.read(source['original_roi'],131072)
            comparison=self.d.compare_roi(owned,native,source['original_rows_sha256'],self.np)
            self.originals[ordinal]=owned
            observations.append({'ordinal':ordinal,'source':ref,'decode':observation,
                                 'same_file_comparison':{k:v for k,v in comparison.items() if k!='row_sha256'}})
            self.io.tick()
        need(len(observations)==27,'independent decode population')
        return observations

    def map_records(self,row):
        n=self.n; route=row['route']; mode=row['observer']; maps=row['gather_site_records']
        need(type(maps) is list and len(maps)==(8 if route==1 and mode in ('on','placebo') else 0),
             'actual map callback population')
        green_identity=True
        for i,m in enumerate(maps):
            need(type(m['dx']) is int and type(m['dy']) is int and (m['dx'],m['dy'])==((i%4)%2,(i%4)//2) and
                 m['warp_kind']==('real' if i<4 else 'synthetic-probe'),'actual map callback order')
            need(type(m['similarity_bits']) is list and len(m['similarity_bits'])==4 and
                 all(type(v) is int and 0<=v<2**64 for v in m['similarity_bits']), 'actual map binary64 fields')
            need(type(m['wb_gain_bits']) is list and len(m['wb_gain_bits'])==3,'actual map WB fields')
            if mode=='placebo':
                need(m['path']=='PLACEBO' and m['similarity_bits']==[0]*4 and m['wb_gain_bits']==[0]*3 and
                     all(m[k] is None for k in ('model','lens_type3','profile_key','profile_debug')),'map placebo shape')
            else:
                need(canonical_path(m['path'])==canonical_path(row['source_metadata']['path']),'resolved map source path')
                need(m['model']=='ILCE-7CM2' and (m['lens_type3'] is None or type(m['lens_type3']) is int),
                     'resolved map camera lens metadata')
                for v in m['wb_gain_bits']:need(math.isfinite(n.from_bits(v)) and n.from_bits(v)>0,'resolved map WB positive')
                actual=[struct.unpack('<d',struct.pack('<Q',v))[0] for v in m['similarity_bits']]
                need(all(math.isfinite(v) for v in actual),'resolved map finite transform')
                if i in (1,2): green_identity &= actual==[1.,0.,0.,0.]
                # R/B transforms and profile debug are retained, never forced to geometric identity.
        return {'records':maps,'green_effective_identity':green_identity if route==1 and mode=='on' else None,
                'scope':'actual resolved t_site callback; CA profile metadata is provenance, not fitted geometry truth'}

    def frame_arrays(self,row,per_chunk):
        np,n,d=self.np,self.n,self.d
        inv,index,route,mode=row['invocation'],row['index'],row['route'],row['observer']
        original=row['original_ordinal']; raw=self.originals[original]
        black,white,gains,rn=source_model(row['source_metadata'],n)
        # Every retained original buffer, including repeated decode occurrences, is authenticated.
        original_bytes=self.io.read(row['source_metadata']['original_roi'],131072)
        d.compare_roi(raw,original_bytes,row['source_metadata']['original_rows_sha256'],np)
        maps=self.map_records(row)
        if mode=='absent':
            need(row['inputs'] is None and row['variance_after_sha256'] is None and
                 row['prepared_roi'] is None and row['trace'] is None,'feature-off unavailable observer fields')
            return {'identity':[inv,index,route],'mode':mode,'maps':maps,'arithmetic':'unobserved-feature-off'}
        inputs=row['inputs']
        closed(inputs,('plane_sha256','luma_sha256','variance_before_sha256','beta_bits'),'native CLI input keys')
        need(type(inputs['plane_sha256']) is list and len(inputs['plane_sha256'])==4,'native plane hash population')
        for h in [*inputs['plane_sha256'],inputs['luma_sha256'],inputs['variance_before_sha256'],row['variance_after_sha256']]:digest(h)
        need(inputs['variance_before_sha256']==row['variance_after_sha256'],'supplied variance changed after fold')
        prefix=[n.from_bits(v) for v in inputs['beta_bits']]
        need(len(prefix)==route*3 and all(math.isfinite(v) and v>=0 for v in prefix),'actual supplied beta prefix')
        if mode=='off':
            need(row['trace'] is None and row['prepared_roi'] is None,'off observer arrays absent')
            return {'identity':[inv,index,route],'mode':mode,'maps':maps,'inputs':inputs,'arithmetic':'hash-witness-only'}
        role_ref(row['prepared_roi'],HERE/f'native-run-{inv}'/f'frame-{index:02}-route-{route}-prepared.u16')
        role_ref(row['trace'],HERE/f'native-run-{inv}'/f'frame-{index:02}-route-{route}.trace')
        prepared_bytes=self.io.read(row['prepared_roi'],131072)
        need(len(prepared_bytes)==131072,'prepared ROI exact extent')
        trace_bytes=self.io.read(row['trace'],2*1024**2)
        fields=d.trace_decode(trace_bytes,route,mode,np)
        if mode=='placebo':
            need(prepared_bytes==bytes(131072),'placebo prepared zeros')
            return {'identity':[inv,index,route],'mode':mode,'maps':maps,'inputs':inputs,
                    'arithmetic':'placebo zeros; common actual hashes compared separately'}
        prepared=np.frombuffer(prepared_bytes,dtype='<u2').reshape(256,256).copy()
        if route==0:need(prepared_bytes==raw.astype('<u2',copy=False).tobytes(),'no-map prepared/original disagreement')
        arrays=d.trace_arrays(fields,np)
        cfg=[index%per_chunk,7,4,n.bits(2),n.bits(2),n.bits(1.4),0,n.bits(2),0,3,n.bits(4),1,n.bits(0),0,0,0,0,0]
        need(fields[1,NONE,NONE].tolist()==cfg,'actual trace configured defaults/chunk frame')
        need(fields[2,NONE,NONE].tolist()==inputs['beta_bits'],'CLI/core supplied beta identity')
        planes,luma=n.extract(prepared,black); variance=n.native_variance(luma,gains,rn)
        for p in range(4):
            n.bit_equal(arrays[100+p,0,NONE],planes[p],'consumed CFA extraction disagreement')
            need(sha(planes[p].astype('<f4',copy=False).tobytes())==inputs['plane_sha256'][p], 'actual input plane hash')
        for tag,value,key in ((104,luma,'luma_sha256'),(105,variance,'variance_before_sha256')):
            n.bit_equal(arrays[tag,0,NONE],value,'consumed luma/variance disagreement')
            need(sha(value.astype('<f4',copy=False).tobytes())==inputs[key],'actual input scalar hash')
        _,luma_pyramid=n.pyramid(luma); variance_pyramid=n.pyramid(variance)[0]
        coefficients=[n.pyramid(p)[1] for p in planes]
        band_rows=[]
        for k,side in enumerate(SIDES):
            self.io.tick()
            n.bit_equal(arrays[10,k,NONE],luma_pyramid[k],'actual luma pyramid disagreement')
            n.bit_equal(arrays[11,k,NONE],variance_pyramid[k],'actual Gaussian variance disagreement')
            for p in range(4):n.bit_equal(arrays[20,k,p],coefficients[p][k],'actual consumed plane coefficients disagreement')
            context=fields[3,k,NONE].tolist()
            if k==4:
                need(context==[1,1,0,0,0,0,0,0,0],'actual base bypass context')
                n.bit_equal(arrays[13,k,NONE],np.zeros((8,8),dtype=np.float32),'BaseMean zero admission weight')
                band_rows.append({'band':4,'kind':'base-mean-bypass','sites':64})
                continue
            selected,white_beta,gate,p,significance,r_floor=[n.from_bits(v) for v in context[3:]]
            need(context[:2]==[0,0] and context[2] in (0,1),'actual Laplacian bypass context')
            n.beta_admit(route,prefix,k,bool(context[2]),selected,white_beta)
            need(n.bits(gate)==n.bits(2) and n.bits(p)==n.bits(n.exponent(k)) and
                 n.bits(significance)==0 and n.bits(r_floor)==0,'actual per-band default scalars')
            n.bit_equal(arrays[12,k,NONE],n.energy(luma_pyramid[k]),'actual smoothed squared energy disagreement')
            checked=n.weights_check(arrays[12,k,NONE],arrays[11,k,NONE],arrays[13,k,NONE],selected,gate,p)
            if self.first_actual_weight is None:
                self.first_actual_weight=(float(arrays[12,k,NONE][0,0]),float(arrays[11,k,NONE][0,0]),
                                          float(arrays[13,k,NONE][0,0]),selected,gate,p)
            strata=[]
            for name,mask in n.support(k):
                strata.append({'stratum':name,'sites':int(mask.sum()),'actual_E':n.summarize(arrays[12,k,NONE],mask),
                               'actual_V':n.summarize(arrays[11,k,NONE],mask),'actual_weight':n.summarize(arrays[13,k,NONE],mask),
                               'derived_floor':n.summarize(checked['floor'],mask),
                               'derived_above':int(checked['above'][mask].sum())})
            band_rows.append({'band':k,'derived_selected_beta_bits':context[3],'derived_white_beta_bits':context[4],
                              'selected_source':'supplied-measured-prefix' if context[2] else 'white-fallback',
                              'derived_effective_exponent_bits':context[6],
                              'classification':{key:value for key,value in checked.items() if key not in ('floor','above')},
                              'strata':strata,'scope':'floor/threshold-side DERIVED; recorded E/V/W actual'})
        green_equal=bool(np.array_equal(prepared[0::2,1::2],raw[0::2,1::2]) and
                         np.array_equal(prepared[1::2,0::2],raw[1::2,0::2]))
        value={'prepared':prepared,'planes':planes,'luma':luma,'variance':variance,'arrays':arrays,
               'fields':fields,'black':black,'white':white,'gains':gains,'rn':rn,'maps':maps,
               'green_code_equal':green_equal,'inputs':inputs,'bands':band_rows}
        key=(route,original)
        if key in self.on:
            previous=self.on[key]
            need(previous['inputs']==inputs and previous['prepared'].tobytes()==prepared.tobytes(),
                 'repeated primary/prefix observed input changed')
        else:self.on[key]=value
        return {'identity':[inv,index,route],'mode':mode,'maps':maps,'inputs':inputs,'bands':band_rows,
                'green_original_code_equal':green_equal,'arithmetic':'all retained source operands checked'}

    def saved_arrays(self):
        rows=[];self.frame_observations=rows;self.frame_attempts=0
        for _,row,per_chunk in self.frames:
            self.io.tick();self.frame_attempts+=1;rows.append(self.frame_arrays(row,per_chunk))
        # Off/placebo mandatory hashes are compared to the actual on record for each same source and route.
        for row in rows:
            inv,index,route=row['identity']
            if row['mode'] in ('off','placebo'):
                need(row['inputs']==self.on[route,BASES[inv]+index]['inputs'],'observer common input hash/beta identity')
        output_rows=[]
        for inv,t in enumerate(self.traversals):
            for route,out in enumerate(t['outputs']):
                self.io.tick()
                need(out['dimensions']==[256,256] and out['writer']=='write_merged/Merged::Bands' and
                     out['space']=='CameraLinear' and out['demosaic'] is True and out['exposure']=='None' and
                     out['restore'] is None,'actual native writer settings')
                primary=self.primary[BASES[inv]]
                need(out['levels_bits']==primary['levels_bits'],'native writer levels')
                wb=[self.n.from_bits(v) for v in primary['wb_coeff_bits'][:3]]
                expected_wb=([self.n.bits(self.n.f32(wb[0]/wb[1])),self.n.bits(1),self.n.bits(self.n.f32(wb[2]/wb[1]))]
                             if all(math.isfinite(v) and v>0 for v in wb) else None)
                need(out['wb_gain_bits']==expected_wb,'native writer optional WB branch')
                role_ref(out['collapsed'],HERE/f'native-run-{inv}'/f'route-{route}-collapsed.f32')
                role_ref(out['tiff'],HERE/f'native-run-{inv}'/f'route-{route}-native.tiff')
                collapsed=self.io.read(out['collapsed'],262144); need(len(collapsed)==262144,'collapsed exact extent')
                values=self.np.frombuffer(collapsed,dtype='<f4')
                need(bool(self.np.isfinite(values).all()),'collapsed finite output')
                tiff=self.io.read(out['tiff'],512*1024); layout=tiff_dimensions(tiff)
                self.outputs[inv,route]={'collapsed':collapsed,'tiff':tiff}
                output_rows.append({'invocation':inv,'route':route,'collapsed':out['collapsed'],'tiff':out['tiff'],
                                    'layout':layout,'settings':{k:v for k,v in out.items() if k not in ('collapsed','tiff')}})
        witnesses=[]
        for name,invocations in (('paper-five',(0,2,3,7)),('dark-first-two',(4,5,6,8))):
            for route in range(2):
                witnesses.append((name+f'-route{route}',[self.outputs[i,route] for i in invocations]))
        return rows,output_rows,witnesses

    def temporal_record(self,name,values,spatial=True):
        n=self.n; t=n.temporal(values)
        result={'frames':len(values),'all_df':t['all_df'],'pair_df':t['pair_df'],
                'mean':n.summarize(t['mean']),'all_variance':n.summarize(t['all_variance']),
                'pair_variance':n.summarize(t['pair_variance']),
                'pair_rms_sigma':math.sqrt(float(t['pair_variance'].mean())),
                'pair_components':[n.summarize(v) for v in t['pair_components']],
                'ordered_frame_means':[float(v.mean()) for v in values],
                'frame_mean_scope':'same-crop drift observations; never subtracted or screened with paper rules for dark',
                'arrays':{key:self.io.array(name+'-'+key,t[key]) for key in
                          ('pair_variance','pair_components')},
                'scope':'Full pair-Q/components retained; mean/all-T variance in complete-crop/16-block summaries and fixed scalar witnesses. Spatial summaries do not multiply temporal degrees of freedom.'}
        if spatial:
            result['blocks']={'ordered_frames':[n.blocks(v) for v in values],'mean':n.blocks(t['mean']),'all_variance':n.blocks(t['all_variance']),
                              'pair_variance':n.blocks(t['pair_variance']),
                              'pair_components':[n.blocks(v) for v in t['pair_components']]}
        return result,t

    def covariance_record(self,values):
        n,np=self.n,self.np
        cross=[]; neighbours=[]
        for pa,pb in ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3)):
            pair,all_t,rho,ok=n.covariance(values[:,pa],values[:,pb])
            cross.append({'planes':[pa,pb],'paired_covariance_dn2':n.summarize(pair),
                          'all_T_covariance_dn2':n.summarize(all_t),'pair_blocks':n.blocks(pair),
                          'all_T_blocks':n.blocks(all_t),
                          'rho':n.summarize(rho[ok]) if bool(ok.any()) else {'count':0,'mean':None,'min':None,'max':None},
                          'rho_unavailable_count':int((~ok).sum())})
        for p in range(4):
            for dx,dy in ((1,0),(0,1),(1,1),(1,-1)):
                left,right=n.overlap(values[:,p],values[:,p],dx,dy)
                pair,all_t,rho,ok=n.covariance(left,right)
                neighbours.append({'plane':p,'dx':dx,'dy':dy,'sites':pair.size,
                                   'paired_covariance_dn2':n.summarize(pair),'all_T_covariance_dn2':n.summarize(all_t),
                                   'rho':n.summarize(rho[ok]) if bool(ok.any()) else {'count':0,'mean':None,'min':None,'max':None},
                                   'rho_unavailable_count':int((~ok).sum()),
                                   'scope':'both endpoints use exact same overlapping rectangle'})
        return {'cross_planes':cross,'neighbours':neighbours,'full_spatial_covariance_model':'not identified'}

    def block_statistics(self,block,route,paper_nuisance):
        np,n=self.np,self.n
        ordinals=list(range(5)) if block=='paper' else list(range(5,27))
        records=[self.on[route,i] for i in ordinals]
        blacks=[v['black'] for v in records]; gains=records[0]['gains']; rn=records[0]['rn']
        need(len(set(blacks))==1 and all(v['gains']==gains and v['rn']==rn for v in records),'block fixed native model/levels')
        black=blacks[0]; stem=block+f'-route{route}'
        signed=np.stack([n.signed_planes(v['prepared'],black) for v in records])
        clamped=np.stack([v['planes'] for v in records])
        signed_green=(signed[:,1]+signed[:,2])/2
        actual_green=np.stack([v['luma'] for v in records])
        paper=block=='paper'
        route_green_eligible=route==0 or all(v['maps']['green_effective_identity'] is True and v['green_code_equal'] for v in records)
        physical_eligible=route_green_eligible and (not paper or paper_nuisance['physical_paper_eligible'])
        result={'block':block,'route':route,'original_ordinals':ordinals,'frames':len(records),
                'model_gain_bits':[n.bits(g) for g in gains],'model_RN_e_bits':[n.bits(r) for r in rn],
                'black':black,'green_transform_eligible':route_green_eligible,
                'paper_input_premises':paper_nuisance if paper else 'not applied to dark',
                'physical_interpretation':'CONDITIONAL_ONLY' if physical_eligible else 'NOT_IDENTIFIED',
                'physical_model_pass':None,'profile_parameter_uncertainty':'unquantified',
                'scope':'one fixed opt-in128 CFA Crop; this block is not a sensor-wide calibration'}
        plane_rows=[]; signed_t=[]; clamped_t=[]
        for p in range(4):
            self.io.tick()
            sr,st=self.temporal_record(stem+f'-signed-p{p}',signed[:,p]); signed_t.append(st)
            cr,ct=self.temporal_record(stem+f'-clamped-p{p}',clamped[:,p]); clamped_t.append(ct)
            plane_rows.append({'plane':p,'signed':sr,'clamped':cr,
                               'clamp_count':int((signed[:,p]<0).sum()),'zero_or_negative_count':int((signed[:,p]<=0).sum()),
                               'observations':int(signed[:,p].size),
                               'clamped_to_signed_Q':n.ratio(float(ct['pair_variance'].mean()),float(st['pair_variance'].mean()))})
        result['planes']=plane_rows
        green_signed,gs=self.temporal_record(stem+'-signed-green',signed_green)
        green_actual,ga=self.temporal_record(stem+'-actual-green',actual_green)
        result['green']={'signed':green_signed,'actual_clamped':green_actual,
                         'clamped_to_signed_Q':n.ratio(float(ga['pair_variance'].mean()),float(gs['pair_variance'].mean()))}
        identities=[]
        for name,values,stats,target in (('signed',signed,signed_t,gs),('clamped',clamped,clamped_t,ga)):
            pc,ac,_,_=n.covariance(values[:,1],values[:,2])
            n.same_real(target['pair_variance'],(stats[1]['pair_variance']+stats[2]['pair_variance']+2*pc)/4,
                        'green paired covariance association')
            n.same_real(target['all_variance'],(stats[1]['all_variance']+stats[2]['all_variance']+2*ac)/4,
                        'green all-T covariance association')
            identities.append({'domain':name,'paired_and_all_T_equal':True,
                               'scope':'algebraic association, not independent calibration evidence'})
        result['green_covariance_identities']=identities
        result['signed_covariance']=self.covariance_record(signed)
        result['clamped_covariance']=self.covariance_record(clamped)
        q_planes=None; qgreen=None; q_uncertainty=None
        prediction_scope='unavailable'
        if paper and paper_nuisance['headroom_ok']:
            q_planes,qgreen,q_uncertainty,q_correlated=n.prediction(self.originals[4],black,gains,rn,{'original_ordinals':[4],'estimator':'single-held-frame4'})
            prediction_scope='disjoint original frame4 fixed diagonal sensor hypothesis; paper premises separately retained'
            result['prediction_reference']={'role':{'original_ordinals':[4],'estimator':'single-held-frame4'},'source':self.original_refs[4]}
            result['reference_uncertainty']={'qG_variance':self.io.array(stem+'-qG-reference-variance',q_uncertainty),
                'qG_fully_correlated_bound':self.io.array(stem+'-qG-reference-correlated-bound',q_correlated),
                'scope':'plug-in conditional model uncertainty; no profile uncertainty or combined exact coverage'}
        elif not paper:
            q_planes=np.stack([np.full((128,128),(gains[p]*rn[p])**2) for p in range(4)])
            qgreen=(q_planes[1]+q_planes[2])/4
            prediction_scope='negligible-signal old-profile read floor; PRECLAMP counterfactual only'
        result['prediction_scope']=prediction_scope
        if qgreen is not None:
            result['q_photosites']=self.io.array(stem+'-q-photosites',q_planes)
            result['q_green']=self.io.array(stem+'-q-green',qgreen)
            result['signed_sensor_ratios']=[{'plane':p,**n.ratio(float(signed_t[p]['pair_variance'].mean()),float(q_planes[p].mean())),
                'interpretation':'CONDITIONAL_ONLY' if route==0 and physical_eligible else 'NOT_IDENTIFIED',
                'scope':'route1 prepared photosites versus original sensor q are nonphysical comparators; R/B may be transformed'} for p in range(4)]
            result['signed_green_ratio']=n.ratio(float(gs['pair_variance'].mean()),float(qgreen.mean()))
            result['native_current_luma_coupling']=[{'original_ordinal':i,'actual_variance':n.summarize(v['variance']),
                'disjoint_qG':n.summarize(qgreen),'difference':n.summarize(v['variance'].astype(np.float64)-qgreen),
                'comparison_is_physical_prediction':paper and physical_eligible,
                'scope':'actual current-luma sqrt/square variance versus independent signal/read-floor comparator'}
                for i,v in zip(ordinals,records)]
        operators=n.independent_operators()
        predicted,smooth_predicted=(n.diagonal_prediction(qgreen,operators) if qgreen is not None else (None,None))
        gaussian_q=n.pyramid(qgreen,np.float64)[0] if qgreen is not None else None
        # Separate signed linear counterfactual from the actual postclamp consumer pyramid.
        signed_laps=[n.pyramid(v,np.float64)[1] for v in signed_green]
        band_rows=[]
        for k in range(4):
            self.io.tick()
            actual=np.stack([v['arrays'][10,k,NONE] for v in records])
            actual_record,at=self.temporal_record(stem+f'-L{k}',actual,spatial=k==0)
            linear=np.stack([v[k] for v in signed_laps]); linear_stats=n.temporal(linear)
            smooth_q=n.smooth(at['pair_variance'],np.float64)
            scene_energy=n.smooth(at['mean']*at['mean'],np.float64)
            row={'band':k,'side':SIDES[k],'actual_temporal':actual_record,
                 'smooth_Q':self.io.array(stem+f'-L{k}-smooth-Q',smooth_q),
                 'scene_energy':self.io.array(stem+f'-L{k}-mean-scene-energy',scene_energy),
                 'scene_energy_scope':'smooth5(square of temporal mean L); finite-repeat noise contamination remains; never subtracted',
                 'smooth_pair_components':self.io.array(stem+f'-L{k}-smooth-pairs',np.stack([n.smooth(v,np.float64) for v in at['pair_components']])),
                 'signed_linear_Q':self.io.array(stem+f'-signed-L{k}-Q',linear_stats['pair_variance']),
                 'actual_to_signed_linear_Q':n.ratio(float(at['pair_variance'].mean()),float(linear_stats['pair_variance'].mean())),
                 'strata':[],'signed_preclamp_predictor_eligible':physical_eligible,
                 'actual_postclamp_physical_predictor_eligible':paper and physical_eligible,
                 'dark_prediction_is_preclamp_counterfactual':not paper}
            if predicted is not None:
                row['B']=self.io.array(stem+f'-B{k}',predicted[k])
                row['smooth_B']=self.io.array(stem+f'-smooth-B{k}',smooth_predicted[k])
            for name,mask in n.support(k):
                summary={'name':name,'sites':int(mask.sum()),'actual_Q':n.summarize(at['pair_variance'],mask),
                         'signed_linear_Q':n.summarize(linear_stats['pair_variance'],mask),
                         'smooth_Q':n.summarize(smooth_q,mask),'mean_scene_energy':n.summarize(scene_energy,mask),
                         'pair_contributions':[n.summarize(v,mask) for v in at['pair_components']],
                         'smooth_pair_contributions':[n.summarize(n.smooth(v,np.float64),mask) for v in at['pair_components']]}
                if predicted is not None:
                    bmean=n.summarize(predicted[k],mask)['mean']; ebmean=n.summarize(smooth_predicted[k],mask)['mean']
                    summary.update(B=n.summarize(predicted[k],mask),smooth_B=n.summarize(smooth_predicted[k],mask),
                                   Q_over_B=n.ratio(summary['actual_Q']['mean'],bmean),
                                   smooth_Q_over_smooth_B=n.ratio(summary['smooth_Q']['mean'],ebmean))
                actual_rows=[]
                for original,v in zip(ordinals,records):
                    ctx=v['fields'][3,k,NONE].tolist(); selected=n.from_bits(ctx[3]); white_beta=n.from_bits(ctx[4])
                    actual_betaV=selected*v['arrays'][11,k,NONE].astype(np.float64)
                    item={'original':original,'derived_selected_beta_times_V_f64':n.summarize(actual_betaV,mask),
                          'scalar_product_scope':'DERIVED binary64 product of recorded beta/V; actual floor comparison used each f32 operation',
                          'actual_E':n.summarize(v['arrays'][12,k,NONE],mask),
                          'actual_weight':n.summarize(v['arrays'][13,k,NONE],mask),
                          'derived_selected_beta_bits':ctx[3],'derived_white_beta_bits':ctx[4]}
                    if predicted is not None:
                        white_term=white_beta*gaussian_q[k]
                        item.update(derived_white_beta_Gaussian_q_f64=n.summarize(white_term,mask),
                                    finite_operator_over_white_scalar=n.ratio(n.summarize(smooth_predicted[k],mask)['mean'],n.summarize(white_term,mask)['mean']),
                                    native_over_disjoint_white=n.ratio(n.summarize(actual_betaV,mask)['mean'],n.summarize(white_term,mask)['mean']))
                    actual_rows.append(item)
                summary['per_frame_comparators']=actual_rows
                row['strata'].append(summary)
            band_rows.append(row)
        result['bands']=band_rows
        scalar=[]
        # Signed sites are independent of clamp. Placed non-green photosites do not inherit a sensor prediction.
        for p,stats in enumerate([*signed_t,gs]):
            value=float(stats['pair_variance'][64,64]); all_value=float(stats['all_variance'][64,64])
            eligible=(route==0 or p==4 and route_green_eligible) and (not paper or paper_nuisance['physical_paper_eligible'])
            scalar.append({'kind':'signed-photosite' if p<4 else 'signed-green','plane':p,'xy':[64,64],
                           'eligible':eligible,'variance':value,
                           'pair_interval':n.variance_interval(value,stats['pair_df']) if eligible else None,
                           'all_T_sensitivity_interval':n.variance_interval(all_value,stats['all_df']) if eligible else None})
        for k,(x,y) in enumerate(((64,64),(32,32),(16,16))):
            linear=n.temporal(np.stack([v[k] for v in signed_laps]))
            value=float(linear['pair_variance'][y,x]); all_value=float(linear['all_variance'][y,x])
            eligible=physical_eligible
            item={'kind':'signed-linear-band','band':k,'xy':[x,y],'eligible':eligible,
                  'variance':value,'actual_clamped_interval':None,
                  'pair_interval':n.variance_interval(value,linear['pair_df'],'linear-band') if eligible else None,
                  'all_T_sensitivity_interval':n.variance_interval(all_value,linear['all_df'],'linear-band') if eligible else None,
                  'scope':'linear operator on signed values; actual postclamp coefficients receive no unconditional interval'}
            if paper and q_planes is not None:
                item['B_reference_uncertainty']=n.reference_uncertainty(q_planes,gains,k,x,y,operators)
                item['smooth_B_reference_uncertainty']=n.reference_uncertainty(q_planes,gains,k,x,y,operators,energy_scale=True)
            scalar.append(item)
        result['scalar_uncertainty']=scalar
        return result

    def statistics(self):
        raw=[self.originals[i] for i in range(5)]
        black=self.on[0,0]['black']; white=self.on[0,0]['white']
        nuisance=self.n.paper_nuisance(raw,black,white)
        results=[]
        for block in ('paper','dark'):
            for route in range(2):
                self.io.tick()
                result=self.block_statistics(block,route,nuisance)
                results.append(self.io.publish(block+f'-route{route}-result.json',result,1920*1024))
        return {'nuisance':nuisance,'block_route_results':results,'physical_model_pass':None,
                'scope':'conditional transfer diagnostic; no refit, scene registration, nuisance subtraction or calibration promotion'}


START=time.monotonic()
MIB=1024**2
BUNDLE_KEYS=('result','tail','outer','stdout','stderr','exit')
MODULES=('independent-numerics.py','independent-decode.py','independent-controls.py')
EXPECTED_VARIANTS=(4,3,9,4,4,20,5,8,3,29,6,3,6,5,6,9,1,13,13,24)
# Prospective root/factor stage ceilings. Owned children are also bounded by
# the remaining stage allowance; exact aggregate accounting is checked below.
STAGE_LIMITS={
    'build-on':{'cpu_seconds':600,'wall_seconds':300,'memory_bytes':3*1024*MIB,'child_cpu_seconds':600,'child_wall_seconds':300},
    'build-off':{'cpu_seconds':600,'wall_seconds':300,'memory_bytes':3*1024*MIB,'child_cpu_seconds':600,'child_wall_seconds':300},
    'controls':{'cpu_seconds':120,'wall_seconds':180,'memory_bytes':1024*MIB,'child_cpu_seconds':100,'child_wall_seconds':150},
    'native':{'cpu_seconds':1800,'wall_seconds':1200,'memory_bytes':2*1024*MIB,'child_cpu_seconds':1800,'child_wall_seconds':1200},
    'verify':{'cpu_seconds':1200,'wall_seconds':900,'memory_bytes':1024*MIB,'child_cpu_seconds':1000,'child_wall_seconds':850},
}


def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')


def source_pin(raw,pin):
    closed(pin,('bytes','sha256'),'source pin keys')
    integer(pin['bytes'],1,4*MIB,'source pin extent'); digest(pin['sha256'])
    need(len(raw)==pin['bytes'] and sha(raw)==pin['sha256'],'actual source bytes')
    return True


def original_population(refs):
    need(type(refs) is list and len(refs)==27,'fixed27 original population')
    for ref,path in zip(refs,ORIGINALS):
        ref_shape(ref)
        need(canonical_path(ref['path'])==canonical_path(path) and ref['bytes']<=38825984,'fixed original order/extent')
    need(sum(r['bytes'] for r in refs)==926855168,'fixed encoded original aggregate')
    return True


def stage_completion(value):
    need(value['status']=='COMPLETE_STAGE_UNVERIFIED' and value.get('error') is None and
         value.get('finalization_errors')==[],'saved stage not complete')
    return True


def shared_identity(s):
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)


def full_identity(s):
    return (*shared_identity(s),s.st_ctime_ns)


class IO:
    def __init__(self,limits,output):
        closed(limits,('cpu_seconds','wall_seconds','memory_bytes','read_bytes','write_bytes'),'reader limits keys')
        for key,value in limits.items():
            if key.endswith('_bytes'):integer(value,1,2**40,'reader byte limit')
            else:need(0<finite(value,'reader time limit')<=3600,'reader finite time range')
        need(limits['write_bytes']<=64*MIB and limits['memory_bytes']<=1024*MIB,'reader retained/owned memory bound')
        self.limits=limits;self.read_bytes=0;self.write_bytes=0;self.refs=[];self.outputs=[]
        self.output=Path(canonical_path(output));self.cache={};self.publishing=False
        need(self.output.parent.is_dir() and not self.output.exists(),'fresh independent output')
        need(self.output in (HERE/'controls-1'/'check',HERE/'verify-1'/'check'),'fixed independent output role')
        self.output.mkdir()
        self.tick()

    def tick(self,reserve=False):
        cpu=time.process_time();wall=time.monotonic()-START
        need(cpu+(1 if reserve or not self.publishing else 0)<=self.limits['cpu_seconds'] and
             wall+(2 if reserve or not self.publishing else 0)<=self.limits['wall_seconds'],'reader CPU/wall bound')
        need(self.read_bytes<=self.limits['read_bytes'] and self.write_bytes+(0 if self.publishing else 256*1024)<=self.limits['write_bytes'],
             'reader aggregate byte bound')

    def read(self,ref,cap,*,empty=False):
        self.tick();ref_shape(ref,empty=empty)
        need(ref['bytes']<=cap,'per-role file cap')
        path=Path(canonical_path(ref['path']))
        need(path.is_relative_to(REPO) or canonical_path(str(path)) in set(map(canonical_path,ORIGINALS)),
             'released repository/original read scope')
        for p in [path,*path.parents]:
            m=p.lstat()
            need(not stat.S_ISLNK(m.st_mode) and not getattr(m,'st_file_attributes',0)&0x400,'read reparse path')
        before=path.stat();need(stat.S_ISREG(before.st_mode),'read regular file')
        need(before.st_size==ref['bytes'],'actual file extent')
        need(self.read_bytes+ref['bytes']+1<=self.limits['read_bytes'],'prospective aggregate read cap')
        self.read_bytes+=ref['bytes']+1
        with path.open('rb') as stream:
            handle_before=os.fstat(stream.fileno())
            need(shared_identity(before)==shared_identity(handle_before),'path/handle shared read identity')
            raw=stream.read(ref['bytes']+1)
            handle_after=os.fstat(stream.fileno())
        after=path.stat()
        need(full_identity(before)==full_identity(after) and full_identity(handle_before)==full_identity(handle_after) and
             shared_identity(after)==shared_identity(handle_after),'read stable path/handle metadata')
        buffer_admit(raw,ref)
        self.refs.append(ref)
        self.tick()
        return raw

    def json(self,ref,cap):
        return metadata_json(self.read(ref,cap))

    def publish_raw(self,name,raw,cap):
        self.tick();need(type(raw) is bytes and len(raw)<=cap,'publication role extent')
        need(re.fullmatch('[a-z0-9][a-z0-9.-]*',name) is not None,'publication filename')
        path=self.output/name;need(not path.exists(),'fresh independent publication')
        need(self.write_bytes+len(raw)<=self.limits['write_bytes'],'prospective aggregate write cap')
        self.write_bytes+=len(raw)
        with path.open('xb') as stream:
            need(stream.write(raw)==len(raw),'complete independent publication')
            stream.flush();os.fsync(stream.fileno())
        ref={'path':str(path.relative_to(REPO)).replace(chr(92),'/'),'bytes':len(raw),'sha256':sha(raw)}
        self.outputs.append(ref);self.tick()
        return ref

    def publish(self,name,value,cap):
        return self.publish_raw(name,encoded(value),cap)

    def array(self,name,a):
        # Arrays are bounded before serialization. Actual values already finite-checked by arithmetic.
        need(a.ndim<=4 and a.size<=11*4*128*128 and a.dtype.kind=='f','fixed derived array extent/type')
        raw=a.astype('<f8',copy=False).tobytes(order='C')
        ref=self.publish_raw(name+'.f64',raw,6*MIB)
        return {'file':ref,'dtype':'float64-le','shape':list(a.shape),'order':'C'}

    def account(self):
        return {'cpu_sample_seconds':time.process_time(),'wall_sample_seconds':time.monotonic()-START,
                'read_bytes_charged':self.read_bytes,'write_bytes_charged':self.write_bytes,
                'publication_reserve':{'cpu_seconds':1,'wall_seconds':2},
                'memory_scope':'external owned Job; no in-process peak claim',
                'scope':'process-local samples before final publication; complete external accounting required'}


def terminal_child(io,ref,expected,index,stage,output):
    value=io.json(ref,32*1024)
    need(canonical_path(ref['path'])==canonical_path(str(output/f'child-{index:02}.json')),'fixed actual child record path')
    command=expected['command'] if type(expected) is dict else expected
    need(value['command']==command,'actual child command')
    log_ref=value['log'];need(canonical_path(log_ref['path'])==canonical_path(str(output/f'child-{index:02}.log')),
                              'fixed actual child log path')
    log=io.read(log_ref,16*MIB if stage.startswith('build-') else MIB,empty=True)
    need(type(value['log_bytes']) is int and value['log_bytes']==len(log),'actual child log extent')
    job=value['job_accounting'];need(type(job) is dict,'terminal child Job unavailable')
    components=[integer(job[k],0,2**63,'Job CPU integer100ns') for k in ('total_user_100ns','total_kernel_100ns','total_cpu_100ns')]
    need(components[0]+components[1]==components[2],'Job CPU components sum')
    cpu=components[2]/1e7;wall=finite(value['wall_seconds'],'actual child wall')
    need(type(job['active_processes']) is int and job['active_processes']==0 and value['terminal_job_accounting'] is True,
         'terminal Job zero/accounting')
    configured=value['configured_job_limits'];caps=STAGE_LIMITS[stage]
    need(configured=={'flags':0x2200,'committed_bytes':caps['memory_bytes']},'installed Job limits')
    peak=integer(value['job_memory']['peak_job_memory_used_bytes'],0,2**63,'actual Job peak memory')
    need(cpu<=caps['child_cpu_seconds'] and 0<=wall<=caps['child_wall_seconds'] and peak<=caps['memory_bytes'],
         'actual child resource cap')
    need(type(value['exit_code']) is int and value['exit_code']==0 and value['error'] is None and
         value['cleanup_errors']==[] and value['direct_exit_observed'] is True and value['pipe_eof_observed'] is True and
         value['post_exit_drain']['completed'] is True,'actual clean child disposition')
    termination=value['termination'];need(termination['attempted'] is False,'child emergency intervention')
    compile_cleanup=value.get('compile_cleanup')
    if compile_cleanup is not None:
        closed(compile_cleanup,('schema','policy','disposition','attempted','succeeded','completed','before_accounting','after_accounting',
                               'remaining_process_ids','pid_query_performed','pid_query_error','started_wall_seconds','ended_wall_seconds',
                               'wait_seconds','max_wait_seconds','error','scope'),'compile cleanup keys')
        need(stage.startswith('build-') and index==0,'compile cleanup scope')
        need(compile_cleanup['schema']=='m194h-compile-owned-descendant-cleanup-v1' and
             compile_cleanup['policy']=='AFTER_DIRECT_ZERO_AND_PIPE_EOF' and compile_cleanup['completed'] is True and
             compile_cleanup['error'] is None and compile_cleanup['pid_query_error'] is None,'compile cleanup disposition')
        need(compile_cleanup['after_accounting']['active_processes']==0 and
             compile_cleanup['after_accounting']==job,'compile cleanup final accounting')
        wait=finite(compile_cleanup['wait_seconds'],'compile cleanup wait')
        need(0<=wait<=5 and compile_cleanup['max_wait_seconds']==5 and
             wait==compile_cleanup['ended_wall_seconds']-compile_cleanup['started_wall_seconds'],'compile cleanup finite interval')
        if compile_cleanup['disposition']=='NATURAL_JOB_EXIT':
            need(compile_cleanup['attempted'] is False and compile_cleanup['succeeded'] is False and
                 compile_cleanup['before_accounting']['active_processes']==0,'natural compile completion')
        else:
            need(compile_cleanup['disposition']=='INTENTIONAL_OWNED_JOB_CLEANUP' and compile_cleanup['attempted'] is True and
                 compile_cleanup['succeeded'] is True and compile_cleanup['before_accounting']['active_processes']>0,
                 'intentional compile completion')
        ids=compile_cleanup['remaining_process_ids']
        need(type(compile_cleanup['pid_query_performed']) is bool and
             (type(ids) is list and len(ids)<=1024 and all(type(v) is int and v>0 for v in ids)
              if compile_cleanup['pid_query_performed'] else ids is None),'compile PID observation')
    else:
        need(not stage.startswith('build-'),'compile-specific completion receipt required')
    return {'record':ref,'log':log_ref,'raw_log':log,'value':value,'cpu_seconds':cpu,'wall_seconds':wall,
            'compile_cleanup_disposition':compile_cleanup['disposition'] if compile_cleanup else None}


def bundle_read(io,bundle,stage,sources):
    caps={'result':256*1024,'tail':8*1024,'outer':64*1024,'stdout':8*1024,'stderr':32*1024,'exit':1024}
    closed(bundle,BUNDLE_KEYS,'six actual stage roles')
    raw={key:io.read(bundle[key],cap,empty=key=='stderr') for key,cap in caps.items()}
    result,tail,outer,advert=[metadata_json(raw[key]) for key in ('result','tail','outer','stdout')]
    need(stage in STAGE_LIMITS,'prospective stage limits absent')
    stage_completion(result)
    need(result['schema']=='native-sensor-transfer-owned-stage-v1' and result['stage']==stage,'saved native stage schema')
    output=Path(canonical_path(bundle['result']['path'])).parent
    need(output==HERE/(stage+('-4' if stage=='build-on' else '-1')) and Path(canonical_path(bundle['result']['path'])).name=='result.json','fixed stage result path')
    need(canonical_path(bundle['tail']['path'])==canonical_path(str(output/'parent-tail.json')),'saved tail fixed path')
    closed(outer,('schema','command','source','exit_code','timeout_terminated','elapsed_wall_seconds',
                 'stdout','stderr','exit','stdout_bytes','stderr_bytes','scope'),'stage outer keys')
    need(outer['schema']=='native-sensor-transfer-stage-external-v1' and type(outer['exit_code']) is int and
         outer['exit_code']==0 and raw['exit'].strip()==b'0' and outer['timeout_terminated'] is False,'actual stage external exit')
    need(outer['command']==result['invocation'],'actual outer/runner argv')
    for key in ('stdout','stderr','exit'):same_ref(outer[key],bundle[key],empty=key=='stderr')
    need(type(outer['stdout_bytes']) is int and outer['stdout_bytes']==len(raw['stdout']) and
         type(outer['stderr_bytes']) is int and outer['stderr_bytes']==len(raw['stderr']),'actual stage stream lengths')
    closed(advert,('status','result','tail'),'actual stage advertisement keys')
    need(advert['status']==result['status'] and raw['stdout']==encoded(advert),'actual stage advertisement bytes')
    same_ref(advert['result'],bundle['result']);same_ref(advert['tail'],bundle['tail']);same_ref(tail['result'],bundle['result'])
    need(tail['schema']=='native-sensor-transfer-parent-tail-v1' and tail['cpu_accounting_complete'] is True and
         tail['live_child_cpu_seconds']==0 and tail['final_external_allowance']=={'cpu_seconds':2,'wall_seconds':3},
         'stage publication accounting')
    release=io.json(result['release'],MIB)
    closed(release,('schema','stage','source_bindings','inputs','originals','command','children','binaries','reader_release','prerequisites'),
           'historical stage release keys')
    need(release['schema']=='native-sensor-transfer-stage-release-v1' and release['stage']==stage,'historical stage release identity')
    historical=release['source_bindings']
    need(type(historical) is dict and 1<=len(historical)<=512,'historical bounded source map')
    if not stage.startswith('build-'):need(historical==sources,'same current nonbuild source map')
    for key,pin in historical.items():
        closed(pin,('bytes','sha256'),'historical source pin keys');integer(pin['bytes'],1,4*MIB,'historical source extent');digest(pin['sha256'])
    original_population(release['originals'])
    need([result['release']['sha256'] if x=='ACTUAL_RELEASE_SHA256' else x for x in release['command']]==result['invocation'],
         'stage release argv')
    script=Path(canonical_path(outer['source']['path']));key=str(script.relative_to(REPO)).replace(chr(92),'/')
    same_ref(outer['source'],{'path':key,**historical[key]})
    need(key=='experiments/native-sensor-transfer/run-stage.py','fixed executed runner source')
    io.read({'path':key,**historical[key]},128*1024)
    expected=release['children'];need(type(expected) is list and len(expected)==(9 if stage=='native' else 1) and
        len(result['children'])==len(expected),'complete actual child population')
    if stage.startswith('build-'):
        command=['cargo','test','-p','strehl-cli','--bin','strehl','--no-run']
        if stage=='build-on':command += ['--features','native-sensor-transfer']
        command += ['--jobs','2','--target-dir',str(REPO/'target'/('native-sensor-transfer-'+stage.removeprefix('build-')+('-4' if stage=='build-on' else '-1'))),
                    '--message-format=json-render-diagnostics','--locked','--offline']
        need(expected==[{'command':command,'expected_exit_code':0}],'fixed actual build argv')
    for child in expected:
        closed(child,('command','expected_exit_code'),'closed child schedule entry')
        need(type(child['expected_exit_code']) is int and child['expected_exit_code']==0,'fixed expected child exit')
    observed=[terminal_child(io,ref,expected[i],i,stage,output) for i,ref in enumerate(result['children'])]
    total=sum(child['cpu_seconds'] for child in observed)
    need(total==tail['completed_child_cpu_seconds'],'each completed Job counted once')
    cpu=finite(tail['actual_parent_cpu_sample'],'parent CPU sample');wall=finite(tail['whole_wall_sample'],'parent wall sample')
    elapsed=finite(outer['elapsed_wall_seconds'],'whole external stage wall');limits=STAGE_LIMITS[stage]
    need(cpu>=0 and wall>=0 and 0<=elapsed<=wall+3 and elapsed<=limits['wall_seconds'] and
         cpu+total+2<=limits['cpu_seconds'],'parent sample/reserve plus exact children')
    need(result['work']['cpu_accounting_complete'] is True,'saved stage work accounting')
    return {'result':result,'release':release,'children':observed,'raw':raw,'bundle':bundle,
            'summary':{'stage':stage,'actual_children':len(observed),'job_cpu_seconds':total,
                       'parent_cpu_sample':cpu,'parent_CPU_reservation':2,'whole_child_stage_wall':elapsed,
                       'scope':'owned child Jobs once; parent sampled+reserved, no complete parent-CPU assertion'}}


def buffer_admit(raw,ref):
    need(type(raw) is bytes and len(raw)==ref['bytes'],'actual file extent')
    need(sha(raw)==ref['sha256'],'actual file hash')
    return True


def bootstrap(path,cap):
    # One bounded release snapshot before its limits can be parsed; its actual
    # maximum requested bytes are charged immediately after IO construction.
    path=Path(path);before=path.stat()
    need(stat.S_ISREG(before.st_mode) and 0<before.st_size<=cap,'bootstrap release extent/type')
    for p in [path,*path.parents]:
        m=p.lstat();need(not stat.S_ISLNK(m.st_mode) and not getattr(m,'st_file_attributes',0)&0x400,'bootstrap reparse')
    with path.open('rb') as stream:
        hb=os.fstat(stream.fileno());need(shared_identity(hb)==shared_identity(before),'bootstrap path/handle')
        raw=stream.read(before.st_size+1);ha=os.fstat(stream.fileno())
    after=path.stat()
    need(len(raw)==before.st_size and full_identity(before)==full_identity(after) and
         full_identity(hb)==full_identity(ha),'bootstrap release changed')
    return raw,{'path':str(path),'bytes':len(raw),'sha256':sha(raw)}


def load_independent_modules(io,sources):
    import types
    buffers={}
    need(type(sources) is dict and 4<=len(sources)<=512,'bounded root source population')
    need(sum(integer(pin['bytes'],1,4*MIB,'source map extent') for pin in sources.values())<=16*MIB,'source aggregate cap')
    canonical=set()
    for key,pin in sources.items():
        need(type(key) is str and not re.match(r'^[A-Za-z]:',key) and chr(92) not in key,'canonical relative source key')
        path=Path(canonical_path(key));need(path.is_relative_to(REPO) and path not in canonical,'unique repository source')
        canonical.add(path)
        raw=io.read({'path':key,**pin},4*MIB);source_pin(raw,pin);buffers[key]=raw
    prefix='experiments/native-sensor-transfer/'
    for name,expected in (('independent-protocol.md',PROTOCOL_SHA),('independent-checker-design.md',DESIGN_SHA)):
        need(sources[prefix+name]['sha256']==expected,'held independent methodology source')
    need(prefix+'independent-read.py' in buffers,'actual entry point source binding')
    modules=[]
    for name in MODULES:
        key=prefix+name;need(key in buffers,'independent module source binding')
        module=types.ModuleType('native_independent_'+name.replace('-','_').replace('.','_'))
        module.__file__=str(HERE/name)
        exec(compile(buffers[key],str(HERE/name),'exec'),module.__dict__)
        modules.append(module)
    return modules,buffers


def array_runtime(mode,n):
    # Ordinary isolated import, with version/origin observations. This is neither
    # a complete imported source inventory nor a native DLL/cache closure claim.
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        need(os.environ.get(name)=='1','fixed independent numerical thread environment')
    site=Path(sys.executable).parent/'Lib'/'site-packages'
    need(site.is_dir(),'existing numerical dependency directory')
    sys.path.append(str(site))
    import numpy as np
    n.configure(np)
    rawpy=None
    observed={'numpy':{'version':str(np.__version__),'module_file':str(np.__file__)},
              'scope':'ordinary isolated import observations; no full runtime/DLL authority assertion'}
    if mode=='verify':
        import rawpy as raw_module
        rawpy=raw_module
        observed['rawpy']={'version':str(rawpy.__version__),'module_file':str(rawpy.__file__),
                          'libraw_version':list(rawpy.libraw_version)}
    return np,rawpy,observed


def compiled_executable(io,stage,feature):
    result=stage['result'];art=result['artifacts'];expected=HERE/('build-on-4' if feature else 'build-off-1')/'cli-tests.exe'
    ref=art['executable'];need(canonical_path(ref['path'])==canonical_path(str(expected)),'fixed compiled native test binary')
    executable=io.read(ref,64*MIB)
    original=art['compiled_original'];ref_shape(original)
    need(original['bytes']==ref['bytes'] and original['sha256']==ref['sha256'],'compiled/copy content identity')
    messages=[]
    for line in stage['children'][0]['raw_log'].splitlines():
        try:value=metadata_json(line)
        except (ValueError,UnicodeDecodeError):continue
        if type(value) is dict:messages.append(value)
    targets=[v for v in messages if v.get('reason')=='compiler-artifact' and v.get('executable') and
             v.get('target',{}).get('name')=='strehl' and v.get('profile',{}).get('test') is True]
    finished=[v for v in messages if v.get('reason')=='build-finished']
    need(len(targets)==1 and len(finished)==1 and finished[0].get('success') is True,'sole Cargo test executable/finished')
    need(art['compiler_message']==targets[0] and art['build_finished']==finished[0],'actual Cargo artifact record association')
    need(canonical_path(targets[0]['executable'])==canonical_path(original['path']),'Cargo original executable path')
    message=targets[0]
    need(message.get('fresh') is False and message['features']==(['native-sensor-transfer'] if feature else []) and
         message['target']['kind']==['bin'] and
         canonical_path(message['target']['src_path'])==canonical_path(str(REPO/'crates/strehl-cli/src/main.rs')) and
         canonical_path(message['manifest_path'])==canonical_path(str(REPO/'crates/strehl-cli/Cargo.toml')),
         'fresh exact compiled target/source/features')
    need(Path(canonical_path(original['path'])).is_relative_to(REPO/'target'/('native-sensor-transfer-'+('on' if feature else 'off')+('-4' if feature else '-1'))),
         'fresh compiled target directory')
    need(all(marker in stage['children'][0]['raw_log'] for marker in (b'Compiling strehl-core',b'Compiling strehl-cli')),'actual native compile markers')
    del executable
    return ref


def compiled_closure(sources,buffers):
    # Source-map projection of the already reviewed runner closure. No crate walk,
    # toolchain discovery, dependency import or producer function execution.
    paths={'Cargo.toml','Cargo.lock','crates/strehl-core/src/defect-map-ILCE-7CM2-dust.txt'}
    paths.update(key for key in sources if key.startswith('crates/') and
                 (key.endswith('.rs') or key.endswith('/Cargo.toml')))
    pending=[(key,'/'.join(key.split('/')[:2])) for key in paths if key.endswith('.rs')]
    seen=set()
    while pending:
        key,crate=pending.pop()
        if (key,crate) in seen:continue
        seen.add((key,crate));need(key in buffers,'compiled included source present')
        text=buffers[key].decode('utf-8')
        names=re.findall(r'^\s*include!\(concat!\(\s*env!\("CARGO_MANIFEST_DIR"\),\s*"([^"]+)"\s*\)\)',text,re.M)
        targets=[Path(crate)/name.lstrip('/') for name in names]
        targets += [Path(key).parent/name for name in re.findall(r'^\s*#\[path\s*=\s*"([^"]+)"\]',text,re.M)]
        for p in targets:
            absolute=(REPO/p).resolve();need(absolute.is_relative_to(REPO),'included source repository scope')
            relative=str(absolute.relative_to(REPO)).replace(chr(92),'/')
            paths.add(relative);pending.append((relative,crate))
    need(paths<=set(sources),'full declared compiled source projection')
    selected={key:sources[key] for key in paths}
    return {'files':len(paths),'canonical_sha256':sha(encoded(selected))}


def fixed_native_commands(stage,on,off):
    need(len(stage['children'])==9,'nine native child processes')
    need(type(stage['result']['operations']) is list and len(stage['result']['operations'])==9,'nine native operation records')
    for i,child in enumerate(stage['children']):
        expected=[str(Path(canonical_path((on if i<7 else off)['path']))),'--ignored','--exact',
                  'merge_cmd::native_sensor_transfer::fixed_native_sensor_transfer_pair','--nocapture','--test-threads=1']
        actual=child['value']['command']
        need(len(actual)==len(expected) and canonical_path(actual[0])==canonical_path(expected[0]) and actual[1:]==expected[1:],
             'native feature binary and exact ignored test argv')
        operation=stage['result']['operations'][i]
        need(operation=={'ordinal':i,'expected_exit_code':0,'status':'EXPECTED_PROCESS_DISPOSITION',
                         'environment':{'RAYON_NUM_THREADS':'4','STREHL_PYRAMID_WORKERS':'4','NATIVE_SENSOR_TRANSFER_INVOCATION':str(i)}},
             'actual declared native invocation environment')
        log=child['raw_log']
        need(b'running 1 test' in log and b'1 passed; 0 failed' in log,'actual single native test completion')
    return True


def authority_cases(suite,release,buffers,build):
    key='experiments/native-sensor-transfer/independent-read.py';source=buffers[key];pin=release['source_bindings'][key]
    log=build['children'][0]['raw_log'];ref=build['children'][0]['log']
    bad_pin={**pin,'sha256':'0'*64 if pin['sha256']!='0'*64 else '1'*64}
    bad_hash={**ref,'sha256':'0'*64 if ref['sha256']!='0'*64 else '1'*64};bad_extent={**ref,'bytes':ref['bytes']+1}
    wm={'indices':[0,1,3,2],'letters':['R','G','G','B'],'black':[512]*4,'camera_white':[12000]*4,'generic_white':16383}
    bad_wm={**wm,'letters':['B','G','G','R']}
    def cfa(metadata):
        suite.d.white_authority(metadata,{'black':512,'white':12000});return True
    frame={'schema':'native-sensor-transfer-frame-v1','invocation':0,'index':0,'original_ordinal':0,
           'route':0,'observer':'on','folded':True,'feature':True,
           'floor_array':'not-stored; threshold derived from exact operands',
           'scalar_context_provenance':'DERIVED_FROM_ACTUAL_CONFIG_AND_PREFIX'}
    bad_arm={**frame,'invocation':1};bad_observer={**frame,'observer':'off'}
    parent=build['result'];bad_parent={**parent,'status':'REFUSED'}
    return [
        ('source-hash',lambda:source_pin(source,pin),lambda:source_pin(source,bad_pin),'actual source bytes'),
        ('file-hash',lambda:buffer_admit(log,ref),lambda:buffer_admit(log,bad_hash),'actual file hash'),
        ('file-extent',lambda:buffer_admit(log,ref),lambda:buffer_admit(log,bad_extent),'actual file extent'),
        ('cfa-order',lambda:cfa(wm),lambda:cfa(bad_wm),'independent local RGGB'),
        ('missing-original',lambda:original_population(release['originals']),lambda:original_population(release['originals'][:-1]),'fixed27 original population'),
        ('wrong-arm',lambda:frame_identity(frame,0,0,0),lambda:frame_identity(bad_arm,0,0,0),'fixed native frame identity'),
        ('wrong-observer',lambda:frame_identity(frame,0,0,0),lambda:frame_identity(bad_observer,0,0,0),'fixed native frame identity'),
        ('changed-terminal',lambda:stage_completion(parent),lambda:stage_completion(bad_parent),'saved stage not complete')]


def saved_control_rows(io,stage,sources,originals):
    ref=stage['result']['artifacts']['independent_result'];raw=io.read(ref,128*1024)
    need(len(stage['children'])==1 and stage['children'][0]['raw_log']==raw,'saved control exact raw result/log')
    value=metadata_json(raw)
    need(value['schema']=='native-sensor-transfer-independent-result-v1' and value['mode']=='controls' and
         value['status']=='PASS_PRIVATE_CONTROLS_PENDING_ACTUAL' and value['software_associations_complete'] is False and
         value['physical_model_pass'] is None and value['error'] is None,'saved independent controls disposition')
    need(value['source_bindings_sha256']==sha(encoded(sources)),'same held independent control source map')
    rows=value['groups'];need(type(rows) is list and len(rows)==20,'saved20 control groups')
    for i,(row,count) in enumerate(zip(rows,EXPECTED_VARIANTS),1):
        need(row['id']==f'{i:02}' and row['status']==('PENDING_ACTUAL' if i in (17,18) else 'PASS') and
             len(row['variants'])==count and all(v['passed'] is True for v in row['variants']),'complete saved control variants')
    prior_release=io.json(value['release'],MIB)
    need(prior_release['mode']=='controls' and prior_release['source_bindings']==sources and prior_release['native'] is None and
         prior_release['controls'] is None and prior_release['originals']==originals and
         value['command']==stage['children'][0]['value']['command'] and
         [value['release']['sha256'] if x=='ACTUAL_RELEASE_SHA256' else x for x in prior_release['command']]==value['command'],
         'saved control authority association')
    return copy.deepcopy(rows)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=('controls','verify'),required=True)
    parser.add_argument('--release',required=True)
    parser.add_argument('--release-sha256',required=True)
    args=parser.parse_args()
    io=None;suite=None;release=None;release_ref=None;consumer=None
    result={'schema':'native-sensor-transfer-independent-result-v1','mode':args.mode,'status':'REFUSED',
            'software_associations_complete':False,'physical_model_pass':None,'error':None,'groups':[],
            'independent_decodes':0,'science_scope':'conditional fixed Crop diagnostic; no physical-model PASS'}
    try:
        need(os.name=='nt' and Path.cwd().resolve()==REPO and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
             'fixed Windows isolated reader')
        need(Path(args.release).is_absolute(),'absolute reader release argument')
        digest(args.release_sha256)
        raw,release_ref=bootstrap(args.release,MIB)
        need(release_ref['sha256']==args.release_sha256,'actual reader release hash')
        release=metadata_json(raw)
        closed(release,('schema','mode','source_bindings','originals','builds','native','controls','output','limits','command'),
               'closed10 reader release keys')
        need(release['schema']=='native-sensor-transfer-reader-release-v1' and release['mode']==args.mode,'reader release mode/schema')
        expected=[str(Path(sys.executable)),'-I','-S','-B',str(HERE/'independent-read.py'),'--mode',args.mode,
                  '--release',str(Path(args.release)),'--release-sha256',args.release_sha256]
        declared=[args.release_sha256 if v=='ACTUAL_RELEASE_SHA256' else v for v in release['command']]
        need(sys.orig_argv==expected==declared,'actual independent reader command')
        output=str(HERE/(args.mode+'-1')/'check')
        need(canonical_path(release['output'])==canonical_path(output),'fixed released reader output')
        upper=(100,150,62*MIB) if args.mode=='controls' else (1000,850,64*MIB)
        need(release['limits']['cpu_seconds']<=upper[0] and release['limits']['wall_seconds']<=upper[1] and
             release['limits']['write_bytes']<=upper[2],'fixed prospective reader sub-allocation')
        io=IO(release['limits'],release['output']);io.read_bytes+=len(raw)+1;io.tick()
        result.update(release=release_ref,command=sys.orig_argv,source_bindings_sha256=sha(encoded(release['source_bindings'])))
        original_population(release['originals'])
        modules,buffers=load_independent_modules(io,release['source_bindings']);n,d,c=modules
        closed(release['builds'],('feature_on','feature_off'),'reader build roles')
        builds={role:bundle_read(io,release['builds'][role],stage,release['source_bindings'])
                for role,stage in (('feature_on','build-on'),('feature_off','build-off'))}
        exes={role:compiled_executable(io,build,role=='feature_on') for role,build in builds.items()}
        closure=compiled_closure(release['source_bindings'],buffers)
        need(all(build['result']['compiled_source_closure']==closure for build in builds.values()),'same compiled closure across both feature builds/current reader')
        result['compiled_source_closure']=closure
        result['stages']=[build['summary'] for build in builds.values()]
        if args.mode=='controls':
            need(release['native'] is None and release['controls'] is None,'controls no scientific native authority')
            np,rawpy,runtime=array_runtime(args.mode,n);result['runtime']=runtime
            suite=c.Suite(np,n,d,io.tick)
            suite.authority(authority_cases(suite,release,buffers,builds['feature_on']))
            suite.initial();rows=suite.output()
            for row,count in zip(rows,EXPECTED_VARIANTS):need(len(row['variants'])==count,'fixed control variant count')
            result['status']='PASS_PRIVATE_CONTROLS_PENDING_ACTUAL'
        else:
            need(release['native'] is not None and release['controls'] is not None,'verify saved native/control bundles')
            controls=bundle_read(io,release['controls'],'controls',release['source_bindings'])
            native=bundle_read(io,release['native'],'native',release['source_bindings'])
            need(controls['result']['compiled_source_closure']==native['result']['compiled_source_closure']==closure,'same current compiled native/control closure')
            fixed_native_commands(native,exes['feature_on'],exes['feature_off'])
            result['stages'] += [controls['summary'],native['summary']]
            rows=saved_control_rows(io,controls,release['source_bindings'],release['originals'])
            np,rawpy,runtime=array_runtime(args.mode,n);result['runtime']=runtime
            suite=c.Suite(np,n,d,io.tick);suite.rows={row['id']:row for row in rows}
            entries=native['result']['artifacts']['traversals']
            need(type(entries) is list and len(entries)==9,'nine saved traversal refs')
            traversals=[]
            for i,entry in enumerate(entries):
                closed(entry,('invocation','result'),'actual traversal entry keys')
                need(type(entry['invocation']) is int and entry['invocation']==i,'actual traversal order')
                need(canonical_path(entry['result']['path'])==canonical_path(str(HERE/f'native-run-{i}'/'result.json')),
                     'fixed actual traversal result path')
                traversals.append(io.json(entry['result'],64*1024))
            consumer=Consumer(np,n,d,io,release['originals']);result['population']=consumer.catalog(traversals)
            decoded=consumer.independent_decode(rawpy);result['independent_decodes']=len(decoded)
            result['independent_decode_result']=io.publish('independent-decodes.json',decoded,MIB)
            frame_rows,outputs,witnesses=consumer.saved_arrays()
            suite.actual_observers(witnesses);suite.actual_weight(consumer.first_actual_weight)
            suite.output(complete=True)
            result['frame_checks']=io.publish('actual-frame-checks.json',frame_rows,2*MIB)
            result['output_checks']=io.publish('native-output-checks.json',outputs,128*1024)
            result['statistics']=consumer.statistics()
            result['software_associations_complete']=True
            result['status']='PASS_CONDITIONAL_NATIVE_DIAGNOSTIC'
        # Rehash source/authority after work, without a second decoder/runtime capture.
        for key,pin in release['source_bindings'].items():io.read({'path':key,**pin},4*MIB)
        io.read(release_ref,MIB)
        io.tick(reserve=True)
    except BaseException as exc:
        result['status']='REFUSED';result['software_associations_complete']=False
        result['error']={'type':type(exc).__name__,'message':str(exc)[:4096]}
    if io is not None:io.publishing=True
    if consumer is not None:
        result['independent_decode_attempts']=getattr(consumer,'decode_attempts',0)
        result['independent_decodes']=len(getattr(consumer,'decode_observations',[]))
        result['saved_frame_attempts']=getattr(consumer,'frame_attempts',0)
        result['saved_frames_checked']=len(getattr(consumer,'frame_observations',[]))
        if result['status']=='REFUSED':
            result['last_original_attempted']=(release['originals'][consumer.decode_attempts-1]
                if getattr(consumer,'decode_attempts',0)>0 else None)
            result['partial_decode_observations_scope']='Complete successful prefix below; an attempted failing decode is not counted complete.'
            if hasattr(consumer,'decode_observations') and not (io.output/'independent-decodes.json').exists():
                result['independent_decode_result']=io.publish('independent-decodes.json',consumer.decode_observations,MIB)
            if hasattr(consumer,'frame_observations') and not (io.output/'actual-frame-checks.json').exists():
                result['frame_checks']=io.publish('actual-frame-checks.json',consumer.frame_observations,2*MIB)
    if suite is not None:result['groups']=suite.output()
    if io is not None:
        io.publishing=True
        result['accounting']=io.account()
        final=encoded(result)
        need(len(final)<=128*1024,'independent final/result stdout cap')
        io.tick()
        io.publish_raw('result.json',final,128*1024)
        # Raw stdout is independently charged even though it is byte-identical to result.json.
        need(io.write_bytes+len(final)<=io.limits['write_bytes'],'stdout publication aggregate cap')
        io.write_bytes+=len(final)
        need(sys.stdout.buffer.write(final)==len(final),'full independent stdout')
        sys.stdout.buffer.flush();io.tick()
    else:
        final=encoded(result);need(len(final)<=8192,'bootstrap refusal stdout bound')
        sys.stdout.buffer.write(final);sys.stdout.buffer.flush()
    return 0 if result['status']!='REFUSED' else 1


if __name__=='__main__':
    raise SystemExit(main())
