import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { Doc, DocumentChunk, DocumentQuery, Page } from '../../core/models';
import { ApiService } from '../../core/services/api.service';

/** Calls for the /documents endpoints. Upload arrives with its own milestone. */
@Injectable({ providedIn: 'root' })
export class DocumentsService {
  private readonly api = inject(ApiService);

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
}
