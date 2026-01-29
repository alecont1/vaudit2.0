import React, { useState, useCallback, useMemo } from 'react';
import Button from '../../../components/ui/Button';
import ExecutiveSummary from './ExecutiveSummary';
import FindingsList from './FindingsList';
import PDFViewer from './PDFViewer';
import {
  AnalysisResult,
  AnalysisFinding,
  PDFHighlight,
  SeverityFilter,
  SortOrder,
} from '../types';

interface ValidationResultsPanelProps {
  result: AnalysisResult;
  onDownloadReport: () => void;
  onNewAnalysis: () => void;
}

const ValidationResultsPanel: React.FC<ValidationResultsPanelProps> = ({
  result,
  onDownloadReport,
  onNewAnalysis,
}) => {
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all');
  const [sortOrder, setSortOrder] = useState<SortOrder>('severity');

  const findings = result.findings || [];

  // Convert findings to PDF highlights
  const highlights: PDFHighlight[] = useMemo(() => {
    return findings
      .filter((f) => f.bbox && f.page)
      .map((f) => ({
        id: f.rule_id,
        page: f.page!,
        bbox: f.bbox!,
        severity: f.severity,
      }));
  }, [findings]);

  const handleFindingSelect = useCallback((finding: AnalysisFinding | null) => {
    if (!finding) {
      setSelectedFindingId(null);
      return;
    }

    setSelectedFindingId(finding.rule_id);

    // Navigate to the finding's page if available
    if (finding.page) {
      setCurrentPage(finding.page);
    }
  }, []);

  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  const handleSortChange = useCallback((order: SortOrder) => {
    setSortOrder(order);
  }, []);

  const handleFilterChange = useCallback((filter: SeverityFilter) => {
    setSeverityFilter(filter);
  }, []);

  // Determine if we should show the PDF viewer (only if document has bbox findings)
  const hasPDFHighlights = highlights.length > 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Executive Summary */}
      <ExecutiveSummary
        status={result.validationStatus || 'PENDING'}
        findings={findings}
        fileName={result.fileName}
        validatedAt={result.uploadDate}
      />

      {/* Main Content Area */}
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        {hasPDFHighlights ? (
          // Side-by-side layout when we have PDF highlights
          <div className="flex flex-col lg:flex-row" style={{ height: '600px' }}>
            {/* Findings List */}
            <div className="w-full lg:w-96 border-b lg:border-b-0 lg:border-r border-border">
              <FindingsList
                findings={findings}
                selectedFindingId={selectedFindingId}
                onFindingSelect={handleFindingSelect}
                sortOrder={sortOrder}
                onSortChange={handleSortChange}
                severityFilter={severityFilter}
                onFilterChange={handleFilterChange}
              />
            </div>

            {/* PDF Viewer */}
            <div className="flex-1 min-h-[400px]">
              <PDFViewer
                documentId={result.documentId}
                currentPage={currentPage}
                onPageChange={handlePageChange}
                highlights={highlights}
                activeHighlightId={selectedFindingId}
              />
            </div>
          </div>
        ) : (
          // Stacked layout when no PDF highlights
          <div className="p-6">
            <FindingsList
              findings={findings}
              selectedFindingId={selectedFindingId}
              onFindingSelect={handleFindingSelect}
              sortOrder={sortOrder}
              onSortChange={handleSortChange}
              severityFilter={severityFilter}
              onFilterChange={handleFilterChange}
            />
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <Button
          variant="default"
          size="lg"
          fullWidth
          iconName="Download"
          iconPosition="left"
          onClick={onDownloadReport}
        >
          Download Relatorio
        </Button>
        <Button
          variant="outline"
          size="lg"
          iconName="Plus"
          iconPosition="left"
          onClick={onNewAnalysis}
        >
          Nova Analise
        </Button>
      </div>
    </div>
  );
};

export default ValidationResultsPanel;
