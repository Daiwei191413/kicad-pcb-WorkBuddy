#!/usr/bin/env python3
"""Schematic generator template — write .kicad_sch as text.

Adapted from a battle-tested NE555+CD4017 build (ERC 0 errors).
Replace the NETS/SYMBOLS/PLACEMENT tables with your circuit.
"""
import uuid

def uid(): return str(uuid.uuid4())

# ── 1. Net table: name → id (must match netlist expectations) ──
NETS = {'+5V': 1, 'GND': 2}  # + signal nets...

# ── 2. Symbol placements: ref → (x, y, lib_id, value) ──
SYMBOLS = {
    # 'U1': (100, 100, 'Timer:NE555', 'NE555'),
    # 'R1': (50, 50, 'Device:R', '10k'),
}

# ── 3. Wire list: ((x1,y1), (x2,y2)) polylines on the schematic grid ──
WIRES = [
    # ((100, 100), (100, 120)),
]

# ── 4. Local labels: (text, x, y, net) — use labels instead of long wires ──
LABELS = [
    # ('CLK', 130, 110, 'CLK'),
]

HEADER = '''(kicad_sch (version 20231120) (generator "codegen")
\t(generator_version "8.0")
\t(uuid "{uuid}")
\t(paper "A4")
\t(lib_symbols)
'''

def emit_symbol(ref, x, y, lib_id, value):
    # Minimal symbol instance; full pin/uuid emission follows the KiCad 8/9/10
    # schematic format — see the kicad-schematic-codegen skill for symbol
    # library extraction (embed lib_symbols block from the .kicad_sym lib).
    return (f'\t(symbol (lib_id "{lib_id}") (at {x} {y} 0) (unit 1)\n'
            f'\t\t(property "Reference" "{ref}" (at {x} {y} 0) (effects (font (size 1.27 1.27))))\n'
            f'\t\t(property "Value" "{value}" (at {x} {y} 0) (effects (font (size 1.27 1.27))))\n'
            f'\t\t(uuid "{uid()}")\n\t)\n')

def emit_wire(x1, y1, x2, y2):
    return (f'\t(wire (pts (xy {x1} {y1}) (xy {x2} {y2})) (stroke '
            f'(width 0) (type default)) (uuid "{uid()}"))\n')

def emit_label(text, x, y):
    return (f'\t(label "{text}" (at {x} {y} 0) (effects (font (size 1.27 1.27))) '
            f'(uuid "{uid()}"))\n')

def generate(path):
    out = HEADER.format(uuid=uid())
    for ref, (x, y, lib_id, value) in SYMBOLS.items():
        out += emit_symbol(ref, x, y, lib_id, value)
    for (p1, p2) in WIRES:
        out += emit_wire(*p1, *p2)
    for (text, x, y) in [(l[0], l[1], l[2]) for l in LABELS]:
        out += emit_label(text, x, y)
    out += ')\n'
    open(path, 'w', encoding='utf-8').write(out)
    print(f'wrote {path}: {out.count("(") - out.count(")")} paren balance must be 0')

if __name__ == '__main__':
    generate('template.kicad_sch')
    # THEN: Gate A structural check → Gate B kicad-cli sch erc → Gate C netlist compare
