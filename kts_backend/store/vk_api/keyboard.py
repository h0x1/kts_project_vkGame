from typing import Optional

from app.store.game.payload import BasePayload, EmptyPayload

MAX_CAROUSEL_ELEMENTS = 6  # вместо 10, иначе может вызвать ошибку по длине сообщения


class ButtonColor:
    red = "negative"
    green = "positive"
    blue = "primary"
    white = "secondary"


class Button:
    type: str
    label: str
    payload: BasePayload
    color: str

    def as_dict(self) -> dict:
        return dict(action=dict(type=self.type, label=self.label, payload=self.payload.as_dict()),
                    color=self.color)


class TextButton(Button):

    def __init__(self, label: str, payload: Optional[BasePayload] = None, color=ButtonColor.white):
        super().__init__()
        self.type = "text"
        self.label = label
        self.payload = payload or EmptyPayload()
        self.color = color


class CallbackButton(Button):

    def __init__(self, label: str, payload: Optional[BasePayload] = None, color=ButtonColor.white):
        super().__init__()
        self.type = "callback"
        self.label = label
        self.payload = payload or EmptyPayload()
        self.color = color


class Keyboard:

    def __init__(self, one_time=False, inline=False, buttons: list[list[Button]] = None):
        self.one_time = one_time
        self.inline = inline
        self.buttons = buttons or []

    def add(self, buttons: list[Button]) -> None:
        assert type(buttons) is list
        self.buttons.append(buttons)

    def as_dict(self) -> dict:
        return dict(one_time=self.one_time,
                    inline=self.inline,
                    buttons=[[i.as_dict() for i in row] for row in self.buttons])


class CarouselAction:

    def as_dict(self) -> dict:
        raise NotImplementedError


class CarouselActionOpenLink(CarouselAction):

    def __init__(self, link: str):
        super().__init__()
        self.link = link

    def as_dict(self) -> dict:
        return dict(type="open_link", link=self.link)


class CarouselActionOpenPhoto(CarouselAction):

    def as_dict(self) -> dict:
        return dict(type="open_photo")


class CarouselElement:

    def __init__(self,
                 title: str,
                 description: str,
                 photo_id: str,
                 buttons: list[Button],
                 action: Optional[CarouselAction] = None):
        self.title = title
        self.description = description
        self.photo_id = photo_id
        self.buttons = buttons
        self.action = action

    def as_dict(self) -> dict:
        d = dict(title=self.title,
                 description=self.description,
                 photo_id=self.photo_id,
                 buttons=[i.as_dict() for i in self.buttons])
        if self.action:
            d["action"] = self.action.as_dict()
        return d


class Carousel:

    def __init__(self, elements: Optional[list[CarouselElement]] = None):
        self.elements = elements or []

    def add_element(self, element: CarouselElement) -> None:
        self.elements.append(element)

    def as_dict(self) -> dict:
        return dict(
            type="carousel",
            elements=[i.as_dict() for i in self.elements[:MAX_CAROUSEL_ELEMENTS]],
        )
