import asyncio

try:
    import evdev
    from evdev import ecodes

    HAS_EVDEV = True
except ImportError:
    HAS_EVDEV = False
    print("Warning: evdev not found. Controller inputs will not work on this OS.")


class InputManager:
    def __init__(self, scene_manager):
        self.scene_manager = scene_manager
        self.running = True

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

    async def _dispatch_key(self, key):
        """Rozcestník: Na základě klávesy spustí příslušnou scénu."""
        if key == "q":
            print("[Input] Ukončuji aplikaci...")
            # Zavoláme stop pro případ, že zrovna hrál zvuk nebo blikala světla
            asyncio.create_task(self.scene_manager.trigger_stop())
            await asyncio.sleep(0.5)  # Krátká pauza na zpracování zhasnutí před exitem
            self.running = False
            return

        # Spouštíme scény asynchronně jako samostatné Tasky.
        # Díky tomu se okamžitě vracíme k naslouchání a můžeme reagovat na další klávesy.
        if key == "n":
            print("[Input] Stisknuto N -> Aktivuji NOC")
            asyncio.create_task(self.scene_manager.trigger_scene_night())

        elif key == "d":
            print("[Input] Stisknuto D -> Aktivuji DEN")
            asyncio.create_task(self.scene_manager.trigger_scene_day())

        elif key == "p":
            print("[Input] Stisknuto P -> Aktivuji POPRAVU")
            asyncio.create_task(self.scene_manager.trigger_scene_execution())

        elif key == "b":
            print("[Input] Stisknuto B -> Aktivuji BLESK")
            asyncio.create_task(self.scene_manager.trigger_sfx_thunder())

        elif key == "s":
            print("[Input] Stisknuto S -> STOP zvuku a reset světel")
            asyncio.create_task(self.scene_manager.trigger_stop())

        else:
            print(f"[Input] Klávesa '{key}' nemá přiřazenou žádnou akci.")
