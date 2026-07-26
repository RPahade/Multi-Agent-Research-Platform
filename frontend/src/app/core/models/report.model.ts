import { PageQuery } from './common.model';

export type ReportStatus = 'draft' | 'final' | 'archived';

export const REPORT_STATUSES: ReportStatus[] = ['draft', 'final', 'archived'];

export interface ReportSection {
  heading: string;
  body: string;
}

export interface ReportCitation {
  claim: string;
  source: string;
}

/**
 * `content` is free-form JSON on the backend. This is the shape the agent
 * actually produces — treat every field as optional and render defensively.
 * `degraded: true` means the LLM was unavailable and a stub was written.
 */
export interface ReportContent {
  title?: string;
  summary?: string;
  sections?: ReportSection[];
  citations?: ReportCitation[];
  degraded?: boolean;
  warnings?: string[];
  generated_by?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface Report {
  id: string;
  job_id: string | null;
  title: string;
  summary: string | null;
  content: ReportContent;
  status: ReportStatus;
  version: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportVersion {
  id: string;
  report_id: string;
  version: number;
  title: string;
  summary: string | null;
  content: ReportContent;
  created_by: string | null;
  created_at: string;
}

export interface ReportCreate {
  title: string;
  summary?: string | null;
  content?: ReportContent;
  status?: ReportStatus;
  job_id?: string | null;
}

export type ReportUpdate = Partial<Omit<ReportCreate, 'job_id'>>;

export interface ReportQuery extends PageQuery {
  status?: ReportStatus;
  job_id?: string;
  q?: string;
}
