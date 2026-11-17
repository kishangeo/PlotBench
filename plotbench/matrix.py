"""PlotBench matrix core: gridding, conversion, images and 2-D operations. No GUI code.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
A matrix is a 2-D array M[row, col] with an extent (x0, x1, y0, y1): columns span x0..x1, rows span y0..y1.
"""
import numpy as np
from scipy import interpolate, ndimage

from .analysis import eval_formula


def axes_of(M, extent):
    ny, nx = M.shape; x0, x1, y0, y1 = extent
    return np.linspace(x0, x1, nx), np.linspace(y0, y1, ny)


def from_formula(expr, nrows, ncols, extent):
    """Values from an expression in x, y (cell centres from extent) and i, j (1-based row, column)."""
    xs, ys = axes_of(np.empty((nrows, ncols)), extent)
    X, Y = np.meshgrid(xs, ys); I, J = np.meshgrid(np.arange(1, nrows + 1), np.arange(1, ncols + 1), indexing="ij")
    out = eval_formula(expr, {"x": X.ravel(), "y": Y.ravel(), "i": I.ravel(), "j": J.ravel()}, X.size)
    return out.reshape(nrows, ncols)


def xyz_to_matrix(x, y, z, nx=100, ny=100, method="linear"):
    """Grid scattered (or regular) XYZ data. method: linear, cubic, nearest. Returns M, extent."""
    x, y, z = (np.asarray(v, float) for v in (x, y, z)); m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    x, y, z = x[m], y[m], z[m]
    ux, uy = np.unique(x), np.unique(y)
    if ux.size * uy.size == x.size and ux.size > 1 and uy.size > 1:  # already a full regular grid: no interpolation
        M = np.full((uy.size, ux.size), np.nan); M[np.searchsorted(uy, y), np.searchsorted(ux, x)] = z
        return M, [ux[0], ux[-1], uy[0], uy[-1]]
    xs, ys = np.linspace(x.min(), x.max(), int(nx)), np.linspace(y.min(), y.max(), int(ny))
    X, Y = np.meshgrid(xs, ys)
    return interpolate.griddata((x, y), z, (X, Y), method=method), [xs[0], xs[-1], ys[0], ys[-1]]


def matrix_to_xyz(M, extent):
    xs, ys = axes_of(M, extent); X, Y = np.meshgrid(xs, ys)
    return X.ravel(), Y.ravel(), np.asarray(M, float).ravel()


def image_to_matrix(path, mode="Grayscale"):
    """Read PNG/JPG/TIFF/BMP. mode: Grayscale, Red, Green, Blue. Row 0 = bottom of the image (y up)."""
    from PIL import Image
    img = np.asarray(Image.open(path).convert("RGB"), float)
    ch = {"Red": img[..., 0], "Green": img[..., 1], "Blue": img[..., 2]}.get(mode)
    M = ch if ch is not None else img @ [0.299, 0.587, 0.114]
    M = M[::-1]
    return M, [0, M.shape[1] - 1, 0, M.shape[0] - 1]


def resample(M, rows, cols, order=1):
    M = np.asarray(M, float)
    return ndimage.zoom(np.nan_to_num(M), (rows / M.shape[0], cols / M.shape[1]), order=order)


def smooth2d(M, method="Gaussian", size=3.0):
    M = np.nan_to_num(np.asarray(M, float))
    if method == "Gaussian": return ndimage.gaussian_filter(M, sigma=size)
    if method == "Median": return ndimage.median_filter(M, size=max(1, int(size)))
    if method == "Mean": return ndimage.uniform_filter(M, size=max(1, int(size)))
    raise ValueError(method)


def fft2_magnitude(M):
    """Centred 2-D amplitude spectrum, log10(1 + |F|)."""
    M = np.nan_to_num(np.asarray(M, float)); F = np.fft.fftshift(np.fft.fft2(M - M.mean()))
    return np.log10(1 + np.abs(F))


def profile(M, extent, along="row", at=0.0):
    """Line profile through the matrix at y = at (along row) or x = at (along column)."""
    xs, ys = axes_of(M, extent)
    if along == "row":
        i = int(np.argmin(np.abs(ys - at))); return xs, np.asarray(M)[i]
    j = int(np.argmin(np.abs(xs - at))); return ys, np.asarray(M)[:, j]


def transform(M, extent, op):
    M = np.asarray(M, float); x0, x1, y0, y1 = extent
    if op == "Transpose": return M.T.copy(), [y0, y1, x0, x1]
    if op == "Flip horizontal": return M[:, ::-1].copy(), extent
    if op == "Flip vertical": return M[::-1].copy(), extent
    if op == "Rotate 90 (counter-clockwise)": return np.rot90(M).copy(), [y0, y1, x0, x1]
    if op == "Rotate 90 (clockwise)": return np.rot90(M, -1).copy(), [y0, y1, x0, x1]
    if op == "Inverse (square matrix)": return np.linalg.inv(M), extent
    raise ValueError(op)


TRANSFORMS = ["Transpose", "Flip horizontal", "Flip vertical", "Rotate 90 (counter-clockwise)", "Rotate 90 (clockwise)",
              "Inverse (square matrix)"]


def image_filter(M, op, value=None):
    """Edge detection and simple image operations on a matrix."""
    M = np.nan_to_num(np.asarray(M, float))
    if op == "Edge detection (Sobel magnitude)": return np.hypot(ndimage.sobel(M, 1), ndimage.sobel(M, 0))
    if op == "Laplacian (edges, second derivative)": return ndimage.laplace(M)
    if op == "Threshold (1 above value, 0 below)": return (M >= (np.nanmean(M) if value is None else value)).astype(float)
    if op == "Invert (max + min - value)": return M.max() + M.min() - M
    if op == "Log10 (values <= 0 become NaN)": return np.where(M > 0, np.log10(np.where(M > 0, M, 1)), np.nan)
    if op == "Normalise to 0-1": return (M - M.min()) / (np.ptp(M) or 1)
    if op == "Gradient magnitude": gy, gx = np.gradient(M); return np.hypot(gx, gy)
    if op == "Clip to range": lo, hi = value; return np.clip(M, lo, hi)
    raise ValueError(op)


FILTERS = ["Edge detection (Sobel magnitude)", "Laplacian (edges, second derivative)", "Threshold (1 above value, 0 below)",
           "Invert (max + min - value)", "Log10 (values <= 0 become NaN)", "Normalise to 0-1", "Gradient magnitude"]


def arithmetic(Ma, op, Mb):
    """Element-wise A op B, where B is a matrix of the same shape or a number."""
    a = np.asarray(Ma, float); b = Mb if np.isscalar(Mb) else np.asarray(Mb, float)
    if not np.isscalar(b) and b.shape != a.shape: raise ValueError(f"Shapes differ: {a.shape} and {b.shape}")
    with np.errstate(divide="ignore", invalid="ignore"):
        return {"+": a + b, "-": a - b, "*": a * b, "/": a / b, "^": a ** b, "max": np.maximum(a, b), "min": np.minimum(a, b)}[op]
