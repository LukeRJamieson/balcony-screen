# Balcony privacy screen and plant benches

Five free-standing timber plant benches with lattice privacy screens for a
first-floor townhouse balcony. Nothing is fixed to the building.

**Live 3D model:** https://lukerjamieson.github.io/balcony-screen/

This repository is both the website (`index.html` at the root, served by GitHub
Pages) and the complete build project for the **506 mm deep bench** version.

## What's here

| Path | What it is |
|---|---|
| `index.html` | The approval page with the interactive 3D model. Self-contained; GitHub Pages serves it |
| `Build_Guide.pdf`, `Build_Guide.docx` | Printable build guide: parts list, seven steps with a render at each stage, the 900 mm module, finishing |
| `Cutting_Guide.pdf` | Every stock length drawn to scale, with each piece, kerf, offcuts and a tick box per length |
| `BalconyScreenBench/` | The design model: Fusion 360 script (also plain Python), BOM and cut-list spreadsheet, drawing, cutting-guide generator, build README |
| `stl/` | 3D-printable models of the AC unit, figure, BBQ and bistro set, at real size in mm |
| `application/` | Owners corporation works application attachment (Word and PDF) |
| `docs/github-pages.md` | Notes on hosting and updating the page |

Online slide version of the build guide: https://claude.ai/artifact/VX7RYzKuyGwnUHXprddLsv

## The design at a glance

* Five modules, 600 / 600 / 900 / 600 / 600 mm wide, 3340 mm overall
* 1820 mm high, 506 mm deep, bench top at 500, lower shelf at 130
* 90x45 H3 pine frames bolted with M10 cup heads, 90x22 H3 decking boards and rails,
  Lattice Makers economy lattice, merbau cover strips
* About $966 in materials (see the spreadsheet)

## Regenerating from the model

Everything is generated from one model, so it all stays consistent. Edit `Config`
in `BalconyScreenBench/BalconyScreenBench.py`, then:

    cd BalconyScreenBench
    python BalconyScreenBench.py     # dimensions, cut list, stability check
    python export_bom.py             # rebuild the spreadsheet
    python cutting_guide.py          # redraw ../Cutting_Guide.pdf

Run `BalconyScreenBench.py` as a script inside Fusion 360 for the 3D CAD model.
