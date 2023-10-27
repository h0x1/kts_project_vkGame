import typing

from app.store.vk_api.dataclasses import Update, Message
import asyncio

if typing.TYPE_CHECKING:
    from app.web.app import Application
from app.store.vk_api import events
class EventType:
    chat_invite_user = "chat_invite_user"
    message_new = "message_new"
    message_event = "message_event"
    message_edit = "message_edit"

class BotManager:
    def __init__(self, app: "Application"):
        self.app = app

    async def handle_updates(self, updates: list[Update]):
        for update in updates:

            if update.type == EventType.message_new:
                if update.type== EventType.chat_invite_user:
                    event = events.ChatInviteRequest(update, self.app)
                else:
                    event = events.MessageText(update, self.app)
            elif update.type == EventType.message_event:
                event = events.MessageCallback(update, self.app)
            elif update.type == EventType.message_edit:
                self.app.logger.debug("skip")
                return
            else:
                self.app.logger.warning(f"unknown update: {update}")
                return

            task = asyncio.create_task(self.app.store.vk_api.handle_event(event))

            self.app.store.vk_api.poller.tasklist.append(task)
