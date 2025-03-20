This is a personal tool that integrates BPM data from [Iron-Heart](https://github.com/nullstalgia/iron-heart/) with Spotify, and optionally Discord Rich Presence for just heart rate, trends and status.  
I built it as a lightweight alternative to buying Pulsoid ^^.

## Features
- **OSC Chat Sender (In VRC Only):**  
  Pauses heart rate and allows you to send chat messages without being overlapped.
- **Reads BPM Data:**  
  Reads heart rate data from a text file (populated by [Iron-Heart](https://github.com/nullstalgia/iron-heart/)) and applies optional exponential smoothing.
- **VRChat OSC Updates:**  
  Sends formatted heart rate messages (with icons and trend symbols) via OSC to VRChat.
- **Spotify Integration (In VRC Only):**  
  Retrieves your currently playing track from Spotify and displays it with a progress bar alongside heart rate.
- **Discord RPC (Optional):**  
  Updates Discord Rich Presence with your BPM data. RPC is disabled by default. Use the `/rpc` command to toggle it on or off.

- **Interactive Terminal Commands:**  
  Use a command prompt (powered by prompt_toolkit) to control the integration:
  - `/status [message]` — Set a custom status (empty clears status).
  - `/clear` — Clear the console and reset the custom status.
  - `/pause` and `/resume` — Pause or resume updates.
  - `/time` — Send your local time to VRChat.
  - `/joke` — Send a random joke (jokes are loaded from the configuration file).
  - `/rpc` — Toggle Discord RPC on or off.
  - `/get` and `/set key value` — View and update configuration settings.
  - `/cmds` — Display the list of available commands.

- **Toolbar Display:**  
  The bottom toolbar shows your current BPM, custom status, Spotify "Now Playing" info, and the current Discord RPC status.

## Screenshots

### Main Usage
![Main_Usage](https://i.imgur.com/DXzrMcK.png)

### VRChat Chatbox
![VRChat Chatbox](https://i.imgur.com/MsTYtgZ.png)

### Discord Rich Presence
![Discord](https://i.imgur.com/ToUjV1W.png)

## Configuration

All settings—including Spotify API credentials, VRChat OSC settings, Discord RPC options, display settings, and jokes—are stored in a JSON configuration file (`config.json`).

## Usage

1. Clone this repository.
2. Update `config.json` with your credentials and preferences.
3. Run the script using your Python interpreter:

   ```bash
   python kaelynnHook.py
