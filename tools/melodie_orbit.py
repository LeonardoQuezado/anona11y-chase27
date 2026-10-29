"""Vector version of Melodie's orbit (dashed arc with beads, two four-point stars, violet crescent).

Coordinates are in the 1536x1024 artwork space, measured from src/static/art/melodie-mark.webp.
The orbit turns around the centre of the main ring, ORBIT_CENTER.
"""
import math

ORBIT_CENTER = (765, 492)
ARC_C, ARC_R = (707, 496), 382          # dashed arc
BEADS = [(508.2, 176.7, 21.5), (417.5, 236.6, 15.5), (323.1, 441.3, 20), (327.1, 584.0, 22), (401.5, 721.1, 18)]  # measured (x, y, r)
CRESCENT = "M1221 456 A396 396 0 0 1 864 889 A438 438 0 0 0 1221 456 Z"


def _pt(deg, c=ARC_C, r=ARC_R):
    a = math.radians(deg)
    return c[0] + r * math.cos(a), c[1] + r * math.sin(a)


def _arc(a0, a1, r=ARC_R):
    (x0, y0), (x1, y1) = _pt(a0, r=r), _pt(a1, r=r)
    large = 1 if abs(a1 - a0) > 180 else 0
    sweep = 1 if a1 > a0 else 0
    return f"M{x0:.1f} {y0:.1f} A{r} {r} 0 {large} {sweep} {x1:.1f} {y1:.1f}"


def _star(cx, cy, hx, h_up, h_down, k=0.16):
    return (f"M{cx} {cy - h_up} Q{cx + hx * k} {cy - h_up * k} {cx + hx} {cy} "
            f"Q{cx + hx * k} {cy + h_down * k} {cx} {cy + h_down} "
            f"Q{cx - hx * k} {cy + h_down * k} {cx - hx} {cy} "
            f"Q{cx - hx * k} {cy - h_up * k} {cx} {cy - h_up} Z")


# each bead drifts back and forth along the dashed arc (rotation around ARC_C keeps it on the arc)
BEAD_DRIFT = [(5, 9.0, 0.0), (7, 11.5, -3.1), (4, 8.2, -5.4), (6, 12.7, -1.7), (5, 10.3, -7.2)]  # (± degrees, period s, phase s)


def orbit_svg(p="orb", css_class="mel-orbit", reveal=False, game_star=False):
    """Return <defs> and <g> markup; p prefixes every id. reveal=True adds a sweep mask for an entrance animation."""
    def bead(i, x, y, r):
        amp, dur, phase = BEAD_DRIFT[i]
        cx, cy = ARC_C
        anim = (f'<animateTransform attributeName="transform" type="rotate" dur="{dur}s" begin="{phase}s" repeatCount="indefinite" '
                f'values="{-amp} {cx} {cy};{amp} {cx} {cy};{-amp} {cx} {cy}" keyTimes="0;0.5;1" calcMode="spline" '
                f'keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>')
        return f'<g class="orb-bead">{anim}<circle cx="{x}" cy="{y}" r="{r}" fill="url(#{p}-bead)"/></g>'
    beads = ''.join(bead(i, x, y, r) for i, (x, y, r) in enumerate(BEADS))
    star1, star2 = _star(766, 90, 64, 66, 72), _star(767, 892, 56, 62, 60)

    def stars_markup(with_waves):
        waves = ''
        if with_waves:
            # pixelated purple ripples glowing in the big star's centre (CSS animates them outwards)
            cells = []
            for gy in range(-48, 49, 8):
                for gx in range(-48, 49, 8):
                    d = (gx * gx + gy * gy) ** 0.5
                    if d > 50:
                        continue
                    col = ('#f0abfc', '#c084fc', '#8b5cf6', '#6d28d9')[int(d // 13) % 4]
                    cells.append(f'<rect x="{766 + gx - 3.5}" y="{90 + gy - 3.5}" width="7" height="7" fill="{col}" style="--d:{d / 50:.2f}"/>')
            waves = (f'<clipPath id="{p}-star1-clip"><path d="{star1}"/></clipPath>'
                     f'<g class="orb-star-waves" clip-path="url(#{p}-star1-clip)">{"".join(cells)}</g>')
        return (f'<g class="orb-star orb-star-1"><path d="{star1}" fill="url(#{p}-star)"/>{waves}</g>'
                f'<g class="orb-star orb-star-2"><path d="{star2}" fill="url(#{p}-star)"/></g>')
    # solid stroke from the top star to the first bead, then dashes down to the bottom star
    solid = _arc(-97, -122)
    dashed = _arc(-122, -250)      # through 180° (left side) down to ≈110°
    inner = _arc(-127, -153, r=362)  # short second dashed arc just inside, near the left wing tip
    ocx, ocy = ORBIT_CENTER
    mask = (f'<mask id="{p}-sweep" maskUnits="userSpaceOnUse" x="0" y="0" width="1536" height="1024">'
            f'<circle class="orb-sweep" cx="{ocx}" cy="{ocy}" r="250" fill="none" stroke="#fff" stroke-width="520" '
            f'pathLength="100" stroke-dasharray="100 100" transform="rotate(-90 {ocx} {ocy})"/></mask>') if reveal else ''
    mask_attr = f' mask="url(#{p}-sweep)"' if reveal else ''
    defs = f'''<defs>
    <linearGradient id="{p}-arc" gradientUnits="userSpaceOnUse" x1="0" y1="100" x2="0" y2="880">
      <stop offset="0" stop-color="#e3459b"/><stop offset="0.6" stop-color="#d62f95"/><stop offset="1" stop-color="#9b1eb4"/>
    </linearGradient>
    <radialGradient id="{p}-bead" cx="0.38" cy="0.32" r="0.75">
      <stop offset="0" stop-color="#ffb3dc"/><stop offset="0.35" stop-color="#f0479e"/><stop offset="1" stop-color="#b8136f"/>
    </radialGradient>
    <linearGradient id="{p}-star" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f25bb4"/><stop offset="1" stop-color="#c026d3"/>
    </linearGradient>
    <linearGradient id="{p}-cres" gradientUnits="userSpaceOnUse" x1="1221" y1="456" x2="864" y2="889">
      <stop offset="0" stop-color="#8b2cf5"/><stop offset="0.6" stop-color="#6a14ec"/><stop offset="1" stop-color="#5310d8"/>
    </linearGradient>
    <filter id="{p}-glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="7"/></filter>
    {mask}
  </defs>'''
    def shapes_markup(with_waves):
        return f'''<path d="{solid}" fill="none" stroke="url(#{p}-arc)" stroke-width="4.5" stroke-linecap="round"/>
      <path d="{dashed}" fill="none" stroke="url(#{p}-arc)" stroke-width="4.5" stroke-linecap="round" stroke-dasharray="30 17"/>
      <path d="{inner}" fill="none" stroke="url(#{p}-arc)" stroke-width="4" stroke-linecap="round" stroke-dasharray="28 16"/>
      <path d="{CRESCENT}" fill="url(#{p}-cres)"/>
      {stars_markup(with_waves)}
      {beads}'''
    g = f'''<g class="{css_class}"{mask_attr}>
    <g filter="url(#{p}-glow)" opacity="0.75">{shapes_markup(False)}</g>
    <g>{shapes_markup(game_star)}</g>
  </g>'''
    return defs, g


def orbit_standalone(viewbox, p="orb", css_class="mel-orbit", reveal=False, game_star=False):
    """A self-contained decorative <svg> with only the orbit, for layering under the artwork or a photo."""
    defs, g = orbit_svg(p, "", reveal, game_star)
    return (f'<svg class="{css_class}" viewBox="{viewbox}" aria-hidden="true" focusable="false">'
            f'{defs}{g.replace(chr(60) + "g class=" + chr(34) + chr(34), chr(60) + "g", 1)}</svg>')


if __name__ == "__main__":
    d, g = orbit_svg()
    print(d); print(g)
