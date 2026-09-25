"""
BalconyScreenBench.py  -  Autodesk Fusion 360 script  (single self-contained file)
===============================================================================
Balcony lattice privacy screen made of FIVE INDEPENDENT MODULES (600/600/900/600/600).
Each module is one lattice panel fixed to its own two-tier plant bench.
Modules are not fixed to each other, the wall or the floor.

This one file contains:
  1. The parametric layout (parts, fixings, cut optimiser, drilling schedule,
     indicative stability check)  - pure Python, no Fusion needed.
  2. The Fusion 360 builder (run() / stop()).

HOW TO RUN IN FUSION
--------------------
1. Put this file and BalconyScreenBench.manifest in a folder named exactly
   BalconyScreenBench  (folder name, .py name and .manifest name must match).
2. Fusion: UTILITIES > ADD-INS > Scripts and Add-Ins > "+" next to My Scripts
   (or "Script or add-in from device") > select that folder.
3. Select BalconyScreenBench > Run.  A progress bar appears and a NEW design
   tab opens.  A summary dialog shows when finished.
4. If anything goes wrong, a dialog shows the error, and a log is written to
   TEXT COMMANDS (View > Show Text Commands) and to
   BalconyScreenBench_log.txt next to this file.

OUTSIDE FUSION
--------------
    python BalconyScreenBench.py      -> prints dimensions, cut list, stability
    python export_bom.py              -> regenerates the BOM spreadsheet

Units: mm.  Coordinates: X along the wall from the unit's left end, Y into the
balcony (0 = inside face of the wall), Z up from the deck.

Construction concept (per module)
---------------------------------
* Two 90x45 H3 posts, flush with the module ends, 90 mm perpendicular to the wall.
  The 900 module also gets a short rear leg in the middle.
* Each post / rear leg forms a cross-frame with a front leg and two lapped
  bearers (bench top + lower shelf), 2 x M10 cup-head bolts per lap.
* 90x22 H3 decking cut to the module width (4 top boards, 3 shelf boards).
* The lattice panel stands on the floor against the wall-side face of the
  posts, clamped by 42x19 merbau strips (wall side) screwed into the posts and
  into three 90x45 rails (bottom / mid / top) between the posts.
* Nothing above 1800. Modules stand side by side with a 10 mm gap.
* Stability comes only from each module's own weight plus its pots.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class Config:
    # --- Site (measure these!) ------------------------------------------------
    wall_length: float = 3550.0      # usable length along the wall
    wall_height: float = 1000.0      # deck to top of balcony wall
    wall_thickness: float = 152.0    # wall thickness (reference body only)

    # --- Lattice (Lattice Makers economy lattice) --------------------------------
    panel_widths: Tuple[float, ...] = (600.0, 600.0, 900.0, 600.0, 600.0)
    lattice_height: float = 1800.0
    lattice_z0: float = 20.0         # bottom of lattice above the floor (keeps it out of standing water)
    mid_rail_t: float = 22.0         # mid rail thickness; 22 finishes flush with the bench top
    module_gap: float = 10.0         # gap between neighbouring independent modules
    max_height: float = 2000.0       # nothing may project above this (1.8 m ideal, under 2 m OK)
    lattice_thickness: float = 12.0  # NOT published by Bunnings - measure a sheet
    lattice_pattern: str = "square"      # "square" grid (Lattice Makers economy) or "diagonal"
    lattice_slat_width: float = 25.0     # visual only - measure your sheet
    lattice_slat_pitch: float = 115.0    # visual only - gives 5 openings across a 600 sheet, matching the real product photos

    # --- Timber sections -------------------------------------------------------
    frame_w: float = 45.0            # 90x45 thickness
    frame_d: float = 90.0            # 90x45 depth
    board_w: float = 90.0            # 90x22 decking width
    board_t: float = 22.0            # 90x22 decking thickness
    board_gap: float = 5.0           # gap between deck boards (drainage)
    strip_w: float = 42.0            # merbau cover strip width
    strip_t: float = 19.0            # merbau cover strip thickness

    # --- Bench geometry --------------------------------------------------------
    bench_top_z: float = 500.0       # top surface of bench
    shelf_top_z: float = 130.0       # top surface of lower shelf
    n_top_boards: int = 4            # boards across the bench top
    board_overhang_front: float = 0.0  # top board overhang past front legs
    shelf_leg_clearance: float = 5.0   # gap between front shelf board and legs
    max_bearer_clear_bay: float = 700.0  # clear span between bearers above this gets a mid frame
    max_board_span: float = 610.0        # warn if bearer spacing exceeds this

    # --- Wall interface (non-penetrating) ----------------------------------------
    wall_gap: float = 10.0           # clearance from rear cover strips to wall (nothing fixed)
    foot_packer_t: float = 10.0      # plastic packer under every leg (0 = none)
    packer_w: float = 72.0           # Titan 10 x 72 x 100 shim packer
    packer_l: float = 100.0

    # --- Stability estimate (INDICATIVE ONLY - not an engineering check) ---------
    density_pine: float = 550.0      # kg/m3, H3 radiata pine (drier end - conservative)
    density_merbau: float = 850.0    # kg/m3
    lattice_solidity: float = 0.20   # Bunnings lists 20% blockout
    drag_coefficient: float = 1.2    # applied to solid frontal area
    wind_shield_z: Optional[float] = None  # screen below this is in the wall's lee
                                            # (None = wall_height)
    design_pot_kg: float = 150.0     # TOTAL pot + soil load over all modules (shared by width)
    min_tip_gust_kmh: float = 90.0   # warn if estimated tipping gust is below this

    # --- Fixings ----------------------------------------------------------------
    strip_screw_spacing: float = 300.0
    bolt_edge: float = 22.5          # bolt centre from lap edges (diagonal pair)

    # --- Stock / cutting --------------------------------------------------------
    kerf: float = 3.0
    end_trim: float = 10.0           # squaring allowance per stock length
    max_carry_length: float = 2700.0 # longest length you'll transport. 2700 takes the
                                     # merbau home whole, so all cutting is done yourself;
                                     # set 2400 to have the store cut it (see CATALOG store_cut)


# ---------------------------------------------------------------------------
# Geometry primitives
# ---------------------------------------------------------------------------


@dataclass
class Box:
    x0: float
    x1: float
    y0: float
    y1: float
    z0: float
    z1: float

    def dims(self) -> Tuple[float, float, float]:
        return (self.x1 - self.x0, self.y1 - self.y0, self.z1 - self.z0)

    def contains(self, p, tol: float = 0.01) -> bool:
        return (self.x0 - tol <= p[0] <= self.x1 + tol and
                self.y0 - tol <= p[1] <= self.y1 + tol and
                self.z0 - tol <= p[2] <= self.z1 + tol)

    def overlap_volume(self, o: "Box") -> float:
        dx = min(self.x1, o.x1) - max(self.x0, o.x0)
        dy = min(self.y1, o.y1) - max(self.y0, o.y0)
        dz = min(self.z1, o.z1) - max(self.z0, o.z0)
        if dx <= 0 or dy <= 0 or dz <= 0:
            return 0.0
        return dx * dy * dz


# Human-readable names for the three axes, used in the drilling schedule.
AXIS_NAME = {0: "X", 1: "Y", 2: "Z"}
AXIS_END_A = {0: "left end", 1: "wall end", 2: "bottom end"}


@dataclass
class Part:
    pid: str                 # unique id, e.g. "POST-3"
    name: str                # description
    group: str               # Bench / Screen
    material: str            # key into CATALOG
    box: Box
    mark: str = ""           # cut-list mark (identical parts share a mark)
    module: str = ""         # M1..M5 - which independent module this belongs to

    @property
    def axis(self) -> int:
        d = self.box.dims()
        return max(range(3), key=lambda i: d[i])

    @property
    def length(self) -> float:
        return self.box.dims()[self.axis]


@dataclass
class Fastener:
    kind: str                # key into FASTENER_CATALOG
    fid: str
    head: Tuple[float, float, float]
    tip: Tuple[float, float, float]
    dia: float
    note: str = ""
    module: str = ""

    @property
    def length(self) -> float:
        return math.dist(self.head, self.tip)


@dataclass
class Packer:
    pid: str
    note: str
    box: Box
    module: str = ""


@dataclass
class Model:
    cfg: Config
    unit_length: float
    x_offset: float                      # unit start measured from wall start
    parts: List[Part] = field(default_factory=list)
    fasteners: List[Fastener] = field(default_factory=list)
    packers: List[Packer] = field(default_factory=list)
    wall_ref: Optional[Box] = None
    info: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def part(self, pid: str) -> Part:
        for p in self.parts:
            if p.pid == pid:
                return p
        raise KeyError(pid)


# ---------------------------------------------------------------------------
# Catalogue (Bunnings, prices checked 16 Sep 2026 - verify before buying)
# ---------------------------------------------------------------------------

CATALOG = {
    "T90x45": dict(
        desc="90 x 45mm Outdoor Framing H3 Treated Pine (MGP10)",
        section="90x45", stock={2400: 18.50},
        url="https://www.bunnings.com.au/90-x-45mm-outdoor-framing-mgp10-h3-treated-pine-1-8m-2-4m_p8032172"),
    "D90x22": dict(
        desc="90 x 22mm Decking H3 Treated Pine",
        section="90x22", stock={2400: 9.58, 3600: 14.36},
        url="https://www.bunnings.com.au/90-x-22mm-decking-h3-treated-pine-2-4m_p8032583"),
    "M42x19": dict(
        desc="SpecRite 42 x 19mm Merbau Pre-Oiled Solid Screening",
        section="42x19", stock={2700: 9.00}, store_cut=True,   # only sold in 2.7 m
        url="https://www.bunnings.com.au/products/building-hardware/fencing/timber-fencing"),
    "LAT600": dict(
        desc="Lattice Makers 1800 x 600mm Economy Lattice",
        section="1800x600 sheet", stock={1: 19.99},
        url="https://www.bunnings.com.au/lattice-makers-1800-x-600mm-economy-lattice_p0920946"),
    "LAT900": dict(
        desc="Lattice Makers 1800 x 900mm Economy Lattice",
        section="1800x900 sheet", stock={1: 27.89},
        url="https://www.bunnings.com.au/lattice-makers-1800-x-900mm-economy-lattice_p0920950"),
}

FASTENER_CATALOG = {
    "BOLT_M10x120": dict(
        desc="ZENITH M10 x 120mm Hot Dip Galvanised Cup Head Bolts & Nuts - Each",
        pack=1, price=1.74, dia=10.0, hole=11.0,
        url="https://www.bunnings.com.au/zenith-m10-x-120mm-hot-dip-galvanised-cup-head-bolts-nuts-each_p2443953"),
    "BOLT_M10x150": dict(
        desc="ZENITH M10 x 150mm Hot Dip Galvanised Cup Head Bolts & Nuts - Each",
        pack=1, price=1.94, dia=10.0, hole=11.0,
        url="https://www.bunnings.com.au/zenith-m10-x-150mm-hot-dip-galvanised-cup-head-bolts-nuts-each_p2443987"),
    "WASHER_M10": dict(
        desc="ZENITH M10 Hot Dip Galvanised Flat Round Washers - Each",
        pack=1, price=0.30, dia=0.0, hole=0.0,
        url="https://www.bunnings.com.au/zenith-m10-hot-dip-galvanised-flat-round-washers-each_p2442070"),
    "SCREW_10Gx50": dict(
        desc="Zenith 10-8 x 50mm Galvanised Countersunk Rib Head Timber Screws - 50 Pack",
        pack=50, price=8.79, dia=4.8, hole=3.5,
        url="https://www.bunnings.com.au/search/products?q=galvanised+timber+screws"),
    "SCREW_10Gx65": dict(
        desc="Zenith 10-8 x 65mm Galvanised Countersunk Rib Head Timber Screws - 50 Pack",
        pack=50, price=10.90, dia=4.8, hole=3.5,
        url="https://www.bunnings.com.au/products/building-hardware/fasteners-fixings/screws/treated-pine-screws"),
    "SCREW_10Gx100": dict(
        desc="Zenith 10-8 x 100mm Galvanised Countersunk Rib Head Timber Screws - 50 Pack",
        pack=50, price=14.90, dia=4.8, hole=3.5,
        url="https://www.bunnings.com.au/zenith-10-8-x-100mm-galvanised-countersunk-rib-head-timber-screws-50-pack_p2420881"),
    "PACKER_10x72x100": dict(
        desc="Titan 10 x 72 x 100mm Black Shim Packing",
        pack=1, price=1.35, dia=0.0, hole=0.0,
        url="https://www.bunnings.com.au/products/building-hardware/fasteners-fixings"),
}


# ---------------------------------------------------------------------------
# Model builder
# ---------------------------------------------------------------------------


def build_model(c: Optional[Config] = None) -> Model:
    """Build five (or however many panel_widths) INDEPENDENT modules.

    Each module = one lattice panel + its own two end posts, bench frames,
    boards, rails and cover strips.  Modules share nothing and are not fixed
    to each other; they stand side by side with module_gap between them.

    Section (Y from the wall outwards):
        wall | gap | cover strip | lattice | post | bench top boards ... front legs
    """
    c = c or Config()
    widths = list(c.panel_widths)
    L = float(sum(widths) + c.module_gap * (len(widths) - 1))
    x_off = (c.wall_length - L) / 2.0
    if x_off < 0:
        raise ValueError(f"Modules total {L:.0f} mm, longer than the wall {c.wall_length:.0f} mm")

    m = Model(cfg=c, unit_length=L, x_offset=x_off)
    x = 0.0
    for n, w in enumerate(widths, start=1):
        _build_module(m, n, x, w)
        x += w + c.module_gap

    # ---- Summary info (dimensions are identical for every module) ----
    top_bearers = [p for p in m.parts if "-TBEAR-" in p.pid]
    spacing = 0.0
    for mod in module_names(m):
        xs = sorted((p.box.x0 + p.box.x1) / 2 for p in top_bearers if p.module == mod)
        spacing = max([spacing] + [b - a for a, b in zip(xs, xs[1:])])
    legs = [p for p in m.parts if "-FLEG-" in p.pid]
    tbear = top_bearers[0].box
    n_bolts = sum(1 for f in m.fasteners if f.kind == "BOLT_M10x120")
    lat_top = c.lattice_z0 + c.lattice_height
    m.wall_ref = Box(-x_off, L + x_off, -c.wall_thickness, 0, 0, c.wall_height)
    m.info = dict(
        unit_length=L, n_modules=len(widths), module_gap=c.module_gap, x_offset_each_end=x_off,
        overall_height=lat_top, bench_depth_from_wall=max(p.box.y1 for p in legs),
        bench_top_z=c.bench_top_z, shelf_top_z=c.shelf_top_z,
        shelf_clear_height=tbear.z0 - c.shelf_top_z,
        n_top_boards=sum(1 for p in m.parts if p.pid.startswith("M1-TOP-")),
        n_shelf_boards=sum(1 for p in m.parts if p.pid.startswith("M1-SHELF-")),
        max_bearer_spacing=spacing, height_above_wall=lat_top - c.wall_height,
        n_bolts=n_bolts, n_washers=n_bolts,
    )
    if lat_top > c.max_height + 0.01:
        m.warnings.append(f"Lattice top {lat_top:.0f} exceeds max height {c.max_height:.0f}")
    if spacing > c.max_board_span:
        m.warnings.append(f"Bearer spacing {spacing:.0f} mm exceeds {c.max_board_span:.0f} mm")

    assign_marks(m)
    m.warnings.extend(check_clashes(m))
    m.warnings.extend(check_fastener_collisions(m))

    worst = None
    for mod in module_names(m):
        st = stability(m, c.design_pot_kg, module=mod)
        if worst is None or st["tip_gust_kmh"] < worst["tip_gust_kmh"]:
            worst = st
    m.info["tip_gust_kmh"] = worst["tip_gust_kmh"]
    m.info["worst_module"] = worst["module"]
    if worst["tip_gust_kmh"] < c.min_tip_gust_kmh:
        m.warnings.append(
            f"STABILITY: module {worst['module']} is estimated to tip forward at "
            f"~{worst['tip_gust_kmh']:.0f} km/h gusts with its share of {c.design_pot_kg:.0f} kg of pots "
            f"(target {c.min_tip_gust_kmh:.0f}). Nothing is fixed to the wall, floor or other modules.")
    return m


def module_names(m: Model) -> List[str]:
    seen: List[str] = []
    for p in m.parts:
        if p.module not in seen:
            seen.append(p.module)
    return seen


def _build_module(m: Model, n: int, X0: float, W: float) -> None:
    """One self-contained lattice + bench module occupying X0..X0+W."""
    c = m.cfg
    mod = f"M{n}"
    fw, fd = c.frame_w, c.frame_d
    g, F = c.wall_gap, c.foot_packer_t
    X1 = X0 + W

    def add_part(pid, name, role, mat, box):
        m.parts.append(Part(f"{mod}-{pid}", name, role, mat, box, module=mod))
        return f"{mod}-{pid}"

    def add_fix(kind, fid, head, tip, dia, note):
        m.fasteners.append(Fastener(kind, f"{mod}-{fid}", head, tip, dia, note, module=mod))

    def is_clear(head, tip, dia, clearance=1.0):
        """True if a new fixing would not hit any fixing already in this module."""
        for f in m.fasteners:
            if f.module == mod and _seg_dist(head, tip, f.head, f.tip) < (dia + f.dia) / 2 + clearance:
                return False
        return True

    def pick_clear(candidates, dia=4.8):
        """First (head, tip) candidate that is clear; falls back to the first one."""
        for head, tip in candidates:
            if is_clear(head, tip, dia):
                return head, tip
        return candidates[0]

    # --- Heights -----------------------------------------------------------------
    top_z = c.bench_top_z
    bearer_top_z1 = top_z - c.board_t
    bearer_top_z0 = bearer_top_z1 - fd
    bearer_low_z1 = c.shelf_top_z - c.board_t
    bearer_low_z0 = bearer_low_z1 - fd
    lat_z0 = c.lattice_z0
    lat_z1 = lat_z0 + c.lattice_height
    post_z1 = lat_z1
    if bearer_low_z0 < F and n == 1:
        m.warnings.append("Lower bearers would sit below the foot packers - raise shelf_top_z")
    # (tag, bottom, top, material). The mid rail is 22 thick so it finishes flush
    # with the bench top, leaving no upstand for wide pots to foul.
    mid_t = c.mid_rail_t
    _flush_mat = "D90x22" if abs(mid_t - c.board_t) < 1 else "T90x45"
    rail_levels = [("BOT", bearer_low_z1, bearer_low_z1 + mid_t, _flush_mat),   # flush with the shelf
                   ("MID", bearer_top_z1, bearer_top_z1 + mid_t, _flush_mat),   # flush with the bench top
                   ("TOP", post_z1 - fw, post_z1, "T90x45")]

    # --- Depths (Y) ----------------------------------------------------------------
    y_strip0, y_strip1 = g, g + c.strip_t
    y_lat0, y_lat1 = y_strip1, y_strip1 + c.lattice_thickness
    y_post0, y_post1 = y_lat1, y_lat1 + fd
    y_board0 = y_post1
    n_top = c.n_top_boards
    y_front = y_board0 + n_top * c.board_w + (n_top - 1) * c.board_gap
    leg_y1 = y_front - c.board_overhang_front
    leg_y0 = leg_y1 - fd
    avail = leg_y0 - c.shelf_leg_clearance - y_board0
    n_shelf = n_top                                  # shelf runs the full depth, like the bench top

    # --- Frames: end posts flush with the module ends, mid frames if wide ------------
    frames = [dict(x0=X0, x1=X0 + fw, kind="post", side=1),
              dict(x0=X1 - fw, x1=X1, kind="post", side=-1)]
    # bearers sit inside the posts, so the clear span is between the bearers
    clear = (X1 - 2 * fw) - (X0 + 2 * fw)
    n_mid = max(0, math.ceil(clear / c.max_bearer_clear_bay) - 1)
    for k in range(1, n_mid + 1):
        xc = X0 + fw + (W - 2 * fw) * k / (n_mid + 1)
        frames.append(dict(x0=xc - fw / 2, x1=xc + fw / 2, kind="mid",
                           side=1 if xc <= X0 + W / 2 + 1e-6 else -1))
    frames.sort(key=lambda f: f["x0"])

    rear_members = []
    post_i = mid_i = 0
    for fi, fr in enumerate(frames, start=1):
        x0, x1, side = fr["x0"], fr["x1"], fr["side"]
        xc = (x0 + x1) / 2
        bx0, bx1 = (x1, x1 + fw) if side > 0 else (x0 - fw, x0)
        if fr["kind"] == "post":
            post_i += 1
            rear_id = add_part(f"POST-{post_i}", "Screen post / rear bench leg", "Screen", "T90x45",
                               Box(x0, x1, y_post0, y_post1, F, post_z1))
            rear_members.append((x0, x1, post_z1))
        else:
            mid_i += 1
            rear_id = add_part(f"RLEG-{mid_i}", "Rear bench leg (mid frame)", "Bench", "T90x45",
                               Box(x0, x1, y_post0, y_post1, F, bearer_top_z1))
            rear_members.append((x0, x1, bearer_top_z1))
        leg_id = add_part(f"FLEG-{fi}", "Front bench leg", "Bench", "T90x45",
                          Box(x0, x1, leg_y0, leg_y1, F, bearer_top_z1))
        tb_id = add_part(f"TBEAR-{fi}", "Bench top bearer", "Bench", "T90x45",
                         Box(bx0, bx1, y_post0, leg_y1, bearer_top_z0, bearer_top_z1))
        lb_id = add_part(f"LBEAR-{fi}", "Lower shelf bearer", "Bench", "T90x45",
                         Box(bx0, bx1, y_post0, leg_y1, bearer_low_z0, bearer_low_z1))
        tb_id2 = lb_id2 = None
        if fr["kind"] == "mid":
            # Second bearers on the far side of the middle leg, at both levels, so the
            # bench top and shelf boards are carried either side of that frame.
            ox0, ox1 = (x0 - fw, x0) if side > 0 else (x1, x1 + fw)
            tb_id2 = add_part(f"TBEAR-{fi}B", "Bench top bearer", "Bench", "T90x45",
                              Box(ox0, ox1, y_post0, leg_y1, bearer_top_z0, bearer_top_z1))
            lb_id2 = add_part(f"LBEAR-{fi}B", "Lower shelf bearer", "Bench", "T90x45",
                              Box(ox0, ox1, y_post0, leg_y1, bearer_low_z0, bearer_low_z1))

        # Frame bolts: 2 per lap, diagonal; head on the member's outer face
        head_x = x0 if side > 0 else x1
        dirx = 1 if side > 0 else -1
        e = c.bolt_edge
        for member, (ly0, ly1) in ((rear_id, (y_post0, y_post1)), (leg_id, (leg_y0, leg_y1))):
            for bear, (lz0, lz1) in ((tb_id, (bearer_top_z0, bearer_top_z1)),
                                     (lb_id, (bearer_low_z0, bearer_low_z1))):
                # Mirror the diagonal on right-hand frames so cup heads on neighbouring
                # modules' end posts never face each other across the module gap.
                pattern = ((ly0 + e, lz0 + e), (ly1 - e, lz1 - e)) if side > 0 else \
                          ((ly0 + e, lz1 - e), (ly1 - e, lz0 + e))
                # a doubled joint is 45 + 45 + 45, so it takes an M10x150
                long_bolt = (lb_id2 is not None and bear in (lb_id, tb_id))
                hx = ((x0 - fw) if side > 0 else (x1 + fw)) if long_bolt else head_x
                for k, (yy, zz) in enumerate(pattern):
                    add_fix("BOLT_M10x150" if long_bolt else "BOLT_M10x120",
                            f"B-{member.split('-', 1)[1]}-{bear.split('-', 1)[1]}-{k + 1}",
                            (hx, yy, zz), (hx + dirx * (150 if long_bolt else 120), yy, zz), 10.0,
                            f"{member} to {bear}" + (" (through both bearers)" if long_bolt else ""))

        # Foot packers, long axis along X, kept inside the module footprint
        if F > 0:
            px0 = max(X0, xc - c.packer_l / 2)
            px1 = min(X1, px0 + c.packer_l)
            px0 = px1 - c.packer_l
            for mem, (yy0, yy1) in ((rear_id, (y_post0, y_post1)), (leg_id, (leg_y0, leg_y1))):
                cy = (yy0 + yy1) / 2
                m.packers.append(Packer(f"PK-{mem}", f"Foot packer under {mem}",
                                        Box(px0, px1, cy - c.packer_w / 2, cy + c.packer_w / 2, 0, F),
                                        module=mod))

    # --- Deck boards (module length) ----------------------------------------------
    for prefix, name, n_boards, z_top, bear_tag in (("TOP", "Bench top board", n_top, top_z, "TBEAR"),
                                                    ("SHELF", "Lower shelf board", n_shelf, c.shelf_top_z, "LBEAR")):
        bearers = [p for p in m.parts if p.pid.startswith(f"{mod}-{bear_tag}-")]
        leg_spans = sorted((fr["x0"], fr["x1"]) for fr in frames)
        for i in range(n_boards):
            y0 = y_board0 + i * (c.board_w + c.board_gap)
            y1 = y0 + c.board_w
            # A shelf board that reaches the front legs is cut into pieces that fit
            # between them; every other board runs the full module width.
            meets_legs = prefix == "SHELF" and y1 > leg_y0 + 1
            pieces = ([(a[1], b[0]) for a, b in zip(leg_spans, leg_spans[1:])]
                      if meets_legs else [(X0, X1)])
            for j, (px0, px1) in enumerate(pieces):
                if px1 - px0 < 50:
                    continue
                tag = f"{prefix}-{i + 1}" + (chr(ord("a") + j) if meets_legs else "")
                pid = add_part(tag, name, "Bench", "D90x22", Box(px0, px1, y0, y1, z_top - c.board_t, z_top))
                for b in bearers:
                    if min(b.box.x1, px1) - max(b.box.x0, px0) < 20:
                        continue                    # this bearer is not under this piece
                    bx = (max(b.box.x0, px0) + min(b.box.x1, px1)) / 2
                    for k, offs in enumerate(((20, 30, 40, 45), (-20, -30, -40, -45))):
                        edge = y0 if k == 0 else y1
                        head, tip = pick_clear([((bx, edge + o, z_top), (bx, edge + o, z_top - 50)) for o in offs])
                        add_fix("SCREW_10Gx50", f"S-{tag}-{b.pid.split('-', 1)[1]}-{k + 1}",
                                head, tip, 4.8, f"{pid} to {b.pid}")

    # --- Lattice rails between this module's rear members ----------------------------
    # All rail fixings are straight (no toe-screwing):
    #   * a rail end that sits on a bench bearer is screwed straight DOWN into it;
    #   * otherwise it is screwed straight THROUGH the post / rear leg into the rail's
    #     end grain, from the member's far face (a module end face, or the mid leg
    #     face before the second half of a split rail goes in).
    bearers = [p for p in m.parts if p.pid.startswith((f"{mod}-TBEAR-", f"{mod}-LBEAR-"))]
    members = [p for p in m.parts if p.pid.startswith((f"{mod}-POST-", f"{mod}-RLEG-"))]
    rail_i = 0
    for tag, rz0, rz1, rail_mat in rail_levels:
        stops = sorted((x0, x1) for x0, x1, z1 in rear_members if z1 > rz0 + 0.01)
        for (a0, a1), (b0, b1) in zip(stops, stops[1:]):
            rx0, rx1 = a1, b0
            if rx1 - rx0 < 1:
                continue
            rail_i += 1
            short = f"RAIL{tag}-{rail_i}"
            rid = add_part(short, f"Lattice rail ({tag.lower()})", "Screen", rail_mat,
                           Box(rx0, rx1, y_post0, y_post1, rz0, rz1))
            for end, (xe, d) in enumerate(((rx0, -1), (rx1, 1))):
                # bearer directly under this end of the rail?
                under = [bb for bb in bearers
                         if abs(bb.box.z1 - rz0) < 0.5
                         and bb.box.x0 < max(rx0, rx1 - fw) + fw and bb.box.x1 > min(rx1, rx0 + fw) - fw
                         and min(bb.box.x1, rx1) - max(bb.box.x0, rx0) > fw / 2
                         and ((d < 0 and bb.box.x0 < rx0 + fw) or (d > 0 and bb.box.x1 > rx1 - fw))]
                if under:
                    bb = under[0]
                    bx = (max(bb.box.x0, rx0) + min(bb.box.x1, rx1)) / 2
                    # Y chosen to clear the bearer's frame bolts
                    used = []
                    for k in range(2):
                        cands = [((bx, y_post0 + o, rz1), (bx, y_post0 + o, rz1 - 100))
                                 for o in (30, 55, 20, 45, 70, 80, 38, 62)
                                 if all(abs(y_post0 + o - u) >= 20 for u in used)]
                        head, tip = pick_clear(cands)
                        used.append(head[1])
                        add_fix("SCREW_10Gx100", f"S-{short}-E{end + 1}-{k + 1}",
                                head, tip, 4.8, f"{rid} screwed down into {bb.pid}")
                    continue
                mem = [mm for mm in members
                       if (abs(mm.box.x1 - rx0) < 0.5 if d < 0 else abs(mm.box.x0 - rx1) < 0.5)
                       and mm.box.z1 >= rz1 - 0.5]
                if not mem:
                    m.warnings.append(f"{rid}: no bearer or member to fix end {end + 1} to")
                    continue
                mm = mem[0]
                head_x = mm.box.x0 if d < 0 else mm.box.x1      # member's far face
                tip_x = head_x - d * 100
                # Z offsets keep clear of the horizontal cover-strip screws at rail mid-height
                used = []
                for k in range(2):
                    cands = [((head_x, y_post0 + oy, zz), (tip_x, y_post0 + oy, zz))
                             for oy in (25, 65, 45, 80) for zz in (rz0 + 11, rz1 - 11, (rz0 + rz1) / 2)
                             if all(math.dist((y_post0 + oy, zz), u) >= 20 for u in used)]
                    if used:  # prefer the position furthest from the first screw
                        cands.sort(key=lambda hc: -min(math.dist((hc[0][1], hc[0][2]), u) for u in used))
                    head, tip = pick_clear(cands)
                    used.append((head[1], head[2]))
                    add_fix("SCREW_10Gx100", f"S-{short}-E{end + 1}-{k + 1}",
                            head, tip, 4.8, f"{rid} screwed through {mm.pid} into rail end")

    # --- Lattice panel (stands on the floor) -----------------------------------------
    mat = "LAT900" if abs(W - 900) < 1 else "LAT600"
    add_part("LAT", f"Lattice panel {W:.0f} wide", "Screen", mat, Box(X0, X1, y_lat0, y_lat1, lat_z0, lat_z1))

    # --- Cover strips on the wall side -------------------------------------------------
    def even_positions(a, b, spacing, min_n=2):
        k = max(min_n, math.ceil((b - a) / spacing) + 1)
        return [a + (b - a) * i / (k - 1) for i in range(k)]

    vs = [(X0, X0 + c.strip_w), (X1 - c.strip_w, X1)]
    for i, (sx0, sx1) in enumerate(vs, start=1):
        sid = add_part(f"VSTRIP-{i}", "Vertical cover strip (wall side)", "Screen", "M42x19",
                       Box(sx0, sx1, y_strip0, y_strip1, lat_z0, lat_z1))
        xx = (sx0 + sx1) / 2
        for k, zz in enumerate(even_positions(max(lat_z0, F) + 60, post_z1 - c.strip_w - 40, c.strip_screw_spacing)):
            # nudge up/down if it would meet a frame bolt inside the post
            head, tip = pick_clear([((xx, y_strip0, zz + dz), (xx, y_strip0 + 65, zz + dz))
                                    for dz in (0, 20, -20, 35, -35, 50)])
            add_fix("SCREW_10Gx65", f"S-VSTRIP{i}-{k + 1}", head, tip, 4.8,
                    f"{sid} through lattice into post")
    _rail_mid = {tag: (rz0 + rz1) / 2 for tag, rz0, rz1, _ in rail_levels}
    # The lattice is clamped around its perimeter: a strip over each post and one
    # along the bottom and top rails. The mid rail carries no strip.
    strip_z = {"TOP": (post_z1 - c.strip_w, post_z1)}
    hx0, hx1 = vs[0][1], vs[1][0]
    for tag, (hz0, hz1) in strip_z.items():
        sid = add_part(f"HSTRIP-{tag}", f"Horizontal cover strip ({tag.lower()}, wall side)", "Screen", "M42x19",
                       Box(hx0, hx1, y_strip0, y_strip1, hz0, hz1))
        zz = (hz0 + hz1) / 2
        for k, xx in enumerate(even_positions(hx0 + 40, hx1 - 40, c.strip_screw_spacing)):
            if any(x0 - 5 <= xx <= x1 + 5 for x0, x1, _ in rear_members):
                xx += 60   # keep off the mid rear leg; land in the rail instead
            head, tip = pick_clear([((xx + dx, y_strip0, zz), (xx + dx, y_strip0 + 65, zz))
                                    for dx in (0, 15, -15, 30, -30)])
            add_fix("SCREW_10Gx65", f"S-HSTRIP{tag}-{k + 1}", head, tip, 4.8,
                    f"{sid} through lattice into {tag.lower()} rail")


# ---------------------------------------------------------------------------
# Checks, marks, cutting and schedules
# ---------------------------------------------------------------------------


def check_clashes(m: Model, tol_vol: float = 1.0) -> List[str]:
    """Report any solid-solid overlap between timber parts, packers and the wall."""
    solids = [(p.pid, p.box) for p in m.parts] + [(k.pid, k.box) for k in m.packers]
    if m.wall_ref:
        solids.append(("WALL", m.wall_ref))
    out = []
    for i in range(len(solids)):
        for j in range(i + 1, len(solids)):
            v = solids[i][1].overlap_volume(solids[j][1])
            if v > tol_vol:
                out.append(f"CLASH {solids[i][0]} x {solids[j][0]} ({v:.0f} mm3)")
    return out


def _seg_dist(p1, q1, p2, q2) -> float:
    """Minimum distance between segments p1-q1 and p2-q2."""
    d1 = [q1[i] - p1[i] for i in range(3)]
    d2 = [q2[i] - p2[i] for i in range(3)]
    r = [p1[i] - p2[i] for i in range(3)]
    dot = lambda u, v: sum(u[i] * v[i] for i in range(3))
    a, e, f = dot(d1, d1), dot(d2, d2), dot(d2, r)
    c, b = dot(d1, r), dot(d1, d2)
    denom = a * e - b * b
    s_ = min(max((b * f - c * e) / denom, 0.0), 1.0) if denom > 1e-9 else 0.0
    t = (b * s_ + f) / e if e > 1e-9 else 0.0
    if t < 0:
        t, s_ = 0.0, min(max(-c / a, 0.0), 1.0) if a > 1e-9 else 0.0
    elif t > 1:
        t, s_ = 1.0, min(max((b - c) / a, 0.0), 1.0) if a > 1e-9 else 0.0
    c1 = [p1[i] + d1[i] * s_ for i in range(3)]
    c2 = [p2[i] + d2[i] * t for i in range(3)]
    return math.dist(c1, c2)


def check_fastener_collisions(m: Model, clearance: float = 1.0) -> List[str]:
    """Report any two bolts/screws whose shanks would hit each other."""
    out = []
    fs = m.fasteners
    boxes = []
    for f in fs:
        r = f.dia / 2 + clearance
        boxes.append([min(f.head[i], f.tip[i]) - r for i in range(3)] +
                     [max(f.head[i], f.tip[i]) + r for i in range(3)])
    for i in range(len(fs)):
        bi = boxes[i]
        for j in range(i + 1, len(fs)):
            bj = boxes[j]
            if any(bi[k] > bj[k + 3] or bj[k] > bi[k + 3] for k in range(3)):
                continue
            if _seg_dist(fs[i].head, fs[i].tip, fs[j].head, fs[j].tip) < (fs[i].dia + fs[j].dia) / 2 + clearance:
                out.append(f"FIXING CLASH {fs[i].fid} x {fs[j].fid}")
    return out


def assign_marks(m: Model) -> None:
    """Parts with identical material and cut dimensions share one letter mark
    (drilling differs per part - see the drilling schedule by part id)."""
    order_mat = ["T90x45", "D90x22", "M42x19"]
    groups: Dict[Tuple, List[Part]] = {}
    for p in m.parts:
        if p.material.startswith("LAT"):
            p.mark = p.material
            continue
        d = tuple(sorted(round(v, 1) for v in p.box.dims()))
        groups.setdefault((p.material, d), []).append(p)
    order = sorted(groups.items(), key=lambda kv: (order_mat.index(kv[0][0]), -max(kv[0][1])))
    for n, (_, parts) in enumerate(order):
        for p in parts:
            p.mark = _mark_name(n)


def _mark_name(n: int) -> str:
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def cut_list(m: Model) -> List[dict]:
    rows: Dict[str, dict] = {}
    for p in m.parts:
        if p.material.startswith("LAT"):
            continue
        r = rows.setdefault(p.mark, dict(mark=p.mark, names=[], material=p.material,
                                         section=CATALOG[p.material]["section"],
                                         length=round(p.length, 1), qty=0, ids=[]))
        if p.name not in r["names"]:
            r["names"].append(p.name)
        r["name"] = "; ".join(r["names"])
        r["qty"] += 1
        r["ids"].append(p.pid)
    return sorted(rows.values(), key=lambda r: (len(r["mark"]), r["mark"]))


def _store_split(pieces: List[Tuple[str, float, str]], c: Config) -> Optional[Tuple[float, list, list]]:
    """Split one stock length's pieces into two groups that each fit within
    max_carry_length, so the store can make a single cut. Returns
    (cut position from end, group A, group B) or None if impossible."""
    limit = c.max_carry_length
    ordered = sorted(pieces, key=lambda x: -x[1])
    a_grp, b_grp, a_len = [], [], c.end_trim / 2
    for pc in ordered:
        if a_len + pc[1] + c.kerf <= limit:
            a_grp.append(pc)
            a_len += pc[1] + c.kerf
        else:
            b_grp.append(pc)
    b_len = sum(pc[1] + c.kerf for pc in b_grp) + c.end_trim / 2
    if b_len > limit:
        return None
    return (round(a_len, 1), a_grp, b_grp)


def _pack(parts: List[Part], stocks: List[float], c: Config, mat: str, store_cut: bool) -> List[dict]:
    """First-fit-decreasing into stock lengths. If store_cut, each length must be
    splittable by one in-store cut into two pieces no longer than max_carry_length."""
    bins: List[dict] = []
    for p in sorted(parts, key=lambda q: -q.length):
        need = p.length + c.kerf
        piece = (p.mark, round(p.length, 1), p.pid)
        best = None
        for b in bins:
            if b["remaining"] < need or (best is not None and b["remaining"] >= best["remaining"]):
                continue
            if store_cut and b["stock"] > c.max_carry_length and _store_split(b["pieces"] + [piece], c) is None:
                continue
            best = b
        if best is None:
            fit = [s_ for s_ in stocks if s_ - c.end_trim >= p.length]
            if not fit:
                return []
            best = dict(material=mat, stock=fit[0], remaining=fit[0] - c.end_trim, pieces=[])
            bins.append(best)
        best["pieces"].append(piece)
        best["remaining"] -= need
    return bins


def optimise_cuts(m: Model) -> List[dict]:
    """Cheapest cutting plan per material using only lengths you can carry
    (<= max_carry_length). Materials only sold longer are split by one
    in-store cut into two carryable pieces."""
    c = m.cfg
    plans = []
    by_mat: Dict[str, List[Part]] = {}
    for p in m.parts:
        if not p.material.startswith("LAT"):
            by_mat.setdefault(p.material, []).append(p)
    for mat, parts in by_mat.items():
        cat = CATALOG[mat]
        prices = cat["stock"]
        carry = sorted(s_ for s_ in prices if s_ <= c.max_carry_length)
        store_cut = False
        if carry:
            all_stocks = carry
        elif cat.get("store_cut"):
            all_stocks = sorted(prices)
            store_cut = True
        else:
            raise ValueError(f"{mat}: no stock length <= {c.max_carry_length:.0f} and no store cut option")
        too_long = [p.pid for p in parts if p.length + c.end_trim > c.max_carry_length]
        if too_long:
            raise ValueError(f"{mat}: parts longer than you can carry: {too_long[:3]}")
        best_bins, best_key = None, None
        candidates = [[s_ for s_ in all_stocks if s_ >= s0] for s0 in all_stocks] + [all_stocks]
        for stocks in candidates:
            bins = _pack(parts, stocks, c, mat, store_cut)
            if not bins:
                continue
            for b in bins:  # downsize part-filled lengths
                used = b["stock"] - c.end_trim - b["remaining"]
                smallest = min(s_ for s_ in all_stocks if s_ - c.end_trim >= used - 1e-6)
                b["remaining"] += smallest - b["stock"]
                b["stock"] = smallest
            key = (round(sum(prices[b["stock"]] for b in bins), 2), max(b["stock"] for b in bins))
            if best_key is None or key < best_key:
                best_bins, best_key = bins, key
        if best_bins is None:
            raise ValueError(f"No cutting plan found for {mat}")
        for i, b in enumerate(best_bins):
            b["n"] = i + 1
            b["store_cut_at"] = None
            if store_cut and b["stock"] > c.max_carry_length:
                cut_at, grp_a, grp_b = _store_split(b["pieces"], c)
                b["store_cut_at"] = cut_at
                b["pieces"] = grp_a + grp_b   # listed in cutting order
        plans.extend(best_bins)
    return plans


def _segment_samples(f: Fastener, n: int = 60):
    for k in range(n + 1):
        t = k / n
        yield tuple(f.head[i] + (f.tip[i] - f.head[i]) * t for i in range(3))


def drilling_schedule(m: Model) -> List[dict]:
    """For every fastener and every timber part it passes through, give the hole
    position measured along the part from its 'end A' plus the across-face offset."""
    rows = []
    for f in m.fasteners:
        vec = [f.tip[i] - f.head[i] for i in range(3)]
        fdir = max(range(3), key=lambda i: abs(vec[i]))
        for p in m.parts:
            inside = [pt for pt in _segment_samples(f) if p.box.contains(pt, tol=-0.5)]
            if not inside:
                continue
            mid = inside[len(inside) // 2]
            ax = p.axis
            mins = (p.box.x0, p.box.y0, p.box.z0)
            along = mid[ax] - mins[ax]
            others = [i for i in range(3) if i not in (ax, fdir)]
            if others:
                across_ax = others[0]
            else:  # end-grain screw: report offset across the wider face
                dims = p.box.dims()
                across_ax = max((i for i in range(3) if i != ax), key=lambda i: dims[i])
            across = mid[across_ax] - mins[across_ax]
            kind = FASTENER_CATALOG[f.kind]
            end_grain = fdir == ax
            rows.append(dict(
                mark=p.mark, part=p.pid, fastener=f.kind, fid=f.fid,
                along=round(along, 1), along_ref=AXIS_END_A[ax],
                across=round(across, 1), across_ref=f"from {AXIS_NAME[across_ax]}-min face",
                drill_dir=AXIS_NAME[fdir] + (" (angled 40deg)" if abs(vec[fdir]) < f.length * 0.99 else ""),
                hole=kind["hole"], end_grain=end_grain))
    rows.sort(key=lambda r: (r["mark"], r["part"], r["along"]))
    return rows



def stability(m: Model, pot_kg_total: float = 0.0, module: Optional[str] = None) -> dict:
    """Rough forward-tipping check for ONE module (they are independent) with
    wind blowing over the wall into the balcony.

    The module pivots about the front edge of its front legs.  Resisting moment
    is its self weight plus its share of the pots (by width) about that edge;
    overturning moment is wind drag on the solid frontal area above the wall top.
    Plants' own windage is ignored - treat this as a sanity check only.
    """
    c = m.cfg
    g = 9.81
    module = module or module_names(m)[0]
    parts = [p for p in m.parts if p.module == module]
    toe_y = max(p.box.y1 for p in parts if p.pid.startswith(f"{module}-FLEG-"))
    mass = moment = 0.0
    for p in parts:
        dx, dy, dz = (v / 1000 for v in p.box.dims())
        vol = dx * dy * dz
        if p.material.startswith("LAT"):
            kg = vol * c.lattice_solidity * c.density_pine
        elif p.material == "M42x19":
            kg = vol * c.density_merbau
        else:
            kg = vol * c.density_pine
        mass += kg
        moment += kg * (toe_y - (p.box.y0 + p.box.y1) / 2) / 1000
    width = max(p.box.x1 for p in parts) - min(p.box.x0 for p in parts)
    share = width / sum(c.panel_widths)
    pot_kg = pot_kg_total * share
    tops = [p for p in parts if p.pid.startswith(f"{module}-TOP-")]
    pot_y = (min(p.box.y0 for p in tops) + max(p.box.y1 for p in tops)) / 2
    pot_lever = (toe_y - pot_y) / 1000
    m_res = g * (moment + pot_kg * pot_lever)

    shield = c.wall_height if c.wind_shield_z is None else c.wind_shield_z
    area = az = 0.0
    for p in parts:
        if p.group != "Screen" or "-POST-" in p.pid or "-RAIL" in p.pid:
            continue
        z0, z1 = max(p.box.z0, shield), p.box.z1
        if z1 <= z0:
            continue
        frac = c.lattice_solidity if p.material.startswith("LAT") else (1 - c.lattice_solidity)
        a = (p.box.x1 - p.box.x0) * (z1 - z0) / 1e6 * frac
        area += a
        az += a * (z0 + z1) / 2 / 1000
    zc = az / area if area else 0.0
    per_v2 = 0.6 * c.drag_coefficient * area * zc
    v_tip = math.sqrt(m_res / per_v2) if per_v2 > 0 else float("inf")
    return dict(module=module, width=width, pot_share=share, self_kg=mass,
                self_lever_m=moment / mass if mass else 0.0, pot_kg=pot_kg, pot_lever_m=pot_lever,
                resisting_Nm=m_res, frontal_area_m2=area, wind_centroid_m=zc,
                tip_gust_ms=v_tip, tip_gust_kmh=v_tip * 3.6)


def fastener_counts(m: Model) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for f in m.fasteners:
        counts[f.kind] = counts.get(f.kind, 0) + 1
    counts["WASHER_M10"] = counts.get("BOLT_M10x120", 0) + counts.get("BOLT_M10x150", 0)
    counts["PACKER_10x72x100"] = len(m.packers)
    return counts


def _cli_summary():
    model = build_model()
    print("Info:")
    for k, v in model.info.items():
        print(f"  {k:28s} {v}")
    print("Warnings:", model.warnings or "none")
    print("Parts:", len(model.parts), " Fasteners:", len(model.fasteners), " Packers:", len(model.packers))
    for r in cut_list(model):
        print(f"  {r['mark']:3s} {r['material']:7s} {r['length']:7.1f} x{r['qty']:2d}  {r['name']}")
    for b in optimise_cuts(model):
        print(f"  {b['material']} #{b['n']} {b['stock']}: {[x[:2] for x in b['pieces']]} left {b['remaining']:.0f}")
    print(fastener_counts(model))
    for kg in (0, 150, 300):
        for mod in module_names(model):
            st = stability(model, kg, mod)
            print(f"  total pots {kg:3d} kg, {mod} ({st['width']:.0f} wide, {st['pot_kg']:.0f} kg) -> "
                  f"tips ~{st['tip_gust_kmh']:.0f} km/h (self {st['self_kg']:.0f} kg)")


# ===========================================================================
# ===========================================================================
#  FUSION 360 BUILDER
# ===========================================================================
# ===========================================================================

import os
import traceback
import datetime

# adsk only exists inside Fusion.  Importing lazily keeps this file usable
# from plain Python (export_bom.py imports it for the spreadsheet).
try:
    import adsk.core
    import adsk.fusion
except ImportError:  # running outside Fusion
    adsk = None

# ---------------------------------------------------------------------------
# Script options  (edit these, or Config above, then re-run)
# ---------------------------------------------------------------------------
MM = 0.1                       # mm -> cm (Fusion's internal length unit)

CONFIG_OVERRIDES = {
    # Quick overrides without editing Config, e.g.
    # "lattice_thickness": 14.0,
    # "wall_height": 1010.0,
}

PARAMETRIC_TIMELINE = False    # False = Direct design (fast, most robust).
                               # True  = parametric with one base feature per part (slow).
BUILD_BENCH = True             # bench parts of each module
BUILD_SCREEN = True            # posts, rails, lattice, strips of each module
BUILD_FIXINGS = True           # bolt / screw / packer proxy bodies ("fixture points")
BUILD_WALL_REFERENCE = True    # grey wall solid for context (not built)
MODEL_LATTICE_SLATS = True     # diagonal slats (slower); False = flat sheet
CUT_BOLT_HOLES = True          # 11 mm holes through timber at every bolt
CUT_SCREW_PILOTS = False       # 3.5 mm pilots at every screw (slow)
ASK_ON_WARNINGS = True         # show layout warnings and ask before building

COLOURS = {
    "T90x45": (200, 137, 79),
    "D90x22": (185, 122, 69),
    "M42x19": (110, 59, 31),
    "LAT600": (226, 176, 122),
    "LAT900": (226, 176, 122),
    "WALL": (190, 190, 190),
    "BOLT_M10x120": (220, 30, 30),
    "BOLT_M10x150": (200, 70, 30),
    "SCREW_10Gx50": (30, 90, 220),
    "SCREW_10Gx65": (20, 160, 60),
    "SCREW_10Gx100": (140, 40, 180),
    "PACKER_10x72x100": (25, 25, 25),
}

FASTENER_FOLDER_NAMES = {
    "BOLT_M10x120": "M10x120 cup head bolts",
    "BOLT_M10x150": "M10x150 cup head bolts (doubled bearers)",
    "SCREW_10Gx50": "10G x 50 screws (deck boards)",
    "SCREW_10Gx65": "10G x 65 screws (cover strips)",
    "SCREW_10Gx100": "10G x 100 screws (rail fixings)",
}

_app = None
_ui = None
_design = None
_LOG_PATH = None


# ---------------------------------------------------------------------------
# Logging - so the script can never fail silently
# ---------------------------------------------------------------------------


def _log(msg):
    line = f"[BalconyScreenBench {datetime.datetime.now():%H:%M:%S}] {msg}"
    try:
        print(line)
    except Exception:
        pass
    try:
        if _app is not None:
            _app.log(line)          # appears in TEXT COMMANDS
    except Exception:
        pass
    try:
        if _LOG_PATH:
            with open(_LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _pt(p):
    """mm tuple -> Point3D (cm)."""
    return adsk.core.Point3D.create(p[0] * MM, p[1] * MM, p[2] * MM)


def temp_box(tbm, b):
    """Axis-aligned temporary BRep box from a Box (mm)."""
    dx, dy, dz = b.dims()
    centre = adsk.core.Point3D.create((b.x0 + b.x1) / 2 * MM,
                                      (b.y0 + b.y1) / 2 * MM,
                                      (b.z0 + b.z1) / 2 * MM)
    obb = adsk.core.OrientedBoundingBox3D.create(
        centre,
        adsk.core.Vector3D.create(1, 0, 0),   # length direction (X)
        adsk.core.Vector3D.create(0, 1, 0),   # width direction  (Y); height = Z
        dx * MM, dy * MM, dz * MM)
    return tbm.createBox(obb)


def temp_cylinder(tbm, p0, p1, dia):
    """Temporary cylinder between two mm points."""
    r = dia / 2 * MM
    return tbm.createCylinderOrCone(_pt(p0), r, _pt(p1), r)


def new_component(parent_comp, name):
    """Add an empty child component with an identity transform."""
    occ = parent_comp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = name
    return comp


def add_bodies(comp, temp_bodies, names=None, appearance=None):
    """Add temporary bodies to a component.
    Direct design: add straight in.  Parametric: wrap in one base feature."""
    if not temp_bodies:
        return []
    bodies = []
    if _design.designType == adsk.fusion.DesignTypes.ParametricDesignType:
        base = comp.features.baseFeatures.add()
        base.startEdit()
        for tb in temp_bodies:
            comp.bRepBodies.add(tb, base)
        base.finishEdit()
        bodies = [base.bodies.item(i) for i in range(base.bodies.count)]
    else:
        for tb in temp_bodies:
            bodies.append(comp.bRepBodies.add(tb))
    for i, body in enumerate(bodies):
        try:
            if names and i < len(names):
                body.name = names[i]
            if appearance is not None:
                body.appearance = appearance
        except Exception:
            pass  # cosmetic only
    return bodies


class Appearances:
    """Coloured appearances copied from a Fusion library appearance (best effort)."""

    LIB_ID = "BA5EE55E-9982-449B-9D66-9F036540E140"   # Fusion Appearance Library
    CANDIDATES = ("Plastic - Matte (Yellow)", "Paint - Enamel Glossy (Yellow)", "Plastic - Glossy (Yellow)")

    def __init__(self, app, design):
        self.design = design
        self.base = None
        self.cache = {}
        try:
            lib = app.materialLibraries.itemById(self.LIB_ID)
            if lib:
                for n in self.CANDIDATES:
                    a = lib.appearances.itemByName(n)
                    if a:
                        self.base = a
                        break
        except Exception:
            self.base = None
        if self.base is None:
            _log("Appearance library not found - bodies will use default colour")

    def get(self, key):
        if self.base is None or key not in COLOURS:
            return None
        if key in self.cache:
            return self.cache[key]
        name = f"BSB_{key}"
        try:
            ap = self.design.appearances.itemByName(name)
            if not ap:
                ap = self.design.appearances.addByCopy(self.base, name)
                r, g, b = COLOURS[key]
                for pid in ("opaque_albedo", "generic_diffuse"):
                    cprop = adsk.core.ColorProperty.cast(ap.appearanceProperties.itemById(pid))
                    if cprop:
                        cprop.value = adsk.core.Color.create(r, g, b, 0)
                        break
            self.cache[key] = ap
        except Exception:
            self.cache[key] = None
        return self.cache[key]


def lattice_body(tbm, part, cfg):
    """Lattice panel as two layers of slats clipped to the panel outline.
    square:   wall-side layer horizontal slats, balcony-side layer vertical slats
    diagonal: two layers at +/-45 degrees
    Falls back to a flat sheet if anything goes wrong."""
    b = part.box
    env = temp_box(tbm, b)
    if not MODEL_LATTICE_SLATS:
        return env
    try:
        w, t, h = b.dims()                 # X width, Y thickness, Z height
        layer_t = t / 2.0
        sw, pitch = cfg.lattice_slat_width, cfg.lattice_slat_pitch
        slats = []
        if cfg.lattice_pattern == "square":
            def centres(span):
                n = max(1, int((span - sw) // pitch) + 1)
                first = (span - (n - 1) * pitch) / 2.0   # symmetric margins
                return [first + i * pitch for i in range(n)]
            # layer 0 (against the strips / wall side): horizontal slats
            for zc in centres(h):
                slats.append(temp_box(tbm, Box(b.x0, b.x1, b.y0, b.y0 + layer_t,
                                               b.z0 + zc - sw / 2, b.z0 + zc + sw / 2)))
            # layer 1 (against the posts): vertical slats
            for xc in centres(w):
                slats.append(temp_box(tbm, Box(b.x0 + xc - sw / 2, b.x0 + xc + sw / 2,
                                               b.y0 + layer_t, b.y1, b.z0, b.z1)))
        else:
            s = 1 / math.sqrt(2)
            cx, cz = (b.x0 + b.x1) / 2, (b.z0 + b.z1) / 2
            diag = math.hypot(w, h) + 50
            n = int(math.ceil((w + h) * s / pitch / 2)) + 1
            for layer, sign in ((0, 1), (1, -1)):
                ymid = b.y0 + layer * layer_t + layer_t / 2
                length_dir = adsk.core.Vector3D.create(s, 0, sign * s)
                width_dir = adsk.core.Vector3D.create(-sign * s, 0, s)
                for k in range(-n, n + 1):
                    off = k * pitch
                    centre = adsk.core.Point3D.create((cx + width_dir.x * off) * MM, ymid * MM,
                                                      (cz + width_dir.z * off) * MM)
                    obb = adsk.core.OrientedBoundingBox3D.create(
                        centre, length_dir, width_dir, diag * MM, sw * MM, layer_t * MM)
                    slat = tbm.createBox(obb)
                    if tbm.booleanOperation(slat, tbm.copy(env),
                                            adsk.fusion.BooleanTypes.IntersectionBooleanType) \
                            and slat.volume > 1e-9:
                        slats.append(slat)
        if not slats:
            return env
        result = slats[0]
        for slat in slats[1:]:
            tbm.booleanOperation(result, slat, adsk.fusion.BooleanTypes.UnionBooleanType)
        return result
    except Exception:
        _log(f"Lattice slats failed for {part.pid}, using flat sheet:\n{traceback.format_exc()}")
        return env


def cut_fastener_holes(tbm, part, body, fasteners):
    """Subtract bolt holes (and optionally screw pilots) from a part body."""
    for f in fasteners:
        if f.kind.startswith("BOLT") and not CUT_BOLT_HOLES:
            continue
        if f.kind.startswith("SCREW") and not CUT_SCREW_PILOTS:
            continue
        if not any(part.box.contains(pt, tol=-0.5) for pt in _segment_samples(f, 30)):
            continue
        tool = temp_cylinder(tbm, f.head, f.tip, FASTENER_CATALOG[f.kind]["hole"])
        tbm.booleanOperation(body, tool, adsk.fusion.BooleanTypes.DifferenceBooleanType)
    return body


def _step(progress, msg):
    """Advance the progress dialog; returns False if cancelled."""
    if progress is None:
        return True
    try:
        progress.message = msg
        progress.progressValue = min(progress.progressValue + 1, progress.maximumValue)
        adsk.doEvents()
        return not progress.wasCancelled
    except Exception:
        return True


SECTION_LABEL = {"T90x45": "90x45 pine", "D90x22": "90x22 decking", "M42x19": "42x19 merbau"}


def cutting_labels(model):
    """Map each part id to the stock length it is cut from, using the same
    optimised cutting plan as Cutting_Guide.pdf and the spreadsheet, so the
    Fusion browser and the printed diagram use the same numbers."""
    where = {}
    for b in optimise_cuts(model):
        for mark, length, pid in b["pieces"]:
            where[pid] = b["n"]
    return where


def fusion_name(text):
    """Component names can't contain some characters (e.g. / and :)."""
    for bad, good in ((" / ", ", "), ("/", "-"), (":", " "), ("\\", "-"), ("*", ""), ("?", ""),
                      ('"', ""), ("<", ""), (">", ""), ("|", "-")):
        text = text.replace(bad, good)
    return " ".join(text.split())


def part_label(p, cut_n):
    """Name shown in the Fusion browser, matching the cutting diagram label:
    mark, length, part name, then which numbered stock length it comes from."""
    if p.material.startswith("LAT"):
        return fusion_name(f"{p.name} - whole sheet, not cut")
    n = cut_n.get(p.pid)
    where = f" - {SECTION_LABEL.get(p.material, p.material)} length #{n}" if n else ""
    return fusion_name(f"{p.mark} {p.length:.0f} - {p.name}{where}")


def build_module(root, tbm, model, mod, apps, progress, cut_n=None):
    """One top-level component per independent module, containing a component
    per timber part and its own Fixings sub-component, so each module can be
    moved, hidden or exported on its own."""
    parts = [p for p in model.parts if p.module == mod]
    lat = next(p for p in parts if p.material.startswith("LAT"))
    width = lat.box.x1 - lat.box.x0
    mod_comp = new_component(root, f"Module {mod[1:]} - {width:.0f} wide")
    mod_fixings = [f for f in model.fasteners if f.module == mod]
    _log(f"Building module {mod}: {len(parts)} parts, {len(mod_fixings)} fixings")

    for p in parts:
        if not BUILD_BENCH and p.group == "Bench":
            continue
        if not BUILD_SCREEN and p.group == "Screen":
            continue
        if not _step(progress, f"{mod}: {p.pid}"):
            return False
        if p.material.startswith("LAT"):
            body = lattice_body(tbm, p, model.cfg)
        else:
            body = cut_fastener_holes(tbm, p, temp_box(tbm, p.box), mod_fixings)
        # Named like the cutting diagram: "A 1810 - Screen post / rear bench leg - 90x45 pine length #3"
        comp = new_component(mod_comp, part_label(p, cut_n or {}))
        try:
            comp.description = (f"{p.name} | {CATALOG[p.material]['desc']} | L={p.length:.1f} mm"
                                f" | part id {p.pid}")
        except Exception:
            pass
        body_name = p.name if p.material.startswith("LAT") else f"{p.mark} {p.length:.0f} {mod}"
        add_bodies(comp, [body], [fusion_name(body_name)], apps.get(p.material))

    if BUILD_FIXINGS:
        fix = new_component(mod_comp, "Fixings")
        by_kind = {}
        for f in mod_fixings:
            by_kind.setdefault(f.kind, []).append(f)
        for kind, items in by_kind.items():
            comp = new_component(fix, f"{FASTENER_FOLDER_NAMES.get(kind, kind)} ({len(items)})")
            add_bodies(comp, [temp_cylinder(tbm, f.head, f.tip, f.dia) for f in items],
                       [f.fid for f in items], apps.get(kind))
        packers = [k for k in model.packers if k.module == mod]
        if packers:
            comp = new_component(fix, f"Foot packers 10x72x100 ({len(packers)})")
            add_bodies(comp, [temp_box(tbm, k.box) for k in packers],
                       [k.pid for k in packers], apps.get("PACKER_10x72x100"))
    return True


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def run(context):
    global _app, _ui, _design, _LOG_PATH
    progress = None
    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface
        try:
            _LOG_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                     "BalconyScreenBench_log.txt")
        except Exception:
            _LOG_PATH = None
        _log("Script started")

        cfg = Config(**CONFIG_OVERRIDES)
        model = build_model(cfg)
        _log(f"Layout OK: {len(model.parts)} parts, {len(model.fasteners)} fixings, "
             f"{len(model.warnings)} warnings")
        for w in model.warnings:
            _log("WARNING: " + w)

        if model.warnings and ASK_ON_WARNINGS:
            res = _ui.messageBox("Layout warnings:\n\n" + "\n\n".join(model.warnings[:10]) +
                                 "\n\nBuild the model anyway?", "Balcony screen",
                                 adsk.core.MessageBoxButtonTypes.YesNoButtonType,
                                 adsk.core.MessageBoxIconTypes.WarningIconType)
            if res != adsk.core.DialogResults.DialogYes:
                _log("Cancelled at warnings dialog")
                return

        # New document so nothing existing is modified
        doc = _app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        _design = adsk.fusion.Design.cast(_app.activeProduct)
        _design.designType = (adsk.fusion.DesignTypes.ParametricDesignType if PARAMETRIC_TIMELINE
                              else adsk.fusion.DesignTypes.DirectDesignType)
        try:
            _design.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        except Exception:
            pass
        root = _design.rootComponent
        tbm = adsk.fusion.TemporaryBRepManager.get()
        apps = Appearances(_app, _design)
        cut_n = cutting_labels(model)       # part id -> stock length number, as in Cutting_Guide.pdf
        _log("New design created (" + ("parametric" if PARAMETRIC_TIMELINE else "direct") + ")")

        progress = _ui.createProgressDialog()
        progress.cancelButtonText = "Cancel"
        progress.isBackgroundTranslucent = False
        progress.show("Building balcony screen", "Starting...", 0, len(model.parts) + 10, 0)
        adsk.doEvents()

        if BUILD_WALL_REFERENCE and model.wall_ref is not None:
            wall = new_component(root, "REF Balcony wall (not built)")
            add_bodies(wall, [temp_box(tbm, model.wall_ref)], ["Wall"], apps.get("WALL"))

        ok = True
        for mod in module_names(model):
            if not ok:
                break
            ok = build_module(root, tbm, model, mod, apps, progress, cut_n)

        progress.hide()
        progress = None
        try:
            _app.activeViewport.fit()
        except Exception:
            pass

        counts = fastener_counts(model)
        summary = (
            f"{'Built' if ok else 'Cancelled part way'}.\n\n"
            f"{model.info['n_modules']} independent modules, {model.unit_length:.0f} long overall "
            f"({cfg.module_gap:.0f} mm gaps) x {model.info['bench_depth_from_wall']:.0f} deep, "
            f"{model.info['overall_height']:.0f} high\n"
            f"({model.x_offset:.0f} mm clear each end of a {cfg.wall_length:.0f} mm wall)\n"
            f"Timber parts: {len(model.parts)}\n"
            + "\n".join(f"  {k}: {v}" for k, v in counts.items())
            + f"\n\nEstimated tipping gust (worst module {model.info['worst_module']}, "
              f"{cfg.design_pot_kg:.0f} kg of pots in total): ~{model.info['tip_gust_kmh']:.0f} km/h"
        )
        _log(summary.replace("\n", " | "))
        _ui.messageBox(summary, "Balcony screen")

    except Exception:
        err = traceback.format_exc()
        _log("FAILED:\n" + err)
        try:
            if progress is not None:
                progress.hide()
        except Exception:
            pass
        if _ui:
            _ui.messageBox("BalconyScreenBench failed:\n\n" + err)


def stop(context):
    pass


if __name__ == "__main__" and adsk is None:
    _cli_summary()
