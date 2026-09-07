"""Re-chosen synthetic sensor law and covariance controls; no RAW input."""
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
M25=ROOT/"experiments/m25-simulator/src"
sys.path.insert(0,str(M25))
from strehl_sim.config import Sensor
from strehl_sim.sensor import expose


def quantized_normal_variance(sigma):
    # Independently integrate the rounding bins, including their total mass.
    cdf=lambda x:.5*(1+math.erf(x/(sigma*math.sqrt(2))))
    k=np.arange(-32,33)
    p=np.array([cdf(v+.5)-cdf(v-.5) for v in k])
    assert abs(p.sum()-1)<1e-12
    mean=float(np.dot(k,p))
    return float(np.dot(k*k,p)-mean*mean)


def parity_variance(cube):
    return [float(cube[:,dy::2,dx::2].var(axis=0,ddof=1).mean())
            for dy,dx in [(0,0),(0,1),(1,0),(1,1)]]


def corr(a,b):
    a=np.asarray(a,dtype=float).ravel(); b=np.asarray(b,dtype=float).ravel()
    a=a-a.mean(); b=b-b.mean()
    return float(np.dot(a,b)/math.sqrt(np.dot(a,a)*np.dot(b,b)))


def main():
    sensor=Sensor(width=96,height=80,gain_divisor=640,base_iso=100,
                  read_noise_e_low=4,read_noise_e_high=4)
    rows=[]; cubes={}
    rng=np.random.default_rng(90217)
    for electrons in [0,1024,8192,32768]:
        mean=np.full((80,96),float(electrons))
        cube=np.array([expose(mean,160,sensor,None,rng) for _ in range(80)],dtype=float)
        cubes[electrons]=cube
        expected=quantized_normal_variance(1) if electrons==0 else .25**2*(electrons+4**2)+1/12
        observed=parity_variance(cube)
        errors=[abs(v/expected-1) for v in observed]
        assert max(errors)<=.02
        correlations=dict(temporal=corr(cube[:-1],cube[1:]),x=corr(cube[:,:,:-1],cube[:,:,1:]),y=corr(cube[:,:-1],cube[:,1:]))
        assert max(abs(v) for v in correlations.values())<=.02
        rows.append(dict(electrons=electrons,expected_variance_dn2=expected,
                         parity_variance_dn2=observed,relative_errors=errors,correlation=correlations))
    negative={}
    # Retain the expected mean while changing gain: the law test cannot win
    # merely by noticing an obvious doubled brightness.
    e=8192
    wrong=np.array([expose(np.full((80,96),e/2),160,sensor,None,rng,gain_dn_per_e=.5)
                    for _ in range(80)],dtype=float)
    baseline_expected=.25**2*(e+16)+1/12
    mismatch=np.array(parity_variance(wrong))/baseline_expected
    assert min(abs(mismatch-1))>.02
    assert abs(wrong.mean()-(512+.25*e))<.5
    negative["same-mean-gain-noise-mismatch"]=dict(variance_ratio=mismatch.tolist(),mean_dn=float(wrong.mean()),rejected=True)
    no_read=np.array([expose(np.zeros((80,96)),160,sensor,None,rng,read=False) for _ in range(80)],dtype=float)
    assert max(parity_variance(no_read))==0
    negative["removed-dark-read-noise"]=dict(variance_dn2=parity_variance(no_read),rejected=True)
    repeated=np.repeat(cubes[e][:1],80,axis=0)
    repeated_correlation=corr(repeated[:-1],repeated[1:])
    assert repeated_correlation>=.99 and max(parity_variance(repeated))==0
    negative["identical-noise-frames"]=dict(correlation=repeated_correlation,variance_dn2=parity_variance(repeated),rejected=True)
    # A separate Gaussian covariance commission keeps the specified marginal
    # variance; no claim that it is the Poisson sensor distribution.
    z=np.random.default_rng(90419)
    correlated=math.sqrt(.75)*z.normal(size=(80,80,96))+math.sqrt(.25)*z.normal(size=(80,80,1))
    spatial=corr(correlated[:,:,:-1],correlated[:,:,1:])
    marginal=float(correlated.var())
    assert spatial>.15 and abs(marginal-1)<.02
    negative["matched-marginal-correlated-noise"]=dict(correlation_x=spatial,variance=marginal,rejected=True)
    expected=np.full((80,96),8192.)
    original=expose(expected,160,sensor,None,np.random.default_rng(99127))
    def delegate(value,enabled):
        held=value.copy() if enabled else np.empty_like(value)
        result=expose(value,160,sensor,None,np.random.default_rng(99127))
        if enabled: assert np.array_equal(held,value)
        return result
    assert np.array_equal(original,delegate(expected,True))
    assert np.array_equal(original,delegate(expected,False))
    evidence=dict(schema="m194b-independent-noise-v1",pass_=True,
                  source_sha256=hashlib.sha256((M25/"strehl_sim/sensor.py").read_bytes()).hexdigest(),
                  scope="synthetic exposure primitive; not full producer interception or real camera calibration",
                  repeats=80,shape=[80,96],seed=90217,rows=rows,negative_controls=negative,
                  delegate_placebo_sha256=hashlib.sha256(original.tobytes()).hexdigest())
    (HERE/"independent-noise.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print(json.dumps(dict(pass_=True,means=len(rows),negative_controls=len(negative),largest_variance_relative_error=max(max(r["relative_errors"]) for r in rows))))


if __name__=="__main__": main()
