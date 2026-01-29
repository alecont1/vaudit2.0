import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import Icon from '../../../components/AppIcon';
import PDFHighlightOverlay from './PDFHighlightOverlay';
import { PDFHighlight } from '../types';
import { documentsService } from '../../../services/documents';

// Set up the worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PDFViewerProps {
  documentId: string;
  currentPage: number;
  onPageChange: (page: number) => void;
  highlights: PDFHighlight[];
  activeHighlightId: string | null;
}

const PDFViewer: React.FC<PDFViewerProps> = ({
  documentId,
  currentPage,
  onPageChange,
  highlights,
  activeHighlightId,
}) => {
  const [numPages, setNumPages] = useState<number>(0);
  const [scale, setScale] = useState<number>(1.0);
  const [pageWidth, setPageWidth] = useState<number>(0);
  const [pageHeight, setPageHeight] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRef = useRef<HTMLDivElement>(null);

  const pdfUrl = documentsService.getFileUrl(documentId);

  // Filter highlights for current page
  const currentPageHighlights = highlights.filter((h) => h.page === currentPage);

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoading(false);
    setError(null);
  }, []);

  const onDocumentLoadError = useCallback((err: Error) => {
    console.error('PDF load error:', err);
    setError('Falha ao carregar o documento PDF');
    setLoading(false);
  }, []);

  const onPageLoadSuccess = useCallback((page: any) => {
    setPageWidth(page.width);
    setPageHeight(page.height);
  }, []);

  const handlePrevPage = useCallback(() => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  }, [currentPage, onPageChange]);

  const handleNextPage = useCallback(() => {
    if (currentPage < numPages) {
      onPageChange(currentPage + 1);
    }
  }, [currentPage, numPages, onPageChange]);

  const handleZoomIn = useCallback(() => {
    setScale((prev) => Math.min(prev + 0.25, 3.0));
  }, []);

  const handleZoomOut = useCallback(() => {
    setScale((prev) => Math.max(prev - 0.25, 0.5));
  }, []);

  const handleZoomReset = useCallback(() => {
    setScale(1.0);
  }, []);

  // Scroll to page when activeHighlightId changes
  useEffect(() => {
    if (activeHighlightId) {
      const highlight = highlights.find((h) => h.id === activeHighlightId);
      if (highlight && highlight.page !== currentPage) {
        onPageChange(highlight.page);
      }
    }
  }, [activeHighlightId, highlights, currentPage, onPageChange]);

  // Scroll page container to show active highlight
  useEffect(() => {
    if (activeHighlightId && pageRef.current) {
      const highlight = currentPageHighlights.find((h) => h.id === activeHighlightId);
      if (highlight) {
        // Scroll to make the highlight visible
        const container = containerRef.current;
        if (container) {
          const scrollTop = (highlight.bbox.top * pageHeight * scale) - (container.clientHeight / 3);
          container.scrollTo({
            top: Math.max(0, scrollTop),
            behavior: 'smooth',
          });
        }
      }
    }
  }, [activeHighlightId, currentPageHighlights, pageHeight, scale]);

  return (
    <div className="flex flex-col h-full bg-muted/30 rounded-lg overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-3 border-b border-border bg-card">
        <div className="flex items-center gap-2">
          <button
            onClick={handlePrevPage}
            disabled={currentPage <= 1}
            className="p-1.5 rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Pagina anterior"
          >
            <Icon name="ChevronLeft" size={18} className="text-foreground" />
          </button>

          <span className="text-sm text-foreground min-w-[80px] text-center">
            {loading ? '-' : `${currentPage} / ${numPages}`}
          </span>

          <button
            onClick={handleNextPage}
            disabled={currentPage >= numPages}
            className="p-1.5 rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Proxima pagina"
          >
            <Icon name="ChevronRight" size={18} className="text-foreground" />
          </button>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={handleZoomOut}
            disabled={scale <= 0.5}
            className="p-1.5 rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Diminuir zoom"
          >
            <Icon name="ZoomOut" size={18} className="text-foreground" />
          </button>

          <button
            onClick={handleZoomReset}
            className="px-2 py-1 text-xs font-medium text-foreground hover:bg-muted rounded-md transition-colors"
            title="Resetar zoom"
          >
            {Math.round(scale * 100)}%
          </button>

          <button
            onClick={handleZoomIn}
            disabled={scale >= 3.0}
            className="p-1.5 rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Aumentar zoom"
          >
            <Icon name="ZoomIn" size={18} className="text-foreground" />
          </button>
        </div>
      </div>

      {/* PDF Content */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto p-4 flex justify-center"
      >
        {loading && (
          <div className="flex flex-col items-center justify-center py-12">
            <Icon
              name="Loader"
              size={32}
              className="text-primary animate-spin mb-3"
            />
            <p className="text-sm text-text-secondary">Carregando documento...</p>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center py-12">
            <Icon name="AlertCircle" size={32} className="text-error mb-3" />
            <p className="text-sm text-error font-medium mb-1">Erro ao carregar</p>
            <p className="text-xs text-text-secondary">{error}</p>
          </div>
        )}

        <Document
          file={pdfUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          onLoadError={onDocumentLoadError}
          loading={null}
          error={null}
          className={loading || error ? 'hidden' : ''}
        >
          <div ref={pageRef} className="relative shadow-lg">
            <Page
              pageNumber={currentPage}
              scale={scale}
              onLoadSuccess={onPageLoadSuccess}
              loading={null}
              renderTextLayer={true}
              renderAnnotationLayer={true}
            />
            {!loading && pageWidth > 0 && pageHeight > 0 && (
              <PDFHighlightOverlay
                highlights={currentPageHighlights}
                activeHighlightId={activeHighlightId}
                containerWidth={pageWidth * scale}
                containerHeight={pageHeight * scale}
              />
            )}
          </div>
        </Document>
      </div>

      {/* Page info footer */}
      {currentPageHighlights.length > 0 && (
        <div className="p-2 border-t border-border bg-card">
          <p className="text-xs text-text-secondary text-center">
            {currentPageHighlights.length}{' '}
            {currentPageHighlights.length === 1 ? 'marcacao' : 'marcacoes'} nesta pagina
          </p>
        </div>
      )}
    </div>
  );
};

export default PDFViewer;
