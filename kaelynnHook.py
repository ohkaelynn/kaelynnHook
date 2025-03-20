import os
import time
import psutil
import json
import random
import threading
from pythonosc.udp_client import SimpleUDPClient
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from prompt_toolkit import PromptSession

# --- Global Variables ---
console_status = ""
smoothed_bpm = None
running = True  # Global flag for all threads

# --- Load Configuration ---
CONFIG_FILE_PATH = "config.json"

def load_config():
    """
    Load configuration from CONFIG_FILE_PATH.
    If not present or invalid, create a default configuration.
    """
    default_config = {
        "spotify": {
            "client_id": "SPOTIFY_CLIENT_ID",
            "client_secret": "SPOTIFY_CLIENT_SECRET",
            "redirect_uri": "http://127.0.0.1:8888/callback"
        },
        "vrchat": {
            "osc_ip": "127.0.0.1",
            "osc_port": 9000,
            "text_file_path": "C:\\path\\to\\bpm.txt",
            "check_interval": 5
        },
        "discord": {
            "enable": False,
            "client_id": "DISCORD_APP_CLIENT_ID",
            "assets_enabled": False,
            "large_image": "custom_large_image",
            "large_text": "Custom Large Image",
            "small_image": "custom_small_image",
            "small_text": "Custom Small Image",
            "debug": False
        },
        "display": {
            "heart_icons": ["❤️", "💖", "💗", "💙", "💚", "💛", "💜"],
            "trend_symbols": {"up": "🔺", "down": "🔻", "steady": "➖"},
            "high_bpm_threshold": 110,
            "low_bpm_threshold": 60,
            "high_bpm_message": "🔥",
            "low_bpm_message": "💤",
            "normal_bpm_message": "🍿",
            "custom_message_format": "{heart_icon} {bpm} {trend_symbol} {status}",
            "enable_trend": True,
            "enable_contextual": False,
            "enable_smoothing": True,
            "smoothing_window": 3,
            "chat_pause_time": 15
        },
        "jokes": [
            "ADD_BAD_JOKES"
        ]
    }
    if not os.path.exists(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, "w") as f:
            json.dump(default_config, f, indent=4)
        return default_config
    else:
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            with open(CONFIG_FILE_PATH, "w") as f:
                json.dump(default_config, f, indent=4)
            return default_config

config = load_config()

# --- OSC Client Setup ---
vrchat_cfg = config["vrchat"]
client = SimpleUDPClient(vrchat_cfg["osc_ip"], vrchat_cfg["osc_port"])

# --- Spotify Setup ---
spotify_cfg = config["spotify"]
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=spotify_cfg["client_id"],
    client_secret=spotify_cfg["client_secret"],
    redirect_uri=spotify_cfg["redirect_uri"],
    scope="user-read-playback-state"
))

def get_spotify_track():
    """
    Return Spotify now-playing info (full details for VRChat).
    For the toolbar, only the first line (artist/title) is used.
    """
    try:
        current = sp.current_playback()
        if current and current["is_playing"]:
            song = current["item"]["name"]
            artist = current["item"]["artists"][0]["name"]
            progress = current["progress_ms"] // 1000
            duration = current["item"]["duration_ms"] // 1000
            progress_bar_length = 10
            progress_blocks = int((progress / duration) * progress_bar_length)
            bar = "█" * progress_blocks + "░" * (progress_bar_length - progress_blocks)
            return f"🎵 {song} - {artist}\n[{bar}]"
        else:
            return ""
    except Exception:
        return ""

# --- Discord RPC Setup ---
discord_cfg = config["discord"]
discord_rpc = None
discord_active = False
custom_rpc_state = None

def init_discord_rpc():
    global discord_rpc, discord_active
    try:
        from pypresence import Presence
        client_id = discord_cfg.get("client_id", "")
        if client_id:
            discord_rpc = Presence(client_id)
            discord_rpc.connect()
            discord_active = True
            print("⌘: Discord RPC connected.")
    except Exception:
        pass

if discord_cfg.get("enable", False):
    init_discord_rpc()

# --- Global Variables ---
hr_history = []
hr_message = ""
spotify_message = ""
last_sent_message = ""
paused = False
update_lock = threading.Lock()
chat_override_timeout = 0
chat_override_duration = config["display"]["chat_pause_time"]
last_discord_update_time = 0
DISCORD_UPDATE_INTERVAL = 5

# --- Dynamic Configuration Functions ---
def update_config(key, value):
    parts = key.split(".")
    cfg = config
    for part in parts[:-1]:
        if part in cfg:
            cfg = cfg[part]
        else:
            print(f"⌘: Unknown config section: {part}")
            return False
    final_key = parts[-1]
    if final_key in cfg:
        orig = cfg[final_key]
        if type(orig) is bool:
            value = value.lower() in ("true", "1", "yes")
        elif isinstance(orig, int):
            try:
                value = int(value)
            except ValueError:
                print(f"⌘: Failed to convert {value} to integer for {key}.")
                return False
        elif isinstance(orig, float):
            try:
                value = float(value)
            except ValueError:
                print(f"⌘: Failed to convert {value} to float for {key}.")
                return False
        cfg[final_key] = value
        try:
            with open(CONFIG_FILE_PATH, "w") as f:
                json.dump(config, f, indent=4)
            print(f"⌘: Updated config '{key}' to {value}.")
            return True
        except Exception as e:
            print(f"⌘: Failed to save config: {e}")
            return False
    else:
        print(f"⌘: Unknown config key: {key}")
        return False

def print_config():
    print("⌘: Current configuration:")
    print(json.dumps(config, indent=4))

# --- HR & Status Functions ---
def update_console_status(effective_bpm=None):
    global console_status
    lines = []
    if effective_bpm is not None:
        lines.append(f"⌘ HR: {effective_bpm} BPM")
    if custom_rpc_state and custom_rpc_state.strip():
        lines.append(f"⌘ Custom Status: {custom_rpc_state.strip()}")
    if spotify_message:
        now_playing = spotify_message.splitlines()[0]
        lines.append(f"⌘ Now Playing: {now_playing}")
    rpc_status = "Enabled" if discord_active else "Disabled"
    lines.append(f"⌘ Discord RPC: {rpc_status}")
    console_status = "\n".join(lines)

def is_iron_heart_running():
    for proc in psutil.process_iter(attrs=['name']):
        if proc.info['name'].lower() == "iron-heart.exe":
            return True
    return False

def read_heart_rate():
    try:
        with open(vrchat_cfg["text_file_path"], "r") as file:
            line = file.readline().strip()
            if line.isdigit():
                return int(line)
    except Exception:
        pass
    return None

def get_heart_icon():
    return random.choice(config["display"]["heart_icons"])

def detect_trend():
    if not config["display"]["enable_trend"] or len(hr_history) < 3:
        return ""
    recent = hr_history[-3:]
    if recent[0] < recent[1] < recent[2]:
        return config["display"]["trend_symbols"]["up"]
    elif recent[0] > recent[1] > recent[2]:
        return config["display"]["trend_symbols"]["down"]
    else:
        return config["display"]["trend_symbols"]["steady"]

def get_status_message(bpm):
    if not config["display"]["enable_contextual"] or bpm is None:
        return ""
    if bpm >= config["display"]["high_bpm_threshold"]:
        return config["display"]["high_bpm_message"]
    elif bpm <= config["display"]["low_bpm_threshold"]:
        return config["display"]["low_bpm_message"]
    else:
        return config["display"]["normal_bpm_message"]

def format_message(bpm):
    heart_icon = get_heart_icon()
    base_message = f"{heart_icon} {bpm}"
    if config["display"].get("enable_trend", True):
        trend = detect_trend()
        if trend:
            base_message += f" {trend}"
    parts = [base_message]
    # Append contextual message if enabled.
    if config["display"].get("enable_contextual", False):
        contextual_message = config["display"].get("contextual_message", "").strip()
        if contextual_message:
            parts.append(contextual_message)
    # Append custom status if provided.
    if custom_rpc_state and custom_rpc_state.strip():
        parts.append(custom_rpc_state.strip())
    return " | ".join(parts)

def send_to_vrchat(message):
    with update_lock:
        try:
            client.send_message("/chatbox/input", [message, True])
        except Exception:
            pass

def update_discord_rpc(bpm):
    global last_discord_update_time
    if not discord_active:
        return
    if time.time() - last_discord_update_time < DISCORD_UPDATE_INTERVAL:
        return
    try:
        # Build details: BPM (and trend, if enabled).
        details = f"⌘ {bpm} BPM"
        if config["display"].get("enable_trend", True):
            trend = detect_trend()
            if trend:
                details += f" {trend}"
        # Append contextual message to details if enabled.
        if config["display"].get("enable_contextual", False):
            contextual_message = config["display"].get("contextual_message", "").strip()
            if contextual_message:
                details += f" | {contextual_message}"
        # State field: include the custom status with a "Status:" prefix, if provided.
        state = f"Status: {custom_rpc_state.strip()}" if custom_rpc_state and custom_rpc_state.strip() else ""
        
        update_kwargs = {"details": details, "start": None}
        if state:
            update_kwargs["state"] = state
        
        if discord_cfg.get("assets_enabled", False):
            update_kwargs["large_image"] = discord_cfg.get("large_image", "")
            update_kwargs["large_text"] = discord_cfg.get("large_text", "")
            update_kwargs["small_image"] = discord_cfg.get("small_image", "")
            update_kwargs["small_text"] = discord_cfg.get("small_text", "")
        
        discord_rpc.update(**update_kwargs)
        last_discord_update_time = time.time()
    except Exception:
        pass

# --- Update Threads ---
def main_loop():
    global hr_message, hr_history, last_sent_message, smoothed_bpm
    update_console_status()  # Removed status_message keyword
    time.sleep(2)
    startup_msg = "⌘ kaelynnHook starting ⌘"
    send_to_vrchat(startup_msg)
    last_sent_message = startup_msg
    if discord_active:
        try:
            discord_rpc.update(details=startup_msg, state=startup_msg, start=None)
        except Exception:
            pass
    while running:
        try:
            if not paused:
                if is_iron_heart_running():
                    bpm = read_heart_rate()
                    if bpm is not None:
                        hr_history.append(bpm)
                        if len(hr_history) > 10:
                            hr_history.pop(0)
                        if config["display"].get("enable_smoothing", False):
                            alpha = 0.3
                            if smoothed_bpm is None:
                                smoothed_bpm = bpm
                            else:
                                smoothed_bpm = alpha * bpm + (1 - alpha) * smoothed_bpm
                            effective_bpm = int(smoothed_bpm)
                        else:
                            effective_bpm = bpm
                        hr_message = format_message(effective_bpm)
                        update_discord_rpc(effective_bpm)
                        update_console_status(effective_bpm)  # Removed status_message argument
                    else:
                        update_console_status()  # Removed status_message argument
                else:
                    update_console_status()  # Removed status_message argument
            else:
                update_console_status()  # Removed status_message argument
            time.sleep(vrchat_cfg["check_interval"])
        except KeyboardInterrupt:
            break
    if discord_active:
        try:
            discord_rpc.close()
        except Exception:
            pass

def update_spotify():
    global spotify_message
    while running:
        spotify_message = get_spotify_track()
        time.sleep(1)

def update_combined():
    global last_sent_message, chat_override_timeout
    while running:
        if time.time() < chat_override_timeout:
            time.sleep(1)
            continue
        if hr_message and spotify_message:
            combined = f"{hr_message}\n{spotify_message}"
        elif hr_message:
            combined = hr_message
        else:
            combined = spotify_message
        if combined and combined != last_sent_message:
            send_to_vrchat(combined)
            last_sent_message = combined
        time.sleep(1)

# --- Refresh Prompt Toolbar ---
def refresh_toolbar(session):
    while running:
        try:
            session.app.invalidate()
            time.sleep(1)
        except Exception:
            break

# --- Input Thread (Commands & Dynamic Config) ---
def input_thread():
    global custom_rpc_state, chat_override_timeout, paused, running, discord_active
    session = PromptSession("> ", bottom_toolbar=lambda: console_status)
    refresh_thread = threading.Thread(target=refresh_toolbar, args=(session,))
    refresh_thread.start()
    cmds = (
        "⌘ Available commands ⌘\n"
        "⌘  Any message without prefix will be sent to VRChat Chatbox.\n"
        "⌘  /status [message] - Set custom status (empty clears status).\n"
        "⌘  /clear - Clear the console and reset custom status.\n"
        "⌘  /pause - Pause updates.\n"
        "⌘  /resume - Resume updates.\n"
        "⌘  /exit - Exit gracefully.\n"
        "⌘  /get - Display current configuration.\n"
        "⌘  /set key value - Update a configuration setting (use dot notation for sections).\n"
        "⌘  /time - Send current local time to chatbox.\n"
        "⌘  /joke - Send a random joke.\n"
        "⌘  /rpc - Toggle Discord RPC sender on/off.\n"
        "⌘  /cmds - Show this command list."
    )
    jokes = config.get("jokes", [])
    while running:
        try:
            line = session.prompt()
            if line.startswith("/status"):
                parts = line.split(maxsplit=1)
                if len(parts) == 1 or parts[1].strip() == "":
                    custom_rpc_state = ""
                    print("⌘: Custom status cleared.")
                else:
                    custom_rpc_state = parts[1].strip()
                    print(f"⌘: Custom status set to: {custom_rpc_state}")
            elif line == "/clear":
                custom_rpc_state = ""
                os.system('cls' if os.name == 'nt' else 'clear')
                print("⌘: Console cleared and custom status reset.")
            elif line == "/pause":
                paused = True
                update_console_status(status_message="⌘: Paused")
                print("⌘: Updates paused.")
            elif line == "/resume":
                paused = False
                update_console_status(status_message="⌘: Resumed")
                print("⌘: Updates resumed.")
            elif line == "/exit":
                print("⌘: Exiting gracefully...")
                running = False
                break
            elif line == "/get":
                print_config()
            elif line.startswith("/set "):
                parts = line.split(maxsplit=2)
                if len(parts) == 3:
                    key = parts[1]
                    value = parts[2]
                    update_config(key, value)
                else:
                    print("⌘: Usage: /set key value")
            elif line == "/time":
                current_time = time.strftime("%H:%M:%S")
                send_to_vrchat(f"⏰ {current_time}")
                print(f"⌘: Sent local time ({current_time})")
                chat_override_timeout = time.time() + 5
            elif line == "/joke":
                if jokes:
                    joke = random.choice(jokes)
                    send_to_vrchat(f"😂 {joke}")
                    print(f"⌘: Sent a joke: {joke}")
                    chat_override_timeout = time.time() + 5
                else:
                    print("⌘: No jokes configured.")
            elif line == "/rpc":
                if discord_active:
                    try:
                        discord_rpc.close()
                        discord_active = False
                        print("⌘: Discord RPC disabled.")
                    except Exception:
                        print("⌘: Failed to disable Discord RPC.")
                else:
                    init_discord_rpc()
                    if discord_active:
                        print("⌘: Discord RPC enabled.")
                    else:
                        print("⌘: Discord RPC disabled.")
            elif line == "/cmds":
                print(cmds)
            elif line.startswith("/"):
                print("⌘: Unknown command.")
            else:
                chat_message = f"💬 {line}"
                send_to_vrchat(chat_message)
                chat_override_timeout = time.time() + config["display"]["chat_pause_time"]
        except Exception as e:
            print(f"⌘: Input thread error: {e}")
            break
    refresh_thread.join()

# --- Main Execution ---
if __name__ == "__main__":
    t_input = threading.Thread(target=input_thread)
    t_main = threading.Thread(target=main_loop)
    t_spotify = threading.Thread(target=update_spotify)
    t_combined = threading.Thread(target=update_combined)
    
    t_input.start()
    t_main.start()
    t_spotify.start()
    t_combined.start()
    
    t_input.join()
    t_main.join()
    t_spotify.join()
    t_combined.join()
