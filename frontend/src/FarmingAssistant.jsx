import { useEffect, useRef, useState } from "react";
import {
  AudioLines, CircleAlert, CircleStop, Clock3, Leaf, LoaderCircle, Mic, Plus, RefreshCw,
  Send, Sprout, Trash2
} from "lucide-react";
import { apiRequest } from "./api";
import "./FarmingAssistant.css";

const starterQuestions = [
  "How can I improve soil health before planting?",
  "What should I check when tomato leaves turn yellow?",
  "Help me plan irrigation during a dry week.",
  "How do I identify common chilli pests?",
];

const speechLanguages = [
  ["kn-IN", "ಕನ್ನಡ"],
  ["en-IN", "English (India)"],
  ["hi-IN", "हिन्दी"],
  ["te-IN", "తెలుగు"],
  ["ta-IN", "தமிழ்"],
  ["kn-IN-mixed", "ಕನ್ನಡ + English"],
];

export default function FarmingAssistant({ t }) {
  const [conversations, setConversations] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [micStatus, setMicStatus] = useState("ready");
  const [micError, setMicError] = useState("");
  const [speechLanguage, setSpeechLanguage] = useState("kn-IN");
  const [provider, setProvider] = useState("local");
  const [language, setLanguage] = useState("Auto-detected");
  const [error, setError] = useState("");
  const [failedMessage, setFailedMessage] = useState(null);
  const recognitionRef = useRef(null);
  const originalDraftRef = useRef("");
  const transcriptRef = useRef("");
  const stopRequestedRef = useRef(false);
  const recognitionErrorRef = useRef("");
  const messagesEndRef = useRef(null);

  useEffect(() => {
    let mounted = true;
    apiRequest("/ai/conversations")
      .then((data) => {
        if (mounted) setConversations(data.conversations || []);
      })
      .catch((err) => {
        if (mounted) setError(err.message);
      });
    return () => {
      mounted = false;
      const recognition = recognitionRef.current;
      recognitionRef.current = null;
      if (recognition) {
        recognition.onresult = null;
        recognition.onerror = null;
        recognition.onend = null;
        recognition.onnomatch = null;
        recognition.abort();
      }
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  async function refreshConversations() {
    const data = await apiRequest("/ai/conversations");
    setConversations(data.conversations || []);
  }

  function startConversation() {
    setConversationId(null);
    setMessages([]);
    setDraft("");
    setError("");
  }

  async function openConversation(id) {
    try {
      setError("");
      const data = await apiRequest(`/ai/conversations/${id}`);
      setConversationId(data.conversation.id);
      setMessages(data.conversation.messages || []);
      setLanguage(data.conversation.language || "Auto-detected");
    } catch (err) {
      setError(err.message);
    }
  }

  async function removeConversation(event, id) {
    event.stopPropagation();
    try {
      await apiRequest(`/ai/conversations/${id}`, { method: "DELETE" });
      if (conversationId === id) startConversation();
      await refreshConversations();
    } catch (err) {
      setError(err.message);
    }
  }

  async function sendMessage(value = draft) {
    const message = value.trim();
    if (!message || busy || micStatus === "listening" || micStatus === "processing") return;
    setDraft("");
    setError("");
    setFailedMessage(null);
    setBusy(true);
    try {
      const result = await apiRequest("/ai/farming-assistant", {
        method: "POST",
        body: JSON.stringify({ message, ...(conversationId ? { conversationId } : {}) }),
      });
      setConversationId(result.conversation.id);
      setProvider(result.provider || "local");
      setLanguage(result.language || "Auto-detected");
      setMessages((current) => [
        ...current,
        { id: `user-${Date.now()}`, role: "user", content: message },
        { id: `assistant-${Date.now()}`, role: "assistant", content: result.answer },
      ]);
      try {
        await refreshConversations();
      } catch (refreshError) {
        setError(`Reply received, but chat history could not refresh: ${refreshError.message}`);
      }
    } catch (err) {
      setDraft(message);
      setError(err.message);
      setFailedMessage(message);
    } finally {
      setBusy(false);
    }
  }

  function stopVoiceInput() {
    const recognition = recognitionRef.current;
    if (!recognition || micStatus !== "listening") return;
    stopRequestedRef.current = true;
    setMicStatus("processing");
    try {
      recognition.stop();
    } catch {
      recognitionRef.current = null;
      setMicStatus(transcriptRef.current ? "ready" : "error");
      setMicError(transcriptRef.current ? "" : "Recording stopped before any speech was recognized.");
    }
  }

  function toggleVoiceInput() {
    if (micStatus === "listening") {
      stopVoiceInput();
      return;
    }
    if (micStatus === "processing" || recognitionRef.current || busy) return;

    if (!window.isSecureContext) {
      setMicError("Microphone access requires HTTPS or localhost.");
      setMicStatus("error");
      return;
    }

    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setMicError("Speech recognition is not supported in this browser. You can still type your question.");
      setMicStatus("error");
      return;
    }

    let recognition;
    try {
      recognition = new Recognition();
    } catch {
      setMicError("Could not start speech recognition. Check microphone access and try again.");
      setMicStatus("error");
      return;
    }

    originalDraftRef.current = draft;
    transcriptRef.current = "";
    stopRequestedRef.current = false;
    recognitionErrorRef.current = "";
    setMicError("");
    setMicStatus("processing");
    recognition.lang = speechLanguage === "kn-IN-mixed" ? "kn-IN" : speechLanguage;
    recognition.interimResults = true;
    recognition.continuous = true;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => {
      if (recognitionRef.current === recognition) setMicStatus("listening");
    };
    recognition.onresult = (event) => {
      if (recognitionRef.current !== recognition) return;
      const transcript = Array.from(event.results, (result) => result[0]?.transcript || "")
        .join(" ")
        .replace(/\s+/g, " ")
        .trim();
      if (!transcript) return;

      transcriptRef.current = transcript;
      const originalDraft = originalDraftRef.current;
      const separator = originalDraft && !/\s$/.test(originalDraft) ? " " : "";
      setDraft(`${originalDraft}${separator}${transcript}`);
    };
    recognition.onnomatch = () => {
      recognitionErrorRef.current = "Speech was not recognized. Try speaking a little more clearly.";
      setMicError(recognitionErrorRef.current);
      setMicStatus("error");
    };
    recognition.onerror = (event) => {
      if (event.error === "aborted" && stopRequestedRef.current) return;
      const errors = {
        "not-allowed": "Microphone permission was denied. Allow microphone access in your browser settings.",
        "service-not-allowed": "The browser blocked speech recognition. Check microphone and site permissions.",
        "no-speech": "No speech detected. Try again and speak near your microphone.",
        "audio-capture": "No microphone was detected. Connect or enable a microphone and try again.",
        network: "Speech recognition is unavailable over the network. Check your connection and retry.",
        aborted: "Recording was interrupted. Please try again.",
      };
      recognitionErrorRef.current = errors[event.error] || "Speech recognition stopped unexpectedly. Please try again.";
      setMicError(recognitionErrorRef.current);
      setMicStatus("error");
    };
    recognition.onend = () => {
      if (recognitionRef.current !== recognition) return;
      recognitionRef.current = null;
      if (recognitionErrorRef.current) {
        setMicStatus("error");
      } else if (!transcriptRef.current) {
        setMicError("No speech detected. Try again and speak near your microphone.");
        setMicStatus("error");
      } else {
        setMicStatus("ready");
      }
    };
    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch {
      recognitionRef.current = null;
      recognitionErrorRef.current = "Could not start speech recognition. Check microphone access and try again.";
      setMicError(recognitionErrorRef.current);
      setMicStatus("error");
    }
  }

  return (
    <section className="detail-view assistant-page">
      <header className="assistant-page-head">
        <div>
          <span className="eyebrow"><Leaf size={15} /> FarmBridge AI</span>
          <h1>{t.assistant}</h1>
          <p>Field-ready guidance for your next growing decision.</p>
        </div>
        <button className="assistant-new-chat" onClick={startConversation}>
          <Plus size={17} /> New chat
        </button>
      </header>

      <div className="assistant-workspace">
        <aside className="assistant-history">
          <div className="assistant-history-title"><Clock3 size={15} /> Recent chats</div>
          <div className="assistant-history-list">
            {conversations.map((conversation) => (
              <div
                className={`assistant-history-item ${conversationId === conversation.id ? "active" : ""}`}
                key={conversation.id}
              >
                <button className="assistant-history-open" onClick={() => openConversation(conversation.id)}>
                  <span>{conversation.title}</span>
                  <small>{new Date(conversation.updatedAt).toLocaleDateString()}</small>
                </button>
                <button
                  className="assistant-history-delete"
                  aria-label={`Delete ${conversation.title}`}
                  onClick={(event) => removeConversation(event, conversation.id)}
                ><Trash2 size={14} /></button>
              </div>
            ))}
            {!conversations.length && <p className="assistant-history-empty">Your conversations will appear here.</p>}
          </div>
          <div className="assistant-history-note"><Sprout size={16} /> Practical advice, rooted in your farm context.</div>
        </aside>

        <div className="assistant-chat-panel">
          <div className="assistant-chat-topline">
            <div className="assistant-online"><span /> Farm assistant</div>
            <div className="assistant-meta">
              <span><AudioLines size={14} /> {provider === "groq" ? "Groq AI" : "FarmBridge guidance"}</span>
              <span>{language}</span>
            </div>
          </div>

          <div className={`assistant-thread ${messages.length ? "has-messages" : ""}`}>
            {!messages.length ? (
              <div className="assistant-welcome">
                <div className="assistant-welcome-mark"><Sprout size={27} /></div>
                <span className="assistant-kicker">YOUR FARM, YOUR QUESTIONS</span>
                <h2>What are you growing through?</h2>
                <p>Ask in your own words. Your reply follows the language you use.</p>
                {busy && <div className="assistant-first-loading" role="status"><LoaderCircle size={16} /> Asking FarmBridge AI…</div>}
                <button
                  className={`assistant-voice-hero ${micStatus === "listening" ? "recording" : ""}`}
                  onClick={toggleVoiceInput}
                  aria-label={micStatus === "listening" ? "Stop voice input" : "Start voice input"}
                  disabled={micStatus === "processing" || busy}
                >
                  {micStatus === "listening" ? <CircleStop size={25} /> : micStatus === "processing" ? <LoaderCircle size={25} /> : micStatus === "error" ? <CircleAlert size={25} /> : <Mic size={25} />}
                  <span>{micStatus === "listening" ? "Listening" : micStatus === "processing" ? "Processing" : micStatus === "error" ? "Try voice input again" : "Ask with your voice"}</span>
                  <small>{micStatus === "listening" ? "Tap to stop and edit" : speechLanguages.find(([value]) => value === speechLanguage)?.[1]}</small>
                </button>
                <div className="assistant-starters">
                  {starterQuestions.map((question) => (
                    <button key={question} onClick={() => sendMessage(question)}>{question}</button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="assistant-messages">
                {messages.map((message) => (
                  <article className={`assistant-message ${message.role}`} key={message.id}>
                    {message.role === "assistant" && <span className="assistant-message-mark"><Sprout size={15} /></span>}
                    <div>
                      <small>{message.role === "assistant" ? "FARMBRIDGE AI" : "YOU"}</small>
                      <p>{message.content}</p>
                    </div>
                  </article>
                ))}
                {busy && <div className="assistant-thinking"><LoaderCircle size={17} /> Looking at your question…</div>}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {error && (
            <div className="assistant-error" role="alert">
              <span>{error}</span>
              {failedMessage && <button type="button" onClick={() => sendMessage(failedMessage)}><RefreshCw size={13} /> Retry</button>}
            </div>
          )}
          <div className="assistant-voice-controls">
            <label className="assistant-language-select">
              <span>Speaking language</span>
              <select
                value={speechLanguage}
                onChange={(event) => setSpeechLanguage(event.target.value)}
                disabled={micStatus === "listening" || micStatus === "processing"}
              >
                {speechLanguages.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <div className={`assistant-mic-state ${micStatus}`} role="status" aria-live="polite">
              {micStatus === "listening" ? <CircleStop size={15} /> : micStatus === "processing" ? <LoaderCircle size={15} /> : micStatus === "error" ? <CircleAlert size={15} /> : <Mic size={15} />}
              <span>{micStatus[0].toUpperCase() + micStatus.slice(1)}</span>
            </div>
          </div>
          {micStatus === "error" && micError && <div className="assistant-voice-error" role="alert">{micError}</div>}
          <form className="assistant-composer" onSubmit={(event) => { event.preventDefault(); sendMessage(); }}>
            <textarea
              value={draft}
              readOnly={micStatus === "listening" || micStatus === "processing"}
              onChange={(event) => {
                setDraft(event.target.value);
                if (micStatus === "error") {
                  setMicError("");
                  setMicStatus("ready");
                }
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  sendMessage();
                }
              }}
              placeholder={t.question}
              rows={1}
              aria-label="Your farming question"
            />
            <button type="button" className={`assistant-mic ${micStatus}`} onClick={toggleVoiceInput} aria-label={micStatus === "listening" ? "Stop voice input" : "Start voice input"} disabled={micStatus === "processing" || busy}>
              {micStatus === "listening" ? <CircleStop size={19} /> : micStatus === "processing" ? <LoaderCircle size={19} /> : micStatus === "error" ? <CircleAlert size={19} /> : <Mic size={19} />}
            </button>
            <button type="submit" className="assistant-send" disabled={!draft.trim() || busy || micStatus === "listening" || micStatus === "processing"} aria-label="Send message">
              {busy ? <LoaderCircle size={18} /> : <Send size={17} />}
            </button>
          </form>
          <p className="assistant-disclaimer">General guidance only. For urgent crop issues, consult a local agricultural expert.</p>
        </div>
      </div>
    </section>
  );
}