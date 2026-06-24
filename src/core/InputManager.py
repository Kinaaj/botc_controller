import asyncio

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
    # Scene keys go through SceneManager's runner-backed trigger_* methods (so
    # pressing one cancels-and-replaces whatever scene is currently active).
    # Real keypad codes aren't known yet (no keypad_mapping_spec.md in this
    # repo). g/e/v/w/c below are arbitrary test bindings, not the final spec
    # mapping - replace them once the physical keypad layout is known.
    SCENE_KEYS = {
        "n": ("Aktivuji NOC", "trigger_scene_night"),
        "d": ("Aktivuji DEN", "trigger_scene_day"),
        "p": ("Aktivuji POPRAVU", "trigger_effect_execution"),
        "b": ("Aktivuji BLESK", "trigger_sfx_thunder"),
        "s": ("STOP zvuku a reset světel", "trigger_stop"),
        "o": ("Zapínám žárovky", "trigger_start"),
        "f": ("Vypínám žárovky", "trigger_stop"),
        "g": ("Aktivuji KRESLENÍ", "trigger_scene_drawing"),
        "e": ("Aktivuji VEČER", "trigger_scene_evening"),
        "v": ("Aktivuji VÝHRU ZLA", "trigger_scene_evil_won"),
        "w": ("Aktivuji VÝHRU DOBRA", "trigger_scene_good_won"),
    }

    # Modifier keys call their SceneManager method directly and never touch
    # SceneRunner, so they can't interrupt whatever scene is active.
    # "equal"/"minus"/"kp..." are evdev's names for the real keypad's keys;
    # the bare "="/"-" cover pynput's raw-char reporting (Windows debug only).
    MODIFIER_KEYS = {
        "=": "trigger_volume_up",
        "equal": "trigger_volume_up",
        "kpplus": "trigger_volume_up",
        "-": "trigger_volume_down",
        "minus": "trigger_volume_down",
        "kpminus": "trigger_volume_down",
        "c": "trigger_set_evil_color",
    }

    def __init__(self, scene_manager: SceneManager, keyboard_select="auto"):
        self.scene_manager: SceneManager = scene_manager
        self.running = True
        self.keyboard_select = keyboard_select
        self._validate_bindings()

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
            print(f"  [{i}] {device.name} ({device.path})")

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

        # 1. Pokus: Hledáme zařízení, které má v názvu explicitně "keyboard"
        for device in devices:
            if "keyboard" in device.name.lower():
                return device

        # 2. Pokus: Pokud nic nenašel (některé integrované ntb klávesnice se jmenují jinak),
        # vezme první dostupné zařízení, které podporuje klávesy
        for device in devices:
            capabilities = device.capabilities()
            if ecodes.EV_KEY in capabilities:
                return device

        return None

    async def start_listening(self):
        """Spustí asynchronní smyčku pro odchytávání stisků kláves."""
        if not HAS_EVDEV and HAS_PYNPUT:
            await self._start_listening_pynput()
            return

        if self.keyboard_select == "interactive":
            keyboard = self._select_keyboard_interactive()
        else:
            keyboard = self._find_keyboard()

        if not keyboard:
            print("[Input] KRITICKÁ CHYBA: Nepodařilo se najít žádnou klávesnici!")
            print(
                "Zkontroluj práva ke čtení z /dev/input - přidej uživatele do skupiny "
                "'input' (sudo usermod -aG input $USER) a přihlas se znovu."
            )
            return

        print(
            f"[Input] Úspěšně připojeno ke klávesnici: {keyboard.name} ({keyboard.path})"
        )
        print("[Input] Naslouchám... Stiskni 'Q' pro ukončení.")

        try:
            # Asynchronní čtení událostí z kernelu
            async for event in keyboard.async_read_loop():
                if not self.running:
                    break

                # Zajímá nás pouze typ události EV_KEY (klávesa) a hodnota 1 (stisknuto)
                # Hodnota 0 je uvolnění klávesy, hodnota 2 je držení klávesy
                if event.type == ecodes.EV_KEY and event.value == 1:
                    key_name = evdev.ecodes.KEY[event.code]

                    # Převedeme název (např. "KEY_N") na jednoduchý malý znak ("n")
                    key = key_name.replace("KEY_", "").lower()

                    await self._dispatch_key(key)

        except PermissionError:
            print(
                "[Input] CHYBA: Nedostatečná práva pro čtení z klávesnice. "
                "Přidej uživatele do skupiny 'input' (sudo usermod -aG input $USER) "
                "a přihlas se znovu."
            )
        except Exception as e:
            print(f"[Input] Neočekávaná chyba: {e}")

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
        if key == "q":
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
