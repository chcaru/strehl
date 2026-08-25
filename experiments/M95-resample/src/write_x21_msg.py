import io
import os

MSG = """M95 x21: measure ORCH's PIL 16-bit hazard against M95's own headline files

ORCH 21:28 named experiments/M95-resample/src/{x9_bitdepth,x9_montage16}.py among
27 scripts that open a .tif through PIL, and warned that the most suspect case is a
metric on a small signal, which "will read as zero, as noise, or -- worst -- as a
clean null". M95's headline IS a clean null on small differences: merged output
byte-identical to the elected frame, 180,697 px, 100.0000 % exact, max 0 DN.

VERDICT: EXPOSED IN NAME ONLY. Not one reported number came through PIL.

Every M95 measurement reads via tifffile, and m95lib.py:48-55 carries the exact
one-line guard ORCH says none of us wrote:

    a = tifffile.imread(path)
    assert a.dtype == np.uint16, a.dtype

PIL appears in the M95 trees only for ImageDraw/ImageFont figure annotation
(s11_figure.py:20, f1_figure.py:25); the pixels those figures measure are read by
tifffile at s11_figure.py:123-125. The two scripts ORCH flagged are the ones that
FOUND this defect: x9_bitdepth.py is a deliberate PIL-vs-tifffile probe whose
docstring derives it from a byte count (7032*4688*3*2 = 197,796,096 against a
197,797,874-byte file) and stops "before any of it is reported"; x9_montage16.py:4-7
documents it verbatim.

Measured rather than argued, on M95's own arm files in C:\\dev\\strehl-out\\M93-out:

  armM-gate0-binlin.tif  tifffile uint16 max 41188  |  PIL uint8 mode=RGB max 160
  distinct green levels  tifffile 11035             |  PIL 149        (74.1x loss)

  exact-match fraction, 250k px crop, merged vs a frame with different content:
    tifffile (uint16)  0.1304 %
    PIL      (uint8)  10.5624 %      <- 81x INFLATION

That is the number that matters. Under PIL the instrument would have called ~1 in 10
genuinely-different pixels identical, which would have destroyed the discriminating
power the whole result rests on -- report control R6a separates elected from
unelected at 100.0000 % vs 0.0519 %, and an 81x inflation of spurious identity sits
far above that margin. The tifffile reader was load-bearing, not lucky.

The crop is labelled in-script as a hazard-magnitude control and explicitly NOT the
headline test, which s5b_checks.py computes on each frame's elected pixel set only.
An arbitrary crop is mostly pixels neither frame won, so its low absolute match is
expected and is not a counter-example; only the PIL/tifffile ratio is being read.

Bars B1-B4 and the interpretation of every outcome are in the docstring, including
the branch where PIL shows no inflation, in which case the report was to say the
headline is reader-independent rather than claim a save it did not earn.
"""

path = os.path.join(os.environ["TEMP"], "m95_x21_commit.txt")
with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(MSG)
print(f"wrote {len(MSG)} chars; control bytes: "
      f"{len([c for c in MSG if ord(c) < 32 and c not in chr(13)+chr(10)+chr(9)])}")
