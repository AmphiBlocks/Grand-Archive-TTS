# AI Layout Notes - Grand Archive (Fracturized)

Last updated: 2026-02-13

## Scope
These notes track only the parts needed for booster/collation work. Avoid dumping full object inventories here.

## Key Files
- Save: `Grand-Archive-Fracturized.json`
- Workspace: `S:\Dev\TTS\aipipeline\workspaces\ga`
- Generator: `Grand-Archive-TTS/build_ga_collation_data.py`

## Key Script Objects
- `GA_EffectLibrary`
  - Effect/lookup data.
- `GA_CollationLibrary`
  - Booster card records, pools, and collation definitions.
- Booster prototype (`Flip it to Rip it`, GUID often `caded0`)
  - Right-click mode switching.
  - Calls `Global.RipBoosterPack` with selected `collation_name`.

## Booster Architecture
- Infinite bag spawns the booster prototype.
- Booster script selects mode/art + collation id.
- Global script asks `GA_CollationLibrary.GeneratePack` for UUIDs.
- Global script resolves card payload via `GA_CollationLibrary.getCardData` and spawns via existing deck pipeline.

## Current Data Model Choices
- Collation library is optimized for size and load time:
  - Pool comments removed.
  - Card records are sparse (booster fields only).
  - DFC orientation data included only when needed.
  - Identical pools are aliased rather than duplicated.
- Effect data remains in `GA_EffectLibrary`; avoid duplicating it in collation data.

## Product Rule References
- Alter/exception rules: `aipipeline/GA_ALTER_PACK_RULES.md`
- API/filter rules: `aipipeline/GA_API_USAGE_NOTES.md`
- Workflow: `aipipeline/AI_WORKFLOW.md`

## Working Rule
- If set tagging is inconsistent, prefer prefix-filter strategy with controlled fallbacks and document any special-case mapping here.
