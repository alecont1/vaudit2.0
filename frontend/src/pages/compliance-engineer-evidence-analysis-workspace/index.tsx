import React, { useState, useCallback, useEffect } from 'react';
import RoleBasedHeader from '../../components/ui/RoleBasedHeader';
import Button from '../../components/ui/Button';
import RecentAnalysisSidebar from './components/RecentAnalysisSidebar';
import EvidenceUploadZone from './components/EvidenceUploadZone';
import AnalysisLoadingState from './components/AnalysisLoadingState';
import ValidationResultsPanel from './components/ValidationResultsPanel';
import DetailedReasoningSidebar from './components/DetailedReasoningSidebar';
import { useAnalysis } from '../../hooks/useAnalysis';
import { AnalysisResult } from './types';

const ComplianceEngineerEvidenceAnalysisWorkspace: React.FC = () => {
  const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisResult | null>(null);

  const {
    isAnalyzing,
    uploadQueue,
    currentResult,
    recentAnalyses,
    error,
    handleFilesSelected,
    handleAnalyzeEvidence,
    handleNewAnalysis,
    loadRecentAnalyses,
    selectAnalysis,
  } = useAnalysis();

  // Load recent analyses on mount
  useEffect(() => {
    loadRecentAnalyses();
  }, [loadRecentAnalyses]);

  const handleDownloadReport = useCallback(() => {
    if (currentResult?.reportUrl) {
      const link = document.createElement('a');
      link.href = currentResult.reportUrl;
      link.download = `Audit_Report_${currentResult.id}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }, [currentResult]);

  const handleSelectAnalysis = useCallback((analysis: AnalysisResult) => {
    setSelectedAnalysis(analysis);
    selectAnalysis(analysis.id);
  }, [selectAnalysis]);

  return (
    <div className="min-h-screen bg-background">
      <RoleBasedHeader userRole="engineer" />

      <div className="pt-16 h-screen flex">
        <div className="hidden lg:block w-80">
          <RecentAnalysisSidebar
            analyses={recentAnalyses}
            onSelectAnalysis={handleSelectAnalysis}
            selectedAnalysisId={selectedAnalysis?.id || null}
          />
        </div>

        <main className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto p-6 lg:p-8">
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-foreground mb-2">
                Evidence Analysis Workspace
              </h1>
              <p className="text-text-secondary">
                Upload commissioning report PDFs for automated validation using
                AI-powered extraction and domain-specific rules
              </p>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                <p className="font-medium">Error</p>
                <p className="text-sm">{error}</p>
              </div>
            )}

            {!isAnalyzing && !currentResult && (
              <div className="space-y-6">
                <EvidenceUploadZone
                  onFilesSelected={handleFilesSelected}
                  isAnalyzing={isAnalyzing}
                  uploadQueue={uploadQueue}
                />

                {uploadQueue.length > 0 &&
                  uploadQueue.every((u) => u.status === 'complete') && (
                    <div className="flex justify-center animate-fade-in">
                      <Button
                        variant="default"
                        size="xl"
                        iconName="Play"
                        iconPosition="left"
                        onClick={handleAnalyzeEvidence}
                        className="min-w-[300px]"
                      >
                        Analyze Evidence
                      </Button>
                    </div>
                  )}
              </div>
            )}

            {isAnalyzing && <AnalysisLoadingState />}

            {!isAnalyzing && currentResult && (
              <ValidationResultsPanel
                result={currentResult}
                onDownloadReport={handleDownloadReport}
                onNewAnalysis={handleNewAnalysis}
              />
            )}
          </div>
        </main>

        <div className="hidden xl:block w-96">
          <DetailedReasoningSidebar result={currentResult || selectedAnalysis} />
        </div>
      </div>

      <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-card border-t border-border p-4 shadow-elevated">
        <Button
          variant="outline"
          size="lg"
          fullWidth
          iconName="Menu"
          iconPosition="left"
          onClick={() => {
            const sidebar = document.querySelector('aside');
            if (sidebar) {
              sidebar.classList.toggle('hidden');
            }
          }}
        >
          View Recent Analyses
        </Button>
      </div>
    </div>
  );
};

export default ComplianceEngineerEvidenceAnalysisWorkspace;
