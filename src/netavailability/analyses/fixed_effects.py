"""OLS with season fixed effects and HC3 standard errors, written with numpy (used by the points decomposition)."""
import numpy as np
import pandas as pd


def ols_fe(y, X, season, hc3=True):
    """OLS of y on X plus season dummies (one dropped) and intercept.
    Returns dict: beta (for X columns), se, p, r2, resid, n, k, df_resid.
    Written with numpy; HC3 = (X'X)^-1 X' diag(e^2/(1-h)^2) X (X'X)^-1."""
    from scipy import stats
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    s = pd.Series(list(season))
    levels = sorted(s.unique())
    D = np.column_stack([(s == L).values.astype(float) for L in levels[1:]]) if len(levels) > 1 else np.empty((len(y), 0))
    Z = np.column_stack([np.ones(len(y)), X, D])
    n, k = Z.shape
    ZtZi = np.linalg.inv(Z.T @ Z)
    b = ZtZi @ Z.T @ y
    e = y - Z @ b
    h = np.einsum("ij,jk,ik->i", Z, ZtZi, Z)
    if hc3:
        meat = Z.T @ (Z * (e ** 2 / (1 - h) ** 2)[:, None])
        V = ZtZi @ meat @ ZtZi
    else:
        V = ZtZi * (e @ e) / (n - k)
    se = np.sqrt(np.diag(V))
    t = b / se
    p = 2 * stats.t.sf(np.abs(t), n - k)
    r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
    nx = X.shape[1]
    return dict(beta=b[1:1 + nx], se=se[1:1 + nx], p=p[1:1 + nx], r2=r2, resid=e,
                n=n, k=k, df_resid=n - k, rss=e @ e, fitted=Z @ b)
