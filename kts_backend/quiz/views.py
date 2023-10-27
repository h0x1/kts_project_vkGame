from aiohttp.web_exceptions import HTTPConflict, HTTPNotFound
from aiohttp_apispec import (
    docs,
    request_schema,
    response_schema,
    querystring_schema,
)

from app.admin.decorators import auth_required
from app.quiz.schemes import (
    ThemeRequestSchema,
    ThemeListResponseSchema,
    QuestionRequestSchema,
    QuestionResponseSchema,
    ThemeResponseSchema,
    QuestionListResponseSchema,
    QuestionRequestQuerySchema,
)
from app.web.app import View
from app.web.utils import json_response


class ThemeAddView(View):
    @docs(
        tags=["quiz"],
        summary="Add new theme",
        description="Add new theme to database",
    )
    @request_schema(ThemeRequestSchema)
    @response_schema(ThemeResponseSchema, 200)
    @auth_required
    async def post(self):
        title = self.data["title"]

        if await self.store.quizzes.get_theme_by_title(title=title) is not None:
            raise HTTPConflict

        theme = await self.store.quizzes.create_theme(title=title)
        return json_response(data=ThemeResponseSchema().dump(theme))


class ThemeListView(View):
    @docs(
        tags=["quiz"],
        summary="Get list of themes",
        description="Get list all of themes from database",
    )
    @response_schema(ThemeListResponseSchema, 200)
    @auth_required
    async def get(self):
        themes = await self.store.quizzes.list_themes()
        return json_response(
            data={"themes": ThemeResponseSchema().dump(themes, many=True)}
        )


class QuestionAddView(View):
    @docs(
        tags=["quiz"],
        summary="Add new question",
        description="Add new question to database",
    )
    @request_schema(QuestionRequestSchema)
    @response_schema(QuestionResponseSchema, 200)
    @auth_required
    async def post(self):
        title, theme_id, answers = (
            self.data["title"],
            self.data["theme_id"],
            self.data["answers"],
        )
        print("sss3")
        if await self.store.quizzes.get_question_by_title(title) is not None:
            raise HTTPConflict
        print("sss2")
        if await self.store.quizzes.get_theme_by_id(theme_id) is None:
            raise HTTPNotFound
        print("sss")
        question = await self.store.quizzes.create_question(
            title, theme_id, answers
        )

        return json_response(data=QuestionResponseSchema().dump(question))


class QuestionListView(View):
    @docs(
        tags=["quiz"],
        summary="Get list of questions",
        description="Get list all of questions from database",
    )
    @querystring_schema(QuestionRequestQuerySchema)
    @response_schema(QuestionListResponseSchema, 200)
    @auth_required
    async def get(self):
        theme_id = self.request.query.get("theme_id")
        questions = await self.store.quizzes.list_questions(theme_id)
        return json_response(
            data={
                "questions": QuestionResponseSchema().dump(questions, many=True)
            }
        )
