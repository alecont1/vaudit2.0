/**
 * History service for AuditEng V2
 */
import api from './api';
import { ValidationFinding } from './documents';

export type ValidationStatus =
  | 'APPROVED'
  | 'REJECTED'
  | 'REVIEW_NEEDED'
  | 'PENDING'
  | 'FAILED';

export interface HistoryListItem {
  id: string;
  document_id: string;
  document_filename: string;
  status: ValidationStatus;
  created_at: string;
  findings_count: number | null;
}

export interface HistoryListResponse {
  items: HistoryListItem[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface HistoryFilters {
  page?: number;
  page_size?: number;
  status?: ValidationStatus;
  start_date?: string; // YYYY-MM-DD
  end_date?: string; // YYYY-MM-DD
  document_name?: string;
}

export interface DocumentInfo {
  id: string;
  filename: string;
  file_hash: string;
  file_size_bytes: number;
  uploaded_at: string;
}

export interface HistoryDetailResponse {
  id: string;
  document: DocumentInfo;
  status: ValidationStatus;
  findings: ValidationFinding[];
  validated_at: string;
  validator_version: string | null;
  model_version: string | null;
  processing_time_ms: number | null;
  findings_count: number;
  has_extraction: boolean;
  has_analysis: boolean;
}

export const historyService = {
  async list(filters: HistoryFilters = {}): Promise<HistoryListResponse> {
    const params = new URLSearchParams();

    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size)
      params.append('page_size', filters.page_size.toString());
    if (filters.status) params.append('status', filters.status);
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.document_name)
      params.append('document_name', filters.document_name);

    const response = await api.get<HistoryListResponse>(
      `/history/?${params.toString()}`
    );
    return response.data;
  },

  async getDetail(validationId: string): Promise<HistoryDetailResponse> {
    const response = await api.get<HistoryDetailResponse>(
      `/history/${validationId}`
    );
    return response.data;
  },
};

export default historyService;
