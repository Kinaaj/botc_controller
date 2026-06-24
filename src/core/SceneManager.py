from .AudioManager import AudioManager
from .BulbGroup import BulbGroup
from .GameState import GameState
from .SceneRunner import SceneContext, SceneRunner

VOLUME_STEP = 0.05


class SceneManager:
    def __init__(self, bulbs_config, audio_manager: AudioManager, game_state: GameState, normal_color):
        self.audio = audio_manager
        self.state = game_state
        self.normal_color = tuple(normal_color)
        self.runner = SceneRunner()
        self.lights = BulbGroup(bulbs_config)
        self._execution_presses = 0
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
            self.audio.play_tracked_sfx("drawing", "drawing.wav", tag="drawing", loops=-1)
            while True:
                r, g, b = self.state.evil_color
                await self.lights.fade_to_rgb(r, g, b, seconds=crossfade_seconds)
                await ctx.sleep(crossfade_seconds + hold_seconds)

                nr, ng, nb = self.normal_color
                await self.lights.fade_to_rgb(nr, ng, nb, seconds=crossfade_seconds)
                await ctx.sleep(crossfade_seconds + hold_seconds)
        finally:
            self.audio.stop_tracked_sfx("drawing", fade_ms=500)

    def trigger_scene_night(self):
        self._start_scene(self._scene_night)

    async def _scene_night(self, ctx: SceneContext):
        fade_off_seconds = 2
        fade_up_seconds = 4
        try:
            await self.lights.fade_off(seconds=fade_off_seconds)
            await ctx.sleep(fade_off_seconds)  # let bulbs actually go dark first

            self.audio.play_sfx("ambient", "gong.wav")
            self.audio.play_permanent_ambient("ambient", "night_crickets_1h.mp3", volume=0.3)
            await ctx.sleep(3)  # blackout pause

            r, g, b = self.state.evil_color
            await self.lights.fade_up_to_rgb(r, g, b, seconds=fade_up_seconds)
            await self.audio.start_night_sequence([], "night")
            await ctx.wait_forever()  # Night stays active until another scene interrupts it
        finally:
            self.audio.stop_permanent_ambient()

    def trigger_scene_day(self):
        self._start_scene(self._scene_day)

    async def _scene_day(self, ctx: SceneContext):
        await self.lights.fade_off(seconds=4)
        self.audio.start_day("day")

    def trigger_scene_evening(self):
        self._start_scene(self._scene_evening)

    async def _scene_evening(self, ctx: SceneContext):
        warm_kelvin = 2700
        fade_up_seconds = 8
        await self.lights.fade_off(seconds=1)
        await ctx.sleep(1)
        await self.lights.fade_up_to_temperature(warm_kelvin, seconds=fade_up_seconds)

    def trigger_effect_clock(self):
        return

    async def trigger_effect_voting(self):
        return

    def trigger_effect_jail(self):
        return

    def trigger_sfx_thunder(self):
        self._start_scene(self._scene_thunder)

    async def _scene_thunder(self, ctx: SceneContext):
        self.audio.play_sfx("lightning", "01.wav")
        await self.lights.flash_lightning()

    def trigger_effect_execution(self):
        self._execution_presses += 1
        if self._execution_presses >= 2:
            self._execution_presses = 0
            self._start_scene(self._scene_execution_behead, is_execution=True)
        else:
            self._start_scene(self._scene_execution_crowd, is_execution=True)

    async def _scene_execution_crowd(self, ctx: SceneContext):
        try:
            self.audio.play_tracked_sfx("execution", "crowd.wav", tag="execution_crowd", loops=-1)
            await ctx.wait_forever()
        finally:
            # Cancelled either by the 2nd press (the "silence" beat) or by an
            # unrelated scene taking over - both want the crowd cut immediately.
            self.audio.stop_tracked_sfx("execution_crowd", fade_ms=0)

    async def _scene_execution_behead(self, ctx: SceneContext):
        self.audio.play_sfx("execution", "behead.wav")
        await self.lights.fade_to_rgb(255, 0, 0, seconds=0.3)
        await ctx.sleep(2)
        await self.lights.fade_off(seconds=2)

    def trigger_effect_scream_woman(self):
        return

    def trigger_effect_scream_man(self):
        return

    def trigger_set_evil_color(self):
        self.state.next_evil_color()

    def trigger_scene_evil_won(self):
        self._start_scene(self._scene_evil_won)

    async def _scene_evil_won(self, ctx: SceneContext):
        r, g, b = self.state.evil_color
        await self.lights.fade_to_rgb(r, g, b, seconds=6)

    def trigger_scene_good_won(self):
        # Same warm fade-up as Evening.
        self._start_scene(self._scene_evening)

    def trigger_volume_up(self):
        self.state.volume += VOLUME_STEP
        self.audio.set_volume(self.state.volume)

    def trigger_volume_down(self):
        self.state.volume -= VOLUME_STEP
        self.audio.set_volume(self.state.volume)

    def trigger_stop(self):
        self._start_scene(self._scene_stop)

    async def _scene_stop(self, ctx: SceneContext):
        self.audio.stop_all()
        await self.lights.turn_off()

    def trigger_start(self):
        self._start_scene(self._scene_start)

    async def _scene_start(self, ctx: SceneContext):
        await self.lights.turn_on()
