import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { useState, useEffect, useRef } from 'react'

export function usePDFExtraction(docId: number) {
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

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const update = () => setPdfWidth(Math.max(280, el.clientWidth - 20))
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
    const element = document.getElementById(`pdf-page-${page}`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' })
    }
  }

  return {
    doc,
    isLoadingDoc,
    textData,
    isLoadingText,
    currentPage,
    setCurrentPage,
    numPages,
    setNumPages,
    pdfWidth,
    scrollRef,
    zoom,
    setZoom,
    handlePageChange
  }
}
