# Interview Assistant (Entry Step) — API Test Cases

## Endpoint
`POST http://localhost:8000/api/chat`

## Request Format
```json
{ "message": "<your question>" }
```

---

## Test Cases

| TC | Category | Type | Input Message | Expected Result |
|---|---|---|---|---|
| TC1 | Valid | Technical | `What is the difference between a process and a thread?` | Structured answer: concept explanation → example → pitfalls → Key Takeaway |
| TC2 | Valid | Behavioral | `Tell me about a time you had to deal with a difficult team member.` | STAR framework suggestion + sample answer + follow-up variations |
| TC3 | Valid | System Design | `How would you design a URL shortening service like bit.ly?` | Assumptions → high-level architecture → components → trade-offs → Key Takeaway |
| TC4 | Valid | Coding | `How do you find the longest substring without repeating characters?` | Approach explanation → code solution → time/space complexity → Key Takeaway |
| TC5 | Invalid | Off-topic | `Write me a poem about the ocean.` | Redirection message only, no answer attempted |
| TC6 | Invalid | Small talk | `What did you have for lunch?` | Redirection message only, no answer attempted |

---

## Expected Redirection Message (TC5, TC6)
> I'm your Interview Assistant and can only help with interview-related questions or topics. Please ask me something related to interview preparation — for example, a technical question, a behavioral scenario, or a concept you'd like explained.

---

## curl Commands

### TC1 — Technical
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What is the difference between a process and a thread?\"}"
```

### TC2 — Behavioral
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Tell me about a time you had to deal with a difficult team member.\"}"
```

### TC3 — System Design
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"How would you design a URL shortening service like bit.ly?\"}"
```

### TC4 — Coding
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"How do you find the longest substring without repeating characters?\"}"
```

### TC5 — Off-topic (Invalid)
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Write me a poem about the ocean.\"}"
```

### TC6 — Small talk (Invalid)
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What did you have for lunch?\"}"
```
