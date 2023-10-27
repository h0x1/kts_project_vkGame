from aiohttp import web_exceptions
from aiohttp_apispec import docs, response_schema, querystring_schema

from app.game import schemes
from app.web.app import View
from app.web.utils import json_response, require_login


@require_login
class FetchGamesView(View):
    @docs(description="Returns all games by page index.")
    @querystring_schema(schemes.QueryFetchGamesSchema)
    @response_schema(schemes.FetchGamesResponseSchema)
    async def get(self):
        query = schemes.QueryFetchGamesSchema().load(self.request.query)
        self.request.app.logger.debug(f"get games {query}")
        games = await self.store.games.fetch_games(
            page=query.get("page"), per_page=query.get("per_page", 10)
        )
        return json_response(
            data=[schemes.GameSchema().dump(i) for i in games],
        )

    async def post(self):
        raise web_exceptions.HTTPNotImplemented()


@require_login
class FetchGameStatsView(View):
    @docs(description="Games stats.")
    @querystring_schema(schemes.QueryFetchGameStatsSchema)
    @response_schema(schemes.FetchGameStatsResponseSchema)
    async def get(self):
        query = schemes.QueryFetchGameStatsSchema().load(self.request.query)
        self.request.app.logger.debug(f"get game stats {query}")
        response = await self.store.games.fetch_game_stats(
            n_winners=query.get("n_winners", 3),
            n_scorers=query.get("n_scorers", 3),
        )
        return json_response(data=schemes.GameStatsSchema().dump(response))

    async def post(self):
        raise web_exceptions.HTTPNotImplemented()
