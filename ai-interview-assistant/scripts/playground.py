from pathlib import Path
import sys

# Ensure imports work when running this file directly via: python scripts/playground.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.chat_service import ChatService


if __name__ == "__main__":
    chat_service = ChatService()

    message = "Explain Python virtual environments in one paragraph."
    reply = chat_service.chat(message)
    print("Chat reply:\n", reply)
