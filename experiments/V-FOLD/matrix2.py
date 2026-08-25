import numpy as np
np.set_printoptions(precision=4, suppress=True)
S = np.array([[0.4124564,0.3575761,0.1804375],
              [0.2126729,0.7151522,0.0721750],
              [0.0193339,0.1191920,0.9503041]])
A = np.array([[0.7460,-0.2365,-0.0588],
              [-0.5687,1.3442,0.2474],
              [-0.0624,0.1156,0.6584]])
def show(name, M):
    print(name)
    print(M)
    print("  row sums", M.sum(axis=1))
    print()
C = A @ S
show("inv(A@S) no normalisation", np.linalg.inv(C))
Cn = C / C.sum(axis=1, keepdims=True)
show("inv(rownorm(A@S))  [what the crate does]", np.linalg.inv(Cn))
M = np.linalg.inv(C); Mn = M / M.sum(axis=1, keepdims=True)
show("rownorm(inv(A@S))", Mn)
show("inv(A) ", np.linalg.inv(A))
Ai = np.linalg.inv(A); Ain = Ai/Ai.sum(axis=1,keepdims=True)
show("rownorm(inv(A))", Ain)
Sinv = np.linalg.inv(S)
show("Sinv @ inv(A) rownormed", (Sinv@Ai)/ (Sinv@Ai).sum(axis=1,keepdims=True))
# candidate: normalise COLUMNS of cam_from_srgb then invert
Cc = C / C.sum(axis=0, keepdims=True)
show("inv(colnorm(A@S))", np.linalg.inv(Cc))
# neutral response
print("neutral_response A@[1,1,1]:", A.sum(axis=1))
