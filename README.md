# Universal TTS Mod (Ren'Py + Unity) - Kokoro Socket Backend

Reads dialogue aloud in real time using a local Kokoro TTS backend. The game-side mod sends dialogue over a local TCP socket to avoid blocking the game UI while audio is generated.

Supports both **Ren'Py** and **Unity** games out of the box!

## Current Architecture

- `renpy_mod/tts_mod.rpy`: Ren'Py client integration, hotkeys, dialogue callback.
- `renpy_mod/tts_server.py`: Local socket server on `127.0.0.1:5050` by default.
- `renpy_mod/tts_engines.py`: Kokoro playback engine plus test mock.
- `renpy_mod/text_cleaner.py`: Removes tags/control text and normalizes punctuation before speech.
- `unity_mod/KokoroTtsPlugin.dll`: Unity BepInEx plugin C# assembly for capturing UI.Text and TextMeshPro dialogue.
- `install_tts_mod.py`: Universal installer script with automatic engine detection (Ren'Py vs Unity).

Protocol commands sent to the backend:

- `STOP`: Stop current playback and clear queued speech.
- `SET_SPEED:<value>`: Update speech speed.
- `SET_VOICE:<voice>`: Update Kokoro voice for future speech.
- any other non-empty line: Clean and speak that dialogue line.
- `QUIT`: Shut down the backend.

## Installation

### Automatic Installer (Recommended)

Run the universal installer on any game folder:

```bat
python install_tts_mod.py --game-folder "path\to\GameFolder"
```

The installer detects whether the game is **Ren'Py** or **Unity** automatically:
- **Ren'Py**: Copies `.rpy` scripts into `game/` and helper backend.
- **Unity**: Installs **BepInEx 5** framework and `KokoroTtsPlugin.dll` into `BepInEx/plugins/`.

### Launching

1. Run `run_backend.bat` in the target game root folder.
2. Start the game.
3. In game:
   - Press **`V`** to connect/reconnect to the TTS backend.
   - Press **`A`** to toggle auto-forward mode.

## Development & Testing

Run unit & integration tests:

```bat
cmd /c run_tests.bat
```

To compile the Unity plugin C# source:

```bat
dotnet build unity_mod/src/KokoroTtsPlugin.csproj -c Release
```
