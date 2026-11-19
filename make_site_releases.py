"""Website release sections from CHANGELOG.md: the download buttons for the newest release, its release notes, and the earlier
versions (up to ten) with download links for every system and their notes. Run after a release is published on GitHub:

    python make_site_releases.py

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import html
import re
from pathlib import Path

from plotbench.whatsnew import sections

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "docs" / "index.html"
REPO = "https://github.com/kishangeo/PlotBench"
FIRST_PUBLISHED = (1, 30, 0)  # the first version released on GitHub with Windows, macOS and Linux builds
KEEP = 10
FILES = [("Windows", "Setup.exe", ".exe"), ("macOS (Apple silicon)", "macos-arm64.dmg", ".dmg"),
         ("macOS (Intel)", "macos-intel.dmg", ".dmg"), ("Linux", "linux-x86_64.tar.gz", ".tar.gz")]


def url(v, suffix): return f"{REPO}/releases/download/v{v}/PlotBench-{v}-{suffix}"


def md_html(text):
    """The changelog's Markdown (bullets with continuation lines, `code`, **bold**) as HTML."""
    items, cur = [], None
    for line in text.splitlines():
        if line.startswith("- "): cur = [line[2:].strip()]; items.append(cur)
        elif line.strip() and cur is not None: cur.append(line.strip())
    def inline(s):
        s = html.escape(s, quote=False)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s); return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    return "<ul>" + "".join(f"<li>{inline(' '.join(i))}</li>" for i in items) + "</ul>"


def published(text):
    """[(version, date, notes)] of the released versions, newest first, at most KEEP."""
    out = [(v, d, b) for v, d, b in sections(text) if tuple(map(int, v.split("."))) >= FIRST_PUBLISHED and d and "not yet" not in d]
    return out[:KEEP]


def build(page, rel):
    v, date, body = rel[0]
    page = re.sub(r"releases/download/v\d+\.\d+\.\d+/PlotBench-\d+\.\d+\.\d+-", f"releases/download/v{v}/PlotBench-{v}-", page)
    page = re.sub(r"Get PlotBench \d+\.\d+\.\d+", f"Get PlotBench {v}", page)
    page = re.sub(r"Version \d+\.\d+\.\d+ · Free", f"Version {v} · Free", page)
    rows = []
    for ov, od, ob in rel[1:]:
        links = " ".join(f'<a href="{url(ov, s)}">{name}</a>' for name, s, _ in FILES)
        rows.append(f'<details class="rel"><summary><b>{ov}</b><span>{od}</span></summary>'
                    f'<p class="files">{links}</p>{md_html(ob)}</details>')
    block = (f'<!-- releases:start (made by make_site_releases.py from CHANGELOG.md; do not edit by hand) -->\n'
             f'<section id="releases"><div class="wrap">\n'
             f'  <div class="eyebrow">Release notes</div>\n  <h2>What\'s new in {v}</h2>\n'
             f'  <p class="lead">Released {date}. The same notes open in PlotBench after the update, and under Help &gt; What\'s New.</p>\n'
             f'  <div class="notes">{md_html(body)}</div>\n'
             + (f'  <h3 class="older">Earlier versions</h3>\n  <p class="note">The last {len(rel) - 1} earlier releases, each with its '
                f'downloads and notes. Every release is also on the <a href="{REPO}/releases">GitHub Releases page</a> and archived on '
                f'<a href="https://doi.org/10.5281/zenodo.24330955">Zenodo</a>.</p>\n  ' + "\n  ".join(rows) + "\n" if len(rel) > 1 else "")
             + '</div></section>\n<!-- releases:end -->')
    if "<!-- releases:start" in page:
        page = re.sub(r"<!-- releases:start.*?<!-- releases:end -->", lambda m: block, page, flags=re.S)
    else:
        page = page.replace('<section id="cite">', block + '\n\n<section id="cite">', 1)
    if 'href="#releases"' not in page: page = page.replace('<a href="#compare">Compare</a>', '<a href="#compare">Compare</a><a href="#releases">Release notes</a>', 1)
    css = ('.notes ul,.rel ul{margin:0;padding-left:20px;color:var(--muted);font-size:15px}.notes li,.rel li{margin:6px 0}'
           '.notes{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:22px 28px}'
           '.older{margin:48px 0 4px;font-size:20px}.rel{border:1px solid var(--border);border-radius:12px;background:var(--panel);margin:10px 0;padding:0 20px}'
           '.rel summary{cursor:pointer;padding:14px 0;display:flex;gap:14px;align-items:baseline}.rel summary span{color:var(--muted);font-size:14px}'
           '.rel[open]{padding-bottom:16px}.rel .files{display:flex;flex-wrap:wrap;gap:8px 18px;margin:0 0 10px;font-size:14.5px}')
    if ".rel summary" not in page: page = page.replace("</style>", css + "\n</style>", 1)
    return page


def main():
    rel = published((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
    if not rel: raise SystemExit("No released version in CHANGELOG.md")
    page = build(SITE.read_text(encoding="utf-8"), rel)
    SITE.write_text(page, encoding="utf-8", newline=""); print(f"docs/index.html: latest {rel[0][0]}, {len(rel) - 1} earlier versions")


if __name__ == "__main__":
    main()
