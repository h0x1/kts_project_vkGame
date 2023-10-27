import asyncio
import json
from collections import defaultdict
from datetime import datetime
from typing import Optional

from redis import Redis
from sqlalchemy import and_, not_
from sqlalchemy.dialects.postgresql import insert

from app.base.base_accessor import BaseAccessor
from app.game.models import (
    UserDC,
    UserModel,
    ChatModel,
    GameDC,
    GameModel,
    GameAskedQuestionModel,
    GameUserScoreModel,
    GameStatsDC,
    TopWinnerDC,
    TopScorerDC,
    ChatDC,
)
from app.quiz.models import (
    Question,
    Answer,
    QuestionModel,
    AnswerModel,
)
from app.store.game.payload import BotActions
from app.store.vk_api.responses import VKUser
from app.utils import now
from app.web.app import Application


class States:
    game_status = "gs"
    game_id = "gi"
    game_users = "gu"
    who_s_turn = "wt"
    game_prices = "gp"
    current_question_id = "cqi"
    current_price = "cp"
    current_question = "cq"
    current_answer = "ca"
    current_answer_id = "cai"
    users_answered = "ua"
    user_info = "ui"
    previous_msg_text = "pmt"
    flood = "fl"


class Locks:
    def __init__(self):
        self._game_status_locks: dict[int, asyncio.Lock] = {}
        self._game_users_locks: dict[int, asyncio.Lock] = {}

    def game_status(self, chat_id: int) -> asyncio.Lock:
        lock = self._game_status_locks.get(chat_id)
        if not lock:
            lock = asyncio.Lock()
            self._game_status_locks[chat_id] = lock
        return lock

    def game_users(self, chat_id: int) -> asyncio.Lock:
        lock = self._game_users_locks.get(chat_id)
        if not lock:
            lock = asyncio.Lock()
            self._game_users_locks[chat_id] = lock
        return lock


class StateAccessor(BaseAccessor):
    redis: Redis
    locks: Locks

    async def connect(self, app: "Application"):
        self.redis = app.database.redis
        self.locks = Locks()

    def restore_status(self, chat_id: int) -> None:
        self.redis.set(States.game_status + str(chat_id), BotActions.main_menu)
        self.redis.delete(States.game_id + str(chat_id))
        self.redis.delete(States.game_users + str(chat_id))
        self.redis.delete(States.who_s_turn + str(chat_id))
        self.redis.delete(States.game_prices + str(chat_id))
        self.redis.delete(States.current_question_id + str(chat_id))
        self.question_ended(chat_id)

    def question_ended(self, chat_id: int) -> None:
        self.redis.delete(States.current_price + str(chat_id))
        self.redis.delete(States.current_question + str(chat_id))
        self.redis.delete(States.current_answer_id + str(chat_id))
        self.redis.delete(States.current_answer + str(chat_id))
        self.redis.delete(States.users_answered + str(chat_id))

    def set_game_id(self, chat_id: int, game_id: int) -> None:
        self.redis.set(States.game_id + str(chat_id), game_id)

    def get_game_id(self, chat_id: int) -> Optional[int]:
        value = self.redis.get(States.game_id + str(chat_id))
        if value is None:
            return None
        return int(value.decode())

    def set_game_status(self, chat_id: int, status: str) -> None:
        self.redis.set(States.game_status + str(chat_id), status)

    def get_game_status(self, chat_id: int) -> Optional[str]:
        value = self.redis.get(States.game_status + str(chat_id))
        if not value:
            return None
        return value.decode()

    def set_users_joined(self, chat_id: int, users: list[VKUser]) -> None:
        self.redis.set(
            States.game_users + str(chat_id),
            json.dumps([i.as_dict() for i in users], ensure_ascii=False),
        )

    def get_joined_users(self, chat_id: int) -> list[VKUser]:
        value = self.redis.get(States.game_users + str(chat_id))
        if not value:
            return []
        return [VKUser(i) for i in json.loads(value.decode())]

    def set_user_info(self, user: VKUser) -> None:
        self.redis.set(
            States.user_info + str(user.id),
            json.dumps(user.as_dict(), ensure_ascii=False),
        )

    def get_user_info(self, user_id: int) -> VKUser:
        value = self.redis.get(States.user_info + str(user_id))
        return VKUser(json.loads(value.decode()))

    def set_who_s_turn(self, chat_id: int, user_id: int) -> None:
        self.redis.set(States.who_s_turn + str(chat_id), user_id)

    def get_who_s_turn(self, chat_id: int) -> int:
        value = self.redis.get(States.who_s_turn + str(chat_id))
        return int(value.decode())

    def set_theme_chosen_prices(
        self, chat_id: int, prices: dict[int, list[int]]
    ) -> None:
        self.redis.set(States.game_prices + str(chat_id), json.dumps(prices))

    def get_theme_chosen_prices(self, chat_id) -> dict[int, list[int]]:
        value = self.redis.get(States.game_prices + str(chat_id))
        if not value:
            return {}
        return {int(k): v for k, v in json.loads(value.decode()).items()}

    def set_current_price(self, chat_id: int, price: int) -> None:
        self.redis.set(States.current_price + str(chat_id), price)

    def get_current_price(self, chat_id: int) -> int:
        return int(self.redis.get(States.current_price + str(chat_id)).decode())

    def set_current_question(self, chat_id: int, question: Question) -> None:
        self.redis.set(
            States.current_question + str(chat_id),
            json.dumps(question.as_dict(), ensure_ascii=False),
        )

    def get_current_question(self, chat_id: int) -> Optional[Question]:
        value = self.redis.get(States.current_question + str(chat_id))
        if not value:
            return None
        return QuestionModel(**json.loads(value.decode())).to_dc()

    def set_current_answer_id(self, chat_id: int, answer_id: int) -> None:
        self.redis.set(States.current_answer_id + str(chat_id), answer_id)

    def get_current_answer_id(self, chat_id: int) -> int:
        value = self.redis.get(States.current_answer_id + str(chat_id))
        return int(value.decode())

    def set_current_answer(self, chat_id: int, answer: Answer) -> None:
        assert answer.is_correct
        self.redis.set(
            States.current_answer + str(chat_id),
            json.dumps(answer.as_dict(), ensure_ascii=False),
        )

    def get_current_answer(self, chat_id: int) -> Answer:
        value = self.redis.get(States.current_answer + str(chat_id))
        return AnswerModel(**json.loads(value.decode())).to_dc()

    def set_users_answered(self, chat_id: int, users: list[int]) -> None:
        self.redis.set(States.users_answered + str(chat_id), json.dumps(users))

    def get_answered_users(self, chat_id: int) -> list[int]:
        value = self.redis.get(States.users_answered + str(chat_id))
        if not value:
            return []
        return json.loads(value.decode())

    def set_previous_text(self, chat_id: int, text: str) -> None:
        self.redis.set(States.previous_msg_text + str(chat_id), text)

    def get_previous_text(self, chat_id: int) -> str:
        return self.redis.get(States.previous_msg_text + str(chat_id)).decode()

    def set_flood_detected(self, chat_id: int) -> None:
        self.redis.set(States.flood + str(chat_id), now().isoformat())

    def set_flood_not_detected(self, chat_id: int) -> None:
        self.redis.delete(States.flood + str(chat_id))

    def is_flood_detected(self, chat_id: int) -> bool:
        """
        По прошествии 3 минут можно пробовать снимать ограничения.
        """
        detected_at = self.redis.get(States.flood + str(chat_id))
        if not detected_at:
            return False
        detected_at = datetime.fromisoformat(detected_at.decode())
        if (now() - detected_at).total_seconds() > 60 * 3:
            return False
        return True


class GameAccessor(BaseAccessor):
    async def restore_status(self, chat_id: int) -> None:
        game_models: list[GameModel] = (
            await GameModel.update.values(is_stopped=True, finished_at=now())
            .where(GameModel.chat_id == chat_id)
            .returning(*GameModel)
            .gino.all()
        )
        if not game_models:
            return
        await GameAskedQuestionModel.update.values(is_done=True).where(
            GameAskedQuestionModel.game_id.in_([i.id for i in game_models])
        ).gino.status()

    async def joined_the_chat(self, chat_id: int) -> None:
        await insert(ChatModel).values(
            id=chat_id
        ).on_conflict_do_nothing().gino.status()

    async def get_chats(self) -> list[ChatDC]:
        chats: list[ChatModel] = await ChatModel.query.gino.all()
        return [i.as_dataclass() for i in chats]

    async def create_users(self, users: list[VKUser]) -> list[UserDC]:
        if not users:
            return []
        stmt = insert(UserModel).values(
            [
                dict(id=i.id, first_name=i.first_name, last_name=i.last_name)
                for i in users
            ]
        )
        user_models: list[UserModel] = (
            await stmt.on_conflict_do_update(
                index_elements=[UserModel.id],
                set_=dict(
                    first_name=stmt.excluded.first_name,
                    last_name=stmt.excluded.last_name,
                ),
            )
            .returning(*UserModel)
            .gino.model(UserModel)
            .all()
        )
        return [i.as_dataclass() for i in user_models]

    async def create_game(self, chat_id, users: list[UserDC]) -> GameDC:
        game: GameModel = await GameModel.create(chat_id=chat_id)
        await GameUserScoreModel.insert().gino.all(
            *(dict(game_id=game.id, user_id=u.id) for u in users)
        )
        return game.as_dataclass()

    async def get_game_by_id(self, game_id: int) -> Optional[GameDC]:
        game: GameModel = await GameModel.query.where(
            GameModel.id == game_id
        ).gino.first()
        if game is None:
            return None
        return game.as_dataclass()

    async def get_game_scores(self, game_id: int) -> list[UserDC]:
        user_models: list[UserModel] = (
            await UserModel.join(
                GameUserScoreModel,
                and_(
                    GameUserScoreModel.user_id == UserModel.id,
                    GameUserScoreModel.game_id == game_id,
                ),
            )
            .select()
            .gino.load(
                UserModel.distinct(UserModel.id).load(
                    score=GameUserScoreModel.score,
                    n_correct_answers=GameUserScoreModel.n_correct_answers,
                    n_wrong_answers=GameUserScoreModel.n_wrong_answers,
                )
            )
            .all()
        )
        return [i.as_dataclass() for i in user_models]

    async def update_game_scores(
        self,
        game_id: int,
        winner_user_id: Optional[int],
        wrong_answered_user_ids: list[int],
        price: int,
    ) -> None:
        if winner_user_id is not None:
            await GameUserScoreModel.update.values(
                score=GameUserScoreModel.score + price,
                n_correct_answers=GameUserScoreModel.n_correct_answers + 1,
            ).where(
                and_(
                    GameUserScoreModel.game_id == game_id,
                    GameUserScoreModel.user_id == winner_user_id,
                )
            ).gino.status()
        if wrong_answered_user_ids:
            await GameUserScoreModel.update.values(
                score=GameUserScoreModel.score - price,
                n_wrong_answers=GameUserScoreModel.n_wrong_answers + 1,
            ).where(
                and_(
                    GameUserScoreModel.game_id == game_id,
                    GameUserScoreModel.user_id.in_(wrong_answered_user_ids),
                )
            ).gino.status()

    async def get_remaining_questions(
        self, game_id: int, theme_id: int
    ) -> list[QuestionModel]:
        exclude_questions = GameAskedQuestionModel.select("question_id").where(
            GameAskedQuestionModel.game_id == game_id
        )

        questions: list[QuestionModel] = (
            await QuestionModel.outerjoin(
                AnswerModel, QuestionModel.id == AnswerModel.question_id
            )
            .select()
            .where(
                and_(
                    QuestionModel.theme_id == theme_id,
                    not_(QuestionModel.id.in_(exclude_questions)),
                )
            )
            .gino.load(
                QuestionModel.distinct(QuestionModel.id).load(
                    answers=AnswerModel.load()
                )
            )
            .all()
        )

        return questions

    async def set_question_asked(
        self, game_id: int, question: QuestionModel
    ) -> None:
        await GameAskedQuestionModel.create(
            game_id=game_id, question_id=question.id
        )

    async def set_game_question_result(
        self, game_id: int, question_id: int, is_answered: bool
    ) -> GameAskedQuestionModel:
        asked_question = (
            await GameAskedQuestionModel.update.values(
                is_answered=is_answered, is_done=True
            )
            .where(
                and_(
                    GameAskedQuestionModel.game_id == game_id,
                    GameAskedQuestionModel.question_id == question_id,
                )
            )
            .returning(*GameAskedQuestionModel)
            .gino.first()
        )
        return asked_question

    async def fetch_games(
        self, page: Optional[int] = None, per_page=10
    ) -> list[GameDC]:
        """
        Этот запрос не работает должным образом, никак не могу понять, почему...
        Данные дублируются, либо суммируются.
        Видимо, потому что имеется отношение many-to-many, которое не поддерживается gino?

        game_models: list[GameModel] = await GameModel \
            .outerjoin(GameUserScoreModel, GameUserScoreModel.game_id == GameModel.id) \
            .outerjoin(UserModel, UserModel.id == GameUserScoreModel.user_id) \
            .select() \
            .gino \
            .load(GameModel.distinct(GameModel.id)
                  .load(users=UserModel.distinct(GameUserScoreModel.user_id)
                        .load(score=GameUserScoreModel.score,
                              n_correct_answers=GameUserScoreModel.n_correct_answers,
                              n_wrong_answers=GameUserScoreModel.n_wrong_answers))) \
            .all()

        А если подгружать и обрабатывать данные только в GameModel,
        то всё работает так, как и ожидается.
        """
        LimitedGameModel = GameModel.alias("limited_games")
        limited_games = GameModel.query
        if page is not None:
            limited_games = limited_games.limit(per_page).offset(
                (page - 1) * per_page
            )
        limited_games = limited_games.alias("limited_games")

        game_models: list[GameModel] = (
            await GameModel.join(
                limited_games, GameModel.id == LimitedGameModel.id
            )
            .outerjoin(
                GameUserScoreModel, GameUserScoreModel.game_id == GameModel.id
            )
            .outerjoin(UserModel, UserModel.id == GameUserScoreModel.user_id)
            .select()
            .gino.load(
                GameModel.distinct(GameModel.id).load(
                    scores=GameUserScoreModel, users=UserModel
                )
            )
            .all()
        )
        return [i.as_dataclass() for i in game_models]

    async def fetch_game_stats(
        self, n_winners: int = 3, n_scorers: int = 3
    ) -> GameStatsDC:
        game_models: list[GameModel] = (
            await GameModel.outerjoin(
                GameUserScoreModel, GameUserScoreModel.game_id == GameModel.id
            )
            .outerjoin(UserModel, UserModel.id == GameUserScoreModel.user_id)
            .select()
            .gino.load(
                GameModel.distinct(GameModel.id).load(
                    scores=GameUserScoreModel, users=UserModel
                )
            )
            .all()
        )

        game_dcs = [i.as_dataclass() for i in game_models]
        finished_game_dcs = [i for i in game_dcs if i.finished_at is not None]

        games_total = len(game_dcs)
        days = (now() - game_dcs[0].started_at).days if game_dcs else 0
        games_average_per_day = games_total / days if days > 0 else 0.0
        duration_total = sum(
            [
                int((i.finished_at - i.started_at).total_seconds())
                for i in finished_game_dcs
            ]
        )
        duration_average = (
            duration_total / len(finished_game_dcs)
            if finished_game_dcs
            else 0.0
        )

        users: dict[int, UserDC] = {u.id: u for g in game_dcs for u in g.users}

        wins = defaultdict(int)
        for game in finished_game_dcs:
            # users already sorted by score
            wins[game.users[0].id] += 1
        wins = [(k, v) for k, v in wins.items()]
        wins.sort(key=lambda i: i[1], reverse=True)
        top_winners = []
        for user_id, win_count in wins[:n_winners]:
            user = users[user_id]
            top_winners.append(
                TopWinnerDC(
                    id=user.id,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    joined_at=user.joined_at,
                    win_count=win_count,
                )
            )

        scores = defaultdict(list)
        for game in finished_game_dcs:
            for user in game.users:
                scores[user.id].append(user.score)
        scores = [(k, max(v)) for k, v in scores.items()]
        scores.sort(key=lambda i: i[1], reverse=True)
        top_scorers = []
        for user_id, max_score in scores[:n_scorers]:
            user = users[user_id]
            top_scorers.append(
                TopScorerDC(
                    id=user.id,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    joined_at=user.joined_at,
                    score=max_score,
                )
            )

        return GameStatsDC(
            games_total=games_total,
            games_average_per_day=games_average_per_day,
            duration_total=duration_total,
            duration_average=duration_average,
            top_winners=top_winners,
            top_scorers=top_scorers,
        )
