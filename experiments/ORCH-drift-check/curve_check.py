import numpy as np
x = np.linspace(0.0, 1.0, 1001)
c = 0.42
cur = x + c*x*(1-x)*(2*x-1)*-1.0     # as shipped
fix = x + c*x*(1-x)*(2*x-1)          # sign removed
def slope_mid(y):
    i = (x>=0.25)&(x<=0.75)
    return np.polyfit(x[i], y[i], 1)[0]
print("           slope over midtones   shadow x=0.25   highlight x=0.75")
print(f"identity        {1.0:8.4f}            {0.25:8.4f}      {0.75:8.4f}")
print(f"AS SHIPPED      {slope_mid(cur):8.4f}            {cur[250]:8.4f}      {cur[750]:8.4f}")
print(f"SIGN REMOVED    {slope_mid(fix):8.4f}            {fix[250]:8.4f}      {fix[750]:8.4f}")
print()
print("A filmic S-curve must: darken shadows (x=0.25 -> <0.25),")
print("brighten highlights (x=0.75 -> >0.75), midtone slope > 1.")
print(f"  as shipped   : shadows {'LIFTED' if cur[250]>0.25 else 'darkened'}, "
      f"highlights {'PULLED DOWN' if cur[750]<0.75 else 'brightened'}, slope {slope_mid(cur):.3f}")
print(f"  sign removed : shadows {'lifted' if fix[250]>0.25 else 'DARKENED'}, "
      f"highlights {'pulled down' if fix[750]<0.75 else 'BRIGHTENED'}, slope {slope_mid(fix):.3f}")
print()
print(f"monotonic as shipped : {bool(np.all(np.diff(cur)>0))}")
print(f"monotonic fixed      : {bool(np.all(np.diff(fix)>0))}")
print(f"endpoints fixed      : {fix[0]:.4f} .. {fix[-1]:.4f}")
