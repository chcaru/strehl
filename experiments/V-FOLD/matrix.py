import numpy as np
S = np.array([[0.4124564,0.3575761,0.1804375],
              [0.2126729,0.7151522,0.0721750],
              [0.0193339,0.1191920,0.9503041]])
A = np.array([[0.7460,-0.2365,-0.0588],
              [-0.5687,1.3442,0.2474],
              [-0.0624,0.1156,0.6584]], dtype=np.float32).astype(np.float64)
cam_from_srgb = A @ S
print("cam_from_srgb raw:\n", cam_from_srgb)
rn = cam_from_srgb / cam_from_srgb.sum(axis=1, keepdims=True)
print("row-normalised:\n", rn)
M = np.linalg.inv(rn)
np.set_printoptions(precision=6, suppress=True)
print("camera_to_srgb matrix (out = M @ cam):\n", M)
print("row sums:", M.sum(axis=1))
print()
print("R row: %.4f %.4f %.4f" % tuple(M[0]))
print("G row: %.4f %.4f %.4f" % tuple(M[1]))
print("B row: %.4f %.4f %.4f" % tuple(M[2]))
print("green-in-red / red-weight = %.4f" % (abs(M[0][1])/M[0][0]))
print("red-in-green / green-weight = %.4f" % (abs(M[1][0])/M[1][1]))
