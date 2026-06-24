import asyncio

from yeelight import Bulb as YeelightBulb, Flow
from yeelight.flow import SleepTransition, TemperatureTransition
from yeelight.main import BulbException


class Bulb:
    def __init__(self, ip, name, port=55443):
        self.ip = ip
        self.name = name
        self.port = port
        self.bulb = YeelightBulb(ip, port=port, duration=30, auto_on=False)

    async def connect(self):
        # Querying properties is the only command that requires an actual
        # round-trip, so it doubles as a reachability probe at startup.
        try:
            await asyncio.to_thread(self.bulb.get_properties)
            return True
        except (BulbException, OSError) as e:
            print(f"[{self.name}] Communication error with bulb {self.ip}: {e}")
            return False

    async def _run(self, func, *args, **kwargs):
        # Runs the library's blocking call off the event loop.
        try:
            await asyncio.to_thread(func, *args, **kwargs)
        except (BulbException, OSError) as e:
            print(f"[{self.name}] Communication error with bulb {self.ip}: {e}")

    async def turn_on(self, duration=500):
        await self._run(self.bulb.turn_on, duration=duration)

    async def turn_off(self, duration=500):
        await self._run(self.bulb.turn_off, duration=duration)

    async def set_brightness(self, level, duration=500):
        await self._run(self.bulb.set_brightness, level, duration=duration)

    async def set_rgb(self, r, g, b, duration=500):
        await self._run(self.bulb.set_rgb, r, g, b, duration=duration)

    async def set_temperature(self, kelvin, duration=500):
        await self._run(self.bulb.set_color_temp, kelvin, duration=duration)

    async def flash_lightning(self):
        # Flow.actions.recover relies on the bulb's own built-in "restore
        # previous state" behavior, which is noticeably slow on this
        # hardware. Instead: snapshot the state ourselves, flash with
        # action=stay (so the bulb just holds the last flash frame instead
        # of trying to recover on its own), then restore the snapshot with
        # our own quick, explicit transition.
        try:
            before = await asyncio.to_thread(
                self.bulb.get_properties, ["power", "bright", "ct", "rgb", "color_mode"]
            )
        except (BulbException, OSError) as e:
            print(f"[{self.name}] Communication error with bulb {self.ip}: {e}")
            return

        # count=1: one pass through these 3 transitions (flash 50ms, pause
        # 100ms, flash 50ms). Flow.count loops the *whole* transition list,
        # so count=3 here would actually flash three times, not once.
        flow = Flow(
            count=1,
            action=Flow.actions.stay,
            transitions=[
                TemperatureTransition(6500, duration=50, brightness=100),
                SleepTransition(duration=100),
                TemperatureTransition(6500, duration=50, brightness=100),
            ],
        )
        await self._run(self.bulb.start_flow, flow)
        await asyncio.sleep(0.25)  # let the ~200ms flow actually finish before restoring
        await self._restore(before)

    async def _restore(self, before, duration=300):
        if before.get("power") != "on":
            await self._run(self.bulb.turn_off, duration=duration)
            return

        if before.get("color_mode") == "2" and before.get("ct"):
            await self._run(self.bulb.set_color_temp, int(before["ct"]), duration=duration)
        elif before.get("rgb"):
            rgb = int(before["rgb"])
            await self._run(
                self.bulb.set_rgb,
                (rgb >> 16) & 0xFF,
                (rgb >> 8) & 0xFF,
                rgb & 0xFF,
                duration=duration,
            )

        if before.get("bright"):
            await self._run(self.bulb.set_brightness, int(before["bright"]), duration=duration)

    async def close(self):
        # No-op: python-yeelight doesn't hold a persistent connection to close.
        return
