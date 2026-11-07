"""Cached-only guide reconstruction, accepted only on exact production hash.

Source payloads and consumed focus files are checksum-verified; original sensor
samples are never decoded. Compact guide witnesses support subsequent replay.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import struct
import time

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "4"
import cv2
import numpy as np
import tifffile

cv2.setNumThreads(4)


def number(bits, fmt="d"):
    return struct.unpack("<" + fmt, int(bits, 16).to_bytes(8, "little"))[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    headers = {}
    for path in args.cache.glob("*.cfa"):
        with path.open("rb") as stream:
            prefix = stream.read(12)
            assert prefix[:8] == b"STRHCFA1"
            length = struct.unpack("<I", prefix[8:])[0]
            assert length <= 256 * 1024
            header = json.loads(stream.read(length))
        headers[(header["source"]["sha256"],header["source"]["path"])] = (path, 12 + length, header)
    identities = json.loads((args.pilot / "source-identities.json").read_text())
    results, images = [], []
    for pass_index, directory in enumerate(sorted(args.pilot.glob("pass-*"))):
        started = time.monotonic()
        focus = directory / "focus"
        receipt = json.loads((focus / "guide-receipt.json").read_text())
        focus_geometry=json.loads((focus/"geometry.json").read_text())
        declared={item["file"]:item for item in focus_geometry["files"]}
        step = receipt["step_quad_pixels"]
        w, h = receipt["guide_geometry"]
        native_w, native_h = receipt["source_geometry"]
        def field(name):
            path=focus/(name+".tiff")
            with path.open("rb") as stream:
                assert hashlib.file_digest(stream,"sha256").hexdigest()==declared[path.name]["sha256"],path
            view = tifffile.memmap(path, mode="r")
            assert view.shape==(native_h,native_w)
            return np.array(view[step // 2:step*h:step, step // 2:step*w:step]).ravel()
        covered = field("focus-coverage") != 0
        usable = field("usable") != 0
        ordinal, width = field("ordinal"), field("width-frames")
        ranked = np.stack([field("source-rank-" + str(i)) for i in range(1, 5)], axis=1)
        alignment = json.loads((directory / "alignment.json").read_text())
        transforms = {}
        for line in alignment["warpmap"].splitlines():
            items = line.split()
            if len(items) > 5 and items[1] == "placed":
                transforms[int(items[0])] = [number(v) for v in items[2:6]]
        start_global = int(json.loads((focus / "geometry.json").read_text())["ordinal_mapping"][0]["global_index"])
        intensity = np.zeros(w*h, np.float32)
        counts = np.zeros(w*h, np.uint8)
        witnesses = np.full((w*h, 4), -1, np.int32)
        contributions = []
        for global_id, identity in enumerate(identities):
            local_id = global_id - start_global
            if local_id not in transforms:
                continue
            selected = covered & ((ranked[:, 0] == global_id) | (usable & np.any(ranked == global_id, axis=1)))
            selected &= (~usable) | (np.abs(local_id - ordinal) <= np.maximum(width, 1.0))
            ids = np.flatnonzero(selected)
            if not len(ids):
                continue
            path, offset, header = headers[(identity["sha256"],identity["path"])]
            assert header["source"] == identity
            sw, sh = header["geometry"]["width"], header["geometry"]["height"]
            assert (sw, sh) == (native_w*2, native_h*2)
            assert path.stat().st_size==offset+sw*sh*2+32
            with path.open("rb") as stream:
                stream.seek(12)
                digest=hashlib.sha256(stream.read(offset-12))
                remaining=sw*sh*2
                while remaining:
                    block=stream.read(min(1024*1024,remaining));assert block
                    digest.update(block);remaining-=len(block)
                assert digest.digest()==stream.read(32),path
            source = np.memmap(path, dtype="<u2", mode="r", offset=offset, shape=(sh, sw))
            black = struct.unpack("<f",struct.pack("<I",header["metadata"]["black_bits"]))[0]
            white = struct.unpack("<f",struct.pack("<I",header["metadata"]["white_bits"]))[0]
            ar, ai, br, bi = transforms[local_id]
            total = np.zeros(len(ids), np.float32)
            good = np.ones(len(ids), bool)
            for by in range(step):
                for bx in range(step):
                    for dx, dy in ((1,0),(0,1)):
                        px = (ids % w)*step + bx + dx*.5-.25 - native_w*.5
                        py = (ids // w)*step + by + dy*.5-.25 - native_h*.5
                        x = ar*px-ai*py+br+native_w*.5-(dx*.5-.25)
                        y = ai*px+ar*py+bi+native_h*.5-(dy*.5-.25)
                        good &= (x>=0)&(y>=0)&(x<=native_w-1)&(y<=native_h-1)
                        ix=np.clip(np.floor(x).astype(np.int32),0,native_w-2)
                        iy=np.clip(np.floor(y).astype(np.int32),0,native_h-2)
                        fx=(x-ix).astype(np.float32);fy=(y-iy).astype(np.float32)
                        value=np.zeros(len(ids),np.float32)
                        for yy,wy in ((iy,1-fy),(iy+1,fy)):
                            for xx,wx in ((ix,1-fx),(ix+1,fx)):
                                weight=wx*wy
                                sample=source[2*yy+dy,2*xx+dx].astype(np.float32)
                                good &= (weight==0)|(sample<white)
                                value += weight*(sample-black)
                        total += value
            target=ids[good]
            intensity[target] += total[good]/np.float32(2*step*step)
            witnesses[target,counts[target]] = global_id
            counts[target] += 1
            contributions.append([global_id,len(target)])
            del source
        mask=counts>0
        intensity[mask]/=counts[mask]
        usable &= mask
        ordered=np.full_like(witnesses,-1);ordered_count=np.zeros(len(witnesses),np.int32)
        for rank in range(4):
            preferred=ranked[:,rank]
            selected=(preferred>=0)&np.any(witnesses==preferred[:,None],axis=1)&~np.any(ordered==preferred[:,None],axis=1)
            selected=np.flatnonzero(selected)
            ordered[selected,ordered_count[selected]]=preferred[selected].astype(np.int32)
            ordered_count[selected]+=1
        assert np.array_equal(ordered_count,counts.astype(np.int32))
        witnesses=ordered
        prefix=struct.pack("<6Q",pass_index,w,h,step,0,0)
        record_type=np.dtype([("intensity","<f4"),("covered","u1"),("usable","u1"),("sources","<u8",(4,))],align=False)
        records=np.zeros(w*h,record_type)
        records["intensity"]=intensity;records["covered"]=mask;records["usable"]=usable;records["sources"]=witnesses.astype(np.int64).astype(np.uint64)
        actual_hash=hashlib.sha256(prefix+records.tobytes()).hexdigest()
        reference=tifffile.imread(focus/"diagnostic-guide.tiff").ravel()
        different_bits=int(np.count_nonzero(reference.view(np.uint32)!=intensity.view(np.uint32)))
        assert actual_hash==receipt["guide_sha256"],dict(pass_index=pass_index,expected=receipt["guide_sha256"],actual=actual_hash,different_intensity_bits=different_bits)
        packed_type=np.dtype(record_type.descr+[("ordinal","<f4"),("width","<f4")],align=False)
        packed=np.zeros(w*h,packed_type)
        for name in record_type.names:packed[name]=records[name]
        packed["ordinal"]=ordinal;packed["width"]=width
        replay_header=dict(schema="strehl.cached-mosaic-guide.v1",record_bytes=packed_type.itemsize,receipt=receipt,
            source_identities_sha256=hashlib.sha256((args.pilot/"source-identities.json").read_bytes()).hexdigest(),
            alignment_envelope_sha256=hashlib.sha256((directory/"alignment.json").read_bytes()).hexdigest(),
            focus_receipt_sha256=hashlib.sha256((focus/"geometry.json").read_bytes()).hexdigest())
        encoded=json.dumps(replay_header,separators=(",",":")).encode()
        with (args.out/f"guide-{pass_index}.bin").open("xb") as stream:
            stream.write(b"STRHGUI1");stream.write(struct.pack("<I",len(encoded)));stream.write(encoded);stream.write(packed.tobytes())
        image=intensity.reshape(h,w)
        tifffile.imwrite(args.out/f"guide-{pass_index}.tiff",image)
        tifffile.imwrite(args.out/f"guide-{pass_index}-valid.tiff",mask.reshape(h,w).astype(np.uint8))
        low,high=np.percentile(intensity[mask],[.2,99.8])
        display=np.clip((image-low)/(high-low),0,1)
        display=np.uint8(np.sqrt(display)*255)
        cv2.imwrite(str(args.out/f"guide-{pass_index}.png"),display)
        images.append(display)
        assert contributions == receipt["source_contributions"],(contributions,receipt["source_contributions"])
        results.append(dict(pass_index=pass_index,covered=int(mask.sum()),usable=int(usable.sum()),
            source_contributions=contributions,elapsed_seconds=time.monotonic()-started,
            guide_sha256=actual_hash,different_intensity_bits=different_bits,
            compact_guide_sha256=hashlib.sha256((args.out/f"guide-{pass_index}.bin").read_bytes()).hexdigest(),
            scope="Cached original-CFA reconstruction with exact production guide/source-witness hash; no RAW decode or focus re-estimation"))
    sift=cv2.SIFT_create(nfeatures=3000,contrastThreshold=.02)
    features=[sift.detectAndCompute(img,None) for img in images]
    matcher=cv2.BFMatcher()
    pairs=[]
    for k in range(len(images)-1):
        a,b=features[k],features[k+1]
        ab={m.queryIdx:m.trainIdx for m,n in matcher.knnMatch(a[1],b[1],k=2) if m.distance<.75*n.distance}
        ba={m.queryIdx:m.trainIdx for m,n in matcher.knnMatch(b[1],a[1],k=2) if m.distance<.75*n.distance}
        mutual=[(i,j) for i,j in ab.items() if ba.get(j)==i]
        pairs.append(dict(passes=[k,k+1],sift_features=[len(a[0]),len(b[0])],reciprocal_ratio_matches=len(mutual)))
    result=dict(source=str(args.pilot),threads=4,raw_decodes=0,passes=results,external_diagnostic_matches=pairs,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.out/"receipt.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
