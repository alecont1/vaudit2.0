export interface KnowledgeDocument {
  id: string;
  filename: string;
  uploadDate: Date;
  fileSize: number;
  category: string;
  status: 'active' | 'archived' | 'pending' | 'processing';
  lastModified: Date;
  uploadedBy: string;
  version: string;
  tags: string[];
  description: string;
}

export interface ComplianceCategory {
  id: string;
  name: string;
  documentCount: number;
  subcategories?: ComplianceCategory[];
}

export interface UploadProgress {
  filename: string;
  progress: number;
  status: 'uploading' | 'processing' | 'complete' | 'error';
  error?: string;
}

export interface BulkAction {
  type: 'categorize' | 'delete' | 'archive' | 'activate';
  selectedIds: string[];
}

export interface FilterState {
  category: string;
  status: string;
  searchQuery: string;
  dateRange: {
    start: Date | null;
    end: Date | null;
  };
}

export interface DocumentMetadata {
  id: string;
  filename: string;
  category: string;
  tags: string[];
  description: string;
  version: string;
}

export interface SortConfig {
  field: keyof KnowledgeDocument;
  direction: 'asc' | 'desc';
}