import numpy as np
import matplotlib.pyplot as plt
from ypstruct import structure
import gng
import cv2

# Load Data
data = cv2.imread(f'triangle_0_0_3_20240828_225937_223579.bmp', 0)


h = data.shape[0]
w = data.shape[1]

points = []

for y in range(0, h):
    for x in range(0, w):
        # threshold the pixel     
        
        if data[y, x] > 0:            
                points.append([x, y])

points_np = np.array(points)
print(points_np)

# Neural Gas Parameters
params = structure()
params.N = 40
params.maxit = 50
params.L = 40
params.epsilon_b = 0.2
params.epsilon_n = 0.01
params.alpha = 0.5
params.delta = 0.995
params.T = 50

# Fit Neural Gas to Data
print("Fitting Growing Neural Gas Network ...")
net = gng.fit(points_np, params)

plt.figure()
plt.grid()
plt.scatter(data[:,0], data[:,1], s=2)
for i in range(0, params.N):
    for j in range(i+1, params.N):
        if net.C[i,j] == 1:
            plt.plot([net.w[i,0], net.w[j,0]], [net.w[i,1], net.w[j,1]], c='r')

plt.scatter(net.w[:,0], net.w[:,1], s=60, c='y', edgecolors='r')

plt.title('GNG for circles dataset')
plt.xlabel('x')
plt.ylabel('y')
plt.axis('equal')
plt.show()
