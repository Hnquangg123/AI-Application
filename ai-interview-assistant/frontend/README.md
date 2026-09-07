# MockMate Frontend

Interactive React UI for the AI Interview Assistant. It creates and resumes persisted interview sessions through the FastAPI backend, sends answers, skips questions, ends sessions, and renders AI-generated feedback.

## Stack

- React 19 and TypeScript
- vinext / Vite
- Tailwind CSS 4 with a custom claymorphism token layer
- Cloudflare Worker-compatible build output

## Run locally

Start the backend first, then run:

```powershell
npm install
npm run dev
```

The API defaults to `http://localhost:8000/api`. Copy `.env.example` to
`.env.local` to override `NEXT_PUBLIC_API_BASE_URL`.

An active session ID is kept in browser local storage so a page refresh can restore the persisted interview.

## Validate

```powershell
npm run lint
npm test
```
