import typing

if typing.TYPE_CHECKING:
    from app.web.app import Application


def setup_routes(app: "Application"):
    from app.game.views import FetchGamesView, FetchGameStatsView

    app.router.add_view("/admin.fetch_games", FetchGamesView)
    app.router.add_view("/admin.fetch_game_stats", FetchGameStatsView)
