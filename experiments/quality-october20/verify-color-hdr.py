"""Independent colored-patch AVIF decode; inverse transfer and xy-derived primaries.

No encoder matrix/transfer function is imported. Primary chromaticities:
https://www.itu.int/dms_pub/itu-r/opb/rep/R-REP-BT.2380-1-2017-PDF-E.pdf
Container/bitstream agreement:
https://aomediacodec.github.io/av1-isobmff/

Run: python experiments/quality-october20/verify-color-hdr.py <fixture directory>
"""
from pathlib import Path
import json
import subprocess
import sys
import numpy as np

def matrix(primaries):
    xy=np.array(primaries).T
    unscaled=np.vstack([xy[0]/xy[1],np.ones(3),(1-xy[0]-xy[1])/xy[1]])
    white=np.array([.3127/.3290,1,(1-.3127-.3290)/.3290])
    return unscaled@np.diag(np.linalg.solve(unscaled,white))

def linear(rgb_pq):
    m=np.maximum(rgb_pq,0)**(32/2523)
    return (np.maximum(m-3424/4096,0)/(2413/128-(2392/128)*m))**(16384/2610)*10000

def decode(yuv):
    # H.273 full-range equations29..31: luma span1023, chroma origin512.
    yy=yuv[0]/1023
    u=(yuv[1]-512)/1023
    v=(yuv[2]-512)/1023
    r=yy+v*2*(1-.2627)
    b=yy+u*2*(1-.0593)
    g=(yy-.2627*r-.0593*b)/.6780
    return linear(np.array([r,g,b]))

def check(actual,expected):
    # Fails on swapped red/blue or omitted gamut conversion. This is a decoded
    # numerical fidelity bound; it is not a perceptual or photographic score.
    error=np.abs(actual-expected)
    assert np.all(error<np.maximum(.75,expected*.03)),(actual,expected,error)

def main():
    directory=Path(sys.argv[1]);path=directory/"color.avif"
    fixture=json.loads((directory/"fixture.json").read_text())
    prim709=matrix([[.64,.33],[.30,.60],[.15,.06]])
    prim2020=matrix([[.708,.292],[.170,.797],[.131,.046]])
    expected=(np.linalg.solve(prim2020,prim709)@np.array(fixture["patches_linear_bt709"]).T).T*250
    probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-of","json",str(path)],text=True))["streams"][0]
    tags={"width":256,"height":64,"pix_fmt":"yuv444p10le","color_range":"pc",
        "color_space":"bt2020nc","color_transfer":"smpte2084","color_primaries":"bt2020"}
    for key,want in tags.items():assert probe[key]==want,(key,probe[key],want)
    blob=path.read_bytes();n=blob.index(b"nclx")
    assert blob[n+4:n+11]==bytes([0,9,0,16,0,9,128]),"CICP container mismatch"
    raw=subprocess.check_output(["ffmpeg","-v","error","-i",str(path),"-pix_fmt","yuv444p10le","-f","rawvideo","pipe:1"])
    yuv=np.frombuffer(raw,dtype="<u2").reshape(3,64,256).astype(float)
    actual=np.array([decode(yuv[:,24,16+32*k]) for k in range(8)])
    check(actual,expected)
    sabotaged=np.array([decode(yuv[[0,2,1],24,16+32*k]) for k in range(8)])
    try:check(sabotaged,expected)
    except AssertionError:control="rejected swapped chroma channels"
    else:raise AssertionError("color verifier accepted swapped chroma")
    content=next(x for x in probe["side_data_list"] if x["side_data_type"]=="Content light level metadata")
    expected_cll=int(np.ceil(expected.max()))
    expected_fall=int(np.ceil((expected@np.array([.2627,.6780,.0593])).mean()))
    assert abs(content["max_content"]-expected_cll)<=1
    assert abs(content["max_average"]-expected_fall)<=1
    report={"metadata":tags,"expected_nits":expected.tolist(),"decoded_nits":actual.tolist(),
        "max_absolute_channel_error_nits":float(abs(actual-expected).max()),
        "content_light":content,"independent_expected_cll_fall":[expected_cll,expected_fall],
        "negative_control":control}
    (directory/"independent-color-review.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__":main()
