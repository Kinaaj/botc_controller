import asyncio

from yeelight import Bulb, Flow
from yeelight.flow import SleepTransition, TemperatureTransition
from yeelight.main import BulbException


class YeelightControllerLib:
    """
    Alternative to YeelightController, built on the python-yeelight library
    (https://gitlab.com/stavros/python-yeelight) instead of the hand-rolled
    TCP/JSON protocol. Mirrors YeelightController's public API so it can be
    used as a drop-in replacement in SceneManager.
    """

    def __init__(self, ip, name, port=55443):
        self.ip = ip
        self.name = name
        self.port = port
        self.bulb = Bulb(ip, port=port, auto_on=False)

    async def connect(self):
        # No-op: python-yeelight opens its socket lazily as needed.
        return

    async def _run(self, func, *args, **kwargs):
        # Runs the library's blocking call off the event loop.
        try:
            await asyncio.to_thread(func, *args, **kwargs)
        except (BulbException, OSError) as e:
            print(f"[{self.name}] Communication error with bulb {self.ip}: {e}")

    async def turn_on(self):
        await self._run(self.bulb.turn_on, duration=500)

    async def turn_off(self):
        await self._run(self.bulb.turn_off, duration=500)

    async def set_brightness(self, level):
        await self._run(self.bulb.set_brightness, level, duration=500)

    async def set_rgb(self, r, g, b, duration=500):
        await self._run(self.bulb.set_rgb, r, g, b, duration=duration)

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

    async def drawing_effect(self):
        # TODO
        return

    async def close(self):
        # No-op: python-yeelight doesn't hold a persistent connection to close.
        return
