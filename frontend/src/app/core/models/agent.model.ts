import { PageQuery } from './common.model';

export interface Agent {
  id: string;
  name: string;
  description: string | null;
  system_prompt: string | null;
  model: string | null;
  config: Record<string, unknown>;
  version: number;
  is_active: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentCreate {
  name: string;
  description?: string | null;
  system_prompt?: string | null;
  model?: string | null;
  config?: Record<string, unknown>;
  is_active?: boolean;
}

export type AgentUpdate = Partial<AgentCreate>;

export interface AgentQuery extends PageQuery {
  is_active?: boolean;
  q?: string;
}
