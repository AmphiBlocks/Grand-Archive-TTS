$source = "C:\Users\JDoYo\Documents\My Games\Tabletop Simulator\Saves\TS_Save_28.json"
$dest = "S:\Dev\TTS\Grand Archive\Grand-Archive-TTS\Grand-Archive-Fracturized.json"

Copy-Item $source $dest -Force
Write-Host "Synced TTS save to repo."
