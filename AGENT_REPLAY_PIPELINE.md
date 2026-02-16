# TTS Replay Notes (Agent)

Use extracted scripts in `S:\Dev\TTS\aipipeline\workspaces\ga\scripts` for editing/inspection; avoid parsing the giant save JSON unless necessary.

Where replay events come from:
- `scripts\global\LuaScript.lua`
  - `ReplayNet.log(...)` batching/upload
  - `onLoadCard(...)` -> `CARD_LOADED`
  - `onUnloadCard(...)` -> `CARD_UNLOADED`
- `scripts\objects\0034_7deec9_ga-load-menu\LuaScript.lua`
  - Calls `Global.call("onLoadCardRemote", ...)` / `Global.call("onUnloadCardRemote", ...)`

If you must patch the mod save:
- Source of truth is `Grand-Archive-Fracturized.json` (`LuaScript` blocks).
- Prefer regenerating/updating from extracted scripts to reduce risk.
