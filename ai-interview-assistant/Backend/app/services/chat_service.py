from typing import Optional

from app.clients.openai_client import get_openai_client
from app.config.settings import get_settings
from app.utils.file_utils import read_text_file


class ChatService:
    def __init__(self, client=None, model: Optional[str] = None) -> None:
        settings = get_settings()
        self.client = client or get_openai_client()
        self.model = model or settings.openai_model_chat
        self.chat_api = settings.openai_chat_api
        self.openai_base_url = settings.openai_base_url or ""

    def _build_system_prompt(self, user_message: str) -> str:
        template = read_text_file("app/prompts/interview_prompt.txt")
        return template.replace("{{user_input}}", user_message).strip()

    def chat(self, user_message: str) -> str:
        prompt = self._build_system_prompt(user_message)

        has_chat_completions = (
            hasattr(self.client, "chat")
            and hasattr(self.client.chat, "completions")
            and hasattr(self.client.chat.completions, "create")
        )
        has_responses = hasattr(self.client, "responses") and hasattr(self.client.responses, "create")

        use_chat_completions = self.chat_api == "chat_completions" or (
            self.chat_api == "auto" and self.openai_base_url.strip()
        )

        if use_chat_completions and has_chat_completions:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            return response.choices[0].message.content or ""

        if not has_responses:
            raise AttributeError("OpenAI client does not support responses.create or chat.completions.create")

        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ],
        )

        if getattr(response, "output_text", None):
            return response.output_text

        return str(response)
