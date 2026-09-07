from app.services.chat_service import ChatService


class _FakeResponses:
    def create(self, **kwargs):
        class _Response:
            output_text = "mock reply"

        return _Response()


class _FakeClient:
    responses = _FakeResponses()


def test_chat_service_returns_output_text():
    service = ChatService(client=_FakeClient(), model="test-model")
    result = service.chat("hello", "You are a test assistant")
    assert result == "mock reply"
