#!/usr/bin/env python3
"""KiCad PCB (.kicad_pcb) text-level manipulation toolkit.

Battle-tested during a full NE555+CD4017 LED-chaser build (0 shorts / 0 unconnected
after 7 iterations). All functions operate on the s-expression text directly —
no pcbnew API, no GUI, works headless via kicad-cli validation.

Usage:
    from pcb_tools import emit_segment, emit_via, pad_pos, extract_pads, \\
        find_and_remove_segment, insert_segments, check_parens
"""
import math
import re
import uuid


def uid() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────
# Emitters — generate .kicad_pcb track/via text blocks
# ─────────────────────────────────────────────────────────────

def emit_segment(x1, y1, x2, y2, net_code, layer="B.Cu", width=0.6) -> str:
    """Emit a track segment block. net_code is the integer net id
    declared in the board's (net N "name") list."""
    return (f'\t(segment\n\t\t(start {x1:.4f} {y1:.4f})\n'
            f'\t\t(end {x2:.4f} {y2:.4f})\n'
            f'\t\t(width {width})\n\t\t(layer "{layer}")\n'
            f'\t\t(net {net_code})\n\t\t(uuid "{uid()}")\n\t)')


def emit_via(x, y, net_code, size=1.0, drill=0.6) -> str:
    return (f'\t(via\n\t\t(at {x:.4f} {y:.4f})\n\t\t(size {size})\n'
            f'\t\t(drill {drill})\n\t\t(layers "F.Cu" "B.Cu")\n'
            f'\t\t(net {net_code})\n\t\t(uuid "{uid()}")\n\t)')


# ─────────────────────────────────────────────────────────────
# Pad geometry — rotation-aware absolute positions
# ─────────────────────────────────────────────────────────────

def pad_pos(fp_x, fp_y, fp_rot, dx, dy):
    """Absolute pad position for a footprint at (fp_x, fp_y) rotated fp_rot deg,
    where (dx, dy) is the pad offset in the footprint's local frame.
    KiCad Y axis points DOWN; rotation is counterclockwise in viewer,
    so the transform uses standard rotation with y-down convention:
        x' = x + dx*cos(r) + dy*sin(r)
        y' = y - dx*sin(r) + dy*cos(r)
    For the common 0/90/180/270 cases use exact branches for speed.
    """
    if fp_rot == 0:
        return (fp_x + dx, fp_y + dy)
    if fp_rot == 180:
        return (fp_x - dx, fp_y - dy)
    if fp_rot == 90:
        return (fp_x + dy, fp_y - dx)
    if fp_rot == 270:
        return (fp_x - dy, fp_y + dx)
    r = math.radians(fp_rot)
    return (fp_x + dx * math.cos(r) + dy * math.sin(r),
            fp_y - dx * math.sin(r) + dy * math.cos(r))


def extract_pads(text, ref):
    """Extract absolute pad positions + net names for one footprint reference
    from a .kicad_pcb text. Returns {pinnum: (abs_x, abs_y, net_name)}.

    CRITICAL: always derive pad coords with this (or equivalent) instead of
    hand-calculating — a wrong C1/C2 pin assumption cost one full rebuild cycle.
    """
    ref_pat = f'(property "Reference" "{ref}"'
    idx = text.find(ref_pat)
    if idx < 0:
        return {}
    fp_start = text.rfind('(footprint', 0, idx)
    if fp_start < 0:
        return {}
    depth, end = 0, fp_start
    for i in range(fp_start, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    block = text[fp_start:end]

    at_m = re.search(r'\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)', block)
    if not at_m:
        return {}
    fp_x, fp_y = float(at_m.group(1)), float(at_m.group(2))
    fp_rot = float(at_m.group(3)) if at_m.group(3) else 0.0

    pads = {}
    for m in re.finditer(
            r'\(pad\s+"(\w+)"\s+\w+\s+\w+\s+\(at\s+([\d.-]+)\s+([\d.-]+)', block):
        pin = m.group(1)
        dx, dy = float(m.group(2)), float(m.group(3))
        rest = block[m.start():m.start() + 500]
        net_m = re.search(r'\(net\s+\d+\s+"([^"]+)"\)', rest)
        net_name = net_m.group(1) if net_m else ''
        ax, ay = pad_pos(fp_x, fp_y, fp_rot, dx, dy)
        pads[pin] = (round(ax, 2), round(ay, 2), net_name)
    return pads


# ─────────────────────────────────────────────────────────────
# Track editing — surgical add/remove on the text level
# ─────────────────────────────────────────────────────────────

def find_and_remove_segment(text, x1, y1, x2, y2, net_code):
    """Remove one segment matching (start,end) in either direction and net id.
    Returns (new_text, removed_bool). Direction-agnostic matching matters —
    the generator may have emitted either endpoint order."""
    for sx, sy, ex, ey in [(x1, y1, x2, y2), (x2, y2, x1, y1)]:
        pat = re.compile(
            r'\t\(segment\s+\(start\s+' + f'{sx:.4f}' + r'\s+' + f'{sy:.4f}' + r'\)'
            r'[\s\S]*?\(end\s+' + f'{ex:.4f}' + r'\s+' + f'{ey:.4f}' + r'\)'
            r'[\s\S]*?\(net\s+' + str(net_code) + r'\)[\s\S]*?\n\t\)\n',
            re.MULTILINE)
        m = pat.search(text)
        if m:
            return text[:m.start()] + text[m.end():], True
    return text, False


def insert_segments(text, blocks):
    """Insert emitted segment/via blocks into the board text, anchored right
    BEFORE the top-level trailing (embedded_fonts ...) declaration — a stable
    top-level anchor in KiCad 9/10 board files."""
    lines = []
    for b in blocks:
        if isinstance(b, str):
            lines.append(b)
    blob = '\n' + '\n'.join(lines) + '\n'
    ip = text.rfind('(embedded_fonts')
    if ip > 0:
        return text[:ip] + blob + text[ip:]
    # Fallback: before the final closing paren of the file
    stripped = text.rstrip()
    if stripped.endswith(')'):
        return stripped[:-1] + blob + ')\n'
    raise ValueError('no insertion anchor found (expected embedded_fonts or file end)')


def check_parens(text):
    """Return (open_count, close_count, balance). Balance must be 0 before
    running kicad-cli; a failed surgical edit usually shows up here first."""
    o, c = text.count('('), text.count(')')
    return o, c, o - c


def strip_all_tracks(text):
    """Remove ALL segments and vias (keep viasonmask etc.). Use to reset to a
    layout-only board for a clean full re-route — the single most effective
    recovery move when patch iterations spiral (14→11→5→3→... stuck loops)."""
    text = re.sub(r'\t\(segment\s+\(start[\s\S]*?\(uuid[^)]*\)\s*\)\s*\n?', '', text)
    text = re.sub(r'\t\(via\s+\(at[\s\S]*?\(uuid[^)]*\)\s*\)\s*\n?', '', text)
    return text


def net_stats(text):
    """Return {'declared': {id: name}, 'refs': set(int)} — find segments/vias
    referencing undeclared nets (a classic silent board-load failure)."""
    declared = {int(n): name for n, name in
                re.findall(r'^\s*\(net\s+(\d+)\s+"([^"]*)"\)', text, re.MULTILINE)}
    refs = {int(x) for x in
            re.findall(r'\(segment[\s\S]*?\(net\s+(\d+)\)', text) +
            re.findall(r'\(via[\s\S]*?\(net\s+(\d+)\)', text)}
    return {'declared': declared, 'refs': refs,
            'missing': refs - set(declared)}
