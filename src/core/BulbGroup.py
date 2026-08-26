import asyncio

from yeelight import Bulb as YeelightBulb, Flow, TemperatureTransition, SleepTransition, RGBTransition
from .Bulb import Bulb
from .BulbState import BulbState


class BulbGroup:
    """Drives all bulbs in lockstep and exposes scene-level verbs instead of raw method names."""

    def __init__(self, bulbs_config):
        self.bulbs = [Bulb(b["ip"], b["name"]) for b in bulbs_config]

    async def _broadcast(self, method_name, *args, **kwargs):
        tasks = [
            getattr(bulb, method_name)(*args, **kwargs)
            for bulb in self.bulbs
            if hasattr(bulb, method_name)
        ]
        if tasks:
            return await asyncio.gather(*tasks)
        return []

    async def connect_all(self):
        # The one place reachability errors are worth surfacing: at boot, so a
        # powered-off bulb is visible immediately instead of failing silently
        # the first time a scene tries to use it.
        results = await self._broadcast("connect")
        for bulb, reachable in zip(self.bulbs, results):
            status = "OK" if reachable else "NEDOSTUPNÁ"
            print(f"[BulbGroup] {bulb.name} ({bulb.ip}): {status}")
        return results

    async def close_all(self):
        await self._broadcast("close")

    async def turn_on(self):
        await self._broadcast("turn_on")

    async def turn_off(self):
        await self._broadcast("turn_off")

    async def fade_off(self, seconds=2.0):
        await self._broadcast("turn_off", duration=int(seconds * 1000))

    async def fade_up_to_rgb(self, r, g, b, seconds=2.0, brightness=100):
        # 1. Bleskové zapnutí, aby žárovka mohla přijímat další příkazy
        await self._broadcast("turn_on", duration=int(seconds * 1000))
        
        # 2. Vytvoření jednoho plynulého přechodu pro barvu i jas současně
        flow = Flow(
            count=1,
            action=Flow.actions.stay,
            transitions=[
                RGBTransition(r, g, b, duration=int(seconds * 1000), brightness=brightness)
            ]
        )
        
        # Odeslání jediného sloučeného příkazu
        await self._broadcast("start_flow", flow)

    async def fade_up_to_temperature(self, kelvin, seconds=2.0, brightness=100):
        # 1. Zapnutí
        await self._broadcast("turn_on", duration=int(seconds * 1000))
        
        # 2. Vytvoření jednoho plynulého přechodu pro teplotu bílé (CT) i jas současně
        flow = Flow(
            count=1,
            action=Flow.actions.stay,
            transitions=[
                TemperatureTransition(kelvin, duration=int(seconds * 1000), brightness=brightness)
            ]
        )
        
        # Odeslání sloučeného příkazu
        await self._broadcast("start_flow", flow)
    
    async def fade_to_rgb(self, r, g, b, seconds=0.5):
        await self._broadcast("set_rgb", r, g, b, duration=int(seconds * 1000))

    async def set_temperature(self, kelvin, seconds=2.0):
        await self._broadcast("set_temperature", kelvin, duration=int(seconds * 1000))

    async def flash_lightning(self, target_state: BulbState):
        await self._broadcast("flash_lightning", target_state)

    async def flash_blood(self, r, g, b, delay, default_bulb_state):
        print("FLASH 2")
        await self._broadcast("flash_color", r, g, b, delay, default_bulb_state)
