# AI Layout Notes - Grand Archive (Fracturized)

Last updated: 2026-02-12

## Primary files in this directory
- Main save: `Grand-Archive-Fracturized.json`

## Preferred AI workflow
- Use extraction/context pipeline before editing.
- Workspace: `S:\Dev\TTS\aipipeline\workspaces\ga`
- Extracted global script: `S:\Dev\TTS\aipipeline\workspaces\ga\scripts\global\LuaScript.lua`
- Script map/context: `S:\Dev\TTS\aipipeline\workspaces\ga\context\CONTEXT.md`
- Call graph: `S:\Dev\TTS\aipipeline\workspaces\ga\context\CALLS.json`
- Repack through pipeline instead of manual full JSON edits.

## Save structure summary
- TTS version observed: `v14.1.8`
- `ObjectStates` count: `62`
- Global Lua length: `139681`
- Global XmlUI length: `17085`
- Scripted objects (non-global): `35`

## Major script-bearing objects
- `c2d323` `PiecePack_Arms` `GA_EffectLibrary` (lua=755884, xml=0, depth=0)
- `02e062` `PiecePack_Arms` `Encoder` (lua=45687, xml=0, depth=0)
- `7deec9` `PiecePack_Moons` `GA Load Menu` (lua=9613, xml=0, depth=0)
- `de4346` `PiecePack_Arms` `πGlimpse` (lua=9249, xml=0, depth=0)
- `7a0067` `PiecePack_Arms` `πNotepad` (lua=8643, xml=0, depth=0)
- `c369d7` `PiecePack_Arms` `πMenu` (lua=8506, xml=0, depth=0)
- `cd83de` `PiecePack_Crowns` `Auto Player Promoter` (lua=7132, xml=0, depth=0)
- `c2df23` `PiecePack_Arms` `ImportReferences` (lua=5434, xml=0, depth=0)
- `3afac9` `CardCustom` `Quick Actions Panel` (lua=2404, xml=2983, depth=1)
- `3afac9` `CardCustom` `Quick Actions Panel` (lua=2402, xml=2983, depth=0)
- `552c1f` `CardCustom` `Quick Actions Panel` (lua=2402, xml=2983, depth=0)
- `df7c50` `Custom_Tile` `` (lua=2061, xml=2637, depth=1)
- `a1b2c3` `CardCustom` `Fracturized Token` (lua=4674, xml=0, depth=1)
- `def0af` `PiecePack_Arms` `πCounter` (lua=3759, xml=0, depth=0)

## Containers worth checking
- `5ddb44` `Infinite_Bag` `D6` (contained=1)
- `f27d35` `Infinite_Bag` `D6` (contained=1)
- `9231d7` `Infinite_Bag` `D20` (contained=1)
- `1f8a47` `Infinite_Bag` `Counters` (contained=1)
- `21d3f1` `Infinite_Bag` `Quick Actions Menu` (contained=1)
- `b2b068` `Infinite_Bag` `Status Tokens` (contained=1)
- `0e628b` `Infinite_Bag` `Herb Board by Sage` (contained=1)
- `6c36d4` `Infinite_Bag` `Status Markers` (contained=1)
- `650a62` `Infinite_Bag` `Booster Packs` (contained=1, prototype=`caded0`)

## Booster setup notes
- Physical booster flow is now canonical for PTM:
  - Infinite bag `650a62` spawns a flip-to-rip model prototype.
  - Prototype supports right-click mode switching (`Set to Phantom Monarchs`, `Set to Abyssal Heaven`) using context menu pattern used by dice/status tokens.
  - Modes currently:
    - `PHANTOM_MONARCHS_8_CARD` with PTM art `https://steamusercontent-a.akamaihd.net/ugc/12077178895808964041/AD104E8BD1C5BD81D9159A08D0739842382C3C4B/`
    - `ABYSSAL_HEAVEN_8_CARD` with Abyssal art `https://steamusercontent-a.akamaihd.net/ugc/12109684205242165739/6CFCD4EFA56B6B3A2EA955D7FA92A36F28F02193/`
  - Additional collation IDs now available in `GA_CollationLibrary`:
    - `HVN_8_CARD` (alias: `ABYSSAL_HEAVEN_8_CARD`)
    - `MRC_1E_8_CARD` (alias: `MRC1E_8_CARD`)
    - `MRC_ALTER_9_CARD` (alias: `MRC_ALTER_8_CARD`)
  - Alter-product collation rules are documented in:
    - `aipipeline/GA_ALTER_PACK_RULES.md`

## Exploration order
1. Refresh extract/context in pipeline workspace.
2. Inspect global script entrypoints first.
3. Inspect major helper/library objects and menu modules.
4. Inspect relevant container prototypes for clone/spawn behavior.
5. Repack and test in TTS.

## Caveat
- GUIDs/object indexes may drift between save revisions; re-scan when save changes.
