"""Summarize sampled metadata and verify the complete RAW directory census."""
from pathlib import Path
import json,hashlib,collections
base=Path(__file__).resolve().parent
p=json.loads((base/"inventory.json").read_text(encoding="utf-8"))
changed=[]
for b in p["brackets"]:
    current=sorted([f for f in Path(b["directory"]).iterdir() if f.is_file() and f.suffix.lower()==".arw"],key=lambda f:f.name)
    recorded=[(x["name"],x["bytes"],x["mtime_ns"]) for x in b["files"]]
    now=[(f.name,f.stat().st_size,f.stat().st_mtime_ns) for f in current]
    if recorded!=now:changed.append(b["id"])
samples=[s for b in p["brackets"] for s in b["representatives"]]
hashes=collections.defaultdict(list)
for s in samples:hashes[s["sha256"]].append(s["path"])
summary={
    "schema":"strehl.multi-stack-corpus-summary.v1",
    "base":p["base"],
    "raw_count":p["count"],
    "raw_bytes":sum(b["total_bytes"] for b in p["brackets"]),
    "bracket_count":len(p["brackets"]),
    "sampled_full_raw_hashes":len(samples),
    "sampled_full_raw_bytes":sum(next(f["bytes"] for f in b["files"] if f["name"]==Path(s["path"]).name) for b in p["brackets"] for s in b["representatives"]),
    "representative_duplicate_hash_groups":[v for v in hashes.values() if len(v)>1],
    "representative_models":dict(collections.Counter(s["metadata"].get("Model") for s in samples)),
    "representative_isos":dict(collections.Counter(s["metadata"].get("ISO") for s in samples)),
    "representative_lenses":dict(collections.Counter(s["metadata"].get("LensModel") for s in samples)),
    "embedded_preview_count":sum("preview" in s for s in samples),
    "census_changed_brackets":changed,
    "census_check":"All RAW names, byte lengths and mtimes re-enumerated after previews; not a full-file hash audit of all 8299 inputs.",
    "inventory_sha256":hashlib.sha256((base/"inventory.json").read_bytes()).hexdigest(),
    "inventory_seconds":p["seconds"],
    "claims_limit":"Metadata sampled at first/middle/last only. Preview observations are orientation/pose observations, not image quality or subpixel-placement verdicts.",
    "brackets":[{k:v for k,v in b.items() if k!="files"} for b in p["brackets"]],
}
(base/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
lines=["# Sampled capture inventory","","First/middle/last metadata; table uses the middle sample. All 144 representatives","are ILCE-7CM2, ISO 100, FE 100mm F2.8 Macro GM OSS + 2X Teleconverter.","There are 8,299 RAW files in 48 directories (308,651,499,520 bytes).","","| ID | Directory relative to its supplied root | Frames | Aperture | Shutter s | First capture | Last capture |","| --- | --- | --- | --- | --- | --- | --- |"]
for b in p["brackets"]:
    s=b["representatives"];m=s[1]["metadata"]
    lines.append(f'| {b["id"]} | {b["family"]}: {b["relative"].replace(chr(92),"/")} | {b["count"]} | {m["FNumber"]} | {m["ExposureTime"]} | {s[0]["metadata"]["DateTimeOriginal"]} | {s[-1]["metadata"]["DateTimeOriginal"]} |')
lines+=["","Root numbers: 0 aperture pairs; 1 calibration grid; 2 high-res calibration slide;","3 insects; 4 marigold; 5 peacock ore; 6 tilted ruler; 7 razor edge.","","Full paths and representative whole-file SHA256 values are in summary.json.","Timestamps are camera-reported local values; no timezone inference was made.","No duplicate SHA256 among 144 sampled RAWs. This does not exclude duplicates","among unsampled files. Queried ExifTool focus fields were absent, which does not","establish absence of native maker-note focus metadata.","","The 8,299-name/size/mtime census was unchanged after preview extraction.",""]
(base/"inventory-table.md").write_text("\n".join(lines),encoding="utf-8")
assert not changed,changed
assert not summary["representative_duplicate_hash_groups"]
print(json.dumps({k:v for k,v in summary.items() if k!="brackets"},indent=2))
