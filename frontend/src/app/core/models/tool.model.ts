import { PageQuery } from './common.model';

export type ToolCategory =
  | 'retrieval'
  | 'web_research'
  | 'citation'
  | 'export'
  | 'compliance';

export const TOOL_CATEGORIES: ToolCategory[] = [
  'retrieval',
  'web_research',
  'citation',
  'export',
  'compliance',
];

export interface Tool {
  id: string;
  key: string;
  name: string;
  description: string | null;
  category: ToolCategory;
  config: Record<string, unknown>;
  enabled: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ToolCreate {
  key: string;
  name: string;
  category: ToolCategory;
  description?: string | null;
  config?: Record<string, unknown>;
  enabled?: boolean;
}

/** `key` is immutable once created, so it is not updatable. */
export type ToolUpdate = Partial<Omit<ToolCreate, 'key'>>;

export interface ToolQuery extends PageQuery {
  category?: ToolCategory;
  enabled?: boolean;
  q?: string;
}
