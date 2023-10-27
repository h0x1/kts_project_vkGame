import json
import random
import typing
from functools import wraps
from typing import Optional, Union

from aiohttp import ClientSession, TCPConnector

from app.base.base_accessor import BaseAccessor
from app.store.vk_api.keyboard import Keyboard, Carousel
from app.store.vk_api.responses import VKUser

if typing.TYPE_CHECKING:
    from app.web.app import Application


class ErrorCodes:
    flood_detected = 9
    too_old_message = 909


def catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs) -> dict:
        self: VKMessenger = args[0]
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            self.app.logger.error(e)
            return dict(error="error")

    return wrapper


class VKMessenger(BaseAccessor):
    API_PATH = "https://api.vk.com/method/"

    session: ClientSession

    async def connect(self, app: "Application"):
        # force_close to avoid errors with close connection
        self.session = ClientSession(connector=TCPConnector(verify_ssl=False, force_close=True))

    async def disconnect(self, app: "Application"):
        await self.session.close()

    def build_query_url(self, method: str, params: dict) -> str:
        params["access_token"] = self.app.config.vk_bot.token
        params["v"] = "5.131"
        return self.API_PATH + method + "?" + "&".join([f"{k}={v}" for k, v in params.items()])

    @catch
    async def query(self, url: str, method="GET") -> dict:
        async with self.session.request(method, url) as resp:
            if not resp.ok:
                self.app.logger.warning(f"status={resp.status}, method={method}, url={url}")
                return dict(error="error")

            data = await resp.json()
            self.app.logger.debug(f"status={resp.status}, method={method}")
            return data

    async def send(self,
                   chat_id: int,
                   message: Optional[str] = None,
                   sticker_id: Optional[int] = None,
                   attachment: Optional[str] = None,
                   keyboard: Optional[Keyboard] = None,
                   carousel: Optional[Carousel] = None) -> Union[bool, int]:
        """
        В сообщении со стикером можно посылать клавиатуру, но нельзя редактировать,
        поэтому реализуем метод отправки ТОЛЬКО здесь (без клавиатуры и карусели).
        Таким образом мы всё равно не сможем получить id сообщения и отредактировать его.
        """
        assert not (message and sticker_id)
        assert not (keyboard and carousel)
        if sticker_id:
            assert not keyboard and not carousel

        params = {
            "peer_id": chat_id,
            "random_id": random.randint(1, 2 ** 32),
        }
        if message:
            params["message"] = message
        if sticker_id:
            params["sticker_id"] = sticker_id
        if attachment:
            params["attachment"] = attachment
        if keyboard:
            params["keyboard"] = json.dumps(keyboard.as_dict())
        if carousel:
            params["template"] = json.dumps(carousel.as_dict())

        url = self.build_query_url("messages.send", params)
        response = await self.query(url, method="POST")

        if response.get("error"):
            self.app.logger.warning(f"msg not sent: {response}, params=({params})")
            return response["error"]["error_code"]
        else:
            self.app.logger.debug("msg sent")
            return True

    async def edit(self,
                   chat_id: int,
                   conversation_message_id: int,
                   message: Optional[str] = None,
                   attachment: Optional[str] = None,
                   keyboard: Optional[Keyboard] = None,
                   carousel: Optional[Carousel] = None) -> Union[bool, int]:
        assert not (keyboard and carousel)
        params = {
            "peer_id": chat_id,
            "conversation_message_id": conversation_message_id,
        }
        if message:
            params["message"] = message
        if attachment:
            params["attachment"] = attachment
        if keyboard:
            params["keyboard"] = json.dumps(keyboard.as_dict())
        if carousel:
            params["template"] = json.dumps(carousel.as_dict())

        url = self.build_query_url("messages.edit", params)
        response = await self.query(url, method="POST")

        if response.get("error"):
            self.app.logger.warning(f"msg not edited: {response}, params=({params})")
            return response["error"]["error_code"]
        else:
            self.app.logger.debug("msg edited")
            return True

    async def delete(self, chat_id: int, conversation_message_id: int) -> Union[bool, int]:
        params = {
            "peer_id": chat_id,
            "cmids": str(conversation_message_id),
            "delete_for_all": 1,
        }

        url = self.build_query_url("messages.delete", params)
        response = await self.query(url, method="POST")

        if response.get("error"):
            self.app.logger.warning(f"msg not deleted: {response}, params=({params})")
            return response["error"]["error_code"]
        else:
            self.app.logger.debug("msg deleted")
            return True

    async def event_ok(self, chat_id: int, user_id: int, event_id: str):
        params = {
            "peer_id": chat_id,
            "user_id": user_id,
            "event_id": event_id,
        }
        url = self.build_query_url("messages.sendMessageEventAnswer", params)
        response = await self.query(url, method="POST")

        if response.get("error"):
            self.app.logger.warning(f"error on event_ok: {response}, params=({params})")
        else:
            self.app.logger.debug("event_ok")

    async def show_snackbar(self, chat_id: int, user_id: int, event_id: str, message: str):
        params = {
            "peer_id": chat_id,
            "user_id": user_id,
            "event_id": event_id,
            "event_data": json.dumps({
                "type": "show_snackbar",
                "text": message,
            }),
        }
        url = self.build_query_url("messages.sendMessageEventAnswer", params)
        response = await self.query(url, method="POST")

        if response.get("error"):
            self.app.logger.warning(f"error on show_snackbar: {response}, params=({params})")
        else:
            self.app.logger.debug("show_snackbar")

    async def get_user_info(self, user_id: int) -> Optional[VKUser]:
        params = {
            "user_ids": str(user_id),
        }
        url = self.build_query_url("users.get", params)
        response = await self.query(url, method="GET")

        if response.get("error"):
            self.app.logger.warning(f"error on get_user_info: {response}, params=({params})")
            return None
        else:
            self.app.logger.debug(f"{user_id}: {response}")
            return VKUser(response["response"][0])
