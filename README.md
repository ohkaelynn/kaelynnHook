# kaelynnHook
Reads BPM Data:
Reads heart rate data from a text file (populated by Iron-Heart) and applies optional exponential smoothing.

VRChat OSC Updates:
Sends formatted heart rate messages (with icons and trend symbols) via OSC to VRChat.

Spotify Integration:
Retrieves your currently playing track from Spotify and uses only the first line (artist/title) in the toolbar.

Discord RPC (Optional):
Updates Discord Rich Presence with your BPM data. By default, RPC is disabled. You can toggle it using the /rpc command, and the toolbar displays the current RPC status.

Interactive Terminal Commands:
The script uses a prompt (via prompt_toolkit) to let you input commands such as:

/status [message] to set (or clear) a custom status.
/clear to clear the console and reset the custom status.
/pause and /resume to pause/resume updates.
/time to send your local time to VRChat.
/joke to send a random joke (jokes are loaded from the config).
/rpc to toggle Discord RPC on or off.
/get and /set key value to view and update configuration settings.
/cmds to display the list of available commands.
Toolbar Display:
The bottom toolbar shows your current BPM, status, now playing info, and whether Discord RPC is enabled.

# Personal Tool, just posting here. I didnt want to pay for Pulsoid to use VRC Magic Chatbox xd plus like this aesthetic 
