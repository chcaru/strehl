"""Independent controls of the actual author API, with per-run source snapshots."""
import os
for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ[key] = "2"
import argparse
import dataclasses
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys
import traceback
import numpy as np

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("independent_model",HERE/"independent-model.py")
m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--model-sha256",required=True)
    ap.add_argument("--render-sha256",required=True)
    args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    result=dict(schema="m194e-independent-author-api-v1",status="RUNNING",argv=sys.argv,
                sources={},checks=[],texture_checks=[])
    budget=m.Budget()
    try:
        for name,expected in (("model.py",args.model_sha256),("render.py",args.render_sha256)):
            if sha(HERE/name)!=expected:
                raise m.Refusal("author preflight source changed: "+name)
        for name in ("model.py","render.py","independent-model.py","independent-author-check.py","independent-design.md"):
            shutil.copyfile(HERE/name,args.output/name)
            result["sources"][name]=sha(HERE/name)
        sys.path.insert(0,str(HERE))
        import model as author
        import render as renderer
        ai=renderer.integrator_for("primary")
        meter=renderer.Meter(ai)

        def convert(scene,frame):
            def field(rad):
                return author.Field(rad.constant,rad.affine,tuple(author.Wave(a,(fx,fy),p) for a,fx,fy,p in rad.waves))
            # Construct the forward map independently, including off-centre gauge.
            s=math.hypot(frame.M[0][0],frame.M[1][0]); angle=math.atan2(frame.M[1][0],frame.M[0][0])
            centre=(37.23,24.61)
            inv=((math.cos(angle)/s,math.sin(angle)/s),(-math.sin(angle)/s,math.cos(angle)/s))
            delta=tuple(centre[i]-frame.b[i] for i in range(2))
            translation=tuple(m.dot(inv[i],delta)-centre[i] for i in range(2))
            sim=author.Similarity(1/s,-angle,centre,translation)
            return (author.Scene(field(scene.foreground),field(scene.background),
                                 (scene.foreground_depth,scene.background_depth),scene.normal,scene.offset),
                    author.Frame(0,frame.inverse_focus,frame.K,sim))

        def rays(scene,frame,xy,u):
            a,f=convert(scene,frame)
            return np.asarray(author.evaluate_rays(a,f,xy,u)).tolist()

        def subject(scene,frame,xy,cell=False):
            budget.check()
            a,f=convert(scene,frame)
            fun=renderer.render_cell if cell else renderer.render_point
            actual,receipt=fun(a,f,xy,ai,meter)
            budget.check()
            return actual,receipt

        def check(name,actual,expected,tol):
            error=float(np.max(np.abs(np.asarray(actual)-np.asarray(expected))))
            result["checks"].append(dict(name=name,actual=actual,expected=expected,max_error_e=error,tolerance_e=tol,passed=error<=tol))
            if error>tol:
                raise AssertionError(f"{name}: {error=}")

        scene=m.alternative_scene(); frame=m.alternative_frame(); n=scene.normal; c=(37.23,24.61)
        d_f,d_b=11*(.53-.8),11*(.53-.4)
        for dc in (0.,10000.,20000.):
            null=dataclasses.replace(scene,foreground=m.Radiance(dc),background=m.Radiance(dc))
            actual,_=subject(null,frame,c,True)
            check(f"flat-first-{dc}",actual,dc,1e-7)
        for sign in (1.,-1.):
            slope=sign*5/d_b
            ray_scene=dataclasses.replace(scene,foreground=m.Radiance(30.),background=m.Radiance(15-slope*m.dot(n,c),(slope*n[0],slope*n[1])))
            check(f"R1-rays-{sign}",rays(ray_scene,frame,c,[(-n[0],-n[1]),n]),[30.,20.] if sign==1 else [30.,10.],1e-10)
            check(f"R1-pupil-permutation-{sign}",rays(ray_scene,frame,c,[n,(-n[0],-n[1])]),[20.,30.] if sign==1 else [10.,30.],1e-10)
        for slope in (-800.,0.,800.):
            affine=m.alternative_scene("affine",slope)
            actual,_=subject(affine,frame,c)
            check(f"R2-continuous-affine-{slope}",actual,11000+slope*d_b*2/(3*math.pi),.02)
        constants=m.alternative_scene("constant")
        for h in (-.73,-.21,.34,.81):
            xy=tuple(c[j]-h*abs(d_f)*n[j] for j in range(2))
            expected=9000+3000*(math.acos(h)-h*math.sqrt(1-h*h))/math.pi
            check(f"R3-segment-{h}",subject(constants,frame,xy)[0],expected,.02)
        for state in ("full","absent"):
            a,f=convert(constants,frame)
            a=dataclasses.replace(a,mask_state=state)
            expected=12000. if state=="full" else 9000.
            check(f"R3-explicit-{state}",renderer.render_cell(a,f,c,ai,meter)[0],expected,.02)
            changed=dataclasses.replace(a,background=author.Field(23000.)) if state=="full" else dataclasses.replace(a,foreground=author.Field(17000.))
            check(f"R3-hidden-change-{state}",renderer.render_cell(changed,f,c,ai,meter)[0],expected,.02)
        a,f=convert(constants,frame)
        # A complete layer made foreground must occlude the formerly foreground layer.
        reversed_order=dataclasses.replace(a,foreground=a.background,background=a.foreground,mask_state="full")
        check("order-reversal-live",renderer.render_cell(reversed_order,f,c,ai,meter)[0],9000.,.02)
        try:
            dataclasses.replace(a,depths=tuple(reversed(a.depths)))
        except ValueError:
            result["checks"].append(dict(name="unordered-depth-refusal",passed=True))
        else:
            raise AssertionError("unordered depths accepted")
        for focused in (.8,.4):
            ff=dataclasses.replace(frame,inverse_focus=focused)
            check(f"R3-focused-{focused}",subject(constants,ff,(c[0]+.2,c[1]-.17))[0],
                  m.render(constants,ff,(c[0]+.2,c[1]-.17),cell=False,eps=.0000078125,budget=budget)[0],.02)
        for sign in (1.,-1.):
            cs=m.Scene(1.25,2.5,(1.,0.),.1,m.Radiance(30.),m.Radiance(10.,(4*sign,0.)))
            check(f"R4-cell-joint-{sign}",subject(cs,dataclasses.replace(frame,K=0.),(0.,0.),True)[0],18-sign*.48,.02)
        transformed=m.alternative_frame(True); affine=m.alternative_scene("affine")
        for fr in (transformed,dataclasses.replace(transformed,K=0.)):
            for cell in (False,True):
                actual,receipt=subject(affine,fr,c,cell)
                expected=m.render(affine,fr,c,cell=cell,eps=.0000078125,budget=budget)[0]
                check(f"R5-transformed-{fr.K}-{cell}",actual,expected,.02)
        # Power of active ray pairing is read against the actual subject, not a disconnected equality.
        power_scene=m.alternative_scene("affine")
        good=subject(power_scene,frame,c)[0]
        unsigned=m.render(power_scene,frame,c,cell=False,unsigned=True,budget=budget)[0]
        check("R2-wrong-unsigned-is-live",float(abs(good-unsigned)>400.),1.,0.)
        check("R2-wrong-separate-is-live",float(abs(good-11000)>200.),1.,0.)
        wrong_cell=18.; good_cell=subject(m.Scene(1.25,2.5,(1.,0.),.1,m.Radiance(30.),m.Radiance(10.,(4.,0.))),dataclasses.replace(frame,K=0.),(0.,0.),True)[0]
        check("R4-wrong-cell-separate-is-live",float(abs(good_cell-wrong_cell)>.4),1.,0.)

        for shift in (0.,.137):
            texture=m.alternative_scene(shift=shift)
            for transformed_flag in (False,True):
                fr=m.alternative_frame(transformed_flag)
                points=[]
                for y in (6,15,24,35,46,55):
                    base=(c[0]-5/12*(y-c[1]),float(y))
                    points.extend(tuple(base[j]+d*n[j] for j in range(2)) for d in (-4.1,-1.3,-.17,.29,1.7,4.7))
                    points.append(tuple(float(round(v)) for v in base))
                for xy in points:
                    for cell in (False,True):
                        actual,receipt=subject(texture,fr,xy,cell)
                        expected=m.render(texture,fr,xy,cell=cell,eps=.0000078125,budget=budget)[0]
                        error=actual-expected
                        result["texture_checks"].append(dict(shift=shift,transformed=transformed_flag,xy=xy,cell=cell,
                                                             actual_e=actual,reference_e=expected,error_e=error,author_receipt=receipt))
                        if abs(error)>.004:
                            raise AssertionError("rechosen texture maximum discrepancy")
                (args.output/"partial.json").write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf8")
                print(json.dumps(dict(texture_checks=len(result["texture_checks"]),budget=budget.receipt())),flush=True)
        errors=np.array([r["error_e"] for r in result["texture_checks"]])
        result["texture_summary"]=dict(count=len(errors),max_e=float(np.max(np.abs(errors))),rms_e=float(np.sqrt(np.mean(errors**2))))
        if result["texture_summary"]["rms_e"]>.0008:
            raise AssertionError("rechosen texture RMS discrepancy")
        result["author_meter"]=meter.receipt()
        result["status"]="PASS_AUTHOR_API_ONLY"
    except Exception as exc:
        result["status"]="UNCOMMISSIONED_NUMERICS" if isinstance(exc,m.Refusal) or type(exc).__name__=="NumericalFailure" else "INSTRUMENT_INVALID"
        result["exception"]=str(exc)
        result["traceback"]=traceback.format_exc()
    finally:
        result["budget"]=budget.receipt()
        result["source_unchanged"]=all(sha(HERE/k)==v for k,v in result["sources"].items())
        if not result["source_unchanged"]:
            result["status"]="SOURCE_CHANGED_INELIGIBLE"
        (args.output/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf8")
        print(json.dumps(dict(status=result["status"],checks=len(result["checks"]),texture_checks=len(result["texture_checks"]),exception=result.get("exception"))))
    return 0 if result["status"]=="PASS_AUTHOR_API_ONLY" else 1


if __name__=="__main__":
    raise SystemExit(main())
