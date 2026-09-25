import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import type { ChatMessage } from '@/hooks/useDocumentChat'

interface ChatInterfaceProps {
  messages: ChatMessage[]
  isPending: boolean
  onSendMessage: (msg: string) => void
}

export function ChatInterface({ messages, isPending, onSendMessage }: ChatInterfaceProps) {
  const [inputMessage, setInputMessage] = useState('')
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (!inputMessage.trim() || isPending) return
    onSendMessage(inputMessage)
    setInputMessage('')
  }

  return (
    <>
      <div className="flex-1 overflow-auto p-4 space-y-4 bloomberg-scrollbar">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
              msg.role === 'assistant' ? 'bg-[#00e1b7]/10' : 'bg-[#3b6978]/20'
            }`}>
              {msg.role === 'assistant' ? (
                <Bot className="w-3.5 h-3.5 text-[#00e1b7]" />
              ) : (
                <User className="w-3.5 h-3.5 text-[#3b6978]" />
              )}
            </div>
            <div className={`max-w-[85%] ${
              msg.role === 'user'
                ? 'bg-[#3b6978]/20 text-[#d0e7f4] rounded-2xl rounded-tr-sm'
                : 'border-l-2 border-[#3b6978] text-[#d0e7f4] pl-3'
            }`}>
              <div className={`p-3 text-sm leading-relaxed ${
                msg.role === 'user' ? 'px-4' : 'prose prose-invert prose-sm max-w-none'
              }`}>
                {msg.role === 'user' ? (
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                ) : (
                  <ReactMarkdown
                    components={{
                      p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                      strong: ({node, ...props}) => <strong className="font-bold text-[#00e1b7]" {...props} />,
                      ul: ({node, ...props}) => <ul className="list-disc pl-4 mb-2 space-y-1" {...props} />,
                      ol: ({node, ...props}) => <ol className="list-decimal pl-4 mb-2 space-y-1" {...props} />,
                      li: ({node, ...props}) => <li className="text-[#d0e7f4]" {...props} />,
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                )}
              </div>

              {/* Source citations */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-[#1b1f2a]">
                  <p className="text-xs text-[#64748b] mb-1.5">Sources:</p>
                  {msg.sources.map((source, si) => (
                    <div key={si} className="flex items-center gap-2 text-xs mb-1">
                      <span className="text-[#00e1b7]">p.{source.page}</span>
                      <span className="text-[#64748b] truncate">{source.text_preview}</span>
                      <span className="text-[#3b6978] shrink-0">{Math.round(source.relevance_score * 100)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isPending && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-[#00e1b7]/10 flex items-center justify-center shrink-0">
              <Bot className="w-3.5 h-3.5 text-[#00e1b7]" />
            </div>
            <div className="border-l-2 border-[#3b6978] pl-3 py-2">
              <Loader2 className="w-4 h-4 text-[#00e1b7] animate-spin" />
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      <div className="p-4 border-t border-[#1b1f2a]">
        <div className="flex items-end gap-2">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            placeholder="Ask about the document..."
            rows={2}
            className="flex-1 bg-[#161d2e] border border-[#1b1f2a] rounded-lg p-3 text-sm text-[#d0e7f4] placeholder:text-[#64748b] focus:border-[#00e1b7] focus:ring-1 focus:ring-[#00e1b7]/20 transition-all resize-none"
          />
          <button
            onClick={handleSend}
            disabled={!inputMessage.trim() || isPending}
            className="w-10 h-10 flex items-center justify-center rounded-lg bg-[#00e1b7] text-[#0b0f19] hover:bg-[#00e1b7]/90 disabled:opacity-30 disabled:hover:bg-[#00e1b7] transition-all"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-[#64748b] mt-2 text-center">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </>
  )
}
