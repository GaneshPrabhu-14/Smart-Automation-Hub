# Smart Automation Hub (Experiment No. 11)

Aim: implement a Smart Automation Hub using Generative AI, AI Agents and Intelligent
Automation to perform tasks beyond simple chatbot interaction.

## System Architecture

```
                         ┌────────────────────────────┐
                         │  USER INTERFACE            │
                         │  Streamlit (app.py) / CLI  │
                         └──────────────┬─────────────┘
                                        │ natural-language request
                                        ▼
┌───────────────────────────────────────────────────────────────────┐
│                       AI AGENT  (hub/agent.py)                    │
│   1. Understand task  2. Plan  3. Choose tool  4. Act  5. Observe │
│                    (loop until task is complete)                  │
└───────┬───────────────────────────────────────────────┬───────────┘
        │ reason / generate                             │ tool calls (JSON)
        ▼                                               ▼
┌──────────────────────┐                  ┌───────────────────────────────┐
│ GENAI LAYER          │                  │ AUTOMATION LAYER (hub/tools)  │
│ hub/llm.py           │                  │  Tool registry + JSON schemas │
│ Groq / Grok API      │                  ├───────────────────────────────┤
│ summarize, decide,   │                  │ read_emails   draft_email     │
│ write reports        │                  │ create_tasks  list_tasks      │
│ (offline fallback)   │                  │ analyze_data  generate_report │
└──────────────────────┘                  └──────────────┬────────────────┘
                                                         ▼
                                          ┌───────────────────────────────┐
                                          │ DATA / SERVICES               │
                                          │ Gmail IMAP/SMTP · sales.csv       │
                                          │ tasks.json · reports · outbox │
                                          └───────────────────────────────┘
                                                         │
                                                         ▼
                                        Final output + agent trace to user
```

## Workflow (example)
"Summarize today's important emails and create a task list"
read_emails -> LLM filters/summarizes -> extracts action items -> create_tasks -> result.

## Run
```
pip install -r requirements.txt
python main.py                                   # offline demo, no key needed
streamlit run app.py                             # web UI (take screenshot here)
python -m pytest -q                              # tests
```
In the Streamlit app, enter a command by text or use **Start voice command**.
Voice input uses the browser's Web Speech API (typically Chrome or Edge) and may
require microphone permission and HTTPS, except on localhost. Responses are read
aloud automatically by default; turn that off or use **Read response** to play
one again. Press **Space** to stop speech playback. To use hands-free submission,
focus the voice controls and hold **Space** for half a second to start listening,
then say the command followed by **“over”**.
The agent removes the final word and runs the command automatically. Browser
speech recognition may send audio to the browser's recognition service.

For live GenAI mode, set `GROQ_API_KEY` in `.env` (or use the existing
`XAI_API_KEY`/`LLM_API_KEY` aliases) and configure `LLM_BASE_URL` and `LLM_MODEL`.
Email context defaults to 5 messages with 400 characters per body; tool results sent
back to the model are capped at 3,500 characters. A rate-limit response is retried
once after 30 seconds.

To adjust the email context in `.env`, use separate lines:
```
DEFAULT_EMAILS=5
EMAIL_BODY_CHARS=400
```
The agent never reads more than 10 emails per request.

## Extending
Add a function in `hub/tools.py` with `@register(name, description, schema)`.
The agent discovers it automatically. Replace `emails.json` with Gmail/IMAP,
and `tasks.json` with Todoist/Trello/Jira APIs for real integrations.

## Real integrations (v2)
- **Groq:** set `GROQ_API_KEY`, `LLM_BASE_URL=https://api.groq.com/openai/v1`, and
  `LLM_MODEL` in `.env`. The OpenAI-compatible client also supports xAI via `XAI_API_KEY`.
- **Email:** set `EMAIL_ADDRESS` + Gmail *App Password*. Reading uses IMAP (read-only, mails
  are not marked as read); sending uses SMTP.
- **Replies:** ask "Reply to my important emails". The agent writes drafts; you approve each
  one with the *Send this email* button. Auto-send needs `ALLOW_AGENT_SEND=true` AND the word
  "send" in your request.
- **Security:** never commit `.env`. Email bodies are treated as untrusted (prompt-injection guard).
