import { PageQuery } from './common.model';

export type DocumentStatus = 'uploaded' | 'processing' | 'ingested' | 'failed';

export interface Doc {
  id: string;
  filename: string;
  title: string | null;
  content_type: string | null;
  size_bytes: number | null;
  status: DocumentStatus;
  page_count: number | null;
  chunk_count: number;
  error: string | null;
  uploaded_by: string | null;
  job_id: string | null;
  created_at: string;
  updated_at: string;
}

/** POST /documents returns the document plus the ingestion job to watch. */
export interface DocumentUploadResponse {
  document: Doc;
  ingestion_job_id: string;
}

/** One chunk of text that RAG searches over. */
export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  text: string;
  char_count: number;
  page_number: number | null;
  created_at: string;
}

export interface DocumentQuery extends PageQuery {
  status?: DocumentStatus;
  q?: string;
}

/** Backend rejects uploads larger than this. */
export const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;
