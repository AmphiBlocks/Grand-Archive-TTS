import argparse
import copy
import json
import random
import string
from pathlib import Path

SOURCE_GUID = "9231d7"
TARGET_NICKNAME = "Booster Packs"
MARKER = "AI_PIPELINE_GA_PTM_BOOSTER"
TARGET_COLLATION = "PHANTOM_MONARCHS_8_CARD"
SOURCE_ART_URL = "https://steamusercontent-a.akamaihd.net/ugc/14410242526919890640/D7B6EB271552D25B8718DEB4E05F84577822AB00/"
TARGET_ART_URL = "https://steamusercontent-a.akamaihd.net/ugc/12077178895808964041/AD104E8BD1C5BD81D9159A08D0739842382C3C4B/"

TARGET_SCRIPT = '''function onObjectRotate(rotated_object, spin, flip, player_color, old_spin, old_flip)
  if flip ~= old_flip and rotated_object == self then
    Global.call("RipBoosterPack", {
      player_color = player_color,
      object = self,
      collation_name = "PHANTOM_MONARCHS_8_CARD"
    })
  end
end'''


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def walk_objects(obj):
    yield obj
    for child in obj.get("ContainedObjects") or []:
        yield from walk_objects(child)


def collect_all_guids(save_data):
    guids = set()
    for obj in save_data.get("ObjectStates") or []:
        for o in walk_objects(obj):
            guid = o.get("GUID")
            if guid:
                guids.add(guid.lower())
    return guids


def generate_guid(existing):
    alphabet = string.hexdigits.lower()[:16]
    for _ in range(10000):
        guid = "".join(random.choice(alphabet) for _ in range(6))
        if guid not in existing:
            existing.add(guid)
            return guid
    raise RuntimeError("Unable to generate unique GUID")


def remap_guids(obj, existing):
    old_guid = (obj.get("GUID") or "").lower()
    if old_guid:
        obj["GUID"] = generate_guid(existing)
    for child in obj.get("ContainedObjects") or []:
        remap_guids(child, existing)


def find_top_level_by_guid(save_data, guid):
    guid = guid.lower()
    for idx, obj in enumerate(save_data.get("ObjectStates") or []):
        if (obj.get("GUID") or "").lower() == guid:
            return idx, obj
    return None, None


def find_existing_target(save_data):
    for idx, obj in enumerate(save_data.get("ObjectStates") or []):
        if obj.get("Name") != "Infinite_Bag":
            continue
        if (obj.get("Nickname") or "") != TARGET_NICKNAME:
            continue
        if (obj.get("GMNotes") or "") == MARKER:
            return idx, obj
    return None, None


def update_bag_for_ptm(bag, pos_x=18.0, pos_y=0.0, pos_z=0.0):
    bag["Nickname"] = TARGET_NICKNAME
    bag["GMNotes"] = MARKER
    bag.setdefault("Transform", {})["posX"] = pos_x
    bag.setdefault("Transform", {})["posY"] = pos_y
    bag.setdefault("Transform", {})["posZ"] = pos_z

    contained = bag.get("ContainedObjects") or []
    if not contained:
        raise RuntimeError("Source booster bag has no contained objects")

    pack = contained[0]
    pack["LuaScript"] = TARGET_SCRIPT
    pack["Nickname"] = "Flip PTM Pack to Rip"
    custom_mesh = pack.get("CustomMesh") or {}
    if custom_mesh.get("DiffuseURL") == SOURCE_ART_URL or custom_mesh.get("DiffuseURL"):
        custom_mesh["DiffuseURL"] = TARGET_ART_URL
    else:
        custom_mesh["DiffuseURL"] = TARGET_ART_URL
    pack["CustomMesh"] = custom_mesh


def main():
    parser = argparse.ArgumentParser(
        description="Inject or update a GA physical PTM booster infinite bag cloned from Riftbound"
    )
    parser.add_argument(
        "--ga-save",
        default="Grand-Archive-Fracturized.json",
        help="Path to GA save JSON",
    )
    parser.add_argument(
        "--rift-save",
        default=str(Path("..") / ".." / "RiftBound" / "Riftbound-TTS" / "Riftbound-LGS-Table.json"),
        help="Path to Riftbound save JSON",
    )
    parser.add_argument(
        "--source-guid",
        default=SOURCE_GUID,
        help="GUID of source infinite booster bag in Riftbound save",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output save path (default: overwrite --ga-save)",
    )
    args = parser.parse_args()

    ga_path = Path(args.ga_save)
    rift_path = Path(args.rift_save)
    output_path = Path(args.output) if args.output else ga_path

    if not ga_path.exists():
        raise FileNotFoundError(f"GA save not found: {ga_path}")
    if not rift_path.exists():
        raise FileNotFoundError(f"Riftbound save not found: {rift_path}")

    ga_data = load_json(ga_path)
    rift_data = load_json(rift_path)

    existing_idx, existing_bag = find_existing_target(ga_data)
    if existing_bag is not None:
        update_bag_for_ptm(existing_bag)
        save_json(output_path, ga_data)
        print(f"Updated existing GA PTM booster bag at ObjectStates[{existing_idx}] -> {output_path}")
        return

    _, source_bag = find_top_level_by_guid(rift_data, args.source_guid)
    if source_bag is None:
        raise RuntimeError(f"Source bag GUID {args.source_guid} not found in Riftbound save")

    cloned = copy.deepcopy(source_bag)
    existing_guids = collect_all_guids(ga_data)
    remap_guids(cloned, existing_guids)
    update_bag_for_ptm(cloned)

    ga_data.setdefault("ObjectStates", []).append(cloned)
    save_json(output_path, ga_data)
    print(f"Injected GA PTM booster bag (new GUID {cloned.get('GUID')}) -> {output_path}")


if __name__ == "__main__":
    main()
