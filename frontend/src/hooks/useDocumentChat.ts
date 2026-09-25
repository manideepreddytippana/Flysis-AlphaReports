import { useState, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/api/client'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{ page: number; text_preview: string; relevance_score: number }>
}

export function useDocumentChat(doc: any) {
  const [messages, setMessages] = useState<ChatMessage[]>([])

  useEffect(() => {
    if (doc && messages.length === 0) {
      setMessages([{
        role: 'assistant',
        content: `I've analyzed "${doc.original_name}". Ask me anything about the content, data, or insights.`,
      }])
    }
  }, [doc])

  const chatMutation = useMutation({
    mutationFn: (newMessages: any[]) => api.llm.chat(doc?.python_doc_id, newMessages, true),
    onSuccess: (data) => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        sources: data.sources?.map((s: any) => ({
          page: s.page || 1,
          text_preview: s.text_preview || s.text || '',
          relevance_score: s.relevance_score || s.score || 0
        }))
      }])
    },
    onError: (error) => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${error.message}`
      }])
    }
  })

  const sendMessage = (inputMessage: string) => {
    const userMsg: ChatMessage = { role: 'user', content: inputMessage }
    const updatedMessages = [...messages, userMsg]
    setMessages(updatedMessages)
    
    const apiMessages = updatedMessages.map(m => ({
      role: m.role,
      content: m.content
    }))
    
    chatMutation.mutate(apiMessages)
  }

  return {
    messages,
    sendMessage,
    isPending: chatMutation.isPending
  }
}
