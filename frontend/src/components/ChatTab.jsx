import { useEffect, useMemo, useRef, useState } from 'react'
import { askChat } from '../api.js'

const QUICK_PROMPTS = [
  '📊 Summarize my lab results',
  '⚠️ What are my abnormal values?',
  '🥗 What should I eat for breakfast?',
  '🚫 What foods should I avoid?',
  '💊 How does my diet relate to my conditions?',
]

const SOURCE_LABELS = {
  structured_json: 'Lab Data',
  ocr_text: 'Report Text',
  diet_plan: 'Diet Plan',
  patient_profile: 'Patient Profile',
  session_aggregate: 'Session Summary',
  safety_json: 'Safety Checks',
  diet_meta: 'Diet Metadata',
}

function normalizeHistory(messages) {
  return messages
    .filter((m) => m.role === 'user' || m.role === 'assistant')
    .map((m) => ({ role: m.role, content: m.content }))
}

function stripPromptEmoji(text) {
  return text.replace(/^[^ ]+\s+/, '')
}

function formatSourceLabel(chunk) {
  const dataType = String(chunk?.data_type || '').toLowerCase()
  const source = String(chunk?.source || '').trim()
  if (source && source !== 'sqlite.sessions' && source !== 'sqlite.documents') {
    return source
  }
  return SOURCE_LABELS[dataType] || 'Medical Context'
}

function summarizeSources(chunks) {
  const seen = new Set()
  const labels = []

  for (const chunk of chunks || []) {
    const label = formatSourceLabel(chunk)
    const key = label.toLowerCase()
    if (!seen.has(key)) {
      seen.add(key)
      labels.push(label)
    }
  }

  return labels.slice(0, 4).join(', ')
}

export default function ChatTab({ sessionId }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "👋 Hi! I'm your health assistant. I've reviewed your reports and diet plan. Ask me anything about your lab results and recommendations.",
      context_chunks: [],
      response_time: 0,
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const threadRef = useRef(null)

  const canChat = Boolean(sessionId)
  const history = useMemo(() => normalizeHistory(messages), [messages])

  useEffect(() => {
    if (!threadRef.current) return
    threadRef.current.scrollTop = threadRef.current.scrollHeight
  }, [messages, loading])

  async function sendMessage(messageText) {
    const text = messageText.trim()
    if (!text || loading) return
    if (!canChat) return

    const nextMessages = [...messages, { role: 'user', content: text }]
    setMessages(nextMessages)
    setInput('')
    setLoading(true)

    try {
      const res = await askChat(sessionId, text, history)
      setMessages((prev) => [...prev, { 
        role: 'assistant', 
        content: res.response || 'No response.',
        context_chunks: res.context_chunks || [],
        response_time: res.response_time_seconds || 0,
      }])
    } catch (err) {
      setMessages((prev) => [...prev, { 
        role: 'assistant', 
        content: `Sorry, chat failed: ${err.message}`,
        context_chunks: [],
        response_time: 0,
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-shell">
      <section className="chat-header-card">
        <h2 className="chat-title">
          <span className="chat-title-icon" aria-hidden="true">💬</span>
          AI Chat Assistant
        </h2>

        {!canChat && (
          <div className="error-box">Please analyze at least one report first to start chat.</div>
        )}
      </section>

      <section className="chat-panel">
        <div className="chat-thread" ref={threadRef}>
          {messages.map((m, idx) => (
            <article key={idx} className={`chat-row ${m.role}`}>
              <div className={`chat-avatar ${m.role}`} aria-hidden="true">
                {m.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className="chat-message-wrapper">
                <div className="chat-message-card">
                  <p className="chat-message-text">{m.content}</p>
                </div>
                {m.role === 'assistant' && m.context_chunks && m.context_chunks.length > 0 && (
                  <p className="chat-source-footer">
                    📎 Sources: {summarizeSources(m.context_chunks)} · {m.response_time?.toFixed(1)}s
                  </p>
                )}
              </div>
            </article>
          ))}
          {loading && (
            <article className="chat-row assistant">
              <div className="chat-avatar assistant" aria-hidden="true">🤖</div>
              <div className="chat-message-wrapper">
                <div className="chat-message-card">
                  <p className="chat-message-text">Thinking...</p>
                </div>
              </div>
            </article>
          )}
        </div>

        <div className="chat-composer">
          <input
            className="chat-composer-input"
            type="text"
            placeholder="Ask about your reports, lab values, or diet plan..."
            value={input}
            disabled={!canChat || loading}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') sendMessage(input)
            }}
          />
          <button
            className="chat-composer-send"
            disabled={!canChat || loading || !input.trim()}
            onClick={() => sendMessage(input)}
          >
            Send
          </button>
        </div>

        <div className="chat-chip-row">
          {QUICK_PROMPTS.map((q) => (
            <button
              key={q}
              className="chat-chip"
              disabled={!canChat || loading}
              onClick={() => sendMessage(stripPromptEmoji(q))}
            >
              {q}
            </button>
          ))}
        </div>
      </section>
    </div>
  )
}
