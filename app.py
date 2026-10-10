"""Streamlit UI: streamlit run app.py"""
import html
import json

import pandas as pd
import streamlit as st

from hub import config
from hub.agent import Agent
from hub.config import DRAFTS_FILE, TASKS_FILE
from hub.tools import send_draft


st.set_page_config(page_title="Smart Mail Summarizer", page_icon="🤖", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(ellipse at 10% 0%, rgba(98, 80, 220, .14), transparent 38%),
            linear-gradient(145deg, #f7f8fc 0%, #eef2fb 55%, #f8f9fc 100%);
        color: #20243a;
    }
    .block-container { max-width: 1120px; padding-top: 2.2rem; padding-bottom: 3rem; }
    h1, h2, h3 { color: #22243a; letter-spacing: -.025em; }
    div[data-testid="stTextArea"] label,
    div[data-testid="stTextArea"] label p {
        color: #454b62 !important;
    }
    div[data-testid="stTextArea"] textarea {
        color: #20243a !important;
        background: rgba(255,255,255,.96) !important;
    }
    div[data-testid="stTextArea"] textarea::placeholder {
        color: #858ba0 !important;
        opacity: 1;
    }
    .hero {
        padding: 1.5rem 1.7rem;
        margin: .2rem 0 1.3rem;
        border: 1px solid rgba(105, 91, 210, .16);
        border-radius: 22px;
        background: linear-gradient(115deg, rgba(255,255,255,.96), rgba(244,242,255,.92));
        box-shadow: 0 12px 38px rgba(40, 39, 82, .08);
    }
    .hero h1 { margin: 0; font-size: clamp(1.8rem, 4vw, 2.45rem); }
    .hero p { margin: .45rem 0 0; color: #626981; font-size: 1rem; }
    div[data-testid="stTextArea"] textarea {
        border: 1px solid #d9ddef;
        border-radius: 14px;
        background: rgba(255,255,255,.88);
    }
    div[data-testid="stButton"] > button {
        min-height: 2.7rem;
        border-radius: 12px !important;
        border: 1px solid #dedff0 !important;
        color: #39345f !important;
        background: #fff !important;
        transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
    }
    div[data-testid="stButton"] > button:hover {
        transform: translateY(-1px);
        border-color: #8e82e8;
        box-shadow: 0 7px 18px rgba(68, 57, 150, .12);
    }
    div[data-testid="stButton"] > button[kind="primary"] {
        border: 0 !important;
        color: #fff !important;
        background: linear-gradient(105deg, #6254d9, #8373ec) !important;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #e1e4f0;
        border-radius: 14px;
        background: rgba(255,255,255,.8);
    }
    .draft-card {
        margin: .35rem 0 .8rem;
        padding: 1rem 1.1rem;
        border: 1px solid #dfe3f0;
        border-radius: 15px;
        background: rgba(255,255,255,.94);
        box-shadow: 0 5px 16px rgba(40,39,82,.045);
    }
    .draft-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        color: #282b43;
        font-size: 1rem;
        font-weight: 650;
    }
    .draft-status {
        flex: 0 0 auto;
        padding: .2rem .6rem;
        border-radius: 999px;
        background: #fff3d9;
        color: #80540a;
        font-size: .76rem;
        font-weight: 650;
        text-transform: uppercase;
    }
    .draft-status.sent { background: #e3f6eb; color: #24643d; }
    .draft-recipient { margin-top: .55rem; color: #5d647c; font-size: .9rem; }
    .draft-body {
        margin-top: .8rem;
        padding: .8rem .9rem;
        border-radius: 10px;
        background: #f5f6fb;
        color: #30364c;
        line-height: 1.55;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #e1e4f0;
        border-radius: 14px;
        overflow: hidden;
    }
    .section-note { color: #686f86; margin-top: -.35rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>🤖 Smart Mail Summarizer</h1>
        <p>Give a command by voice or text. Your agent handles the work and can read its response aloud.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

agent = Agent()
sb = st.sidebar
sb.header("System status")
sb.write(f"**LLM:** {agent.llm.mode}")
sb.write(f"**Mailbox:** {config.EMAIL_ADDRESS if config.EMAIL_LIVE else 'sample inbox (demo)'}")
sb.write(f"**Agent may auto-send:** {'yes' if config.ALLOW_AGENT_SEND else 'no (drafts only)'}")
if sb.button("Clear tasks & drafts"):
    TASKS_FILE.unlink(missing_ok=True)
    DRAFTS_FILE.unlink(missing_ok=True)
    st.rerun()

st.subheader("What would you like me to do?")
st.markdown('<p class="section-note">Choose a suggestion or enter your own command.</p>',
            unsafe_allow_html=True)
examples = [
    "Summarize today's important emails and create a task list.",
    "Reply to my important emails politely.",
]
for col, example in zip(st.columns(len(examples)), examples):
    if col.button(example, use_container_width=True):
        st.session_state["req"] = example

if "agent_answer" not in st.session_state:
    st.session_state["agent_answer"] = ""
if "response_id" not in st.session_state:
    st.session_state["response_id"] = 0
if "speak_responses" not in st.session_state:
    st.session_state["speak_responses"] = True

st.checkbox("Read responses aloud automatically", key="speak_responses")
request = st.text_area("Command", key="req", height=100,
                       placeholder="For example: summarize my important emails...")
run_command = st.button("Run command", type="primary", disabled=not request.strip())

def _use_voice_transcript():
    component_state = st.session_state.get("voice_command")
    submission = component_state.get("submission") if component_state else None
    transcript = submission.get("transcript", "") if submission else ""
    command_id = submission.get("id") if submission else None
    if transcript and command_id != st.session_state.get("last_voice_command_id"):
        st.session_state["req"] = transcript
        st.session_state["voice_command_pending"] = True
        st.session_state["last_voice_command_id"] = command_id


voice_command_pending = st.session_state.pop("voice_command_pending", False)
if run_command or voice_command_pending:
    command = st.session_state["req"].strip()
    if command:
        with st.spinner("Your agent is working..."):
            result = agent.run(command)
        st.session_state["agent_answer"] = result.answer
        st.session_state["response_id"] += 1
        st.session_state["agent_steps"] = result.steps


voice_component = st.components.v2.component(
    "smart_hub_voice",
    html="""
    <div class="voice-panel">
      <div class="voice-actions">
        <button id="listen" type="button">🎙️ Start voice command</button>
        <button id="speak" type="button">🔊 Read response</button>
      </div>
      <p id="voice-status" role="status">Press Space to stop reading, or hold it for half a second to listen. Say “over” to run your command.</p>
    </div>
    """,
    css="""
    .voice-panel { font: 14px/1.45 system-ui, sans-serif; color: #555d76; }
    .voice-actions { display: flex; flex-wrap: wrap; gap: 10px; }
    button {
      padding: 10px 15px; border: 1px solid #dedff0; border-radius: 12px;
      background: #fff; color: #39345f; font: 600 14px system-ui, sans-serif;
      cursor: pointer;
    }
    button:hover { border-color: #8e82e8; background: #f8f7ff; }
    #voice-status { margin: 8px 0 0; color: #6b7187; }
    """,
    js=r"""
    let lastSpokenId = null;
    let activeRecognition = null;
    let activeUtterance = null;
    let spaceHoldTimer = null;
    let spaceHoldStarted = false;
    let keyboardHandlers = null;

    export default function(component) {
      const { parentElement, data, setStateValue } = component;
      const listen = parentElement.querySelector("#listen");
      const speak = parentElement.querySelector("#speak");
      const status = parentElement.querySelector("#voice-status");
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

      const startListening = () => {
        if (!SpeechRecognition) {
          status.textContent = "Voice input is not supported in this browser. Try Chrome or Edge.";
          return;
        }
        if (activeRecognition) {
          status.textContent = "Already listening. Finish your command by saying “over”.";
          return;
        }

        const recognition = new SpeechRecognition();
        let commandSubmitted = false;
        activeRecognition = recognition;
        listen.textContent = "🎙️ Listening...";
        recognition.lang = "en-US";
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;
        status.textContent = "Listening... Say your command, then say “over” to run it.";
        recognition.onresult = (event) => {
          const results = Array.from(event.results);
          const transcript = results
            .map((result) => result[0].transcript.trim())
            .filter(Boolean)
            .join(" ")
            .trim();
          const lastResult = results[results.length - 1];
          if (lastResult?.isFinal && /\bover[.!?,;:]*\s*$/i.test(transcript)) {
            const command = transcript.replace(/\bover[.!?,;:]*\s*$/i, "").trim();
            if (!command) {
              status.textContent = "I heard “over” but no command. Start again and say a command first.";
              return;
            }
            commandSubmitted = true;
            setStateValue("submission", {transcript: command, id: Date.now()});
            status.textContent = "Command received. Running it now...";
            recognition.stop();
          } else if (transcript) {
            status.textContent = `Heard: ${transcript} — say “over” when finished.`;
          }
        };
        recognition.onerror = (event) => {
          status.textContent = event.error === "not-allowed"
            ? "Microphone permission was denied. Allow microphone access and try again."
            : `Voice input error: ${event.error}`;
        };
        recognition.onend = () => {
          if (activeRecognition === recognition) activeRecognition = null;
          listen.textContent = "🎙️ Start voice command";
          if (!commandSubmitted) {
            status.textContent = "Listening stopped. Start again and end your command with “over”.";
          }
        };
        try {
          recognition.start();
        } catch (error) {
          activeRecognition = null;
          listen.textContent = "🎙️ Start voice command";
          status.textContent = `Could not start voice input: ${error.message}`;
        }
      };

      const stopSpeaking = () => {
        if (!activeUtterance || !("speechSynthesis" in window)) return;
        activeUtterance = null;
        window.speechSynthesis.cancel();
        status.textContent = "Response reading stopped.";
      };

      if (!SpeechRecognition) {
        listen.disabled = true;
        status.textContent = "Voice input is not supported in this browser. Try Chrome or Edge.";
      } else {
        listen.disabled = false;
        listen.onclick = () => {
          if (activeRecognition) {
            activeRecognition.stop();
            return;
          }
          startListening();
        };
      }

      if (keyboardHandlers) {
        window.removeEventListener("keydown", keyboardHandlers.keydown);
        window.removeEventListener("keyup", keyboardHandlers.keyup);
        window.removeEventListener("blur", keyboardHandlers.blur);
      }
      const isTextEntry = (target) =>
        target instanceof HTMLElement &&
        (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
      const clearSpaceTimer = () => {
        if (spaceHoldTimer !== null) {
          window.clearTimeout(spaceHoldTimer);
          spaceHoldTimer = null;
        };
      };
      keyboardHandlers = {
        keydown: (event) => {
          if (event.code !== "Space" || event.repeat || isTextEntry(event.target)) return;
          event.preventDefault();
          stopSpeaking();
          if (SpeechRecognition) {
            spaceHoldTimer = window.setTimeout(() => {
              spaceHoldTimer = null;
              spaceHoldStarted = true;
              startListening();
            }, 500);
          }
        },
        keyup: (event) => {
          if (event.code !== "Space") return;
          clearSpaceTimer();
          if (spaceHoldStarted) {
            spaceHoldStarted = false;
            event.preventDefault();
          }
        },
        blur: () => {
          clearSpaceTimer();
          spaceHoldStarted = false;
        },
      };
      window.addEventListener("keydown", keyboardHandlers.keydown);
      window.addEventListener("keyup", keyboardHandlers.keyup);
      window.addEventListener("blur", keyboardHandlers.blur);

      const speakResponse = () => {
        if (!data.speak_text) {
          status.textContent = "Run a command first; its response will be read here.";
          return;
        }
        if (!("speechSynthesis" in window)) {
          status.textContent = "Speech playback is not supported in this browser.";
          return;
        }
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(data.speak_text);
        activeUtterance = utterance;
        utterance.onstart = () => {
          if (activeUtterance === utterance) status.textContent = "Reading the response aloud...";
        };
        utterance.onend = () => {
          if (activeUtterance !== utterance) return;
          activeUtterance = null;
          status.textContent = "Finished reading the response.";
        };
        utterance.onerror = () => {
          if (activeUtterance !== utterance) return;
          activeUtterance = null;
          status.textContent = "Could not play speech. Try the Read response button again.";
        };
        window.speechSynthesis.speak(utterance);
      };
      speak.onclick = speakResponse;

      if (data.auto_speak && data.speak_text && data.speak_id !== lastSpokenId) {
        lastSpokenId = data.speak_id;
        speakResponse();
      }
    }
    """,
)

voice_component(
    key="voice_command",
    data={
        "speak_text": st.session_state["agent_answer"],
        "speak_id": st.session_state["response_id"],
        "auto_speak": st.session_state["speak_responses"],
    },
    default={"submission": {"transcript": "", "id": 0}},
    on_submission_change=_use_voice_transcript,
    height=90,
)
st.caption(
    "Press Space to stop a response being read aloud. Hold Space for half a second to listen. "
    "Say “over” at the end to run your command. Voice recognition requires browser microphone "
    "permission and HTTPS (or localhost)."
)

if st.session_state["agent_answer"]:
    st.subheader("Response")
    st.markdown(st.session_state["agent_answer"])
    steps = st.session_state.get("agent_steps", [])
    with st.expander(f"Agent trace ({len(steps)} tool calls)", expanded=False):
        for index, step in enumerate(steps, 1):
            st.markdown(f"**Step {index}: `{step.tool}`**")
            st.json({"input": step.args, "result": step.result}, expanded=False)

if DRAFTS_FILE.exists():
    st.subheader("Email drafts")
    st.markdown('<p class="section-note">Review a draft before sending.</p>',
                unsafe_allow_html=True)
    for draft in json.loads(DRAFTS_FILE.read_text()):
        status = str(draft["status"])
        status_class = "sent" if status == "sent" else ""
        st.markdown(
            f"""
            <div class="draft-card">
              <div class="draft-card-header">
                <span>Draft #{html.escape(str(draft['id']))} · {html.escape(draft['subject'])}</span>
                <span class="draft-status {status_class}">{html.escape(status)}</span>
              </div>
              <div class="draft-recipient">To: {html.escape(draft['to'])}</div>
              <div class="draft-body">{html.escape(draft['body'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if status == "draft" and st.button("Send this email", key=f"send{draft['id']}"):
            result = send_draft(draft["id"])
            st.success(f"Sent to {result['to']}") if "to" in result else st.error(result)

if TASKS_FILE.exists():
    st.subheader("Task manager")
    st.dataframe(pd.DataFrame(json.loads(TASKS_FILE.read_text())), use_container_width=True)
