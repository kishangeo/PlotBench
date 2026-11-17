"""PlotBench analysis core: fitting, statistics, signal processing, peaks.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Pure numpy/scipy functions with no GUI dependency, so they can be tested alone.
"""
import numpy as np
from scipy import optimize, signal, stats, integrate, interpolate

# ---------------------------------------------------------------- numbers typed by people
_SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")


def parse_number(text):
    """'2400', '1e-18', '1E-18', '10^-18', '10^(-18)', '10**-18', '10⁻¹⁸', '2.5x10^3', '2.5×10^3', '2.5*10^3', '−3' (Unicode minus),
    '1,5' (decimal comma), '1/3', '50%' -> float. Raises ValueError with a hint for anything else."""
    import re
    s0 = str(text).strip(); s = s0.replace("−", "-").replace("–", "-").replace(" ", "").replace("\u00a0", "")
    s = re.sub(r"10([⁻⁺]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+)", lambda m: "10^" + m.group(1).translate(_SUP), s)
    if not s: raise ValueError("empty")
    if re.fullmatch(r"[-+]?\d+,\d+", s): s = s.replace(",", ".")
    if s.endswith("%"): return parse_number(s[:-1]) / 100
    m = re.fullmatch(r"([-+]?)((?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)?[x×X*·]?10(?:\^|\*\*)\(?([-+]?\d+(?:\.\d+)?)\)?", s)
    if m: return (-1.0 if m.group(1) == "-" else 1.0) * (float(m.group(2)) if m.group(2) else 1.0) * 10 ** float(m.group(3))
    m = re.fullmatch(r"([-+]?(?:\d+\.?\d*|\.\d+))/((?:\d+\.?\d*|\.\d+))", s)
    if m: return float(m.group(1)) / float(m.group(2))
    try: return float(s)
    except ValueError: raise ValueError(f"'{s0}' is not a number; write it as 2400, 1e-18, 10^-18 or 2.5x10^3") from None


# ---------------------------------------------------------------- formulas
SAFE_NS = {k: getattr(np, k) for k in (
    "sin cos tan arcsin arccos arctan arctan2 sinh cosh tanh exp log log10 log2 "
    "sqrt abs pi e floor ceil round sign maximum minimum where cumsum diff mean std "
    "min max sum power hypot radians degrees isnan nan").split()}
SAFE_NS["ln"] = np.log

# Europium and cerium anomalies from ppm values, normalised to CI chondrite (McDonough & Sun 1995):
# Eu/Eu* = Eu_N / sqrt(Sm_N * Gd_N);  Ce/Ce* = Ce_N / sqrt(La_N * Pr_N)
_CI = {"La": 0.237, "Ce": 0.613, "Pr": 0.0928, "Nd": 0.457, "Sm": 0.148, "Eu": 0.0563, "Gd": 0.199}


def _norm(v, el):
    """Chondrite-normalised value; zero, negative or missing concentrations give NaN instead of a warning or inf."""
    v = np.asarray(v, float); return np.where(v > 0, v, np.nan) / _CI[el]


def eu_anomaly(Eu, Sm, Gd):
    """Eu/Eu* = Eu_N / sqrt(Sm_N * Gd_N)."""
    with np.errstate(all="ignore"): return _norm(Eu, "Eu") / np.sqrt(_norm(Sm, "Sm") * _norm(Gd, "Gd"))


def ce_anomaly(Ce, La, Pr):
    """Ce/Ce* = Ce_N / sqrt(La_N * Pr_N)."""
    with np.errstate(all="ignore"): return _norm(Ce, "Ce") / np.sqrt(_norm(La, "La") * _norm(Pr, "Pr"))


def ce_anomaly_nd(Ce, La, Nd):
    """Ce/Ce* without Pr: Ce_N / (La_N^(2/3) * Nd_N^(1/3)), Ce* interpolated between La and Nd on a log scale."""
    with np.errstate(all="ignore"): return _norm(Ce, "Ce") / (_norm(La, "La") ** (2 / 3) * _norm(Nd, "Nd") ** (1 / 3))


SAFE_NS.update(eu_anomaly=eu_anomaly, ce_anomaly=ce_anomaly, ce_anomaly_nd=ce_anomaly_nd, eu_star=eu_anomaly, ce_star=ce_anomaly)


import ast  # noqa: E402
from functools import lru_cache  # noqa: E402

_OK_NODES = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp, ast.Call, ast.Name, ast.Constant,
             ast.Load, ast.operator, ast.unaryop, ast.cmpop, ast.boolop)


class FormulaError(ValueError):
    pass


@lru_cache(maxsize=512)
def compile_formula(expr):
    """Parse and check a formula before it is evaluated. Only arithmetic, comparisons, names and calls to the
    whitelisted maths functions are allowed: no attributes, subscripts, lambdas or comprehensions. Formulas are
    stored in project files, so this is what stops a crafted project from running arbitrary code when opened."""
    if len(expr) > 2000: raise FormulaError("Formula is too long.")
    try: tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError as e: raise FormulaError(f"Formula syntax error: {e.msg}") from None
    for node in ast.walk(tree):
        if not isinstance(node, _OK_NODES): raise FormulaError(f"Not allowed in a formula: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id.startswith("_"): raise FormulaError(f"Not allowed in a formula: {node.id}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_NS or node.keywords:
                raise FormulaError("Only these functions may be called: " + ", ".join(sorted(k for k in SAFE_NS if callable(SAFE_NS[k]))))
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float, bool, str)):
            raise FormulaError("Unsupported constant in formula.")
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) > 200: raise FormulaError("Text too long.")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow) and isinstance(node.right, ast.Constant) \
                and isinstance(node.right.value, (int, float)) and abs(node.right.value) > 1000:
            raise FormulaError("Exponent too large.")
    for node in ast.walk(tree):  # whole numbers become floats: 9**9**9 then overflows at once instead of hanging on big integers
        if isinstance(node, ast.Constant) and type(node.value) is int: node.value = float(node.value)
    return compile(tree, "<formula>", "eval")


class _ToElementwise(ast.NodeTransformer):
    """and/or/not and chained comparisons -> element-wise &, |, ~ on the parsed tree, so precedence stays correct."""

    def visit_BoolOp(self, node):
        self.generic_visit(node); op = ast.BitAnd() if isinstance(node.op, ast.And) else ast.BitOr(); out = node.values[0]
        for v in node.values[1:]: out = ast.BinOp(left=out, op=op, right=v)
        return out

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        return ast.UnaryOp(op=ast.Invert(), operand=node.operand) if isinstance(node.op, ast.Not) else node

    def visit_Compare(self, node):
        self.generic_visit(node)
        if len(node.ops) == 1: return node
        parts, left = [], node.left
        for op, right in zip(node.ops, node.comparators): parts.append(ast.Compare(left=left, ops=[op], comparators=[right])); left = right
        out = parts[0]
        for p_ in parts[1:]: out = ast.BinOp(left=out, op=ast.BitAnd(), right=p_)
        return out


def eval_condition(expr, columns, n_rows):
    """Row filter such as 'SiO2 > 45 and Class == "iron"' -> boolean array. Same whitelist as formulas."""
    compile_formula(expr)  # validation only
    tree = ast.fix_missing_locations(_ToElementwise().visit(ast.parse(expr.strip(), mode="eval")))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and type(node.value) is int: node.value = float(node.value)
    with np.errstate(all="ignore"):
        out = eval(compile(tree, "<condition>", "eval"), {"__builtins__": {}}, {**SAFE_NS, **columns})
    return np.broadcast_to(np.asarray(out, bool), (n_rows,)).copy()


def eval_formula(expr, columns, n_rows):
    """Evaluate a column formula like 'A*2 + sin(B)'. columns: {name: array}."""
    code = compile_formula(expr)
    ns = {**SAFE_NS, "i": np.arange(1, n_rows + 1), **columns}  # caller's names (e.g. matrix i, j) win
    try:
        with np.errstate(all="ignore"): out = eval(code, {"__builtins__": {}}, ns)  # safe: code passed the whitelist above
    except OverflowError: raise FormulaError("Number too large in formula.") from None
    try: out = np.asarray(out, dtype=float)
    except (TypeError, ValueError):  # text results, e.g. where(SiO2 > 63, "Felsic", "Mafic")
        out = np.asarray(out, dtype=object)
        return np.full(n_rows, out.item(), dtype=object) if out.ndim == 0 else out
    return np.full(n_rows, float(out)) if out.ndim == 0 else out


# ---------------------------------------------------------------- fitting
def _gauss(x, y0, xc, w, A): return y0 + A / (w * np.sqrt(np.pi / 2)) * np.exp(-2 * ((x - xc) / w) ** 2)
def _lorentz(x, y0, xc, w, A): return y0 + 2 * A / np.pi * w / (4 * (x - xc) ** 2 + w ** 2)
def _expdec1(x, y0, A1, t1): return y0 + A1 * np.exp(-x / t1)
def _expdec2(x, y0, A1, t1, A2, t2): return y0 + A1 * np.exp(-x / t1) + A2 * np.exp(-x / t2)
def _expgro1(x, y0, A1, t1): return y0 + A1 * np.exp(x / t1)
def _boltzmann(x, A1, A2, x0, dx): return A2 + (A1 - A2) / (1 + np.exp((x - x0) / dx))
def _logistic(x, A1, A2, x0, p): return A2 + (A1 - A2) / (1 + (np.abs(x) / x0) ** p)
def _allometric(x, a, b): return a * np.abs(x) ** b
def _hill(x, START, END, k, n): return START + (END - START) * x ** n / (k ** n + x ** n)
def _voigt_pv(x, y0, xc, w, A, mu): return y0 + A * (mu * 2 / np.pi * w / (4 * (x - xc) ** 2 + w ** 2)
                                                   + (1 - mu) * np.sqrt(4 * np.log(2)) / (np.sqrt(np.pi) * w)
                                                   * np.exp(-4 * np.log(2) / w ** 2 * (x - xc) ** 2))
def _sine(x, y0, A, w, xc): return y0 + A * np.sin(np.pi * (x - xc) / w)
def _line(x, a, b): return a + b * x


def _peak_guess(x, y):
    i = int(np.argmax(y)); y0 = float(np.min(y)); h = float(y[i] - y0)
    half = np.where(y - y0 >= h / 2)[0]
    w = float(x[half[-1]] - x[half[0]]) if half.size > 1 else float(np.ptp(x)) / 10 or 1.0
    return y0, float(x[i]), w, h * w * 1.2


def _decay_guess(x, y):
    return float(y[-1]), float(y[0] - y[-1]), float(np.ptp(x)) / 3 or 1.0


MODELS = {
    "Gaussian": (_gauss, lambda x, y: _peak_guess(x, y)),
    "Lorentzian": (_lorentz, lambda x, y: _peak_guess(x, y)),
    "PseudoVoigt": (_voigt_pv, lambda x, y: (*_peak_guess(x, y), 0.5)),
    "ExpDec1": (_expdec1, _decay_guess),
    "ExpDec2": (_expdec2, lambda x, y: (*_decay_guess(x, y), float(y[0] - y[-1]) / 2, float(np.ptp(x)) / 10 or 1.0)),
    "ExpGrow1": (_expgro1, lambda x, y: (float(y[0]), 1.0, float(np.ptp(x)) / 3 or 1.0)),
    "Boltzmann": (_boltzmann, lambda x, y: (float(y[0]), float(y[-1]), float(np.median(x)), float(np.ptp(x)) / 10 or 1.0)),
    "Logistic": (_logistic, lambda x, y: (float(y[0]), float(y[-1]), float(np.median(np.abs(x))) or 1.0, 2.0)),
    "Allometric (a*x^b)": (_allometric, lambda x, y: (1.0, 1.0)),
    "Hill": (_hill, lambda x, y: (float(y[0]), float(y[-1]), float(np.median(x)) or 1.0, 1.0)),
    "Sine": (_sine, lambda x, y: (float(np.mean(y)), float(np.ptp(y)) / 2, float(np.ptp(x)) / 4 or 1.0, 0.0)),
    "Line (a+b*x)": (_line, lambda x, y: (0.0, 1.0)),
}

from scipy import special as _sp  # noqa: E402


def _expdec3(x, y0, A1, t1, A2, t2, A3, t3): return y0 + A1 * np.exp(-x / t1) + A2 * np.exp(-x / t2) + A3 * np.exp(-x / t3)
def _expassoc(x, y0, A1, t1): return y0 + A1 * (1 - np.exp(-x / t1))
def _power(x, y0, A, p): return y0 + A * np.abs(x) ** p
def _logfn(x, y0, A): return y0 + A * np.log(np.abs(x))
def _langmuir(x, qmax, K): return qmax * K * x / (1 + K * x)
def _mm(x, Vmax, Km): return Vmax * x / (Km + x)
def _gompertz(x, a, k, xc): return a * np.exp(-np.exp(-k * (x - xc)))
def _weibull_cdf(x, A, lam, k): return A * (1 - np.exp(-(np.abs(x) / lam) ** k))
def _voigt(x, y0, xc, A, wG, wL): return y0 + A * _sp.voigt_profile(x - xc, np.abs(wG), np.abs(wL))
def _lognormal_pk(x, y0, xc, w, A): return y0 + A / (np.sqrt(2 * np.pi) * w * np.abs(x)) * np.exp(-np.log(np.abs(x) / xc) ** 2 / (2 * w ** 2))
def _erfstep(x, y0, A, xc, w): return y0 + A / 2 * (1 + _sp.erf((x - xc) / (w * np.sqrt(2))))
def _doseresp(x, A1, A2, LOGx0, p): return A1 + (A2 - A1) / (1 + 10 ** ((LOGx0 - x) * p))
def _arrhenius(x, A, Ea): return A * np.exp(-Ea / (8.314462618 * x))
def _extreme(x, y0, xc, w, A): z = (x - xc) / w; return y0 + A * np.exp(-np.exp(-z) - z + 1)
def _asym2sig(x, y0, xc, A, w1, w2, w3):
    return y0 + A / (1 + np.exp(-(x - xc + w1 / 2) / w2)) * (1 - 1 / (1 + np.exp(-(x - xc - w1 / 2) / w3)))


def _arrh_guess(x, y):
    """Linearise: ln y = ln A - Ea/(R T)."""
    m = (y > 0) & (x > 0)
    if m.sum() < 2: return 1.0, 10000.0
    b, a = np.polyfit(1 / x[m], np.log(y[m]), 1); return float(np.exp(a)), float(-b * 8.314462618)


def _sig_guess(x, y): return float(y[0]), float(y[-1] - y[0]), float(np.median(x)), float(np.ptp(x)) / 10 or 1.0


MODELS.update({
    "ExpDec3": (_expdec3, lambda x, y: (*_decay_guess(x, y), float(y[0] - y[-1]) / 3, float(np.ptp(x)) / 10 or 1.0,
                                        float(y[0] - y[-1]) / 10, float(np.ptp(x)) / 30 or 1.0)),
    "ExpAssoc (rise to max)": (_expassoc, lambda x, y: (float(y[0]), float(y[-1] - y[0]), float(np.ptp(x)) / 3 or 1.0)),
    "Power (y0 + A*x^p)": (_power, lambda x, y: (0.0, 1.0, 1.0)),
    "Logarithm (y0 + A*ln x)": (_logfn, lambda x, y: (float(np.mean(y)), 1.0)),
    "Langmuir isotherm": (_langmuir, lambda x, y: (float(np.max(y)) * 1.2, 1.0 / (float(np.median(x)) or 1.0))),
    "Michaelis-Menten": (_mm, lambda x, y: (float(np.max(y)) * 1.2, float(np.median(x)) or 1.0)),
    "Gompertz": (_gompertz, lambda x, y: (float(np.max(y)), 4.0 / (float(np.ptp(x)) or 1.0), float(np.median(x)))),
    "Weibull CDF": (_weibull_cdf, lambda x, y: (float(np.max(y)), float(np.median(np.abs(x))) or 1.0, 1.5)),
    "Voigt": (_voigt, lambda x, y: (lambda g: (g[0], g[1], g[3], g[2] / 3.6, g[2] / 4))(_peak_guess(x, y))),
    "LogNormal peak": (_lognormal_pk, lambda x, y: (lambda g: (g[0], g[1] if g[1] > 0 else 1.0, 0.3, g[3]))(_peak_guess(x, y))),
    "Error-function step": (_erfstep, _sig_guess),
    "Dose-response (log x)": (_doseresp, lambda x, y: (float(y[0]), float(y[-1]), float(np.median(x)), 1.0)),
    "Arrhenius (x = T in K)": (_arrhenius, lambda x, y: _arrh_guess(x, y)),
    "Extreme value peak": (_extreme, lambda x, y: (lambda g: (g[0], g[1], g[2] / 2.5, g[3] / g[2]))(_peak_guess(x, y))),
    "Asymmetric double sigmoid": (_asym2sig, lambda x, y: (lambda g: (g[0], g[1], (np.max(y) - g[0]) * 1.2, g[2], g[2] / 5, g[2] / 5))(_peak_guess(x, y))),
})


class FitResult(dict):
    """Parameters, errors and goodness-of-fit, plus a callable for the fitted curve."""


def _gof(y, yfit, n_par):
    res = y - yfit
    ss_res = float(np.sum(res ** 2)); ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    dof = max(len(y) - n_par, 1)
    r2 = 1 - ss_res / ss_tot if ss_tot else float("nan")
    return {"N": len(y), "DOF": dof, "SS_res": ss_res, "Reduced_ChiSq": ss_res / dof, "R2": r2,
            "Adj_R2": 1 - (1 - r2) * (len(y) - 1) / dof, "RMSE": np.sqrt(ss_res / dof)}


def _clean(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    return x[m], y[m]


def fit_polynomial(x, y, order=1):
    x, y = _clean(x, y)
    coef, cov = np.polyfit(x, y, order, cov=True) if len(x) > order + 2 else (np.polyfit(x, y, order), None)
    err = np.sqrt(np.diag(cov)) if cov is not None else np.full(order + 1, np.nan)
    names = [f"B{k}" for k in range(order, -1, -1)]  # highest power first, like np.polyfit
    r = FitResult(model=f"Polynomial (order {order})", params=dict(zip(names, coef)), errors=dict(zip(names, err)),
                  func=lambda t, c=coef: np.polyval(c, t))
    r.update(_gof(y, np.polyval(coef, x), order + 1))
    if cov is not None:
        r["conf_band"], r["pred_band"] = _bands(lambda t, *c: np.polyval(c, t), x, np.array(coef, float),
                                                list(range(order + 1)), cov, r["DOF"], r["Reduced_ChiSq"])
    if order == 1:
        lr = stats.linregress(x, y)
        r.update(Pearson_r=lr.rvalue, p_slope=lr.pvalue)
    return r


def model_params(name, user_params=None):
    if name == "User": return list(user_params)
    f = MODELS[name][0]; return list(f.__code__.co_varnames[1:f.__code__.co_argcount])


def initial_guess(name, x, y):
    x, y = _clean(x, y); return list(MODELS[name][1](x, y))


def _bands(f, x_fit, popt, free, cov, dof, s2, level=0.95):
    """Return functions giving confidence and prediction bands (delta method, numerical Jacobian)."""
    tcrit = stats.t.ppf(0.5 + level / 2, dof)

    def half_width(t, pred):
        t = np.asarray(t, float); J = np.empty((t.size, len(free)))
        for k, i in enumerate(free):
            h = 1e-6 * max(abs(popt[i]), 1e-3); p1 = popt.copy(); p2 = popt.copy(); p1[i] += h; p2[i] -= h
            J[:, k] = (f(t, *p1) - f(t, *p2)) / (2 * h)
        var = np.einsum("ij,jk,ik->i", J, cov, J) + (s2 if pred else 0)
        return tcrit * np.sqrt(np.abs(var))

    def conf(t): yv = f(np.asarray(t, float), *popt); d = half_width(t, False); return yv - d, yv + d
    def pred(t): yv = f(np.asarray(t, float), *popt); d = half_width(t, True); return yv - d, yv + d
    return conf, pred


def param_table(r):
    """Rows: name, value, SE, t, p, 95% CI low, high, fixed."""
    dof = r["DOF"]; tcrit = stats.t.ppf(0.975, dof); rows = []
    for k, v in r["params"].items():
        se = r["errors"][k]; fixed = k in r.get("fixed", {})
        t = v / se if se and np.isfinite(se) and not fixed else np.nan
        p = 2 * stats.t.sf(abs(t), dof) if np.isfinite(t) else np.nan
        rows.append([k, v, se, t, p, v - tcrit * se if not fixed else v, v + tcrit * se if not fixed else v, "fixed" if fixed else ""])
    return rows


def fit_model(x, y, name, p0=None, user_expr=None, user_params=None, fixed=None, bounds=None, yerr=None):
    """Nonlinear least squares. name from MODELS or 'User' with user_expr.
    fixed: {param: value} held constant. bounds: {param: (lo, hi)}. yerr: per-point errors used as weights."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    if yerr is not None:
        yerr = np.asarray(yerr, float); m &= np.isfinite(yerr) & (yerr > 0)
    x, y = x[m], y[m]; yerr = yerr[m] if yerr is not None else None
    pnames = model_params(name, user_params)
    if name == "User":
        def f(t, *p): return eval_formula(user_expr, dict(zip(pnames, p), x=t), len(t))
        p0 = list(p0) if p0 else [1.0] * len(pnames)
    else:
        f = MODELS[name][0]; p0 = list(p0) if p0 else list(MODELS[name][1](x, y))
    fixed = {k: float(v) for k, v in (fixed or {}).items() if k in pnames}
    for k, v in fixed.items(): p0[pnames.index(k)] = v
    free = [i for i, n in enumerate(pnames) if n not in fixed]
    if not free: raise ValueError("All parameters are fixed.")
    full = np.array(p0, float)

    def g(t, *q):
        p = full.copy(); p[free] = q; return f(t, *p)

    lo = [(bounds or {}).get(pnames[i], (-np.inf, np.inf))[0] for i in free]
    hi = [(bounds or {}).get(pnames[i], (-np.inf, np.inf))[1] for i in free]
    start = [min(max(full[i], l + 1e-12 if np.isfinite(l) else full[i]), h - 1e-12 if np.isfinite(h) else full[i])
             for i, l, h in zip(free, lo, hi)]
    q, qcov = optimize.curve_fit(g, x, y, p0=start, bounds=(lo, hi), sigma=yerr, absolute_sigma=yerr is not None,
                                 maxfev=20000)
    popt = full.copy(); popt[free] = q
    if not np.all(np.isfinite(qcov)): qcov = np.full((len(free), len(free)), np.nan)
    err = np.zeros(len(pnames)); err[free] = np.sqrt(np.abs(np.diag(qcov)))
    r = FitResult(model=name, params=dict(zip(pnames, popt)), errors=dict(zip(pnames, err)), fixed=fixed,
                  func=lambda t, p=popt: f(np.asarray(t, float), *p))
    r.update(_gof(y, f(x, *popt), len(free)))
    r["conf_band"], r["pred_band"] = _bands(f, x, popt, free, qcov, r["DOF"], r["Reduced_ChiSq"])
    if yerr is not None: r["ChiSq_weighted"] = float(np.sum(((y - f(x, *popt)) / yerr) ** 2))
    return r


# ---------------------------------------------------------------- regression
def multiple_regression(y, X, names):
    """OLS with intercept. X: 2-D array (n x k). Returns coefficient table, ANOVA, diagnostics, residuals."""
    y = np.asarray(y, float); X = np.asarray(X, float)
    m = np.isfinite(y) & np.all(np.isfinite(X), axis=1); y, X = y[m], X[m]
    n, k = X.shape; D = np.column_stack([np.ones(n), X])
    beta, *_ = np.linalg.lstsq(D, y, rcond=None)
    fit = D @ beta; res = y - fit; dfe = n - k - 1
    sse = float(res @ res); sst = float(((y - y.mean()) ** 2).sum()); ssr = sst - sse
    rank = np.linalg.matrix_rank(D)
    mse = sse / dfe; cov = mse * np.linalg.pinv(D.T @ D); se = np.sqrt(np.abs(np.diag(cov)))
    if rank < D.shape[1]: se = np.where(se < 1e-12 * (np.abs(beta) + 1), np.nan, se)
    t = beta / se; p = 2 * stats.t.sf(np.abs(t), dfe); tc = stats.t.ppf(0.975, dfe)
    vif = []
    for j in range(k):  # variance inflation factor: regress each predictor on the others
        others = np.column_stack([np.ones(n), np.delete(X, j, axis=1)])
        b, *_ = np.linalg.lstsq(others, X[:, j], rcond=None); rj = X[:, j] - others @ b
        r2j = 1 - (rj @ rj) / (((X[:, j] - X[:, j].mean()) ** 2).sum()); vif.append(1 / (1 - r2j) if r2j < 1 else np.inf)
    F = (ssr / k) / mse
    coef = [[nm, b, s, tt, pp, b - tc * s, b + tc * s, v] for nm, b, s, tt, pp, v in
            zip(["Intercept"] + list(names), beta, se, t, p, [np.nan] + vif)]
    return {"coef": coef, "anova": [["Model", ssr, k, ssr / k, F, stats.f.sf(F, k, dfe)], ["Error", sse, dfe, mse, "", ""],
                                    ["Total", sst, n - 1, "", "", ""]],
            "stats": {"N": n, "R2": ssr / sst, "Adj_R2": 1 - (sse / dfe) / (sst / (n - 1)), "RMSE": np.sqrt(mse),
                      "Durbin-Watson": float(np.sum(np.diff(res) ** 2) / sse) if sse > 0 else np.nan,
                      "Residual Shapiro p": stats.shapiro(res).pvalue if n >= 3 and np.ptp(res) > 0 else np.nan,
                      "Warning": "" if rank == D.shape[1] else "Predictors are collinear: coefficients are not unique (see VIF)"},
            "fitted": fit, "residuals": res, "mask": m}


# ---------------------------------------------------------------- more tests
def tukey(groups):
    """groups: {name: array}. Tukey HSD pairwise comparisons."""
    names = list(groups); data = [_fin(groups[n]) for n in names]
    res = stats.tukey_hsd(*data); ci = res.confidence_interval(0.95); rows = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            rows.append([f"{names[i]} - {names[j]}", data[i].mean() - data[j].mean(), ci.low[i, j], ci.high[i, j], res.pvalue[i, j],
                         "yes" if res.pvalue[i, j] < 0.05 else "no"])
    return rows


def bonferroni(groups):
    names = list(groups); pairs = [(i, j) for i in range(len(names)) for j in range(i + 1, len(names))]; rows = []
    for i, j in pairs:
        a, b = _fin(groups[names[i]]), _fin(groups[names[j]]); t = stats.ttest_ind(a, b)
        padj = min(1.0, t.pvalue * len(pairs))
        rows.append([f"{names[i]} - {names[j]}", a.mean() - b.mean(), t.statistic, t.pvalue, padj, "yes" if padj < 0.05 else "no"])
    return rows


def homogeneity(groups):
    d = [_fin(v) for v in groups.values()]
    lv = stats.levene(*d); bt = stats.bartlett(*d)
    return {"Levene W": lv.statistic, "Levene p": lv.pvalue, "Bartlett T": bt.statistic, "Bartlett p": bt.pvalue}


def kruskal(groups):
    k = stats.kruskal(*[_fin(v) for v in groups.values()]); return {"H": k.statistic, "p": k.pvalue}


def rm_anova(M):
    """One-way repeated-measures ANOVA. M: subjects (rows) x conditions (columns), complete rows only."""
    M = np.asarray(M, float); M = M[np.all(np.isfinite(M), axis=1)]; n, k = M.shape; g = M.mean()
    ss_cond = n * ((M.mean(0) - g) ** 2).sum(); ss_subj = k * ((M.mean(1) - g) ** 2).sum()
    ss_err = ((M - g) ** 2).sum() - ss_cond - ss_subj; df1, df2 = k - 1, (k - 1) * (n - 1)
    F = (ss_cond / df1) / (ss_err / df2)
    fr = stats.friedmanchisquare(*M.T) if k >= 3 else None
    return {"Subjects": n, "SS conditions": ss_cond, "SS subjects": ss_subj, "SS error": ss_err, "df conditions": df1,
            "df error": df2, "F": F, "p": stats.f.sf(F, df1, df2),
            "Friedman chi2": fr.statistic if fr else np.nan, "Friedman p": fr.pvalue if fr else np.nan}


def wilcoxon(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float); m = np.isfinite(a) & np.isfinite(b)
    w = stats.wilcoxon(a[m], b[m]); return {"W": w.statistic, "p": w.pvalue, "pairs": int(m.sum())}


def chi_square(cat_a, cat_b):
    import pandas as pd
    tab = pd.crosstab(pd.Series(cat_a, name="A"), pd.Series(cat_b, name="B"))
    chi2, p, dof, exp = stats.chi2_contingency(tab)
    return tab, {"Chi-square": chi2, "df": dof, "p": p, "Cramer's V": np.sqrt(chi2 / (tab.values.sum() * (min(tab.shape) - 1)))}


def grubbs(a, alpha=0.05):
    """Two-sided Grubbs test, applied repeatedly. Returns list of outliers removed, in order."""
    a = list(_fin(a)); out = []
    while len(a) > 2:
        v = np.array(a); n = len(v); z = np.abs(v - v.mean()) / v.std(ddof=1); i = int(np.argmax(z))
        t = stats.t.ppf(1 - alpha / (2 * n), n - 2); G = (n - 1) / np.sqrt(n) * np.sqrt(t ** 2 / (n - 2 + t ** 2))
        if z[i] <= G: break
        out.append({"Value": v[i], "G": z[i], "G critical": G}); a.pop(i)
    return out


def distribution_fit(a):
    """MLE fits of common distributions, ranked by AIC, with KS goodness of fit."""
    a = _fin(a); rows = []
    for nm, dist in (("Normal", stats.norm), ("Lognormal", stats.lognorm), ("Weibull", stats.weibull_min),
                     ("Gamma", stats.gamma), ("Exponential", stats.expon)):
        if nm != "Normal" and np.any(a <= 0): continue
        try:
            par = dist.fit(a, floc=0) if nm != "Normal" else dist.fit(a)
            ll = np.sum(dist.logpdf(a, *par)); kfree = len(par) - (0 if nm == "Normal" else 1)
            ks = stats.kstest(a, dist.cdf, args=par)
            rows.append([nm, ", ".join(f"{p:.5g}" for p in par), ll, 2 * kfree - 2 * ll, ks.statistic, ks.pvalue])
        except Exception:
            continue
    return sorted(rows, key=lambda r: r[3])


# ---------------------------------------------------------------- statistics
def descriptive(a):
    a = np.asarray(a, float); a = a[np.isfinite(a)]
    if a.size == 0:
        return {"N": 0}
    q1, med, q3 = np.percentile(a, [25, 50, 75])
    sd = float(np.std(a, ddof=1)) if a.size > 1 else float("nan")
    return {"N": a.size, "Mean": a.mean(), "SD": sd, "SE": sd / np.sqrt(a.size), "Min": a.min(), "Q1": q1,
            "Median": med, "Q3": q3, "Max": a.max(), "Range": np.ptp(a), "Sum": a.sum(),
            "Variance": sd ** 2, "Skewness": stats.skew(a), "Kurtosis": stats.kurtosis(a),
            "CV%": 100 * sd / a.mean() if a.mean() else float("nan")}


def _fin(a):
    a = np.asarray(a, float); return a[np.isfinite(a)]


def ttest_one(a, mu=0.0):
    t = stats.ttest_1samp(_fin(a), mu); return {"t": t.statistic, "p": t.pvalue, "mu0": mu}


def ttest_two(a, b, equal_var=True):
    t = stats.ttest_ind(_fin(a), _fin(b), equal_var=equal_var)
    return {"t": t.statistic, "p": t.pvalue, "equal_var": equal_var}


def ttest_paired(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float); m = np.isfinite(a) & np.isfinite(b)
    t = stats.ttest_rel(a[m], b[m]); return {"t": t.statistic, "p": t.pvalue, "pairs": int(m.sum())}


def anova_oneway(*groups):
    g = [_fin(x) for x in groups]
    f = stats.f_oneway(*g)
    k = len(g); n = sum(len(x) for x in g)
    return {"F": f.statistic, "p": f.pvalue, "df_between": k - 1, "df_within": n - k}


def anova_twoway(y, fa, fb):
    """Two-way ANOVA with interaction, balanced or unbalanced (sequential type I SS)."""
    y = np.asarray(y, float); fa = np.asarray(fa).astype(str); fb = np.asarray(fb).astype(str)
    m = np.isfinite(y); y, fa, fb = y[m], fa[m], fb[m]

    def design(*facs):
        cols = [np.ones(len(y))]
        for fac in facs:
            if isinstance(fac, tuple):  # interaction of two dummy blocks
                cols += [a * b for a in fac[0] for b in fac[1]]
            else:
                cols += fac
        return np.column_stack(cols)

    def dummies(f):
        lv = sorted(set(f)); return [(f == l).astype(float) for l in lv[1:]]

    da, db = dummies(fa), dummies(fb)
    def sse(X): beta = np.linalg.lstsq(X, y, rcond=None)[0]; return float(np.sum((y - X @ beta) ** 2))
    s0 = float(np.sum((y - y.mean()) ** 2)); s1 = sse(design(da)); s2 = sse(design(da, db)); s3 = sse(design(da, db, (da, db)))
    dfe = len(y) - (1 + len(da) + len(db) + len(da) * len(db))
    mse = s3 / dfe if dfe > 0 else float("nan")
    out = {}
    for name, ss, df in (("A", s0 - s1, len(da)), ("B", s1 - s2, len(db)), ("A*B", s2 - s3, len(da) * len(db))):
        F = (ss / df) / mse if df else float("nan")
        out[name] = {"SS": ss, "df": df, "F": F, "p": float(stats.f.sf(F, df, dfe)) if df else float("nan")}
    out["Error"] = {"SS": s3, "df": dfe}
    return out


def correlation(cols):
    """cols: {name: array}. Returns Pearson r and Spearman rho matrices (pairwise complete)."""
    names = list(cols); n = len(names)
    pr = np.eye(n); sr = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = _clean(cols[names[i]], cols[names[j]])
            pr[i, j] = pr[j, i] = stats.pearsonr(a, b)[0]
            sr[i, j] = sr[j, i] = stats.spearmanr(a, b)[0]
    return names, pr, sr


def normality(a):
    a = _fin(a)
    sw = stats.shapiro(a)
    ks = stats.kstest((a - a.mean()) / a.std(ddof=1), "norm")
    return {"Shapiro-Wilk W": sw.statistic, "Shapiro p": sw.pvalue, "KS D": ks.statistic, "KS p": ks.pvalue}


def nonparam(a, b):
    a, b = _fin(a), _fin(b)
    mw = stats.mannwhitneyu(a, b); ks = stats.ks_2samp(a, b)
    return {"Mann-Whitney U": mw.statistic, "MW p": mw.pvalue, "KS D": ks.statistic, "KS p": ks.pvalue}


def pca(X):
    """X: rows=observations, cols=variables. Standardized PCA. Returns eigenvalues, loadings, scores."""
    X = np.asarray(X, float); X = X[np.all(np.isfinite(X), axis=1)]
    Z = (X - X.mean(0)) / X.std(0, ddof=1)
    u, s, vt = np.linalg.svd(Z, full_matrices=False)
    ev = s ** 2 / (len(Z) - 1)
    return ev, ev / ev.sum() * 100, vt.T, Z @ vt.T


# ---------------------------------------------------------------- signal / math
def smooth(y, method="Savitzky-Golay", window=7, order=2):
    y = np.asarray(y, float); window = max(3, int(window) | 1)
    if method == "Savitzky-Golay":
        return signal.savgol_filter(y, window, min(order, window - 1))
    if method == "Adjacent average":
        return np.convolve(y, np.ones(window) / window, mode="same")
    if method == "Median":
        return signal.medfilt(y, window)
    raise ValueError(method)


def fft(x, y):
    """One-sided amplitude spectrum. Returns frequency, amplitude, phase."""
    y = np.asarray(y, float); x = np.asarray(x, float)
    dt = float(np.mean(np.diff(x))) if len(x) > 1 else 1.0
    Y = np.fft.rfft(y - np.mean(y))
    return np.fft.rfftfreq(len(y), dt), 2 * np.abs(Y) / len(y), np.angle(Y)


def fft_lowpass(x, y, cutoff):
    y = np.asarray(y, float); dt = float(np.mean(np.diff(x)))
    Y = np.fft.rfft(y); Y[np.fft.rfftfreq(len(y), dt) > cutoff] = 0
    return np.fft.irfft(Y, len(y))


def derivative(x, y): return np.gradient(np.asarray(y, float), np.asarray(x, float))
def integrate_cum(x, y): return integrate.cumulative_trapezoid(y, x, initial=0)
def area(x, y): x, y = _clean(x, y); return float(np.trapz(y, x))


def interpolate_xy(x, y, n=200, kind="cubic"):
    x, y = _clean(x, y); o = np.argsort(x); x, y = x[o], y[o]
    xi = np.linspace(x.min(), x.max(), int(n))
    return xi, interpolate.interp1d(x, y, kind=kind)(xi)


def normalize(y, method="0-1"):
    y = np.asarray(y, float)
    if method == "0-1": return (y - np.nanmin(y)) / np.ptp(y[np.isfinite(y)])
    if method == "Z-score": return (y - np.nanmean(y)) / np.nanstd(y, ddof=1)
    if method == "Divide by max": return y / np.nanmax(y)
    raise ValueError(method)


def baseline_shirley(x, y, n_iter=100, tol=1e-7):
    """Iterative Shirley (1972) background (XPS): the background moves from the level at one end to the level at the other in
    proportion to the peak area (above the background) lying beyond each point. The ends are the lowest and highest x."""
    o = np.argsort(x); xs, ys = np.asarray(x, float)[o], np.asarray(y, float)[o]; lo, hi = ys[0], ys[-1]; B = np.full_like(ys, hi)
    for _ in range(n_iter):
        s = ys - B; cum = np.r_[0.0, np.cumsum((s[1:] + s[:-1]) / 2 * np.diff(xs))]
        if cum[-1] == 0: break
        Bn = hi + (lo - hi) * (cum[-1] - cum) / cum[-1]; done = np.max(np.abs(Bn - B)) < tol * (np.ptp(ys) or 1.0); B = Bn
        if done: break
    out = np.empty_like(B); out[o] = B; return out


def savgol_derivative(x, y, deriv=1, window=11, order=3):
    """d^k y/dx^k (k = 1-4) from Savitzky-Golay smoothing; unevenly spaced data go through an even grid of the same length."""
    from scipy.signal import savgol_filter
    x, y = np.asarray(x, float), np.asarray(y, float); o = np.argsort(x); xs, ys = x[o], y[o]; n = len(xs)
    window = int(window) | 1; window = min(window, n if n % 2 else n - 1); order = min(int(order), window - 1)
    if int(deriv) > order: raise ValueError("The polynomial order must be at least the derivative order.")
    g = np.linspace(xs[0], xs[-1], n); even = np.allclose(np.diff(xs), g[1] - g[0], rtol=1e-3)
    d = savgol_filter(ys if even else np.interp(g, xs, ys), window, order, deriv=int(deriv), delta=g[1] - g[0])
    out = np.empty(n); out[o] = d if even else np.interp(xs, g, d); return out


def baseline_als(y, lam=1e5, p=0.01, n_iter=10):
    """Asymmetric least squares baseline (Eilers & Boelens 2005)."""
    from scipy import sparse
    from scipy.sparse.linalg import spsolve
    y = np.asarray(y, float); L = len(y)
    D = sparse.diags([1, -2, 1], [0, -1, -2], shape=(L, L - 2))
    D = lam * D.dot(D.T); w = np.ones(L)
    for _ in range(n_iter):
        W = sparse.spdiags(w, 0, L, L)
        z = spsolve((W + D).tocsc(), w * y)
        w = p * (y > z) + (1 - p) * (y < z)
    return z


def find_peaks(x, y, prominence=None, min_distance=1):
    x, y = np.asarray(x, float), np.asarray(y, float)
    prominence = prominence if prominence else 0.05 * float(np.ptp(y[np.isfinite(y)]))
    idx, prop = signal.find_peaks(y, prominence=prominence, distance=max(1, int(min_distance)))
    w = signal.peak_widths(y, idx, rel_height=0.5)[0] * (float(np.mean(np.diff(x))) if len(x) > 1 else 1)
    return [{"Index": int(i), "X": x[i], "Y": y[i], "Prominence": p, "FWHM": fw}
            for i, p, fw in zip(idx, prop["prominences"], w)]


def fit_multipeak(x, y, centers, shape="Gaussian"):
    """Fit sum of peaks + constant baseline, starting at given centers."""
    x, y = _clean(x, y)
    base = MODELS[shape][0]
    w0 = float(np.ptp(x)) / (10 * max(1, len(centers)))
    p0 = [float(np.min(y))]
    for c in centers:
        p0 += [c, w0, float(np.interp(c, x, y) - np.min(y)) * w0]

    def f(t, y0, *p):
        return y0 + sum(base(t, 0, p[k], p[k + 1], p[k + 2]) for k in range(0, len(p), 3))
    popt, pcov = optimize.curve_fit(f, x, y, p0=p0, maxfev=40000)
    err = np.sqrt(np.abs(np.diag(pcov)))
    names = ["y0"] + [f"{n}{j + 1}" for j in range(len(centers)) for n in ("xc", "w", "A")]
    r = FitResult(model=f"{len(centers)} x {shape}", params=dict(zip(names, popt)), errors=dict(zip(names, err)),
                  func=lambda t, p=popt: f(np.asarray(t, float), *p),
                  components=[(lambda t, q=popt[k:k + 3], y0=popt[0]: y0 + base(np.asarray(t, float), 0, *q))
                              for k in range(1, len(popt), 3)])
    r.update(_gof(y, f(x, *popt), len(popt)))
    return r
