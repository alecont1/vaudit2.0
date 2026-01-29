export type ValidationStatus = 'APPROVED' | 'REJECTED' | 'REVIEW_NEEDED' | 'PENDING' | 'FAILED';

export interface BoundingBox {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export interface AnalysisResult {
  id: string;
  documentId: string;
  fileName: string;
  fileType: string;
  uploadDate: Date;
  status: 'compliant' | 'non-compliant' | 'pending' | 'processing';
  validationStatus?: ValidationStatus;
  complianceScore: number;
  reasoning: string;
  confidenceLevel?: number;
  knowledgeBaseVersion?: string;
  apiResponseTime?: number;
  reportUrl?: string;
  findings?: AnalysisFinding[];
}

export interface AnalysisFinding {
  rule_id: string;
  rule_name: string;
  status: 'APPROVED' | 'REJECTED' | 'REVIEW_NEEDED';
  message: string;
  severity: 'error' | 'warning' | 'info';
  field_name?: string;
  found_value?: string;
  expected_value?: string;
  page?: number;
  bbox?: BoundingBox;
}

export type SeverityFilter = 'all' | 'error' | 'warning' | 'info';
export type SortOrder = 'severity' | 'page' | 'rule_id';

export interface PDFHighlight {
  id: string;
  page: number;
  bbox: BoundingBox;
  severity: 'error' | 'warning' | 'info';
}

export interface FileUpload {
  file: File;
  id: string;
  progress: number;
  status: 'uploading' | 'analyzing' | 'complete' | 'error';
  error?: string;
}

export interface FilterOptions {
  status: string[];
  scoreRange: {
    min: number;
    max: number;
  };
  dateRange: {
    start: Date | null;
    end: Date | null;
  };
}

export interface AnalysisQueueItem {
  id: string;
  fileName: string;
  priority: number;
  status: 'queued' | 'processing' | 'complete';
  addedAt: Date;
}