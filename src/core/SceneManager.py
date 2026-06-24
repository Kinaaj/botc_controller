import asyncio
from enum import Enum

from .AudioManager import AudioManager
from .YeelightControllerLib import YeelightControllerLib


class Scene(Enum):
    NONE = 0
    DRAWING = 1
    NIGHT = 2
    DAY = 3
    EVENING = 4
    EXECUTION = 5
    EVIL_WON = 6
    GOOD_WON = 7


class SceneManager:
    def __init__(self, bulbs_config, audio_manager: AudioManager):
        self.audio = audio_manager
        self.current_scene = Scene.NONE
        self.last_scene = Scene.NONE

        # Inicializace 4 controllerů pro žárovky z YAML konfigurace
        self.bulbs = [YeelightControllerLib(b["ip"], b["name"]) for b in bulbs_config]
        print(f"[Scene] SceneManager připraven s {len(self.bulbs)} žárovkami.")

    async def _broadcast(self, method_name, *args, **kwargs):
        """
        Pomocná metoda, která vezme název metody z YeelightControlleru
        (např. 'set_rgb') a spustí ji na všech žárovkách ZÁROVEŇ.
        """
        tasks = []
        for bulb in self.bulbs:
            # Získáme konkrétní funkci z objektu žárovky podle názvu
            func = getattr(bulb, method_name, None)
            if func:
                tasks.append(func(*args, **kwargs))

        # Odeslání všech příkazů do sítě paralelně
        if tasks:
            await asyncio.gather(*tasks)

    async def _set_default_lights(self):
        # TODO
        return

    # --- HERNÍ SCÉNY ---

    async def trigger_scene_drawing(self):
        if self.current_scene != Scene.DRAWING:
            self.audio.play_tracked_sfx("drawing", "drawing.wav", tag="drawing")
            await self._broadcast("drawing_effect")
        else:
            self.audio.stop_tracked_sfx("drawing", "drawing.wav", tag="drawing")
            await self._set_default_lights()
            self.current_scene = Scene.NONE
        return

    async def trigger_scene_night(self):
        # TODO: self._broadcast
        self.audio.start_night_sequence()
        return

    async def trigger_scene_day(self):
        # TODO: self._broadcast

        return

    async def trigger_scene_evening(self):
        return

    def trigger_effect_clock(self):
        return

    async def trigger_effect_voting(self):
        return

    def trigger_effect_jail(self):
        return

    async def trigger_sfx_thunder(self):
        self.audio.play_sfx("lightning", "01.wav", volume=1.0)
        await self._broadcast("flash_lightning")

    async def trigger_effect_execution(self):
        return

    def trigger_effect_scream_woman(self):
        return

    def trigger_effect_scream_man(self):
        return

    async def trigger_set_evil_color(self):
        return

    async def trigger_scene_evil_won(self):
        return

    async def trigger_scene_good_won(self):
        return

    def trigger_volume_up(self):
        return

    def trigger_volume_down(self):
        return

    async def trigger_stop(self):
        await self._broadcast("turn_off")
        return

    async def trigger_start(self):
        await self._broadcast("turn_on")
        return

    # OLD SCENES:

    async def trigger_scene_night_OLD(self):
        """Klávesa N: Noc (Temná modrá, gong, cvrčci a noční playlist)."""
        print("\n=== SCÉNA: NOC ZAČÍNÁ ===")

        # 1. Světla: Zapnout (pro jistotu), tmavě modrá (RGB: 0, 0, 255), jas 10%
        await self._broadcast("turn_on")
        await self._broadcast("set_rgb", 0, 0, 255, duration=2000)
        await self._broadcast("set_brightness", 10)

        # 2. Zvuk: Permanentní ambient (např. cvrčci v lese) tiše na pozadí
        self.audio.play_permanent_ambient(
            "ambients", "night_crickets_1h.mp3", volume=0.3
        )

        # 3. Zvuk: Úvodní gong a následný plynulý přechod do noční hudby
        intro_zvuky = [("ambient", "gong.wav")]
        await self.audio.start_night_sequence(intro_zvuky, "night")

    async def trigger_scene_day_OLD(self):
        """Klávesa D: Den (Teplá bílá, denní playlist)."""
        print("\n=== SCÉNA: DEN ZAČÍNÁ ===")

        # 1. Světla: Teplá bílá barva (např. RGB 255, 200, 100), plný jas
        await self._broadcast("turn_on")
        await self._broadcast("set_rgb", 255, 200, 100, duration=2000)
        await self._broadcast("set_brightness", 100)

        # 2. Zvuk: Start denní hudby (např. probuzení vesnice, ptáci)
        self.audio.start_day("day")

    async def trigger_scene_execution_OLD(self):
        """Klávesa P: Poprava hráče (Křik, červené bliknutí a zhasnutí)."""
        print("\n=== SCÉNA: POPRAVA ===")

        # 1. Zvuk: Rychlý výkřik
        self.audio.play_sfx("events", "scream.wav", volume=1.0)

        # 2. Světla: Blesková změna na krvavě červenou
        await self._broadcast("set_rgb", 255, 0, 0, duration=300)
        await self._broadcast("set_brightness", 100)

        # 3. Chvíli svítí červeně, pak světla zhasnou (smrt)
        await asyncio.sleep(2)
        await self._broadcast("turn_off")

    async def trigger_sfx_thunder_OLD(self):
        """Klávesa B: Úder blesku (Hrom + stroboskop)."""
        print("\n=== EFEKT: BLESK ===")

        # 1. Zvuk: Hrom (hraje přes cokoliv, co zrovna běží)
        self.audio.play_sfx("lightning", "01.wav", volume=1.0)

        # 2. Světla: Spuštění naší naprogramované sekvence (color flow) z PDF
        await self._broadcast("flash_lightning")

    async def trigger_stop_OLD(self):
        """Klávesa Q nebo S: Reset všeho (Zastaví zvuk, rozsvítí normálně)."""
        print("\n=== STOP VŠEHO ===")

        # Zastavení veškerého audia
        self.audio.stop_all()

        # Rozsvícení světel na neutrální stav (např. běžná bílá na čtení)
        await self._broadcast("turn_on")
        await self._broadcast("set_rgb", 255, 255, 255, duration=1000)
        await self._broadcast("set_brightness", 50)
