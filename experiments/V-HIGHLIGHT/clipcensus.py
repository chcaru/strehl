import sys, numpy as np, tifffile
MAX = 65535
for name, path in [("BEFORE(off)", sys.argv[1]), ("AFTER(def)", sys.argv[2])]:
    a = tifffile.imread(path)
    clipped_ch = (a >= MAX)
    anyc = clipped_ch.any(axis=2)
    allc = clipped_ch.all(axis=2)
    n_any, n_all = anyc.sum(), allc.sum()
    print("%-12s any-channel clipped %8d (%.4f%%)   all-channel %8d (%.4f%%)" % (
        name, n_any, 100.0*n_any/anyc.size, n_all, 100.0*n_all/anyc.size))
    if n_any:
        print("               of clipped pixels: neutral(all 3) %.3f%%   COLOURED(some) %.3f%%" % (
            100.0*n_all/n_any, 100.0*(n_any-n_all)/n_any))
    for i,ch in enumerate("RGB"):
        print("               %s clipped %.4f%%" % (ch, 100.0*clipped_ch[:,:,i].mean()))
