"""Root-run generated arithmetic smoke only; independent controls own admission."""
from dataclasses import asdict
import json
import numpy as np
import model


def main():
    h = w = 192
    y, x = np.mgrid[:h, :w].astype(np.float32)
    a = np.exp(-((x-48)**2/30+(y-55)**2/80)).astype(np.float32)
    b = np.exp(-((x-61)**2/80+(y-64)**2/20)).astype(np.float32)
    c = np.exp(-((x-133)**2/12+(y-130)**2/25)).astype(np.float32)
    signal = np.stack([800+900*a+250*b+700*c, 1100+700*a+700*b+400*c,
                       1100+700*a+700*b+400*c, 650+400*a+950*b+850*c])
    target = model._Predictor(signal)((5., 2., .35))
    train = (x >= 34) & (x < 77) & (y >= 32) & (y < 82)
    held = (x >= 112) & (x < 156) & (y >= 109) & (y < 155)
    fitted = model.fit(signal, target, train, protected_mask=held)
    result = model.evaluate(signal, target, fitted, held, rmse_limit4=(1.,)*4)
    print(json.dumps({"scope": "same-family arithmetic smoke, not independent quality",
                      "fit": asdict(fitted), "held": result}, indent=2))


if __name__ == "__main__":
    main()
