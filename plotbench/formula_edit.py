"""Excel-style help while a cell formula is typed: the function list that pops up under the cell, the argument hint (calltip), F4
($ cycling), and picking cells and ranges with the mouse (point mode), with each referenced range outlined on the grid.

The text logic is in plain functions (tested without a window); FormulaAssist attaches it to the cell editor of a sheet.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import re

from . import cellformula as CF

_ = None
# Syntax and a one-line description of every function (aliases point to the same entry).
SIGS = {
    "ABS": ("number", "Absolute value"), "ACOS": ("number", "Arc cosine (radians)"), "AND": ("logical1, logical2, ...", "TRUE if all are true"),
    "ASIN": ("number", "Arc sine (radians)"), "ATAN": ("number", "Arc tangent (radians)"), "ATAN2": ("x, y", "Arc tangent of y/x (radians), as in Excel"),
    "AVERAGE": ("range, ...", "Mean of the numbers"), "AVERAGEIF": ("range, criteria, [average_range]", "Mean of the cells that meet a condition"),
    "AVERAGEIFS": ("average_range, range1, criteria1, ...", "Mean of the cells that meet several conditions"),
    "CONCAT": ("text1, text2, ...", "Joins texts"), "COS": ("number", "Cosine (radians)"), "COSH": ("number", "Hyperbolic cosine"),
    "COUNT": ("range, ...", "Number of numbers"), "COUNTA": ("range, ...", "Number of non-empty cells"), "COUNTBLANK": ("range", "Number of empty cells"),
    "COUNTIF": ("range, criteria", "Cells that meet a condition"), "COUNTIFS": ("range1, criteria1, ...", "Cells that meet several conditions"),
    "DEGREES": ("radians", "Radians to degrees"), "EXP": ("number", "e to a power"), "FACT": ("number", "Factorial"),
    "GEOMEAN": ("range, ...", "Geometric mean"), "HARMEAN": ("range, ...", "Harmonic mean"),
    "HLOOKUP": ("value, table, row, [approximate]", "Looks a value up in the first row of a table"),
    "IF": ("condition, value_if_true, [value_if_false]", "One of two values by a condition"), "IFERROR": ("value, value_if_error", "A fallback when a formula gives an error"),
    "INDEX": ("range, row, [column]", "The value at a position in a range"), "INT": ("number", "Rounds down to an integer"),
    "IQR": ("range, ...", "Interquartile range"), "ISBLANK": ("value", "TRUE if empty"), "ISNUMBER": ("value", "TRUE if a number"), "ISTEXT": ("value", "TRUE if text"),
    "LARGE": ("range, k", "k-th largest value"), "LEFT": ("text, [n]", "First n characters"), "LEN": ("text", "Number of characters"),
    "LN": ("number", "Natural logarithm"), "LOG": ("number, [base]", "Logarithm (base 10 by default)"), "LOG10": ("number", "Base-10 logarithm"),
    "LOWER": ("text", "Lower case"), "MATCH": ("value, range, [match_type]", "Position of a value in a range"), "MAX": ("range, ...", "Largest number"),
    "MAXIFS": ("max_range, range1, criteria1, ...", "Largest value that meets conditions"), "MEDIAN": ("range, ...", "Median"), "MIN": ("range, ...", "Smallest number"),
    "MINIFS": ("min_range, range1, criteria1, ...", "Smallest value that meets conditions"), "MOD": ("number, divisor", "Remainder"),
    "MODE": ("range, ...", "Most frequent value"), "NOT": ("logical", "Reverses TRUE and FALSE"), "OR": ("logical1, logical2, ...", "TRUE if any is true"),
    "PERCENTILE": ("range, k", "k-th percentile (k from 0 to 1)"), "PI": ("", "3.14159..."), "POWER": ("number, power", "A number raised to a power"),
    "PRODUCT": ("range, ...", "Product of the numbers"), "QUARTILE": ("range, quart", "Quartile 0 to 4"), "RADIANS": ("degrees", "Degrees to radians"),
    "RIGHT": ("text, [n]", "Last n characters"), "ROUND": ("number, [digits]", "Rounds to digits"), "ROUNDDOWN": ("number, [digits]", "Rounds towards zero"),
    "ROUNDUP": ("number, [digits]", "Rounds away from zero"), "SIGN": ("number", "-1, 0 or 1"), "SIN": ("number", "Sine (radians)"), "SINH": ("number", "Hyperbolic sine"),
    "SMALL": ("range, k", "k-th smallest value"), "SQRT": ("number", "Square root"), "STDEV": ("range, ...", "Sample standard deviation"),
    "STDEVP": ("range, ...", "Population standard deviation"), "SUM": ("range, ...", "Adds the numbers"), "SUMIF": ("range, criteria, [sum_range]", "Sum of the cells that meet a condition"),
    "SUMIFS": ("sum_range, range1, criteria1, ...", "Sum of the cells that meet several conditions"), "SUMPRODUCT": ("range1, range2, ...", "Sum of the products"),
    "SUMSQ": ("range, ...", "Sum of squares"), "TAN": ("number", "Tangent (radians)"), "TANH": ("number", "Hyperbolic tangent"), "TEXT": ("value, format", "A number as text"),
    "TRIM": ("text", "Removes extra spaces"), "TRUNC": ("number, [digits]", "Cuts off the decimals"), "UPPER": ("text", "Upper case"), "VALUE": ("text", "Text to number"),
    "VAR": ("range, ...", "Sample variance"), "VARP": ("range, ...", "Population variance"),
    "VLOOKUP": ("value, table, column, [approximate]", "Looks a value up in the first column of a table"),
    "XLOOKUP": ("value, lookup_range, return_range, [if_not_found]", "Looks a value up and returns the matching value"),
}
ALIAS = {"AVG": "AVERAGE", "MEAN": "AVERAGE", "STDEV.S": "STDEV", "STDEV.P": "STDEVP", "VAR.S": "VAR", "VAR.P": "VARP",
         "CONCATENATE": "CONCAT", "SUMSQUARES": "SUMSQ"}


def sig(name):
    """(arguments, description) of a function; aliases share their entry."""
    return SIGS.get(ALIAS.get(name, name), ("value, ...", ""))


DELIMS = set("=(,;:+-*/^&<> ")
REF = re.compile(r"(?:(?P<sheet>'(?:[^']|'')+'|[A-Za-z_][A-Za-z0-9_.]*)!)?(?P<a>\$?[A-Za-z]{1,3}\$?\d+)(?::(?P<b>\$?[A-Za-z]{1,3}\$?\d+))?(?![A-Za-z0-9_(])")


def _in_quotes(text, pos):
    """True inside "text" or a 'quoted sheet name' (both ignored when counting brackets and commas)."""
    dq = sq = False
    for ch in text[:pos]:
        if ch == '"' and not sq: dq = not dq
        elif ch == "'" and not dq: sq = not sq
    return dq or sq


def token_at(text, pos):
    """(identifier, start) typed just before the cursor in a formula, after = ( , : or an operator; None elsewhere."""
    if not text.startswith("=") or _in_quotes(text, pos): return None
    m = re.search(r"[A-Za-z_][A-Za-z0-9_.]*$", text[:pos])
    if not m or m.start() == 0 or text[m.start() - 1] not in DELIMS: return None
    if pos < len(text) and re.match(r"[A-Za-z0-9_.(]", text[pos]): return None  # inside a longer word or a name already followed by (
    return m.group(0), m.start()


def suggest(prefix):
    """(functions starting with the prefix, alphabetical) or, when none does, ([], functions containing it)."""
    p = prefix.upper(); names = sorted(CF.FUNCS)
    first = [n for n in names if n.startswith(p)]
    return (first, []) if first else ([], [n for n in names if p in n])


def accept(text, pos, name):
    """Replace the identifier before the cursor by NAME( ; returns (new text, cursor inside the bracket)."""
    t = token_at(text, pos)
    start = t[1] if t else pos
    new = text[:start] + name + "(" + text[pos:]
    return new, start + len(name) + 1


def call_context(text, pos):
    """(function name, index of the argument at the cursor) of the innermost open bracket before the cursor; None outside one."""
    if not text.startswith("="): return None
    depth, commas = 0, 0
    for i in range(pos - 1, 0, -1):
        ch = text[i]
        if _in_quotes(text, i) or ch in "'\"": continue
        if ch == ")": depth += 1
        elif ch == "(":
            if depth == 0:
                m = re.search(r"([A-Za-z_][A-Za-z0-9_.]*)$", text[:i])
                return (m.group(1).upper(), commas) if m and m.group(1).upper() in CF.FUNCS else None
            depth -= 1
        elif ch in ",;" and depth == 0: commas += 1
    return None


def calltip_html(name, index):
    """NAME(arg1, <b>arg2</b>, ...) with the argument at the cursor in bold, and the description."""
    args, desc = sig(name); parts = [a.strip() for a in args.split(",")] if args else []
    if parts and index >= len(parts) and parts[-1] in ("...",): index = len(parts) - 2 if len(parts) > 1 else 0
    shown = ", ".join(f"<b>{a}</b>" if k == min(index, len(parts) - 1) else a for k, a in enumerate(parts))
    return f"{name}({shown})" + (f"<br><span style='font-size:8pt'>{desc}</span>" if desc else "")


def ref_slot(text, pos):
    """True when the cursor waits for a value or reference: right after =, (, comma, ;, : or an operator."""
    if not text.startswith("=") or _in_quotes(text, pos): return False
    before = text[:pos].rstrip(" ")
    return bool(before) and before[-1] in "=(,;:+-*/^&<>"


def col_letter(i):
    s = ""; i += 1
    while i:
        i, r = divmod(i - 1, 26); s = chr(65 + r) + s
    return s


def col_number(letters):
    n = 0
    for ch in letters.upper(): n = n * 26 + ord(ch) - 64
    return n - 1


def ref_text(r1, c1, r2=None, c2=None, sheet=None):
    """A1 text of a cell or a range (data rows from 0), normalised top-left to bottom-right, with the sheet when given."""
    r2 = r1 if r2 is None else r2; c2 = c1 if c2 is None else c2
    a, b = (min(r1, r2), min(c1, c2)), (max(r1, r2), max(c1, c2))
    s = f"{col_letter(a[1])}{a[0] + 1}" + ("" if a == b else f":{col_letter(b[1])}{b[0] + 1}")
    return (CF.quote_sheet(sheet) + "!" if sheet else "") + s


def _cell(t):
    m = re.fullmatch(r"\$?([A-Za-z]{1,3})\$?(\d+)", t); return int(m.group(2)) - 1, col_number(m.group(1))


def refs_in(text):
    """[(sheet name or None, r1, c1, r2, c2, start, end)] of the references in a formula (data rows from 0), outside quoted text."""
    if not text.startswith("="): return []
    out = []
    for m in REF.finditer(text):
        if _in_quotes(text, m.start()) or (m.start() and re.match(r"[A-Za-z0-9_.]", text[m.start() - 1])): continue
        (r1, c1) = _cell(m.group("a")); (r2, c2) = _cell(m.group("b")) if m.group("b") else (r1, c1)
        sh = CF.sheet_name(m.group("sheet")) if m.group("sheet") else None
        out.append((sh, min(r1, r2), min(c1, c2), max(r1, r2), max(c1, c2), m.start(), m.end()))
    return out


_CYCLE = {(False, False): (True, True), (True, True): (False, True), (False, True): (True, False), (True, False): (False, False)}


def _cycle_cell(t, state=None):
    m = re.fullmatch(r"(\$?)([A-Za-z]{1,3})(\$?)(\d+)", t); col_abs, row_abs = _CYCLE[state or (bool(m.group(1)), bool(m.group(3)))]
    return ("$" if col_abs else "") + m.group(2) + ("$" if row_abs else "") + m.group(4)


def cycle_f4(text, pos):
    """F4: the reference at or just before the cursor goes A1 -> $A$1 -> A$1 -> $A1 -> A1 (both ends of a range alike).
    Returns (new text, new cursor) or None when the cursor is on no reference."""
    for sh, *_r, s, e in refs_in(text):
        if s <= pos <= e:
            m = REF.match(text, s); a = m.group("a"); ma = re.fullmatch(r"(\$?)[A-Za-z]{1,3}(\$?)\d+", a)
            state = (bool(ma.group(1)), bool(ma.group(2)))
            new = (text[s:m.start("a")] + _cycle_cell(a, state)
                   + (":" + _cycle_cell(m.group("b"), state) if m.group("b") else ""))
            out = text[:s] + new + text[e:]; return out, s + len(new)
    return None


def close_brackets(text):
    """Adds the missing closing brackets at the end of a formula (outside quoted text)."""
    if not text.startswith("="): return text
    depth = 0
    for i, ch in enumerate(text):
        if ch in "()" and not _in_quotes(text, i): depth += 1 if ch == "(" else -1
    return text + ")" * depth if depth > 0 and not _in_quotes(text, len(text)) else text


class Picker:
    """Point-mode state of one formula editor: the span of the reference inserted last (replaced by the next click, as in Excel,
    until something else is typed) and the anchor cell of a drag."""

    def __init__(self): self.span = None; self.anchor = None; self.sheet = None

    def can_pick(self, text, pos, ctrl=False):
        if not text.startswith("="): return False
        return ctrl or ref_slot(text, pos) or (self.span is not None and pos == self.span[1])

    def put(self, text, pos, ref, ctrl=False):
        """Insert ref at the cursor, or over the reference picked last while the cursor is still at its end (a new click, or the
        drag moving on). Ctrl adds a new reference after the last one, with a comma."""
        if self.span is not None and pos == self.span[1] and not ctrl: s, e = self.span
        else:
            s = e = pos
            if ctrl and not ref_slot(text, pos): text, s, e = text[:pos] + "," + text[pos:], pos + 1, pos + 1
        self.span = (s, s + len(ref)); return text[:s] + ref + text[e:], s + len(ref)


COLOURS = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf"]  # reference outlines, in the order of the formula


class FormulaAssist:
    """Attached to the line editor of a sheet cell: the function popup and calltip under the cell, F4, and point-mode picking
    (the sheet views call pick()). One per open editor; it removes itself when the editor closes."""

    def __init__(self, sheet, editor):
        from PySide6.QtWidgets import QListWidget, QLabel
        from PySide6.QtCore import Qt
        from .ui_style import palette
        self.closed = False; self.sh, self.ed, self.picker = sheet, editor, Picker(); c = palette(getattr(sheet.main, "_theme", "light"))
        flags = Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus
        self.popup = QListWidget(); self.popup.setWindowFlags(flags); self.popup.setFocusPolicy(Qt.NoFocus)
        self.popup.setAttribute(Qt.WA_ShowWithoutActivating); self.popup.setMinimumWidth(360)
        self.tip = QLabel(); self.tip.setWindowFlags(flags); self.tip.setAttribute(Qt.WA_ShowWithoutActivating)
        css = f"background:{c['panel']}; color:{c['text']}; border:1px solid {c['border']};"
        self.popup.setStyleSheet(f"QListWidget {{ {css} }} QListWidget::item:selected {{ background:{c.get('raised', c['panel'])}; }}")
        self.tip.setStyleSheet(f"QLabel {{ {css} padding:3px 6px; }}"); self.muted = c["muted"]
        self.popup.itemClicked.connect(self.complete); self.popup.itemDoubleClicked.connect(self.complete)
        editor.textEdited.connect(self._edited); editor.cursorPositionChanged.connect(lambda *_: self.update())
        editor._assist = self; sheet._fx_assist = self; sheet.book._formula_assist = self
        editor.destroyed.connect(lambda *_: self.close())

    def alive(self):
        if getattr(self, "closed", False): return False
        try: self.ed.text(); return True
        except RuntimeError: return False

    def close(self):
        self.closed = True
        for w in (self.popup, self.tip):
            try: w.hide(); w.deleteLater()
            except RuntimeError: pass
        if getattr(self.sh.book, "_formula_assist", None) is self: self.sh.book._formula_assist = None
        try:
            if getattr(self.sh, "_fx_assist", None) is self: self.sh._fx_assist = None
            for s in getattr(self.sh.book, "sheets", []): s.view.viewport().update()
        except RuntimeError: pass  # the workbook is closing

    def _edited(self, *_):
        self.picker.span = None; self.update()
        for s in getattr(self.sh.book, "sheets", []): s.view.viewport().update()

    def _below(self, w):
        """Under the cell, or above it when there is no room below; kept inside the screen on the right."""
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QGuiApplication
        p = self.ed.mapToGlobal(QPoint(0, self.ed.height() + 1)); scr = QGuiApplication.screenAt(p) or QGuiApplication.primaryScreen()
        a = scr.availableGeometry(); h, wd = w.height(), w.width()
        y = p.y() if p.y() + h <= a.bottom() else self.ed.mapToGlobal(QPoint(0, 0)).y() - h - 1
        x = min(max(p.x(), a.left()), a.right() - wd)
        return QPoint(x, max(a.top(), y))

    def update(self):
        """Show the popup (identifier typed after = or an operator) or the calltip (inside a function's brackets)."""
        from PySide6.QtWidgets import QListWidgetItem, QLabel
        from PySide6.QtCore import Qt
        if not self.alive(): return
        text, pos = self.ed.text(), self.ed.cursorPosition(); tok = token_at(text, pos) if self.ed.isVisible() else None
        first, rest = suggest(tok[0]) if tok else ([], [])
        if first or rest:
            self.popup.clear()
            if rest:
                head = QListWidgetItem("no function starts with this; names containing it:"); head.setFlags(Qt.NoItemFlags); self.popup.addItem(head)
            for n in first or rest:
                args, desc = sig(n); it = QListWidgetItem(); it.setData(Qt.UserRole, n); it.setToolTip(desc); self.popup.addItem(it)
                lab = QLabel(f"<b>{n}</b>({args}) &nbsp;<span style='color:{self.muted}'>{desc}</span>"); lab.setContentsMargins(6, 2, 6, 2)
                self.popup.setItemWidget(it, lab); hs = lab.sizeHint(); hs.setHeight(max(26, hs.height() + 8)); it.setSizeHint(hs)
            self.popup.setCurrentRow(1 if rest else 0)
            hints = [self.popup.item(i).sizeHint() for i in range(self.popup.count())]
            labs = [self.popup.itemWidget(self.popup.item(i)) for i in range(self.popup.count())]
            wide = max([l.sizeHint().width() for l in labs if l is not None] + [self.popup.fontMetrics().horizontalAdvance(self.popup.item(0).text())])
            high = sum(max(26, h.height()) for h in hints[:9]) + 6
            self.popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.popup.resize(min(680, max(360, self.ed.width(), wide + 30)), high)
            self.popup.move(self._below(self.popup)); self.popup.show(); self.tip.hide(); return
        self.popup.hide()
        ctx = call_context(text, pos) if self.ed.isVisible() else None
        if ctx: self.tip.setText(calltip_html(*ctx)); self.tip.adjustSize(); self.tip.move(self._below(self.tip)); self.tip.show()
        else: self.tip.hide()

    def complete(self, item=None):
        from PySide6.QtCore import Qt
        item = item or self.popup.currentItem()
        name = item.data(Qt.UserRole) if item is not None else None
        if not name: return False
        new, pos = accept(self.ed.text(), self.ed.cursorPosition(), name); self.picker.span = None  # typed text, not a picked reference
        self.ed.setText(new); self.ed.setCursorPosition(pos); self.popup.hide(); self.update(); return True

    def key(self, ev):
        """Keys for the popup and F4; True when used (the cell editor and the sheet do not see them)."""
        from PySide6.QtCore import Qt
        k = ev.key()
        if self.popup.isVisible():
            if k in (Qt.Key_Up, Qt.Key_Down):
                n = self.popup.count(); r = self.popup.currentRow() + (1 if k == Qt.Key_Down else -1)
                while 0 <= r < n and not (self.popup.item(r).flags() & Qt.ItemIsEnabled): r += 1 if k == Qt.Key_Down else -1
                if 0 <= r < n: self.popup.setCurrentRow(r)
                return True
            if k in (Qt.Key_Tab, Qt.Key_Return, Qt.Key_Enter): return self.complete()
            if k == Qt.Key_Escape: self.popup.hide(); return True
        if k == Qt.Key_F4 and self.ed.text().startswith("="):
            got = cycle_f4(self.ed.text(), self.ed.cursorPosition())
            if got: self.ed.setText(got[0]); self.ed.setCursorPosition(got[1]); self.picker.span = None; self._edited()
            return True
        return False

    def can_pick(self, ctrl=False): return self.alive() and self.picker.can_pick(self.ed.text(), self.ed.cursorPosition(), ctrl)

    def pick(self, sheet, r1, c1, r2, c2, ctrl=False):
        """Put the reference of a clicked cell or dragged range (data rows from 0) into the formula; another sheet adds its name."""
        ref = ref_text(r1, c1, r2, c2, sheet=None if sheet is self.sh else sheet.name)
        text, pos = self.picker.put(self.ed.text(), self.ed.cursorPosition(), ref, ctrl)
        self.ed.setText(text); self.ed.setCursorPosition(pos); self.popup.hide(); self.update()  # the argument hint stays up
        for s in getattr(self.sh.book, "sheets", []): s.view.viewport().update()

    def highlights(self, sheet):
        """[(r1, c1, r2, c2, colour, picked now)] of the references that point into this sheet."""
        if not self.alive(): return []
        out, k = [], 0
        for name, r1, c1, r2, c2, s, e in refs_in(self.ed.text()):
            here = (name is None and sheet is self.sh) or (name is not None and name.casefold() == sheet.name.casefold())
            if here: out.append((r1, c1, r2, c2, COLOURS[k % len(COLOURS)], self.picker.span == (s, e) or (self.picker.span and self.picker.span[1] == e)))
            k += 1
        return out


def _demo():
    assert suggest("a")[0][:5] == ["ABS", "ACOS", "AND", "ASIN", "ATAN"] and "AVERAGE" in suggest("av")[0]
    assert token_at("=AVERAGE(A1)+S", 14) == ("S", 13) and token_at("SUM", 3) is None and token_at('="ab', 4) is None
    assert accept("=a", 2, "AVERAGE") == ("=AVERAGE(", 9)
    assert call_context("=VLOOKUP(A2, ", 13) == ("VLOOKUP", 1) and "<b>table</b>" in calltip_html("VLOOKUP", 1)
    p = Picker(); t, c = p.put("=SUM(", 5, "B3"); assert (t, c) == ("=SUM(B3", 7)
    t, c = p.put(t, c, "C4"); assert t == "=SUM(C4"
    t, c = p.put(t, c, "D1:D5", ctrl=True); assert t == "=SUM(C4,D1:D5", t
    assert ref_text(9, 3, 1, 1) == "B2:D10" and ref_text(1, 1, sheet="Sheet 2") == "'Sheet 2'!B2"
    s = "=A1"; seq = []
    for _i in range(4): s, _c = cycle_f4(s, len(s)); seq.append(s)
    assert seq == ["=$A$1", "=A$1", "=$A1", "=A1"], seq
    assert cycle_f4("=SUM(A1:B5)", 9)[0] == "=SUM($A$1:$B$5)"
    assert [r[:5] for r in refs_in("=SUM(A1:B5)+'My s'!C3")] == [(None, 0, 0, 4, 1), ("My s", 2, 2, 2, 2)]
    assert close_brackets("=SUM(A1,MAX(B1") == "=SUM(A1,MAX(B1))" and close_brackets('="(" & A1') == '="(" & A1'
    assert close_brackets("=SUM('Data (raw)'!A1:A3") == "=SUM('Data (raw)'!A1:A3)"
    assert call_context("=IF('a, b'!A1, ", 15) == ("IF", 1)
    print("formula_edit ok")


if __name__ == "__main__":
    _demo()
