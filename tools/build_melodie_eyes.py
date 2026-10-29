"""Generates the inline SVG for the landing mark: the original artwork plus vector eyes.

Usage: python tools/build_melodie_eyes.py /static/art/melodie-mark.webp "240 0 1060 1024"
Coordinates are in the 1536x1024 artwork space; the right eye mirrors the left around x = MIRROR / 2.
"""
import sys, json
MIRROR = 1529
VIEWBOX = sys.argv[2] if len(sys.argv) > 2 else '0 0 1536 1024'
LID_OPEN = 185  # left iris x 612 + right iris x 917
L = dict(
    iris=(612, 553, 49),
    top=[(492, 477), (700, 588)],
    bottom=[(700, 588), (670, 606), (640, 619), (600, 623), (560, 606), (540, 590), (520, 569), (505, 530), (497, 500), (492, 477)],
    glints=[(641, 575, 7.5), (599, 580, 3.2)],
)
def mirror(e):
    m = lambda p: (MIRROR - p[0],) + tuple(p[1:])
    return dict(iris=m(e['iris']), top=[m(p) for p in e['top']], bottom=[m(p) for p in e['bottom']], glints=[m(g) for g in e['glints']])
R = mirror(L)

def smooth(points):
    """Quadratic path through midpoints: a rounded curve following the points."""
    d = f"M{points[0][0]},{points[0][1]}"
    for i in range(1, len(points) - 1):
        (x0, y0), (x1, y1) = points[i], points[i + 1]
        d += f" Q{x0},{y0} {(x0 + x1) / 2:.1f},{(y0 + y1) / 2:.1f}"
    d += f" L{points[-1][0]},{points[-1][1]}"
    return d

def eye(name, e):
    cx, cy, r = e['iris']
    pts = e['top'] + e['bottom'][1:]
    poly = ' '.join(f'{x},{y}' for x, y in pts)
    (x1, y1), (x2, y2) = e['top']
    # lid: the eye's own lower curve, pushed a little lower and wider so a closed lid covers the whole opening
    bottom = e['bottom']                       # inner corner -> around -> outer top corner
    sign = 1 if bottom[0][0] > bottom[-1][0] else -1   # inner corner on the right for the left eye
    curve = [(bottom[0][0] + 10 * sign, bottom[0][1] + 3)] + [(x, y + 6) for x, y in bottom[1:-1]] + [(bottom[-1][0] - 3 * sign, bottom[-1][1] + 2)]
    lash = smooth(curve)
    top_y = min(y for _, y in pts) - 230
    lid_path = lash + f" L{curve[-1][0]},{top_y} L{curve[0][0]},{top_y} Z"
    lid_clip = ' '.join(f'{x},{y}' for x, y in [e['top'][0], e['top'][1]] + curve[::-1][:0] + [(curve[0][0], curve[0][1] + 3)] + [(x, y + 3) for x, y in curve[1:-1]] + [(curve[-1][0], curve[-1][1] + 1)])
    import math
    dxl, dyl = x2 - x1, y2 - y1; ln = math.hypot(dxl, dyl)
    nx, ny = -dyl / ln, dxl / ln            # normal to the brow line
    if ny < 0: nx, ny = -nx, -ny             # pointing down
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    gx1, gy1 = round(mx - nx * 6), round(my - ny * 6)
    gx2, gy2 = round(mx + nx * 92), round(my + ny * 92)
    gl = ''.join((f'<circle cx="{gx-cx}" cy="{gy-cy}" r="{gr+3}" fill="#f9a6f9" opacity="0.45" filter="url(#mel-glow)"/><circle cx="{gx-cx}" cy="{gy-cy}" r="{gr}" fill="#ffd2ff"/>' if gr > 4 else
                  f'<circle cx="{gx-cx}" cy="{gy-cy}" r="{gr+0.8}" fill="#e23cf2" opacity="0.9"/>') for gx, gy, gr in e['glints'])
    return f'''
  <g class="mel-eye" data-eye="{name}" data-cx="{cx}" data-cy="{cy}">
    <clipPath id="mel-clip-{name}"><polygon points="{poly}"/></clipPath>
    <linearGradient id="mel-sclera-{name}" gradientUnits="userSpaceOnUse" x1="{gx1}" y1="{gy1}" x2="{gx2}" y2="{gy2}">
      <stop offset="0" stop-color="#2a1cf2"/><stop offset="0.24" stop-color="#6c12f6"/><stop offset="0.45" stop-color="#d81ef6"/>
      <stop offset="0.62" stop-color="#f790f5"/><stop offset="0.86" stop-color="#fff2ff"/>
    </linearGradient>
    <g clip-path="url(#mel-clip-{name})">
      <polygon points="{poly}" fill="url(#mel-sclera-{name})"/>
      <g class="mel-iris" transform="translate({cx} {cy})">
        <circle r="{r}" fill="url(#mel-iris)"/>
        <ellipse cx="0" cy="{r*0.42:.1f}" rx="{r*0.62:.1f}" ry="{r*0.26:.1f}" fill="#a24cf8" opacity="0.7" filter="url(#mel-soft)"/>
        <circle r="{r*0.5:.1f}" cy="2" fill="#04000f" opacity="0.85"/>
        {gl}
      </g>
      <polyline points="{x1},{y1} {x2},{y2}" stroke="#07002a" stroke-width="16" fill="none" filter="url(#mel-lidblur)" opacity="0.6"/>
    </g>
    <clipPath id="mel-lidclip-{name}"><polygon points="{lid_clip}"/></clipPath>
    <g clip-path="url(#mel-lidclip-{name})">
      <g class="mel-lid" transform="translate(0 -{LID_OPEN})">
        <path d="{lid_path}" fill="url(#mel-lid)"/>
        <path d="{lash}" fill="none" stroke="#c77dff" stroke-width="2.2" stroke-linecap="round" opacity="0.55" transform="translate(0 -3)"/>
        <path d="{lash}" fill="none" stroke="#05001a" stroke-width="4" stroke-linecap="round"/>
      </g>
    </g>
  </g>'''

svg = f'''<svg class="mel-mark" viewBox="{VIEWBOX}" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">
  <defs>
    <linearGradient id="sclera" x1="0" y1="470" x2="0" y2="625" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#3a00d8"/><stop offset="0.22" stop-color="#b000f6"/>
      <stop offset="0.5" stop-color="#f53ef6"/><stop offset="0.8" stop-color="#fab0f6"/><stop offset="1" stop-color="#ffeaff"/>
    </linearGradient>
    <radialGradient id="mel-iris" cx="0.5" cy="0.46" r="0.5">
      <stop offset="0" stop-color="#05001a"/><stop offset="0.55" stop-color="#0b0233"/>
      <stop offset="0.82" stop-color="#2a0a95"/><stop offset="0.95" stop-color="#4a16d0"/><stop offset="1" stop-color="#170456"/>
    </radialGradient>
    <linearGradient id="mel-lid" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#05001a"/><stop offset="0.75" stop-color="#140548"/><stop offset="1" stop-color="#2a0c82"/></linearGradient>
    <filter id="mel-soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>
    <filter id="mel-lidblur" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="5"/></filter>
    <filter id="mel-glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="2"/></filter>
  </defs>
  <image href="{sys.argv[1]}" width="1536" height="1024"/>
  {eye("left", L)}
  {eye("right", R)}
</svg>'''
print(svg)
