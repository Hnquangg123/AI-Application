"""Minimal mock of the OpenAI API to structurally test rag_chatbot.py offline."""
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
            data = []
            for i, text in enumerate(inputs):
                rng = random.Random(hash(str(text)) % (2**32))
                data.append({"object": "embedding", "index": i,
                             "embedding": [rng.uniform(-1, 1) for _ in range(16)]})
            self._send({"object": "list", "data": data, "model": req.get("model"),
                        "usage": {"prompt_tokens": 1, "total_tokens": 1}})
            return
        if self.path.endswith("/chat/completions"):
            user = " ".join(m.get("content") or "" for m in req.get("messages", []))
            snippet = user.replace("\n", " ")[:80]
            msg = {"role": "assistant",
                   "content": f"MOCK ANSWER grounded in retrieved context (prompt began: {snippet}...)"}
            self._send({"id": "chatcmpl-mock", "object": "chat.completion", "created": 0,
                        "model": req.get("model"),
                        "choices": [{"index": 0, "message": msg, "finish_reason": "stop"}],
                        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})
            return
        self._send({"error": "unknown path " + self.path})

if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8933), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    import os, subprocess, sys
    env = dict(os.environ, OPENAI_BASE_URL="http://127.0.0.1:8933/v1")
    r = subprocess.run([sys.executable, "rag_chatbot.py"], env=env)
    sys.exit(r.returncode)
