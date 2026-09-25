import { useState } from 'react'
import { useParams, Link } from 'react-router'
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Loader2,
  FileText,
  Sparkles,
  PanelRightOpen,
  PanelRightClose
} from 'lucide-react'

import { usePDFExtraction } from '@/hooks/usePDFExtraction'
import { useDocumentChat } from '@/hooks/useDocumentChat'

import { ExecutiveSummaryCard } from '@/components/SummaryCard'
import { PDFViewer } from '@/components/PDFViewer'
import { ChatInterface } from '@/components/ChatInterface'

export default function DocumentViewerPage() {
  const { id } = useParams<{ id: string }>()
  const docId = Number(id)

  const {
    doc,
    isLoadingDoc,
    textData,
    currentPage,
    setCurrentPage,
    numPages,
    setNumPages,
    pdfWidth,
    scrollRef,
    zoom,
    setZoom,
    handlePageChange
  } = usePDFExtraction(docId)

  const { messages, sendMessage, isPending } = useDocumentChat(doc)
  const [chatOpen, setChatOpen] = useState(true)
  const [activeTab, setActiveTab] = useState<'chat' | 'extract' | 'tables' | 'analysis'>('chat')

  if (isLoadingDoc) {
    return <div className="flex h-[calc(100vh-4rem)] items-center justify-center bg-[#161d2e]"><Loader2 className="w-8 h-8 text-[#00e1b7] animate-spin" /></div>
  }

  if (!doc) {
    return <div className="flex h-[calc(100vh-4rem)] items-center justify-center bg-[#161d2e]"><p className="text-[#d0e7f4]">Document not found</p></div>
  }

  const extractedTables = textData?.tables || []
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
                <PDFViewer 
                  pythonDocId={doc.python_doc_id}
                  numPages={numPages}
                  pdfWidth={pdfWidth}
                  zoom={zoom}
                  setNumPages={setNumPages}
                  setCurrentPage={setCurrentPage}
                />
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

          {activeTab === 'chat' && (
            <ChatInterface 
              messages={messages} 
              isPending={isPending} 
              onSendMessage={sendMessage} 
            />
          )}

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
