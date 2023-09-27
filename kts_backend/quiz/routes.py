import typing

from kts_backend.quiz.views import (
    ThemeAddView,
    ThemeListView,
    QuestionAddView,
    QuestionListView,
)

if typing.TYPE_CHECKING:
    from kts_backend.web.app import Application


def setup_routes(app: "Application"):
    app.router.add_view("/quiz.add_theme", ThemeAddView)
    app.router.add_view("/quiz.list_themes", ThemeListView)
    app.router.add_view("/quiz.add_question", QuestionAddView)
    app.router.add_view("/quiz.list_questions", QuestionListView)
