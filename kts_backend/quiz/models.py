from dataclasses import dataclass
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, BigInteger, Boolean, ForeignKey
from kts_backend.database.sqlalchemy_base import db


@dataclass
class Theme:
    id: int
    title: str


@dataclass
class Question:
    id: int
    title: str
    theme_id: int
    answers: list["Answer"]


@dataclass
class Answer:
    title: str
    is_correct: bool


class ThemeModel(db):
    __tablename__ = "themes"
    id = Column(BigInteger, primary_key=True)
    title = Column(String, unique=True, nullable=False)

    def to_dc(self) -> Theme:
        return Theme(id=self.id, title=self.title)


class QuestionModel(db):
    __tablename__ = "questions"
    id = Column(BigInteger, primary_key=True)
    title = Column(String, unique=True)
    theme_id = Column(
        BigInteger, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False
    )
    answers = relationship("AnswerModel")

    def to_dc(self) -> Question:
        return Question(
            id=self.id,
            title=self.title,
            theme_id=self.theme_id,
            answers=[answer.to_dc() for answer in self.answers],
        )


class AnswerModel(db):
    __tablename__ = "answers"
    id = Column(BigInteger, primary_key=True)
    title = Column(String)
    is_correct = Column(Boolean)
    question_id = Column(
        BigInteger,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )

    def to_dc(self) -> Answer:
        return Answer(title=self.title, is_correct=self.is_correct)
