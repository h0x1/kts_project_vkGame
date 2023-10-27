import asyncio
import json
import typing
from typing import Optional

from app.store.game.payload import BasePayload, PayloadFactory, EmptyPayload, Texts
from app.store.vk_api.keyboard import Keyboard, Carousel
from app.store.vk_api.messenger import ErrorCodes
from app.store.vk_api.responses import VKUser

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BaseEvent:
    chat_id: int
    payload: BasePayload

    def __init__(self, app: "Application"):
        self.app = app
        self.states = app.store.states
        self.games = app.store.games
        self.quiz = app.store.quizzes

    async def send(self,
                   message: Optional[str] = None,
                   sticker_id: Optional[int] = None,
                   attachment: Optional[str] = None,
                   keyboard: Optional[Keyboard] = None,
                   carousel: Optional[Carousel] = None):
        """
        Ожидаем полного завершения действия. Действует проверка на flood detection.
        """
        if message:
            self.states.set_previous_text(self.chat_id, message)
        while not self.app.store.vk_messenger.session.closed:
            result = await self.app.store.vk_messenger.send(self.chat_id,
                                                            message=message,
                                                            sticker_id=sticker_id,
                                                            attachment=attachment,
                                                            keyboard=keyboard,
                                                            carousel=carousel)
            if result is not True:
                if result == ErrorCodes.flood_detected and not self.states.is_flood_detected(self.chat_id):
                    self.states.set_flood_detected(self.chat_id)
                    if isinstance(self, MessageCallback):
                        await self.show_snackbar(Texts.flood_detected)
                self.app.logger.info("sleeping 30 sec")
                await asyncio.sleep(30.0)
                continue

            self.states.set_flood_not_detected(self.chat_id)
            return


class ChatInviteRequest(BaseEvent):

    def __init__(self, data: dict, app: "Application"):
        super(ChatInviteRequest, self).__init__(app)
        self.chat_id = data["object"]["message"]["peer_id"]
        self.payload = EmptyPayload()


class BaseMessageEvent(BaseEvent):
    event_id: str
    conversation_message_id: int
    user_id: int

    async def get_user_info(self) -> Optional[VKUser]:
        return await self.app.store.vk_messenger.get_user_info(self.user_id)

    async def edit(self,
                   message: Optional[str] = None,
                   attachment: Optional[str] = None,
                   keyboard: Optional[Keyboard] = None,
                   carousel: Optional[Carousel] = None):
        """
        Ожидаем полного завершения действия. Действует проверка на flood detection.
        """
        if message:
            self.states.set_previous_text(self.chat_id, message)
        while not self.app.store.vk_messenger.session.closed:
            result = await self.app.store.vk_messenger.edit(self.chat_id,
                                                            self.conversation_message_id,
                                                            message=message,
                                                            attachment=attachment,
                                                            keyboard=keyboard,
                                                            carousel=carousel)
            if result is not True:
                if result == ErrorCodes.too_old_message:
                    return await self.send(message=message, attachment=attachment, keyboard=keyboard, carousel=carousel)
                elif result == ErrorCodes.flood_detected and not self.states.is_flood_detected(self.chat_id):
                    self.states.set_flood_detected(self.chat_id)
                    if isinstance(self, MessageCallback):
                        await self.show_snackbar(Texts.flood_detected)
                self.app.logger.info("sleeping 30 sec")
                await asyncio.sleep(30.0)
                continue

            self.states.set_flood_not_detected(self.chat_id)
            return

    async def delete(self):
        """
        Ожидаем полного завершения действия. Действует проверка на flood detection.
        """
        while not self.app.store.vk_messenger.session.closed:
            result = await self.app.store.vk_messenger.delete(self.chat_id, self.conversation_message_id)
            if result is not True:
                if result == ErrorCodes.too_old_message:
                    return
                elif result == ErrorCodes.flood_detected:
                    self.states.set_flood_detected(self.chat_id)
                self.app.logger.info("sleeping 30 sec")
                await asyncio.sleep(30.0)
                continue

            self.states.set_flood_not_detected(self.chat_id)
            return


class MessageText(BaseMessageEvent):

    def __init__(self, data: dict, app: "Application"):
        super(MessageText, self).__init__(app)
        self.payload: BasePayload = PayloadFactory.create({"action": "bot_info"})


class MessageCallback(BaseMessageEvent):

    def __init__(self, data: dict, app: "Application"):
        print("calback")
        super(MessageCallback, self).__init__(app)
        body = data["object"]
        self.chat_id: int = body["peer_id"]
        self.event_id: str = body["event_id"]  # в поле object
        self.conversation_message_id: int = body["conversation_message_id"]
        self.user_id: int = body["user_id"]
        self.payload: BasePayload = PayloadFactory.create(
            body.payload or {}  # empty payload returns as [] :-/
        )

    async def event_ok(self):
        # нет необходимости в том, чтобы убедиться в завершении действия
        await self.app.store.vk_messenger.event_ok(self.chat_id, self.user_id, self.event_id)

    async def show_snackbar(self, message: str):
        # нет необходимости в том, чтобы убедиться в завершении действия
        await self.app.store.vk_messenger.show_snackbar(self.chat_id, self.user_id, self.event_id, message)
