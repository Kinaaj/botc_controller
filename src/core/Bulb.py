import asyncio
import random

from yeelight import Bulb as YeelightBulb, Flow, TemperatureTransition, SleepTransition, RGBTransition
from yeelight.main import BulbException
from .BulbState import BulbState, BulbStateType


class Bulb:
    def __init__(self, ip, name, port=55443):
        self.ip = ip
        self.name = name
        self.port = port
        self.bulb = YeelightBulb(ip, port=port, duration=30, auto_on=False)
        self.is_online = False

    def _reset_socket(self):
        """Uzavře a vyčistí interní socket, aby se při dalším volání navázalo nové TCP spojení."""
        try:
            if hasattr(self.bulb, "_socket") and self.bulb._socket:
                self.bulb._socket.close()
        except Exception:
            pass
        self.bulb._socket = None

    async def connect(self):
        """Vyzkouší spojení a naváže trvalé TCP spojení se žárovkou."""
        try:
            await asyncio.to_thread(self.bulb.get_properties)
            if not self.is_online:
                self.is_online = True
                print(f"[Bulb] {self.name} ({self.ip}): ONLINE (připojeno)")
            return True
        except (BulbException, OSError):
            if self.is_online:
                self.is_online = False
                print(f"[Bulb] {self.name} ({self.ip}): OFFLINE")
            self._reset_socket()
            return False

    async def _run(self, func, *args, **kwargs):
        """Spustí blokující metodu python-yeelight nad trvalým spojením mimo hlavní event loop."""
        try:
            await asyncio.to_thread(func, *args, **kwargs)
            if not self.is_online:
                self.is_online = True
                print(f"[Bulb] {self.name} ({self.ip}): ONLINE (připojeno)")
        except (BulbException, OSError):
            if self.is_online:
                self.is_online = False
                print(f"[{self.name}] Žárovka {self.ip} je nedostupná. Připojí se automaticky po zapnutí.")
            self._reset_socket()

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

    async def start_flow(self, flow):
        await self._run(self.bulb.start_flow, flow)

    async def flash_lightning(self, target_state: BulbState):
        flashes_count = random.randint(1, 3)

        if target_state.state_type == BulbStateType.TEMPERATURE:
            transitions = flashes_count * [
                TemperatureTransition(6500, duration=50, brightness=100),
                SleepTransition(duration=100),
                TemperatureTransition(6500, duration=50, brightness=100),
                TemperatureTransition(6500, duration=50, brightness=1),
            ] + [
                TemperatureTransition(target_state.temperature, duration=1500, brightness=target_state.brightness)
            ]
        else:
            transitions = flashes_count * [
                TemperatureTransition(6500, duration=50, brightness=100),
                SleepTransition(duration=100),
                TemperatureTransition(6500, duration=50, brightness=100),
                TemperatureTransition(6500, duration=50, brightness=1),
            ] + [
                RGBTransition(target_state.r, target_state.g, target_state.b, duration=1500, brightness=target_state.brightness)
            ]

        flow = Flow(
            count=1,
            action=Flow.actions.stay,
            transitions=transitions,
        )
        await self.start_flow(flow)

    async def flash_color(self, r, g, b, delay, target_state: BulbState):
        if target_state.state_type == BulbStateType.TEMPERATURE:
            transitions = [
                SleepTransition(duration=delay),
                RGBTransition(r, g, b, duration=50, brightness=100),
                SleepTransition(duration=220),
                RGBTransition(r, g, b, duration=50, brightness=100),
                TemperatureTransition(target_state.temperature, duration=1500, brightness=target_state.brightness),
            ]
        else:
            transitions = [
                SleepTransition(duration=delay),
                RGBTransition(r, g, b, duration=50, brightness=100),
                SleepTransition(duration=220),
                RGBTransition(r, g, b, duration=50, brightness=100),
                RGBTransition(target_state.r, target_state.g, target_state.b, duration=1500, brightness=target_state.brightness),
            ]

        flow = Flow(
            count=1,
            action=Flow.actions.stay,
            transitions=transitions,
        )
        await self.start_flow(flow)

    async def close(self):
        self._reset_socket()
