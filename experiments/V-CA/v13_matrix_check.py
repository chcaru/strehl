import numpy as np
S = np.array([[0.4124564,0.3575761,0.1804375],
              [0.2126729,0.7151522,0.0721750],
              [0.0193339,0.1191920,0.9503041]])
A = np.array([[0.7460,-0.2365,-0.0588],
              [-0.5687,1.3442,0.2474],
              [-0.0624,0.1156,0.6584]])
def rownorm(M):
    return M / M.sum(axis=1, keepdims=True)
crate  = np.linalg.inv(rownorm(A @ S))   # color.rs: normalise THEN invert
corpus = rownorm(np.linalg.inv(A @ S))   # what the corpus claimed
def leak(M):
    return abs(M[0,1])/abs(M[0,0])*100, abs(M[1,0])/abs(M[1,1])*100
print("CRATE  inv(rownorm(A@S)) :")
for r in crate:  print("   [%9.6f %9.6f %9.6f]" % tuple(r))
print("CORPUS rownorm(inv(A@S)):")
for r in corpus: print("   [%9.6f %9.6f %9.6f]" % tuple(r))
print()
print("leak g->R, r->G   crate : %.1f%%  %.1f%%" % leak(crate))
print("leak g->R, r->G   corpus: %.1f%%  %.1f%%" % leak(corpus))
print()
orch = np.array([[1.636062,-0.448619,-0.187443],
                 [-0.115165,1.488971,-0.373806],
                 [-0.004740,-0.323601,1.328341]])
print("max|crate - ORCH's quoted matrix| = %.2e" % np.abs(crate-orch).max())
doc = np.array([-0.115,1.489,-0.374])
print("crate green row      = [%.6f %.6f %.6f]" % tuple(crate[1]))
print("color.rs:221 doc says= [%.3f  %.3f  %.3f]" % tuple(doc))
print("agree to 3dp? ", np.allclose(np.round(crate[1],3), doc))
print("corpus green row     = [%.6f %.6f %.6f]  -> doc match? %s"
      % (*corpus[1], np.allclose(np.round(corpus[1],3), doc)))
