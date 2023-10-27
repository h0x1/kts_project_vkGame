from dataclasses import dataclass
from typing import Optional

LINE_BREAK = "%0A"
PLUS_SIGN = "%2B"

PRICES = [500, 1000, 1500, 2000, 2500]


class UserCommands:
    start = "/start"
    stop = "/stop"


class BotActions:
    empty = "empty"
    invite = "invite"
    main_menu = "main_menu"
    game_rules = "game_rules"
    bot_info = "bot_info"
    create_new_game = "create_new_game"
    join_users = "join_users"
    start_game = "start_game"
    choose_theme = "choose_theme"
    choose_question = "choose_question"
    send_question = "send_question"
    get_answer = "get_answer"
    show_answer = "show_answer"
    show_scoreboard = "show_scoreboard"
    confirm_stop_game = "confirm_stop_game"
    stop_game = "stop_game"
    game_finished = "stop_game"


class Stickers:
    dog_wait_sec = 6571


class Photos:
    main_wallpaper = "photo-210566950_457239020"
    theme_carousel = "-210566950_457239018"


class Texts:
    about = f"""🕹 Привет.{LINE_BREAK}
Я - бот для игры в викторину.{LINE_BREAK}
Моя страница ВК: https://vk.com/public210566950 {LINE_BREAK}
Команды:{LINE_BREAK}
👉🏻 "/start" - начать новую сессию.{LINE_BREAK}
👉🏻 "/stop" - завершить игру во время выбора вопроса.{LINE_BREAK}
Желаю приятной игры."""
    rules = f"""📖 Правила игры.{LINE_BREAK}
👉🏻 Основная задача игры - заработать как можно больше очков, правильно отвечая на вопросы.{LINE_BREAK}
👉🏻 Первый вопрос выбирает тот, кто первым нажал на кнопку Старт.{LINE_BREAK}
👉🏻 Каждый вопрос имеет свою стоимость (от 500 до 2500).{LINE_BREAK}
👉🏻 Очки начисляются первому, кто правильно ответил на вопрос. 
Он же имеет право на выбор следующего вопроса.{LINE_BREAK}
👉🏻 За неправильный ответ снимаются очки в количестве стоимости вопроса.{LINE_BREAK}
👉🏻 Если не знаете ответ - можете не отвечать. {LINE_BREAK}
👉🏻 Если по прошествии 12 секунд никто не ответил или не было правильного ответа,
то предлагается выбор другого вопроса.{LINE_BREAK}
👉🏻 Вы можете завершить игру после любого раунда.{LINE_BREAK}
✊🏻 Удачи!"""
    goodbye = "👋🏻"

    game_is_already_started = "Игра уже началась."
    game_is_already_stopped = "Игра уже остановлена."
    you_are_already_joined = "Вы уже присоединились к игре."
    nobody_joined = "Никто не присоединился к игре."
    firstly_join_the_game = "Сначала присоединитесь к игре."
    error_try_again = "Произошла ошибка. Повторите ещё раз."
    not_your_turn = "Сейчас не ваша очередь."
    not_your_game = "Вы не участвуете в игре."
    old_game_round = "Этот раунд игры устарел."
    too_late = "Опоздали..."
    you_are_already_answered = "Вы уже ответили."
    flood_detected = "VK ограничивает количество сообщений в час. Продолжим, как только снимется ограничение."


@dataclass
class BasePayload:
    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class EmptyPayload(BasePayload):
    action: str = BotActions.empty


@dataclass
class MainMenuPayload(BasePayload):
    source: str
    new: bool = False
    action: str = BotActions.main_menu


@dataclass
class GameRulesPayload(BasePayload):
    action: str = BotActions.game_rules


@dataclass
class BotInfoPayload(BasePayload):
    action: str = BotActions.bot_info


@dataclass
class CreateNewGamePayload(BasePayload):
    action: str = BotActions.create_new_game


@dataclass
class JoinUsersPayload(BasePayload):
    action: str = BotActions.join_users


@dataclass
class StartGamePayload(BasePayload):
    action: str = BotActions.start_game


@dataclass
class BaseGamePayload(BasePayload):
    game_id: int


@dataclass
class ChooseThemePayload(BaseGamePayload):
    new: bool = False
    action: str = BotActions.choose_theme


@dataclass
class ChooseQuestionPayload(BaseGamePayload):
    theme_id: int
    theme_title: str
    action: str = BotActions.choose_question


@dataclass
class SendQuestionPayload(BaseGamePayload):
    theme_id: int
    price: int
    action: str = BotActions.send_question


@dataclass
class GetAnswerPayload(BaseGamePayload):
    question_id: int
    answer_id: int
    uid: str
    action: str = BotActions.get_answer


@dataclass
class ShowAnswerPayload(BaseGamePayload):
    question_id: int
    winner: Optional[int] = None
    action: str = BotActions.show_answer


@dataclass
class ShowScoreboardPayload(BaseGamePayload):
    new: Optional[bool] = True
    action: str = BotActions.show_scoreboard


@dataclass
class ConfirmStopGamePayload(BaseGamePayload):
    action: str = BotActions.confirm_stop_game


@dataclass
class StopGamePayload(BaseGamePayload):
    new: Optional[bool] = True
    action: str = BotActions.stop_game


class PayloadFactory:
    @classmethod
    def create(cls, payload: dict) -> BasePayload:
        action = payload.get("action")
        if action == BotActions.main_menu:
            return MainMenuPayload(
                source=payload["source"], new=payload.get("new", False)
            )
        elif action == BotActions.game_rules:
            return GameRulesPayload()
        elif action == BotActions.bot_info:
            return BotInfoPayload()
        elif action == BotActions.create_new_game:
            return CreateNewGamePayload()
        elif action == BotActions.join_users:
            return JoinUsersPayload()
        elif action == BotActions.start_game:
            return StartGamePayload()
        elif action == BotActions.choose_theme:
            return ChooseThemePayload(
                game_id=payload["game_id"], new=payload.get("new", False)
            )
        elif action == BotActions.choose_question:
            return ChooseQuestionPayload(
                game_id=payload["game_id"],
                theme_id=payload["theme_id"],
                theme_title=payload["theme_title"],
            )
        elif action == BotActions.send_question:
            return SendQuestionPayload(
                game_id=payload["game_id"],
                theme_id=payload["theme_id"],
                price=payload["price"],
            )
        elif action == BotActions.get_answer:
            return GetAnswerPayload(
                game_id=payload["game_id"],
                question_id=payload["question_id"],
                answer_id=payload["answer_id"],
                uid=payload["uid"],
            )
        elif action == BotActions.show_answer:
            return ShowAnswerPayload(
                game_id=payload["game_id"],
                question_id=payload["question_id"],
                winner=payload.get("winner"),
            )
        elif action == BotActions.show_scoreboard:
            return ShowScoreboardPayload(
                game_id=payload["game_id"], new=payload.get("new", True)
            )
        elif action == BotActions.confirm_stop_game:
            return ConfirmStopGamePayload(game_id=payload["game_id"])
        elif action == BotActions.stop_game:
            return StopGamePayload(
                game_id=payload["game_id"], new=payload.get("new", True)
            )
        else:
            return EmptyPayload()
