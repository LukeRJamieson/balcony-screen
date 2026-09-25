# Balcony lattice screen: 5 independent bench modules

Five free-standing modules (600 / 600 / 900 / 600 / 600). Each module is one Lattice Makers economy
(square grid) lattice panel standing 20 mm off the floor, fixed to the back of its own two-tier plant bench.
**Modules are not fixed to each other, the wall or the floor.** Lattice sits 20 mm off the floor; overall height 1820.

## Files

| File | Purpose |
|---|---|
| `BalconyScreenBench.py` | Fusion 360 script **and** the whole parametric layout, in one file |
| `BalconyScreenBench.manifest` | Required by Fusion; must sit next to the .py |
| `export_bom.py` | Regenerates `Balcony_Screen_BOM.xlsx` from the .py (`--csv` for CSV) |
| `Drawings_elevation_section.png` | Dimensioned elevation + section |

## Running in Fusion 360

1. Unzip so you have a folder named exactly **`BalconyScreenBench`** directly containing
   `BalconyScreenBench.py` and `BalconyScreenBench.manifest`.
2. **Utilities > Add-Ins > Scripts and Add-Ins**, click **+** (or *Script or add-in from device*), pick that folder.
3. Select **BalconyScreenBench** > **Run**. Progress bar > a **new design tab** > summary dialog.

The model has one top-level component per module (`Module 1 - 600 wide` ... `Module 5 - 600 wide`).
Each contains a component per timber part (`MARK_PARTID_length`) plus its own **Fixings** sub-component
(red M10 bolts, blue 10G x 50, green 10G x 65, purple 10G x 100, black packers), so modules can be moved
or hidden individually.

**If it seems to do nothing:** look at the new tab, then check Text Commands and
`BalconyScreenBench_log.txt` in the script folder. No log file = Fusion never ran the script (folder /
manifest issue). A log that stops part way shows which step failed.

Outside Fusion, `python BalconyScreenBench.py` prints dimensions, the cut list and per-module stability.

## Design (per module)

* Width = its lattice panel; row of 5 is 3340 long with 10 mm gaps, centred on the 3550 wall (105 clear each end).
* 601 deep, bench top 500, lower shelf 130, 258 clear under the bench top, 10 mm clear of the wall.
* Section from the wall out: gap > 42x19 merbau strips > lattice > 90x45 post > bench.
* Two 90x45 posts flush with the module ends (1790 long on 10 mm foot packers). The 900 module also
  gets a short mid rear leg and a third frame so the boards don't span too far.
* Each post/leg forms a cross-frame with a front leg and two bearers, bolted 2 x M10 per lap.
* Three 90x45 rails between the posts (bottom, mid, top at 1820). The lattice is screwed through
  wall-side merbau strips into the posts and rails.
* 90x22 H3 decking cut to module width: 5 top boards, 4 shelf boards.
* Lattice modelled as a square grid (25 mm slats at 95 mm centres - visual only; measure your sheets
  and set `lattice_slat_width` / `lattice_slat_pitch`).

## Stability: read this

Each module stands on its own, so it's only as stable as its own weight (~29 kg for a 600, ~40 kg for
the 900) plus the pots on it. Indicative forward-tipping estimate for wind over the wall, assuming the
total pot load is spread evenly along the row and Bunnings' 20% blockout figure (editable on the Summary sheet):

| Total pots across all 5 modules | 600 modules tip at | 900 module tips at |
|---|---|---|
| None | ~92 km/h | ~90 km/h |
| 150 kg | ~114 km/h | ~115 km/h |
| 300 kg | ~132 km/h | ~135 km/h |

If your sheets are denser than 20% (a 25 mm slat on a 95 mm grid is closer to 45%), set
`lattice_solidity` to suit: at 45% the 150 kg case drops to about 95 km/h.

**People are the bigger risk than wind.** An empty 600 module tips forward with a pull of about
6.5 kg (64 N) at the top of the lattice. A child climbing the bench or pulling on the lattice could
bring it down. Keep the pots on them, and treat them as not climbable.

Rough check only (plants' windage ignored), not an engineering assessment.

## Buying and transport (up to 2.7 m)

`max_carry_length = 2700`, so every length is bought whole and all cutting is done at home:
* 90x45 H3 framing and 90x22 H3 decking: all 2.4 m lengths.
* 42x19 merbau screening is only sold in 2.7 m at Bunnings, so you'll be carrying 2.7 m lengths.
  (Set `max_carry_length = 2400` to have the store make one cut per merbau length instead.)

## Before cutting: measure

1. Actual lattice sheet size, **thickness** (model assumes 12 mm), slat width and grid spacing.
2. Clear length between the side balustrades, and the floor fall along the wall (each module may need
   its own packers to sit level, and neighbouring modules should line up).
3. Whether water pools along the wall. The lattice bottom is 20 mm up (`lattice_z0`); raise it if puddles
   are deeper. Overall height = `lattice_z0` + 1800, and the layout check warns above `max_height` (2000).

## Build sequence (repeat for each module)

1. Cut per the **Cutting Plan** sheet; brush cut ends of H3 pine (especially post tops) with end-grain preservative.
2. Build the cross-frames flat, bearers inside the posts. Clamp square, drill 11 mm, bolt.
3. Stand the frames on foot packers at the module width, screw the rear top board first to lock
   spacing, then the other top and shelf boards.
4. Fit the lattice rails with straight 10G x 100 screws (no angled screws anywhere):
   * **Bottom and mid rails** sit on the shelf and bench-top bearers; screw straight down through the
     rail into the bearer at each end.
   * **Top rail**: screw straight through each end post from the module's outside face into the rail end.
   * **900 module bottom rail** is two pieces either side of the mid rear leg. Fit the left piece first and
     screw through the mid leg from its right-hand face into the rail end, *then* fit the right piece,
     which sits on the mid bearer and the right-hand bearer.
   * Use the **Drilling** sheet for exact screw positions; they're placed to miss the frame bolts.
5. Lay the module on its front (bench side down), place the lattice on the posts, fix the vertical
   merbau strips then the horizontals. Pre-drill and countersink all merbau.
6. Stand it up and carry it out. Each module fits through a standard door (the 900 goes through on
   its 506 mm depth). Place 10 mm off the wall, 10 mm from its neighbour, level with packers.

## Notes

* Merbau with galvanised screws can leave dark tannin stains; stainless 10G screws avoid that.
* M10 x 120 bolts protrude ~15 mm past the nut on the 90 mm laps (M10 x 100 is too short).
* Bolt patterns are mirrored on each module's right-hand frames so cup heads on neighbouring modules
  never line up across the 10 mm gap. The model also checks that no two fixings collide.
* The modular version costs more than a single shared-post unit (10 posts and 88 bolts instead of 6 and 56).
