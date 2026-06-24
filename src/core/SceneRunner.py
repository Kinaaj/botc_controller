import asyncio


class SceneRunner:
    """Runs at most one scene at a time; a new run() cancels and replaces the active one."""

    def __init__(self):
        self._active: asyncio.Task | None = None

    def run(self, coro):
        old = self._active

        async def _runner():
            if old is not None and not old.done():
                old.cancel()
                await asyncio.gather(old, return_exceptions=True)  # wait for old to settle
            await coro

        self._active = asyncio.create_task(_runner())


class SceneContext:
    async def sleep(self, seconds):
        await asyncio.sleep(seconds)
