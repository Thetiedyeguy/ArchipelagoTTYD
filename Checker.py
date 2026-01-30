from collections import Counter, defaultdict
import importlib
json = importlib.import_module("json")

IGNORE_TARGETS = {"Vanilla", "One Way"}


def debug_loading_zones(loading_zones):
    errors = False

    print(f"Total loading zones (before filtering): {len(loading_zones)}")

    # Filter zones we actually care about
    vanilla_zones = [
        z for z in loading_zones
        if z.get("target") == "Vanilla"
    ]

    one_way_zones = [
        z for z in loading_zones
        if z.get("target") == "One Way"
    ]

    # Filter zones we actually care about
    filtered_zones = [
        z for z in loading_zones
        if z.get("target") not in IGNORE_TARGETS
    ]

    print(f"Total Vanilla zones (after filtering): {len(vanilla_zones)}")
    print(f"Total One Way zones (after filtering): {len(one_way_zones)}")
    print(f"Total loading zones (after filtering): {len(filtered_zones)}")

    # -------------------------
    # 1. Check unique names
    # -------------------------
    name_counts = Counter(z["name"] for z in filtered_zones)
    duplicate_names = {name: count for name, count in name_counts.items() if count > 1}

    if duplicate_names:
        errors = True
        print("\n❌ Duplicate loading zone names found:")
        for name, count in duplicate_names.items():
            print(f"  - '{name}' appears {count} times")
    else:
        print("\n✅ All loading zone names are unique")

    # -------------------------
    # 2. Check target references
    # -------------------------
    target_counts = Counter(z["target"] for z in filtered_zones)

    missing_references = []
    multiple_references = []

    for name in name_counts:
        count = target_counts.get(name, 0)
        if count == 0:
            missing_references.append(name)
        elif count > 1:
            multiple_references.append((name, count))

    if missing_references:
        errors = True
        print("\n❌ Loading zones never referenced as a target:")
        for name in missing_references:
            print(f"  - {name}")

    if multiple_references:
        errors = True
        print("\n❌ Loading zones referenced more than once as a target:")
        for name, count in multiple_references:
            print(f"  - {name} referenced {count} times")

    if not missing_references and not multiple_references:
        print("\n✅ All loading zones are referenced exactly once")

    # -------------------------
    # Summary
    # -------------------------
    if errors:
        print("\n⚠️ Problems found. See output above.")
    else:
        print("\n🎉 No issues found. Loading zones look consistent!")


# -------------------------------------------------
# Example usage
# -------------------------------------------------
if __name__ == "__main__":
    # Replace this with however you load your data
    # e.g. from JSON, regions dict, etc.
    with open("files/zones.json", "r", encoding="utf-8") as f:
        loading_zones = json.load(f)

    debug_loading_zones(loading_zones)
