# Pitfalls — hard-won lessons from a real 27-component THT board build

Every item below cost at least one failed iteration during the LED-chaser
build (NE555 + CD4017, 103 tracks, 0 vias, final DRC 0 short / 0 unconnected).
Read before generating any board, and again whenever DRC stalls.

## 1. Workflow-level lessons (most important)

### 1.1 Never trust hand-computed pad coordinates
- A wrong C1/C2 pin-1/pin-2 assumption silently routed GND over a signal pad
  and cost one full rebuild. ALWAYS extract absolute pad positions from the
  generated board file with `extract_pads()` and route from those numbers.
- Pads file (`.kicad_mod`) local coordinates must go through rotation
  transform (`pad_pos()`). A rotated DIP-16 at 180° mirrors BOTH columns.

### 1.2 When patch iterations stall, wipe and rebuild
- Symptom: fatal count oscillates (14 → 11 → 5 → 7 → 5 → 3 ...) — each fix
  creates a new conflict elsewhere. Patching is deferring the problem.
- Cure: `strip_all_tracks()` back to the layout-only board, then re-route
  everything in ONE pass with every known conflict designed around.
  The rebuild reached 0/0 in a single session. Patching never would have.
- Keep the layout-only board file as a pristine reset point at all times.

### 1.3 Validate after EVERY change, with the tool, not by reasoning
- Run `drc_summary.py` after each edit batch. Track the fatal count as the
  only progress metric. Never claim "done" without a fresh DRC run.

## 2. Routing geometry rules (DIP/THT specific)

### 2.1 DIP pin pitch is the wall
- DIP pitch 2.54 mm; track width 0.6 mm + clearance ⇒ only ONE track fits
  between adjacent pads. Never route a bus THROUGH a DIP pin column.
- Route around: power buses on a clear vertical corridor (e.g. x offset from
  the chip), horizontal taps into each pin.

### 2.2 Minimum track-to-track spacing
- Two parallel tracks 0.32 mm apart (center-to-center) WILL be flagged.
  Offset one track to another corridor; do not try to squeeze.
- Assign distinct vertical corridors per signal (e.g. x=29/34/36/55/58/61/64…)
  and stagger horizontal runs at different y values.

### 2.3 GND daisy-chains across a pin column
- A GND track linking pin13→pin15 on the same column crosses pin14 (another
  net). Detour one column over (x+2mm) instead of running through.

### 2.4 Layer strategy that worked
- F.Cu: power (+5V) + control signals (CLK/TRIG/CONT/DISCH)
- B.Cu: LED matrix + Q-signals + GND bus
- Two-sided boards: tracks crossing on DIFFERENT layers are legal
  (`tracks_crossing` on different layers is expected, not a short).

### 2.5 Component pin1/pin2 order traps
- Radial electrolytic (CP): pin1 = +, pin2 = GND. Disc cap: either way.
- R_Axial DIN0207: pin1=(0,0), pin2=(10.16,0) — 10.16mm body length.
- LED D3.0: pin1 = cathode, pin2 = anode. Diodes/LEDs: verify against the
  footprint file, never against memory.

## 3. KiCad file-format traps (KiCad 9/10)

### 3.1 Footprint embedding from .kicad_mod
- When inlining a `.kicad_mod` into `.kicad_pcb`, the `version`, `generator`,
  and `layer` header fields must be stripped — they are invalid inside a
  board-level footprint instance and can make the board fail to load.
- `(embedded_fonts no)` INSIDE a footprint block (before 3D model) is normal
  in KiCad 10; the top-level one at file end is the insertion anchor.

### 3.2 Pad net injection
- KiCad 9/10 pads have NO `uuid` field. To assign a net, inject
  `(net N "name")` immediately before the pad's final closing paren.
- Undeclared net references (segment says net 27, board declares 26 nets)
  make the board silently fail to load in kicad-cli. `net_stats()` catches
  this before the CLI does.

### 3.3 S-expression surgery
- Every regex deletion of a segment block must match the FULL block ending
  `\n\t)\n` — truncated matches break paren balance (cost a -11 imbalance
  incident). Run `check_parens()` after every batch edit.
- Segment endpoint order is not canonical: match both directions
  (`find_and_remove_segment` does this).

### 3.4 kicad-cli quirks
- `pcb drc --output -` may fail with "board load failed" on 10.99 nightlies.
  Run plain `pcb drc --severity-all <file>` and read `<stem>-drc.rpt`.
- `pcb export gerbers` flag is `-o/--output` (a DIRECTORY), not `--output-dir`.
- `pcb export drill -o` wants the directory with trailing slash on Windows.
- `pcb render` gives high-quality PNG 3D views headless (~1 min each).

## 4. Schematic stage (quick reference)

- Three validation gates before touching PCB:
  Gate A: structural check (paren balance, required fields)
  Gate B: `kicad-cli sch erc` — must be 0 errors
  Gate C: netlist export vs expected nets — every net connected as designed
- `(hpglpennumber 1)` etc. in board setup need explicit parens when emitted.
- KiCad 10 ERC reads `rule_severities` from the schematic file; `.kicad_pro`
  settings are ignored by CLI.

## 5. Definition of done (fabrication gate)

| Check | Requirement |
|---|---|
| shorting_items | 0 |
| unconnected_items | 0 |
| ERC errors | 0 |
| net refs vs declared | no missing |
| paren balance | 0 |

Cosmetic classes that do NOT block a hobby/prototype fab run:
silk_overlap, silk_over_copper, courtyards_overlap, pth_inside_courtyard,
holes_co_located (R+D share a node by design), solder_mask_bridge.
Review-but-tolerable: clearance (≥0.15mm real-world OK for cheap fabs),
copper_edge_clearance, tracks_crossing (different layers).
