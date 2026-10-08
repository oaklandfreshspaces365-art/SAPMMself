#!/usr/bin/env python3
"""Generate a layered Value Stream Map (.vsdx) — no dependencies.

Layers (View > Layer Properties, or double-click the toggle buttons on the page):
  1 Entities & Control   2 Process & Data Boxes   3 Material Flow
  4 Information Flow     5 Timeline               6 Legend & Title   7 Layer Toggles
Edit the DATA section below and re-run:  python3 build_vsm_vsdx.py
"""
import zipfile, math
from xml.sax.saxutils import escape

OUT = "VSM_Current_State_Layered.vsdx"
PW, PH = 17.0, 11.0                      # tabloid landscape, inches

NAVY, MAT, INFO, GREY, LIGHT = "#00305E", "#1F4E79", "#D35400", "#595959", "#EAF1F8"
LAYERS = ["Entities & Control", "Process & Data Boxes", "Material Flow",
          "Information Flow", "Timeline", "Legend & Title", "Layer Toggles"]
L = {n: i for i, n in enumerate(LAYERS)}

# ---------------------------------------------------------------- DATA
CUSTOMER = ("Customer (OEM)", ["18,400 pcs / month", "920 pcs / day", "2 shifts · Takt 59 s"])
SUPPLIER = ("Steel Coil Supplier", ["LT 6 weeks", "MOQ 20 t", "Delivery 2x / week"])
PROCESSES = [  # name, x, data-box lines, CT seconds
    ("Stamping", 2.8,  ["C/T = 1.2 s", "C/O = 45 min", "Uptime = 85 %", "Operators = 1", "Shifts = 2", "EPEI = 2 d"], 1.2),
    ("Welding",  5.2,  ["C/T = 52 s", "C/O = 10 min", "Uptime = 92 %", "Operators = 2", "Shifts = 2"], 52),
    ("Painting", 7.6,  ["C/T = 40 s", "C/O = 30 min", "Uptime = 88 %", "Operators = 1", "Batch = 120"], 40),
    ("Assembly", 10.3, ["C/T = 55 s", "C/O = 0", "Uptime = 97 %", "Operators = 3", "Shifts = 2"], 55),
    ("Packing",  12.7, ["C/T = 30 s", "C/O = 0", "Uptime = 99 %", "Operators = 1", "Shifts = 2"], 30),
]
INVENTORY = [  # x, label, days, kind
    (1.4,  "Coils\n4,600 pcs", 5.0, "tri"),
    (4.0,  "2,300 pcs", 2.5, "tri"),
    (6.4,  "1,400 pcs", 1.5, "tri"),
    (8.95, "920 pcs", 1.0, "sm"),
    (11.5, "460 pcs", 0.5, "tri"),
    (14.1, "FG\n2,760 pcs", 3.0, "tri"),
]
# ---------------------------------------------------------------- shape builder
shapes, _id = [], [0]

def nid():
    _id[0] += 1
    return _id[0]

def C(n, v, u=None, f=None):
    a = f' U="{u}"' if u else ""
    fa = f' F="{escape(f, {chr(34): "&quot;"})}"' if f else ""
    return f'<Cell N="{n}" V="{v}"{a}{fa}/>'

def shape(x, y, w, h, geoms=(), text=None, layer=0, line=GREY, lw=0.75, lp=1,
          fill=None, size=8, bold=False, tcolor="#000000", halign=1, valign=1,
          end_arrow=0, arrow_size=2, rounding=0, txt=None, extra="", name=None, fill_f=None):
    """x,y = bottom-left; geoms = list of (nofill, [rows]) in local coords."""
    sid = nid()
    w, h = max(w, 0.01), max(h, 0.01)
    tx, ty, tw, th = txt if txt else (0, 0, w, h)
    cells = [C("PinX", round(x, 4)), C("PinY", round(y, 4)), C("Width", round(w, 4)), C("Height", round(h, 4)),
             C("LocPinX", 0), C("LocPinY", 0), C("Angle", 0), C("FlipX", 0), C("FlipY", 0),
             C("LineWeight", round(lw / 72, 5), "PT"), C("LineColor", line), C("LinePattern", lp),
             C("Rounding", rounding), C("EndArrow", end_arrow), C("EndArrowSize", arrow_size), C("BeginArrow", 0),
             C("FillForegnd", fill or "#FFFFFF", f=fill_f), C("FillPattern", 1 if fill else 0),
             C("TxtPinX", round(tx + tw / 2, 4)), C("TxtPinY", round(ty + th / 2, 4)),
             C("TxtWidth", round(tw, 4)), C("TxtHeight", round(th, 4)),
             C("TxtLocPinX", round(tw / 2, 4)), C("TxtLocPinY", round(th / 2, 4)), C("TxtAngle", 0),
             C("VerticalAlign", valign), C("LeftMargin", 0.04, "PT"), C("RightMargin", 0.04, "PT"),
             C("TopMargin", 0.03, "PT"), C("BottomMargin", 0.03, "PT"), extra]
    secs = [f'<Section N="Character"><Row IX="0">{C("Size", round(size / 72, 5), "PT")}{C("Color", tcolor)}'
            f'{C("Style", 1 if bold else 0)}</Row></Section>',
            f'<Section N="Paragraph"><Row IX="0">{C("HorzAlign", halign)}</Row></Section>',
            f'<Section N="LayerMem"><Row IX="0">{C("LayerMember", layer)}</Row></Section>']
    for gi, (nofill, rows) in enumerate(geoms):
        r = "".join(rows_xml(rows))
        secs.append(f'<Section N="Geometry" IX="{gi}">{C("NoFill", 1 if nofill else 0)}{C("NoLine", 0)}'
                    f'{C("NoShow", 0)}{C("NoSnap", 0)}{r}</Section>')
    t = f"<Text>{escape(text)}</Text>" if text else ""
    nm = f' NameU="{escape(name)}" Name="{escape(name)}"' if name else ""
    shapes.append(f'<Shape ID="{sid}"{nm} Type="Shape" LineStyle="0" FillStyle="0" TextStyle="0">'
                  f'{"".join(cells)}{"".join(secs)}{t}</Shape>')
    return sid

def rows_xml(rows):
    for i, r in enumerate(rows, 1):
        if r[0] == "E":   # ellipse cx, cy, rx, ry
            _, cx, cy, rx, ry = r
            yield (f'<Row T="Ellipse" IX="{i}">{C("X", cx)}{C("Y", cy)}{C("A", cx + rx)}{C("B", cy)}'
                   f'{C("C", cx)}{C("D", cy + ry)}</Row>')
        else:
            yield f'<Row T="{r[0]}" IX="{i}">{C("X", round(r[1], 4))}{C("Y", round(r[2], 4))}</Row>'

def poly(pts, close=False):
    rows = [("MoveTo",) + pts[0]] + [("LineTo",) + p for p in pts[1:]]
    if close:
        rows.append(("LineTo",) + pts[0])
    return rows

def rect_geo(w, h):
    return [(False, poly([(0, 0), (w, 0), (w, h), (0, h)], True))]

def box(cx, cy, w, h, text, layer, **kw):
    return shape(cx - w / 2, cy - h / 2, w, h, rect_geo(w, h), text, layer, **kw)

def label(cx, cy, text, layer, w=1.6, h=0.3, **kw):
    return shape(cx - w / 2, cy - h / 2, w, h, (), text, layer, **kw)

def path(pts, layer, color, lw, lp=1, arrow=4, asize=2, zig=False, name=None):
    """Polyline arrow in page coords; zig=True puts a lightning jag on the longest segment."""
    if zig:
        i = max(range(len(pts) - 1), key=lambda k: math.dist(pts[k], pts[k + 1]))
        (x1, y1), (x2, y2) = pts[i], pts[i + 1]
        d = math.dist(pts[i], pts[i + 1]); ux, uy = (x2 - x1) / d, (y2 - y1) / d; nx, ny = -uy, ux
        at = lambda t, o: (x1 + ux * (d / 2 + t) + nx * o, y1 + uy * (d / 2 + t) + ny * o)
        jag = [at(-0.1, 0), at(0.05, 0.14), at(-0.05, -0.14), at(0.1, 0)]
        pts = pts[:i + 1] + jag + pts[i + 1:]
    mx, my = min(p[0] for p in pts), min(p[1] for p in pts)
    w, h = max(p[0] for p in pts) - mx, max(p[1] for p in pts) - my
    loc = [(p[0] - mx, p[1] - my) for p in pts]
    return shape(mx, my, w, h, [(True, poly(loc))], None, layer, line=color, lw=lw, lp=lp,
                 end_arrow=arrow, arrow_size=asize, name=name)

def push_arrow(x1, x2, y, layer=L["Material Flow"]):
    """Striped VSM push arrow = thick line + white dashed overlay."""
    path([(x1, y), (x2, y)], layer, MAT, 7, arrow=4, asize=3, name="Push Arrow")
    path([(x1 + 0.05, y), (x2 - 0.2, y)], layer, "#FFFFFF", 3, lp=2, arrow=0, name="Push Arrow Stripe")

def factory(cx, cy, title, layer):
    w, h = 1.5, 0.85
    pts = [(0, 0), (w, 0), (w, 0.5), (1.125, 0.75), (1.125, 0.5), (0.75, 0.75), (0.75, 0.5),
           (0.375, 0.75), (0.375, 0.5), (0, 0.75)]
    shape(cx - w / 2, cy - h / 2, w, h, [(False, poly(pts, True))], title, layer, line=NAVY, lw=1.25,
          fill=LIGHT, bold=True, size=8, txt=(0, 0, w, 0.5), name="Factory")

def truck(cx, cy, text, layer):
    w, h = 1.1, 0.6
    g = [(False, poly([(0, 0.12), (0.7, 0.12), (0.7, 0.6), (0, 0.6)], True)),
         (False, poly([(0.72, 0.12), (1.1, 0.12), (1.1, 0.36), (0.96, 0.5), (0.72, 0.5)], True)),
         (False, [("E", 0.2, 0.1, 0.09, 0.09)]), (False, [("E", 0.88, 0.1, 0.09, 0.09)])]
    shape(cx - w / 2, cy - h / 2, w, h, g, text, layer, line=MAT, lw=1, fill="#FFFFFF", size=7,
          bold=True, txt=(0, 0.12, 0.7, 0.48), name="Truck")

def triangle(cx, cy, layer):
    w, h = 0.46, 0.4
    shape(cx - w / 2, cy - h / 2, w, h, [(False, poly([(0, 0), (w, 0), (w / 2, h)], True))], "I", layer,
          line=MAT, lw=1.25, fill="#FFF2CC", bold=True, size=9, txt=(0, 0, w, h * 0.6), name="Inventory")

def supermarket(cx, cy, layer):
    w, h = 0.5, 0.55
    g = [(True, poly([(0, h), (w, h), (w, 0), (0, 0)]))] + \
        [(True, poly([(0, h * k / 3), (w, h * k / 3)])) for k in (1, 2)]
    shape(cx - w / 2, cy - h / 2, w, h, g, None, layer, line=MAT, lw=1.5, name="Supermarket")

def glasses(cx, cy, layer):
    w, h = 0.5, 0.2
    g = [(False, [("E", 0.12, 0.1, 0.1, 0.08)]), (False, [("E", 0.38, 0.1, 0.1, 0.08)]),
         (True, poly([(0.22, 0.12), (0.28, 0.12)]))]
    shape(cx - w / 2, cy - h / 2, w, h, g, None, layer, line=INFO, lw=1, fill="#FFFFFF", name="Go See")

# ---------------------------------------------------------------- DRAW
E, P, M, I, T, G = (L["Entities & Control"], L["Process & Data Boxes"], L["Material Flow"],
                    L["Information Flow"], L["Timeline"], L["Legend & Title"])

label(PW / 2, 10.65, "MFG – [Plant] Current State Value Stream Map", G, w=9, h=0.4, size=16, bold=True, tcolor=NAVY)
label(PW / 2, 10.35, "Product family: [Part / Family]  ·  Date: 10/08/2026  ·  Mapped by: Logistics Planning",
      G, w=9, h=0.25, size=8, tcolor=GREY)

# Entities
factory(1.4, 9.5, SUPPLIER[0], E)
box(1.4, 8.45, 1.5, 0.75, "\n".join(SUPPLIER[1]), E, line=NAVY, size=7, halign=0, valign=0)
factory(15.5, 9.5, CUSTOMER[0], E)
box(15.5, 8.45, 1.5, 0.75, "\n".join(CUSTOMER[1]), E, line=NAVY, size=7, halign=0, valign=0)
box(8.5, 9.45, 3.4, 1.0, "Logistics Planning / Production Control\nSAP ERP – MRP · WM/EWM", E,
    line=NAVY, lw=1.5, fill=LIGHT, size=9, bold=True)

# Processes + data boxes
for name, x, data, ct in PROCESSES:
    box(x, 5.6, 1.5, 0.75, name, P, line=NAVY, lw=1.5, fill=NAVY, tcolor="#FFFFFF", size=10, bold=True)
    box(x, 4.65, 1.5, 1.05, "\n".join(data), P, line=NAVY, size=7.5, halign=0, valign=0)

# Material flow: inventory, push arrows, trucks, shipments, supermarket
for x, txt, days, kind in INVENTORY:
    if kind == "sm":
        supermarket(x, 5.75, M)
        label(x, 6.25, f"Supermarket\n{txt} · {days} d", M, w=1.1, h=0.35, size=7)
    else:
        triangle(x, 6.0, M)
        lx, ly = (x - 0.85, 6.0) if x < 2 else (x, 6.45)
        label(lx, ly, f"{txt}\n{days} d", M, w=1.0, h=0.35, size=7)
xs = [p[1] for p in PROCESSES]
push_arrow(1.65, 2.0, 5.45)
for a, b in zip(xs, xs[1:]):
    push_arrow(a + 0.8, b - 0.8, 5.45)
push_arrow(xs[-1] + 0.8, 13.85, 5.45)
truck(1.4, 7.05, "2x / week", M)
truck(15.5, 7.05, "Daily", M)
path([(0.65, 9.5), (0.35, 9.5), (0.35, 7.05), (0.82, 7.05)], M, MAT, 4.5, asize=3, name="Shipment Arrow")
path([(1.4, 6.73), (1.4, 6.25)], M, MAT, 4.5, asize=3, name="Shipment Arrow")
path([(14.35, 6.0), (15.5, 6.0), (15.5, 6.72)], M, MAT, 4.5, asize=3, name="Shipment Arrow")
path([(16.06, 7.05), (16.6, 7.05), (16.6, 9.5), (16.27, 9.5)], M, MAT, 4.5, asize=3, name="Shipment Arrow")

# Information flow
path([(14.73, 9.75), (10.22, 9.75)], I, INFO, 1.25, zig=True, name="Electronic Info")
label(12.45, 10.05, "EDI forecast 90/60/30 d · daily call-offs", I, w=3.4, size=7, tcolor=INFO)
path([(6.78, 9.75), (2.17, 9.75)], I, INFO, 1.25, zig=True, name="Electronic Info")
label(4.45, 10.05, "6-week forecast (EDI)", I, w=2.6, size=7, tcolor=INFO)
path([(6.78, 9.15), (2.17, 9.15)], I, INFO, 1, name="Manual Info")
label(4.45, 8.95, "Weekly call-off (e-mail)", I, w=2.6, size=7, tcolor=INFO)
path([(8.5, 8.95), (8.5, 7.6)], I, INFO, 1, arrow=0, name="Manual Info")
path([(xs[0], 7.6), (xs[-1], 7.6)], I, INFO, 1, arrow=0, name="Schedule Bus")
for x in xs:
    path([(x, 7.6), (x, 6.0)], I, INFO, 1, name="Manual Info")
label(5.0, 7.78, "Weekly production schedule", I, w=2.4, size=7, tcolor=INFO)
path([(10.2, 9.1), (14.3, 9.1), (14.3, 7.05), (14.93, 7.05)], I, INFO, 1, name="Manual Info")
label(12.3, 9.27, "Daily ship schedule", I, w=2.0, size=7, tcolor=INFO)
path([(9.75, 5.98), (9.75, 6.8), (8.2, 6.8), (8.2, 5.98)], I, INFO, 1, lp=2, name="Kanban Loop")
box(8.95, 6.8, 0.55, 0.22, "Kanban", I, line=INFO, fill="#FDEBD0", size=6.5, bold=True)
glasses(11.4, 6.95, I)
label(11.4, 6.7, "Go see / expediting", I, w=1.4, h=0.22, size=6.5, tcolor=INFO)

# Timeline ladder
hi, lo = 3.25, 2.85
inv_x = [v[0] for v in INVENTORY]
edges = [0.7] + [e for x in xs for e in (x - 0.75, x + 0.75)] + [14.8]
pts = []
for k in range(len(inv_x)):
    pts += [(edges[2 * k], hi), (edges[2 * k + 1], hi)]
    if k < len(xs):
        pts += [(edges[2 * k + 1], lo), (edges[2 * k + 2], lo)]
path(pts, T, NAVY, 1.5, arrow=0, name="Timeline")
for x, _, d, _ in INVENTORY:
    label(x, hi + 0.15, f"{d} d", T, w=0.9, h=0.22, size=8, bold=True)
for _, x, _, ct in PROCESSES:
    label(x, lo - 0.15, f"{ct:g} s", T, w=0.9, h=0.22, size=8, bold=True)
lt, va = sum(v[2] for v in INVENTORY), sum(p[3] for p in PROCESSES)
box(16.0, 3.05, 1.7, 0.9, f"Production lead time\n= {lt:g} days\nProcessing time\n= {va:g} s", T,
    line=NAVY, lw=1.5, fill=LIGHT, size=8, bold=True)

# Legend
label(1.6, 2.2, "LEGEND", G, w=2.0, h=0.25, size=9, bold=True, tcolor=NAVY, halign=0)
leg = [("Push (material)", "push"), ("Shipment", "ship"), ("Manual info", "man"),
       ("Electronic info", "elec"), ("Kanban / pull", "kan")]
for k, (txt, kind) in enumerate(leg):
    y = 1.9 - k * 0.3
    if kind == "push": push_arrow(0.7, 1.5, y, G)
    if kind == "ship": path([(0.7, y), (1.5, y)], G, MAT, 4.5, asize=3)
    if kind == "man": path([(0.7, y), (1.5, y)], G, INFO, 1)
    if kind == "elec": path([(0.7, y), (1.5, y)], G, INFO, 1.25, zig=True)
    if kind == "kan": path([(0.7, y), (1.5, y)], G, INFO, 1, lp=2)
    label(2.45, y, txt, G, w=1.6, h=0.25, size=7.5, halign=0)
for k, (txt, fn) in enumerate([("Inventory", triangle), ("Supermarket", supermarket), ("Truck shipment", None)]):
    y = 1.85 - k * 0.6
    (fn or (lambda cx, cy, l: truck(cx, cy, "", l)))(3.9, y, G)
    label(5.2, y, txt, G, w=1.3, h=0.25, size=7.5, halign=0)

# Layer toggle buttons (double-click) — row index in Layers section is 1-based
label(9.6, 2.15, "LAYERS – double-click to toggle  (or View ▸ Layer Properties)", L["Layer Toggles"],
      w=5.2, h=0.25, size=8, bold=True, tcolor=NAVY, halign=0)
for k, ln in enumerate(["Material Flow", "Information Flow", "Process & Data Boxes", "Timeline", "Entities & Control"]):
    i = L[ln] + 1
    cx, cy = 7.95 + (k % 3) * 1.85, 1.75 - (k // 3) * 0.45
    ev = f"SETF(GetRef(ThePage!Layers.Visible[{i}]),NOT(ThePage!Layers.Visible[{i}]))"
    fl = f"IF(ThePage!Layers.Visible[{i}],RGB(0,48,94),RGB(191,191,191))"
    box(cx, cy, 1.7, 0.35, ln, L["Layer Toggles"], line=NAVY, fill=NAVY, tcolor="#FFFFFF", size=8, bold=True,
        rounding=0.06, extra=C("EventDblClick", 0, f=ev), fill_f=fl, name=f"Toggle {ln}")

# ---------------------------------------------------------------- PACKAGE
NS = 'xmlns="http://schemas.microsoft.com/office/visio/2012/main" ' \
     'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xml:space="preserve"'
HDR = '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'

layer_rows = "".join(
    f'<Row IX="{i}">{C("Name", escape(n))}{C("NameUniv", escape(n))}{C("Color", 255)}{C("Status", 0)}'
    f'{C("Visible", 1)}{C("Print", 0 if n == "Layer Toggles" else 1)}{C("Active", 0)}{C("Lock", 0)}'
    f'{C("Snap", 1)}{C("Glue", 1)}{C("ColorTrans", 0)}</Row>' for i, n in enumerate(LAYERS))

style0 = "".join([C("EnableLineProps", 1), C("EnableFillProps", 1), C("EnableTextProps", 1),
    C("LineWeight", 0.01041666666666667), C("LineColor", "#000000"), C("LinePattern", 1), C("Rounding", 0),
    C("EndArrowSize", 2), C("BeginArrow", 0), C("EndArrow", 0), C("LineCap", 0), C("BeginArrowSize", 2),
    C("LineColorTrans", 0), C("CompoundType", 0), C("FillForegnd", "#FFFFFF"), C("FillBkgnd", "#000000"),
    C("FillPattern", 1), C("ShdwForegnd", "#000000"), C("ShdwPattern", 0), C("FillForegndTrans", 0),
    C("FillBkgndTrans", 0), C("ShdwForegndTrans", 0), C("ShapeShdwType", 0), C("ShapeShdwOffsetX", 0),
    C("ShapeShdwOffsetY", 0), C("ShapeShdwObliqueAngle", 0), C("ShapeShdwScaleFactor", 1), C("ShapeShdwBlur", 0),
    C("ShapeShdwShow", 0), C("LeftMargin", 0), C("RightMargin", 0), C("TopMargin", 0), C("BottomMargin", 0),
    C("VerticalAlign", 1), C("TextBkgnd", 0), C("DefaultTabStop", 0.5), C("TextDirection", 0),
    C("TextBkgndTrans", 0), C("LockTextEdit", 0), C("LockVtxEdit", 0), C("LockCalcWH", 0)]) + \
    '<Section N="Character"><Row IX="0">' + C("Font", "Calibri") + C("Color", "#000000") + C("Style", 0) + \
    C("Case", 0) + C("Pos", 0) + C("FontScale", 1) + C("Size", 0.1666666666666667) + C("DblUnderline", 0) + \
    C("Overline", 0) + C("Strikethru", 0) + C("DoubleStrikethrough", 0) + C("Letterspace", 0) + \
    C("ColorTrans", 0) + C("AsianFont", 0) + C("ComplexScriptFont", 0) + C("ComplexScriptSize", -1) + \
    C("LangID", "en-US") + '</Row></Section>' + \
    '<Section N="Paragraph"><Row IX="0">' + C("IndFirst", 0) + C("IndLeft", 0) + C("IndRight", 0) + \
    C("SpLine", -1.2) + C("SpBefore", 0) + C("SpAfter", 0) + C("HorzAlign", 1) + C("Bullet", 0) + \
    C("BulletStr", "") + C("BulletFont", 0) + C("BulletFontSize", -1) + C("TextPosAfterBullet", 0) + \
    C("Flags", 0) + '</Row></Section>'

files = {
"[Content_Types].xml": HDR + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
  '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
  '<Default Extension="xml" ContentType="application/xml"/>'
  '<Override PartName="/visio/document.xml" ContentType="application/vnd.ms-visio.drawing.main+xml"/>'
  '<Override PartName="/visio/pages/pages.xml" ContentType="application/vnd.ms-visio.pages+xml"/>'
  '<Override PartName="/visio/pages/page1.xml" ContentType="application/vnd.ms-visio.page+xml"/>'
  '<Override PartName="/visio/windows.xml" ContentType="application/vnd.ms-visio.windows+xml"/>'
  '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
  '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
  '</Types>',
"_rels/.rels": HDR + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
  '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/document" Target="visio/document.xml"/>'
  '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
  '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
  '</Relationships>',
"docProps/core.xml": HDR + '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
  'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
  'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>Current State VSM</dc:title>'
  '<dc:creator>Logistics Planning</dc:creator></cp:coreProperties>',
"docProps/app.xml": HDR + '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
  '<Application>Microsoft Visio</Application><Template></Template></Properties>',
"visio/_rels/document.xml.rels": HDR + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
  '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/pages" Target="pages/pages.xml"/>'
  '<Relationship Id="rId2" Type="http://schemas.microsoft.com/visio/2010/relationships/windows" Target="windows.xml"/>'
  '</Relationships>',
"visio/document.xml": HDR + f'<VisioDocument {NS}>'
  '<DocumentSettings TopPage="0" DefaultTextStyle="0" DefaultLineStyle="0" DefaultFillStyle="0" DefaultGuideStyle="0">'
  '<GlueSettings>9</GlueSettings><SnapSettings>65847</SnapSettings><SnapExtensions>34</SnapExtensions><SnapAngles/>'
  '<DynamicGridEnabled>1</DynamicGridEnabled><ProtectStyles>0</ProtectStyles><ProtectShapes>0</ProtectShapes>'
  '<ProtectMasters>0</ProtectMasters><ProtectBkgnds>0</ProtectBkgnds></DocumentSettings>'
  '<Colors><ColorEntry IX="0" RGB="#000000"/><ColorEntry IX="1" RGB="#FFFFFF"/></Colors>'
  '<FaceNames><FaceName NameU="Calibri" UnicodeRanges="-536859905 -1073732485 9 0" CharSets="536871423 0" '
  'Panos="2 15 5 2 2 2 4 3 2 4" Flags="325"/></FaceNames>'
  f'<StyleSheets><StyleSheet ID="0" NameU="No Style" IsCustomNameU="1" Name="No Style" IsCustomName="1">{style0}</StyleSheet></StyleSheets>'
  '<DocumentSheet NameU="TheDoc" IsCustomNameU="1" Name="TheDoc" IsCustomName="1" LineStyle="0" FillStyle="0" TextStyle="0">'
  + C("OutputFormat", 0) + C("LockPreview", 0) + C("AddMarkup", 0) + C("ViewMarkup", 0) + C("DocLockReplace", 0) +
  C("NoCoauth", 0) + C("DocLockDuplicatePage", 0) + C("PreviewQuality", 0) + C("PreviewScope", 0) +
  C("DocLangID", "en-US") + '</DocumentSheet></VisioDocument>',
"visio/windows.xml": HDR + f'<Windows ClientWidth="1600" ClientHeight="900" {NS}>'
  f'<Window ID="0" WindowType="Drawing" WindowState="1073741824" WindowLeft="-8" WindowTop="-31" WindowWidth="1616" '
  f'WindowHeight="939" ContainerType="Page" Page="0" ViewScale="-1" ViewCenterX="{PW/2}" ViewCenterY="{PH/2}">'
  '<ShowRulers>1</ShowRulers><ShowGrid>0</ShowGrid><ShowPageBreaks>0</ShowPageBreaks><ShowGuides>1</ShowGuides>'
  '<ShowConnectionPoints>1</ShowConnectionPoints><GlueSettings>9</GlueSettings><SnapSettings>65847</SnapSettings>'
  '<SnapExtensions>34</SnapExtensions><SnapAngles/><DynamicGridEnabled>1</DynamicGridEnabled>'
  '<TabSplitterPos>0.5</TabSplitterPos></Window></Windows>',
"visio/pages/_rels/pages.xml.rels": HDR + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
  '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/page" Target="page1.xml"/></Relationships>',
"visio/pages/pages.xml": HDR + f'<Pages {NS}><Page ID="0" NameU="Current State VSM" Name="Current State VSM" '
  f'ViewScale="-1" ViewCenterX="{PW/2}" ViewCenterY="{PH/2}"><PageSheet LineStyle="0" FillStyle="0" TextStyle="0">'
  + C("PageWidth", PW, "IN") + C("PageHeight", PH, "IN") + C("ShdwOffsetX", 0.125) + C("ShdwOffsetY", -0.125) +
  C("PageScale", 1, "IN") + C("DrawingScale", 1, "IN") + C("DrawingSizeType", 0) + C("DrawingScaleType", 0) +
  C("InhibitSnap", 0) + C("PageLockReplace", 0, "BOOL") + C("PageLockDuplicate", 0, "BOOL") +
  C("UIVisibility", 0) + C("ShdwType", 0) + C("ShdwObliqueAngle", 0) + C("ShdwScaleFactor", 1) +
  C("DrawingResizeType", 1) + C("PageShapeSplit", 1) + C("PrintPageOrientation", 2) +
  f'<Section N="Layer">{layer_rows}</Section></PageSheet><Rel r:id="rId1"/></Page></Pages>',
"visio/pages/page1.xml": HDR + f'<PageContents {NS}><Shapes>' + "".join(shapes) +
  '</Shapes></PageContents>',
}

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for name in ["[Content_Types].xml"] + [n for n in files if n != "[Content_Types].xml"]:
        z.writestr(name, files[name])
print(f"wrote {OUT}: {len(shapes)} shapes, {len(LAYERS)} layers")
