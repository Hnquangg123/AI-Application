"""Minimal mock of the OpenAI API to structurally test patient_chatbot.py offline."""
import json
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def _send(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(length) or b"{}")
        if self.path.endswith("/embeddings"):
            inputs = req.get("input")
            if isinstance(inputs, str):
                inputs = [inputs]
            rng = random.Random(42)
            data = [
                {"object": "embedding", "index": i,
                 "embedding": [rng.uniform(-1, 1) for _ in range(16)]}
                for i, _ in enumerate(inputs)
            ]
            self._send({"object": "list", "data": data, "model": req.get("model"),
                        "usage": {"prompt_tokens": 1, "total_tokens": 1}})
            return
        if self.path.endswith("/chat/completions"):
            msgs = req.get("messages", [])
            has_tool_result = any(m.get("role") == "tool" for m in msgs)
            user_text = " ".join(m.get("content") or "" for m in msgs if m.get("role") == "user").lower()
            if has_tool_result:
                msg = {"role": "assistant",
                       "content": "MOCK FINAL ADVICE: rest, hydrate, warm fluids. See a doctor if fever exceeds 38.5C. (not a diagnosis)"}
                finish = "stop"
            elif "sore throat" in user_text or "tired" in user_text:
                msg = {"role": "assistant", "content": None,
                       "tool_calls": [{"id": "call_1", "type": "function",
                                       "function": {"name": "retrieve_advice",
                                                    "arguments": json.dumps({"user_input": "fatigue and sore throat"})}}]}
                finish = "tool_calls"
            else:
                msg = {"role": "assistant", "content": "MOCK: Could you tell me your name, age, and symptoms?"}
                finish = "stop"
            self._send({"id": "chatcmpl-mock", "object": "chat.completion", "created": 0,
                        "model": req.get("model"),
                        "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
                        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})
            return
        self._send({"error": "unknown path " + self.path})

if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8931), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    import os, subprocess, sys
    env = dict(os.environ, OPENAI_BASE_URL="http://127.0.0.1:8931/v1")
    r = subprocess.run([sys.executable, "-W", "ignore::DeprecationWarning", "patient_chatbot.py"], env=env)
    sys.exit(r.returncode)
