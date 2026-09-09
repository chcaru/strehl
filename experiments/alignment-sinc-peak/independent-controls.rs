// Independent analytic peak controls; source author/root owns execution.
use serde_json::{json, Value};

type Answer = (Option<(f32,f32)>,usize,&'static str);
fn grid<F>(side: usize, centre: (usize,usize), field: F) -> Vec<f32>
where F: Fn(f64,f64)->f64 {
    (0..side).flat_map(|y| (0..side).map(move |x| (x,y)))
        .map(|(x,y)| field(x as f64-centre.0 as f64,y as f64-centre.1 as f64) as f32).collect()
}
fn peak(scores: &[f32], side: usize) -> (usize,usize) {
    let mut best = 0;
    for i in 1..scores.len() { if scores[i] > scores[best] { best=i; } }
    (best%side,best/side)
}
fn analytic(kind: usize, x: f64, y: f64, shift: (f64,f64)) -> f64 {
    let (x,y)=(x-shift.0,y-shift.1);
    let angle: f64 = if kind==0 {0.6} else if kind==1 {0.45} else {0.4};
    let (u,v)=(angle.cos()*x+angle.sin()*y,-angle.sin()*x+angle.cos()*y);
    let g = |a:f64,b:f64| (-0.5*(u*u/(a*a)+v*v/(b*b))).exp();
    match kind {0=>g(1.4,2.3),1=>g(2.7,3.6),_=>0.5*g(0.95,2.7)+0.5*g(2.7,0.95)}
}
fn evaluate<F>(refine: &F, values: &[f32], side: usize, at: (usize,usize)) -> Answer
where F: Fn(&[f32],usize,usize,usize)->Answer {
    let result=refine(values,side,at.0,at.1);
    assert!(result.1<=80,"fixed interpolant-evaluation budget");
    if let Some((x,y))=result.0 {
        assert!(x.is_finite() && y.is_finite() && x.abs()<0.5 && y.abs()<0.5,
            "accepted displacement must be finite and strictly interior");
    }
    result
}
fn require_same(actual: (f32,f32), expected: (f32,f32), name: &str) {
    assert!((actual.0-expected.0).hypot(actual.1-expected.1)<=0.001,
        "{name}: actual={actual:?}, expected={expected:?}");
}

// The callback must invoke the real feature-gated helper and preserve its Outcome.
// Gaussian/crossed/ringing fields below supply their own analytic maxima; they
// are not synthesized by the interpolation being tested.
pub(super) fn literal_controls<F>(refine: F) -> Value
where F: Fn(&[f32],usize,usize,usize)->Answer {
    let side=13;
    let at=(6,6);
    let mut checks=Vec::new();
    let mut positive=0;
    for kind in 0..3 {
        for shift in [(0.0,0.0),(0.1875,-0.3125),(-0.1875,0.3125)] {
            let values=grid(side,at,|x,y| analytic(kind,x,y,shift));
            assert_eq!(peak(&values,side),at,"positive plant must nominate supplied integer peak");
            let result=evaluate(&refine,&values,side,at);
            let offset=result.0.expect("analytic positive peak must exercise candidate");
            let error=(offset.0 as f64-shift.0).hypot(offset.1 as f64-shift.1);
            assert!(error<=if shift==(0.0,0.0) {0.001} else {0.15},
                "signed analytic maximum error={error}, kind={kind}, shift={shift:?}");
            let reflected:Vec<f32>=(0..side).flat_map(|y|(0..side).map(move |x|(x,y)))
                .map(|(x,y)|values[y*side+(side-1-x)]).collect();
            let swapped:Vec<f32>=(0..side).flat_map(|y|(0..side).map(move |x|(x,y)))
                .map(|(x,y)|values[x*side+y]).collect();
            let affine:Vec<f32>=values.iter().map(|v|0.25*v+0.125).collect();
            require_same(evaluate(&refine,&reflected,side,at).0.expect("reflection lost peak"),
                (-offset.0,offset.1),"x reflection");
            require_same(evaluate(&refine,&swapped,side,at).0.expect("transpose lost peak"),
                (offset.1,offset.0),"axis transpose");
            require_same(evaluate(&refine,&affine,side,at).0.expect("positive affine score transform lost peak"),
                offset,"score gain/offset invariance");
            if shift!=(0.0,0.0) {
                let wrong_sign=(-offset.0 as f64-shift.0).hypot(-offset.1 as f64-shift.1);
                assert!(wrong_sign>0.5,"wrong-sign control lacks power");
            }
            positive+=1;
            checks.push(json!({"kind":kind,"truth":shift,"offset":offset,"error":error,
                "evaluations":result.1,"reason":result.2,"symmetry_affine":"PASS"}));
        }
    }
    // A positive Gaussian envelope times a bounded carrier has a unique true
    // maximum at shift. Its rapidly varying shoulders challenge sinc ringing.
    // Refusal is admissible here; an accepted false maximum is not.
    let mut ringing=Vec::new();
    for shift in [(0.1875,-0.3125),(-0.1875,0.3125)] {
        let values=grid(side,at,|x,y| {
            let (u,v)=(x-shift.0,y-shift.1);
            (-0.5*(u*u+v*v)/(1.8*1.8)).exp()
                *(1.0+0.35*(2.6*u).cos()*(2.2*v).cos())/1.35
        });
        assert_eq!(peak(&values,side),at,"ringing plant must nominate supplied peak");
        let result=evaluate(&refine,&values,side,at);
        let error=result.0.map(|(x,y)|(x as f64-shift.0).hypot(y as f64-shift.1));
        if let Some(e)=error { assert!(e<=0.15,"accepted ringing displacement error={e}"); }
        ringing.push(json!({"truth":shift,"offset":result.0,"error":error,
            "reason":result.2,"evaluations":result.1}));
    }
    let mut fallback=Vec::new();
    let base=grid(side,at,|x,y|analytic(0,x,y,(0.0,0.0)));
    let mut nan=base.clone();nan[at.1*side+at.0+4]=f32::NAN;
    let mut inf=base.clone();inf[(at.1-4)*side+at.0]=f32::NEG_INFINITY;
    let mut plateau=base.clone();
    for y in 5..=7 {for x in 5..=7 {plateau[y*side+x]=1.0;}}
    let mut separated=base.clone();separated[at.1*side+at.0+2]=1.0;
    // This rotated convex quadratic has its unique continuous maximum outside
    // x=+0.5, yet its actual best integer sample is the supplied central sample.
    let outside=grid(side,at,|x,y| {
        let (u,v)=(x-0.625,y-0.25);0.9-0.01*(u*u-1.6*u*v+v*v)
    });
    assert_eq!(peak(&outside,side),at,"boundary plant must have a valid integer maximum");
    for (name,values) in [("flat",vec![0.75;side*side]),("nonfinite-nan",nan),
        ("nonfinite-infinity",inf),("plateau",plateau),("separated-equal-maxima",separated),
        ("outside-cell-maximum",outside)] {
        let result=evaluate(&refine,&values,side,at);
        assert!(result.0.is_none(),"{name}: candidate must retain original parabola");
        fallback.push(json!({"name":name,"reason":result.2,"evaluations":result.1}));
    }
    let edge_at=(3,6);
    let edge=grid(side,edge_at,|x,y|analytic(0,x,y,(0.0,0.0)));
    assert_eq!(peak(&edge,side),edge_at);
    let edge_result=evaluate(&refine,&edge,side,edge_at);
    assert!(edge_result.0.is_none(),"insufficient union support must retain original parabola");
    fallback.push(json!({"name":"support","reason":edge_result.2,"evaluations":edge_result.1}));
    assert_eq!(positive,9);
    json!({"status":"PASS","positive_count":positive,"positive":checks,"ringing":ringing,
        "fallback":fallback,"truth":"analytic maxima, independent of Lanczos interpolation",
        "limits":"coarse literal0.15px error checks; actual-NCC decisions supply finer accuracy evidence"})
}
