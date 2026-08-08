import { HttpEventType, HttpResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, filter, map } from 'rxjs';

import {
  Doc,
  DocumentChunk,
  DocumentQuery,
  DocumentUploadResponse,
  Page,
} from '../../core/models';
import { ApiService } from '../../core/services/api.service';

/** What the caller sees while a file uploads; `result` arrives on the last emission. */
export interface UploadProgress {
  percent: number;
  result?: DocumentUploadResponse;
}

/** Calls for the /documents endpoints. */
@Injectable({ providedIn: 'root' })
export class DocumentsService {
  private readonly api = inject(ApiService);

  /**
   * Upload one file. The backend accepts a single file per request and starts
   * an ingestion job, returning the document plus that job's id.
   */
  upload(file: File): Observable<UploadProgress> {
    const form = new FormData();
    form.append('file', file);

    return this.api.upload<DocumentUploadResponse>('/documents', form).pipe(
      filter(
        (event) =>
          event.type === HttpEventType.UploadProgress ||
          event.type === HttpEventType.Response,
      ),
      map((event) => {
        if (event.type === HttpEventType.Response) {
          const response = event as HttpResponse<DocumentUploadResponse>;
          return { percent: 100, result: response.body ?? undefined };
        }
        const total = event.total ?? 0;
        return { percent: total ? Math.round((100 * event.loaded) / total) : 0 };
      }),
    );
  }

  list(query: DocumentQuery = {}): Observable<Page<Doc>> {
    return this.api.getPage<Doc>('/documents', {
      page: query.page,
      size: query.size,
      status: query.status,
      q: query.q,
    });
  }

  get(id: string): Observable<Doc> {
    return this.api.get<Doc>(`/documents/${id}`);
  }

  /** The chunks RAG searches over. */
  chunks(id: string, page = 1, size = 20): Observable<Page<DocumentChunk>> {
    return this.api.getPage<DocumentChunk>(`/documents/${id}/chunks`, { page, size });
  }

  /**
   * Soft delete. Analyst + admin only.
   *
   * There is no re-ingest endpoint, so this is not reversible from the UI —
   * restoring a document means uploading the file again.
   */
  remove(id: string): Observable<void> {
    return this.api.delete<void>(`/documents/${id}`);
  }
}
