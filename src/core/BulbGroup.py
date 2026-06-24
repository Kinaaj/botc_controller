import asyncio

from .YeelightControllerLib import YeelightControllerLib


class BulbGroup:
    """Drives all bulbs in lockstep and exposes scene-level verbs instead of raw method names."""

    def __init__(self, bulbs_config):
        self.bulbs = [YeelightControllerLib(b["ip"], b["name"]) for b in bulbs_config]

    async def _broadcast(self, method_name, *args, **kwargs):
        tasks = [
            getattr(bulb, method_name)(*args, **kwargs)
            for bulb in self.bulbs
            if hasattr(bulb, method_name)
        ]
        if tasks:
            await asyncio.gather(*tasks)

    async def connect_all(self):
        await self._broadcast("connect")

    async def close_all(self):
        await self._broadcast("close")

    async def turn_on(self):
        await self._broadcast("turn_on")

    async def turn_off(self):
        await self._broadcast("turn_off")

    async def fade_off(self, seconds=2.0):
        await self._broadcast("turn_off", duration=int(seconds * 1000))

    async def fade_up(self, seconds=2.0, brightness=100):
        await self._broadcast("turn_on")
        await self._broadcast("set_brightness", brightness, duration=int(seconds * 1000))

    async def fade_to_rgb(self, r, g, b, seconds=0.5):
        await self._broadcast("set_rgb", r, g, b, duration=int(seconds * 1000))

    async def set_temperature(self, kelvin, seconds=2.0):
        await self._broadcast("set_temperature", kelvin, duration=int(seconds * 1000))

    async def flash_lightning(self):
        await self._broadcast("flash_lightning")
