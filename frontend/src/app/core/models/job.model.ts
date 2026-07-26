import { PageQuery } from './common.model';

export type JobStatus =
  | 'pending'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'cancelled';

export type JobType = 'research' | 'ingestion' | 'export';

export type JobStepStatus =
  | 'pending'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'skipped';

/** A job is finished when it reaches one of these; the SSE stream closes too. */
export const TERMINAL_JOB_STATUSES: JobStatus[] = [
  'succeeded',
  'failed',
  'cancelled',
];

export interface Job {
  id: string;
  user_id: string | null;
  agent_id: string | null;
  type: JobType;
  status: JobStatus;
  input: Record<string, unknown>;
  progress: number;
  current_step: string | null;
  error: string | null;
  idempotency_key: string | null;
  attempts: number;
  max_attempts: number;
  last_heartbeat: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
}

/** Input for a `research` job. */
export interface ResearchInput {
  query: string;
  document_ids?: string[];
  top_k?: number;
  [key: string]: unknown;
}

export interface JobCreate {
  type?: JobType;
  input: Record<string, unknown>;
  agent_id?: string | null;
  max_attempts?: number;
}

/** One tool run inside a job — GET /jobs/{id}/steps */
export interface JobStep {
  id: string;
  job_id: string;
  sequence: number;
  tool_key: string;
  name: string;
  required: boolean;
  status: JobStepStatus;
  output: Record<string, unknown> | null;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

/** A single message from GET /jobs/{id}/stream (SSE). */
export interface JobEvent {
  id: string;
  status: JobStatus;
  progress: number;
  current_step: string | null;
  attempts?: number;
  error?: string | null;
}

export interface JobQuery extends PageQuery {
  status?: JobStatus;
  type?: JobType;
}
