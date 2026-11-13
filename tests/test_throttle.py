import psycopg
from flask import Flask

from otto import throttle


class BrokenConnection:
    def __init__(self) -> None:
        self.rolled_back = False

    def rollback(self) -> None:
        self.rolled_back = True


def test_guard_rolls_back_failed_throttle_write(monkeypatch) -> None:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret"
    connection = BrokenConnection()

    def fail_to_count(*args) -> None:
        raise psycopg.OperationalError("boom")

    monkeypatch.setitem(throttle.LIMITS, "contact", (1, 1))
    monkeypatch.setattr(throttle, "get_db", lambda: connection)
    monkeypatch.setattr(throttle, "_consume", fail_to_count)

    @app.post("/contact")
    def contact() -> str:
        return "ok"

    app.before_request(throttle.guard)

    response = app.test_client().post("/contact")

    assert response.status_code == 200
    assert connection.rolled_back
