"""PlotBench modern style sheet (light and dark). Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>"""

ACCENT = "#1f8f86"  # teal from the logo
ACCENT_HOVER = "#23a59a"


def palette(theme):
    if theme == "dark":
        return dict(bg="#202124", panel="#2a2b2f", raised="#33353a", base="#1b1c1f", text="#e6e6e6", muted="#9aa0a6",
                    border="#3d4046", grid="#4a4d54", hover="#3a3d44", header="#2f3136", sel="#1f8f8655")
    return dict(bg="#f4f5f7", panel="#ffffff", raised="#ffffff", base="#ffffff", text="#1f2328", muted="#5f6670",
                border="#d7dae0", grid="#d9dce2", hover="#eef1f5", header="#f1f3f6", sel="#1f8f8633")


def arrows(theme):
    """Paths of chevron arrows (down, up, right) drawn in the theme's text colour, for combo boxes, spin boxes, tree branches and
    folding headers; Qt draws none, or faint ones, once a style sheet styles those widgets."""
    import os, tempfile
    col = palette(theme)["text"]; d = os.path.join(tempfile.gettempdir(), "plotbench_arrows"); os.makedirs(d, exist_ok=True); out = {}
    for name, pts in (("down", "3,6 8,11 13,6"), ("up", "3,10 8,5 13,10"), ("right", "6,3 11,8 6,13")):
        f = os.path.join(d, f"{name}_{theme}.svg").replace("\\", "/")
        with open(f, "w") as h:
            h.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16"><polyline points="{pts}" fill="none" '
                    f'stroke="{col}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>')
        out[name] = f
    return out


def qss(theme):
    c = palette(theme); a, ah = ACCENT, ACCENT_HOVER; ar = arrows(theme)
    return f"""
* {{ font-family: "Segoe UI", "Arial"; font-size: 9.5pt; }}
QMainWindow, QDialog {{ background: {c['bg']}; }}
QMenuBar {{ background: {c['panel']}; border-bottom: 1px solid {c['border']}; padding: 2px 4px; }}
QMenuBar::item {{ padding: 5px 10px; border-radius: 6px; background: transparent; }}
QMenuBar::item:selected {{ background: {c['hover']}; }}
QMenu {{ background: {c['raised']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 6px; }}
QMenu::item {{ padding: 6px 26px 6px 14px; border-radius: 5px; }}
QMenu::item:selected {{ background: {a}; color: white; }}
QMenu::separator {{ height: 1px; background: {c['border']}; margin: 5px 8px; }}
QToolBar {{ background: {c['panel']}; border: none; spacing: 3px; padding: 3px; }}
QToolBar::separator {{ background: {c['border']}; width: 1px; height: 1px; margin: 4px; }}
QToolButton {{ border: 1px solid transparent; border-radius: 6px; padding: 3px; }}
QToolButton:hover {{ background: {c['hover']}; border-color: {c['border']}; }}
QToolButton:checked, QToolButton:pressed {{ background: {c['sel']}; border-color: {a}; }}
QPushButton {{ background: {c['raised']}; border: 1px solid {c['border']}; border-radius: 6px; padding: 6px 16px; }}
QPushButton:hover {{ border-color: {a}; background: {c['hover']}; }}
QPushButton:default {{ background: {a}; color: white; border-color: {a}; }}
QPushButton:default:hover {{ background: {ah}; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit {{
    background: {c['base']}; border: 1px solid {c['border']}; border-radius: 6px; padding: 3px 6px; selection-background-color: {a}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {a}; }}
QComboBox {{ padding-right: 24px; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right; width: 22px; border: none;
    border-left: 1px solid {c['border']}; border-top-right-radius: 6px; border-bottom-right-radius: 6px; }}
QComboBox::drop-down:hover {{ background: {c['hover']}; }}
QComboBox::down-arrow {{ image: url({ar['down']}); width: 12px; height: 12px; }}
QComboBox::down-arrow:on {{ image: url({ar['up']}); }}
QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit {{ padding-right: 22px; }}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ subcontrol-origin: border; width: 20px; border: none;
    border-left: 1px solid {c['border']}; background: transparent; }}
QAbstractSpinBox::up-button {{ subcontrol-position: top right; border-top-right-radius: 6px; }}
QAbstractSpinBox::down-button {{ subcontrol-position: bottom right; border-bottom-right-radius: 6px; border-top: 1px solid {c['border']}; }}
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{ background: {c['hover']}; }}
QAbstractSpinBox::up-arrow {{ image: url({ar['up']}); width: 10px; height: 10px; }}
QAbstractSpinBox::down-arrow {{ image: url({ar['down']}); width: 10px; height: 10px; }}
QAbstractSpinBox::up-arrow:disabled, QAbstractSpinBox::down-arrow:disabled {{ image: none; }}
QTreeView::branch:has-children:closed {{ image: url({ar['right']}); }}
QTreeView::branch:has-children:open {{ image: url({ar['down']}); }}
QToolButton::menu-indicator {{ image: url({ar['down']}); width: 10px; height: 10px; subcontrol-position: bottom right; }}
QToolButton[popupMode="1"] {{ padding-right: 14px; }}
QToolButton::menu-button {{ border: none; width: 14px; }}
QToolButton::menu-arrow {{ image: url({ar['down']}); width: 10px; height: 10px; }}
QComboBox QAbstractItemView {{ background: {c['raised']}; border: 1px solid {c['border']}; selection-background-color: {a}; selection-color: white; }}
QCheckBox::indicator {{ width: 15px; height: 15px; border-radius: 4px; border: 1px solid {c['border']}; background: {c['base']}; }}
QCheckBox::indicator:checked {{ background: {a}; border-color: {a}; }}
QTabWidget::pane {{ border: 1px solid {c['border']}; border-radius: 8px; top: -1px; background: {c['panel']}; }}
QTabBar::tab {{ background: transparent; padding: 6px 14px; margin-right: 2px; border-top-left-radius: 7px; border-top-right-radius: 7px; color: {c['muted']}; }}
QTabBar::tab:selected {{ background: {c['panel']}; color: {c['text']}; border: 1px solid {c['border']}; border-bottom: 2px solid {a}; }}
QTabBar::tab:hover:!selected {{ background: {c['hover']}; color: {c['text']}; }}
QDockWidget::title {{ background: {c['panel']}; padding: 6px 8px; border-bottom: 1px solid {c['border']}; font-weight: 600; }}
QTreeWidget, QListWidget {{ background: {c['panel']}; border: none; outline: 0; }}
QTreeWidget::item, QListWidget::item {{ padding: 3px; border-radius: 5px; }}
QTreeWidget::item:hover, QListWidget::item:hover {{ background: {c['hover']}; }}
QTreeWidget::item:selected, QListWidget::item:selected {{ background: {c['sel']}; color: {c['text']}; }}
QTableView {{ gridline-color: {c['grid']}; background: {c['base']}; selection-background-color: {a}; selection-color: white; border: none; }}
QHeaderView::section {{ background: {c['header']}; border: 0px; border-right: 1px solid {c['grid']}; border-bottom: 1px solid {c['grid']};
    padding: 4px 6px; font-weight: 600; color: {c['text']}; }}
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle {{ background: {c['grid']}; border-radius: 4px; min-height: 24px; min-width: 24px; }}
QScrollBar::handle:hover {{ background: {c['muted']}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: none; border: none; width: 0; height: 0; }}
QStatusBar {{ background: {c['panel']}; border-top: 1px solid {c['border']}; color: {c['muted']}; }}
QMdiArea {{ background: {c['bg']}; }}
QToolTip {{ background: {c['raised']}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 6px; padding: 5px; }}
QLabel#sectionTitle {{ font-size: 11pt; font-weight: 600; }}
QFrame#formatBar {{ background: {c['panel']}; border-bottom: 1px solid {c['border']}; }}
"""
