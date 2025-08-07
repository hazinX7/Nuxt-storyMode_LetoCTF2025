from flask import Blueprint

from CTFd.exceptions.challenges import (
    ChallengeCreateException,
    ChallengeUpdateException,
)
from CTFd.models import Challenges, db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES, BaseChallenge
from CTFd.plugins.dynamic_challenges.decay import DECAY_FUNCTIONS, logarithmic
from CTFd.plugins.migrations import upgrade


class DynamicChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "dynamic"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    initial = db.Column(db.Integer, default=0)
    minimum = db.Column(db.Integer, default=0)
    decay = db.Column(db.Integer, default=0)
    function = db.Column(db.String(32), default="logarithmic")

    def __init__(self, *args, **kwargs):
        super(DynamicChallenge, self).__init__(**kwargs)
        try:
            self.value = kwargs["initial"]
        except KeyError:
            raise ChallengeCreateException("Missing initial value for challenge")


class DynamicValueChallenge(BaseChallenge):
    id = "dynamic"
    name = "dynamic"
    templates = (
        {
            "create": "/plugins/dynamic_challenges/assets/create.html",
            "update": "/plugins/dynamic_challenges/assets/update.html",
            "view": "/plugins/dynamic_challenges/assets/view.html",
        }
    )
    scripts = {
        "create": "/plugins/dynamic_challenges/assets/create.js",
        "update": "/plugins/dynamic_challenges/assets/update.js",
        "view": "/plugins/dynamic_challenges/assets/view.js",
    }

    route = "/plugins/dynamic_challenges/assets/"

    blueprint = Blueprint(
        "dynamic_challenges",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )
    challenge_model = DynamicChallenge

    @classmethod
    def calculate_value(cls, challenge):
        f = DECAY_FUNCTIONS.get(challenge.function, logarithmic)
        value = f(challenge)

        challenge.value = value
        db.session.commit()
        return challenge

    @classmethod
    def read(cls, challenge):
        challenge = DynamicChallenge.query.filter_by(id=challenge.id).first()
        data = super().read(challenge)
        data.update(
            {
                "initial": challenge.initial,
                "decay": challenge.decay,
                "minimum": challenge.minimum,
                "function": challenge.function,
            }
        )
        return data

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json()

        for attr, value in data.items():

            if attr in ("initial", "minimum", "decay"):
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    raise ChallengeUpdateException(f"Invalid input for '{attr}'")
            setattr(challenge, attr, value)

        return DynamicValueChallenge.calculate_value(challenge)

    @classmethod
    def solve(cls, user, team, challenge, request):
        super().solve(user, team, challenge, request)

        DynamicValueChallenge.calculate_value(challenge)


def load(app):
    upgrade(plugin_name="dynamic_challenges")
    CHALLENGE_CLASSES["dynamic"] = DynamicValueChallenge
    register_plugin_assets_directory(
        app, base_path="/plugins/dynamic_challenges/assets/"
    )
