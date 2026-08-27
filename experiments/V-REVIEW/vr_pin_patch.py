import io, os
F = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW\vr_lib.py"
d = open(F, "rb").read()

old_imp = b"import os\r\nimport subprocess\r\nimport sys\r\n"
new_imp = b"import glob\r\nimport hashlib\r\nimport os\r\nimport subprocess\r\nimport sys\r\n"
assert d.count(old_imp) == 1, "import block not found exactly once"
d = d.replace(old_imp, new_imp)

old = (b'SHIP = r"C:\\dev\\strehl-out\\acceptance\\SHIP-V3"\r\n'
       b'ARM = "SHIP-V3"\r\n'
       b'OUT = r"C:\\dev\\strehl-out\\V-REVIEW"\r\n'
       b'EXE = r"C:\\dev\\strehl-out\\acceptance-pins\\740e7056\\target\\release\\strehl.exe"\r\n'
       b'SRC = r"D:\\personal\\macro"\r\n')
assert d.count(old) == 1, "config block not found exactly once"

new = (b'SHIP = r"C:\\dev\\strehl-out\\acceptance\\SHIP-V3"\r\n'
       b'ARM = "SHIP-V3"\r\n'
       b'OUT = r"C:\\dev\\strehl-out\\V-REVIEW"\r\n'
       b'SRC = r"D:\\personal\\macro"\r\n'
       b'PINS = r"C:\\dev\\strehl-out\\acceptance-pins"\r\n'
       b'\r\n'
       b'\r\n'
       b'def _sha256(path):\r\n'
       b'    h = hashlib.sha256()\r\n'
       b'    with open(path, "rb") as f:\r\n'
       b'        for blk in iter(lambda: f.read(1 << 20), b""):\r\n'
       b'            h.update(blk)\r\n'
       b'    return h.hexdigest().upper()\r\n'
       b'\r\n'
       b'\r\n'
       b'def corpus_seal(ship=None, arm=None):\r\n'
       b'    """The SHA256 every master in this corpus records as its renderer.\r\n'
       b'\r\n'
       b'    Hard-fails if the corpus is unsealed or the seals disagree. Never\r\n'
       b'    returns a value that has not been read off the masters themselves.\r\n'
       b'    """\r\n'
       b'    ship = SHIP if ship is None else ship\r\n'
       b'    arm = ARM if arm is None else arm\r\n'
       b'    oks = sorted(glob.glob(os.path.join(ship, "*--%s.tiff.ok" % arm)))\r\n'
       b'    if not oks:\r\n'
       b'        raise RuntimeError("PIN GUARD: no .ok seals in %s" % ship)\r\n'
       b'    seals = set()\r\n'
       b'    for q in oks:\r\n'
       b'        with open(q) as f:\r\n'
       b'            seals.add(f.read().strip().upper())\r\n'
       b'    if len(seals) != 1:\r\n'
       b'        raise RuntimeError(\r\n'
       b'            "PIN GUARD: corpus %s is not internally sealed; %d distinct "\r\n'
       b'            "renderer hashes across %d masters: %s"\r\n'
       b'            % (ship, len(seals), len(oks), sorted(seals)))\r\n'
       b'    return seals.pop(), len(oks)\r\n'
       b'\r\n'
       b'\r\n'
       b'def pin_for(seal):\r\n'
       b'    """Select the pin whose binary hashes to the corpus seal.\r\n'
       b'\r\n'
       b'    Derivation, not declaration: re-pointing SHIP/ARM at another corpus\r\n'
       b'    automatically selects that corpus\'s renderer. A cross-gauge render is\r\n'
       b'    therefore not merely discouraged, it is unreachable.\r\n'
       b'    """\r\n'
       b'    found = {}\r\n'
       b'    for name in sorted(os.listdir(PINS)):\r\n'
       b'        cand = os.path.join(PINS, name, "target", "release", "strehl.exe")\r\n'
       b'        if os.path.isfile(cand):\r\n'
       b'            found[name] = _sha256(cand)\r\n'
       b'    for name, h in found.items():\r\n'
       b'        if h == seal:\r\n'
       b'            return os.path.join(PINS, name, "target", "release",\r\n'
       b'                                "strehl.exe"), name\r\n'
       b'    raise RuntimeError(\r\n'
       b'        "PIN GUARD: no pin matches the corpus seal.\\n"\r\n'
       b'        "  corpus seal : %s\\n"\r\n'
       b'        "  pins present: %s"\r\n'
       b'        % (seal, ", ".join("%s=%s" % kv for kv in sorted(found.items()))))\r\n'
       b'\r\n'
       b'\r\n'
       b'CORPUS_SEAL, N_SEALED = corpus_seal()\r\n'
       b'EXE, EXE_PIN = pin_for(CORPUS_SEAL)\r\n')

d = d.replace(old, new)
open(F, "wb").write(d)
print("patched", F, len(d))
