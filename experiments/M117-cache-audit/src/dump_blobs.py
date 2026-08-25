import subprocess, os, hashlib
out = r"C:\dev\strehl-out\M117\blobs"
os.makedirs(out, exist_ok=True)
shas = {
 "ed45144":"crates/strehl-cli/src/align_cmd.rs",
 "885e9f7":"crates/strehl-cli/src/align_cmd.rs",
 "8118dd7":"crates/strehl-cli/src/align_cmd.rs",
 "b9ba221":"crates/strehl-cli/src/align_cmd.rs",
 "69f7b4c":"crates/strehl-cli/src/align_cmd.rs",
}
for sha, path in shas.items():
    r = subprocess.run(["git","show",f"{sha}:{path}"], capture_output=True)
    if r.returncode != 0:
        print(sha, "MISSING", r.stderr.decode()); continue
    b = r.stdout
    fn = os.path.join(out, f"align_cmd.{sha}.rs")
    with open(fn,"wb") as f: f.write(b)
    print(sha, len(b), hashlib.sha256(b).hexdigest()[:16], fn)
