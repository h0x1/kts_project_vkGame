from marshmallow import Schema, fields, validate, ValidationError
from app.web.schemes import OkResponseSchema


class UserSchema(Schema):
    id = fields.Int(required=True)
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    joined_at = fields.Str(required=True)
    score = fields.Int(required=True)
    n_correct_answers = fields.Int(required=True)
    n_wrong_answers = fields.Int(required=True)


class GameSchema(Schema):
    id = fields.Int(required=True)
    chat_id = fields.Int(required=True)
    is_stopped = fields.Boolean(required=True)
    started_at = fields.DateTime(required=True)
    finished_at = fields.DateTime(required=False)
    users = fields.Nested(UserSchema, many=True)


def validate_page(value):
    if value < 1:
        raise ValidationError("Page must be >= 1")


class QueryFetchGamesSchema(Schema):
    page = fields.Int(required=False, validate=validate_page)
    per_page = fields.Int(required=False)


class FetchGamesResponseSchema(OkResponseSchema):
    data = fields.Nested(GameSchema, many=True)


# ----------------------------------------------------


class TopWinner(Schema):
    id = fields.Int(required=True)
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    joined_at = fields.DateTime(required=True)
    win_count = fields.Int(required=True)


class TopScorer(Schema):
    id = fields.Int(required=True)
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    joined_at = fields.DateTime(required=True)
    score = fields.Int(required=True)


class GameStatsSchema(Schema):
    games_total = fields.Int(required=True)
    games_average_per_day = fields.Float(required=True)
    duration_total = fields.Int(required=True)
    duration_average = fields.Float(required=True)
    top_winners = fields.Nested(TopWinner, many=True)
    top_scorers = fields.Nested(TopScorer, many=True)


class QueryFetchGameStatsSchema(Schema):
    n_winners = fields.Int(required=False)
    n_scorers = fields.Int(required=False)


class FetchGameStatsResponseSchema(OkResponseSchema):
    data = fields.Nested(GameStatsSchema)
