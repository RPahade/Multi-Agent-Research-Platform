import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { Job, JobStatus, JobType } from '../../core/models';
import { apiErrorMessage } from '../../core/services/api-error';
import { AuthService } from '../../core/services/auth.service';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { Paginator } from '../../shared/components/paginator/paginator';
import { StatusBadge } from '../../shared/components/status-badge/status-badge';
import { JobsService } from './jobs.service';

const JOB_STATUSES: JobStatus[] = ['pending', 'running', 'succeeded', 'failed', 'cancelled'];
const JOB_TYPES: JobType[] = ['research', 'ingestion', 'export'];

@Component({
  selector: 'app-jobs-page',
  imports: [ReactiveFormsModule, RouterLink, DatePipe, StatusBadge, Paginator, EmptyState],
  templateUrl: './jobs-page.html',
  styleUrl: './jobs-page.scss',
})
export class JobsPage implements OnInit {
  private readonly jobs = inject(JobsService);
  private readonly auth = inject(AuthService);

  protected readonly statuses = JOB_STATUSES;
  protected readonly types = JOB_TYPES;

  protected readonly statusControl = new FormControl<JobStatus | ''>('', { nonNullable: true });
  protected readonly typeControl = new FormControl<JobType | ''>('', { nonNullable: true });

  protected readonly items = signal<Job[]>([]);
  protected readonly total = signal(0);
  protected readonly page = signal(1);
  protected readonly size = signal(10);
  protected readonly pages = signal(0);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  /** Only analyst + admin may start a job, so only they get the button. */
  protected readonly canCreate = signal(false);

  constructor() {
    this.statusControl.valueChanges.pipe(takeUntilDestroyed()).subscribe(() => this.reload());
    this.typeControl.valueChanges.pipe(takeUntilDestroyed()).subscribe(() => this.reload());
  }

  ngOnInit(): void {
    const role = this.auth.role();
    this.canCreate.set(role === 'admin' || role === 'analyst');
    this.load();
  }

  private reload(): void {
    this.page.set(1);
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.error.set(null);

    this.jobs
      .list({
        page: this.page(),
        size: this.size(),
        status: this.statusControl.value || undefined,
        type: this.typeControl.value || undefined,
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
    this.load();
  }

  protected onSize(size: number): void {
    this.size.set(size);
    this.page.set(1);
    this.load();
  }

  /** Research jobs are best identified by their question. */
  protected label(job: Job): string {
    const query = job.input?.['query'];
    return typeof query === 'string' && query ? query : job.type;
  }
}
