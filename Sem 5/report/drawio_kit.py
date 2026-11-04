"""Tiny builder for draw.io (mxGraph) diagrams.

Each diagram is written as a real .drawio file (editable in diagrams.net / draw.io) and rendered to PNG with
draw.io's own viewer engine in headless Chrome, so the report figures look exactly like draw.io output."""

import html
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

# draw.io's standard pastel palette: (fill, stroke)
PAL = {
    "blue": ("#dae8fc", "#6c8ebf"),
    "green": ("#d5e8d4", "#82b366"),
    "yellow": ("#fff2cc", "#d6b656"),
    "orange": ("#ffe6cc", "#d79b00"),
    "red": ("#f8cecc", "#b85450"),
    "purple": ("#e1d5e7", "#9673a6"),
    "gray": ("#f5f5f5", "#666666"),
    "white": ("#ffffff", "#000000"),
}
FONT = "fontFamily=Helvetica;"


def q(s):
    return escape(str(s), {'"': "&quot;"})


class Diagram:
    def __init__(self, name, width, height, fs=1.0):
        self.name, self.w, self.h = name, width, height
        self.fs = fs                      # global font scale so labels stay legible at page width
        self.cells = []
        self._n = 1

    def _id(self):
        self._n += 1
        return f"c{self._n}"

    def _vertex(self, label, x, y, w, h, style, parent="1", cid=None):
        cid = cid or self._id()
        self.cells.append(
            f'<mxCell id="{cid}" value="{q(label)}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return cid

    # ─────────────── shapes ───────────────
    def box(self, x, y, w, h, label, color="blue", font=12, bold=False, rounded=True, dashed=False, extra="", parent="1",
            align="center", cid=None):
        f, s = PAL[color]
        st = (f"rounded={1 if rounded else 0};whiteSpace=wrap;html=1;fillColor={f};strokeColor={s};fontSize={font};"
              f"fontColor=#000000;align={align};{FONT}" + ("fontStyle=1;" if bold else "") + ("dashed=1;" if dashed else "")
              + ("arcSize=10;" if rounded else "") + extra)
        return self._vertex(label, x, y, w, h, st, parent, cid)

    def container(self, x, y, w, h, label, color="gray", font=13, extra=""):
        f, s = PAL[color]
        st = (f"rounded=1;arcSize=3;whiteSpace=wrap;html=1;dashed=1;dashPattern=6 4;fillColor={f};strokeColor={s};"
              f"fillOpacity=45;verticalAlign=top;align=left;spacingLeft=10;spacingTop=2;fontStyle=1;fontSize={font};"
              f"fontColor=#000000;{FONT}" + extra)
        return self._vertex(label, x, y, w, h, st)

    def text(self, x, y, w, h, label, font=11, align="center", bold=False, color="#000000", parent="1", extra=""):
        st = (f"text;html=1;strokeColor=none;fillColor=none;align={align};verticalAlign=middle;whiteSpace=wrap;"
              f"fontSize={font};fontColor={color};{FONT}" + ("fontStyle=1;" if bold else "") + extra)
        return self._vertex(label, x, y, w, h, st, parent)

    def ellipse(self, x, y, w, h, label, color="white", font=12):
        f, s = PAL[color]
        st = f"ellipse;whiteSpace=wrap;html=1;fillColor={f};strokeColor={s};fontSize={font};fontColor=#000000;{FONT}"
        return self._vertex(label, x, y, w, h, st)

    def rhombus(self, x, y, w, h, label, color="white", font=12):
        f, s = PAL[color]
        st = f"rhombus;whiteSpace=wrap;html=1;fillColor={f};strokeColor={s};fontSize={font};fontColor=#000000;{FONT}"
        return self._vertex(label, x, y, w, h, st)

    def store(self, x, y, w, h, label, color="yellow", font=12):
        f, s = PAL[color]
        st = (f"shape=partialRectangle;whiteSpace=wrap;html=1;left=0;right=0;fillColor={f};strokeColor={s};"
              f"fontSize={font};fontColor=#000000;{FONT}")
        return self._vertex(label, x, y, w, h, st)

    def actor(self, x, y, label, font=11):
        st = (f"shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;"
              f"fontSize={font};fontColor=#000000;{FONT}")
        return self._vertex(label, x, y, 30, 60, st)

    def lifeline(self, cx, y, w, h, label, color="gray", font=11, size=44):
        f, s = PAL[color]
        st = (f"shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=0;collapsible=0;"
              f"recursiveResize=0;outlineConnect=0;size={size};fillColor={f};strokeColor={s};fontSize={font};"
              f"fontColor=#000000;{FONT}")
        return self._vertex(label, cx - w / 2, y, w, h, st)

    def activation(self, cx, y, h=22):
        st = "html=1;points=[];perimeter=orthogonalPerimeter;fillColor=#ffffff;strokeColor=#000000;"
        return self._vertex("", cx - 5, y, 10, h, st)

    def table(self, x, y, w, title, rows, color="yellow", font=11, row_h=20):
        """Entity box: a swimlane header with one text row per attribute. Returns (swimlane id, [row ids])."""
        f, s = PAL[color]
        h = 26 + row_h * len(rows)
        st = (f"swimlane;fontStyle=1;childLayout=stackLayout;horizontal=1;startSize=26;horizontalStack=0;"
              f"resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=0;marginBottom=0;html=1;fillColor={f};"
              f"strokeColor={s};fontSize=12;fontColor=#000000;swimlaneFillColor=#ffffff;{FONT}")
        sid = self._vertex(title, x, y, w, h, st)
        ids = []
        for i, r in enumerate(rows):
            rst = (f"text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=6;spacingRight=4;"
                   f"overflow=hidden;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;rotatable=0;html=1;"
                   f"fontSize={font};fontColor=#000000;{FONT}")
            ids.append(self._vertex(r, 0, 26 + row_h * i, w, row_h, rst, parent=sid))
        return sid, ids

    # ─────────────── connectors ───────────────
    def edge(self, src=None, tgt=None, label="", exit=None, entry=None, pts=None, dashed=False, color="#333333",
             start=False, end=True, font=11, straight=False, p1=None, p2=None, arrow="classic", label_bg=True,
             label_pos=None, extra="", end_arrow=None, start_arrow=None):
        st = ("edgeStyle=orthogonalEdgeStyle;" if not straight else "") + "rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"
        ea = end_arrow or (arrow if end else "none")
        sa = start_arrow or (arrow if start else "none")
        st += (f"strokeColor={color};fontSize={font};fontColor=#000000;{FONT}endArrow={ea};endFill=1;startArrow={sa};startFill=1;"
               + ("dashed=1;" if dashed else "") + ("labelBackgroundColor=#ffffff;" if label_bg else ""))
        if exit:
            st += f"exitX={exit[0]};exitY={exit[1]};exitDx=0;exitDy=0;"
        if entry:
            st += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
        st += extra
        cid = self._id()
        attrs = f' source="{src}"' if src else ""
        attrs += f' target="{tgt}"' if tgt else ""
        geo = '<mxGeometry relative="1" as="geometry">'
        if label_pos is not None:
            geo = f'<mxGeometry x="{label_pos}" relative="1" as="geometry">'
        if p1:
            geo += f'<mxPoint x="{p1[0]}" y="{p1[1]}" as="sourcePoint"/>'
        if p2:
            geo += f'<mxPoint x="{p2[0]}" y="{p2[1]}" as="targetPoint"/>'
        if pts:
            geo += '<Array as="points">' + "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in pts) + "</Array>"
        geo += "</mxGeometry>"
        self.cells.append(f'<mxCell id="{cid}" value="{q(label)}" style="{st}" edge="1" parent="1"{attrs}>{geo}</mxCell>')
        return cid

    # ─────────────── output ───────────────
    def xml(self):
        body = "".join(self.cells)
        body = re.sub(r"fontSize=(\d+(?:\.\d+)?)", lambda m: f"fontSize={round(float(m.group(1)) * self.fs)}", body)
        return (f'<mxfile host="app.diagrams.net"><diagram name="{q(self.name)}" id="{q(self.name)}">'
                f'<mxGraphModel dx="{self.w}" dy="{self.h}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
                f'arrows="1" fold="1" page="1" pageScale="1" pageWidth="{self.w}" pageHeight="{self.h}" math="0" shadow="0">'
                f'<root><mxCell id="0"/><mxCell id="1" parent="0"/>{body}</root></mxGraphModel></diagram></mxfile>')

    def save(self, folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{self.name}.drawio").write_text(self.xml(), encoding="utf-8")


def render_all(diagrams, out_dir, scale=3):
    """Render every diagram to PNG using draw.io's own viewer in headless Chrome."""
    import tempfile
    from playwright.sync_api import sync_playwright
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1500, "height": 1300}, device_scale_factor=scale)
        for d in diagrams:
            cfg = {"highlight": "#0000ff", "nav": False, "resize": False, "toolbar": "", "xml": d.xml()}
            doc = ('<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#ffffff">'
                   f'<div id="wrap" style="width:{d.w + 60}px;padding:10px;background:#ffffff">'
                   '<div class="mxgraph" style="max-width:100%;" data-mxgraph="' + html.escape(json.dumps(cfg), quote=True) +
                   '"></div></div><script src="https://viewer.diagrams.net/js/viewer-static.min.js"></script></body></html>')
            f = tmp / f"{d.name}.html"
            f.write_text(doc, encoding="utf-8")
            page.goto(f.as_uri(), wait_until="load", timeout=60000)
            page.wait_for_selector(".mxgraph svg", timeout=30000)
            page.wait_for_timeout(500)
            box = page.locator(".mxgraph").bounding_box()
            page.screenshot(path=str(out_dir / f"{d.name}.png"), clip={
                "x": max(box["x"] - 8, 0), "y": max(box["y"] - 8, 0), "width": box["width"] + 16, "height": box["height"] + 16})
            print("rendered", d.name, f"{box['width']:.0f}x{box['height']:.0f}")
        browser.close()
