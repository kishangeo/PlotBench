"""Help windows: the user manual (read in the app, or save as PDF) and the feedback form.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import platform
import sys
from pathlib import Path
from urllib.parse import quote

from PySide6.QtCore import Qt, QUrl, QMarginsF, QSizeF
from PySide6.QtGui import QDesktopServices, QTextDocument, QPdfWriter, QPageSize, QPageLayout, QTextCharFormat, QColor, QKeySequence
from PySide6.QtWidgets import (QTextEdit, QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, QPushButton, QLineEdit, QComboBox, QPlainTextEdit,
                               QCheckBox, QFormLayout, QLabel, QFileDialog, QApplication, QMessageBox, QListWidget, QSplitter)

MANUAL_DIR = Path(__file__).parent / "manual"
MANUAL = MANUAL_DIR / "manual.html"
AUTHOR, CONTACT = "Kishan Tiwari", "kishantiwari@iitkgp.ac.in"


def save_manual_pdf(path, html_path=MANUAL):
    """Typeset the HTML manual (with its screenshots) into an A4 PDF."""
    doc = QTextDocument(); doc.setBaseUrl(QUrl.fromLocalFile(str(Path(html_path).parent) + "/"))
    doc.setHtml(Path(html_path).read_text(encoding="utf-8"))
    w = QPdfWriter(str(path)); w.setTitle("PlotBench User Manual"); w.setCreator(AUTHOR); w.setResolution(150)
    if hasattr(w, "setAuthor"): w.setAuthor(AUTHOR)
    w.setPageLayout(QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait, QMarginsF(15, 15, 15, 15), QPageLayout.Millimeter))
    doc.setPageSize(QSizeF(w.width(), w.height()))
    doc.print_(w); return str(path)


class ManualWindow(QDialog):
    """The manual with a clickable table of contents and a search box."""

    def __init__(self, parent, anchor=None):
        super().__init__(parent); self.setWindowTitle("PlotBench User Manual"); self.resize(1180, 820)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self.view = QTextBrowser(); self.view.setOpenExternalLinks(True)
        self.view.setSearchPaths([str(MANUAL_DIR)]); self.view.setSource(QUrl.fromLocalFile(str(MANUAL)))
        self.toc = QListWidget(); self.toc.setMaximumWidth(300)
        for level, text, aid in self._headings(): self.toc.addItem(("    " * (level - 2)) + text); self.toc.item(self.toc.count() - 1).setData(Qt.UserRole, aid)
        self.toc.itemClicked.connect(lambda it: self.view.scrollToAnchor(it.data(Qt.UserRole)))
        self.find = QLineEdit(); self.find.setPlaceholderText("Find in manual (Enter = next, Shift+Enter = previous)")
        self.find.setClearButtonEnabled(True); self.find.textChanged.connect(self._highlight)
        self.hits = QLabel(""); self.hits.setMinimumWidth(110)
        pdf = QPushButton("Save as PDF..."); pdf.clicked.connect(self._pdf)
        web = QPushButton("Open in web browser"); web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(MANUAL))))
        for b in (pdf, web): b.setAutoDefault(False); b.setDefault(False)  # Enter in the search box must not press these
        top = QHBoxLayout(); top.addWidget(self.find, 1); top.addWidget(self.hits); top.addWidget(web); top.addWidget(pdf)
        split = QSplitter(); split.addWidget(self.toc); split.addWidget(self.view); split.setStretchFactor(1, 1)
        lay = QVBoxLayout(self); lay.addLayout(top); lay.addWidget(split, 1)
        if anchor: self.view.scrollToAnchor(anchor)

    def _headings(self):
        import re
        html = MANUAL.read_text(encoding="utf-8") if MANUAL.exists() else ""
        return [(int(m.group(1)), re.sub("<[^>]+>", "", m.group(3)), m.group(2))
                for m in re.finditer(r"<h([23])[^>]*id=['\"]([^'\"]+)['\"][^>]*>(.*?)</h\1>", html)]

    def keyPressEvent(self, ev):
        if ev.key() in (Qt.Key_Return, Qt.Key_Enter) and self.find.hasFocus():
            return self._find(back=bool(ev.modifiers() & Qt.ShiftModifier))
        if ev.key() == Qt.Key_F3: return self._find(back=bool(ev.modifiers() & Qt.ShiftModifier))
        if ev.matches(QKeySequence.Find): self.find.setFocus(); self.find.selectAll(); return
        super().keyPressEvent(ev)

    def _highlight(self, text):
        """Mark every match in yellow and show how many there are."""
        sels, doc = [], self.view.document()
        if text.strip():
            fmt = QTextCharFormat(); fmt.setBackground(QColor("#ffe36e")); fmt.setForeground(QColor("black"))
            c = doc.find(text)
            while not c.isNull() and len(sels) < 2000:
                s = QTextEdit.ExtraSelection(); s.cursor = c; s.format = fmt; sels.append(s); c = doc.find(text, c)
        self.view.setExtraSelections(sels)
        self.hits.setText("" if not text.strip() else f"{len(sels)} match{'es' if len(sels) != 1 else ''}" if sels else "no match")
        self.hits.setStyleSheet("color: firebrick" if text.strip() and not sels else "")
        return len(sels)

    def _find(self, back=False):
        t = self.find.text()
        if not t.strip(): return False
        flag = QTextDocument.FindBackward if back else QTextDocument.FindFlag(0)
        if self.view.find(t, flag): return True
        c = self.view.textCursor(); c.movePosition(c.End if back else c.Start); self.view.setTextCursor(c)  # wrap around
        return self.view.find(t, flag)

    def _pdf(self):
        fn, _ = QFileDialog.getSaveFileName(self, "Save manual as PDF", "PlotBench_User_Manual.pdf", "PDF (*.pdf)")
        if not fn: return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try: save_manual_pdf(fn)
        finally: QApplication.restoreOverrideCursor()
        QDesktopServices.openUrl(QUrl.fromLocalFile(fn))


def system_info(version):
    from PySide6 import __version__ as pyside
    import numpy, scipy, matplotlib, pandas
    return (f"PlotBench {version}; {platform.system()} {platform.release()} ({platform.version()}); Python {sys.version.split()[0]}; "
            f"PySide6 {pyside}; numpy {numpy.__version__}; scipy {scipy.__version__}; matplotlib {matplotlib.__version__}; pandas {pandas.__version__}")


class FeedbackDialog(QDialog):
    """Write feedback, then send it with your e-mail program, copy it, or save it to a file. Nothing is sent automatically."""

    def __init__(self, parent, version):
        super().__init__(parent); self.setWindowTitle("Send Feedback"); self.resize(620, 560); self.version = version
        self.kind = QComboBox(); self.kind.addItems(["Bug report", "Feature request", "Question", "Something I liked", "Other"])
        self.subject = QLineEdit(); self.subject.setPlaceholderText("One line summary")
        self.text = QPlainTextEdit(); self.text.setPlaceholderText(
            "What happened, or what would you like?\nFor a bug: what you did, what you expected, what you saw (and any error message).")
        self.reply = QLineEdit(); self.reply.setPlaceholderText("Optional: your e-mail if you want a reply")
        self.sysinfo = QCheckBox("Include program and system versions (helps with bug reports)"); self.sysinfo.setChecked(True)
        note = QLabel(f"<span style='color:gray'>Feedback goes to {AUTHOR} ({CONTACT}). <b>Send by e-mail</b> opens your e-mail program with "
                      "the message filled in; you can read it before sending. Nothing is sent by PlotBench itself.</span>"); note.setWordWrap(True)
        f = QFormLayout(); f.addRow("Type", self.kind); f.addRow("Subject", self.subject); f.addRow("Message", self.text); f.addRow("Reply to", self.reply)
        f.addRow("", self.sysinfo)
        mail, copy, save, close = QPushButton("Send by e-mail"), QPushButton("Copy to clipboard"), QPushButton("Save as file..."), QPushButton("Close")
        mail.setDefault(True); mail.clicked.connect(self.send); copy.clicked.connect(self.copy); save.clicked.connect(self.save); close.clicked.connect(self.reject)
        row = QHBoxLayout(); row.addWidget(mail); row.addWidget(copy); row.addWidget(save); row.addStretch(); row.addWidget(close)
        lay = QVBoxLayout(self); lay.addLayout(f); lay.addWidget(note); lay.addLayout(row)

    def title(self): return f"[PlotBench {self.version}] {self.kind.currentText()}: {self.subject.text().strip() or '(no subject)'}"

    def body(self):
        parts = [self.text.toPlainText().strip() or "(no message)"]
        if self.reply.text().strip(): parts.append(f"Reply to: {self.reply.text().strip()}")
        if self.sysinfo.isChecked(): parts.append(system_info(self.version))
        return "\n\n".join(parts)

    def _empty(self):
        if self.text.toPlainText().strip(): return False
        QMessageBox.information(self, "Feedback", "Please write a message first."); return True

    def send(self):
        if self._empty(): return
        body = self.body()
        if len(body) > 1800:  # long messages do not fit in a mailto link: put the full text on the clipboard
            QApplication.clipboard().setText(f"{self.title()}\n\n{body}"); body = body[:1500] + "\n\n[Message shortened: paste the full text from the clipboard.]"
        QDesktopServices.openUrl(QUrl(f"mailto:{CONTACT}?subject={quote(self.title())}&body={quote(body)}")); self.accept()

    def copy(self):
        if self._empty(): return
        QApplication.clipboard().setText(f"To: {CONTACT}\nSubject: {self.title()}\n\n{self.body()}")
        QMessageBox.information(self, "Feedback", f"Copied. Paste it into an e-mail to {CONTACT}.")

    def save(self):
        if self._empty(): return
        fn, _ = QFileDialog.getSaveFileName(self, "Save feedback", "PlotBench_feedback.txt", "Text (*.txt)")
        if fn: Path(fn).write_text(f"To: {CONTACT}\nSubject: {self.title()}\n\n{self.body()}\n", encoding="utf-8")
