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


def parse(s):
    r"""Markup to runs [[text, bold, italic, script]] (script '', 'sub' or 'sup'). Markup: \b{..} bold, \i{..} italic, _{..}
    subscript, ^{..} superscript; they nest (_{\b{2}}). Anything else is plain text."""
    runs = []

    def add(t, b, it, sc):
        if not t: return
        if runs and runs[-1][1:] == [b, it, sc]: runs[-1][0] += t
        else: runs.append([t, b, it, sc])

    def walk(s, b, it, sc):
        i, buf = 0, []
        while i < len(s):
            c = s[i]
            if c in "_^" and i + 1 < len(s) and s[i + 1] == "{":
                body, j = _group(s, i + 1)
                if body is not None:
                    add("".join(buf), b, it, sc); buf = []; walk(body, b, it, sc or ("sub" if c == "_" else "sup")); i = j; continue
            if c == "\\" and i + 2 < len(s) and s[i + 1] in "bi" and s[i + 2] == "{":
                body, j = _group(s, i + 2)
                if body is not None:
                    add("".join(buf), b, it, sc); buf = []; walk(body, b or s[i + 1] == "b", it or s[i + 1] == "i", sc); i = j; continue
            buf.append(c); i += 1
        add("".join(buf), b, it, sc)
    walk(str(s), False, False, ""); return runs


def markup(runs):
    """Runs back to markup (the inverse of parse)."""
    out = []
    for t, b, it, sc in runs:
        if it: t = r"\i{" + t + "}"
        if b: t = r"\b{" + t + "}"
        if sc: t = ("_{" if sc == "sub" else "^{") + t + "}"
        out.append(t)
    return "".join(out)


def rich(s):
    """Markup to the string matplotlib draws: SiO_{2} -> SiO$_{\mathregular{2}}$, Fe^{3+} -> Fe$^{\mathregular{3+}}$, part of a text bold
    or italic, a subscript directly followed by a superscript stacked. Text that already holds $ goes to mathtext unchanged."""
    s = str(s)
    if "$" in s or not re.search(r"[_^]\{|\\[bi]\{", s): return s
    out, runs, k = [], parse(s), 0

    def piece(t, b, it):
        return r"\math%s{%s}" % ("bfit" if b and it else "bf" if b else "it" if it else "regular", _math(t))
    while k < len(runs):
        t, b, it, sc = runs[k]
        if not (b or it or sc): out.append(t); k += 1; continue
        if not sc: out.append("$" + piece(t, b, it) + "$"); k += 1; continue
        m = "_{%s}" % piece(t, b, it) if sc == "sub" else "^{%s}" % piece(t, b, it)
        if sc == "sub" and k + 1 < len(runs) and runs[k + 1][3] == "sup":  # stacked sub- and superscript
            m += "^{%s}" % piece(*runs[k + 1][:3]); k += 1
        out.append("$" + m + "$"); k += 1
    return "".join(out)


def to_greek(s): return "".join(GREEK.get(c, c) for c in s)




# ---------------------------------------------------------------- symbols offered by the symbol button, by kind
SYMBOLS = [
    ("Greek", "αβγδεϵζηθϑικλμνξοπϖρϱσςτυφϕχψω"
              "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"),
    ("Math", "±∓×÷·⋅∗∘√∛∜∑∏∫∬∮∂∇Δ∞∝′″‴‰‱%"
             "−⁄⌊⌋⌈⌉⟨⟩‖∣∠∡⊥∥≅⋆⊕⊗⊙†‡"),
    ("Relations", "=≠≈≃≅≡≢≤≥≦≧≪≫<>∼≁≙≟≔∈∉∋⊂⊃⊆⊇"
                  "∪∩∅∀∃∄¬∧∨⊢⊨∴∵∟"),
    ("Arrows", "←→↑↓↔↕↖↗↘↙⇌⇋⇄⇆⇐⇒⇑⇓⇔⇕⟶⟵⟷⟹⟸"
               "↦↺↻⇀⇁↼↽⤴⤵↯➜➤▶◀▲▼"),
    ("Scripts", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱ"
                "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓ"),
    ("Units", "°℃℉ÅµΩ℧‰ℓℏħ№™©®§¶†‡′″㎡㎥㏑㎠"
              "≤≥≈±×·"),
    ("Chemistry", "⇌⇄→⇒↑↓•·∙∶∷≡═―–⁺⁻²³₂₃₄⊕⊖⊙☉♁☿♀♂♃♄"),
    ("Shapes", "●○■□▲△▼▽◆◇★☆✚✖✕✓✗✦✧✶⬟⬠⬡⬢◐◑◒◓"
               "⬤▪▫▬▭▮▸◂♦♣♠♥"),
    ("Numbers", "½⅓⅔¼¾⅕⅖⅗⅘⅙⅚⅐⅛⅜⅝⅞⅑⅒"
                "ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫⅰⅱⅲⅳⅴⅵⅶⅷⅸⅹ"
                "①②③④⑤⑥⑦⑧⑨⑩"),
    ("Letters", "ÅåÄäÖöÜüÉéÈèÊêËëÍíÑñÇçßØøÆæŒœ"
                "ŁłıŠšŽžČčĞğŘřÓóÚúÁáÃãÕõÂâÔôāēīōū"),
    ("Punctuation", "–—…‐‑‘’‚“”„«»‹›•‣⁃¡¿¦‖※⁂⁀¨´ˆ˜¯"),
]


# ---------------------------------------------------------------- the format bar (Qt)
from PySide6.QtWidgets import (QToolBar, QTextEdit, QComboBox, QDoubleSpinBox, QLabel, QToolButton, QMenu, QColorDialog, QWidgetAction,  # noqa: E402
                               QTabWidget, QWidget, QGridLayout, QFrame)
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor  # noqa: E402
from PySide6.QtCore import Qt, QEvent  # noqa: E402

_FONTS = []
SUB, SUP, NORMAL = QTextCharFormat.AlignSubScript, QTextCharFormat.AlignSuperScript, QTextCharFormat.AlignNormal


def _fonts():
    if not _FONTS:
        from matplotlib import font_manager
        _FONTS.extend(sorted({f.name for f in font_manager.fontManager.ttflist}))
    return _FONTS


def _mods(e):
    m = e.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)
    return (int(m.value) if hasattr(m, "value") else int(m), int(e.key()))


def doc_runs(edit):
    """[[text, bold, italic, script]] of a QTextEdit, read from the character formats shown in it."""
    runs, block = [], edit.document().begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            fr = it.fragment()
            if fr.isValid():
                f = fr.charFormat(); va = f.verticalAlignment()
                sc = "sub" if va == SUB else "sup" if va == SUP else ""
                r = [fr.text().replace(" ", " "), f.fontWeight() >= QFont.Bold, f.fontItalic(), sc]
                if runs and runs[-1][1:] == r[1:]: runs[-1][0] += r[0]
                else: runs.append(r)
            it += 1
        block = block.next()
    return runs


def set_runs(edit, runs):
    """Show runs in a QTextEdit with real bold, italic, subscript and superscript."""
    edit.clear(); cur = QTextCursor(edit.document())
    for t, b, i, sc in runs:
        f = QTextCharFormat(); f.setFontWeight(QFont.Bold if b else QFont.Normal); f.setFontItalic(bool(i))
        f.setVerticalAlignment(SUB if sc == "sub" else SUP if sc == "sup" else NORMAL); cur.insertText(t, f)
    edit.setCurrentCharFormat(QTextCharFormat())


class TextBar(QToolBar):
    """Origin-style text format bar of a graph window. The words box shows the selected graph text with its formatting; select
    letters in it and press B, I, x2 (superscript), x2 (subscript) or x21 (stacked) to format just those letters, as in a word
    processor. Font, size, colour and angle apply to the whole text. All state lives on this object (no closures over child
    widgets), so a closed graph leaves nothing behind that Qt could reuse."""

    def __init__(self, graph):
        super().__init__("Text format"); self.setObjectName("text_format_bar"); self.g = graph; self.key = None; self.busy = False
        self.addWidget(QLabel(" T "))
        self.field = QTextEdit(); self.field.setAcceptRichText(False); self.field.setLineWrapMode(QTextEdit.NoWrap)
        self.field.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.field.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.field.setTabChangesFocus(True); self.field.setFixedHeight(32); self.field.setMinimumWidth(130); self.field.setMaximumWidth(300)
        self.field.document().setDocumentMargin(3)
        self.field.setPlaceholderText("Click a text in the graph")
        self.field.setToolTip("Words of the selected text. Select letters, then click B, I, superscript, subscript or stacked to format "
                              "only those letters. Enter applies the words.")
        self.field.installEventFilter(self); self.addWidget(self.field)
        self.family = QComboBox(); self.family.setEditable(True); self.family.setMaxVisibleItems(25); self.family.setMinimumWidth(100)
        self.family.setMaximumWidth(150); self.family.setToolTip("Font of the whole text"); self.family.addItems(_fonts()); self.addWidget(self.family)
        self.size = QDoubleSpinBox(); self.size.setRange(3, 96); self.size.setDecimals(1); self.size.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.size.setToolTip("Size of the whole text (pt)"); self.size.setMinimumWidth(76); self.size.setMaximumWidth(84); self.addWidget(self.size)
        self.buttons = []
        self.b_bold = self._button("B", "Bold (Ctrl+B): the selected letters, or the whole text", self.bold, bold=True)
        self.b_italic = self._button("I", "Italic (Ctrl+I): the selected letters, or the whole text", self.italic, italic=True)
        self._button("x²", "Superscript (Ctrl+Shift+=): the selected letters, e.g. the 3+ of Fe3+", self.sup)
        self._button("x₂", "Subscript (Ctrl+=): the selected letters, e.g. the 2 of SiO2", self.sub)
        self._button("x²₁", "Stacked sub- and superscript (Ctrl+-): select e.g. '2,3+' (or two characters); the part before the comma "
                     "becomes the subscript and the part after it the superscript, one above the other", self.subsup)
        self.b_sym = self._button("Ω", "Symbols (Greek, maths, relations, arrows, units, chemistry, shapes, numbers, letters, punctuation); "
                                  "Ctrl+G turns selected Latin letters into Greek", self.symbols)
        self.sym_menu = QMenu(self); wa = QWidgetAction(self.sym_menu); wa.setDefaultWidget(self._symbol_tabs()); self.sym_menu.addAction(wa)
        self._button("A⁺", "Larger, whole text (Ctrl+Shift+>)", self.larger)
        self._button("A⁻", "Smaller, whole text (Ctrl+Shift+<)", self.smaller)
        self._button("A", "Colour of the whole text", self.colour)
        self.addWidget(QLabel("↻"))
        self.rot = QDoubleSpinBox(); self.rot.setRange(-180, 180); self.rot.setDecimals(0); self.rot.setSingleStep(15); self.rot.setSuffix("°")
        self.rot.setButtonSymbols(QDoubleSpinBox.NoButtons); self.rot.setWrapping(True); self.rot.setMinimumWidth(70); self.rot.setMaximumWidth(80)
        self.rot.setToolTip("Orientation: angle of the text, counter-clockwise (0 = horizontal, 90 = vertical)"); self.addWidget(self.rot)
        self._button("↺", "Reset: back to the graph's own font, size, colour, words and position for this text", self.reset)
        C, CS = int(Qt.ControlModifier.value), int((Qt.ControlModifier | Qt.ShiftModifier).value)
        K = lambda k: int(getattr(Qt, k).value)
        self.keys = {(C, K("Key_B")): "bold", (C, K("Key_I")): "italic", (C, K("Key_Equal")): "sub", (CS, K("Key_Plus")): "sup",
                     (CS, K("Key_Equal")): "sup", (C, K("Key_Plus")): "sup", (C, K("Key_Minus")): "subsup", (C, K("Key_G")): "greek",
                     (CS, K("Key_Greater")): "larger", (CS, K("Key_Period")): "larger", (CS, K("Key_Less")): "smaller", (CS, K("Key_Comma")): "smaller",
                     (0, K("Key_Return")): "commit", (0, K("Key_Enter")): "commit", (CS - C, K("Key_Return")): "commit"}
        self.family.activated.connect(self._family); self.family.lineEdit().returnPressed.connect(self._family)
        self.size.editingFinished.connect(self._size); self.rot.editingFinished.connect(self._rotation)
        self.load(None)

    def _button(self, text, tip, slot, bold=False, italic=False):
        b = QToolButton(); b.setText(text); b.setToolTip(tip); b.setAutoRaise(True); b.setMaximumWidth(30); b.setFocusPolicy(Qt.NoFocus)
        f = QFont(); f.setBold(bold); f.setItalic(italic); f.setPointSize(10); b.setFont(f); b.clicked.connect(slot); self.addWidget(b)
        self.buttons.append(b); return b

    def _symbol_tabs(self):
        """Symbol picker: kinds of symbol listed on the left, the symbols of the chosen kind in a grid on the right."""
        from PySide6.QtWidgets import QListWidget, QStackedWidget, QHBoxLayout
        box = QWidget(); h = QHBoxLayout(box); h.setContentsMargins(4, 4, 4, 4); h.setSpacing(6)
        kinds = QListWidget(); kinds.setFixedWidth(110); pages = QStackedWidget(); h.addWidget(kinds); h.addWidget(pages)
        for name, chars in SYMBOLS:
            page = QWidget(); grid = QGridLayout(page); grid.setSpacing(1); grid.setContentsMargins(0, 0, 0, 0)
            for i, ch in enumerate(dict.fromkeys(chars)):  # each symbol once, in order
                b = QToolButton(); b.setText(ch); b.setAutoRaise(True); b.setFixedSize(30, 30); b.setFocusPolicy(Qt.NoFocus)
                f = QFont(); f.setPointSize(12); b.setFont(f); b.setToolTip(f"U+{ord(ch):04X}"); b.setProperty("sym", ch)
                b.clicked.connect(self._symbol_clicked); grid.addWidget(b, i // 12, i % 12)
            grid.setRowStretch(grid.rowCount(), 1); grid.setColumnStretch(12, 1); pages.addWidget(page); kinds.addItem(name)
        kinds.currentRowChanged.connect(pages.setCurrentIndex); kinds.setCurrentRow(0)
        pages.setMinimumWidth(12 * 31 + 4); kinds.setMinimumHeight(len(SYMBOLS) * kinds.sizeHintForRow(0) + 8); return box

    def eventFilter(self, obj, e):
        """In the words box the formatting keys win over the window's own (Ctrl+= is subscript here, not zoom); Enter applies."""
        if obj is self.field:
            if e.type() in (QEvent.ShortcutOverride, QEvent.KeyPress):
                name = self.keys.get(_mods(e))
                if name:
                    e.accept()
                    if e.type() == QEvent.KeyPress: getattr(self, name)()
                    return True
            elif e.type() == QEvent.FocusOut and not self.sym_menu.isVisible(): self.commit()
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
    def words(self): return markup(doc_runs(self.field))

    def apply(self, **kw):
        if self.key and not self.busy and self.alive(): self.g._set_text(self.key, **kw)

    def commit(self, *_):
        """Apply the words and their formatting to the graph text (when they changed)."""
        if not self.key or self.busy or not self.alive() or not self.field.isEnabled(): return
        cur = self.current(); m = self.words()
        if cur is None or m != cur[2].get("text", cur[3]):
            c = self.field.textCursor(); a, b = c.anchor(), c.position()
            kw = {"text": m}
            for k in ("bold", "italic"):  # whole-text bold or italic now lives in the words, letter by letter
                if cur is not None and (cur[2].get(k) or k == "bold" and str(cur[1][0].get_fontweight()) in ("bold", "700") or
                                        k == "italic" and cur[1][0].get_fontstyle() == "italic"): kw[k] = False
            self.apply(**kw)
            c = self.field.textCursor(); c.setPosition(min(a, len(self.field.toPlainText()))); c.setPosition(min(b, len(self.field.toPlainText())), QTextCursor.KeepAnchor)
            self.field.setTextCursor(c)  # the same letters stay selected for the next button

    # ---- formatting of the selected letters
    def _sel(self):
        """Cursor over the selected letters, or over the whole text when nothing is selected."""
        c = self.field.textCursor()
        if not c.hasSelection(): c.select(QTextCursor.Document)
        return c

    def _all(self, c, test):
        """True when every selected letter passes test(char format)."""
        a, b = sorted((c.anchor(), c.position()))
        k = QTextCursor(self.field.document())
        for p in range(a, b):
            k.setPosition(p + 1)
            if not test(k.charFormat()): return False
        return b > a

    def _merge(self, c, f): c.mergeCharFormat(f); self.commit()

    def bold(self, *_):
        if not self.field.isEnabled():  # tick labels: the whole group
            cur = self.current(); on = not bool((cur[2] if cur else {}).get("bold", False)); return self.apply(bold=on)
        c = self._sel(); f = QTextCharFormat(); f.setFontWeight(QFont.Normal if self._all(c, lambda x: x.fontWeight() >= QFont.Bold) else QFont.Bold)
        self._merge(c, f)

    def italic(self, *_):
        if not self.field.isEnabled():
            cur = self.current(); on = not bool((cur[2] if cur else {}).get("italic", False)); return self.apply(italic=on)
        c = self._sel(); f = QTextCharFormat(); f.setFontItalic(not self._all(c, lambda x: x.fontItalic())); self._merge(c, f)

    def _script(self, va):
        c = self.field.textCursor()
        if not c.hasSelection() or not self.field.isEnabled(): return
        f = QTextCharFormat(); f.setVerticalAlignment(NORMAL if self._all(c, lambda x: x.verticalAlignment() == va) else va); self._merge(c, f)

    def sup(self, *_): self._script(SUP)
    def sub(self, *_): self._script(SUB)

    def subsup(self, *_):
        """Selected '2,3+' (or two characters) becomes a subscript 2 with a superscript 3+ stacked above it."""
        c = self.field.textCursor()
        if not c.hasSelection() or not self.field.isEnabled(): return
        t = c.selectedText(); lo, hi = (t.split(",", 1) if "," in t else (t[:1], t[1:]))
        fsub, fsup = QTextCharFormat(c.charFormat()), QTextCharFormat(c.charFormat())
        fsub.setVerticalAlignment(SUB); fsup.setVerticalAlignment(SUP)
        c.insertText(lo, fsub); c.insertText(hi, fsup); self.commit()

    def greek(self, *_):
        c = self.field.textCursor()
        if c.hasSelection(): c.insertText(to_greek(c.selectedText()), c.charFormat()); self.commit()
        else: self.symbols()

    def symbols(self, *_): self.sym_menu.exec(self.b_sym.mapToGlobal(self.b_sym.rect().bottomLeft()))

    def _symbol_clicked(self):
        ch = self.sender().property("sym")
        if ch and self.field.isEnabled(): self.field.textCursor().insertText(ch); self.commit()

    # ---- whole text
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
        """Show the selected text's words, with their formatting, and its font in the bar (key None: nothing selected)."""
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
            if ticks: self.field.setPlainText(f"({len(arts)} tick labels: format only)")
            else:
                whole_bold = bool(ov.get("bold", str(t.get_fontweight()) in ("bold", "700", "heavy", "black")))
                whole_it = bool(ov.get("italic", t.get_fontstyle() == "italic"))
                runs = parse(ov.get("text", words))
                if whole_bold or whole_it: runs = [[x, b or whole_bold, i or whole_it, sc] for x, b, i, sc in runs]
                set_runs(self.field, runs)
            self.family.setCurrentText(ov.get("family") or (t.get_fontfamily() or ["DejaVu Sans"])[0])
            self.size.setValue(float(ov.get("size", t.get_fontsize()))); self.rot.setValue(float(ov.get("rotation", t.get_rotation())))
        finally: self.busy = False


def make_bar(graph): return TextBar(graph)
