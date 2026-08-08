import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Observable, debounceTime, distinctUntilChanged, take, takeWhile, timer } from 'rxjs';
import { switchMap } from 'rxjs/operators';

import { Doc, DocumentChunk, DocumentStatus } from '../../core/models';
import { apiErrorMessage } from '../../core/services/api-error';
import { AuthService } from '../../core/services/auth.service';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { Paginator } from '../../shared/components/paginator/paginator';
import { StatusBadge } from '../../shared/components/status-badge/status-badge';
import { DocumentsService } from './documents.service';
import { ACCEPT_ATTRIBUTE, ALLOWED_EXTENSIONS, formatBytes, validateUpload } from './upload-rules';

const DOCUMENT_STATUSES: DocumentStatus[] = ['uploaded', 'processing', 'ingested', 'failed'];

/** How many chunks to show when a document is expanded. */
const CHUNK_PAGE_SIZE = 20;

/** Ingestion watch: poll every 1.5s, give up after ~90s. */
const POLL_INTERVAL_MS = 1500;
const POLL_MAX_TICKS = 60;

/** A file being uploaded from this screen. */
interface Upload {
  name: string;
  status: 'uploading' | 'ingesting' | 'done' | 'failed';
  percent: number;
  error?: string;
}

@Component({
  selector: 'app-documents-page',
  imports: [ReactiveFormsModule, RouterLink, DatePipe, StatusBadge, Paginator, EmptyState],
  templateUrl: './documents-page.html',
  styleUrl: './documents-page.scss',
})
export class DocumentsPage implements OnInit {
  private readonly documents = inject(DocumentsService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  protected readonly statuses = DOCUMENT_STATUSES;
  protected readonly allowedTypes = ALLOWED_EXTENSIONS.join(', ');
  protected readonly accept = ACCEPT_ATTRIBUTE;
  protected readonly formatBytes = formatBytes;

  /** Upload and delete are analyst + admin (the backend's require_job_writer). */
  protected readonly canWrite = computed(() => {
    const role = this.auth.role();
    return role === 'admin' || role === 'analyst';
  });

  private readonly currentUserId = computed(() => this.auth.user()?.id ?? null);

  protected readonly qControl = this.fb.nonNullable.control('');
  protected readonly statusControl = this.fb.nonNullable.control<DocumentStatus | ''>('');

  protected readonly items = signal<Doc[]>([]);
  protected readonly total = signal(0);
  protected readonly page = signal(1);
  protected readonly size = signal(10);
  protected readonly pages = signal(0);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly notice = signal<string | null>(null);

  protected readonly uploads = signal<Upload[]>([]);

  /** Which document's chunks are open, plus the chunks loaded per document. */
  protected readonly expandedId = signal<string | null>(null);
  protected readonly chunks = signal<Record<string, DocumentChunk[]>>({});
  protected readonly chunkTotals = signal<Record<string, number>>({});
  protected readonly chunksLoading = signal(false);

  constructor() {
    this.qControl.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed())
      .subscribe(() => this.reload());
    this.statusControl.valueChanges.pipe(takeUntilDestroyed()).subscribe(() => this.reload());
  }

  ngOnInit(): void {
    this.load();
  }

  private reload(): void {
    this.page.set(1);
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.error.set(null);

    this.documents
      .list({
        page: this.page(),
        size: this.size(),
        q: this.qControl.value || undefined,
        status: this.statusControl.value || undefined,
      })
      .subscribe({
        next: (result) => {
          this.items.set(result.items);
          this.total.set(result.total);
          this.pages.set(result.pages);
          this.loading.set(false);
        },
        error: (err) => {
          this.error.set(apiErrorMessage(err));
          this.items.set([]);
          this.loading.set(false);
        },
      });
  }

  protected onPage(page: number): void {
    this.page.set(page);
    this.expandedId.set(null);
    this.load();
  }

  protected onSize(size: number): void {
    this.size.set(size);
    this.page.set(1);
    this.load();
  }

  protected isMine(doc: Doc): boolean {
    return !!doc.uploaded_by && doc.uploaded_by === this.currentUserId();
  }

  // --- chunk inspector -------------------------------------------------

  /**
   * The chunks are exactly what retrieval searches over. Nothing else in the
   * app shows them, and report citations cannot be expanded to their source
   * (the backend does not persist retrieved passages), so this is the only way
   * to read the evidence a report was grounded in.
   */
  protected toggleChunks(doc: Doc): void {
    if (this.expandedId() === doc.id) {
      this.expandedId.set(null);
      return;
    }

    this.expandedId.set(doc.id);

    if (this.chunks()[doc.id]) {
      return;
    }

    this.chunksLoading.set(true);
    this.documents.chunks(doc.id, 1, CHUNK_PAGE_SIZE).subscribe({
      next: (result) => {
        this.chunks.update((cache) => ({ ...cache, [doc.id]: result.items }));
        this.chunkTotals.update((cache) => ({ ...cache, [doc.id]: result.total }));
        this.chunksLoading.set(false);
      },
      error: (err) => {
        this.error.set(apiErrorMessage(err));
        this.chunks.update((cache) => ({ ...cache, [doc.id]: [] }));
        this.chunksLoading.set(false);
      },
    });
  }

  protected chunksFor(id: string): DocumentChunk[] {
    return this.chunks()[id] ?? [];
  }

  protected chunkTotal(id: string): number {
    return this.chunkTotals()[id] ?? 0;
  }

  // --- upload ----------------------------------------------------------

  protected onFilesPicked(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    input.value = ''; // allow re-picking the same file after a failure

    for (const file of files) {
      const problem = validateUpload(file);
      if (problem) {
        this.addUpload({ name: file.name, status: 'failed', percent: 0, error: problem });
      } else {
        this.addUpload({ name: file.name, status: 'uploading', percent: 0 });
        this.startUpload(file);
      }
    }
  }

  private addUpload(upload: Upload): void {
    this.uploads.update((list) => [...list, upload]);
  }

  private patchUpload(name: string, patch: Partial<Upload>): void {
    this.uploads.update((list) =>
      list.map((item) => (item.name === name ? { ...item, ...patch } : item)),
    );
  }

  private startUpload(file: File): void {
    this.documents.upload(file).subscribe({
      next: (progress) => {
        this.patchUpload(file.name, { percent: progress.percent });

        if (progress.result) {
          this.patchUpload(file.name, { status: 'ingesting' });
          // Show the row immediately, then follow it to a terminal state.
          this.load();
          this.watchIngestion(file.name, progress.result.document.id);
        }
      },
      error: (err) => this.patchUpload(file.name, { status: 'failed', error: apiErrorMessage(err) }),
    });
  }

  /** Ingestion runs as a background job, so poll the document until it settles. */
  private watchIngestion(name: string, documentId: string): void {
    pollDocument(this.documents, documentId).subscribe({
      next: (doc) => {
        if (doc.status === 'ingested') {
          this.patchUpload(name, { status: 'done' });
          this.load();
        } else if (doc.status === 'failed') {
          this.patchUpload(name, { status: 'failed', error: doc.error ?? 'Ingestion failed.' });
          this.load();
        }
      },
      error: (err) => this.patchUpload(name, { status: 'failed', error: apiErrorMessage(err) }),
    });
  }

  protected clearUploads(): void {
    this.uploads.set([]);
  }

  // --- delete ----------------------------------------------------------

  protected remove(doc: Doc): void {
    // There is no re-ingest endpoint, so deleting is genuinely destructive:
    // recovering means uploading the file again.
    if (!confirm(`Delete "${doc.filename}"? Re-adding it means uploading the file again.`)) {
      return;
    }

    this.documents.remove(doc.id).subscribe({
      next: () => {
        this.notice.set(`"${doc.filename}" deleted.`);
        if (this.expandedId() === doc.id) {
          this.expandedId.set(null);
        }
        this.load();
      },
      error: (err) => this.error.set(apiErrorMessage(err)),
    });
  }
}

function pollDocument(documents: DocumentsService, id: string): Observable<Doc> {
  return timer(0, POLL_INTERVAL_MS).pipe(
    take(POLL_MAX_TICKS),
    switchMap(() => documents.get(id)),
    takeWhile((doc) => doc.status === 'uploaded' || doc.status === 'processing', true),
  );
}
