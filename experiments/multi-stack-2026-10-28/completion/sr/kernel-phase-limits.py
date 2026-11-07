"""DERIVED Gaussian phase-Gram limits; no camera observations or RAW access."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import json, math, pathlib
import numpy as np
rows=[]
for columns in [2,3,4]:
    for policy in ['old_output_scaled','physical_sensor_invariant']:
        step=2/columns
        sigma=0.35*(step if policy=='old_output_scaled' else 1)
        # Continuous normalized Gaussian Fourier moment: E exp(i*pi*d*x).
        gram=np.array([[math.exp(-.5*(math.pi*sigma*(i-j))**2) for j in range(columns)] for i in range(columns)])
        eigen=np.linalg.eigvalsh(gram)
        # 2D separability gives eigenvalue ratio squared. The design condition
        # is sqrt(lambda_max/lambda_min), hence this 1D eigenvalue ratio.
        condition=float(eigen[-1]/eigen[0])
        rows.append(dict(columns_per_axis=columns,output_scale=columns/2,sigma_sensor=sigma,policy=policy,condition_2d=condition))
assert rows[2]['condition_2d']>20 and rows[4]['condition_2d']>400
assert all(row['condition_2d']<20 for row in rows if row['policy']=='physical_sensor_invariant')
result={'status':'DERIVED, ideal continuous Gaussian and infinite dense sampling; not measured camera evidence','workers':1,'formula':'G_ij=exp(-0.5*(pi*sigma_sensor*(i-j))^2); separable 2D design condition=lambda_max(G)/lambda_min(G)','rows':rows}
p=pathlib.Path(__file__).with_suffix('.json');p.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
