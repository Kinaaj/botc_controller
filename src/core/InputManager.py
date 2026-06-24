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
    def __init__(self, scene_manager: SceneManager, keyboard_select="auto"):
        self.scene_manager: SceneManager = scene_manager
        self.running = True
        self.keyboard_select = keyboard_select

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
        """Rozcestník: Na základě klávesy spustí příslušnou scénu."""
        if key == "q":
            print("[Input] Ukončuji aplikaci...")
            # Zavoláme stop pro případ, že zrovna hrál zvuk nebo blikala světla
            self.scene_manager.trigger_stop()
            await asyncio.sleep(0.5)  # Krátká pauza na zpracování zhasnutí před exitem
            self.running = False
            return

        # All trigger_* methods are sync now: they hand off to SceneRunner (or,
        # for modifiers, run immediately) and return right away.
        if key == "n":
            print("[Input] Stisknuto N -> Aktivuji NOC")
            self.scene_manager.trigger_scene_night()

        elif key == "d":
            print("[Input] Stisknuto D -> Aktivuji DEN")
            self.scene_manager.trigger_scene_day()

        elif key == "p":
            print("[Input] Stisknuto P -> Aktivuji POPRAVU")
            self.scene_manager.trigger_effect_execution()

        elif key == "b":
            print("[Input] Stisknuto B -> Aktivuji BLESK")
            self.scene_manager.trigger_sfx_thunder()

        elif key == "s":
            print("[Input] Stisknuto S -> STOP zvuku a reset světel")
            self.scene_manager.trigger_stop()

        elif key == "o":
            print("[Input] Stisknuto O -> Zapinam zarovky")
            self.scene_manager.trigger_start()
        elif key == "f":
            print("[Input] Stisknuto F -> Vypinam zarovky")
            self.scene_manager.trigger_stop()

        # Volume is a modifier: it never goes through SceneRunner, so it can't
        # interrupt a running scene. "equal"/"minus" are evdev's names for the
        # main-row +/- keys; pynput (Windows debug fallback) reports the raw char.
        elif key in ("=", "equal", "kpplus"):
            self.scene_manager.trigger_volume_up()

        elif key in ("-", "minus", "kpminus"):
            self.scene_manager.trigger_volume_down()

        else:
            print(f"[Input] Klávesa '{key}' nemá přiřazenou žádnou akci.")
