import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, of, shareReplay } from 'rxjs';

import { ApiService } from '../../core/services/api.service';
import { environment } from '../../../environments/environment';

/** One piece of evidence backing an answer. */
export interface ChatCitation {
  quote?: string;
  source?: string;
  section?: string;
}

export interface ChatReply {
  answer: string;
  citations?: ChatCitation[];
  /** False when the sources do not support an answer — rendered distinctly. */
  grounded?: boolean;
  generated_by?: Record<string, unknown>;
}

/** A turn in the transcript. The client owns the history; the API is stateless. */
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: ChatCitation[];
  grounded?: boolean;
  failed?: boolean;
}

/**
 * Chat grounded in a report — `POST /reports/{id}/chat`.
 *
 * The backend grounds answers on the report's content plus live RAG over the
 * documents its job used, and returns `grounded: false` rather than inventing
 * an answer it cannot support. It answers 503 (not a fabricated fallback) when
 * the language model is unavailable.
 *
 * Availability is still probed from the API's own OpenAPI document rather than
 * assumed: it keeps the panel honest against a backend where the endpoint is
 * absent or disabled, and it is what let the UI ship before the endpoint did.
 */
@Injectable({ providedIn: 'root' })
export class ReportChatService {
  private readonly http = inject(HttpClient);
  private readonly api = inject(ApiService);

  /** Probed once per session and replayed to every caller. */
  private availability?: Observable<boolean>;

  isAvailable(): Observable<boolean> {
    this.availability ??= this.http.get<{ paths?: Record<string, unknown> }>(openApiUrl()).pipe(
      map((spec) => Object.keys(spec?.paths ?? {}).some(isChatPath)),
      // No spec served, or it cannot be reached: treat chat as unavailable
      // rather than letting the panel look broken.
      catchError(() => of(false)),
      shareReplay({ bufferSize: 1, refCount: false }),
    );

    return this.availability;
  }

  send(reportId: string, message: string, history: ChatMessage[]): Observable<ChatReply> {
    return this.api.post<ChatReply>(`/reports/${reportId}/chat`, {
      message,
      // Send only what the contract asks for — not our UI-only fields.
      history: history.map((turn) => ({ role: turn.role, content: turn.content })),
    });
  }
}

/** Matches `/api/v1/reports/{report_id}/chat` whatever the path param is named. */
function isChatPath(path: string): boolean {
  return /\/reports\/\{[^}]+\}\/chat$/.test(path);
}

/** The spec lives at the API root, one level above the /api/v1 prefix. */
function openApiUrl(): string {
  return `${environment.apiUrl.replace(/\/api\/v\d+$/, '')}/openapi.json`;
}
