import asyncio
import random

from .AudioPaths import SFX, BGM
from .AudioManager import AudioManager
from .BulbGroup import BulbGroup
from .GameState import GameState
from .SceneRunner import SceneContext, SceneRunner
from .BulbState import BulbStateType

VOLUME_STEP = 0.05


class SceneManager:
    def __init__(self, bulbs_config, audio_manager: AudioManager, game_state: GameState):
        self.audio = audio_manager
        self.state = game_state
        self.runner = SceneRunner()
        self.lights = BulbGroup(bulbs_config)
        self._execution_presses = 0
        self._execution_effect_delay = 0.6
        self._lights_on = True  # Přidán výchozí stav světel
        print(f"[Scene] SceneManager připraven s {len(self.lights.bulbs)} žárovkami.")

    def _start_scene(self, scene_fn, *, is_execution=False):
        # Per spec: any scene other than Execution clears its press count, so a
        # stray earlier press can't carry over into an unrelated later one.
        if not is_execution:
            self._execution_presses = 0
        self.runner.run(scene_fn(SceneContext()))

    # --- HERNÍ SCÉNY ---

    def trigger_scene_drawing(self):
        self._start_scene(self._scene_drawing)

    async def _scene_drawing(self, ctx: SceneContext):
        crossfade_seconds = 3
        hold_seconds = 2
        try:
            self.audio.play_tracked_sfx(category_class=SFX.Other.Drawing, tag="drawing", loops=-1, volume=self.state.volume)
            while True:
                r, g, b = self.state.evil_color
                await self.lights.fade_to_rgb(r, g, b, seconds=crossfade_seconds)
                await ctx.sleep(crossfade_seconds + hold_seconds)

                await self.lights.fade_up_to_temperature(self.state.normal_temperature, seconds=crossfade_seconds)
                
                await ctx.sleep(crossfade_seconds + hold_seconds)
        finally:
            self.audio.stop_tracked_sfx(tag="drawing", fade_ms=500)

    def trigger_scene_night(self):
        self._start_scene(self._scene_night)

    async def _scene_night(self, ctx: SceneContext):
        self.state.default_bulb_state.state_type = BulbStateType.RGB

        fade_off_seconds = 2
        fade_up_seconds = 4
        try:
            await self.lights.fade_off(seconds=fade_off_seconds)
            await ctx.sleep(fade_off_seconds)  # let bulbs actually go dark first

            # 1. Pustíme ambient a random zvuk hned na začátku (tyto funkce neblokují běh programu)
            if random.random() < 0.10:
                print("[Scene] Pouštím náhodný noční efekt...")
                self.audio.play_sfx(SFX.Night.Effects)
            self.audio.play_permanent_ambient(category_class=SFX.Night.Ambient, volume=self.state.volume)

            # 2. Nyní pustíme zvony. Program se zde zastaví a počká, než dohraje intro,
            #    ale ambient a random efekty už mezitím vesele hrají na pozadí!
            await self.audio.start_night_sequence(intro_sfx_list=[SFX.Night.Bells], bgm_class=BGM.Night)
            
            r, g, b = self.state.evil_color
            await self.lights.fade_up_to_rgb(r, g, b, seconds=fade_up_seconds)
            await ctx.wait_forever()  # Night stays active until another scene interrupts it
        finally:
            self.audio.stop_permanent_ambient()
            self.audio.stop_night_sequence()

    def trigger_scene_day(self):
        self._start_scene(self._scene_day)

    async def _scene_day(self, ctx: SceneContext):
        try:
            self.state.default_bulb_state.state_type = BulbStateType.TEMPERATURE
            await self.lights.fade_off(seconds=2.2)
            self.audio.play_tracked_sfx(SFX.Day.Morning_Ambient, tag = "morning_ambient", volume = self.state.volume, fade_ms = 400)
        finally:
            self.audio.stop_tracked_sfx(tag="morning_ambient")
    def trigger_scene_evening(self):
        self._start_scene(self._scene_evening)

    async def _scene_evening(self, ctx: SceneContext):
        self.state.default_bulb_state.state_type = BulbStateType.TEMPERATURE
        fade_up_seconds = 4
        await self.lights.fade_off(seconds=1)
        await ctx.sleep(1)
        await self.lights.fade_up_to_temperature(self.state.normal_temperature, seconds=fade_up_seconds)

    def trigger_effect_clock(self):
        self.audio.play_sfx(SFX.Day.Clocks)
        return

    def trigger_effect_jail(self):
        self.audio.play_sfx(SFX.Day.Jail)
        return

    def trigger_effect_execution(self):
        self._execution_presses += 1
        if self._execution_presses >= 2:
            self._execution_presses = 0
            self._start_scene(self._scene_execution_behead, is_execution=True)
        else:
            self._start_scene(self._scene_execution_crowd, is_execution=True)

    async def _scene_execution_crowd(self, ctx: SceneContext):
        my_channel = self.audio.play_tracked_sfx(SFX.Day.Crowd, loops=-1, volume=self.state.volume)
        
        try:
            print("[Scene] Spouštím atmosféru davu k popravě...")
            await ctx.wait_forever()
        finally:
            self.audio.stop_tracked_sfx(SFX.Day.Crowd, fade_ms=80, specific_channel=my_channel, delay_ms=620)

    async def _scene_execution_behead(self, ctx: SceneContext):
        print("[Scene] Spouštím gilotinu a krvavý záblesk...")
        self.audio.play_tracked_sfx(category_class=SFX.Day.Gilotina, volume=self.state.volume)
        await self.lights.flash_blood(255, 0, 0, delay=600, default_bulb_state=self.state.default_bulb_state)

    def trigger_effect_clocks(self):
        self.audio.play_sfx(SFX.Day.Clocks)
        return

    def trigger_set_evil_color(self):
        self._start_scene(self._scene_set_evil_color)

    async def _scene_set_evil_color(self, ctx: SceneContext):
        r, g, b = self.state.next_evil_color()
        await self.lights.fade_to_rgb(r, g, b, seconds=0.5)

    def trigger_scene_evil_won(self):
        self._start_scene(self._scene_evil_won)

    async def _scene_evil_won(self, ctx: SceneContext):
        try:
        
            fade_up_seconds = 14

            r, g, b = self.state.evil_color
            self.state.default_bulb_state.state_type = BulbStateType.RGB
            
            self.audio.play_tracked_sfx(SFX.Evil_Win, tag="evil_win", fade_ms=1500, volume=self.state.volume)
            await self.lights.fade_up_to_rgb(r, g, b, seconds=fade_up_seconds)
            await ctx.wait_forever()  # Night stays active until another scene interrupts it
        finally:
            self.audio.stop_tracked_sfx(tag="evil_win")

    def trigger_scene_good_won(self):
        self._start_scene(self._scene_good_won)
        
    async def _scene_good_won(self, ctx:SceneContext):
        try:
            self.state.default_bulb_state.state_type = BulbStateType.TEMPERATURE
            fade_up_seconds = 10
            await self.lights.fade_off(seconds=0.5)
            await ctx.sleep(0.5)
            await self.lights.fade_up_to_temperature(self.state.normal_temperature, seconds=fade_up_seconds)
            
            self.audio.play_tracked_sfx(SFX.Good_Win, tag = "good_win", fade_ms=1500, volume=self.state.volume)
            await ctx.wait_forever()  # Night stays active until another scene interrupts it
        finally:
            self.audio.stop_tracked_sfx(tag="good_win")


    def trigger_volume_up(self):
        self.state.volume = min(1.0, self.state.volume + VOLUME_STEP)
        self.audio.set_volume(self.state.volume)

    def trigger_volume_down(self):
        self.state.volume = max(0.0, self.state.volume - VOLUME_STEP)
        self.audio.set_volume(self.state.volume)

    def trigger_stop_audio(self):
        """Zastaví veškerou hudbu/sfx na jedno zavolání."""
        print("[Audio] Zastavuji veškerou hudbu.")
        self.audio.stop_all()

    def trigger_start(self):
        self._start_scene(self._scene_start)
    
    def trigger_stop(self):
        self._start_scene(self._scene_stop)
        
    async def _scene_stop(self, ctx: SceneContext):  # Zde chybělo 'ctx: SceneContext'
        self._lights_on = False
        await self.lights.turn_off()
        self.audio.stop_all()

    async def _scene_start(self, ctx: SceneContext):
        await self.lights.turn_on()
        self._lights_on = True
        
    def trigger_toggle_lights(self):
        """Přepíná světla: zapnuto -> vypnuto, vypnuto -> zapnuto."""
        self._start_scene(self._scene_toggle_lights)
        
    async def _scene_toggle_lights(self, ctx: SceneContext):
        if self._lights_on:
            await self.lights.turn_off()
            self._lights_on = False
            print("[Scene] Světla vypnuta.")
        else:
            await self.lights.turn_on()
            self._lights_on = True
            print("[Scene] Světla zapnuta.")

# --- JEDNORÁZOVÉ A VIZUÁLNÍ EFEKTY (Nijak nepřeruší Noc/Den) ---

    def trigger_sfx_thunder(self):
        # OPRAVA: Místo _start_scene to odpálíme jako nezávislý úkol na pozadí!
        # Tím pádem Noc dál vesele běží ve SceneRunneru a Blesk si jen "blikne" přes ni.
        asyncio.create_task(self._scene_thunder())

    async def _scene_thunder(self):
        # Už nepotřebujeme ctx: SceneContext, jen pustíme zvuk a blikneme
        self.audio.play_sfx(category_class=SFX.Other.Lightning)
        await self.lights.flash_lightning(self.state.default_bulb_state)

    def trigger_effect_demon(self):
        # OPRAVA: Odstraněno 'async def'. Přehrání SFX zvuků v AudioManageru 
        # není asynchronní, takže obyčejný 'def' je přesně to, co potřebujeme.
        self.audio.play_sfx(SFX.Night.Demon)

    def trigger_effect_scream_woman(self):
        # Zde už to máš správně (nepoužíváš _start_scene)
        self.audio.play_sfx(SFX.Other.Scream_Woman)

    def trigger_effect_scream_man(self):
        # Zde už to máš správně
        self.audio.play_sfx(SFX.Other.Scream_Man)