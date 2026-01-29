/**
 * Hook for document analysis workflow
 */
import { useState, useCallback } from 'react';
import { documentsService, historyService, getErrorMessage } from '../services';
import type { AnalysisResult, FileUpload } from '../pages/compliance-engineer-evidence-analysis-workspace/types';

interface UseAnalysisReturn {
  isAnalyzing: boolean;
  uploadQueue: FileUpload[];
  currentResult: AnalysisResult | null;
  recentAnalyses: AnalysisResult[];
  error: string | null;
  handleFilesSelected: (files: File[]) => void;
  handleAnalyzeEvidence: () => Promise<void>;
  handleNewAnalysis: () => void;
  loadRecentAnalyses: () => Promise<void>;
  selectAnalysis: (id: string) => Promise<void>;
}

function mapValidationStatus(status: string): 'compliant' | 'non-compliant' | 'pending' | 'processing' {
  switch (status) {
    case 'APPROVED':
      return 'compliant';
    case 'REJECTED':
    case 'FAILED':
      return 'non-compliant';
    case 'REVIEW_NEEDED':
    case 'PENDING':
      return 'pending';
    default:
      return 'processing';
  }
}

function calculateComplianceScore(findings: { status: string }[]): number {
  if (!findings || findings.length === 0) return 0;
  const approved = findings.filter(f => f.status === 'APPROVED').length;
  return Math.round((approved / findings.length) * 100);
}

function buildReasoning(findings: { rule_name: string; status: string; message: string }[]): string {
  if (!findings || findings.length === 0) {
    return 'No findings available.';
  }

  const approved = findings.filter(f => f.status === 'APPROVED');
  const rejected = findings.filter(f => f.status === 'REJECTED');
  const review = findings.filter(f => f.status === 'REVIEW_NEEDED');

  let reasoning = '';

  if (approved.length > 0) {
    reasoning += `**Validated (${approved.length}):**\n`;
    approved.forEach(f => {
      reasoning += `- ${f.rule_name}: ${f.message}\n`;
    });
    reasoning += '\n';
  }

  if (rejected.length > 0) {
    reasoning += `**Issues Found (${rejected.length}):**\n`;
    rejected.forEach(f => {
      reasoning += `- ${f.rule_name}: ${f.message}\n`;
    });
    reasoning += '\n';
  }

  if (review.length > 0) {
    reasoning += `**Needs Review (${review.length}):**\n`;
    review.forEach(f => {
      reasoning += `- ${f.rule_name}: ${f.message}\n`;
    });
  }

  return reasoning || 'Analysis complete.';
}

export function useAnalysis(): UseAnalysisReturn {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [uploadQueue, setUploadQueue] = useState<FileUpload[]>([]);
  const [currentResult, setCurrentResult] = useState<AnalysisResult | null>(null);
  const [recentAnalyses, setRecentAnalyses] = useState<AnalysisResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleFilesSelected = useCallback((files: File[]) => {
    const newUploads: FileUpload[] = files.map((file) => ({
      file,
      id: `upload-${Date.now()}-${Math.random()}`,
      progress: 0,
      status: 'uploading' as const,
    }));

    setUploadQueue(newUploads);
    setError(null);

    // Simulate upload progress (actual upload happens in handleAnalyzeEvidence)
    newUploads.forEach((upload, index) => {
      setTimeout(() => {
        setUploadQueue((prev) =>
          prev.map((u) =>
            u.id === upload.id ? { ...u, progress: 100, status: 'complete' as const } : u
          )
        );
      }, 500 * (index + 1));
    });
  }, []);

  const handleAnalyzeEvidence = useCallback(async () => {
    if (uploadQueue.length === 0) return;

    setIsAnalyzing(true);
    setError(null);
    setCurrentResult(null);

    try {
      const file = uploadQueue[0].file;

      // 1. Upload document
      const uploadResponse = await documentsService.upload(file);

      // 2. Trigger extraction
      await documentsService.triggerExtraction(uploadResponse.id);

      // 3. Run validation
      const validationResult = await documentsService.validate(uploadResponse.id);

      // 4. Build analysis result
      const result: AnalysisResult = {
        id: validationResult.document_id,
        documentId: uploadResponse.id,
        fileName: file.name,
        fileType: file.type.includes('pdf') ? 'pdf' : 'image',
        uploadDate: new Date(),
        status: mapValidationStatus(validationResult.status),
        validationStatus: validationResult.status,
        complianceScore: calculateComplianceScore(validationResult.findings),
        reasoning: buildReasoning(validationResult.findings),
        confidenceLevel: 90,
        knowledgeBaseVersion: 'v2.0',
        apiResponseTime: validationResult.processing_time_ms || 0,
        findings: validationResult.findings,
      };

      setCurrentResult(result);
      setUploadQueue([]);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsAnalyzing(false);
    }
  }, [uploadQueue]);

  const handleNewAnalysis = useCallback(() => {
    setCurrentResult(null);
    setUploadQueue([]);
    setError(null);
  }, []);

  const loadRecentAnalyses = useCallback(async () => {
    try {
      const response = await historyService.list({ page_size: 10 });

      const analyses: AnalysisResult[] = response.items.map((item) => ({
        id: item.id,
        documentId: item.document_id,
        fileName: item.document_filename,
        fileType: 'pdf',
        uploadDate: new Date(item.created_at),
        status: mapValidationStatus(item.status),
        validationStatus: item.status,
        complianceScore: 0, // Will be loaded on detail view
        reasoning: '',
        findingsCount: item.findings_count,
      }));

      setRecentAnalyses(analyses);
    } catch (err) {
      console.error('Failed to load recent analyses:', err);
    }
  }, []);

  const selectAnalysis = useCallback(async (validationId: string) => {
    try {
      const detail = await historyService.getDetail(validationId);

      const result: AnalysisResult = {
        id: detail.id,
        documentId: detail.document.id,
        fileName: detail.document.filename,
        fileType: 'pdf',
        uploadDate: new Date(detail.validated_at),
        status: mapValidationStatus(detail.status),
        validationStatus: detail.status,
        complianceScore: calculateComplianceScore(detail.findings),
        reasoning: buildReasoning(detail.findings),
        confidenceLevel: 90,
        knowledgeBaseVersion: detail.model_version || 'v2.0',
        apiResponseTime: detail.processing_time_ms || 0,
        findings: detail.findings,
      };

      setCurrentResult(result);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, []);

  return {
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
  };
}

export default useAnalysis;
