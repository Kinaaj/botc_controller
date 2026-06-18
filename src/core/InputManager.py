import asyncio
import evdev
from evdev import ecodes


class InputManager:
    def __init__(self, scene_manager):
        self.scene_manager = scene_manager
        self.running = True

    def _find_keyboard(self):
        """Vyhledá připojenou klávesnici mezi systémovými zařízeními."""
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
            print("Zkontroluj, zda skript spouštíš jako ROOT (sudo python3 main.py).")
            return

        print(f"[Input] Úspěšně připojeno ke klávesnici: {keyboard.name} ({keyboard.path})")
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
            print("[Input] CHYBA: Nedostatečná práva pro čtení z klávesnice. Spusť program přes 'sudo'.")
        except Exception as e:
            print(f"[Input] Neočekávaná chyba: {e}")

    async def _dispatch_key(self, key):
        """Rozcestník: Na základě klávesy spustí příslušnou scénu."""
        if key == 'q':
            print("[Input] Ukončuji aplikaci...")
            self.running = False
            return

        # Spouštíme scény asynchronně jako samostatné Tasky.
        # Díky tomu se okamžitě vracíme k naslouchání a můžeme reagovat na další klávesy.
        if key == 'n':
            asyncio.create_task(self.scene_manager.trigger_scene_night())
        elif key == 'd':
            asyncio.create_task(self.scene_manager.trigger_scene_day())
        elif key == 'p':
            asyncio.create_task(self.scene_manager.trigger_scene_execution())
        elif key == 's':
            # Příklad pro rychlý "jump scare" zvukový efekt bez změny světel
            asyncio.create_task(self.scene_manager.trigger_sfx_scream())
        else:
            print(f"[Input] Klávesa '{key}' nemá přiřazenou žádnou akci.")