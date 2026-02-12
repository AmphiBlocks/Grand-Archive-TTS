import argparse
import copy
import json
import random
import string
from pathlib import Path


TARGET_NICKNAME = "GA_CollationLibrary"
TEMPLATE_NICKNAME = "GA_EffectLibrary"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def collect_objects(obj):
    yield obj
    for child in obj.get("ContainedObjects") or []:
        yield from collect_objects(child)


def all_guids(save_data):
    guids = set()
    for obj in save_data.get("ObjectStates") or []:
        for o in collect_objects(obj):
            guid = o.get("GUID")
            if guid:
                guids.add(guid.lower())
    return guids


def find_top_level_by_nickname(save_data, nickname):
    for i, obj in enumerate(save_data.get("ObjectStates") or []):
        if (obj.get("Nickname") or "") == nickname:
            return i, obj
    return None, None


def generate_guid(existing):
    alphabet = string.hexdigits.lower()[:16]
    for _ in range(10000):
        g = "".join(random.choice(alphabet) for _ in range(6))
        if g not in existing:
            return g
    raise RuntimeError("Unable to generate unique GUID.")


def main():
    parser = argparse.ArgumentParser(
        description="Inject or update GA_CollationLibrary object in a TTS save."
    )
    parser.add_argument(
        "--save",
        default="Grand-Archive-Fracturized.json",
        help="Path to TTS save JSON",
    )
    parser.add_argument(
        "--collation-lua",
        default="out_lua/collation/ga_collation_phantom_monarchs.lua",
        help="Path to generated GA collation Lua file",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output save path (default: overwrite --save)",
    )
    args = parser.parse_args()

    save_path = Path(args.save)
    output_path = Path(args.output) if args.output else save_path
    collation_path = Path(args.collation_lua)

    if not save_path.exists():
        raise FileNotFoundError(f"Save not found: {save_path}")
    if not collation_path.exists():
        raise FileNotFoundError(f"Collation lua not found: {collation_path}")

    save_data = load_json(save_path)
    lua_script = collation_path.read_text(encoding="utf-8")

    idx, existing = find_top_level_by_nickname(save_data, TARGET_NICKNAME)
    if existing is not None:
        existing["LuaScript"] = lua_script
        existing["LuaScriptState"] = ""
        existing["XmlUI"] = ""
        save_json(output_path, save_data)
        print(f"Updated existing {TARGET_NICKNAME} at ObjectStates[{idx}] -> {output_path}")
        return

    _, template = find_top_level_by_nickname(save_data, TEMPLATE_NICKNAME)
    if template is None:
        raise RuntimeError(f"Template object '{TEMPLATE_NICKNAME}' not found in top-level ObjectStates.")

    existing_guids = all_guids(save_data)
    new_guid = generate_guid(existing_guids)
    cloned = copy.deepcopy(template)
    cloned["GUID"] = new_guid
    cloned["Nickname"] = TARGET_NICKNAME
    cloned["LuaScript"] = lua_script
    cloned["LuaScriptState"] = ""
    cloned["XmlUI"] = ""
    if isinstance(cloned.get("Transform"), dict):
        cloned["Transform"]["posY"] = (cloned["Transform"].get("posY") or 0) + 1.25
        cloned["Transform"]["posZ"] = (cloned["Transform"].get("posZ") or 0) + 1.25

    save_data.setdefault("ObjectStates", []).append(cloned)
    save_json(output_path, save_data)
    print(f"Injected {TARGET_NICKNAME} cloned from {TEMPLATE_NICKNAME} with GUID {new_guid} -> {output_path}")


if __name__ == "__main__":
    main()
