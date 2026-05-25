import logging
import numpy as np
from ypstruct import structure

try:
    from skeletonization.settings import Settings
except ModuleNotFoundError:
    from settings import Settings

try:
    from numba import njit as _njit

    _NUMBA_AVAILABLE = True
except ImportError:
    _NUMBA_AVAILABLE = False

_logger = logging.getLogger(__name__)


def _fit_numpy_optimized(
    data: np.ndarray,
    N: int,
    maxit: int,
    L: int,
    epsilon_b: float,
    epsilon_n: float,
    alpha: float,
    delta: float,
    T: int,
    seed: int = 42,
) -> tuple:
    ndata = data.shape[0]
    ndim = data.shape[1]
    np.random.seed(seed)
    np.random.shuffle(data)

    xmin = np.amin(data, axis=0)
    xmax = np.amax(data, axis=0)

    w = np.zeros((N, ndim))
    E = np.zeros(N)
    C = np.zeros((N, N))
    t = np.zeros((N, N))
    K = 2
    nx = 0

    for i in range(K):
        w[i] = np.random.uniform(xmin, xmax, (1, ndim))

    for _it in range(maxit):
        for _l in range(ndata):
            nx += 1
            x = data[_l]

            if K < 2:
                continue

            d = np.sum((x - w[:K]) ** 2, axis=1)

            if K > 2:
                idx2 = np.argpartition(d, 2)[:2]
                if d[idx2[0]] <= d[idx2[1]]:
                    i, j = int(idx2[0]), int(idx2[1])
                else:
                    i, j = int(idx2[1]), int(idx2[0])
            else:
                i, j = (0, 1) if d[0] <= d[1] else (1, 0)

            t[i, :K] += 1
            t[:K, i] += 1
            E[i] += d[i]

            # Vectorized adaptation: winner + connected neighbors
            w[i] += epsilon_b * (x - w[i])
            neighbors = np.where(C[i, :K] == 1)[0]
            if neighbors.size > 0:
                w[neighbors] += epsilon_n * (x - w[neighbors])

            C[i, j] = 1
            C[j, i] = 1
            t[i, j] = 0
            t[j, i] = 0

            # Remove old links
            old_links = t[:K, :K] > T
            if old_links.any():
                C[:K, :K][old_links] = 0

            # Lazy reorder: only when a neuron actually dies
            nNeighbor = np.sum(C[:K, :K], axis=0)
            K_new = int(np.sum(nNeighbor > 0))

            if K_new < K:
                # Sort only active neurons; append inactive indices after
                active_order = np.argsort(-nNeighbor).tolist()
                inactive = [i for i in range(N) if i not in set(active_order)]
                keeporder = active_order + inactive
                C = C[keeporder, :][:, keeporder]
                t = t[keeporder, :][:, keeporder]
                w = w[keeporder, :]
                E = E[keeporder]

            K = K_new

            if K >= 2 and K < N and nx % L == 0:
                q = int(np.argmax(E[:K]))
                f = int(np.argmax(C[q, :K] * E[:K]))

                w[K] = (w[q] + w[f]) / 2
                C[K, :] = 0
                C[:, K] = 0
                t[K, :] = 0
                t[:, K] = 0

                C[q, f] = 0
                C[f, q] = 0
                C[q, K] = 1
                C[K, q] = 1
                C[f, K] = 1
                C[K, f] = 1

                E[q] *= alpha
                E[f] *= alpha
                E[K] = E[q]
                K += 1

            E[:K] *= delta

    return w, C, t, E


if _NUMBA_AVAILABLE:

    @_njit(cache=True)
    def _fit_numba(
        data, N, maxit, L, epsilon_b, epsilon_n, alpha, delta, T, seed
    ):
        ndata = data.shape[0]
        ndim = data.shape[1]

        # Seed for deterministic shuffle and neuron init
        np.random.seed(seed)

        # Fisher-Yates shuffle (np.random.shuffle not supported in njit)
        for idx in range(ndata - 1, 0, -1):
            swap = int(np.random.random() * (idx + 1))
            for dim in range(ndim):
                tmp = data[idx, dim]
                data[idx, dim] = data[swap, dim]
                data[swap, dim] = tmp

        xmin = np.empty(ndim)
        xmax = np.empty(ndim)
        for dim in range(ndim):
            xmin[dim] = data[0, dim]
            xmax[dim] = data[0, dim]
            for p in range(1, ndata):
                if data[p, dim] < xmin[dim]:
                    xmin[dim] = data[p, dim]
                if data[p, dim] > xmax[dim]:
                    xmax[dim] = data[p, dim]

        w = np.zeros((N, ndim))
        E = np.zeros(N)
        C = np.zeros((N, N))
        t = np.zeros((N, N))
        K = 2
        nx = 0

        for ki in range(K):
            for dim in range(ndim):
                w[ki, dim] = xmin[dim] + np.random.random() * (xmax[dim] - xmin[dim])

        for _it in range(maxit):
            for _l in range(ndata):
                nx += 1
                x = data[_l]

                if K < 2:
                    continue

                # Single-pass O(K) find best and second-best neurons
                d_best = 0.0
                d_second = 0.0
                for dim in range(ndim):
                    diff = x[dim] - w[0, dim]
                    d_best += diff * diff
                for dim in range(ndim):
                    diff = x[dim] - w[1, dim]
                    d_second += diff * diff

                best = 0
                second = 1
                if d_second < d_best:
                    best, second = 1, 0
                    d_best, d_second = d_second, d_best

                for k in range(2, K):
                    dk = 0.0
                    for dim in range(ndim):
                        diff = x[dim] - w[k, dim]
                        dk += diff * diff
                    if dk < d_best:
                        second = best
                        d_second = d_best
                        best = k
                        d_best = dk
                    elif dk < d_second:
                        second = k
                        d_second = dk

                i = best
                j = second

                # Aging
                for k in range(K):
                    t[i, k] += 1.0
                    t[k, i] += 1.0

                E[i] += d_best

                # Adaptation: winner + connected neighbors
                for dim in range(ndim):
                    w[i, dim] += epsilon_b * (x[dim] - w[i, dim])
                for k in range(K):
                    if k != i and C[i, k] > 0.0:
                        for dim in range(ndim):
                            w[k, dim] += epsilon_n * (x[dim] - w[k, dim])

                # Create link
                C[i, j] = 1.0
                C[j, i] = 1.0
                t[i, j] = 0.0
                t[j, i] = 0.0

                # Remove old links
                any_died = False
                for a in range(K):
                    for b in range(K):
                        if t[a, b] > T:
                            C[a, b] = 0.0

                # Count live neurons
                K_new = 0
                for a in range(K):
                    has_neighbor = False
                    for b in range(K):
                        if C[a, b] > 0.0:
                            has_neighbor = True
                            break
                    if has_neighbor:
                        K_new += 1

                # Lazy reorder: only when K shrinks
                if K_new < K:
                    nNeighbor = np.zeros(N)
                    for a in range(K):
                        for b in range(K):
                            nNeighbor[a] += C[a, b]
                    keeporder = np.argsort(-nNeighbor)

                    w_new = np.zeros((N, ndim))
                    E_new = np.zeros(N)
                    C_new = np.zeros((N, N))
                    t_new = np.zeros((N, N))
                    for a in range(N):
                        ka = keeporder[a]
                        w_new[a] = w[ka]
                        E_new[a] = E[ka]
                        for b in range(N):
                            kb = keeporder[b]
                            C_new[a, b] = C[ka, kb]
                            t_new[a, b] = t[ka, kb]
                    w = w_new
                    E = E_new
                    C = C_new
                    t = t_new

                K = K_new

                # Add new node
                if K >= 2 and K < N and nx % L == 0:
                    q = 0
                    for a in range(1, K):
                        if E[a] > E[q]:
                            q = a
                    f = -1
                    best_ce = -1.0
                    for a in range(K):
                        val = C[q, a] * E[a]
                        if val > best_ce:
                            best_ce = val
                            f = a

                    if f >= 0:
                        for dim in range(ndim):
                            w[K, dim] = (w[q, dim] + w[f, dim]) / 2.0
                        for a in range(N):
                            C[K, a] = 0.0
                            C[a, K] = 0.0
                            t[K, a] = 0.0
                            t[a, K] = 0.0

                        C[q, f] = 0.0
                        C[f, q] = 0.0
                        C[q, K] = 1.0
                        C[K, q] = 1.0
                        C[f, K] = 1.0
                        C[K, f] = 1.0

                        E[q] *= alpha
                        E[f] *= alpha
                        E[K] = E[q]
                        K += 1

                # Decrease errors
                for a in range(K):
                    E[a] *= delta

        return w, C, t, E


def fit(data: np.ndarray, params: Settings) -> structure:
    N = params.N
    maxit = params.maxit
    L = params.L
    epsilon_b = params.epsilon_b
    epsilon_n = params.epsilon_n
    alpha_val = params.alpha
    delta_val = params.delta
    T = params.T
    seed = getattr(params, "seed", 42)

    if _NUMBA_AVAILABLE:
        w, C, t, E = _fit_numba(
            data.astype(np.float64), N, maxit, L,
            epsilon_b, epsilon_n, alpha_val, delta_val, T, seed,
        )
    else:
        w, C, t, E = _fit_numpy_optimized(
            data, N, maxit, L,
            epsilon_b, epsilon_n, alpha_val, delta_val, T, seed,
        )

    net = structure()
    net.w = w
    net.C = C
    net.t = t
    net.E = E
    return net


_logger.info(
    "GNG backend: %s", "numba (JIT)" if _NUMBA_AVAILABLE else "numpy (optimized)"
)


def get_list_points_from_image(image: np.ndarray, threshold: float = 0.0) -> np.ndarray:
    h = image.shape[0]
    w = image.shape[1]
    points = []
    for y in range(0, h):
        for x in range(0, w):
            if image[y, x] > threshold:
                points.append([y, x])
    return np.array(points)
