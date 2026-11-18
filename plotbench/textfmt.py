"""Per-text formatting of graphs: every text (title, axis titles, tick labels, legend entries, plot texts, annotations) can be
selected and formatted on its own from the text format bar, as in Origin. Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>

Rich text is typed with a small markup that the bar's buttons insert:
    _{2}      subscript            SiO_{2}
    ^{3+}     superscript          Fe^{3+}
    _{a}^{b}  stacked sub- and superscript
    \\b{...}   bold part of a text  \\i{...}  italic part
Greek letters are typed or inserted as Unicode (alpha button, or Ctrl+G on selected Latin letters). Text that already contains $
is passed to matplotlib's mathtext unchanged.
"""
import re

GREEK = dict(zip("abgdezhqiklmnxoprstufcywABGDEZHQIKLMNXOPRSTUFCYW",
                 "αβγδεζηθικλμνξοπρστυφχψω"
                 "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"))
_SPECIAL = {"\\": r"\backslash{}", "{": r"\{", "}": r"\}", "%": r"\%", "#": r"\#", "&": r"\&", "_": r"\_", "^": r"\^{}", "$": r"\$",
            "~": r"\~{}", " ": r"\ "}


def _math(s):
    """Plain characters as mathtext in the regular text font."""
    return "".join(_SPECIAL.get(c, c) for c in s)


def _group(s, i):
    """(content, index after the closing brace) of the {...} group opening at s[i]; braces may nest."""
    depth, j = 0, i
    while j < len(s):
        if s[j] == "{": depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0: return s[i + 1:j], j + 1
        j += 1
    return None, i


def rich(s):
    """Markup to the string matplotlib draws: SiO_{2} -> SiO$_{\\mathregular{2}}$, Fe^{3+} -> Fe$^{\\mathregular{3+}}$, \\b{x} -> bold."""
    s = str(s)
    if "$" in s or not re.search(r"[_^]\{|\\[bi]\{", s): return s
    out, i, plain = [], 0, []

    def flush():
        if plain: out.append("".join(plain)); plain.clear()
    while i < len(s):
        c = s[i]
        if c in "_^" and i + 1 < len(s) and s[i + 1] == "{":
            parts = {}
            while i < len(s) and s[i] in "_^" and i + 1 < len(s) and s[i + 1] == "{" and s[i] not in parts:
                body, j = _group(s, i + 1)
                if body is None: break
                parts[s[i]] = body; i = j
            if not parts: plain.append(c); i += 1; continue
            flush(); out.append("$" + "".join(f"{k}{{\\mathregular{{{_math(v)}}}}}" for k, v in sorted(parts.items(), key=lambda kv: kv[0] != "_")) + "$")
            continue
        if c == "\\" and i + 2 < len(s) and s[i + 1] in "bi" and s[i + 2] == "{":
            body, j = _group(s, i + 2)
            if body is not None:
                flush(); out.append("$\\math%s{%s}$" % ("bf" if s[i + 1] == "b" else "it", _math(body))); i = j; continue
        plain.append(c); i += 1
    flush(); return "".join(out)


def to_greek(s): return "".join(GREEK.get(c, c) for c in s)


# ---------------------------------------------------------------- the format bar (Qt)
from PySide6.QtWidgets import QToolBar, QLineEdit, QComboBox, QDoubleSpinBox, QLabel, QToolButton, QMenu, QColorDialog  # noqa: E402
from PySide6.QtGui import QFont, QColor  # noqa: E402
from PySide6.QtCore import Qt, QEvent  # noqa: E402

GREEK_MENU = "αβγδεθλμνπρστφχψωΔΣΦΩ°±×‰→"
_FONTS = []


def _fonts():
    if not _FONTS:
        from matplotlib import font_manager
        _FONTS.extend(sorted({f.name for f in font_manager.fontManager.ttflist}))
    return _FONTS


def _mods(e):
    m = e.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)
    return (int(m.value) if hasattr(m, "value") else int(m), int(e.key()))


class TextBar(QToolBar):
    """Origin-style text format bar of a graph window: words (with markup), font, size, bold, italic, superscript, subscript,
    stacked sub/superscript, Greek, larger/smaller, colour and orientation of the selected text. All state lives on this object
    (no closures over child widgets), so a closed graph leaves nothing behind that Qt could reuse."""

    def __init__(self, graph):
        super().__init__("Text format"); self.setObjectName("text_format_bar"); self.g = graph; self.key = None; self.busy = False
        self.addWidget(QLabel(" T "))
        self.field = QLineEdit(); self.field.setMinimumWidth(100); self.field.setMaximumWidth(260)
        self.field.setPlaceholderText("Click a text in the graph")
        self.field.setToolTip("Words of the selected text. SiO_{2}: subscript, Fe^{3+}: superscript, \b{..} bold, \i{..} italic. Enter applies.")
        self.field.installEventFilter(self); self.addWidget(self.field)
        self.family = QComboBox(); self.family.setEditable(True); self.family.setMaxVisibleItems(25); self.family.setMinimumWidth(100); self.family.setMaximumWidth(150); self.family.setToolTip("Font of the selected text")
        self.family.addItems(_fonts()); self.addWidget(self.family)
        self.size = QDoubleSpinBox(); self.size.setRange(3, 96); self.size.setDecimals(1); self.size.setButtonSymbols(QDoubleSpinBox.NoButtons); self.size.setToolTip("Size of the selected text (pt)"); self.size.setMinimumWidth(76); self.size.setMaximumWidth(84); self.addWidget(self.size)
        self.buttons = []
        self.b_bold = self._button("B", "Bold (Ctrl+B): the whole text, or the selected words", self.bold, True, bold=True)
        self.b_italic = self._button("I", "Italic (Ctrl+I): the whole text, or the selected words", self.italic, True, italic=True)
        self._button("x²", "Superscript (Ctrl+Shift+=): selected words, e.g. Fe^{3+}", self.sup)
        self._button("x₂", "Subscript (Ctrl+=): selected words, e.g. SiO_{2}", self.sub)
        self._button("x²₁", "Sub- and superscript stacked (Ctrl+-): selected words become the subscript", self.subsup)
        self.b_greek = self._button("αβ", "Greek (Ctrl+G): turns selected Latin letters into Greek, or picks a letter", self.greek)
        self.greek_menu = QMenu(self)
        for ch in GREEK_MENU: self.greek_menu.addAction(ch).setData(ch)
        self.greek_menu.triggered.connect(self._insert_symbol)
        self._button("A⁺", "Larger (Ctrl+Shift+>)", self.larger)
        self._button("A⁻", "Smaller (Ctrl+Shift+<)", self.smaller)
        self._button("A", "Text colour", self.colour)
        self.addWidget(QLabel("↻"))
        self.rot = QDoubleSpinBox(); self.rot.setRange(-180, 180); self.rot.setDecimals(0); self.rot.setButtonSymbols(QDoubleSpinBox.NoButtons); self.rot.setSingleStep(15); self.rot.setSuffix("°"); self.rot.setMinimumWidth(70); self.rot.setMaximumWidth(80)
        self.rot.setWrapping(True); self.rot.setToolTip("Orientation: angle of the text, counter-clockwise (0 = horizontal, 90 = vertical)")
        self.addWidget(self.rot)
        self._button("↺", "Reset: back to the graph's own font, size, colour, words and position for this text", self.reset)
        C, CS = int(Qt.ControlModifier.value), int((Qt.ControlModifier | Qt.ShiftModifier).value)
        K = lambda k: int(getattr(Qt, k).value)
        self.keys = {(C, K("Key_B")): "key_bold", (C, K("Key_I")): "key_italic", (C, K("Key_Equal")): "sub", (CS, K("Key_Plus")): "sup",
                     (CS, K("Key_Equal")): "sup", (C, K("Key_Plus")): "sup", (C, K("Key_Minus")): "subsup", (C, K("Key_G")): "greek",
                     (CS, K("Key_Greater")): "larger", (CS, K("Key_Period")): "larger", (CS, K("Key_Less")): "smaller", (CS, K("Key_Comma")): "smaller"}
        self.field.returnPressed.connect(self.commit); self.field.editingFinished.connect(self.commit)
        self.family.activated.connect(self._family); self.family.lineEdit().returnPressed.connect(self._family)
        self.size.editingFinished.connect(self._size); self.rot.editingFinished.connect(self._rotation)
        self.load(None)

    def _button(self, text, tip, slot, check=False, bold=False, italic=False):
        b = QToolButton(); b.setText(text); b.setToolTip(tip); b.setCheckable(check); b.setAutoRaise(True); b.setMaximumWidth(30)
        f = QFont(); f.setBold(bold); f.setItalic(italic); f.setPointSize(10); b.setFont(f); b.clicked.connect(slot); self.addWidget(b)
        self.buttons.append(b); return b

    def eventFilter(self, obj, e):
        """In the words field the formatting keys win over the window's own (Ctrl+= is subscript here, not zoom)."""
        if obj is self.field and e.type() in (QEvent.ShortcutOverride, QEvent.KeyPress):
            name = self.keys.get(_mods(e))
            if name:
                e.accept()
                if e.type() == QEvent.KeyPress: getattr(self, name)()
                return True
        return False

    # ---- state
    def alive(self):
        """False while the graph window is closing or closed: losing focus then must not redraw it."""
        try:
            from shiboken6 import isValid
            if not isValid(self.g) or not isValid(self): return False
        except ImportError: pass
        return not self.g.isHidden() and not getattr(self.g.main, "_bulk_close", False)

    def current(self): return self.g._text_target(self.key) if self.key else None

    def apply(self, **kw):
        if self.key and not self.busy and self.alive(): self.g._set_text(self.key, **kw)

    def commit(self, *_):
        if not self.key or self.busy or not self.alive() or not self.field.isEnabled(): return
        cur = self.current()
        if cur is None or self.field.text() != cur[2].get("text", cur[3]): self.apply(text=self.field.text())

    def wrap(self, left, right):
        """Wrap the selected words of the field in markup (or insert empty markup at the cursor) and apply."""
        f = self.field; t = f.text(); n = len(f.selectedText()); a = f.selectionStart() if n else f.cursorPosition()
        f.setText(t[:a] + left + t[a:a + n] + right + t[a + n:]); f.setCursorPosition(a + len(left) + n); self.commit()

    # ---- buttons and keys
    def sup(self, *_): self.wrap("^{", "}")
    def sub(self, *_): self.wrap("_{", "}")
    def subsup(self, *_): self.wrap("_{", "}^{}")
    def key_bold(self): self.b_bold.toggle(); self.bold()
    def key_italic(self): self.b_italic.toggle(); self.italic()

    def bold(self, *_):
        if self.field.selectedText(): self.wrap("\\b{", "}")
        else: self.apply(bold=self.b_bold.isChecked())

    def italic(self, *_):
        if self.field.selectedText(): self.wrap("\\i{", "}")
        else: self.apply(italic=self.b_italic.isChecked())

    def greek(self, *_):
        f = self.field
        if f.selectedText():
            a, n, t = f.selectionStart(), len(f.selectedText()), f.text(); f.setText(t[:a] + to_greek(t[a:a + n]) + t[a + n:]); self.commit()
        else: self.greek_menu.exec(self.b_greek.mapToGlobal(self.b_greek.rect().bottomLeft()))

    def _insert_symbol(self, act): self.field.insert(act.data()); self.commit()

    def larger(self, *_):
        if self.key: self.size.setValue(self.size.value() + 1); self.apply(size=self.size.value())

    def smaller(self, *_):
        if self.key: self.size.setValue(self.size.value() - 1); self.apply(size=self.size.value())

    def colour(self, *_):
        import matplotlib
        cur = self.current()
        if cur is None: return
        c = QColorDialog.getColor(QColor(matplotlib.colors.to_hex(cur[1][0].get_color())), self.g, "Text colour")
        if c.isValid(): self.apply(color=c.name())

    def reset(self, *_):
        if self.key: self.g._set_text(self.key, reset=True)

    def _family(self, *_): self.apply(family=self.family.currentText())

    def _size(self):
        cur = self.current()
        if cur is not None and abs(self.size.value() - float(cur[2].get("size", cur[1][0].get_fontsize()))) > 1e-6: self.apply(size=self.size.value())

    def _rotation(self):
        cur = self.current()
        if cur is not None and abs(self.rot.value() - float(cur[2].get("rotation", cur[1][0].get_rotation()))) > 1e-6: self.apply(rotation=self.rot.value())

    def load(self, key):
        """Show the selected text's words and format in the bar (key None: nothing selected)."""
        self.key = key; cur = self.current(); self.busy = True
        try:
            controls = [self.field, self.family, self.size, self.rot] + self.buttons
            if cur is None:
                self.key = None; self.field.clear()
                for w in controls: w.setEnabled(False)
                return
            k, arts, ov, words = cur; t = arts[0]
            for w in controls: w.setEnabled(True)
            ticks = k.endswith(("@xticks", "@yticks", "@zticks")); self.field.setEnabled(not ticks)
            self.field.setText(f"({len(arts)} tick labels: format only)" if ticks else ov.get("text", words))
            self.family.setCurrentText(ov.get("family") or (t.get_fontfamily() or ["DejaVu Sans"])[0])
            self.size.setValue(float(ov.get("size", t.get_fontsize()))); self.rot.setValue(float(ov.get("rotation", t.get_rotation())))
            self.b_bold.setChecked(bool(ov.get("bold", str(t.get_fontweight()) in ("bold", "700", "heavy", "black"))))
            self.b_italic.setChecked(bool(ov.get("italic", t.get_fontstyle() == "italic")))
        finally: self.busy = False


def make_bar(graph): return TextBar(graph)
