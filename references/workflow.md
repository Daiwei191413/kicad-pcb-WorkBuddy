# Full workflow — schematic to fabrication package (code-only, no GUI)

Six stages. Each stage has a hard gate; do not advance until the gate passes.

## Stage 0 — Environment & sanity check
1. Locate kicad-cli (`D:/Program Files/KiCad/10.99/bin/kicad-cli.exe` on this
   machine; verify with `kicad-cli version`). Verify footprint library path
   (`<kicad>/share/kicad/footprints`).
2. Confirm Python 3.10+ available for generation scripts.
3. Gate: `kicad-cli sch erc --help` runs without error.

## Stage 1 — Schematic generation (write text, don't draw)
1. Derive the net list from the circuit design first (net name → id map).
2. Generate the `.kicad_sch` via a Python script: symbols from the KiCad
   symbol library (embed or reference by lib_id), wires, labels, power
   symbols. Template: `assets/gen_sch_template.py`.
3. Gate A — structural: paren balance 0, required fields present.
4. Gate B — ERC: `kicad-cli sch erc <file>` → 0 errors.
5. Gate C — netlist: `kicad-cli sch export netlist` then compare every net's
   pin membership against the design intent table.
Gate: A+B+C all green.

## Stage 2 — PCB layout (placement only)
1. Define layout table: ref → (padset, x, y, rotation, footprint file, value,
   net map). Rotate parts to face their connection targets (e.g. counter IC
   180° so Q-outputs face the LED column).
2. Generate `.kicad_pcb` with embedded footprints (strip version/generator/
   layer fields; inject `(net N "name")` before each pad's closing paren).
3. Emit board edge (Edge.Cuts) and optional GND zone.
4. Save this state as `<project>-layout-only.kicad_pcb` — the pristine reset
   point.
Gate: board loads in kicad-cli (run `pcb drc`); only unconnected_items
violations expected, zero shorts.

## Stage 3 — Routing (the hard part)
1. Extract ALL absolute pad coordinates with `extract_pads()` — never
   hand-compute.
2. Plan corridors per net class:
   - F.Cu: power bus + control signals
   - B.Cu: signal fanout + GND bus
   - one distinct vertical corridor per fanned-out signal, staggered y
   - never route through a DIP pin column
3. Emit all segments/vias in one pass (`emit_segment`/`emit_via`).
4. Run `drc_summary.py`. Fix conflicts by re-designing the specific corridor
   (delete with `find_and_remove_segment`, re-insert with
   `insert_segments`).
5. If fatal count oscillates across 2+ iterations → Stage 3R:
   `strip_all_tracks()` and re-route from scratch with ALL lessons applied.
Gate: shorting_items = 0 AND unconnected_items = 0.

## Stage 4 — Fabrication export
Run `scripts/export_fab.py <board> <outdir>`:
- Gerbers (all layers) + Excellon drill + assembly PDF + 3D PNGs.
Gate: gerber file count ≥ 9 (Cu×2, Silk×2, Mask×2, Edge, Fab×2) + drill file.

## Stage 5 — Deliverables (optional)
- Layered PDF preview, 3D renders for documentation.
- Optionally produce an illustrated article/report from the real exports
  (PDF→PNG via pypdfium2; terminal-style DRC screenshots from real report
  data via PIL).
