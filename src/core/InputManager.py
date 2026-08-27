import asyncio
import json
import os
from pathlib import Path

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .SceneManager import SceneManager

try:
    import evdev
    from evdev import ecodes

    HAS_EVDEV = True
except ImportError:
    HAS_EVDEV = False
    print("Warning: evdev not found. Controller inputs will not work on this OS.")

try:
    from pynput import keyboard as pynput_keyboard

    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False


class InputManager:
    # Default scene keys fallback
    DEFAULT_SCENE_KEYS = {
        "u": ("Aktivuji NOC", "trigger_scene_night"),
        "y": ("Aktivuji DEN", "trigger_scene_day"),
        "b": ("Aktivuji POPRAVU", "trigger_effect_execution"),
        "h": ("Aktivuji BLESK", "trigger_sfx_thunder"),
        "x": ("STOP zvuku", "trigger_stop_audio"),
        "c": ("Prepinam žárovky", "trigger_toggle_lights"),
        "i": ("Aktivuji LOSOVANI", "trigger_scene_drawing"),
        "t": ("Aktivuji VEČER", "trigger_scene_evening"),
        "a": ("Aktivuji VÝHRU ZLA", "trigger_scene_evil_won"),
        "q": ("Aktivuji VÝHRU DOBRA", "trigger_scene_good_won"),
        "e": ("Měním barvu zla", "trigger_set_evil_color"),
        "n": ("Jail", "trigger_effect_jail"),
        "j": ("Man", "trigger_effect_scream_man"),
        "k": ("Female", "trigger_effect_scream_woman"),
        "m": ("Clocks", "trigger_effect_clocks"),
        "g": ("Demon", "trigger_effect_demon"),
    }

    DEFAULT_MODIFIER_KEYS = {
        "d": "trigger_volume_up",
        "s": "trigger_volume_down",
        "minus": "trigger_volume_down",
        "kpminus": "trigger_volume_down",
    }

    # Class-level defaults for backward compatibility
    SCENE_KEYS = DEFAULT_SCENE_KEYS
    MODIFIER_KEYS = DEFAULT_MODIFIER_KEYS

    def __init__(
        self,
        scene_manager: "SceneManager",
        keyboard_select="auto",
        keymap_path=None,
        device_name=None,
    ):
        self.scene_manager: "SceneManager" = scene_manager
        self.running = True
        self.keyboard_select = keyboard_select
        self.keymap_path = keymap_path
        self.device_name = device_name
        self.SCENE_KEYS = dict(self.DEFAULT_SCENE_KEYS)
        self.MODIFIER_KEYS = dict(self.DEFAULT_MODIFIER_KEYS)
        self._load_keymap()
        self._validate_bindings()

    def _load_keymap(self):
        candidate_paths = []
        if self.keymap_path:
            candidate_paths.append(Path(self.keymap_path))
        else:
            candidate_paths.append(Path(__file__).resolve().parent.parent / "keymap.json")
            candidate_paths.append(Path("keymap.json"))
            candidate_paths.append(Path(__file__).resolve().parent.parent.parent / "keymap.json")

        for path in candidate_paths:
            if path.is_file():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    scene_keys = data.get("SCENE_KEYS")
                    modifier_keys = data.get("MODIFIER_KEYS")
                    if not self.device_name and data.get("DEVICE_NAME"):
                        self.device_name = data.get("DEVICE_NAME")
                    if isinstance(scene_keys, dict) and isinstance(modifier_keys, dict):
                        self.SCENE_KEYS = scene_keys
                        self.MODIFIER_KEYS = modifier_keys
                        print(f"[Input] Keymap loaded from {path}")
                        return
                    else:
                        print(f"[Input] Warning: {path} has invalid format, using default key bindings.")
                except Exception as e:
                    print(f"[Input] Warning: Failed to load keymap from {path}: {e}")

        print("[Input] No custom keymap found, using default key bindings.")

    def _validate_bindings(self):
        # Catches a typo'd or renamed trigger_* method at startup instead of
        # the first time someone happens to press that key.
        method_names = {name for _, name in self.SCENE_KEYS.values()}
        method_names |= set(self.MODIFIER_KEYS.values())
        missing = sorted(name for name in method_names if not hasattr(self.scene_manager, name))
        if missing:
            raise AttributeError(
                f"SceneManager is missing methods referenced in the key table: {missing}"
            )

    @staticmethod
    def _score_device_capabilities(device):
        """
        Hodnotí zařízení podle toho, jak moc odpovídá reálné klávesnici / numerickému bloku.
        Ignoruje myši, HDMI jacky, systémová/multimediální tlačítka s 1-2 klávesami.
        """
        if not HAS_EVDEV:
            return 0
        try:
            capabilities = device.capabilities(verbose=False)
        except Exception:
            return 0

        if ecodes.EV_KEY not in capabilities:
            return 0

        key_codes = set(capabilities[ecodes.EV_KEY])

        # Vyloučíme zařízení, která mají v názvu explicitně mouse/jack/system/consumer
        name_lower = device.name.lower()
        if any(ign in name_lower for ign in ["mouse", "consumer", "system control", "jack"]):
            return 0

        # Klávesy v evdev standardu (pod 256 jsou klasické klávesové kódy)
        keyboard_keys = [k for k in key_codes if k < 256]
        score = len(keyboard_keys)

        # Numerické klávesy (KP0-KP9, KPENTER, NUMLOCK, atd.)
        keypad_keys = {
            ecodes.KEY_KP0, ecodes.KEY_KP1, ecodes.KEY_KP2, ecodes.KEY_KP3,
            ecodes.KEY_KP4, ecodes.KEY_KP5, ecodes.KEY_KP6, ecodes.KEY_KP7,
            ecodes.KEY_KP8, ecodes.KEY_KP9, ecodes.KEY_KPENTER, ecodes.KEY_NUMLOCK,
            ecodes.KEY_KPPLUS, ecodes.KEY_KPMINUS, ecodes.KEY_KPASTERISK, ecodes.KEY_KPSLASH,
        }
        if key_codes & keypad_keys:
            score += 200

        # Běžné klávesy psacího stroje
        standard_keys = {
            ecodes.KEY_A, ecodes.KEY_B, ecodes.KEY_SPACE, ecodes.KEY_ENTER,
            ecodes.KEY_1, ecodes.KEY_2, ecodes.KEY_ESC,
        }
        if key_codes & standard_keys:
            score += 100

        return score

    def _select_keyboard_interactive(self):
        """Vypíše dostupná evdev zařízení a nechá uživatele vybrat jedno číslem."""
        if not HAS_EVDEV:
            print("Warning: evdev not found, interaktivní výběr zařízení není možný.")
            return None

        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

        if not devices:
            print("[Input] Nebyla nalezena žádná vstupní zařízení.")
            return None

        print("[Input] Dostupná zařízení:")
        for i, device in enumerate(devices):
            score = self._score_device_capabilities(device)
            hint = " [DOPORUČENO: Klávesnice/Keypad]" if score >= 50 else ""
            print(f"  [{i}] {device.name} ({device.path}){hint}")

        while True:
            choice = input("[Input] Zadej číslo klávesnice, kterou chceš použít: ").strip()
            if choice.isdigit() and 0 <= int(choice) < len(devices):
                return devices[int(choice)]
            print("[Input] Neplatná volba, zkus to znovu.")

    def _find_keyboard(self):
        """Vyhledá připojenou klávesnici mezi systémovými zařízeními."""
        if not HAS_EVDEV:
            print("Warning: evdev not found. Controller inputs will not work on this OS.")
            return None

        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        if not devices:
            return None

        # 1. Pokud je zadán specifický název (např. "Compx 2.4G Receiver")
        target_name = (self.device_name or "").strip().lower()
        if target_name and target_name != "auto":
            matching = [d for d in devices if target_name in d.name.lower()]
            if matching:
                scored = [(d, self._score_device_capabilities(d)) for d in matching]
                scored.sort(key=lambda x: x[1], reverse=True)
                best_device, best_score = scored[0]
                if best_score > 0:
                    return best_device
                # Pokud žádný neměl score > 0, vrátíme alespoň první matching
                return matching[0]

        # 2. Automatické vyhledání: vybereme zařízení s nejvyšším keyboard score
        scored_devices = [(d, self._score_device_capabilities(d)) for d in devices]
        scored_devices.sort(key=lambda x: x[1], reverse=True)

        best_device, best_score = scored_devices[0]
        if best_score > 0:
            return best_device

        return None

    async def start_listening(self):
        """Spustí asynchronní smyčku pro odchytávání stisků kláves."""
        if not HAS_EVDEV and HAS_PYNPUT:
            await self._start_listening_pynput()
            return

        while self.running:
            if self.keyboard_select == "interactive":
                keyboard = self._select_keyboard_interactive()
            else:
                keyboard = self._find_keyboard()

            if not keyboard:
                print(
                    "[Input] Klávesnice nenalezena, čekám 3 sekundy a zkouším znovu... "
                    "(Zkontroluj připojení USB přijímače a práva ke čtení /dev/input)"
                )
                await asyncio.sleep(3)
                continue

            print(
                f"[Input] Úspěšně připojeno ke klávesnici: {keyboard.name} ({keyboard.path})"
            )
            print("[Input] Naslouchám... Stiskni 'Q' pro ukončení.")

            try:
                # Asynchronní čtení událostí z kernelu
                async for event in keyboard.async_read_loop():
                    if not self.running:
                        return

                    # EV_KEY (klávesa) a hodnota 1 (stisknuto)
                    if event.type == ecodes.EV_KEY and event.value == 1:
                        key_name = evdev.ecodes.KEY.get(event.code, "UNKNOWN")
                        if isinstance(key_name, list):
                            key_name = key_name[0]

                        # Převedeme název (např. "KEY_N") na jednoduchý malý znak ("n")
                        key = key_name.replace("KEY_", "").lower()

                        await self._dispatch_key(key)

            except PermissionError:
                print(
                    "[Input] CHYBA: Nedostatečná práva pro čtení z klávesnice. "
                    "Přidej uživatele do skupiny 'input' (sudo usermod -aG input $USER) "
                    "a přihlas se znovu."
                )
                await asyncio.sleep(5)
            except OSError as e:
                print(f"[Input] Klávesnice odpojena ({e}), pokusím se znovu připojit...")
                await asyncio.sleep(2)
            except Exception as e:
                print(f"[Input] Neočekávaná chyba: {e}")
                await asyncio.sleep(2)

    async def _start_listening_pynput(self):
        """
        Windows keyboard listener
        """
        print("[Input] evdev nedostupný - používám pynput (pouze pro debug na Windows).")
        print("[Input] Naslouchám... Stiskni 'Q' pro ukončení.")

        loop = asyncio.get_running_loop()

        def on_press(key):
            try:
                char = key.char
            except AttributeError:
                return  # Speciální klávesy (shift, ctrl...) ignorujeme

            if char:
                loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(self._dispatch_key(char.lower()))
                )

        listener = pynput_keyboard.Listener(on_press=on_press)
        listener.start()

        try:
            while self.running:
                await asyncio.sleep(0.1)
        finally:
            listener.stop()

    async def _dispatch_key(self, key):
        """Rozcestník: na základě klávesy zavolá příslušnou metodu SceneManageru."""
        if key == "l":
            print("[Input] Ukončuji aplikaci...")
            # Zavoláme stop pro případ, že zrovna hrál zvuk nebo blikala světla
            self.scene_manager.trigger_stop()
            await asyncio.sleep(0.5)  # Krátká pauza na zpracování zhasnutí před exitem
            self.running = False
            return

        if key in self.SCENE_KEYS:
            label, method_name = self.SCENE_KEYS[key]
            print(f"[Input] Stisknuto '{key}' -> {label}")
            getattr(self.scene_manager, method_name)()

        elif key in self.MODIFIER_KEYS:
            getattr(self.scene_manager, self.MODIFIER_KEYS[key])()

        else:
            print(f"[Input] Klávesa '{key}' nemá přiřazenou žádnou akci.")
