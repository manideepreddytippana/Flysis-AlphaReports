import { useState, useRef, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router'
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Send,
  Bot,
  User,
  Loader2,
  FileText,
  Sparkles,
  PanelRightOpen,
  PanelRightClose,
  Download,
  BookOpen,
  BarChart3,
  TrendingUp,
  Lightbulb,
  ChevronDown,
  ChevronUp,
  ListChecks,
  AlertTriangle
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()

import { useInView } from 'react-intersection-observer'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '@/api/client'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{ page: number; text_preview: string; relevance_score: number }>
}

// ── Executive Summary Card Component ──────────────────────────────────────

interface ParsedSummary {
  summary: string
  sections: Array<{ title: string; content: string }>
  key_metrics: Array<{ name: string; value: string; significance: string }>
  recommendations: string[]
}

function parseSummary(raw: string): ParsedSummary {
  const fallback: ParsedSummary = {
    summary: raw,
    sections: [],
    key_metrics: [],
    recommendations: [],
  }

  try {
    // The summary might be a JSON string directly
    let text = raw.trim()
    // Strip markdown code fences if wrapped
    if (text.startsWith('```')) {
      text = text.replace(/^```(?:json)?\n?/, '').replace(/\n?```$/, '')
    }
    const parsed = JSON.parse(text)
    return {
      summary: parsed.summary || raw,
      sections: Array.isArray(parsed.sections) ? parsed.sections : [],
      key_metrics: Array.isArray(parsed.key_metrics) ? parsed.key_metrics : [],
      recommendations: Array.isArray(parsed.recommendations) ? parsed.recommendations : [],
    }
  } catch {
    // Not JSON — try to detect if it looks like stringified JSON embedded in text
    const jsonMatch = raw.match(/\{[\s\S]*"summary"[\s\S]*\}/)
    if (jsonMatch) {
      try {
        const parsed = JSON.parse(jsonMatch[0])
        return {
          summary: parsed.summary || raw,
          sections: Array.isArray(parsed.sections) ? parsed.sections : [],
          key_metrics: Array.isArray(parsed.key_metrics) ? parsed.key_metrics : [],
          recommendations: Array.isArray(parsed.recommendations) ? parsed.recommendations : [],
        }
      } catch {
        // fall through
      }
    }
    return fallback
  }
}

const sectionIcons: Record<string, React.ReactNode> = {
  'executive overview': <BookOpen className="w-3.5 h-3.5" />,
  'key findings': <TrendingUp className="w-3.5 h-3.5" />,
  'methodology': <ListChecks className="w-3.5 h-3.5" />,
  'methodology notes': <ListChecks className="w-3.5 h-3.5" />,
  'quantitative highlights': <BarChart3 className="w-3.5 h-3.5" />,
  'implications': <Lightbulb className="w-3.5 h-3.5" />,
  'implications/recommendations': <Lightbulb className="w-3.5 h-3.5" />,
  'recommendations': <Lightbulb className="w-3.5 h-3.5" />,
  'risk factors': <AlertTriangle className="w-3.5 h-3.5" />,
  'risks': <AlertTriangle className="w-3.5 h-3.5" />,
}

function getSectionIcon(title: string) {
  const key = title.toLowerCase().trim()
  for (const [pattern, icon] of Object.entries(sectionIcons)) {
    if (key.includes(pattern)) return icon
  }
  return <FileText className="w-3.5 h-3.5" />
}

function ExecutiveSummaryCard({ summary }: { summary: string }) {
  const data = parseSummary(summary)
  const [expandedSections, setExpandedSections] = useState<Record<number, boolean>>(
    // Default: expand all sections
    Object.fromEntries(data.sections.map((_, i) => [i, true]))
  )

  const toggleSection = (idx: number) => {
    setExpandedSections(prev => ({ ...prev, [idx]: !prev[idx] }))
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#00e1b7] to-[#00b894] flex items-center justify-center">
          <Sparkles className="w-3.5 h-3.5 text-[#0b0f19]" />
        </div>
        <h3 className="text-sm font-semibold text-[#d0e7f4]">AI Executive Summary</h3>
      </div>

      {/* Overview Card */}
      <div className="bg-gradient-to-br from-[#121828] to-[#0e1422] border border-[#1b1f2a] rounded-xl p-5">
        <p className="text-sm text-[#d0e7f4] leading-relaxed">
          {data.summary}
        </p>
      </div>

      {/* Sections */}
      {data.sections.length > 0 && (
        <div className="space-y-2">
          {data.sections.map((section, i) => (
            <div
              key={i}
              className="bg-[#121828] border border-[#1b1f2a] rounded-lg overflow-hidden transition-all duration-200 hover:border-[#2a3040]"
            >
              <button
                onClick={() => toggleSection(i)}
                className="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-[#1b1f2a]/30"
              >
                <div className="w-6 h-6 rounded-md bg-[#00e1b7]/10 text-[#00e1b7] flex items-center justify-center shrink-0">
                  {getSectionIcon(section.title)}
                </div>
                <span className="text-xs font-semibold text-[#d0e7f4] flex-1 truncate">
                  {section.title}
                </span>
                {expandedSections[i] ? (
                  <ChevronUp className="w-3.5 h-3.5 text-[#64748b] shrink-0" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5 text-[#64748b] shrink-0" />
                )}
              </button>
              {expandedSections[i] && (
                <div className="px-4 pb-4 pt-0">
                  <div className="pl-9">
                    <div className="text-xs text-[#a0b4c0] leading-relaxed whitespace-pre-line">
                      {section.content}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Key Metrics */}
      {data.key_metrics.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-3.5 h-3.5 text-[#3b6978]" />
            <h4 className="text-xs font-semibold text-[#3b6978] uppercase tracking-wider">Key Metrics</h4>
          </div>
          <div className="grid grid-cols-1 gap-2">
            {data.key_metrics.map((metric, i) => (
              <div
                key={i}
                className="bg-[#121828] border border-[#1b1f2a] rounded-lg p-3 flex items-start gap-3 transition-all hover:border-[#2a3040]"
              >
                <div className="w-8 h-8 rounded-lg bg-[#00e1b7]/8 border border-[#00e1b7]/20 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-xs font-bold text-[#00e1b7]">{i + 1}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-semibold text-[#d0e7f4] truncate">{metric.name}</span>
                  </div>
                  <div className="text-sm font-bold text-[#00e1b7] mb-1">{metric.value}</div>
                  <p className="text-[10px] text-[#64748b] leading-relaxed">{metric.significance}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {data.recommendations.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb className="w-3.5 h-3.5 text-[#3b6978]" />
            <h4 className="text-xs font-semibold text-[#3b6978] uppercase tracking-wider">Recommendations</h4>
          </div>
          <div className="bg-[#121828] border border-[#1b1f2a] rounded-lg divide-y divide-[#1b1f2a]">
            {data.recommendations.map((rec, i) => (
              <div key={i} className="flex items-start gap-3 px-4 py-3">
                <div className="w-5 h-5 rounded-full bg-[#00e1b7]/10 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-[10px] font-bold text-[#00e1b7]">{i + 1}</span>
                </div>
                <p className="text-xs text-[#a0b4c0] leading-relaxed">{rec}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Virtualized PDF Page Component ────────────────────────────────────────

function VirtualizedPage({ pageNumber, pdfWidth, scale, onVisible }: { pageNumber: number, pdfWidth: number, scale: number, onVisible: (page: number) => void }) {
  const { ref: renderRef, inView: shouldRender } = useInView({
    rootMargin: '1000px 0px 1000px 0px',
    triggerOnce: false,
  })

  const { ref: visibleRef, inView: isVisible } = useInView({
    threshold: 0.5,
  })

  const setRefs = useCallback(
    (node: HTMLDivElement | null) => {
      renderRef(node)
      visibleRef(node)
    },
    [renderRef, visibleRef]
  )

  useEffect(() => {
    if (isVisible) {
      onVisible(pageNumber)
    }
  }, [isVisible, pageNumber, onVisible])

  return (
    <div 
      ref={setRefs} 
      className="mb-8 flex justify-center w-full" 
      id={`pdf-page-${pageNumber}`}
    >
      {shouldRender ? (
        <Page
          pageNumber={pageNumber}
          width={pdfWidth}
          scale={scale}
          renderAnnotationLayer={false}
          renderTextLayer={true}
          className="pdf-page bg-white shadow-2xl"
        />
      ) : (
        <div 
          className="bg-[#0b0f19] animate-pulse shadow-2xl" 
          style={{ width: pdfWidth * scale, height: pdfWidth * scale * 1.414 }} 
        />
      )}
    </div>
  )
}

export default function DocumentViewerPage() {
  const { id } = useParams<{ id: string }>()
  const docId = Number(id)

  const { data: doc, isLoading: isLoadingDoc } = useQuery({
    queryKey: ['document', docId],
    queryFn: () => api.documents.get(docId),
  })

  const { data: textData, isLoading: isLoadingText } = useQuery({
    queryKey: ['documentText', doc?.python_doc_id],
    queryFn: () => api.documents.text(doc?.python_doc_id),
    enabled: !!doc?.python_doc_id && doc.status === 'ready',
    refetchInterval: doc?.status === 'processing' ? 2000 : false
  })

  const [currentPage, setCurrentPage] = useState(1)
  const [numPages, setNumPages] = useState<number>(0)
  const [pdfWidth, setPdfWidth] = useState(560)
  const scrollRef = useRef<HTMLDivElement>(null)
  const [zoom, setZoom] = useState(100)
  const [chatOpen, setChatOpen] = useState(true)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [activeTab, setActiveTab] = useState<'chat' | 'extract' | 'tables' | 'analysis'>('chat')
  const chatEndRef = useRef<HTMLDivElement>(null)

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
    const element = document.getElementById(`pdf-page-${page}`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' })
    }
  }

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const update = () => setPdfWidth(Math.max(280, el.clientWidth - 20)) // 20 for 10px left/right gap
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

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

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || chatMutation.isPending) return

    const userMsg: ChatMessage = { role: 'user', content: inputMessage }
    const updatedMessages = [...messages, userMsg]
    setMessages(updatedMessages)
    setInputMessage('')
    
    const apiMessages = updatedMessages.map(m => ({
      role: m.role,
      content: m.content
    }))
    
    chatMutation.mutate(apiMessages)
  }

  if (isLoadingDoc) {
    return <div className="flex h-[calc(100vh-4rem)] items-center justify-center bg-[#161d2e]"><Loader2 className="w-8 h-8 text-[#00e1b7] animate-spin" /></div>
  }

  if (!doc) {
    return <div className="flex h-[calc(100vh-4rem)] items-center justify-center bg-[#161d2e]"><p className="text-[#d0e7f4]">Document not found</p></div>
  }

  const extractedTables = textData?.tables || []
  
  const currentPageData = textData?.pages?.find((p: any) => p.page_num === currentPage)
  const currentPageBlocks = currentPageData?.blocks || []
  const currentPageTables = extractedTables.filter((t: any) => t.page === currentPage)

  const combinedExtractedText = textData?.pages?.map((p: any) => p.blocks.map((b: any) => b.text).join('\n')).join('\n\n') || ''

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
      <div className={`flex-1 flex flex-col bg-[#161d2e] transition-all min-w-0 ${chatOpen ? '' : 'w-full'}`}>

        <div className="relative h-14 bg-[#0b0f19] border-b border-[#1b1f2a] flex items-center justify-between px-4">
          
          <div className="flex items-center gap-6">
            <Link to="/library" className="flex items-center gap-2 text-[#64748b] hover:text-[#d0e7f4] transition-colors">
              <ChevronLeft className="w-5 h-5" />
            </Link>
            
            <div className="flex items-center gap-3">
              <button
                onClick={() => handlePageChange(Math.max(1, currentPage - 1))}
                disabled={currentPage <= 1}
                className="w-8 h-8 flex items-center justify-center rounded hover:bg-[#1b1f2a] text-[#64748b] hover:text-[#d0e7f4] disabled:opacity-30 transition-all"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              
              <div className="flex items-center gap-2 text-xs text-[#d0e7f4] bg-[#1b1f2a] px-3 py-1.5 rounded" style={{ fontFamily: 'JetBrains Mono' }}>
                <span className="font-semibold text-white">{currentPage}</span>
                <span className="text-[#64748b]">/ {numPages || doc.page_count}</span>
              </div>
              
              <button
                onClick={() => handlePageChange(Math.min(numPages || doc.page_count, currentPage + 1))}
                disabled={currentPage >= (numPages || doc.page_count)}
                className="w-8 h-8 flex items-center justify-center rounded hover:bg-[#1b1f2a] text-[#64748b] hover:text-[#d0e7f4] disabled:opacity-30 transition-all"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3 absolute left-1/2 -translate-x-1/2">
            <button onClick={() => setZoom(z => Math.max(50, z - 10))} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-[#1b1f2a] text-[#64748b] hover:text-[#d0e7f4] transition-all">
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-sm text-[#64748b] w-12 text-center select-none" style={{ fontFamily: 'Inter' }}>{zoom}%</span>
            <button onClick={() => setZoom(z => Math.min(300, z + 10))} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-[#1b1f2a] text-[#64748b] hover:text-[#d0e7f4] transition-all">
              <ZoomIn className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center gap-4">
            <Link
              to={`/pdf-information/${id}`}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#1b1f2a] text-[#64748b] hover:text-[#00e1b7] hover:bg-[#1b1f2a]/80 transition-all text-xs font-medium border border-[#2a3040]"
              title="View Raw Extraction Data"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Data.json</span>
            </Link>
            <button
              onClick={() => setChatOpen(!chatOpen)}
              className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-[#1b1f2a] text-[#64748b] hover:text-[#00e1b7] transition-all"
            >
              {chatOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
            </button>
          </div>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-auto scroll-smooth bg-[#161d2e] pt-[7px] pb-0 px-[10px] bloomberg-scrollbar">
          <div className="flex flex-col items-center w-full min-w-max mx-auto">
            {doc.status === 'processing' && (
              <div className="bg-[#0b0f19] border border-[#1b1f2a] rounded-lg p-6 mb-8 text-center max-w-md">
                <Loader2 className="w-8 h-8 text-[#00e1b7] animate-spin mx-auto mb-4" />
                <p className="text-[#d0e7f4] font-medium">Document is being processed...</p>
                <p className="text-xs text-[#64748b] mt-2">Report Summary generation in progress.</p>
              </div>
            )}

            <div className="w-full min-h-[800px] flex justify-center relative">
              {doc.status === 'processing' ? (
                <div className="flex flex-col items-center justify-center py-20 opacity-50 w-full">
                  <Loader2 className="w-12 h-12 text-[#00e1b7] animate-spin mb-4" />
                  <p className="text-[#d0e7f4]">Document is being processed...</p>
                </div>
              ) : (
                <Document
                  file={`/api/v1/documents/${doc.python_doc_id}/download`}
                  onLoadSuccess={({ numPages }) => setNumPages(numPages)}
                  loading={
                    <div className="flex flex-col items-center justify-center p-20 w-full h-full">
                      <Loader2 className="w-8 h-8 text-[#00e1b7] animate-spin mb-4" />
                      <p className="text-[#d0e7f4]">Loading PDF...</p>
                    </div>
                  }
                  error={
                    <div className="flex flex-col items-center justify-center p-20 w-full h-full text-red-400">
                      <p>Failed to load PDF document.</p>
                    </div>
                  }
                  className="rounded-lg shadow-xl"
                >
                  <div className="flex flex-col items-center">
                    {Array.from(new Array(numPages || 0), (el, index) => (
                      <VirtualizedPage
                        key={`page_${index + 1}`}
                        pageNumber={index + 1}
                        pdfWidth={pdfWidth}
                        scale={(zoom / 100) * 1.6}
                        onVisible={setCurrentPage}
                      />
                    ))}
                  </div>
                </Document>
              )}
            </div>
          </div>
        </div>

      </div>

      {chatOpen && (
        <div className="w-[480px] bg-[#0b0f19] border-l border-[#1b1f2a] flex flex-col">
          <div className="p-4 border-b border-[#1b1f2a]">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-[#00e1b7]" />
              <h2 className="text-sm font-semibold text-[#d0e7f4]">AI Research Assistant</h2>
            </div>

            <div className="space-y-1.5">
              <div className={`flex items-center gap-2 text-xs px-2 py-1.5 rounded transition-all ${doc.status === 'ready' ? 'bg-[#00e1b7]/5 border-l-2 border-[#00e1b7]' : 'bg-yellow-500/5 border-l-2 border-yellow-500'}`}>
                <div className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] ${doc.status === 'ready' ? 'bg-[#00e1b7] text-[#0b0f19]' : 'bg-yellow-500 text-[#0b0f19]'}`}>
                  {doc.status === 'ready' ? '✓' : '1'}
                </div>
                <span className="text-[#d0e7f4] flex-1">Extract & Index Document</span>
                <span className="text-[#64748b]">{doc.status === 'ready' ? 'Completed' : 'Running...'}</span>
              </div>
            </div>
          </div>

          <div className="flex border-b border-[#1b1f2a]">
            {(['chat', 'analysis', 'extract', 'tables'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 py-2.5 text-xs font-medium transition-all relative ${
                  activeTab === tab ? 'text-[#00e1b7]' : 'text-[#64748b] hover:text-[#d0e7f4]'
                }`}
              >
                {tab === 'analysis' ? 'Quick Analysis' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                {activeTab === tab && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#00e1b7]" />
                )}
              </button>
            ))}
          </div>

          {/* Chat Messages */}
          {activeTab === 'chat' && (
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

                {chatMutation.isPending && (
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

              {/* Input */}
              <div className="p-4 border-t border-[#1b1f2a]">
                <div className="flex items-end gap-2">
                  <textarea
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleSendMessage()
                      }
                    }}
                    placeholder="Ask about the document..."
                    rows={2}
                    className="flex-1 bg-[#161d2e] border border-[#1b1f2a] rounded-lg p-3 text-sm text-[#d0e7f4] placeholder:text-[#64748b] focus:border-[#00e1b7] focus:ring-1 focus:ring-[#00e1b7]/20 transition-all resize-none"
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!inputMessage.trim() || chatMutation.isPending}
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
          )}

          {/* Quick Analysis Tab */}
          {activeTab === 'analysis' && (
            <div className="flex-1 overflow-auto p-4 space-y-6 bloomberg-scrollbar">
              {doc?.extracted_summary && (
                <ExecutiveSummaryCard summary={doc.extracted_summary} />
              )}

              {extractedTables?.length > 0 && (
                <div className="space-y-4">
                  <h3 className="text-xs font-semibold text-[#3b6978] uppercase tracking-wider pl-1">Extracted Tables</h3>
                  {extractedTables.map((table: any, ti: number) => (
                    <div key={ti} className="border border-[#1b1f2a] rounded-lg overflow-hidden bg-[#0b0f19]">
                      <div className="bg-[#121828] px-3 py-2 text-[10px] text-[#3b6978] font-medium flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-[#00e1b7]">Table {ti + 1}</span>
                        </div>
                        <span>Page {table.page} · {table.rows}×{table.cols}</span>
                      </div>
                      <div className="overflow-x-auto bloomberg-scrollbar">
                        <table className="w-full">
                          <tbody>
                            {table.data.map((row: string[], ri: number) => (
                              <tr key={ri} className={`transition-colors ${ri === 0 ? 'bg-[#1b1f2a]' : 'border-t border-[#1b1f2a] hover:bg-[#1b1f2a]/40'}`}>
                                {row.map((cell: string, ci: number) => (
                                  <td key={ci} className={`px-3 py-2 text-[10px] ${
                                    ri === 0 ? 'text-[#00e1b7] font-semibold uppercase tracking-wider' : 'text-[#d0e7f4]'
                                  }`} style={{ fontFamily: 'Inter' }}>
                                    {cell}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              {!doc?.extracted_summary && (!extractedTables || extractedTables.length === 0) && (
                <div className="flex flex-col items-center justify-center py-10 opacity-50 text-center">
                  <p className="text-sm text-[#d0e7f4]">No analysis available yet.</p>
                </div>
              )}
            </div>
          )}

          {/* Extracted Text Tab */}
          {activeTab === 'extract' && (
            <div className="flex-1 overflow-auto p-4 bloomberg-scrollbar">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-[#d0e7f4]">Extracted Content</h3>
                  <span className="text-xs text-[#64748b]">{combinedExtractedText.length.toLocaleString()} chars</span>
                </div>
                <div className="bg-[#121828] border border-[#1b1f2a] rounded-lg p-4">
                  <pre className="text-xs text-[#d0e7f4] whitespace-pre-wrap leading-relaxed" style={{ fontFamily: 'JetBrains Mono' }}>
                    {combinedExtractedText}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* Tables Tab */}
          {activeTab === 'tables' && (
            <div className="flex-1 overflow-auto p-4 bloomberg-scrollbar space-y-4">
              {extractedTables?.map((table: any, ti: number) => (
                <div key={ti} className="border border-[#1b1f2a] rounded-lg overflow-hidden">
                  <div className="bg-[#121828] px-3 py-2 text-xs text-[#3b6978] font-medium flex items-center gap-2">
                    <TableIcon className="w-3 h-3" />
                    Table {ti + 1} — Page {table.page} · {table.rows}×{table.cols}
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <tbody>
                        {table.data.map((row: string[], ri: number) => (
                          <tr key={ri} className={ri === 0 ? 'bg-[#1b1f2a]' : 'border-t border-[#1b1f2a] hover:bg-[#1b1f2a]/50'}>
                            {row.map((cell: string, ci: number) => (
                              <td key={ci} className={`px-3 py-2 text-xs whitespace-nowrap ${
                                ri === 0 ? 'text-[#3b6978] font-semibold uppercase tracking-wider' : 'text-[#d0e7f4]'
                              }`} style={{ fontFamily: ri === 0 ? 'Inter' : 'JetBrains Mono' }}>
                                {cell}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
              {(!extractedTables || extractedTables.length === 0) && (
                <div className="text-center py-8">
                  <TableIcon className="w-8 h-8 mx-auto mb-2 text-[#3b6978]" />
                  <p className="text-sm text-[#64748b]">No tables extracted yet</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function TableIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
      <line x1="3" x2="21" y1="9" y2="9" />
      <line x1="3" x2="21" y1="15" y2="15" />
      <line x1="12" x2="12" y1="3" y2="21" />
    </svg>
  )
}
