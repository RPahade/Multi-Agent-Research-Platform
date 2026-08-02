import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { Agent, JobCreate } from '../../core/models';
import { apiErrorMessage, apiFieldErrors } from '../../core/services/api-error';
import { AgentsService } from '../agents/agents.service';
import { DocumentUpload } from './document-upload';
import { JobsService } from './jobs.service';
import { PipelinePreview } from './pipeline-preview';

/** Tool keys that `input.fail_tool` accepts, for the testing panel. */
const TOOL_KEYS = ['retrieval', 'research', 'synthesis', 'citation', 'compliance'];

/** Backend default for retrieval depth (`RETRIEVAL_TOP_K`). */
const DEFAULT_TOP_K = 5;

@Component({
  selector: 'app-new-job-page',
  imports: [ReactiveFormsModule, DocumentUpload, PipelinePreview],
  templateUrl: './new-job-page.html',
  styleUrl: './new-job-page.scss',
})
export class NewJobPage implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly jobs = inject(JobsService);
  private readonly agents = inject(AgentsService);
  private readonly router = inject(Router);

  protected readonly toolKeys = TOOL_KEYS;

  protected readonly form = this.fb.nonNullable.group({
    query: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(2000)]],
    top_k: [DEFAULT_TOP_K, [Validators.required, Validators.min(1), Validators.max(20)]],
    max_attempts: [3, [Validators.required, Validators.min(1), Validators.max(10)]],
    agent_id: [''],
    fail_tool: [''],
    tool_seconds: [0.4, [Validators.min(0), Validators.max(10)]],
  });

  protected readonly availableAgents = signal<Agent[]>([]);
  protected readonly selectedDocumentIds = signal<string[]>([]);
  protected readonly uploadsBusy = signal(false);
  protected readonly showAdvanced = signal(false);

  protected readonly submitting = signal(false);
  protected readonly error = signal<string | null>(null);

  /**
   * Sent as Idempotency-Key so a double submit returns the job already created
   * rather than starting a second run. Replaced after each successful create.
   */
  private idempotencyKey = crypto.randomUUID();

  ngOnInit(): void {
    this.agents.list({ page: 1, size: 50, is_active: true }).subscribe({
      next: (result) => this.availableAgents.set(result.items),
      error: () => this.availableAgents.set([]),
    });
  }

  protected onSelectionChange(ids: string[]): void {
    this.selectedDocumentIds.set(ids);
  }

  protected onUploadsBusy(busy: boolean): void {
    this.uploadsBusy.set(busy);
  }

  protected toggleAdvanced(): void {
    this.showAdvanced.update((open) => !open);
  }

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.error.set(null);

    this.jobs.create(this.buildPayload(), this.idempotencyKey).subscribe({
      next: (job) => {
        this.submitting.set(false);
        // A new run should be a new job, not a repeat of this one.
        this.idempotencyKey = crypto.randomUUID();
        // Straight to the live progress view — the job is already running.
        this.router.navigate(['/jobs', job.id]);
      },
      error: (err) => {
        this.error.set(apiErrorMessage(err));
        this.applyFieldErrors(err);
        this.submitting.set(false);
      },
    });
  }

  /** Only sends keys the backend actually reads (see the orchestrator's tools). */
  private buildPayload(): JobCreate {
    const value = this.form.getRawValue();

    const input: Record<string, unknown> = {
      query: value.query.trim(),
      top_k: value.top_k,
    };

    const documentIds = this.selectedDocumentIds();
    if (documentIds.length) {
      input['document_ids'] = documentIds;
    }

    if (this.showAdvanced()) {
      if (value.fail_tool) {
        input['fail_tool'] = value.fail_tool;
      }
      if (value.tool_seconds !== 0.4) {
        input['tool_seconds'] = value.tool_seconds;
      }
    }

    const payload: JobCreate = {
      type: 'research',
      input,
      max_attempts: value.max_attempts,
    };

    if (value.agent_id) {
      payload.agent_id = value.agent_id;
    }

    return payload;
  }

  /** Maps a 422 back onto the matching controls so errors show inline. */
  private applyFieldErrors(err: unknown): void {
    const fields = apiFieldErrors(err);
    for (const [field, message] of Object.entries(fields)) {
      const control = this.form.get(field);
      if (control) {
        control.setErrors({ server: message });
        control.markAsTouched();
      }
    }
  }


  protected showError(field: string): boolean {
    const control = this.form.get(field);
    return !!control && control.invalid && control.touched;
  }

  /** The server's own message wins over the generic one when present. */
  protected errorFor(field: string): string | null {
    const control = this.form.get(field);
    return (control?.errors?.['server'] as string) ?? null;
  }
}
