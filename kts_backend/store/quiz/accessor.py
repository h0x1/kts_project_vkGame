from typing import Optional

from kts_backend.base.base_accessor import BaseAccessor
from kts_backend.quiz.models import Theme, Question, Answer


class QuizAccessor(BaseAccessor):
    async def create_theme(self, title: str) -> Theme:
        theme = Theme(id=self.app.database.next_theme_id, title=str(title))
        self.app.database.themes.append(theme)
        return theme

    async def get_theme_by_title(self, title: str) -> Optional[Theme]:
        for theme in self.app.database.themes:
            if theme.title == title:
                return theme
        return None

    async def get_theme_by_id(self, id_: int) -> Optional[Theme]:
        for theme in self.app.database.themes:
            if theme.id == id_:
                return theme
        return None

    async def list_themes(self) -> list[Theme]:
        return self.app.database.themes.copy()

    async def get_question_by_title(self, title: str) -> Optional[Question]:
        for question in self.app.database.questions:
            if question.title == title:
                return question
        return None

    async def create_question(
        self, title: str, theme_id: int, answers: list[Answer]
    ) -> Question:
        question = Question(
            title=title,
            theme_id=theme_id,
            answers=answers,
            id=self.app.database.next_question_id,
        )

        self.app.database.questions.append(question)
        return question

    async def list_questions(
        self, theme_id: Optional[int] = None
    ) -> list[Question]:
        all_questions = self.app.database.questions

        if theme_id is None:
            return all_questions

        return list(filter(lambda q: q.theme_id == theme_id, all_questions))
