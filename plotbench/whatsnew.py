"""What's new: the release notes of this version (from CHANGELOG.md), shown once after an update and from Help > What's New.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import re
import sys
from pathlib import Path


def changelog_path():
    """CHANGELOG.md beside the program (installed builds) or at the top of the source tree."""
    for p in (Path(getattr(sys, "_MEIPASS", "")) / "CHANGELOG.md", Path(sys.executable).resolve().parent / "CHANGELOG.md",
              Path(__file__).resolve().parent.parent / "CHANGELOG.md"):
        if p.is_file(): return p
    return None


def sections(text):
    """[(version, date or '', markdown body)] in the order of the file."""
    out = []
    for m in re.finditer(r"^## (\d+\.\d+\.\d+)\s*(?:\(([^)]*)\))?\s*$(.*?)(?=^## |\Z)", text, re.M | re.S):
        out.append((m.group(1), (m.group(2) or "").strip(), m.group(3).strip()))
    return out


def notes(version):
    """(date, markdown) of a version's release notes, or None."""
    p = changelog_path()
    if p is None: return None
    for v, date, body in sections(p.read_text(encoding="utf-8")):
        if v == version: return date, body
    return None


def muted(parent):
    from .ui_style import palette
    return palette(getattr(parent, "_theme", "light"))["muted"]


def show(parent, version):
    """A window with the version's release notes. Returns it (None when there are no notes for this version)."""
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox, QLabel
    got = notes(version)
    if got is None: return None
    date, body = got
    d = QDialog(parent); d.setWindowTitle(f"What's new in PlotBench {version}"); d.resize(760, 620)
    head = QLabel(f"<h2 style='margin:0'>What's new in PlotBench {version}</h2>"
                  f"<span style='color:{muted(parent)}'>{'Released ' + date + '. ' if date and 'not yet' not in date else ''}"
                  "Help &gt; What's New shows this again.</span>")
    box = QTextBrowser(); box.setOpenExternalLinks(True); box.setMarkdown(body)
    bb = QDialogButtonBox(QDialogButtonBox.Ok); bb.accepted.connect(d.accept)
    lay = QVBoxLayout(d); lay.addWidget(head); lay.addWidget(box, 1); lay.addWidget(bb)
    d.show(); return d


def _demo():
    text = "# Changelog\n\n## 2.0.0 (2027-01-02)\n\n- A\n  more\n- B\n\n## 1.9.9\n\n- C\n"
    s = sections(text); assert [(v, d) for v, d, _ in s] == [("2.0.0", "2027-01-02"), ("1.9.9", "")] and s[0][2] == "- A\n  more\n- B", s
    assert changelog_path() is not None and notes("1.30.0") is not None
    print("WHATSNEW OK")


if __name__ == "__main__":
    _demo()
