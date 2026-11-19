"""Graphs as a Word document (one per page) or a PowerPoint presentation (one per slide), written directly as Office Open XML.
No Word, PowerPoint or extra package is needed to write the files; they open in Microsoft Office, LibreOffice and Google Docs.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import zipfile
from xml.sax.saxutils import escape

EMU = 914400  # English Metric Units per inch
_HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_OD = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _rels(items):
    return _HEAD + f'<Relationships xmlns="{_REL}">' + "".join(f'<Relationship Id="{i}" Type="{_OD}/{t}" Target="{target}"/>' for i, t, target in items) + "</Relationships>"


def _fit(w_in, h_in, max_w, max_h):
    """Size in inches that fits the box and keeps the shape."""
    k = min(max_w / w_in, max_h / h_in, 1.0) if w_in > max_w or h_in > max_h else 1.0
    return w_in * k, h_in * k


def write_docx(path, pictures, title=""):
    """pictures: [(png bytes, width in inches, height in inches, caption)]. A4 portrait, one graph with its caption per page."""
    ns = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="%s" '
          'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="%s" '
          'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"') % (_OD, _A)
    body = []
    if title: body.append(f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:b/><w:sz w:val="32"/></w:rPr><w:t>{escape(title)}</w:t></w:r></w:p>')
    for i, (png, w_in, h_in, cap) in enumerate(pictures, 1):
        w_in, h_in = _fit(w_in, h_in, 6.3, 8.6); cx, cy = int(w_in * EMU), int(h_in * EMU)
        body.append(
            f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{i}" name="Graph {i}" descr="{escape(cap, {chr(34): "&quot;"})}"/>'
            f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
            f'<pic:nvPicPr><pic:cNvPr id="{i}" name="graph{i}.png"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="rId{i}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            f'</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')
        if cap: body.append(f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:t xml:space="preserve">{escape(cap)}</w:t></w:r></w:p>')
        if i < len(pictures): body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
    doc = (_HEAD + f"<w:document {ns}><w:body>" + "".join(body)
           + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>'
           + "</w:body></w:document>")
    types = (_HEAD + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
             '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types); z.writestr("_rels/.rels", _rels([("rId1", "officeDocument", "word/document.xml")]))
        z.writestr("word/document.xml", doc)
        z.writestr("word/_rels/document.xml.rels", _rels([(f"rId{i}", "image", f"media/graph{i}.png") for i in range(1, len(pictures) + 1)]))
        for i, p in enumerate(pictures, 1): z.writestr(f"word/media/graph{i}.png", p[0])
    return path


_THEME = (_HEAD + f'<a:theme xmlns:a="{_A}" name="PlotBench"><a:themeElements><a:clrScheme name="PlotBench">'
          '<a:dk1><a:srgbClr val="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="1F2937"/></a:dk2><a:lt2><a:srgbClr val="F3F4F6"/></a:lt2>'
          '<a:accent1><a:srgbClr val="14A39A"/></a:accent1><a:accent2><a:srgbClr val="1F77B4"/></a:accent2><a:accent3><a:srgbClr val="FF7F0E"/></a:accent3>'
          '<a:accent4><a:srgbClr val="2CA02C"/></a:accent4><a:accent5><a:srgbClr val="D62728"/></a:accent5><a:accent6><a:srgbClr val="9467BD"/></a:accent6>'
          '<a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink></a:clrScheme>'
          '<a:fontScheme name="PlotBench"><a:majorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
          '<a:minorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme>'
          '<a:fmtScheme name="PlotBench"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
          '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst>'
          '<a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="12700"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
          '<a:ln w="19050"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>'
          '<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>'
          '<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
          '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>')
_PNS = f'xmlns:a="{_A}" xmlns:r="{_OD}" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
_TREE0 = ('<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
          '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>')
_MAP = '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'


def write_pptx(path, pictures):
    """pictures: [(png bytes, width in inches, height in inches, caption)]. A 16:9 presentation, one graph centred on each slide
    with its caption as the slide title."""
    W, H = 12192000, 6858000; n = len(pictures)
    master = (_HEAD + f'<p:sldMaster {_PNS}><p:cSld><p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/></p:bgRef></p:bg><p:spTree>{_TREE0}</p:spTree></p:cSld>'
              f'{_MAP}<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst></p:sldMaster>')
    layout = (_HEAD + f'<p:sldLayout {_PNS} type="blank" preserve="1"><p:cSld name="Blank"><p:spTree>{_TREE0}</p:spTree></p:cSld>'
              '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>')
    pres = (_HEAD + f'<p:presentation {_PNS}><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>'
            + "".join(f'<p:sldId id="{255 + i}" r:id="rId{i + 1}"/>' for i in range(1, n + 1))
            + f'</p:sldIdLst><p:sldSz cx="{W}" cy="{H}"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>')
    types = (_HEAD + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
             '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
             '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
             '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
             '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
             + "".join(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(1, n + 1))
             + "</Types>")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types); z.writestr("_rels/.rels", _rels([("rId1", "officeDocument", "ppt/presentation.xml")]))
        z.writestr("ppt/presentation.xml", pres)
        z.writestr("ppt/_rels/presentation.xml.rels", _rels([("rId1", "slideMaster", "slideMasters/slideMaster1.xml")]
                                                             + [(f"rId{i + 1}", "slide", f"slides/slide{i}.xml") for i in range(1, n + 1)]
                                                             + [(f"rId{n + 2}", "theme", "theme/theme1.xml")]))
        z.writestr("ppt/slideMasters/slideMaster1.xml", master)
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", _rels([("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml"), ("rId2", "theme", "../theme/theme1.xml")]))
        z.writestr("ppt/slideLayouts/slideLayout1.xml", layout)
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", _rels([("rId1", "slideMaster", "../slideMasters/slideMaster1.xml")]))
        z.writestr("ppt/theme/theme1.xml", _THEME)
        for i, (png, w_in, h_in, cap) in enumerate(pictures, 1):
            top = 0.9 if cap else 0.3; k = min(12.5 / w_in, (7.2 - top) / h_in); cx, cy = int(w_in * k * EMU), int(h_in * k * EMU)
            x, y = (W - cx) // 2, int(top * EMU) + (H - int(top * EMU) - int(0.3 * EMU) - cy) // 2
            title = (f'<p:sp><p:nvSpPr><p:cNvPr id="3" name="Title"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{int(0.4 * EMU)}" y="{int(0.2 * EMU)}"/>'
                     f'<a:ext cx="{W - int(0.8 * EMU)}" cy="{int(0.6 * EMU)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
                     f'<p:txBody><a:bodyPr wrap="square" anchor="ctr"/><a:lstStyle/><a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-GB" sz="2400" b="1"/><a:t>{escape(cap)}</a:t></a:r></a:p></p:txBody></p:sp>') if cap else ""
            slide = (_HEAD + f'<p:sld {_PNS}><p:cSld><p:spTree>{_TREE0}{title}<p:pic><p:nvPicPr><p:cNvPr id="2" name="Graph {i}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
                     f'<p:blipFill><a:blip r:embed="rId2"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
                     '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>')
            z.writestr(f"ppt/slides/slide{i}.xml", slide)
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", _rels([("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml"), ("rId2", "image", f"../media/graph{i}.png")]))
            z.writestr(f"ppt/media/graph{i}.png", png)
    return path
