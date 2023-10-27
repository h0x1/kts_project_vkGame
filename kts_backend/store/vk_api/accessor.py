import typing
from pprint import pprint
import random
from typing import Optional, Union
from collections.abc import Callable, Awaitable
import asyncio
import aiohttp
from functools import wraps
from aiohttp.client import ClientSession
from dataclasses import dataclass
from app.base.base_accessor import BaseAccessor
from app.store.vk_api.dataclasses import (
    Message,
    Update,
    UpdateObject,
    UpdateMessage,
)
from app.store.vk_api.poller import Poller


from app.store.game import keyboards
from app.store.game.payload import (
    BasePayload, MainMenuPayload, CreateNewGamePayload, JoinUsersPayload,
    StartGamePayload, BaseGamePayload, ChooseThemePayload, ChooseQuestionPayload,
    SendQuestionPayload, GetAnswerPayload, ShowAnswerPayload, ConfirmStopGamePayload, StopGamePayload,
    ShowScoreboardPayload, GameRulesPayload, BotInfoPayload,
)
from app.store.game.payload import PRICES, Texts, Photos, Stickers, LINE_BREAK, PLUS_SIGN
from app.store.game.payload import UserCommands, BotActions
from app.store.vk_api.events import BaseEvent, ChatInviteRequest, MessageText, MessageCallback
from app.store.vk_api.keyboard import CallbackButton, Carousel, CarouselElement, Keyboard, ButtonColor
from app.utils import generate_uuid

if typing.TYPE_CHECKING:
    from app.web.app import Application

TypeCondition = Callable[[BaseEvent], bool]
TypeMessageFunc = Callable[[BaseEvent, BasePayload], Awaitable[None]]


if typing.TYPE_CHECKING:
    from app.web.app import Application

@dataclass
class EventSubscriber:
    condition: TypeCondition
    func: TypeMessageFunc


def dummy_condition(_: BaseEvent) -> bool:
    return True

def catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        self: VkApiAccessor = args[0]
        while 1:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                self.app.logger.warning(e)
                await asyncio.sleep(5.0)

    return wrapper


class VkApiAccessor(BaseAccessor):
    def __init__(self, app: "Application", *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.session: Optional[ClientSession] = None
        self.key: Optional[str] = None
        self.server: Optional[str] = None
        self.poller: Optional[Poller] = None
        self.ts: Optional[int] = None

        self.chat_invite_request_subscribers: list[EventSubscriber] = []
        self.message_text_subscribers: list[EventSubscriber] = []
        self.message_callback_subscribers: list[EventSubscriber] = []

    async def connect(self, app: "Application"):
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False)
        )
        self.poller = Poller(self.app.store)
        await self._get_long_poll_service()
        await self.poller.start()

    async def disconnect(self, app: "Application"):
        if self.session is not None:
            await self.session.close()
            self.session = None

        if self.poller is not None and self.poller.is_running:
            await self.poller.stop()
            self.poller = None

    @staticmethod
    def _build_query(host: str, method: str, params: dict) -> str:
        url = host + method + "?"
        if "v" not in params:
            params["v"] = "5.131"
        url += "&".join([f"{k}={v}" for k, v in params.items()])
        return url

    async def _get_long_poll_service(self):
        group_id = self.app.config.bot.group_id
        token = self.app.config.bot.token

        query = self._build_query(
            host="https://api.vk.com/",
            method="method/groups.getLongPollServer",
            params={"group_id": group_id, "access_token": token},
        )

        async with self.session.get(query) as response:
            response_body = (await response.json())["response"]
            self.key = response_body["key"]
            self.server = response_body["server"]
            self.ts = response_body["ts"]

    @catch
    async def poll(self):
        query = self._build_query(
            host=self.server,
            method="",
            params={
                "act": "a_check",
                "key": self.key,
                "wait": 25,
                "mode": 2,
                "ts": self.ts,
            },
        )
        async with self.session.get(query) as response:
            resp_json = await response.json()
            self.ts = resp_json["ts"]
            raw_updates = resp_json["updates"]
            updates = self._pack_updates(raw_updates)
            await self.app.store.vk_api_queue.put(updates)

    async def send_message(self, message: Message) -> None:
        query = self._build_query(
            host="https://api.vk.com/",
            method="method/messages.send",
            params={
                "message": message.text,
                "access_token": self.app.config.bot.token,
                "group_id": self.app.config.bot.group_id,
                "random_id": 0,
                "peer_id": -202369435,
                "user_id": message.user_id,
            },
        )

        async with self.session.get(query) as resp:
            pprint(await resp.json())

    @staticmethod
    def _pack_updates(raw_updates: dict) -> list[Update]:
        return [
            Update(
                type=u["type"],
                object=UpdateObject(
                    message=UpdateMessage(
                        from_id=u["object"]["message"]["from_id"],
                        text=u["object"]["message"]["text"],
                        id=u["object"]["message"]["id"],
                    )
                ),
            )
            for u in raw_updates
            if u["type"] == "message_new"
        ]

    def on_chat_invite_request(self, condition: Optional[TypeCondition] = None):
        condition = condition or dummy_condition

        def decorator(func: TypeMessageFunc):
            self.chat_invite_request_subscribers.append(
                EventSubscriber(condition=condition, func=func)
            )

            @wraps(func)
            async def wrapper(msg: MessageCallback, payload: BasePayload):
                return await func(msg, payload)

            return wrapper

        return decorator

    def on_message_text(self, condition: Optional[TypeCondition] = None):
        condition = condition or dummy_condition

        def decorator(func: TypeMessageFunc):
            self.message_text_subscribers.append(
                EventSubscriber(condition=condition, func=func)
            )

            @wraps(func)
            async def wrapper(msg: MessageCallback, payload: BasePayload):
                return await func(msg, payload)

            return wrapper

        return decorator

    def on_message_callback(self, condition: Optional[TypeCondition] = None):
        condition = condition or dummy_condition

        def decorator(func: TypeMessageFunc):
            self.message_callback_subscribers.append(
                EventSubscriber(condition=condition, func=func)
            )

            @wraps(func)
            async def wrapper(msg: MessageCallback, payload: BasePayload):
                return await func(msg, payload)

            return wrapper

        return decorator

    async def handle_event(self, event: BaseEvent) -> None:
        if isinstance(event, ChatInviteRequest):
            if self.app.store.states.is_flood_detected(event.chat_id):
                return
            for subscriber in self.chat_invite_request_subscribers:
                if subscriber.condition(event):
                    return await subscriber.func(event, event.payload)
        elif isinstance(event, MessageText):
            if self.app.store.states.is_flood_detected(event.chat_id):
                return
            for subscriber in self.message_text_subscribers:
                if subscriber.condition(event):
                    return await subscriber.func(event, event.payload)
        elif isinstance(event, MessageCallback):
            if self.app.store.states.is_flood_detected(event.chat_id):
                return await event.show_snackbar(Texts.flood_detected)
            for subscriber in self.message_callback_subscribers:
                if subscriber.condition(event):
                    return await subscriber.func(event, event.payload)
        else:
            self.app.logger.warning(f"unknown event: {event}")


def register_bot_actions(bot: VkApiAccessor):


    bot.on_message_text(lambda i: i.text.lower() == UserCommands.start)(invite)
    bot.on_message_text(lambda i: i.text.lower() == UserCommands.stop)(force_stop_game)

    bot.on_message_callback(lambda i: i.payload.action == BotActions.main_menu)(main_menu)
    bot.on_message_callback(lambda i: i.payload.action == BotActions.create_new_game)(create_new_game)
    bot.on_message_callback(lambda i: i.payload.action == BotActions.join_users)(join_users)
    bot.on_message_callback(lambda i: i.payload.action == BotActions.start_game)(start_game)
    bot.on_message_callback(lambda i: i.payload.action == BotActions.choose_theme)(choose_theme)
    bot.on_message_callback(lambda i: i.payload.action == BotActions.choose_question)(choose_question)
    bot.on_message_callback(lambda i: i.payload.action == BotActions.send_question)(send_question)
    bot.on_message_callback(lambda i: i.payload.action == BotActions.get_answer)(get_answer)
    bot.on_message_callback(lambda i: i.payload.action == BotActions.show_scoreboard)(show_scoreboard)
    bot.on_message_callback(lambda i: i.payload.action == BotActions.confirm_stop_game)(confirm_stop_game)
    bot.on_message_callback(lambda i: i.payload.action == BotActions.stop_game)(stop_game)

    bot.on_message_callback(lambda i: i.payload.action == BotActions.game_rules)(game_rules)
    bot.on_message_callback(lambda i: i.payload.action == BotActions.bot_info)(bot_info)


def filter_game_id(func: TypeMessageFunc):
    @wraps(func)
    async def wrapper(msg: MessageCallback, payload: BaseGamePayload):
        if msg.states.get_game_id(msg.chat_id) != payload.game_id:
            return await msg.show_snackbar(Texts.old_game_round)
        return await func(msg, payload)

    return wrapper


def filter_who_s_turn(func: TypeMessageFunc):
    @wraps(func)
    async def wrapper(msg: MessageCallback, payload: BaseGamePayload):
        if msg.states.get_who_s_turn(msg.chat_id) != msg.user_id:
            return await msg.show_snackbar(Texts.not_your_turn)
        return await func(msg, payload)

    return wrapper


def filter_playing_users(func: TypeMessageFunc):
    @wraps(func)
    async def wrapper(msg: MessageCallback, payload: BaseGamePayload):
        users = msg.states.get_joined_users(msg.chat_id)
        if msg.user_id not in [i.id for i in users]:
            return await msg.show_snackbar(Texts.not_your_game)
        return await func(msg, payload)

    return wrapper


async def invite(msg: Union[ChatInviteRequest, MessageText], _: BasePayload):
    async with msg.states.locks.game_status(msg.chat_id):
        if msg.states.get_game_status(msg.chat_id) == BotActions.invite:
            return
        msg.states.set_game_status(msg.chat_id, BotActions.invite)

    await msg.games.joined_the_chat(msg.chat_id)
    await msg.send(attachment=Photos.main_wallpaper, keyboard=keyboards.invite())


async def main_menu(msg: MessageCallback, payload: MainMenuPayload):
    is_passed = False
    async with msg.states.locks.game_status(msg.chat_id):
        if (
                msg.states.get_game_status(msg.chat_id) != BotActions.main_menu
                or
                payload.source == BotActions.main_menu  # update button
        ):
            is_passed = True
            msg.states.restore_status(msg.chat_id)
    if not is_passed:
        return await msg.event_ok()  # do it after release lock

    await msg.games.restore_status(msg.chat_id)
    if payload.new:
        if msg.app.config.vk_bot.beautiful:
            if payload.source == BotActions.main_menu:
                await msg.edit(Texts.goodbye)
            else:
                await msg.edit(msg.states.get_previous_text(msg.chat_id))
        else:
            await msg.event_ok()
        await msg.send(attachment=Photos.main_wallpaper, keyboard=keyboards.main_menu())
    else:
        await msg.edit(attachment=Photos.main_wallpaper, keyboard=keyboards.main_menu())


async def game_rules(msg: MessageCallback, _: GameRulesPayload):
    is_passed = False
    async with msg.states.locks.game_status(msg.chat_id):
        if msg.states.get_game_status(msg.chat_id) == BotActions.main_menu:
            is_passed = True
            msg.states.set_game_status(msg.chat_id, BotActions.game_rules)
    if not is_passed:
        return await msg.event_ok()

    await msg.edit(Texts.rules, keyboard=keyboards.back(source=BotActions.game_rules))


async def bot_info(msg: MessageCallback, _: BotInfoPayload):
    is_passed = False
    async with msg.states.locks.game_status(msg.chat_id):
        if msg.states.get_game_status(msg.chat_id) == BotActions.main_menu:
            is_passed = True
            msg.states.set_game_status(msg.chat_id, BotActions.bot_info)
    if not is_passed:
        return await msg.event_ok()

    await msg.edit(Texts.about, keyboard=keyboards.back(source=BotActions.bot_info))


async def create_new_game(msg: MessageCallback, _: CreateNewGamePayload):
    is_passed = False
    async with msg.states.locks.game_status(msg.chat_id):
        if msg.states.get_game_status(msg.chat_id) == BotActions.main_menu:
            is_passed = True
            msg.states.set_game_status(msg.chat_id, BotActions.join_users)
    if not is_passed:
        return await msg.show_snackbar(Texts.too_late)

    text = f"Присоединились к игре:{LINE_BREAK}😥 Пока никого..."
    await msg.edit(text, keyboard=keyboards.join_users())


async def join_users(msg: MessageCallback, _: JoinUsersPayload):
    is_passed = False
    async with msg.states.locks.game_status(msg.chat_id):
        if msg.states.get_game_status(msg.chat_id) == BotActions.join_users:
            is_passed = True
    if not is_passed:
        return await msg.show_snackbar(Texts.too_late)

    async with msg.states.locks.game_users(msg.chat_id):
        users = msg.states.get_joined_users(msg.chat_id)
        if any(msg.user_id == u.id for u in users):
            return await msg.show_snackbar(Texts.you_are_already_joined)

        new_user = await msg.get_user_info()
        if new_user is None:
            return await msg.show_snackbar(Texts.error_try_again)
        msg.states.set_user_info(new_user)

        users.append(new_user)
        msg.states.set_users_joined(msg.chat_id, users)

    text = f"Присоединились к игре:{LINE_BREAK}"
    text += LINE_BREAK.join(f"👤 {u.first_name} {u.last_name}" for i, u in enumerate(users))
    await msg.edit(text, keyboard=keyboards.join_users())


async def start_game(msg: MessageCallback, _: StartGamePayload):
    async with msg.states.locks.game_status(msg.chat_id):
        if msg.states.get_game_status(msg.chat_id) != BotActions.join_users:
            return await msg.show_snackbar(Texts.game_is_already_started)
        async with msg.states.locks.game_users(msg.chat_id):
            users = msg.states.get_joined_users(msg.chat_id)
            if not users:
                return await msg.show_snackbar(Texts.nobody_joined)
            if not any(msg.user_id == u.id for u in users):
                return await msg.show_snackbar(Texts.firstly_join_the_game)
        msg.states.set_game_status(msg.chat_id, BotActions.choose_theme)

    user_dcs = await msg.games.create_users(users)
    game_dc = await msg.games.create_game(msg.chat_id, user_dcs)
    msg.states.set_game_id(msg.chat_id, game_dc.id)
    msg.states.set_who_s_turn(msg.chat_id, msg.user_id)

    await choose_theme(msg, ChooseThemePayload(game_id=game_dc.id, new=True))

@filter_game_id
@filter_playing_users
async def choose_theme(msg: MessageCallback, payload: ChooseThemePayload):
    # на view выбора темы может перейти любой пользователь,
    # но выбирать саму тему может только тот, чья сейчас очередь
    is_passed = False
    async with msg.states.locks.game_status(msg.chat_id):
        if msg.states.get_game_status(msg.chat_id) == BotActions.choose_theme:
            is_passed = True
            msg.states.set_game_status(msg.chat_id, BotActions.choose_question)
    if not is_passed:
        return await msg.show_snackbar(Texts.old_game_round)

    themes = await msg.quiz.list_themes()
    theme_chosen_prices = msg.states.get_theme_chosen_prices(msg.chat_id)
    exclude_theme_ids = [k for k, v in theme_chosen_prices.items() if 0 not in v]
    themes = [i for i in themes if i.id not in exclude_theme_ids]

    if not themes:  # все вопросы исчерпаны, конец игры
        return await stop_game(msg, StopGamePayload(game_id=payload.game_id, new=True))

    carousel = Carousel()
    for theme in themes:
        element = CarouselElement(
            title=theme.title,
            description=theme.title,
            photo_id=Photos.theme_carousel,
            buttons=[
                CallbackButton("Выбрать", payload=ChooseQuestionPayload(game_id=payload.game_id,
                                                                        theme_id=theme.id,
                                                                        theme_title=theme.title))
            ])
        carousel.add_element(element)

    user = msg.states.get_user_info(msg.states.get_who_s_turn(msg.chat_id))
    if payload.new:
        if msg.app.config.vk_bot.beautiful:
            await msg.edit(msg.states.get_previous_text(msg.chat_id))
        else:
            await msg.event_ok()
        await msg.send(f"👉🏻 {user.name}, выберите тему:", carousel=carousel)
    else:
        await msg.edit(f"👉🏻 {user.name}, выберите тему:", carousel=carousel)


@filter_game_id
@filter_who_s_turn
async def choose_question(msg: MessageCallback, payload: ChooseQuestionPayload):
    is_passed = False
    async with msg.states.locks.game_status(msg.chat_id):
        if msg.states.get_game_status(msg.chat_id) == BotActions.choose_question:
            is_passed = True
            msg.states.set_game_status(msg.chat_id, BotActions.send_question)
    if not is_passed:
        return await msg.show_snackbar(Texts.old_game_round)

    # всего 5 вопросов в теме, 1 = вопрос уже выбран ранее
    chosen_prices = msg.states.get_theme_chosen_prices(msg.chat_id).get(payload.theme_id, [0] * 5)
    button_texts = iter(str(p) if c == 0 else "--" for c, p in zip(chosen_prices, PRICES))
    button_prices = iter(p if c == 0 else 0 for c, p in zip(chosen_prices, PRICES))
    button_colors = iter(ButtonColor.blue if c == 0 else ButtonColor.white for c in chosen_prices)

    def get_button() -> CallbackButton:
        return CallbackButton(next(button_texts),
                              payload=SendQuestionPayload(game_id=payload.game_id,
                                                          theme_id=payload.theme_id,
                                                          price=next(button_prices)),
                              color=next(button_colors))

    keyboard = Keyboard(inline=True, buttons=[
        [get_button(), get_button(), get_button()],
        [get_button(), get_button()],
    ])

    await msg.edit(f"Тема:{LINE_BREAK}📗 {payload.theme_title}")

    user = msg.states.get_user_info(msg.user_id)
    await msg.send(f"👉🏻 {user.name}, выберите вопрос:", keyboard=keyboard)


@filter_game_id
@filter_who_s_turn
async def send_question(msg: MessageCallback, payload: SendQuestionPayload):
    if payload.price == 0:
        return await msg.event_ok()

    is_passed = False
    async with msg.states.locks.game_status(msg.chat_id):
        if msg.states.get_game_status(msg.chat_id) == BotActions.send_question:
            is_passed = True
            msg.states.set_game_status(msg.chat_id, BotActions.get_answer)
    if not is_passed:
        return await msg.show_snackbar(Texts.old_game_round)

    # всего 5 вопросов в теме, 1 = вопрос уже выбран ранее
    theme_chosen_prices = msg.states.get_theme_chosen_prices(msg.chat_id)
    chosen_prices = theme_chosen_prices.get(payload.theme_id, [0] * 5)
    chosen_prices[PRICES.index(payload.price)] = 1
    theme_chosen_prices[payload.theme_id] = chosen_prices
    msg.states.set_theme_chosen_prices(msg.chat_id, theme_chosen_prices)

    question_models = await msg.games.get_remaining_questions(payload.game_id, payload.theme_id)
    question_model = random.choice(question_models)
    question_dc = question_model.as_dataclass()
    await msg.games.set_question_asked(payload.game_id, question_dc)
    random.shuffle(question_dc.answers)
    msg.states.set_current_question(msg.chat_id, question_dc)

    # id, not title, to avoid big length of the payload
    # answer_dc has no id, so we use answer model
    answer_id = [i.id for i in question_model.answers if i.is_correct][0]
    msg.states.set_current_answer_id(msg.chat_id, answer_id)
    msg.states.set_current_answer(msg.chat_id, [i for i in question_dc.answers if i.is_correct][0])
    msg.states.set_current_price(msg.chat_id, payload.price)

    text = f"Вопрос на {payload.price} очков:{LINE_BREAK}{LINE_BREAK}" \
           f"🔎 {question_dc.title}{LINE_BREAK}{LINE_BREAK}"
    answers = iter(question_model.answers)
    task_uid = generate_uuid()

    def get_button() -> CallbackButton:
        answer = next(answers)
        return CallbackButton(answer.title[:40],
                              payload=GetAnswerPayload(game_id=payload.game_id,
                                                       question_id=question_dc.id,
                                                       answer_id=answer.id,
                                                       uid=task_uid),
                              color=ButtonColor.white)

    keyboard = Keyboard(inline=True, buttons=[
        [get_button()],
        [get_button()],
        [get_button()],
        [get_button()],
    ])

    if msg.app.config.vk_bot.beautiful:
        if msg.app.config.vk_bot.animate_timer:
            for i in range(msg.app.config.vk_bot.sleep_before_show_variants, 0, -1):
                await msg.edit(text + f"⏱ {i}...")
                await asyncio.sleep(1.0)
        else:
            await msg.edit(text)
            await asyncio.sleep(msg.app.config.vk_bot.sleep_before_show_variants)

    async def timer():
        if msg.app.config.vk_bot.animate_timer:
            for i in range(msg.app.config.vk_bot.sleep_before_show_answer, 0, -1):
                await msg.edit(text + f"⏱ {i}...", keyboard=keyboard)
                await asyncio.sleep(1.0)
        else:
            await msg.edit(text, keyboard=keyboard)
            await asyncio.sleep(msg.app.config.vk_bot.sleep_before_show_answer)

        async with msg.states.locks.game_status(msg.chat_id):
            if msg.states.get_game_status(msg.chat_id) == BotActions.get_answer:
                msg.states.set_game_status(msg.chat_id, BotActions.show_answer)

        await show_answer(msg, ShowAnswerPayload(game_id=payload.game_id,
                                                 question_id=question_dc.id,
                                                 winner=None))

    await msg.app.store.vk_bot.schedule_task(task_uid, timer())


@filter_game_id
@filter_playing_users
async def get_answer(msg: MessageCallback, payload: GetAnswerPayload):
    question = msg.states.get_current_question(msg.chat_id)
    if not question or question.id != payload.question_id:
        return await msg.show_snackbar(Texts.old_game_round)

    async with msg.states.locks.game_status(msg.chat_id):
        if msg.states.get_game_status(msg.chat_id) != BotActions.get_answer:
            return await msg.show_snackbar(Texts.too_late)

        answered_users = msg.states.get_answered_users(msg.chat_id)
        if msg.user_id in answered_users:
            return await msg.show_snackbar(Texts.you_are_already_answered)
        answered_users.append(msg.user_id)
        msg.states.set_users_answered(msg.chat_id, answered_users)

        answer_id = msg.states.get_current_answer_id(msg.chat_id)
        if len(answered_users) == len(msg.states.get_joined_users(msg.chat_id)):
            winner = msg.user_id if answer_id == payload.answer_id else None
        else:
            if answer_id != payload.answer_id:
                return await msg.event_ok()
            winner = msg.user_id
        msg.states.set_game_status(msg.chat_id, BotActions.show_answer)

    msg.app.store.vk_bot.cancel_task(payload.uid)
    await show_answer(msg, ShowAnswerPayload(game_id=payload.game_id,
                                             question_id=payload.question_id,
                                             winner=winner))


@filter_game_id
@filter_playing_users
async def show_answer(msg: MessageCallback, payload: ShowAnswerPayload):
    question = msg.states.get_current_question(msg.chat_id)
    if not question or question.id != payload.question_id:
        return await msg.show_snackbar(Texts.old_game_round)

    is_passed = False
    async with msg.states.locks.game_status(msg.chat_id):
        if msg.states.get_game_status(msg.chat_id) == BotActions.show_answer:
            is_passed = True
            msg.states.set_game_status(msg.chat_id, BotActions.show_scoreboard)
    if not is_passed:
        return await msg.show_snackbar(Texts.too_late)

    if msg.app.config.vk_bot.beautiful:
        await msg.edit(f"Вопрос:{LINE_BREAK}🔎 {question.title}")
    else:
        await msg.event_ok()

    await msg.send(sticker_id=Stickers.dog_wait_sec)
    await asyncio.sleep(1.0)

    current_price = msg.states.get_current_price(msg.chat_id)
    answered_users_ids = msg.states.get_answered_users(msg.chat_id)
    wrong_answered_users_ids = [i for i in answered_users_ids if i != payload.winner]
    await msg.games.update_game_scores(payload.game_id,
                                       payload.winner,
                                       wrong_answered_users_ids,
                                       current_price)

    await msg.games.set_game_question_result(payload.game_id,
                                             question.id,
                                             is_answered=payload.winner is not None)

    answer = msg.states.get_current_answer(msg.chat_id)

    text = ""
    if payload.winner is None:
        users = msg.states.get_joined_users(msg.chat_id)
        who_s_turn = random.choice(users).id
    else:
        who_s_turn = payload.winner
        user = msg.states.get_user_info(payload.winner)
        # знак "+" удаляется при отправке в ВК
        text += f"💪🏻 {user.name}: {PLUS_SIGN}{current_price}{LINE_BREAK}"

    msg.states.set_who_s_turn(msg.chat_id, who_s_turn)
    for user_id in wrong_answered_users_ids:
        user = msg.states.get_user_info(user_id)
        text += f"😥 {user.name}: -{current_price}{LINE_BREAK}"

    if not text:
        text = "Ответов не поступило... 💤"

    if msg.app.config.vk_bot.beautiful:
        await msg.send(f"Правильный ответ:{LINE_BREAK}💡 {answer.title}{LINE_BREAK}📖 {answer.description}")
        await msg.send(f"Итоги раунда:{LINE_BREAK}" + text)
    else:
        await msg.send(f"Правильный ответ:{LINE_BREAK}"
                       f"💡 {answer.title}{LINE_BREAK}📖 {answer.description}{LINE_BREAK}{LINE_BREAK}"
                       f"Итоги раунда:{LINE_BREAK}" + text)

    msg.states.question_ended(msg.chat_id)
    await show_scoreboard(msg, ShowScoreboardPayload(game_id=payload.game_id, new=True))


@filter_game_id
@filter_playing_users
async def show_scoreboard(msg: MessageCallback, payload: ShowScoreboardPayload):
    is_passed = False
    async with msg.states.locks.game_status(msg.chat_id):
        if msg.states.get_game_status(msg.chat_id) == BotActions.show_scoreboard:
            is_passed = True
            msg.states.set_game_status(msg.chat_id, BotActions.choose_theme)
    if not is_passed:
        return await msg.show_snackbar(Texts.old_game_round)

    scores = await msg.games.get_game_scores(payload.game_id)
    scores.sort(key=lambda i: i.score, reverse=True)

    text = f"Топ 5 игроков:{LINE_BREAK}"
    for user in scores[:5]:
        text += f"👤 {user.first_name} {user.last_name}: {user.score} " \
                f"({user.n_correct_answers}:{user.n_wrong_answers}){LINE_BREAK}"

    keyboard = Keyboard(inline=True, buttons=[
        [CallbackButton("👍🏻 Дальше",
                        payload=ChooseThemePayload(game_id=payload.game_id, new=True),
                        color=ButtonColor.green)],
        [CallbackButton("⛔ Завершить игру",
                        payload=ConfirmStopGamePayload(game_id=payload.game_id),
                        color=ButtonColor.red)],
    ])

    if payload.new:
        await msg.send(text, keyboard=keyboard)
    else:
        await msg.edit(text, keyboard=keyboard)


@filter_game_id
@filter_playing_users
async def confirm_stop_game(msg: MessageCallback, payload: ConfirmStopGamePayload):
    # остановить игру может любой пользователь
    is_passed = False
    async with msg.states.locks.game_status(msg.chat_id):
        if msg.states.get_game_status(msg.chat_id) == BotActions.choose_theme:
            is_passed = True
            msg.states.set_game_status(msg.chat_id, BotActions.show_scoreboard)
    if not is_passed:
        return await msg.show_snackbar(Texts.too_late)

    if msg.app.config.vk_bot.beautiful:
        await msg.delete()
    else:
        await msg.event_ok()
    await msg.send("Завершить игру?", keyboard=Keyboard(inline=True, buttons=[
        [
            CallbackButton("Да",
                           payload=StopGamePayload(game_id=payload.game_id, new=False),
                           color=ButtonColor.red),
            CallbackButton("Нет",
                           payload=ShowScoreboardPayload(game_id=payload.game_id, new=False),
                           color=ButtonColor.green),
        ]
    ]))


@filter_game_id
@filter_playing_users
async def stop_game(msg: Union[MessageText, MessageCallback], payload: StopGamePayload):
    # остановить игру может любой пользователь
    if isinstance(msg, MessageCallback):
        is_passed = False
        async with msg.states.locks.game_status(msg.chat_id):
            if msg.states.get_game_status(msg.chat_id) != BotActions.game_finished:
                is_passed = True
                msg.states.set_game_status(msg.chat_id, BotActions.game_finished)
        if not is_passed:
            return await msg.show_snackbar(Texts.game_is_already_stopped)

    users = await msg.games.get_game_scores(payload.game_id)
    users.sort(key=lambda i: i.score, reverse=True)

    medals = "🥇🥈🥉" + "👤" * max(0, len(users) - 3)
    text = f"Итоговые результаты:{LINE_BREAK}"
    for user, medal in zip(users, medals):
        text += f"{medal} {user.first_name} {user.last_name}: {user.score} " \
                f"({user.n_correct_answers}:{user.n_wrong_answers}){LINE_BREAK}{LINE_BREAK}"

    if payload.new:
        if msg.app.config.vk_bot.beautiful and isinstance(msg, MessageCallback):
            await msg.edit(msg.states.get_previous_text(msg.chat_id))
        await msg.send(text, keyboard=keyboards.final_results())
    else:
        assert isinstance(msg, MessageCallback)
        await msg.edit(text, keyboard=keyboards.final_results())


async def force_stop_game(msg: MessageText, _: BasePayload):
    # force stop game if anybody can't proceed (works only where apply filter_who_s_turn decorator)
    async with msg.states.locks.game_status(msg.chat_id):
        if msg.states.get_game_status(msg.chat_id) not in [
            BotActions.choose_question, BotActions.send_question
        ]:
            return
        msg.states.set_game_status(msg.chat_id, BotActions.game_finished)

    game_id = msg.states.get_game_id(msg.chat_id)
    if game_id is None:
        return

    users = await msg.games.get_game_scores(game_id)
    users.sort(key=lambda i: i.score, reverse=True)

    medals = "🥇🥈🥉" + "👤" * max(0, len(users) - 3)
    text = f"Итоговые результаты:{LINE_BREAK}"
    for user, medal in zip(users, medals):
        text += f"{medal} {user.first_name} {user.last_name}: {user.score} " \
                f"({user.n_correct_answers}:{user.n_wrong_answers}){LINE_BREAK}{LINE_BREAK}"

    await msg.send(text, keyboard=keyboards.final_results())
