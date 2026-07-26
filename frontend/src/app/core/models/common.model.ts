/** Shapes that are shared by every part of the API. */

/** Every list endpoint returns this wrapper. */
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

/** Query params accepted by every list endpoint. */
export interface PageQuery {
  page?: number;
  size?: number;
}

/** GET /health */
export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  env: string;
}

/** GET /health/db */
export interface DbHealthResponse {
  status: string;
  database: string;
}

/** Plain `{ "detail": "..." }` responses (e.g. logout). */
export interface MessageResponse {
  detail: string;
}

/** GET /mcp/status */
export interface McpStatus {
  enabled: boolean;
  server_url: string | null;
  reachable: boolean;
  tools: string[];
}

/** GET /events/status */
export interface EventsStatus {
  kafka_enabled: boolean;
  bootstrap_servers: string | null;
  topic: string | null;
  consumer_group: string | null;
}
