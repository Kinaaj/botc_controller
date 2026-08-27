import asyncio

from yeelight import Flow, TemperatureTransition, RGBTransition
from .Bulb import Bulb
from .BulbState import BulbState


class BulbGroup:
    """Drives all bulbs in lockstep, maintains persistent connections and auto-reconnects."""

    def __init__(self, bulbs_config):
        self.bulbs = [Bulb(b["ip"], b["name"]) for b in bulbs_config]

    async def _broadcast(self, method_name, *args, **kwargs):
        tasks = [
            getattr(bulb, method_name)(*args, **kwargs)
            for bulb in self.bulbs
            if hasattr(bulb, method_name)
        ]
        if tasks:
            return await asyncio.gather(*tasks, return_exceptions=True)
        return []

    async def connect_all(self):
        results = await self._broadcast("connect")
        online_count = sum(1 for b in self.bulbs if b.is_online)
        if online_count == len(self.bulbs):
            print(f"[BulbGroup] Všechny žárovky ({online_count}/{len(self.bulbs)}) jsou online.")
        elif online_count > 0:
            print(f"[BulbGroup] Připojeno {online_count}/{len(self.bulbs)} žárovek (zbývající se připojí automaticky po zapnutí).")
        else:
            print(f"[BulbGroup] Žádná žárovka není online (připojí se automaticky po zapnutí vypínačem).")
        return results

    async def start_background_watcher(self, check_interval=4):
        """Periodicky na pozadí zkouší znovu připojit žárovky, které jsou offline."""
        while True:
            await asyncio.sleep(check_interval)
            offline_bulbs = [b for b in self.bulbs if not b.is_online]
            if offline_bulbs:
                await asyncio.gather(*[b.connect() for b in offline_bulbs], return_exceptions=True)

    async def close_all(self):
        await self._broadcast("close")

    async def turn_on(self):
        await self._broadcast("turn_on")

    async def turn_off(self):
        await self._broadcast("turn_off")

    async def fade_off(self, seconds=2.0):
        await self._broadcast("turn_off", duration=int(seconds * 1000))

    async def fade_up_to_rgb(self, r, g, b, seconds=2.0, brightness=100):
        duration_ms = int(seconds * 1000)
        await self._broadcast("turn_on", duration=duration_ms)
        flow = Flow(
            count=1,
            action=Flow.actions.stay,
            transitions=[RGBTransition(r, g, b, duration=duration_ms, brightness=brightness)],
        )
        await self._broadcast("start_flow", flow)

    async def fade_up_to_temperature(self, kelvin, seconds=2.0, brightness=100):
        duration_ms = int(seconds * 1000)
        await self._broadcast("turn_on", duration=duration_ms)
        flow = Flow(
            count=1,
            action=Flow.actions.stay,
            transitions=[TemperatureTransition(kelvin, duration=duration_ms, brightness=brightness)],
        )
        await self._broadcast("start_flow", flow)

    async def fade_to_rgb(self, r, g, b, seconds=0.5):
        await self._broadcast("set_rgb", r, g, b, duration=int(seconds * 1000))

    async def set_temperature(self, kelvin, seconds=2.0):
        await self._broadcast("set_temperature", kelvin, duration=int(seconds * 1000))

    async def flash_lightning(self, target_state: BulbState):
        await self._broadcast("flash_lightning", target_state)

    async def flash_blood(self, r, g, b, delay, default_bulb_state):
        await self._broadcast("flash_color", r, g, b, delay, default_bulb_state)
