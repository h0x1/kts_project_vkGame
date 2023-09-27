import asyncio
from asyncio import Task
from typing import Optional

from kts_backend.store import Store


class Poller:
    long_poll_task: asyncio.Task
    taskCollector: asyncio.Task
    tasklist: list[asyncio.Task]

    def __init__(self, store: Store):
        self.store = store
        self.is_running = False
        self.poll_task: Task | None = None

    async def start(self):
        self.tasklist = [asyncio.create_task(self.poll())]
        self.taskCollector = asyncio.create_task(self.gb_collect())
        self.long_poll_task = asyncio.create_task(self.long_polling())
        self.is_running = True

    async def stop(self):
        for task in self.tasklist:
            if task.done() or task.cancelled():
                continue
            await task
        if not self.taskCollector.done():
            await self.taskCollector
        await self.long_poll_task
        self.is_running = False

    async def long_polling(self):
        while self.is_running:
            await self.store.vk_api.poll()


    async def poll(self):
        queue = self.store.vk_api_queue
        seconds = 0.5
        while self.is_running:
            while not queue.empty():
                update = await queue.get()
                await self.store.bots_manager.handle_updates(update)
            await asyncio.sleep(seconds)

    async def gb_collect(self):
        seconds = 5
        while self.is_running:
            self.tasklist = [task for task in self.tasklist if not (task.cancelled() or task.done() )]
            await asyncio.sleep(seconds)



