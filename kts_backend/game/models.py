import typing
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, Boolean
from app.store.database.sqlalchemy_base import db
from app.utils import now

if typing.TYPE_CHECKING:
    import sqlalchemy as db


@dataclass
class UserDC:
    id: int  # this is vk_id
    first_name: str
    last_name: str
    joined_at: Optional[datetime] = None
    score: Optional[int] = None
    n_correct_answers: Optional[int] = None
    n_wrong_answers: Optional[int] = None


class UserModel(db):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    joined_at = Column(DateTime(timezone=True), default=now)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.score = 0
        self.n_correct_answers = 0
        self.n_wrong_answers = 0

    def as_dataclass(self) -> UserDC:
        return UserDC(
            id=self.id,
            first_name=self.first_name,
            last_name=self.last_name,
            joined_at=self.joined_at,
            score=self.score,
            n_correct_answers=self.n_correct_answers,
            n_wrong_answers=self.n_wrong_answers,
        )


@dataclass
class ChatDC:
    id: int  # this is vk_id
    joined_at: Optional[datetime] = None


class ChatModel(db):
    __tablename__ = "chats"

    id = Column(BigInteger, primary_key=True, nullable=False)
    joined_at = Column(DateTime(timezone=True), default=now)

    def as_dataclass(self) -> ChatDC:
        return ChatDC(id=self.id, joined_at=self.joined_at)


@dataclass
class GameDC:
    id: int
    chat_id: int
    is_stopped: bool
    started_at: datetime
    finished_at: Optional[datetime]
    users: list[UserDC]


# При удалении чата удаляется и игра
class GameModel(db):
    __tablename__ = "games"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    chat_id = Column(
        ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    is_stopped = Column(Boolean, default=False)
    started_at = Column(DateTime(timezone=True), default=now)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    def __init__(self, *args, **kwargs):
        super(GameModel, self).__init__(*args, **kwargs)
        self._users: list[UserModel] = []
        self._scores: list[GameUserScoreModel] = []

    @property
    def scores(self):
        return self._scores

    @scores.setter
    def scores(self, value):
        self._scores.append(value)

    @property
    def users(self):
        return self._users

    @users.setter
    def users(self, value):
        self._users.append(value)

    def as_dataclass(self) -> GameDC:
        scores: dict[int, GameUserScoreModel] = {
            i.user_id: i for i in self.scores
        }
        for user in self._users:
            user.score = scores[user.id].score
            user.n_correct_answers = scores[user.id].n_correct_answers
            user.n_wrong_answers = scores[user.id].n_wrong_answers
        self._users.sort(key=lambda i: i.score, reverse=True)
        return GameDC(
            id=self.id,
            chat_id=self.chat_id,
            is_stopped=self.is_stopped,
            started_at=self.started_at,
            finished_at=self.finished_at,
            users=[i.as_dataclass() for i in self._users],
        )


# Данные score просто дополняют таблицу "GameUsers", поэтому объединены в эту таблицу
# При удалении игры или пользователя удаляется и score
class GameUserScoreModel(db):
    __tablename__ = "game_user_scores"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    game_id = Column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    score = Column(BigInteger, default=0)
    n_correct_answers = Column(BigInteger, default=0)
    n_wrong_answers = Column(BigInteger, default=0)


# При удалении игры или вопроса удаляется и эта запись
class GameAskedQuestionModel(db):
    __tablename__ = "game_asked_questions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    game_id = Column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=False
    )
    question_id = Column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    is_answered = Column(Boolean, default=False)

    # по истечении времени может не быть правильных ответов,
    # поэтому вводим это поле для определения завершения приема ответов
    is_done = Column(Boolean, default=False)

    started_at = Column(DateTime(timezone=True), default=now)


@dataclass
class TopWinnerDC:
    id: int
    first_name: str
    last_name: str
    joined_at: datetime
    win_count: int


@dataclass
class TopScorerDC:
    id: int
    first_name: str
    last_name: str
    joined_at: datetime
    score: int


@dataclass
class GameStatsDC:
    games_total: int
    games_average_per_day: float
    duration_total: int
    duration_average: float
    top_winners: list[TopWinnerDC]
    top_scorers: list[TopScorerDC]

    def as_dict(self) -> dict:
        return asdict(self)
