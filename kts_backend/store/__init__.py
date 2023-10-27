import typing
from asyncio import Queue
from app.store.manager import BotManager
from app.store.database.database import Database


if typing.TYPE_CHECKING:
    from app.web.app import Application


class Store:
    def __init__(self, app: "Application"):
        from app.store.quiz.accessor import QuizAccessor
        from app.store.vk_api.accessor import VkApiAccessor
        from app.store.admin.accessor import AdminAccessor
        from app.store.vk_api.messenger import VKMessenger
        from app.store.game.accessor import StateAccessor, GameAccessor

        self.quizzes = QuizAccessor(app)
        self.admins = AdminAccessor(app)
        self.vk_api = VkApiAccessor(app)
        self.vk_api_queue = Queue()
        self.bots_manager = BotManager(app)
        self.vk_messenger = VKMessenger(app)
        self.states = StateAccessor(app)
        self.games = GameAccessor(app)


def setup_store(app: "Application"):
    app.database = Database(app)
    app.on_startup.append(app.database.connect)
    app.on_shutdown.append(app.database.disconnect)
    app.store = Store(app)
