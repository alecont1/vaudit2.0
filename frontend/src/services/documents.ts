/**
 * Document service for AuditEng V2
 */
import api from './api';

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  file_hash: string;
  file_size_bytes: number;
  status: string;
  created_at: string;
}

export interface FieldLocation {
  page: number;
  bbox: {
    left: number;
    top: number;
    right: number;
    bottom: number;
  };
  chunk_id?: string;
}

export interface ExtractedField {
  name: string;
  value: string;
  location?: FieldLocation;
}

export interface CalibrationInfo {
  instrument_type?: string;
  serial_number?: ExtractedField;
  calibration_date?: ExtractedField;
  expiration_date?: ExtractedField;
  certificate_number?: ExtractedField;
  calibrating_lab?: ExtractedField;
}

export interface ExtractionResult {
  document_id: string;
  status: 'completed' | 'failed' | 'processing';
  page_count: number;
  calibrations: CalibrationInfo[];
  measurements: unknown[];
  raw_markdown?: string;
  raw_chunks_count?: number;
  processing_time_ms?: number;
  model_version?: string;
  error_message?: string;
}

export interface ValidationFinding {
  rule_id: string;
  rule_name: string;
  status: 'APPROVED' | 'REJECTED' | 'REVIEW_NEEDED';
  message: string;
  severity: 'error' | 'warning' | 'info';
  evidence?: {
    page?: number;
    field_name?: string;
    found_value?: string;
    expected_value?: string;
  };
}

export interface ValidationResult {
  document_id: string;
  status: 'APPROVED' | 'REJECTED' | 'REVIEW_NEEDED' | 'PENDING' | 'FAILED';
  findings: ValidationFinding[];
  validated_at: string;
  processing_time_ms?: number;
}

export const documentsService = {
  async upload(file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<DocumentUploadResponse>(
      '/documents/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  async triggerExtraction(documentId: string): Promise<ExtractionResult> {
    const response = await api.post<ExtractionResult>(
      `/documents/${documentId}/extract`
    );
    return response.data;
  },

  async getExtraction(documentId: string): Promise<ExtractionResult> {
    const response = await api.get<ExtractionResult>(
      `/documents/${documentId}/extraction`
    );
    return response.data;
  },

  async validate(documentId: string): Promise<ValidationResult> {
    const response = await api.post<ValidationResult>(
      `/documents/${documentId}/validate`
    );
    return response.data;
  },

  async getValidation(documentId: string): Promise<ValidationResult> {
    const response = await api.get<ValidationResult>(
      `/documents/${documentId}/validation`
    );
    return response.data;
  },
};

export default documentsService;
