inline uniform double distance_impl(uniform const double x[],
                                    uniform const double y[],
                                    uniform int nDim) {
    varying double partial = 0.0d;
    foreach (i = 0 ... nDim) {
        varying double delta = x[i] - y[i];
        partial += delta * delta;
    }
    // Per-lane sums remove the scalar dependency chain, changing addition order.
    return sqrt(reduce_add(partial));
}

export void assignments_ispc(uniform const double data[],
                             uniform const double centers[],
                             uniform int assignments[], uniform int N,
                             uniform int clusterBegin, uniform int clusterEnd,
                             uniform int pointBegin, uniform int pointEnd) {
    for (uniform int m = pointBegin; m < pointEnd; ++m) {
        uniform double minimum = 1e30d;
        uniform int best = -1;
        for (uniform int k = clusterBegin; k < clusterEnd; ++k) {
            uniform double d = distance_impl(data + m * N, centers + k * N, N);
            if (d < minimum) {
                minimum = d;
                best = k;
            }
        }
        assignments[m] = best;
    }
}
