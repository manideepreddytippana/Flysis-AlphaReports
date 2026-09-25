import { useCallback, useEffect } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import { useInView } from 'react-intersection-observer'
import { Loader2 } from 'lucide-react'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()

interface VirtualizedPageProps {
  pageNumber: number
  pdfWidth: number
  scale: number
  onVisible: (page: number) => void
}

function VirtualizedPage({ pageNumber, pdfWidth, scale, onVisible }: VirtualizedPageProps) {
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

interface PDFViewerProps {
  pythonDocId: string
  numPages: number
  pdfWidth: number
  zoom: number
  setNumPages: (pages: number) => void
  setCurrentPage: (page: number) => void
}

export function PDFViewer({ pythonDocId, numPages, pdfWidth, zoom, setNumPages, setCurrentPage }: PDFViewerProps) {
  return (
    <Document
      file={`/api/v1/documents/${pythonDocId}/download`}
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
        {Array.from(new Array(numPages || 0), (_, index) => (
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
  )
}
