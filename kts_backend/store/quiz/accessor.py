from typing import Optional

from app.base.base_accessor import BaseAccessor
from app.quiz.models import Theme, ThemeModel, Question, QuestionModel, Answer
from sqlalchemy import select, func


class QuizAccessor(BaseAccessor):
    async def create_theme(self, title: str) -> Theme:
        async with self.app.database.session() as session:
            themeid = (await session.execute(
                select([func.count()]).select_from(ThemeModel)
            ))
        async with self.app.database.session.begin() as session:
            theme = ThemeModel(title=title,
            id=themeid.scalar()+1)
            session.add(theme)
            return theme.to_dc()

    async def get_theme_by_title(self, title: str) -> Optional[Theme]:
        async with self.app.database.session() as session:
            theme = (await session.execute(
                select(ThemeModel)
                .where(ThemeModel.title == title)
            )).scalar()
        if not theme:
            return
        return theme.to_dc()


    async def get_theme_by_id(self, id_: int) -> Optional[Theme]:
        async with self.app.database.session() as session:
            theme = (await session.execute(
                select(ThemeModel)
                .where(ThemeModel.id == id_)
            )).scalar()
        if not theme:
            return
        return theme.to_dc()


    async def list_themes(self) -> list[Theme]:
        async with self.app.database.session() as session:
            theme_models:list[ThemeModel] = (await session.execute(
                select(ThemeModel)
            )).all()
        return theme_models

    async def get_question_by_title(self, title: str) -> Optional[Question]:
        async with self.app.database.session() as session:
            question = (await session.execute(
                select(QuestionModel)
                .where(QuestionModel.title == title)
            )).scalar()
        if not question:
            return
        return question.to_dc()

    async def create_question(
        self, title: str, theme_id: int, answers: list[Answer]
    ) -> Question:

        async with self.app.database.session() as session:
            questid = (await session.execute(
                select([func.count()]).select_from(QuestionModel)
            ))
        async with self.app.database.session.begin() as session:
            question = QuestionModel(title=title,
            theme_id=theme_id,
            answers=answers,
            id=questid.scalar()+1)
            session.add(question)
            return question.to_dc()

    async def list_questions(
        self, theme_id: Optional[int] = None
    ) -> list[Question]:
        async with self.app.database.session() as session:
            all_questions:list[QuestionModel] = (await session.execute(
                select(QuestionModel)
            )).all()
        if theme_id is None:
            return all_questions

        return list(filter(lambda q: q.theme_id == theme_id, all_questions))
