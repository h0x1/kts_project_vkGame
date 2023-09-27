import typing
from asyncio import Queue
from kts_backend.store.manager import BotManager


if typing.TYPE_CHECKING:
    from kts_backend.web.app import Application


class Store:
    def __init__(self, app: "Application"):
        from kts_backend.store.quiz.accessor import QuizAccessor
        from kts_backend.store.vk_api.accessor import VkApiAccessor
        from kts_backend.store.admin.accessor import AdminAccessor

        self.quizzes = QuizAccessor(app)
        self.admins = AdminAccessor(app)
        self.vk_api = VkApiAccessor(app)
        self.vk_api_queue = Queue()
        self.bots_manager = BotManager(app)
