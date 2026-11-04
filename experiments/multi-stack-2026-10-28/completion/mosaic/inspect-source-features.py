"""Bounded existing-CFA diagnostic of coarse feature contrast and scale.

Reads one cached original at a time, never decodes RAW. No resulting pixels or
external descriptors are fed to the production renderer.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "4"
import cv2
import numpy as np
import tifffile
cv2.setNumThreads(4)
cv2.setRNGSeed(310528)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--pilot",type=Path,required=True)
    p.add_argument("--cache",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--sources",type=int,nargs=2,default=[5,21])
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    identities=json.loads((a.pilot/"source-identities.json").read_text())
    wanted={identities[i]["sha256"]:i for i in a.sources}
    guides={}
    for path in a.cache.glob("*.cfa"):
        with path.open("rb") as f:
            prefix=f.read(12);assert prefix[:8]==b"STRHCFA1"
            length=struct.unpack("<I",prefix[8:])[0];assert length<=256*1024
            header=json.loads(f.read(length))
        if header["source"]["sha256"] not in wanted:continue
        index=wanted[header["source"]["sha256"]]
        assert header["source"]==identities[index]
        w,h=header["geometry"]["width"],header["geometry"]["height"]
        original=np.memmap(path,dtype="<u2",mode="r",offset=12+length,shape=(h,w))
        black=struct.unpack("<f",struct.pack("<I",header["metadata"]["black_bits"]))[0]
        green=(original[::2,1::2].astype(np.float32)+original[1::2,::2].astype(np.float32))*.5-black
        guide=cv2.resize(green,(w//8,h//8),interpolation=cv2.INTER_AREA)
        del green,original
        guides[index]=guide
        tifffile.imwrite(a.out/f"source-{index}-guide.tiff",guide)
    assert len(guides)==2
    report=dict(sources=[identities[i] for i in a.sources],threads=4,raw_decodes=0,arms=[])
    for transform in ("linear","sqrt"):
        features=[]
        for index in a.sources:
            guide=np.maximum(guides[index],0)
            if transform=="sqrt":guide=np.sqrt(guide)
            img=np.uint8(np.clip(guide/max(float(guide.max()),1e-8)*255,0,255))
            cv2.imwrite(str(a.out/f"source-{index}-{transform}.png"),img)
            features.append(cv2.SIFT_create(nfeatures=3000,contrastThreshold=.01).detectAndCompute(img,None))
        for minimum_size in (0.,4.,6.):
            f=[]
            for keypoints,desc in features:
                keep=[i for i,k in enumerate(keypoints) if k.size>=minimum_size]
                f.append(([keypoints[i] for i in keep],desc[keep]))
            matcher=cv2.BFMatcher()
            ab={x.queryIdx:x.trainIdx for x,y in matcher.knnMatch(f[0][1],f[1][1],k=2) if x.distance<.75*y.distance}
            ba={x.queryIdx:x.trainIdx for x,y in matcher.knnMatch(f[1][1],f[0][1],k=2) if x.distance<.75*y.distance}
            pairs=[(i,j) for i,j in ab.items() if ba.get(j)==i]
            points=np.array([[f[0][0][i].pt,f[1][0][j].pt] for i,j in pairs],np.float32)
            inlier_count=0;model=None
            if len(points)>=2:
                model,inliers=cv2.estimateAffinePartial2D(points[:,0].copy(),points[:,1].copy(),method=cv2.RANSAC,
                    ransacReprojThreshold=6,maxIters=1024,confidence=.99)
                if inliers is not None:inlier_count=int(inliers.sum())
            report["arms"].append(dict(transform=transform,minimum_feature_size=minimum_size,
                features=[len(v[0]) for v in f],reciprocal_matches=len(pairs),coarse_inliers=inlier_count,
                transform_a_to_b=None if model is None else model.tolist()))
    report["scope"]="External feature detector diagnosis on single-source box guides only; no native acceptance or output quality inferred."
    report["script_sha256"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (a.out/"receipt.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report["arms"],indent=2))


if __name__=="__main__":main()
