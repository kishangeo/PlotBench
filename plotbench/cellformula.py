"""Excel-style cell formulas: type =A1/B1, =SUM(B2:B10), =AVERAGE(C:C), =IF(A2>5, "high", "low") ... into any data cell.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
References are by column letter and row number as in Excel (A1 = first column, first data row; $ signs are allowed and
ignored). The formula is translated to a small expression and checked against a whitelist (no attributes, no imports, only
the functions below), so a formula stored in a project can never run other code.
"""
import ast
import math
import re
import statistics

import numpy as np

ERRORS = ("#DIV/0!", "#NAME?", "#REF!", "#VALUE!", "#CIRC!", "#NUM!", "#N/A")


class CellError(Exception):
    def __init__(self, code): super().__init__(code); self.code = code


def col_index(letters):
    n = 0
    for ch in letters.upper(): n = n * 26 + ord(ch) - 64
    return n - 1


def _nums(args):
    """Numbers in the arguments (ranges flattened); text and blanks are skipped, as in Excel."""
    out = []
    for a in args:
        for v in (a if isinstance(a, list) else [a]):
            if isinstance(v, bool): out.append(float(v))
            elif isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v)): out.append(float(v))
    return out


def _flat(args): return [v for a in args for v in (a if isinstance(a, list) else [a])]


def _need(xs, k=1):
    if len(xs) < k: raise CellError("#DIV/0!")
    return xs


def _crit(c):
    """Excel criteria such as '>5', '<=2', '<>0', 'Olivine' -> test function."""
    if isinstance(c, (int, float)): return lambda v: isinstance(v, (int, float)) and v == c
    m = re.match(r"\s*(<=|>=|<>|<|>|=)?\s*(.*)$", str(c)); op, val = m.group(1) or "=", m.group(2)
    try: val = float(val); num = True
    except ValueError: num = False
    ops = {"<": lambda a, b: a < b, ">": lambda a, b: a > b, "<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b,
           "=": lambda a, b: a == b, "<>": lambda a, b: a != b}

    def test(v):
        if num:
            return isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v)) and ops[op](float(v), val)
        return ops[op](str(v).lower(), str(val).lower()) if op in ("=", "<>") else False
    return test


def _round(x, n=0, how=round):
    f = 10 ** int(n); return how(float(x) * f) / f


def _if(cond, a=True, b=False): return a if cond else b


def _log(x, base=10.0):
    if x <= 0: raise CellError("#NUM!")
    return math.log(x, base)


def _sqrt(x):
    if x < 0: raise CellError("#NUM!")
    return math.sqrt(x)


def _percentile(r, p):
    xs = sorted(_nums([r]))
    if not xs or not 0 <= p <= 1: raise CellError("#NUM!")
    return float(np.percentile(xs, p * 100))


class _Range(list):
    """Cells of a range, column by column, with its shape (rows nr, columns nc) for INDEX and the LOOKUP functions."""
    def __init__(self, cells, nr, nc): super().__init__(cells); self.nr, self.nc = nr, nc


def _shape(r):
    if isinstance(r, _Range): return r.nr, r.nc
    return (len(r), 1) if isinstance(r, list) else (1, 1)


def _at(r, i, j):
    """Cell (row i, column j), 0-based, of a range."""
    nr, nc = _shape(r)
    if not (0 <= i < nr and 0 <= j < nc): raise CellError("#REF!")
    return r[j * nr + i] if isinstance(r, list) else r


def _vec(r):
    nr, nc = _shape(r)
    if nr > 1 and nc > 1: raise CellError("#VALUE!")  # needs one row or one column
    return list(r) if isinstance(r, list) else [r]


def _same(a, b):
    if isinstance(a, str) or isinstance(b, str): return str(a).strip().casefold() == str(b).strip().casefold()
    try: return float(a) == float(b)
    except (TypeError, ValueError): return False


def _match(v, vec, mode=1):
    """0-based position of v: mode 0 exact (text ignores case; * and ? are wildcards), 1 the largest value <= v, -1 the smallest
    value >= v (data sorted ascending or descending, as in Excel)."""
    mode = int(mode)
    if mode == 0:
        if isinstance(v, str) and any(ch in v for ch in "*?"):
            import fnmatch
            for i, x in enumerate(vec):
                if isinstance(x, str) and fnmatch.fnmatchcase(x.casefold(), v.casefold()): return i
        for i, x in enumerate(vec):
            if _same(v, x): return i
        raise CellError("#N/A")
    best = None
    for i, x in enumerate(vec):
        if isinstance(x, str) != isinstance(v, str) or x is None or (isinstance(x, float) and math.isnan(x)): continue
        a, b = (x.casefold(), v.casefold()) if isinstance(x, str) else (x, v)
        if (a <= b) if mode > 0 else (a >= b): best = i
        else: break  # sorted data: past the value
    if best is None: raise CellError("#N/A")
    return best


def _vlookup(v, table, col, approx=True):
    nr, nc = _shape(table); col = int(col)
    if not 1 <= col <= nc: raise CellError("#REF!")
    return _at(table, _match(v, [_at(table, i, 0) for i in range(nr)], 1 if approx else 0), col - 1)


def _hlookup(v, table, row, approx=True):
    nr, nc = _shape(table); row = int(row)
    if not 1 <= row <= nr: raise CellError("#REF!")
    return _at(table, row - 1, _match(v, [_at(table, 0, j) for j in range(nc)], 1 if approx else 0))


def _index(r, i, j=None):
    nr, nc = _shape(r)
    if j is None:
        if nr == 1 and nc > 1: return _at(r, 0, int(i) - 1)
        j = 1
    return _at(r, int(i) - 1, int(j) - 1)


def _xlookup(v, look, ret, missing=None):
    a, b = _vec(look), _vec(ret)
    if len(a) != len(b): raise CellError("#VALUE!")
    try: return b[_match(v, a, 0)]
    except CellError:
        if missing is None: raise
        return missing


def _ifs(pairs):
    """For each row, whether every (range, criterion) pair matches (SUMIFS, COUNTIFS ...)."""
    if not pairs or len(pairs) % 2: raise CellError("#VALUE!")
    rs = [_flat([pairs[k]]) for k in range(0, len(pairs), 2)]; cs = [_crit(pairs[k]) for k in range(1, len(pairs), 2)]
    if len({_shape(pairs[k]) for k in range(0, len(pairs), 2)}) != 1: raise CellError("#VALUE!")  # same rows x columns, not just the same count
    return [all(c(r[i]) for r, c in zip(rs, cs)) for i in range(len(rs[0]))]


def _pick(rng, pairs):
    vals, keep = _flat([rng]), _ifs(pairs)
    if len(vals) != len(keep) or (pairs and _shape(rng) != _shape(pairs[0])): raise CellError("#VALUE!")
    return [v for v, k in zip(vals, keep) if k]


FUNCS = {
    "SUM": lambda *a: sum(_nums(a)), "AVERAGE": lambda *a: statistics.fmean(_need(_nums(a))), "MIN": lambda *a: min(_need(_nums(a))),
    "MAX": lambda *a: max(_need(_nums(a))), "COUNT": lambda *a: float(len(_nums(a))),
    "COUNTA": lambda *a: float(sum(1 for v in _flat(a) if v not in ("", None) and not (isinstance(v, float) and math.isnan(v)))),
    "COUNTBLANK": lambda *a: float(sum(1 for v in _flat(a) if v in ("", None) or (isinstance(v, float) and math.isnan(v)))),
    "PRODUCT": lambda *a: math.prod(_nums(a)), "MEDIAN": lambda *a: statistics.median(_need(_nums(a))),
    "STDEV": lambda *a: statistics.stdev(_need(_nums(a), 2)), "STDEVP": lambda *a: statistics.pstdev(_need(_nums(a))),
    "VAR": lambda *a: statistics.variance(_need(_nums(a), 2)), "VARP": lambda *a: statistics.pvariance(_need(_nums(a))),
    "MODE": lambda *a: statistics.mode(_need(_nums(a))), "GEOMEAN": lambda *a: statistics.geometric_mean(_need(_nums(a))),
    "HARMEAN": lambda *a: statistics.harmonic_mean(_need(_nums(a))), "SUMSQ": lambda *a: sum(v * v for v in _nums(a)),
    "SUMPRODUCT": lambda *a: _sumproduct(*a),
    "LARGE": lambda r, k: sorted(_nums([r]), reverse=True)[int(k) - 1], "SMALL": lambda r, k: sorted(_nums([r]))[int(k) - 1],
    "PERCENTILE": _percentile, "QUARTILE": lambda r, q: _percentile(r, q / 4),
    "COUNTIF": lambda r, c: float(sum(1 for v in _flat([r]) if _crit(c)(v))),
    "SUMIF": lambda r, c, s=None: sum(_nums([[y for v, y in zip(_flat([r]), _flat([s if s is not None else r])) if _crit(c)(v)]])),
    "AVERAGEIF": lambda r, c, s=None: statistics.fmean(_need(_nums([[y for v, y in zip(_flat([r]), _flat([s if s is not None else r]))
                                                                        if _crit(c)(v)]]))),
    "ABS": abs, "SQRT": _sqrt, "EXP": math.exp, "LN": lambda x: _log(x, math.e), "LOG": _log, "LOG10": lambda x: _log(x, 10.0),
    "POWER": lambda x, y: float(x) ** float(y), "MOD": lambda x, y: float(x) - float(y) * math.floor(float(x) / float(y)),
    "INT": lambda x: float(math.floor(x)), "TRUNC": lambda x, n=0: _round(x, n, math.trunc), "ROUND": lambda x, n=0: _round(x, n),
    "ROUNDUP": lambda x, n=0: _round(x, n, lambda v: math.ceil(v) if v > 0 else math.floor(v)),
    "ROUNDDOWN": lambda x, n=0: _round(x, n, math.trunc), "SIGN": lambda x: float(np.sign(x)), "FACT": lambda x: float(math.factorial(int(x))),
    "PI": lambda: math.pi, "SIN": math.sin, "COS": math.cos, "TAN": math.tan, "ASIN": math.asin, "ACOS": math.acos, "ATAN": math.atan,
    "ATAN2": lambda x, y: math.atan2(y, x), "SINH": math.sinh, "COSH": math.cosh, "TANH": math.tanh,
    "DEGREES": math.degrees, "RADIANS": math.radians,
    "IF": _if, "AND": lambda *a: all(_flat(a)), "OR": lambda *a: any(_flat(a)), "NOT": lambda x: not x,
    "ISBLANK": lambda v: v in ("", None) or (isinstance(v, float) and math.isnan(v)),
    "ISNUMBER": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and not (isinstance(v, float) and math.isnan(v)),
    "ISTEXT": lambda v: isinstance(v, str), "CONCAT": lambda *a: "".join(_text(v) for v in _flat(a)),
    "LEN": lambda s: float(len(_text(s))), "UPPER": lambda s: _text(s).upper(), "LOWER": lambda s: _text(s).lower(),
    "TRIM": lambda s: " ".join(_text(s).split()), "LEFT": lambda s, n=1: _text(s)[:int(n)], "RIGHT": lambda s, n=1: _text(s)[-int(n):] if n else "",
    "VALUE": lambda s: float(s), "TEXT": lambda v, fmt="": _format(v, fmt), "IFERROR": lambda thunk, alt: _iferror(thunk, alt),
}
FUNCS.update({
    "VLOOKUP": _vlookup, "HLOOKUP": _hlookup, "XLOOKUP": _xlookup, "INDEX": _index, "MATCH": lambda v, r, mode=1: float(_match(v, _vec(r), mode) + 1),
    "SUMIFS": lambda s, *p: sum(_nums([_pick(s, p)])), "COUNTIFS": lambda *p: float(sum(_ifs(p))),
    "AVERAGEIFS": lambda s, *p: statistics.fmean(_need(_nums([_pick(s, p)]))), "MAXIFS": lambda s, *p: max(_need(_nums([_pick(s, p)]))),
    "MINIFS": lambda s, *p: min(_need(_nums([_pick(s, p)]))), "IQR": lambda r: _percentile(r, 0.75) - _percentile(r, 0.25),
})


def _sumproduct(*ranges):
    """Pairwise products summed; blank or text cells count as 0 (as in Excel), ranges must be the same size."""
    arrs = [np.array([v if isinstance(v, (int, float)) and not isinstance(v, bool) and not (isinstance(v, float) and math.isnan(v)) else 0.0
                      for v in (r if isinstance(r, list) else [r])], float) for r in ranges]
    if len({a.size for a in arrs}) != 1: raise CellError("#VALUE!")
    return float(np.sum(np.prod(np.vstack(arrs), axis=0)))


def _iferror(thunk, alt):
    try: v = thunk()
    except Exception: return alt  # CellError, division by zero, bad maths
    return alt if (isinstance(v, str) and v in ERRORS) or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))) else v


def _format(v, fmt):
    """TEXT(value, format) for the common Excel patterns: '0', '0.00', '0.0%', '0.00E+00', '#,##0.0'."""
    if not fmt or not isinstance(v, (int, float)): return _text(v)
    f = str(fmt); dec = len(f.split(".")[1].rstrip("%").split("E")[0].split("e")[0]) if "." in f else 0
    if f.endswith("%"): return f"{v * 100:.{dec}f}%"
    if "E" in f.upper(): return f"{v:.{dec}E}"
    return f"{v:,.{dec}f}" if "," in f else f"{v:.{dec}f}"
FUNCS.update({"AVG": FUNCS["AVERAGE"], "MEAN": FUNCS["AVERAGE"], "STDEV.S": FUNCS["STDEV"], "STDEV.P": FUNCS["STDEVP"],
              "VAR.S": FUNCS["VAR"], "VAR.P": FUNCS["VARP"], "CONCATENATE": FUNCS["CONCAT"], "SUMSQUARES": FUNCS["SUMSQ"]})


def _truth(v):
    if isinstance(v, str):
        if v.upper() in ("TRUE", "FALSE"): return v.upper() == "TRUE"
        raise CellError("#VALUE!")
    return bool(v)


def _text(v):
    if isinstance(v, float):
        if math.isnan(v): return ""
        return str(int(v)) if v.is_integer() else repr(v)
    return "" if v is None else str(v)


_TOKEN = re.compile(r'''\s*(?:
    (?P<str>"[^"]*")|
    (?P<sheet>'(?:[^']|'')+'|[A-Za-z_][A-Za-z0-9_.]*)!|
    (?P<range>\$?[A-Za-z]{1,3}\$?\d+\s*:\s*\$?[A-Za-z]{1,3}\$?\d+)|
    (?P<func>[A-Za-z][A-Za-z0-9_.]*)(?=\s*\()|
    (?P<colrange>\$?[A-Za-z]{1,3}\s*:\s*\$?[A-Za-z]{1,3})(?![A-Za-z0-9(])|
    (?P<ref>\$?[A-Za-z]{1,3}\$?\d+)(?![A-Za-z0-9(])|
    (?P<num>\d+\.?\d*(?:[eE][-+]?\d+)?%?|\.\d+(?:[eE][-+]?\d+)?%?)|
    (?P<name>[A-Za-z_][A-Za-z0-9_]*)|
    (?P<op><>|<=|>=|[-+*/^&=<>(),])
)''', re.X)


def sheet_name(tok):
    """'Sheet2' or "'My data'" (as written before the !) -> the sheet name."""
    return tok[1:-1].replace("''", "'") if tok.startswith("'") else tok


def quote_sheet(name):
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", name) else "'" + name.replace("'", "''") + "'"


def translate(text):
    """'=SUM(A1:A3)/B2' -> Python source using RNG/REF/CAT calls; raises CellError('#NAME?') for unknown names."""
    s = text.strip()
    if s.startswith("="): s = s[1:]
    if "#REF!" in s.upper(): raise CellError("#REF!")  # a reference to a deleted column
    out, pos, sheet = [], 0, None
    while pos < len(s):
        m = _TOKEN.match(s, pos)
        if not m or m.end() == pos:
            if s[pos:].strip() == "": break
            raise CellError("#VALUE!")
        pos = m.end(); k = m.lastgroup; t = m.group(k)
        if sheet is not None and k not in ("range", "colrange", "ref"): raise CellError("#REF!")  # Sheet2! must be followed by a cell
        sx = f", {sheet!r}" if sheet is not None else ""
        if k == "sheet": sheet = sheet_name(t); continue
        if k == "str": out.append(repr(t[1:-1]))
        elif k == "range":
            a, b = [re.match(r"\$?([A-Za-z]+)\$?(\d+)", p.strip()).groups() for p in t.split(":")]
            out.append(f"RNG({col_index(a[0])}, {int(a[1])}, {col_index(b[0])}, {int(b[1])}{sx})")
        elif k == "colrange":
            a, b = [p.strip().strip("$") for p in t.split(":")]
            out.append(f"RNG({col_index(a)}, 0, {col_index(b)}, 0{sx})")
        elif k == "ref":
            c, r = re.match(r"\$?([A-Za-z]+)\$?(\d+)", t).groups(); out.append(f"REF({col_index(c)}, {int(r)}{sx})")
        elif k == "func":
            name = t.upper()
            if name not in FUNCS: raise CellError("#NAME?")
            out.append("F_" + name.replace(".", "_"))
        elif k == "num": out.append(f"({float(t[:-1])}/100)" if t.endswith("%") else repr(float(t)))
        elif k == "name":
            u = t.upper()
            if u in ("TRUE", "FALSE"): out.append(u.title())
            else: raise CellError("#NAME?")
        else: out.append({"^": "**", "<>": "!=", "=": "==", "&": "@"}.get(t, t))
        sheet = None
    if sheet is not None: raise CellError("#REF!")
    return " ".join(out)


_OK = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Compare, ast.Call, ast.Name, ast.Constant, ast.Load, ast.operator, ast.unaryop, ast.cmpop)
# (IfExp and Lambda nodes are added by _Lazy after the check; a typed formula can never contain them)


class _Concat(ast.NodeTransformer):
    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.MatMult): return ast.Call(func=ast.Name(id="CAT", ctx=ast.Load()), args=[node.left, node.right], keywords=[])
        return node


class _Lazy(ast.NodeTransformer):
    """Applied after the whitelist check: IF(c, a, b) -> (a if c else b) so only the chosen branch is worked out (=IF(B1=0, 0, A1/B1)
    gives 0, not #DIV/0!), and IFERROR(v, alt) gets v as a deferred expression so its error can be caught."""

    def visit_Call(self, node):
        self.generic_visit(node)
        name = node.func.id if isinstance(node.func, ast.Name) else ""
        if name == "F_IF" and len(node.args) in (2, 3):
            other = node.args[2] if len(node.args) == 3 else ast.Constant(value=False)
            test = ast.Call(func=ast.Name(id="TRUTH", ctx=ast.Load()), args=[node.args[0]], keywords=[])
            return ast.copy_location(ast.IfExp(test=test, body=node.args[1], orelse=other), node)
        if name == "F_IFERROR" and len(node.args) == 2:
            thunk = ast.Lambda(args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]), body=node.args[0])
            node.args = [thunk, node.args[1]]
        return node


def compile_cell(text):
    src = translate(text)
    try: tree = ast.parse(src, mode="eval")
    except SyntaxError: raise CellError("#VALUE!") from None
    tree = ast.fix_missing_locations(_Concat().visit(tree))
    allowed = {"RNG", "REF", "CAT"} | {"F_" + k.replace(".", "_") for k in FUNCS}
    for node in ast.walk(tree):
        if not isinstance(node, _OK): raise CellError("#VALUE!")
        if isinstance(node, ast.Name) and node.id not in allowed | {"True", "False"}: raise CellError("#NAME?")
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.keywords): raise CellError("#VALUE!")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow) and isinstance(node.right, ast.Constant) and abs(node.right.value) > 1000:
            raise CellError("#NUM!")
    tree = ast.fix_missing_locations(_Lazy().visit(tree))  # only after the check: these nodes are made here, never typed
    return compile(tree, "<cell>", "eval")


def evaluate(text, get, n_rows, n_cols, sheets=None):
    """Value of one cell formula. get(col, row0) -> cell value (float, str or nan). sheets(name) -> (get, n_rows, n_cols) of another
    sheet of the workbook, or None if there is no such sheet. Returns a float, str or an error code."""
    def source(s):
        if s is None: return get, n_rows, n_cols
        src = sheets(s) if sheets else None
        if src is None: raise CellError("#REF!")  # no sheet of that name
        return src

    def cell(c, r, s=None):
        g, nr, nc = source(s)
        if not (0 <= c < nc) or not (1 <= r <= nr): raise CellError("#REF!")
        v = g(c, r - 1)
        if isinstance(v, str) and v in ERRORS: raise CellError(v)
        return v

    def ref(c, r, s=None):
        v = cell(c, r, s)
        return 0.0 if v is None or (isinstance(v, float) and math.isnan(v)) else v  # blank cells count as 0 in arithmetic

    def rng(c1, r1, c2, r2, s=None):
        if r1 == 0: r1, r2 = 1, source(s)[1]  # whole column A:A
        rows, cols = range(min(r1, r2), max(r1, r2) + 1), range(min(c1, c2), max(c1, c2) + 1)
        return _Range([cell(c, r, s) for c in cols for r in rows], len(rows), len(cols))
    ns = {"REF": ref, "RNG": rng, "CAT": lambda a, b: _text(a) + _text(b), "True": True, "False": False, "TRUTH": _truth}
    ns.update({"F_" + k.replace(".", "_"): f for k, f in FUNCS.items()})
    try:
        out = eval(compile_cell(text), {"__builtins__": {}, **ns})  # safe: only whitelisted names and calls (compile_cell)
        if isinstance(out, list): raise CellError("#VALUE!")  # a bare range
        if isinstance(out, bool): return "TRUE" if out else "FALSE"
        if isinstance(out, (int, float, np.floating)):
            out = float(out)
            if math.isinf(out) or math.isnan(out): return "#NUM!"
        return out
    except CellError as e: return e.code
    except ZeroDivisionError: return "#DIV/0!"
    except (statistics.StatisticsError, IndexError): return "#NUM!"
    except OverflowError: return "#NUM!"
    except Exception: return "#VALUE!"  # e.g. text in arithmetic, SQRT of text


def shift_refs(text, axis, at, delta, sheet=None, own=True):
    """References after inserting (delta=+1) or deleting (delta=-1) row or column 'at' (axis 0 = row, 1-based row number;
    axis 1 = column, 0-based index), as Excel does. Changes references without a sheet name when own is True (the formula's own
    sheet) and references written as sheet!A1 for the given sheet name. A reference to a deleted row or column becomes #REF!;
    a range that loses an end shrinks."""
    s = text.strip(); body = s[1:] if s.startswith("=") else s; out, pos, pend = [], 0, None

    def mine(p):
        return own if p is None else (sheet is not None and p.casefold() == sheet.casefold())

    def one(tok, end=None):
        m = re.match(r"(\$?)([A-Za-z]{1,3})(\$?)(\d*)$", tok.strip())
        c, r = col_index(m.group(2)), (int(m.group(4)) if m.group(4) else None)
        v = c if axis == 1 else r
        if v is None: return f"{m.group(1)}{_letter(c)}"  # A:A when rows change
        if delta < 0 and v == at:
            if end is None: return None
            v = at if not end else at - 1  # range end deleted: shrink
        elif v >= at: v += delta
        if axis == 1: c = v
        else: r = v
        if c < 0 or (r is not None and r < 1): return None
        return f"{m.group(1)}{_letter(c)}{m.group(3)}{'' if r is None else r}"
    while pos < len(body):
        m = _TOKEN.match(body, pos)
        if not m or m.end() == pos: out.append(body[pos:]); break
        k = m.lastgroup; lead = body[pos:m.start(k)]; t = m.group(k); pos = m.end()
        if k == "sheet": pend = sheet_name(t); out.append(lead + t + "!"); continue
        if k in ("ref", "range", "colrange") and mine(pend):
            if k == "ref":
                r = one(t); out.append(lead + ("#REF!" if r is None else r))
            else:
                a, b = t.split(":")
                ends = [one(a), one(b)]
                if delta < 0 and ends[0] is None and ends[1] is None and k != "colrange" or (k == "colrange" and axis == 1 and ends == [None, None]):
                    out.append(lead + "#REF!")
                else: out.append(lead + f"{one(a, end=False)}:{one(b, end=True)}")
        else: out.append(lead + t)
        pend = None
    return "=" + "".join(out)


def shift_columns(text, at, delta, sheet=None, own=True): return shift_refs(text, 1, at, delta, sheet, own)


def rename_sheet(text, old, new):
    """Sheet names in references follow a renamed sheet: =Old!A1 -> =New!A1."""
    s = text.strip(); body = s[1:] if s.startswith("=") else s; out, pos = [], 0
    while pos < len(body):
        m = _TOKEN.match(body, pos)
        if not m or m.end() == pos: out.append(body[pos:]); break
        k = m.lastgroup; lead = body[pos:m.start(k)]; t = m.group(k); pos = m.end()
        if k == "sheet" and sheet_name(t).casefold() == old.casefold(): out.append(lead + quote_sheet(new) + "!")
        elif k == "sheet": out.append(lead + t + "!")
        else: out.append(lead + t)
    return "=" + "".join(out)


def _letter(i):
    s = ""; i += 1
    while i: i, r = divmod(i - 1, 26); s = chr(65 + r) + s
    return s


def shift_formula(text, dr, dc):
    """Copy a formula dr rows down and dc columns right, as Excel's fill handle does: relative references move, parts marked
    with $ stay ($A1 keeps the column, A$1 the row, $A$1 both). A reference pushed off the sheet becomes #REF!."""
    s = text.strip(); body = s[1:] if s.startswith("=") else s; out, pos = [], 0

    def one(tok, col_only=False):
        m = re.match(r"(\$?)([A-Za-z]{1,3})(\$?)(\d*)$", tok.strip())
        c = col_index(m.group(2)) + (0 if m.group(1) else dc)
        if c < 0: return None
        if col_only or not m.group(4): return f"{m.group(1)}{_letter(c)}"
        r = int(m.group(4)) + (0 if m.group(3) else dr)
        return None if r < 1 else f"{m.group(1)}{_letter(c)}{m.group(3)}{r}"
    while pos < len(body):
        m = _TOKEN.match(body, pos)
        if not m or m.end() == pos: out.append(body[pos:]); break
        k = m.lastgroup; lead = body[pos:m.start(k)]; t = m.group(k); pos = m.end()
        if k == "sheet": out.append(lead + t + "!"); continue
        if k == "ref":
            r = one(t); out.append(lead + ("#REF!" if r is None else r))
        elif k in ("range", "colrange"):
            a, b = (one(p, k == "colrange") for p in t.split(":"))
            out.append(lead + ("#REF!" if a is None or b is None else f"{a}:{b}"))
        else: out.append(lead + t)
    return "=" + "".join(out)


def refs_in(text):
    """Columns (0-based) a formula reads, for the formula bar and for warnings."""
    try: src = translate(text)
    except CellError: return set()
    cols = set()
    for m in re.finditer(r"REF\((\d+), \d+\)", src): cols.add(int(m.group(1)))
    for m in re.finditer(r"RNG\((\d+), \d+, (\d+), \d+\)", src):
        a, b = sorted((int(m.group(1)), int(m.group(2)))); cols.update(range(a, b + 1))  # C1:A5 counts too
    return cols


def _demo():
    grid = [[1.0, 2.0, "Olivine"], [3.0, 0.0, "Pyroxene"], [5.0, float("nan"), "Olivine"]]  # rows x cols
    get = lambda c, r: grid[r][c]
    ev = lambda t: evaluate(t, get, 3, 3)
    assert ev("=A1+A2*2") == 7 and ev("=A1/B2") == "#DIV/0!" and ev("=SUM(A1:A3)") == 9 and ev("=AVERAGE(A1:B3)") == 2.2
    assert ev("=avg(A:A)") == 3 and ev("=MAX(A1:A3)-MIN(A1:A3)") == 4 and ev("=A3^2") == 25 and ev("=COUNT(B1:B3)") == 2
    assert ev('=IF(A2>2, "high", "low")') == "high" and ev("=ROUND(PI(), 2)") == 3.14 and ev("=SQRT(-1)") == "#NUM!"
    assert ev('=COUNTIF(C1:C3, "Olivine")') == 2 and ev('=SUMIF(C1:C3, "Olivine", A1:A3)') == 6 and ev("=Z9") == "#REF!"
    assert ev("=FOO(1)") == "#NAME?" and ev('=C1&" "&A1') == "Olivine 1" and ev("=A1<>A2") == "TRUE" and ev("=50%*A3") == 2.5
    assert ev("=B3+1") == 1 and ev("=$A$1*-2") == -2 and ev("=STDEV(A1:A3)") == 2 and ev("=MEDIAN(A1:A3)") == 3
    assert ev("=__import__") == "#NAME?" and ev("=A1.real") == "#VALUE!" and ev("=LOG(100)") == 2 and ev("=MOD(7,3)") == 1
    assert refs_in("=SUM(A1:B3)+C2") == {0, 1, 2} and refs_in("=SUM(C1:A2)") == {0, 1, 2}
    assert ev("=IF(B2=0, 0, A1/B2)") == 0 and ev("=IF(A1>0, LOG(A1), 0)") == 0 and ev("=IF(B2=0, 1/B2, 7)") == "#DIV/0!"
    assert ev("=IFERROR(A1/B2, -1)") == -1 and ev("=IFERROR(A2, -1)") == 3 and ev("=SUMPRODUCT(A1:A3, B1:B3)") == 2
    assert ev("=SUMPRODUCT(A1:A2, B1:B3)") == "#VALUE!" and ev('=TEXT(A1/3, "0.00")') == "0.33" and ev('=TEXT(0.256, "0.0%")') == "25.6%"
    assert ev('=IF("x", 1, 2)') == "#VALUE!" and ev("=IF(A1>2, 1)") == "FALSE"
    assert shift_columns("=A1+C2*$D$3", 1, 1) == "=A1+D2*$E$3" and shift_columns("=A1+C2", 2, -1) == "=A1+#REF!"
    assert shift_columns("=SUM(B1:D4)/A1", 0, -1) == "=SUM(A1:C4)/#REF!"
    assert shift_columns("=SUM(B1:D1)", 1, -1) == "=SUM(B1:C1)" and shift_columns("=SUM(B1:D1)", 3, -1) == "=SUM(B1:C1)" and shift_columns("=AVERAGE(C:C)", 1, 1) == "=AVERAGE(D:D)"
    assert shift_columns('=IF(B2>1,"B2",0)', 0, 1) == '=IF(C2>1,"B2",0)' and evaluate("=1+#REF!", get, 3, 3) == "#REF!"
    from .analysis import parse_number
    for t, v in (("10^-18", 1e-18), ("1e-18", 1e-18), ("2.5x10^3", 2500.0), ("10⁻¹⁸", 1e-18), ("-10^3", -1000.0), ("1,5", 1.5), ("50%", 0.5)):
        assert abs(parse_number(t) - v) <= abs(v) * 1e-12, t
    assert shift_formula("=A1*B$1+$C2+$D$3", 2, 1) == "=B3*C$1+$C4+$D$3"
    assert shift_formula("=SUM(A1:A3)/COUNT(B:B)", 1, 1) == "=SUM(B2:B4)/COUNT(C:C)" and shift_formula("=A1", -1, 0) == "=#REF!"
    assert shift_formula('=IF(A2>1,"A2",0)', 1, 0) == '=IF(A3>1,"A2",0)'
    other = [[100.0, "x"], [200.0, "y"]]
    books = {"data": (lambda c, r: other[r][c], 2, 2), "my data": (lambda c, r: other[r][c] * 2 if c == 0 else "z", 2, 2)}
    ev2 = lambda t: evaluate(t, get, 3, 3, lambda n: books.get(n.casefold()))
    assert ev2("=Data!A2/A1") == 200 and ev2("=SUM(Data!A1:A2)+A1") == 301 and ev2("='My data'!A1") == 200
    assert ev2("=AVERAGE(Data!A:A)") == 150 and ev2("=Nope!A1") == "#REF!" and ev2("=Data!") == "#REF!" and ev2("=Data!C1") == "#REF!"
    assert shift_formula("=Data!A1+B1", 1, 0) == "=Data!A2+B2" and rename_sheet("=Data!A1+'Data'!B2+data!C3", "data", "My data") == \
        "='My data'!A1+'My data'!B2+'My data'!C3"
    assert shift_refs("=Data!B1+B1", 1, 0, 1, sheet="Data", own=False) == "=Data!C1+B1"
    assert shift_refs("=Data!B1+B1", 1, 0, 1, sheet="Main", own=True) == "=Data!B1+C1"
    assert shift_refs("=A5+SUM(B2:B9)+A$5+A3", 0, 4, 1) == "=A6+SUM(B2:B10)+A$6+A3" and shift_refs("=A5+A2", 0, 5, -1) == "=#REF!+A2"
    assert shift_refs("=SUM(A2:A5)", 0, 5, -1) == "=SUM(A2:A4)" and shift_refs("=SUM(C:C)", 0, 1, 1) == "=SUM(C:C)"
    import ast as _ast
    assert not any(isinstance(n, (_ast.Lambda, _ast.IfExp)) for n in _ast.walk(_ast.parse(translate("=IF(A1>1, 2, 3)"), mode="eval")))
    assert ev("=VLOOKUP(3, A1:C3, 3, FALSE)") == "Pyroxene" and ev("=VLOOKUP(4, A1:B3, 2)") == 0 and ev("=VLOOKUP(9, A1:C3, 4, 0)") == "#REF!"
    assert ev("=VLOOKUP(7, A1:C3, 2, FALSE)") == "#N/A" and ev("=HLOOKUP(1, A1:C3, 2, FALSE)") == 3 and ev("=INDEX(A1:C3, 3, 1)") == 5
    assert ev("=INDEX(C1:C3, 2)") == "Pyroxene" and ev('=MATCH("pyroxene", C1:C3, 0)') == 2 and ev("=MATCH(4, A1:A3)") == 2
    assert ev('=MATCH("Oliv*", C1:C3, 0)') == 1 and ev('=XLOOKUP("Olivine", C1:C3, A1:A3)') == 1 and ev('=XLOOKUP("Garnet", C1:C3, A1:A3, -1)') == -1
    assert ev('=XLOOKUP("Garnet", C1:C3, A1:A3)') == "#N/A" and ev('=SUMIFS(A1:A3, C1:C3, "Olivine", A1:A3, ">2")') == 5
    assert ev('=COUNTIFS(C1:C3, "Olivine", B1:B3, ">1")') == 1 and ev('=AVERAGEIFS(A1:A3, C1:C3, "Olivine")') == 3
    assert ev('=MAXIFS(A1:A3, C1:C3, "Olivine")') == 5 and ev('=MINIFS(A1:A3, C1:C3, "Garnet")') == "#DIV/0!" and ev("=IQR(A1:A3)") == 2
    assert ev("=MATCH(1, A1:B3, 0)") == "#VALUE!" and ev('=IFERROR(VLOOKUP("x", A1:C3, 2, FALSE), "none")') == "none"
    assert ev('=SUMIFS(A1:A3, A1:B1, ">0")') == "#VALUE!" and ev('=COUNTIFS(A1, ">0")') == 1 and ev('=SUMIFS(A1:B1, A1:A2, ">0")') == "#VALUE!"
    print("CELLFORMULA OK")


if __name__ == "__main__":
    _demo()
