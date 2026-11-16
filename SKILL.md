---
name: kicad-pcb-codegen
description: This skill should be used when generating, routing, DRC-fixing, or fabricating KiCad PCB boards entirely via code (no GUI). Covers the full flow from schematic text generation to Gerber export: .kicad_sch / .kicad_pcb s-expression codegen, footprint embedding with pad-net injection, rotation-aware pad geometry, track/via surgical editing, DRC violation triage (shorting/unconnected), and one-click fabrication package export. Battle-tested on KiCad 10.99 with kicad-cli. Complements the kicad-schematic-codegen skill (which covers symbol extraction for schematics); use that skill for symbol-library handling, this one for everything from netlist to fab files.
agent_created: true
---

# KiCad PCB Codegen — code-only board design, routing & fabrication

## Overview

Design KiCad PCBs end-to-end by writing files as text and validating with
`kicad-cli` — no GUI, fully scriptable, fully verifiable. Built from a real
27-component THT build (NE555 + CD4017 LED chaser) that went from 231 DRC
violations / 14 shorts to 0/0 and a complete Gerber fab package.

## Workflow (6 stages, each with a hard gate)

1. **Stage 0 — Environment**: locate kicad-cli; verify footprint library.
2. **Stage 1 — Schematic**: generate `.kicad_sch` as text; pass 3 gates
   (structural paren check → `kicad-cli sch erc` 0 errors → netlist export
   vs design intent). For symbol extraction, use the
   `kicad-schematic-codegen` skill.
3. **Stage 2 — Layout**: layout table → `.kicad_pcb` with embedded,
   net-injected footprints → board edge. Save a **layout-only reset copy**.
   Gate: board loads in CLI; 0 shorts.
4. **Stage 3 — Routing**: extract ALL pad coords with `extract_pads()`
   (never hand-compute!), plan per-net corridors (F.Cu = power/control,
   B.Cu = signals/GND; one vertical corridor per fanout signal; never route
   through a DIP pin column), emit tracks, DRC, fix.
   **If fatal count oscillates 2+ iterations → wipe all tracks
   (`strip_all_tracks`) and re-route in one pass with all lessons applied.**
   Gate: shorting_items = 0 AND unconnected_items = 0.
5. **Stage 4 — Fabrication**: `scripts/export_fab.py` → Gerbers + drill +
   assembly PDF + 3D renders.
6. **Stage 5 — Deliverables**: optional reports/articles from the real
   exports.

Full stage details: read `references/workflow.md` before starting any board.

## When to use

- "画/生成 PCB" / "布线" / "出制板文件" / "导出 Gerber" for a KiCad project
- DRC fixing sessions on a hand- or code-generated board
- Any request needing headless/board-file-level KiCad operations

## Non-negotiable rules (each one cost a real failure)

1. Pad coordinates ALWAYS via `extract_pads()` from the generated file —
   a hand-assumed C1 pin order cost a full rebuild.
2. Paren balance check (`check_parens`) after EVERY text edit batch —
   a regex ate closing parens once (-11 balance, board unloadable).
3. DRC after every change (`scripts/drc_summary.py`); the fatal count is the
   only progress metric. Never claim done without a fresh run.
4. Patch loops stall → wipe and rebuild. Always keep the layout-only copy.
5. Segments match in either endpoint direction
   (`find_and_remove_segment` handles both).
6. Cosmetic violations (silk/courtyard/holes_co_located) do NOT block
   prototyping; shorts and unconnects always do.

## Resources

### scripts/
- `pcb_tools.py` — core library: `emit_segment`/`emit_via` (uuid'd blocks),
  `pad_pos` (rotation transform), `extract_pads` (absolute pad coords + nets),
  `find_and_remove_segment` (bidirectional surgical delete),
  `insert_segments` (anchored before trailing `embedded_fonts`),
  `strip_all_tracks` (reset to layout-only), `check_parens`, `net_stats`
  (catches undeclared net refs before the CLI does).
- `drc_summary.py` — run DRC + classify violations (fatal/cosmetic/review)
  + print fatal locations. NOTE: do NOT pass `--output -` (broken on 10.99).
- `export_fab.py` — Gerbers (flag is `-o`, not `--output-dir`) + drill +
  PDF + 3D PNG renders in one shot.

### references/
- `pitfalls.md` — READ FIRST. All hard-won traps: DIP 2.54mm pitch rules,
  footprint field stripping (version/generator/layer), KiCad 9/10 pad net
  injection (no uuid anchor), kicad-cli quirks, fabrication gate table.
- `workflow.md` — the 6-stage process with gates in full detail.

### assets/
- `gen_sch_template.py` — schematic codegen skeleton (3-gate validation).
- `gen_pcb_template.py` — board codegen skeleton: layout table, footprint
  embedding with pad-net injection, edge, optional tracks.

## Fabrication gate (definition of done)

| Check | Must be |
|---|---|
| shorting_items | 0 |
| unconnected_items | 0 |
| ERC errors | 0 |
| net refs vs declared | no missing |
| paren balance | 0 |
