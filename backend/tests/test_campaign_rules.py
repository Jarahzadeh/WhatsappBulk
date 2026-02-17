from app.services.campaigns import auto_pause_needed


class Msg:
    def __init__(self, status, campaign_id=1):
        self.status = status
        self.campaign_id = campaign_id


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeDB:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, _):
        return FakeResult(self.rows)


def test_auto_pause_threshold():
    db = FakeDB([Msg('failed'), Msg('failed'), Msg('sent')])
    assert auto_pause_needed(db, 1, threshold=0.5)
