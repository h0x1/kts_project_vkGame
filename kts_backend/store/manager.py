import typing

from kts_backend.store.vk_api.dataclasses import Update, Message
import asyncio

if typing.TYPE_CHECKING:
    from kts_backend.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app

    async def handle_updates(self, updates: list[Update]):
        for update in updates:
            if update.type == "message_new":
                task = asyncio.create_task(
                    self.app.store.vk_api.send_message(
                        Message(
                            user_id=update.object.message.from_id,
                            text="___Test message___",
                        )
                    )
                )
                self.app.store.vk_api.poller.tasklist.append(task)
