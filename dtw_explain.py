import numpy as np
import matplotlib.pyplot as plt

def dtw(x, y):
    N, M = len(x), len(y)
    D = np.zeros((N, M))

    # Step 1: 距离矩阵（欧式距离）
    for i in range(N):
        for j in range(M):
            D[i, j] = (x[i] - y[j]) ** 2

    # Step 2: 累计代价矩阵
    C = np.zeros((N, M))
    C[0, 0] = D[0, 0]

    for i in range(1, N):
        C[i, 0] = D[i, 0] + C[i-1, 0]
    for j in range(1, M):
        C[0, j] = D[0, j] + C[0, j-1]

    for i in range(1, N):
        for j in range(1, M):
            C[i, j] = D[i, j] + min(C[i-1, j], C[i, j-1], C[i-1, j-1])

    # Step 3: 回溯最优路径
    i, j = N - 1, M - 1
    path = [(i, j)]
    while i > 0 and j > 0:
        steps = [C[i-1, j], C[i, j-1], C[i-1, j-1]]
        argmin = np.argmin(steps)
        if argmin == 0:
            i -= 1
        elif argmin == 1:
            j -= 1
        else:
            i -= 1
            j -= 1
        path.append((i, j))
    while i > 0:
        i -= 1
        path.append((i, j))
    while j > 0:
        j -= 1
        path.append((i, j))

    path.reverse()
    return D, C, path

# 示例时间序列
x = np.array([1, 2, 3, 4, 2])
y = np.array([1, 1, 2, 3, 4, 3, 2])

# 执行 DTW
D, C, path = dtw(x, y)

# 📊 可视化
plt.figure(figsize=(10, 4))

plt.subplot(1, 2, 1)
plt.title("Distance Matrix (D)")
plt.imshow(D, origin='lower', cmap='Blues')
plt.colorbar()
for (i, j) in path:
    plt.plot(j, i, 'ro')  # 红色路径点

plt.subplot(1, 2, 2)
plt.title("Accumulated Cost (C)")
plt.imshow(C, origin='lower', cmap='Greens')
plt.colorbar()
for (i, j) in path:
    plt.plot(j, i, 'ro')

plt.tight_layout()
plt.show()
