import evdev
from evdev import ecodes
import sys
import json
from pathlib import Path

SCENE_ACTIONS = [
    ("Aktivuji NOC", "trigger_scene_night"),
    ("Aktivuji DEN", "trigger_scene_day"),
    ("Aktivuji VEČER", "trigger_scene_evening"),
    ("Aktivuji VÝHRU ZLA", "trigger_scene_evil_won"),
    ("Aktivuji VÝHRU DOBRA", "trigger_scene_good_won"),
    ("Aktivuji LOSOVANI", "trigger_scene_drawing"),
    ("Aktivuji POPRAVU", "trigger_effect_execution"),
    ("Aktivuji BLESK", "trigger_sfx_thunder"),
    ("Prepinam žárovky", "trigger_toggle_lights"),
    ("Měním barvu zla", "trigger_set_evil_color"),
    ("STOP zvuku", "trigger_stop_audio"),
    ("Jail", "trigger_effect_jail"),
    ("Man", "trigger_effect_scream_man"),
    ("Female", "trigger_effect_scream_woman"),
    ("Clocks", "trigger_effect_clocks"),
    ("Demon", "trigger_effect_demon")
]

MODIFIER_ACTIONS = [
    ("Zvýšit Hlasitost", "trigger_volume_up"),
    ("Snížit Hlasitost", "trigger_volume_down")
]

def get_keypad():
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    if not devices:
        print("No input devices found. Try running with 'sudo'.")
        sys.exit(1)

    print("=== Select your Keypad ===")
    for i, device in enumerate(devices):
        print(f"[{i}] {device.name}")

    choice = input("\nEnter the number of your keypad: ").strip()
    try:
        return devices[int(choice)]
    except (ValueError, IndexError):
        print("Invalid choice.")
        sys.exit(1)

def wait_for_key(device, used_keys):
    for event in device.read_loop():
        if event.type == ecodes.EV_KEY and event.value == 1:
            key_name = evdev.ecodes.KEY.get(event.code, "UNKNOWN")
            if isinstance(key_name, list):
                key_name = key_name[0]
            
            dict_key = key_name.replace("KEY_", "").lower()
            
            if dict_key in used_keys:
                print(f"  [!] Key '{dict_key}' is already bound! Please press a different key.")
                continue
                
            return dict_key

def main():
    device = get_keypad()
    print(f"\n--- Connected to {device.name} ---")
    print("Press the key on your keypad that you want to bind to each action.\n")

    bound_scenes = {}
    bound_modifiers = {}
    used_keys = set()

    print("=== BINDING SCENES ===")
    for label, method in SCENE_ACTIONS:
        print(f"Press key for: {label} ({method})")
        key = wait_for_key(device, used_keys)
        # We store it as a list because JSON doesn't support Python tuples natively
        bound_scenes[key] = [label, method]
        used_keys.add(key)
        print(f"  -> Bound to '{key}'\n")

    print("=== BINDING MODIFIERS ===")
    for label, method in MODIFIER_ACTIONS:
        print(f"Press key for: {label} ({method})")
        key = wait_for_key(device, used_keys)
        bound_modifiers[key] = method
        used_keys.add(key)
        print(f"  -> Bound to '{key}'\n")

    # Save to JSON file
    config = {
        "SCENE_KEYS": bound_scenes,
        "MODIFIER_KEYS": bound_modifiers
    }
    
    keymap_path = Path(__file__).resolve().parent / "keymap.json"
    with open(keymap_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    print("="*50)
    print(f"SUCCESS! Keys have been saved to '{keymap_path}'.")
    print("="*50)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBinding cancelled.")
    except PermissionError:
        print("\n[!] Permission Denied. Run with 'sudo'.")