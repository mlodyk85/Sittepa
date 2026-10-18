#!/usr/bin/env python3
"""
Ender 3 V3 SE C13 - layer counter + manual multicolor helper.

Adds:
  M73 L<current> T<total>  -> layer information for custom firmware
  M600                    -> safe filament-change pause on selected layers

Layer numbers passed to --change are human-friendly (first layer = 1).
Supports Cura ;LAYER:n and Prusa/Orca ;LAYER_CHANGE markers.
"""
from pathlib import Path
import argparse
import re
import sys

CURA_RE = re.compile(r"^;LAYER:(-?\d+)\s*$")

def parse_changes(raw: str):
    if not raw.strip():
        return set()
    out = set()
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        value = int(item)
        if value < 1:
            raise ValueError("Layer numbers must be >= 1")
        out.add(value)
    return out

def find_layers(lines):
    cura = []
    for idx, line in enumerate(lines):
        m = CURA_RE.match(line.strip())
        if m and int(m.group(1)) >= 0:
            cura.append((idx, int(m.group(1)) + 1))
    if cura:
        total = max(n for _, n in cura)
        return "cura", cura, total

    orca_indices = [i for i, line in enumerate(lines) if line.strip() == ";LAYER_CHANGE"]
    if orca_indices:
        layers = [(idx, n + 1) for n, idx in enumerate(orca_indices)]
        return "orca-prusa", layers, len(layers)

    raise RuntimeError("No Cura ;LAYER:n or Orca/Prusa ;LAYER_CHANGE markers found.")

def transform(src: Path, dst: Path, changes):
    lines = src.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    style, layers, total = find_layers(lines)
    layer_by_line = {idx: human for idx, human in layers}

    invalid = sorted(x for x in changes if x > total)
    if invalid:
        raise ValueError(f"Requested change layers exceed total {total}: {invalid}")

    out = []
    for idx, line in enumerate(lines):
        out.append(line)
        human = layer_by_line.get(idx)
        if human is None:
            continue

        out.append(f"M73 L{human} T{total} ; V3SE layer counter\n")
        if human in changes:
            out.append(f"M600 ; V3SE filament/color change before layer {human}\n")

    dst.write_text("".join(out), encoding="utf-8")
    return style, total

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="Input .gcode")
    ap.add_argument("-o", "--output", type=Path, help="Output .gcode")
    ap.add_argument("--change", default="", help="Comma-separated 1-based layers, e.g. 25,60,80")
    args = ap.parse_args()

    changes = parse_changes(args.change)
    dst = args.output or args.input.with_name(args.input.stem + "_V3SE_COLOR.gcode")
    style, total = transform(args.input, dst, changes)

    print(f"Slicer markers: {style}")
    print(f"Total layers: {total}")
    print(f"Color-change layers: {sorted(changes) if changes else 'none'}")
    print(f"Output: {dst}")

if __name__ == "__main__":
    main()
