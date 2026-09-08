"""Lossless compact LightGlue output codec. Stdlib only, source-only until release."""
import copy
import hashlib
import json
import math
import struct

SCHEMA="m193c-lightglue-tensor-output-v1"
ORDER=("matches0","matches1","matching_scores0","matching_scores1","prune0","prune1","matches","scores")

def need(ok,code):
    if not ok:raise ValueError(code)
def canonical(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def sha(data):return hashlib.sha256(data).hexdigest()
def flat(value,shape):
    need(type(value) is list and len(value)==shape[0],"TENSOR_SHAPE")
    return [part for child in value for part in flat(child,shape[1:])] if len(shape)>1 else value
def reshape(values,shape):
    if len(shape)==1:
        need(len(values)==shape[0],"RECONSTRUCTED_SHAPE");return values
    step=math.prod(shape[1:])
    need(len(values)==math.prod(shape),"RECONSTRUCTED_SHAPE")
    return [reshape(values[i*step:(i+1)*step],shape[1:]) for i in range(shape[0])]
def shape_map(n0,n1,k):
    need(type(n0) is int and type(n1) is int and 1<=n0<=1024 and 1<=n1<=1024,"FEATURE_COUNT")
    need(type(k) is int and 0<=k<=min(n0,n1),"ACCEPTED_COUNT")
    return dict(matches0=[1,n0],matches1=[1,n1],matching_scores0=[1,n0],matching_scores1=[1,n1],
                prune0=[1,n0],prune1=[1,n1],matches=[k,2],scores=[k])
def storage(key):return ("<i4","i",4) if key in ("matches0","matches1") else ("<u2","H",2) if key=="matches" else ("<f4","f",4)
def original(key):return ("<i8","q",8) if key.startswith("matches") else ("<f4","f",4)
def values_valid(key,values,n0,n1):
    if key.startswith("matches"):
        need(all(type(x) is int for x in values),"INTEGER_TYPE")
        if key=="matches":
            need(all(0<=x<(n0 if i%2==0 else n1) for i,x in enumerate(values)),"INDEX_RANGE")
        else:
            maximum=n1 if key=="matches0" else n0
            need(all(-1<=x<maximum for x in values),"INDEX_RANGE")
    else:
        need(all(type(x) is float and math.isfinite(x) for x in values),"FLOAT32_TYPE")
        need(all(x==9.0 for x in values) if key.startswith("prune") else all(0<=x<=1 for x in values),"PRUNING_OR_SCORE_RANGE")
def associate(output,n0,n1):
    need(type(output["stop"]) is int and output["stop"]==9,"FIXED_STOP")
    m0,m1=output["matches0"][0],output["matches1"][0]
    s0,s1=output["matching_scores0"][0],output["matching_scores1"][0]
    pairs=[]
    for i,j in enumerate(m0):
        if j>=0:
            need(m1[j]==i and .1<s0[i]<=1 and s0[i]==s1[j],"MUTUAL_CONFIDENCE")
            pairs.append([i,j])
    need(all(i<0 or m0[i]==j for j,i in enumerate(m1)),"REVERSE_MUTUAL")
    need(output["matches"]==pairs and output["scores"]==[s0[i] for i,j in pairs],"DENSE_COMPACT_IDENTITY")

def pack(record,n0,n1):
    before=canonical(record)
    need(type(record) is dict and "output" in record and "tensor_bytes" in record,"RECORD_SCHEMA")
    output=record["output"];witnesses=record["tensor_bytes"]
    need(type(output) is dict and set(output)==set(ORDER)|{"stop"} and type(witnesses) is dict and set(witnesses)==set(ORDER),"OUTPUT_FIELDS")
    k=len(output["matches"]);shapes=shape_map(n0,n1,k);chunks=[];segments=[];offset=0
    for key in ORDER:
        values=flat(output[key],shapes[key]);values_valid(key,values,n0,n1)
        dtype,fmt,width=original(key);actual=struct.pack("<"+fmt*len(values),*values)
        need(witnesses[key]==dict(dtype=dtype,shape=shapes[key],sha256=sha(actual)),"ORIGINAL_TENSOR_HASH")
        if dtype=="<f4":need(list(struct.unpack("<"+"f"*len(values),actual))==values,"ACTUAL_FLOAT32_VALUES")
        packed_type,packed_format,packed_width=storage(key)
        encoded=struct.pack("<"+packed_format*len(values),*values)
        segments.append(dict(name=key,offset=offset,bytes=len(encoded),storage_dtype=packed_type,original_dtype=dtype,
                             shape=shapes[key],original_sha256=sha(actual)))
        chunks.append(encoded);offset+=len(encoded)
    associate(output,n0,n1);payload=b"".join(chunks)
    need(len(payload)==12*(n0+n1)+8*k and 0<len(payload)<=32768,"EXACT_PACKED_EXTENT")
    header=dict(schema=SCHEMA,n0=n0,n1=n1,accepted_count=k,payload_bytes=len(payload),payload_sha256=sha(payload),segments=segments,
                stop=output["stop"],record_sha256=sha(before),
                intrinsic_extras={key:copy.deepcopy(value) for key,value in record.items() if key not in ("output","tensor_bytes")})
    need(canonical(record)==before,"PACK_INPUT_UNCHANGED")
    return header,payload

def unpack(header,payload):
    need(type(header) is dict and set(header)==set("schema n0 n1 accepted_count payload_bytes payload_sha256 segments stop record_sha256 intrinsic_extras".split()),"HEADER_FIELDS")
    need(header["schema"]==SCHEMA and type(payload) is bytes,"HEADER_VERSION")
    n0,n1,k=(header[key] for key in ("n0","n1","accepted_count"));shapes=shape_map(n0,n1,k)
    need(len(payload)==header["payload_bytes"]==12*(n0+n1)+8*k and sha(payload)==header["payload_sha256"],"PAYLOAD_IDENTITY")
    need(type(header["segments"]) is list and len(header["segments"])==len(ORDER),"SEGMENT_POPULATION")
    need(type(header["intrinsic_extras"]) is dict and not {"output","tensor_bytes"}&set(header["intrinsic_extras"]),"EXTRA_FIELD_DOMAIN")
    output={};witnesses={};offset=0
    for key,segment in zip(ORDER,header["segments"],strict=True):
        need(type(segment) is dict and set(segment)==set("name offset bytes storage_dtype original_dtype shape original_sha256".split()),"SEGMENT_FIELDS")
        packed_type,packed_format,width=storage(key);dtype,fmt,_=original(key);count=math.prod(shapes[key])
        need(segment["name"]==key and type(segment["shape"]) is list and all(type(x) is int for x in segment["shape"]) and segment["shape"]==shapes[key] and segment["storage_dtype"]==packed_type and
             segment["original_dtype"]==dtype and type(segment["bytes"]) is int and segment["bytes"]==count*width,"SEGMENT_SCHEMA")
        need(type(segment["offset"]) is int and segment["offset"]==offset,"SEGMENT_OFFSET")
        values=list(struct.unpack("<"+packed_format*count,payload[offset:offset+count*width]));values_valid(key,values,n0,n1)
        actual=struct.pack("<"+fmt*count,*values);need(sha(actual)==segment["original_sha256"],"ORIGINAL_TENSOR_HASH")
        output[key]=reshape(values,shapes[key]);witnesses[key]=dict(dtype=dtype,shape=shapes[key],sha256=sha(actual))
        offset+=count*width
    need(offset==len(payload),"COMPLETE_PAYLOAD_CONSUMPTION")
    output["stop"]=header["stop"];associate(output,n0,n1)
    record=dict(copy.deepcopy(header["intrinsic_extras"]),output=output,tensor_bytes=witnesses)
    need(sha(canonical(record))==header["record_sha256"],"WHOLE_RECORD_HASH")
    return record

def commission(record,n0,n1,save,progress):
    """Fixed actual-cache codec controls; caller persists each raw mutant/receipt before assertions."""
    need(type(record) is dict,"ACTUAL_CACHED_RECORD")
    before=sha(canonical(record));header,payload=pack(record,n0,n1);need(header["accepted_count"]>0,"POWERED_NONEMPTY_PRIVATE_OUTPUT")
    baseline=save("positive",header,payload);rows=[]
    def report(name,ok,evidence):
        row=dict(id=name,passed=bool(ok),evidence=evidence);rows.append(row);progress(rows)
        need(ok,"CODEC_CONTROL_"+name)
    restored=unpack(header,payload)
    report("whole-actual-record",canonical(restored)==canonical(record),dict(artifact=baseline,record_sha256=before))
    modes={"off":sha(canonical(record))}
    modes["on"]=sha(canonical(unpack(*pack(record,n0,n1))))
    tuple(record.items());modes["placebo"]=sha(canonical(record))
    report("serializer-observer",len(set(modes.values()))==1 and modes["off"]==before,dict(modes=modes,scope="codec only; no inference observation claim"))
    faults=[]
    bad=bytearray(payload);bad[0]^=1;head=copy.deepcopy(header);head["payload_sha256"]=sha(bad)
    faults.append(("one-payload-byte",head,bytes(bad),None))
    bad=bytearray(payload);bad[:4]=struct.pack("<i",-2);head=copy.deepcopy(header);head["payload_sha256"]=sha(bad)
    faults.append(("index-range",head,bytes(bad),"INDEX_RANGE"))
    head=copy.deepcopy(header);head["segments"][0]["shape"][1]+=1
    faults.append(("declared-dimension",head,payload,"SEGMENT_SCHEMA"))
    head=copy.deepcopy(header);head["segments"][1]["offset"]+=1
    faults.append(("declared-offset",head,payload,"SEGMENT_OFFSET"))
    head=copy.deepcopy(header);bad=bytearray(payload);at=head["segments"][-1]["offset"];bad[at]^=1;head["payload_sha256"]=sha(bad)
    faults.append(("score-bit",head,bytes(bad),("ORIGINAL_TENSOR_HASH","PRUNING_OR_SCORE_RANGE")))
    head=copy.deepcopy(header);head["intrinsic_extras"]["codec_fixed_metadata_fault"]=True
    faults.append(("whole-record-field",head,payload,"WHOLE_RECORD_HASH"))
    for name,head,data,expected in faults:
        artifact=save(name,head,data);error=None
        try:unpack(head,data)
        except ValueError as exc:error=str(exc)
        allowed=expected if isinstance(expected,tuple) else None if expected is None else (expected,)
        report(name,error is not None and (allowed is None or error in allowed),dict(artifact=artifact,error=error,expected_error=expected))
    zero_output=dict(matches0=[[-1]*n0],matches1=[[-1]*n1],matching_scores0=[[0.0]*n0],
                     matching_scores1=[[0.0]*n1],prune0=[[9.0]*n0],prune1=[[9.0]*n1],matches=[],scores=[],stop=9)
    zero_shapes=shape_map(n0,n1,0);zero_witness={}
    for key in ORDER:
        dtype,fmt,_=original(key);values=flat(zero_output[key],zero_shapes[key])
        zero_witness[key]=dict(dtype=dtype,shape=zero_shapes[key],sha256=sha(struct.pack("<"+fmt*len(values),*values)))
    zero=dict(schema="m193c-zero-match-codec-fixture-v1",output=zero_output,tensor_bytes=zero_witness,
              scope="labelled structural metadata fixture using actual feature counts; not an inferred or actual model return")
    zh,zp=pack(zero,n0,n1);zero_artifact=save("zero-match-metadata",zh,zp)
    report("zero-match-structure",canonical(unpack(zh,zp))==canonical(zero) and len(zp)==12*(n0+n1) and
           zh["accepted_count"]==0 and all(x["bytes"]==0 for x in zh["segments"][-2:]),
           dict(artifact=zero_artifact,scope=zero["scope"],dense_bytes=len(zp),compact_rows=0))
    after=unpack(header,payload)
    report("restored",sha(canonical(after))==before and sha(canonical(record))==before,
           dict(artifact=baseline,restored_sha256=sha(canonical(after)),input_after_sha256=sha(canonical(record))))
    return dict(schema="m193c-real-codec-controls-v1",passed=True,rows=rows,scope="actual saved private prediction only; zero new inference or fitting")
