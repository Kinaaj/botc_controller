import asyncio

from .Bulb import Bulb


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
        # Yeelight doesn't reliably show a color set while off once powered
        # back on (depends on the bulb's own power-on-behavior setting), so
        # color/brightness must be sent after turn_on, not staged before it.
        await self._broadcast("turn_on", duration=int(seconds * 1000))
        await self._broadcast("set_rgb", r, g, b, duration=int(seconds * 1000))
        await self._broadcast("set_brightness", brightness, duration=int(seconds * 1000))

    async def fade_up_to_temperature(self, kelvin, seconds=2.0, brightness=100):
        await self._broadcast("turn_on", duration=int(seconds * 1000))
        await self._broadcast("set_temperature", kelvin, duration=int(seconds * 1000))
        await self._broadcast("set_brightness", brightness, duration=int(seconds * 1000))

    async def fade_to_rgb(self, r, g, b, seconds=0.5):
        await self._broadcast("set_rgb", r, g, b, duration=int(seconds * 1000))

    async def set_temperature(self, kelvin, seconds=2.0):
        await self._broadcast("set_temperature", kelvin, duration=int(seconds * 1000))

    async def flash_lightning(self):
        await self._broadcast("flash_lightning")
