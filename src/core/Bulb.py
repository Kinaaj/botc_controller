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
        # Equivalent to the original start_cf expression
        # "50,2,6500,100,100,7,0,0,50,2,6500,100": flash, brief pause, flash again,
        # then recover to the bulb's previous state.
        flow = Flow(
            count=3,
            action=Flow.actions.recover,
            transitions=[
                TemperatureTransition(6500, duration=50, brightness=100),
                SleepTransition(duration=100),
                TemperatureTransition(6500, duration=50, brightness=100),
            ],
        )
        await self._run(self.bulb.start_flow, flow)

    async def close(self):
        # No-op: python-yeelight doesn't hold a persistent connection to close.
        return
