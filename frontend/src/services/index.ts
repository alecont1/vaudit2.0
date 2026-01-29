/**
 * Services index - exports all API services
 */
export { default as api, getErrorMessage } from './api';
export { default as authService } from './auth';
export { default as documentsService } from './documents';
export { default as historyService } from './history';

export type { LoginRequest, TokenResponse, SessionInfo, User } from './auth';
export type {
  DocumentUploadResponse,
  ExtractionResult,
  ValidationResult,
  ValidationFinding,
} from './documents';
export type {
  HistoryListItem,
  HistoryListResponse,
  HistoryFilters,
  HistoryDetailResponse,
  ValidationStatus,
} from './history';
