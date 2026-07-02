import { useState } from 'react'
import { runAgent } from './service.jsx'
import './App.css'

function App() {
  const [prompt, setPrompt] = useState('')
  const [answer, setAnswer] = useState('')
  const [status, setStatus] = useState('Ready')
  const [isLoading, setIsLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()

    if (!prompt.trim()) {
      setStatus('Write a prompt first.')
      return
    }

    setIsLoading(true)
    setStatus('Waiting for backend...')
    setAnswer('')

    try {
      const result = await runAgent(prompt)
      setAnswer( result.final_answer || 'No answer returned.')
      setStatus(`Connected to backend. ${result.task_type ? `Task type: ${result.task_type}` : 'Review graph completed.'}`)
    } catch (error) {
      setStatus(error.message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="app-shell">
      <section className="prompt-panel">
        <div className="header-block">
          <p className="eyebrow">FastAPI + LangGraph</p>
          <h1>Ask the Agent</h1>
        </div>

        <form className="prompt-form" onSubmit={handleSubmit}>
          <label htmlFor="prompt">Prompt</label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Example: give me 3 random words"
            rows={5}
          />

          <div className="actions-row">
            <button type="submit" disabled={isLoading}>
              {isLoading ? 'Sending...' : 'Send'}
            </button>
            <span className="status-text">{status}</span>
          </div>
        </form>

        <section className="answer-panel" aria-live="polite">
          <h2>Backend Response</h2>
          <div className="answer-box">
            {answer || 'The model response will appear here.'}
          </div>
        </section>
      </section>
    </main>
  )
}

export default App
