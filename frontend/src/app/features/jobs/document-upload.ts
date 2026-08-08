import { DatePipe } from '@angular/common';
import { Component, OnDestroy, OnInit, inject, output, signal } from '@angular/core';
import { Observable, Subscription, take, takeWhile, timer } from 'rxjs';
import { switchMap } from 'rxjs/operators';

import { Doc, MAX_UPLOAD_BYTES } from '../../core/models';
import { apiErrorMessage } from '../../core/services/api-error';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { StatusBadge } from '../../shared/components/status-badge/status-badge';
import { DocumentsService } from '../documents/documents.service';
import {
  ACCEPT_ATTRIBUTE,
  ALLOWED_EXTENSIONS,
  validateUpload,
} from '../documents/upload-rules';

/** Give up watching an ingestion after roughly 90 seconds. */
const POLL_INTERVAL_MS = 1500;
const POLL_MAX_TICKS = 60;

/** One file the user picked, tracked from selection through to ingestion. */
interface Upload {
  name: string;
  size: number;
  status: 'queued' | 'uploading' | 'ingesting' | 'ingested' | 'failed';
  percent: number;
  error?: string;
  documentId?: string;
}

@Component({
  selector: 'app-document-upload',
  imports: [StatusBadge, EmptyState, DatePipe],
  templateUrl: './document-upload.html',
  styleUrl: './document-upload.scss',
})
export class DocumentUpload implements OnInit, OnDestroy {
  private readonly documents = inject(DocumentsService);

  /** Documents the research job should be scoped to (empty = search everything). */
  readonly selectionChange = output<string[]>();
  /** True while an upload or ingestion is still running, so the form can block submit. */
  readonly busyChange = output<boolean>();

  protected readonly available = signal<Doc[]>([]);
  protected readonly selected = signal<Set<string>>(new Set());
  protected readonly uploads = signal<Upload[]>([]);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly maxBytes = MAX_UPLOAD_BYTES;
  protected readonly allowedTypes = ALLOWED_EXTENSIONS.join(', ');
  protected readonly accept = ACCEPT_ATTRIBUTE;

  private pollSubscription?: Subscription;

  ngOnInit(): void {
    this.loadDocuments();
  }

  /** Only ingested documents are useful — anything else has no embeddings yet. */
  protected loadDocuments(): void {
    this.loading.set(true);
    this.documents.list({ page: 1, size: 50, status: 'ingested' }).subscribe({
      next: (result) => {
        this.available.set(result.items);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(apiErrorMessage(err));
        this.loading.set(false);
      },
    });
  }

  protected onFilesPicked(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    input.value = ''; // let the same file be picked again after a failure

    for (const file of files) {
      const problem = validateUpload(file);
      if (problem) {
        this.addUpload({ name: file.name, size: file.size, status: 'failed', percent: 0, error: problem });
      } else {
        this.addUpload({ name: file.name, size: file.size, status: 'queued', percent: 0 });
        this.startUpload(file);
      }
    }
  }

  private addUpload(upload: Upload): void {
    this.uploads.update((list) => [...list, upload]);
    this.emitBusy();
  }

  private patchUpload(name: string, patch: Partial<Upload>): void {
    this.uploads.update((list) =>
      list.map((item) => (item.name === name ? { ...item, ...patch } : item)),
    );
    this.emitBusy();
  }

  /** Uploads run one request per file — the endpoint takes a single file. */
  private startUpload(file: File): void {
    this.patchUpload(file.name, { status: 'uploading' });

    this.documents.upload(file).subscribe({
      next: (progress) => {
        this.patchUpload(file.name, { percent: progress.percent });

        if (progress.result) {
          const document = progress.result.document;
          this.patchUpload(file.name, { status: 'ingesting', documentId: document.id });
          this.watchIngestion(file.name, document.id);
        }
      },
      error: (err) => {
        this.patchUpload(file.name, { status: 'failed', error: apiErrorMessage(err) });
      },
    });
  }

  /**
   * Ingestion (parse, chunk, embed) runs as a background job, so poll the
   * document until it settles. Watching the document rather than the job gives
   * us the failure reason directly.
   */
  private watchIngestion(name: string, documentId: string): void {
    this.pollSubscription = pollDocument(this.documents, documentId).subscribe({
      next: (document) => {
        if (document.status === 'ingested') {
          this.patchUpload(name, { status: 'ingested' });
          // Newly ingested documents are added and selected automatically.
          this.available.update((list) => [document, ...list.filter((d) => d.id !== document.id)]);
          this.toggle(document.id, true);
        } else if (document.status === 'failed') {
          this.patchUpload(name, {
            status: 'failed',
            error: document.error ?? 'Ingestion failed.',
          });
        }
      },
      error: (err) => this.patchUpload(name, { status: 'failed', error: apiErrorMessage(err) }),
    });
  }

  protected isSelected(id: string): boolean {
    return this.selected().has(id);
  }

  protected onToggle(id: string, event: Event): void {
    this.toggle(id, (event.target as HTMLInputElement).checked);
  }

  private toggle(id: string, on: boolean): void {
    this.selected.update((current) => {
      const next = new Set(current);
      if (on) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
    this.selectionChange.emit([...this.selected()]);
  }

  protected clearSelection(): void {
    this.selected.set(new Set());
    this.selectionChange.emit([]);
  }

  /** Busy = anything still uploading or ingesting. */
  private emitBusy(): void {
    const busy = this.uploads().some(
      (upload) => upload.status === 'queued' || upload.status === 'uploading' || upload.status === 'ingesting',
    );
    this.busyChange.emit(busy);
  }

  protected formatSize(bytes: number): string {
    return bytes < 1024 * 1024
      ? `${Math.max(1, Math.round(bytes / 1024))} KB`
      : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  ngOnDestroy(): void {
    this.pollSubscription?.unsubscribe();
  }
}

/** Polls a document until it stops being uploaded/processing, or we time out. */
function pollDocument(documents: DocumentsService, id: string): Observable<Doc> {
  return timer(0, POLL_INTERVAL_MS).pipe(
    take(POLL_MAX_TICKS),
    switchMap(() => documents.get(id)),
    // `true` emits the terminal value as well as stopping there.
    takeWhile((doc) => doc.status === 'uploaded' || doc.status === 'processing', true),
  );
}
