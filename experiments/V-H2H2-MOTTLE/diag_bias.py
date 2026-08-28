import numpy as np, sys
sys.path.insert(0, ".")
import decomplib
y,x = np.mgrid[0:512,0:512].astype(float)
S = 40*np.sin(x/7)*np.cos(y/11) + 25*np.sin((x+y)/31) + 30*((x//37+y//41)%2) + 128
truth = float(np.var(decomplib.bandpass(S,20,60)))
rng = np.random.default_rng(7)
for sigma in (200.0, 800.0):
    ests=[]
    for _ in range(96):
        a = S + rng.normal(0,sigma,S.shape); b = S + rng.normal(0,sigma,S.shape)
        sc,_ = decomplib.decompose(a,b,20,60); ests.append(sc**2)
    m = float(np.mean(ests)); sd = float(np.std(ests, ddof=1)); se = sd/np.sqrt(len(ests))
    bias = m/truth-1
    print("sigma %5.0f  n=96  bias %+7.3f%%  per-draw scatter %5.2f%%  se-of-mean %5.2f%%  z=%.2f  min draw %+.3f%%"
          % (sigma, 100*bias, 100*sd/truth, 100*se/truth, abs(m-truth)/se, 100*(min(ests)/truth-1)))
