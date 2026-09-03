"""Fixed external predicate for the astigmatism peak fitter.

These literals are not produced by ``astiglib`` or ``truth_factory``.  They are
samples of two externally specified log-quadratic curves with sigma 1.35:

    log E_1(k) = -0.5 * ((k - 3.25) / 1.35)^2
    log E_2(k) = -0.5 * ((k - 7.375) / 1.35)^2

Completing the square fixes their vertices at 3.25 and 7.375, hence the split
at 4.125.  The estimator receives only the literal tables below.
"""

CURVE_1 = (
    0.055144116948348,
    0.249352208777296,
    0.651375231630207,
    0.982999392927830,
    0.856996891435279,
    0.431627624018743,
    0.125586571543005,
    0.021109656453671,
    0.002049854871806,
    0.000114992376996,
    0.000003726653172,
    0.000000069770669,
)

CURVE_2 = (
    0.000000330723828,
    0.000014379724592,
    0.000361193261057,
    0.005241223715883,
    0.043936933623407,
    0.212779987286225,
    0.595299888405200,
    0.962154491713458,
    0.898375315020466,
    0.484590389239007,
    0.151006544995509,
    0.027184461443714,
)

PEAK_1 = 3.25
PEAK_2 = 7.375
SPLIT = 4.125
TOLERANCE = 0.02

# Literal geometry predicate copied from the preregistered cardinal mapping.
# These values are not produced by the synthetic image factory.
CARDINAL_MAPPING = {
    "left": (7.0, 3.0, 4.0),
    "right": (7.0, 3.0, 4.0),
    "top": (3.0, 7.0, 4.0),
    "bottom": (3.0, 7.0, 4.0),
}
