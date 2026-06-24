from enum import Enum

from .AudioManager import AudioManager
from .BulbGroup import BulbGroup
from .SceneRunner import SceneContext, SceneRunner


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
        self.runner = SceneRunner()
        self.lights = BulbGroup(bulbs_config)
        print(f"[Scene] SceneManager připraven s {len(self.lights.bulbs)} žárovkami.")

    async def _broadcast(self, method_name, *args, **kwargs):
        # Forwards to BulbGroup; kept for scenes not yet migrated to lights.* verbs.
        await self.lights._broadcast(method_name, *args, **kwargs)

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

    def trigger_sfx_thunder(self):
        self.runner.run(self._scene_thunder(SceneContext()))

    async def _scene_thunder(self, ctx: SceneContext):
        self.audio.play_sfx("lightning", "01.wav")
        await self.lights.flash_lightning()

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

    def trigger_stop(self):
        self.runner.run(self._scene_stop(SceneContext()))

    async def _scene_stop(self, ctx: SceneContext):
        await self.lights.turn_off()

    def trigger_start(self):
        self.runner.run(self._scene_start(SceneContext()))

    async def _scene_start(self, ctx: SceneContext):
        await self.lights.turn_on()

    # Temporary proof scene for Phase 1, removed in Phase 4.
    def trigger_scene_demo(self):
        self.runner.run(self._scene_demo(SceneContext()))

    async def _scene_demo(self, ctx: SceneContext):
        await self.lights.fade_to_rgb(255, 0, 0)
        await ctx.sleep(4)
        await self.lights.fade_to_rgb(0, 255, 0)
