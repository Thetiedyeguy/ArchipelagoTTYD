import typing
import json
import pkgutil
from collections import defaultdict, deque

from BaseClasses import Region
from .Locations import TTYDLocation, shadow_queen, LocationData
from . import StateLogic, get_locations_by_tags, Goal
from .Rules import _build_single_rule
from rule_builder.rules import Has, True_, CanReachRegion, CanReachLocation

if typing.TYPE_CHECKING:
    from . import TTYDWorld


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class RegionState:
    """Holds all mutable state used during region-connection graph construction."""

    def __init__(self):
        # Maps region name → list of zone dicts that originate from that region
        self.zones_by_region: dict[str, list[dict]] = defaultdict(list)
        # Directed adjacency list representing traversable region connections
        self.region_graph: dict[str, set[str]] = defaultdict(set)
        # Zone names that have already been assigned to a connection
        self.used_zones: set[str] = set()
        # Edge → set of region names the edge depends on (for deferred resolution)
        self.edge_dependencies: dict[tuple[str, str], set[str]] = {}
        # Regions excluded from reachability requirements (e.g. skipped chapters)
        self.unneeded_regions: set[str] = set()


# ---------------------------------------------------------------------------
# JSON loaders
# ---------------------------------------------------------------------------

def get_region_defs_from_json() -> list[dict]:
    """Load and return the list of region definitions from regions.json."""
    raw = pkgutil.get_data(__name__, "json/regions.json")
    if raw is None:
        raise FileNotFoundError("json/regions.json not found in apworld")
    return json.loads(raw.decode("utf-8"))


def get_zone_dict_from_json() -> dict[str, dict]:
    """Load zones.json and return a dict keyed by zone name."""
    raw = pkgutil.get_data(__name__, "json/zones.json")
    if raw is None:
        raise FileNotFoundError("json/zones.json not found in apworld")
    zone_defs = json.loads(raw.decode("utf-8"))
    return {z["name"]: z for z in zone_defs}


# ---------------------------------------------------------------------------
# Region / connection definitions
# ---------------------------------------------------------------------------

def get_regions_dict() -> dict[str, list[LocationData]]:
    """Return a mapping of region name → list of LocationData for that region."""
    return {
        "Rogueport":                               get_locations_by_tags("rogueport"),
        "Rogueport (Westside)":                    get_locations_by_tags("rogueport_westside"),
        "Rogueport Sewers":                        get_locations_by_tags("sewers"),
        "Rogueport Sewers Westside":               get_locations_by_tags("sewers_westside"),
        "Rogueport Sewers Westside Ground":        get_locations_by_tags("sewers_westside_ground"),
        "Petal Meadows (Left)":                    get_locations_by_tags("petal_left"),
        "Petal Meadows (Right)":                   get_locations_by_tags("petal_right"),
        "Hooktail's Castle":                       get_locations_by_tags("hooktails_castle"),
        "Boggly Woods":                            get_locations_by_tags("boggly_woods"),
        "Great Tree":                              get_locations_by_tags("great_tree"),
        "Glitzville":                              get_locations_by_tags("glitzville"),
        "Twilight Town":                           get_locations_by_tags("twilight_town"),
        "Twilight Trail":                          get_locations_by_tags("twilight_trail"),
        "Creepy Steeple":                          get_locations_by_tags("creepy_steeple"),
        "Keelhaul Key":                            get_locations_by_tags("keelhaul_key"),
        "Pirate's Grotto":                         get_locations_by_tags("pirates_grotto"),
        "Excess Express":                          get_locations_by_tags("excess_express"),
        "Riverside Station":                       get_locations_by_tags("riverside"),
        "Poshley Heights":                         get_locations_by_tags("poshley_heights"),
        "Fahr Outpost":                            get_locations_by_tags("fahr_outpost"),
        "X-Naut Fortress":                         get_locations_by_tags("xnaut_fortress"),
        "Palace of Shadow":                        get_locations_by_tags("palace"),
        "Palace of Shadow (Post-Riddle Tower)":    get_locations_by_tags("riddle_tower"),
        "Pit of 100 Trials":                       get_locations_by_tags("pit"),
        "Shadow Queen":                            shadow_queen,
        "Tattlesanity":                            get_locations_by_tags("tattle"),
    }


def get_region_connections_dict(world: "TTYDWorld") -> dict[tuple[str, str], typing.Any]:
    """
    Return all hard-coded region connections and their access rules.

    Keys are (source_region, target_region) tuples. Values are rule objects
    (True_() means always accessible). These connections are independent of
    loading-zone shuffle — they represent in-map traversal logic.
    """
    return {
        # --- Menu / top-level ---
        ("Menu", "Rogueport Center"):                                   True_(),
        ("Menu", "Tattlesanity"):                                       True_(),

        # --- Rogueport West ---
        ("Rogueport West Tall Pipe", "Rogueport West"):                 True_(),

        # --- Rogueport Sewers East ---
        ("Rogueport Sewers East", "Rogueport Sewers East Bobbery Pipe"):        Has("Bobbery"),
        ("Rogueport Sewers East Bobbery Pipe", "Rogueport Sewers East"):        Has("Bobbery"),
        ("Rogueport Sewers East", "Rogueport Sewers East Fortune Pipe"):        Has("Paper Mode"),
        ("Rogueport Sewers East Fortune Pipe", "Rogueport Sewers East"):        True_(),
        ("Rogueport Sewers East", "Rogueport Sewers East Plane Mode"):          Has("Plane Mode"),
        ("Rogueport Sewers East Plane Mode", "Rogueport Sewers East"):          True_(),
        ("Rogueport Sewers East Top", "Rogueport Sewers East"):                 True_(),
        ("Rogueport Sewers East Top", "Rogueport Sewers East Fortune Pipe"):    Has("Yoshi"),
        ("Rogueport Sewers East Top", "Rogueport Sewers East Plane Mode"):      True_(),

        # --- Rogueport Sewers Blooper ---
        ("Rogueport Sewers Blooper", "Rogueport Sewers Blooper Pipe"):          True_(),

        # --- Rogueport Sewers Town ---
        ("Rogueport Sewers Town", "Rogueport Sewers Town Dazzle"):              StateLogic.fallen_pipe(),
        ("Rogueport Sewers Town Dazzle", "Rogueport Sewers Town"):              StateLogic.fallen_pipe(),
        ("Rogueport Sewers Town Teleporter", "Rogueport Sewers Town"):          True_(),
        ("Rogueport Sewers Town", "Rogueport Sewers Town Teleporter"):          True_(),

        # --- Rogueport Sewers West ---
        ("Rogueport Sewers West", "Rogueport Sewers West West"):                Has("Yoshi"),
        ("Rogueport Sewers West West", "Rogueport Sewers West"):                Has("Yoshi"),
        ("Rogueport Sewers West", "Rogueport Sewers West Bottom"):              True_(),
        ("Rogueport Sewers West West", "Rogueport Sewers West Bottom"):         True_(),
        ("Rogueport Sewers West Bottom", "Rogueport Sewers West West"):         StateLogic.ultra_boots(),
        ("Rogueport Sewers West West", "Rogueport Sewers West Fahr"):           StateLogic.ultra_hammer(),
        ("Rogueport Sewers West Fahr", "Rogueport Sewers West West"):           StateLogic.ultra_hammer(),

        # --- Rogueport Sewers Enemy Halls ---
        ("Rogueport Sewers East Enemy Hall", "Rogueport Sewers East Enemy Hall Barred Door"):   Has("Paper Mode"),
        ("Rogueport Sewers East Enemy Hall Barred Door", "Rogueport Sewers East Enemy Hall"):   Has("Paper Mode"),
        ("Rogueport Sewers West Enemy Hall", "Rogueport Sewers West Enemy Hall Flurrie"):       Has("Flurrie"),
        ("Rogueport Sewers West Enemy Hall Flurrie", "Rogueport Sewers West Enemy Hall"):       Has("Flurrie"),

        # --- Rogueport Sewers Warp Rooms ---
        # West warp room — Ultra Hammer needed to move between left/right; top always drops down
        ("Rogueport Sewers West Warp Room Left", "Rogueport Sewers West Warp Room Right"):      StateLogic.ultra_hammer(),
        ("Rogueport Sewers West Warp Room Right", "Rogueport Sewers West Warp Room Left"):      StateLogic.ultra_hammer(),
        ("Rogueport Sewers West Warp Room Left", "Rogueport Sewers West Warp Room Top"):        StateLogic.ultra_hammer(),
        ("Rogueport Sewers West Warp Room Top", "Rogueport Sewers West Warp Room Left"):        True_(),
        ("Rogueport Sewers West Warp Room Right", "Rogueport Sewers West Warp Room Top"):       StateLogic.ultra_hammer(),
        ("Rogueport Sewers West Warp Room Top", "Rogueport Sewers West Warp Room Right"):       True_(),
        # East warp room — identical layout/rules to west
        ("Rogueport Sewers East Warp Room Left", "Rogueport Sewers East Warp Room Right"):      StateLogic.ultra_hammer(),
        ("Rogueport Sewers East Warp Room Right", "Rogueport Sewers East Warp Room Left"):      StateLogic.ultra_hammer(),
        ("Rogueport Sewers East Warp Room Left", "Rogueport Sewers East Warp Room Top"):        StateLogic.ultra_hammer(),
        ("Rogueport Sewers East Warp Room Top", "Rogueport Sewers East Warp Room Left"):        True_(),
        ("Rogueport Sewers East Warp Room Right", "Rogueport Sewers East Warp Room Top"):       StateLogic.ultra_hammer(),
        ("Rogueport Sewers East Warp Room Top", "Rogueport Sewers East Warp Room Right"):       True_(),

        # --- Rogueport Black Key Room ---
        ("Rogueport Sewers Black Key Room", "Rogueport Sewers Black Key Room Puni Door"):       Has("Paper Mode"),
        ("Rogueport Sewers Black Key Room Puni Door", "Rogueport Sewers Black Key Room"):       Has("Paper Mode"),

        # --- Rogueport Second Chapter Entrance Room ---
        ("Rogueport Sewers Puni Room", "Rogueport Sewers Puni Room Exit"):                      True_(),

        # --- Entering the Pit (Pit not Randomized) ---
        ("Rogueport Sewers Pit Room", "Pit of 100 Trials"):                                     StateLogic.pit(),

        # --- Petal Meadows ---
        ("Petal Meadows Bridge West", "Petal Meadows Bridge East"):             True_(),

        # --- Hooktail's Castle ---
        # Drawbridge: Yoshi can cross bottom level eastward; plane glides west from top
        ("Hooktail's Castle Drawbridge East Bottom", "Hooktail's Castle Drawbridge West Bottom"):   Has("Yoshi"),
        ("Hooktail's Castle Drawbridge West Bottom", "Hooktail's Castle Drawbridge East Bottom"):   True_(),
        ("Hooktail's Castle Drawbridge East Top", "Hooktail's Castle Drawbridge East Bottom"):      True_(),
        ("Hooktail's Castle Drawbridge East Top", "Hooktail's Castle Drawbridge West Bottom"):      Has("Plane Mode"),
        ("Hooktail's Castle Drawbridge West Top", "Hooktail's Castle Drawbridge West Bottom"):      True_(),
        ("Hooktail's Castle Stair Switch Room Upper Level", "Hooktail's Castle Stair Switch Room"): True_(),
        ("Hooktail's Castle Life Shroom Room", "Hooktail's Castle Life Shroom Room Upper Level"):   StateLogic.partner_press_switch(),
        ("Hooktail's Castle Life Shroom Room Upper Level", "Hooktail's Castle Life Shroom Room"): True_(),
        ("Hooktail's Castle Central Staircase Upper Level", "Hooktail's Castle Central Staircase"): True_(),

        # --- Boggly Woods ---
        ("Boggly Woods Plane Panel Room", "Boggly Woods Plane Panel Room Upper"):                   Has("Plane Mode"),
        ("Boggly Woods Plane Panel Room Upper", "Boggly Woods Plane Panel Room"):                   True_(),
        ("Boggly Woods Outside Flurrie's House", "Boggly Woods Outside Flurrie's House Grass Area"):       Has("Paper Mode"),
        ("Boggly Woods Outside Flurrie's House Grass Area", "Boggly Woods Outside Flurrie's House"):       Has("Paper Mode"),

        # --- Glitzville ---
        ("Glitzville Promoter's Office Vent", "Glitzville Promoter's Office"):  True_(),

        # --- Creepy Steeple ---
        ("Creepy Steeple Main Hall Upper", "Creepy Steeple Main Hall"):         True_(),
        ("Creepy Steeple Main Hall Upper South", "Creepy Steeple Main Hall"):   True_(),
        ("Creepy Steeple Well Buzzy Room", "Creepy Steeple Well Buzzy Room Vivian"): Has("Vivian"),

        # --- Pirate's Grotto ---
        ("Pirate's Grotto Handle Room Canal", "Pirate's Grotto Handle Room"):           Has("Boat Mode"),
        ("Pirate's Grotto Sluice Gate Upper", "Pirate's Grotto Sluice Gate Upper Canal"):       Has("Boat Mode"),
        ("Pirate's Grotto Sluice Gate Upper Canal", "Pirate's Grotto Sluice Gate Upper"):       Has("Boat Mode"),
        ("Pirate's Grotto Sluice Gate Upper Canal", "Pirate's Grotto Sluice Gate Canal"):       True_(),
        ("Pirate's Grotto Toad Boat Room", "Pirate's Grotto Toad Boat Room East"): Has("Boat Mode") & Has("Plane Mode"),
        ("Pirate's Grotto Toad Boat Room East", "Pirate's Grotto Toad Boat Room"):  Has("Boat Mode"),

        # --- Riverside Station ---
        ("Riverside Station Ultra Boots Room Upper", "Riverside Station Ultra Boots Room"): True_(),

        # --- Excess Express ---
        # Storage Car West is unlocked only after completing a chain of story prerequisites
        ("Excess Express Storage Car", "Excess Express Storage Car West"):
            CanReachRegion("Riverside Station Entrance")
            & Has("Elevator Key (Station)")
            & CanReachRegion("Excess Express Middle Passenger Car")
            & CanReachLocation("Excess Express Middle Passenger Car: Briefcase")
            & CanReachRegion("Excess Express Locomotive")
            & CanReachRegion("Excess Express Back Passenger Car")
            & CanReachRegion("Excess Express Front Passenger Car"),
        ("Excess Express Storage Car West", "Excess Express Storage Car"):  True_(),

        # --- X-Naut Fortress elevators ---
        # Elevator Key 1 covers floors G/B1/B2; Elevator Key 2 covers B2/B3/B4
        ("X-Naut Fortress Hall Ground Floor", "X-Naut Fortress Hall Sublevel One"):    Has("Elevator Key 1"),
        ("X-Naut Fortress Hall Sublevel One", "X-Naut Fortress Hall Ground Floor"):    Has("Elevator Key 1"),
        ("X-Naut Fortress Hall Ground Floor", "X-Naut Fortress Hall Sublevel Two"):    Has("Elevator Key 1"),
        ("X-Naut Fortress Hall Sublevel One", "X-Naut Fortress Hall Sublevel Two"):    Has("Elevator Key 1"),
        ("X-Naut Fortress Hall Sublevel Two", "X-Naut Fortress Hall Sublevel One"):    Has("Elevator Key 1"),
        ("X-Naut Fortress Hall Sublevel Two", "X-Naut Fortress Hall Sublevel Three"):  Has("Elevator Key 2"),
        ("X-Naut Fortress Hall Sublevel Three", "X-Naut Fortress Hall Sublevel Two"):  Has("Elevator Key 2"),
        ("X-Naut Fortress Hall Sublevel Two", "X-Naut Fortress Hall Sublevel Four"):   Has("Elevator Key 2"),
        ("X-Naut Fortress Hall Sublevel Four", "X-Naut Fortress Hall Sublevel Two"):   Has("Elevator Key 2"),
        ("X-Naut Fortress Hall Sublevel Three", "X-Naut Fortress Hall Sublevel Four"): Has("Elevator Key 2"),
        ("X-Naut Fortress Hall Sublevel Four", "X-Naut Fortress Hall Sublevel Three"): Has("Elevator Key 2"),

        # --- Palace of Shadow ---
        # Each Far Hallway has a post Riddle Tower variant
        ("Palace of Shadow Far Hallway One", "Palace of Shadow Far Hallway One Post Riddle Tower"): StateLogic.riddle_tower(),
        ("Palace of Shadow Far Hallway 2",   "Palace of Shadow Far Hallway 2 Post Riddle"):         StateLogic.riddle_tower(),
        ("Palace of Shadow Far Hallway 3",   "Palace of Shadow Far Hallway 3 Post Riddle"):         StateLogic.riddle_tower(),
        ("Palace of Shadow Far Hallway 4",   "Palace of Shadow Far Hallway 4 Post Riddle"):         StateLogic.riddle_tower(),
        ("Palace of Shadow Far Backroom 2",     "Palace of Shadow Far Backroom 2 Top"):             Has("Bobbery"),
        ("Palace of Shadow Far Backroom 2 Top", "Palace of Shadow Far Backroom 2"):                 True_(),
        # Final staircase → Shadow Queen (standard route)
        ("Palace of Shadow Final Staircase", "Shadow Queen"):
            StateLogic.PalaceAccess(world.options.goal_stars.value),
        # Direct TTYD → Shadow Queen shortcut used when palace_skip is enabled
        ("TTYD", "Shadow Queen"):
            StateLogic.PalaceAccess(world.options.goal_stars.value),
    }


# ---------------------------------------------------------------------------
# Region creation
# ---------------------------------------------------------------------------

def create_regions(world: "TTYDWorld") -> None:
    """
    Create all Archipelago Region objects for the TTYD world.

    The Menu region is always created. All other regions come from regions.json.
    Regions belonging to excluded chapters (or chapter 8 when palace_skip is on)
    are skipped and their locations added to disabled_locations instead.
    """
    menu_region = Region("Menu", world.player, world.multiworld)
    world.multiworld.regions.append(menu_region)

    for region in get_region_defs_from_json():
        name = region["name"]
        tag = region["tag"]
        locations = get_locations_by_tags(tag)

        skip = name in world.excluded_regions or (world.options.palace_skip and region["chapter"] == "Eight")
        if skip:
            # Collect disabled locations so items are not placed here
            world.disabled_locations.update(
                loc.name for loc in locations if loc.name not in world.disabled_locations
            )
        else:
            create_region(world, name, locations)


def create_region(world: "TTYDWorld", name: str, locations: list[LocationData]) -> None:
    """Create a single Region and register it with the multiworld."""
    reg = Region(name, world.player, world.multiworld)
    reg.add_locations(
        {loc.name: loc.id for loc in locations if loc.name not in world.disabled_locations},
        TTYDLocation,
    )
    world.multiworld.regions.append(reg)


# ---------------------------------------------------------------------------
# Region connections (loading-zone graph)
# ---------------------------------------------------------------------------

# Chapter names in order; index corresponds to chapter number (0 = Prologue)
_CHAPTERS = ["Prologue", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight"]

# Palace of Shadow sub-regions that must be bypassed when palace_skip is active
_PALACE_REGIONS = [
    "Palace of Shadow Far Hallway One", "Palace of Shadow Far Hallway One Post Riddle Tower",
    "Palace of Shadow Far Hallway 2",   "Palace of Shadow Far Hallway 2 Post Riddle",
    "Palace of Shadow Far Hallway 3",   "Palace of Shadow Far Hallway 3 Post Riddle",
    "Palace of Shadow Far Hallway 4",   "Palace of Shadow Far Hallway 4 Post Riddle",
    "Palace of Shadow Far Backroom 2",  "Palace of Shadow Far Backroom 2 Top",
    "Palace of Shadow Final Staircase",
]

# Regions that are never required to be reachable during the first traversal step regardless of settings
_ALWAYS_UNNEEDED = {"Tattlesanity", "Palace of Shadow", "Palace of Shadow (Post-Riddle Tower)", "Shadow Queen"}

# Excess Express Storage Car dependencies (regions that must be reachable first)
_STORAGE_CAR_DEPS = [
    "Riverside Station Entrance",
    "Excess Express Middle Passenger Car",
    "Excess Express Locomotive",
    "Excess Express Back Passenger Car",
    "Excess Express Front Passenger Car",
]


def connect_regions(world: "TTYDWorld") -> None:
    """
    Build the full loading-zone connection graph for the TTYD world.

    Connections fall into four categories processed in order:
      1. Vanilla  — fixed connections unchanged by loading-zone shuffle.
      2. One-way  — cyclic chain of one-directional warps (e.g. grates).
      3. Dungeon  — paired entrance/exit swaps when dungeon_shuffle is on.
      4. Generic  — bidirectional zone pairs placed to ensure full reachability.

    Connections whose access rule references an as-yet-unreached region are
    deferred and resolved once that region becomes reachable.
    """
    # Initialize the state and retrieve general zone/region information
    state = RegionState()
    zones = get_zone_dict_from_json()
    tag_to_region = get_region_name_by_tag()

    # Bucket zones by category during the initial pass
    one_way: list[dict] = []
    vanilla: list[dict] = []
    dungeon_entrance: list[dict] = []
    dungeon_exit: list[dict] = []
    ttyd_north_zone = None  # Deferred: injected into the remaining pool at the end

    # Connections whose rules depend on a region that isn't yet reachable
    delayed_connections: dict[str, list] = defaultdict(list)

    connections_dict = get_region_connections_dict(world)
    reachable_regions = {"Menu", "Rogueport Center"}

    # ------------------------------------------------------------------
    # Step 1 — Wire up hard-coded (non-zone) region connections
    # ------------------------------------------------------------------
    for (source, target), rule in connections_dict.items():
        # Skip connections involving excluded regions
        if source in world.excluded_regions or target in world.excluded_regions:
            continue
        # TTYD → Shadow Queen shortcut is only used when palace_skip is enabled
        if source == "TTYD" and target == "Shadow Queen" and not world.options.palace_skip:
            continue
        # Palace sub-regions are bypassed entirely when palace_skip is on
        if world.options.palace_skip and (source in _PALACE_REGIONS or target in _PALACE_REGIONS):
            continue

        source_region = world.multiworld.get_region(source, world.player)
        target_region = world.multiworld.get_region(target, world.player)
        world.create_entrance(source_region, target_region, rule)

        # Track the Storage Car's special region dependencies in the graph
        if source == "Excess Express Storage Car" and target == "Excess Express Storage Car West":
            add_edge(state, source, target, _STORAGE_CAR_DEPS)
        else:
            add_edge(state, source, target)

    # ------------------------------------------------------------------
    # Step 2 — Mark which regions are unneeded (out-of-scope chapters)
    # ------------------------------------------------------------------
    for region in get_region_defs_from_json():
        chapter = region.get("chapter")
        in_limited = chapter and chapter in _CHAPTERS and _CHAPTERS.index(chapter) in world.limited_chapters
        skipped_palace = world.options.palace_skip and chapter == "Eight"
        if in_limited or skipped_palace:
            state.unneeded_regions.add(region["name"])

    state.unneeded_regions.update(_ALWAYS_UNNEEDED)

    # ------------------------------------------------------------------
    # Step 3 — Categorise zones from zones.json
    # ------------------------------------------------------------------
    all_regions = set(tag_to_region.values())

    for z in zones.values():
        limited_zone = any(
            tag in _CHAPTERS and _CHAPTERS.index(tag) in world.limited_chapters
            for tag in z["tags"]
        )
        if world.options.palace_skip and any(tag == "Eight" for tag in z["tags"]):
            continue  # Entire palace chapter omitted for palace skip

        is_vanilla = "vanilla" in z["tags"] or not world.options.loading_zone_shuffle or limited_zone
        if is_vanilla:
            vanilla.append(z)
        elif world.options.dungeon_shuffle and any(tag == "Dungeon Entrance" for tag in z["tags"]):
            dungeon_entrance.append(z)
        elif world.options.dungeon_shuffle and any(tag == "Dungeon Exit" for tag in z["tags"]):
            dungeon_exit.append(z)
        elif z["target"] == "One Way":
            one_way.append(z)
        elif z["name"] == "TTYD - North":
            # Save for injection into the remaining-zones pool after all others are placed
            ttyd_north_zone = z
        else:
            region = tag_to_region.get(z["region"])
            state.zones_by_region[region].append(z)

    # ------------------------------------------------------------------
    # Step 4 — Wire vanilla connections
    # ------------------------------------------------------------------
    for src in vanilla:
        if src["target"] not in ("", "One Way", "filler"):
            dst = zones[src["target"]]
            src_region = tag_to_region[src["region"]]
            dst_region = tag_to_region[dst["region"]]
            rule_dict = src.get("rules")
            rule = build_rule_lambda(rule_dict, world)
            region_deps = has_region_dependency(world, rule_dict)

            if region_deps and world.options.loading_zone_shuffle:
                # Defer until the dependent regions become reachable
                for dep in region_deps:
                    delayed_connections[dep].append([region_deps, src, dst])
                continue

            source_region = world.multiworld.get_region(src_region, world.player)
            target_region = world.multiworld.get_region(dst_region, world.player)
            world.create_entrance(source_region, target_region, rule, dst["name"])
            if "Chapter Edge" not in src["tags"]:
                add_edge(state, src_region, dst_region, region_deps)
            mark_used(state, src, dst)

        elif src["target"] == "One Way":
            # One-way vanilla connections go from src_region → region (not dst)
            source = tag_to_region.get(src["src_region"])
            target = tag_to_region.get(src["region"])
            rule = build_rule_lambda(src.get("rules"), world)
            source_region = world.multiworld.get_region(source, world.player)
            target_region = world.multiworld.get_region(target, world.player)
            add_edge(state, source, target)
            world.create_entrance(source_region, target_region, rule, src["name"])

    # ------------------------------------------------------------------
    # Step 5 — Wire one-way cyclic connections
    # ------------------------------------------------------------------
    # Shuffle until no zone connects back to itself or hits forbidden pairs
    for attempt in range(1000):
        world.multiworld.random.shuffle(one_way)
        if is_valid_one_way_arrangement(one_way):
            break
    else:
        raise RuntimeError("Could not find a valid one_way arrangement after 1000 attempts")

    for i, a in enumerate(one_way):
        b = one_way[(i + 1) % len(one_way)]  # Cyclic wrap

        world.warp_table[(a["map"], a["bero"])] = (b["map"], b["bero"])
        source = tag_to_region.get(a["src_region"])
        target = tag_to_region.get(b["region"])
        rule_dict = a.get("rules")
        rule = build_rule_lambda(rule_dict, world)
        region_deps = has_region_dependency(world, rule_dict)

        if region_deps:
            for dep in region_deps:
                delayed_connections[dep].append([region_deps, a, b])
            continue

        source_region = world.multiworld.get_region(source, world.player)
        target_region = world.multiworld.get_region(target, world.player)
        add_edge(state, source, target)
        world.create_entrance(source_region, target_region, rule, b["name"])

    # ------------------------------------------------------------------
    # Step 6 — Wire dungeon entrance/exit pairs (shuffled if option is on)
    # ------------------------------------------------------------------
    world.multiworld.random.shuffle(dungeon_entrance)

    for src, dst in zip(dungeon_entrance, dungeon_exit):
        src_region = tag_to_region[src["region"]]
        dst_region = tag_to_region[dst["region"]]

        src_target = zones[src["target"]]
        dst_target = zones[dst["target"]]

        src_rule = build_rule_lambda(src.get("rules"), world)
        dst_rule = build_rule_lambda(dst.get("rules"), world)

        world.warp_table[(src_target["map"], src_target["bero"])] = (dst["map"], dst["bero"])
        world.warp_table[(dst_target["map"], dst_target["bero"])] = (src["map"], src["bero"])

        source_region = world.multiworld.get_region(src_region, world.player)
        target_region = world.multiworld.get_region(dst_region, world.player)

        world.create_entrance(source_region, target_region, src_rule, dst["name"])
        world.create_entrance(target_region, source_region, dst_rule, src["name"])

        add_edge(state, src_region, dst_region)
        add_edge(state, dst_region, src_region)

    # ------------------------------------------------------------------
    # Step 7 — Iteratively connect unreached regions via generic zones
    # ------------------------------------------------------------------
    # Allows for improbable failures to happen and to continue attempting to connect regions
    # Can hopefully be removed at the end but has been helpful for testing purposes
    consecutive_failures = 0
    max_consecutive_failures = 50

    reachable_regions = compute_reachable(state, "Menu")
    unreached_regions = all_regions - reachable_regions - state.unneeded_regions

    def _dst_contenders(unreached, used):
        """Zones in unreached regions with no unresolved rule dependencies."""
        return [
            z for r in unreached for z in state.zones_by_region[r]
            if z["name"] not in used
            and not any(dep in unreached for dep in has_region_dependency(world, z.get("rules")))
        ]

    def _src_contenders(reachable, unreached, used):
        """Zones in reachable regions with no unresolved rule dependencies."""
        return [
            z for r in reachable for z in state.zones_by_region[r]
            if z["name"] not in used
            and not any(dep in unreached for dep in has_region_dependency(world, z.get("rules")))
        ]

    dst_contenders = _dst_contenders(unreached_regions, state.used_zones)
    src_contenders = _src_contenders(reachable_regions, unreached_regions, state.used_zones)

    while unreached_regions:
        if not dst_contenders:
            # No valid destinations remain; give up after too many failures
            if consecutive_failures > max_consecutive_failures:
                print("WARNING: Could not reach all regions:", unreached_regions)
                break
            consecutive_failures += 1
            continue

        src_zone = world.multiworld.random.choice(src_contenders)
        dst_zone = world.multiworld.random.choice(dst_contenders)
        src_region = tag_to_region[src_zone["region"]]
        dst_region = tag_to_region[dst_zone["region"]]

        src_target = zones[src_zone["target"]]
        dst_target = zones[dst_zone["target"]]
        src_rule = build_rule_lambda(src_zone.get("rules"), world)
        dst_rule = build_rule_lambda(dst_zone.get("rules"), world)

        # Register both warp directions
        world.warp_table[(src_target["map"], src_target["bero"])] = (dst_zone["map"], dst_zone["bero"])
        world.warp_table[(dst_target["map"], dst_target["bero"])] = (src_zone["map"], src_zone["bero"])

        mark_used(state, src_zone, dst_zone)
        add_edge(state, src_region, dst_region, has_region_dependency(world, src_zone.get("rules")))
        add_edge(state, dst_region, src_region, has_region_dependency(world, dst_zone.get("rules")))

        reachable_regions = compute_reachable(state, "Menu")
        unreached_regions = all_regions - reachable_regions - state.unneeded_regions
        dst_contenders = _dst_contenders(unreached_regions, state.used_zones)
        src_contenders = _src_contenders(reachable_regions, unreached_regions, state.used_zones)

        if dst_contenders and not src_contenders:
            # Dead end: revert this pairing and try again
            world.warp_table.pop((src_target["map"], src_target["bero"]), None)
            world.warp_table.pop((dst_target["map"], dst_target["bero"]), None)
            mark_unused(state, src_zone, dst_zone)
            remove_edge(state, src_region, dst_region)
            remove_edge(state, dst_region, src_region)

            reachable_regions = compute_reachable(state, "Menu")
            unreached_regions = all_regions - reachable_regions - state.unneeded_regions
            dst_contenders = _dst_contenders(unreached_regions, state.used_zones)
            src_contenders = _src_contenders(reachable_regions, unreached_regions, state.used_zones)

            consecutive_failures += 1
            if consecutive_failures > max_consecutive_failures:
                print("WARNING 2: Could not reach all regions:", unreached_regions)
                break
            continue

        # Resolve any connections waiting on dst_region becoming reachable
        if dst_region in delayed_connections:
            _flush_delayed(state, world, delayed_connections, dst_region, tag_to_region)
            reachable_regions = compute_reachable(state, "Menu")
            unreached_regions = all_regions - reachable_regions - state.unneeded_regions

        source_region = world.multiworld.get_region(src_region, world.player)
        target_region = world.multiworld.get_region(dst_region, world.player)
        world.create_entrance(source_region, target_region, src_rule, dst_zone["name"])
        world.create_entrance(target_region, source_region, dst_rule, src_zone["name"])

    # ------------------------------------------------------------------
    # Step 8 — Flush any remaining delayed connections
    # ------------------------------------------------------------------
    processed: set[int] = set()
    for key in list(delayed_connections.keys()):
        for connection in delayed_connections.get(key, []):
            conn_id = id(connection)
            if conn_id in processed:
                continue
            # Remove this key from the dependency list
            deps = connection[0]
            if key in deps:
                deps.remove(key)
            if not deps:
                processed.add(conn_id)
                _create_delayed_entrance(state, world, connection, tag_to_region)
    delayed_connections.clear()

    # ------------------------------------------------------------------
    # Step 9 — Pair any leftover zones without need for region logic (includes TTYD - North if deferred)
    # ------------------------------------------------------------------
    remaining_zones = [
        z for region in state.zones_by_region
        for z in state.zones_by_region[region]
        if z["name"] not in state.used_zones
    ]
    if ttyd_north_zone is not None:
        remaining_zones.append(ttyd_north_zone)

    world.multiworld.random.shuffle(remaining_zones)
    assert len(remaining_zones) % 2 == 0, "Remaining zones count must be even for clean pairing"

    for i in range(0, len(remaining_zones), 2):
        src = remaining_zones[i]
        dst = remaining_zones[i + 1]

        src_region = tag_to_region[src["region"]]
        dst_region = tag_to_region[dst["region"]]
        src_target = zones[src["target"]]
        dst_target = zones[dst["target"]]
        src_rule = build_rule_lambda(src.get("rules"), world)
        dst_rule = build_rule_lambda(dst.get("rules"), world)

        world.warp_table[(src_target["map"], src_target["bero"])] = (dst["map"], dst["bero"])
        world.warp_table[(dst_target["map"], dst_target["bero"])] = (src["map"], src["bero"])

        source_region = world.multiworld.get_region(src_region, world.player)
        target_region = world.multiworld.get_region(dst_region, world.player)
        world.create_entrance(source_region, target_region, src_rule, dst["name"])
        world.create_entrance(target_region, source_region, dst_rule, src["name"])


# ---------------------------------------------------------------------------
# Delayed-connection helpers
# ---------------------------------------------------------------------------

def _flush_delayed(
    state: RegionState,
    world: "TTYDWorld",
    delayed_connections: dict[str, list],
    resolved_region: str,
    tag_to_region: dict[str, str],
) -> None:
    """
    Remove `resolved_region` from all pending delayed connections.
    Any connection whose dependency list is now empty is immediately wired up.
    """
    connections = delayed_connections.pop(resolved_region, [])
    for connection in connections:
        deps, dep_src, dep_dst = connection
        if resolved_region in deps:
            deps.remove(resolved_region)
        if not deps:
            _create_delayed_entrance(state, world, connection, tag_to_region)


def _create_delayed_entrance(
    state: RegionState,
    world: "TTYDWorld",
    connection: list,
    tag_to_region: dict[str, str],
) -> None:
    """
    Wire up a previously-deferred connection once all its dependencies are met.

    Handles both one-way (src_region → region) and standard (region → target region)
    connection formats.
    """
    _deps, dep_src, dep_dst = connection

    if dep_src.get("target") == "One Way":
        src_name = tag_to_region[dep_src["src_region"]]
        dst_name = tag_to_region[dep_dst["region"]]
        rule = build_rule_lambda(dep_src["rules"], world)
        label = dep_dst["name"]
    else:
        src_name = tag_to_region[dep_src["region"]]
        dst_name = tag_to_region[dep_dst["region"]]
        rule = build_rule_lambda(dep_src["rules"], world)
        label = dep_dst["name"]

    src_region = world.multiworld.get_region(src_name, world.player)
    dst_region = world.multiworld.get_region(dst_name, world.player)
    add_edge(state, src_name, dst_name)
    world.create_entrance(src_region, dst_region, rule, label)


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------

def add_edge(state: RegionState, a: str, b: str, dependencies: list[str] = None) -> None:
    """Add a directed edge a → b to the region graph, optionally with region dependencies."""
    state.region_graph[a].add(b)
    if dependencies:
        state.edge_dependencies[(a, b)] = set(dependencies)


def remove_edge(state: RegionState, a: str, b: str) -> None:
    """Remove the directed edge a → b and any associated dependency data."""
    state.region_graph[a].discard(b)
    state.edge_dependencies.pop((a, b), None)


def compute_reachable(state: RegionState, start: str, excluding_region: str = None) -> set[str]:
    """
    BFS over the region graph from `start`, returning all reachable region names.

    If `excluding_region` is given, edges that depend on it are skipped, which
    allows computing reachability as if that region did not yet exist.
    """
    visited: set[str] = set()
    queue: deque[str] = deque([start])

    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)

        for neighbor in state.region_graph[current]:
            edge = (current, neighbor)
            if excluding_region and edge in state.edge_dependencies:
                if excluding_region in state.edge_dependencies[edge]:
                    continue
            if neighbor not in visited:
                queue.append(neighbor)

    return visited


# ---------------------------------------------------------------------------
# Zone / rule helpers
# ---------------------------------------------------------------------------

def has_region_dependency(world: "TTYDWorld", rule_dict: dict | None) -> list[str]:
    """
    Recursively extract all `can_reach_region` dependencies from a rule dict.
    Returns a flat list of region names referenced by the rule.
    """
    if not rule_dict or not isinstance(rule_dict, dict):
        return []

    deps: list[str] = []
    if "can_reach_region" in rule_dict:
        deps.append(rule_dict["can_reach_region"])

    for key, value in rule_dict.items():
        if key in ("and", "or"):
            sub_rules = value if isinstance(value, list) else [value]
            for sub in sub_rules:
                deps.extend(has_region_dependency(world, sub))

    return deps


def is_valid_one_way_arrangement(one_way: list[dict]) -> bool:
    """
    Return True if the cyclic one-way chain has no self-loops or forbidden pairs.

    Forbidden: any zone whose src_region connects back to its own region,
    and the special regions 'steeple_boo_background' / 'glitzville_attic'
    may appear at most once as consecutive partners in the cycle.
    """
    FORBIDDEN_PAIR = {"steeple_boo_background", "glitzville_attic"}
    forbidden_pair_count = 0

    for i, a in enumerate(one_way):
        b = one_way[(i + 1) % len(one_way)]

        # A zone must not connect back to its own region
        if a["src_region"] == b["region"] or b["src_region"] == a["region"]:
            return False

        # The two forbidden regions may share at most one edge in the cycle
        if a["src_region"] in FORBIDDEN_PAIR and b["region"] in FORBIDDEN_PAIR:
            forbidden_pair_count += 1
            if forbidden_pair_count >= 2:
                return False

    return True


def build_rule_lambda(rule_json: dict | None, world: "TTYDWorld"):
    """Convert a JSON rule dict into a callable rule object (True_() if None)."""
    if rule_json is None:
        return True_()
    return _build_single_rule(rule_json, world)


def get_region_name_by_tag() -> dict[str, str]:
    """Return a mapping of region tag → region name from regions.json."""
    return {r["tag"]: r["name"] for r in get_region_defs_from_json()}


# ---------------------------------------------------------------------------
# State accessors
# ---------------------------------------------------------------------------

def unused_zones(state: RegionState, region: str) -> list[dict]:
    """Return all zones in `region` that have not yet been assigned to a connection."""
    return [z for z in state.zones_by_region[region] if z["name"] not in state.used_zones]


def mark_used(state: RegionState, *zones: dict) -> None:
    """Mark one or more zones as used so they are not assigned a second time."""
    for z in zones:
        state.used_zones.add(z["name"])


def mark_unused(state: RegionState, *zones: dict) -> None:
    """Un-mark one or more zones so they can be re-assigned (used during backtracking)."""
    for z in zones:
        state.used_zones.discard(z["name"])