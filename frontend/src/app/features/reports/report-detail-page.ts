import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, input, signal } from '@angular/core';
import {
  FormArray,
  FormBuilder,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { RouterLink } from '@angular/router';

import {
  REPORT_STATUSES,
  Report,
  ReportContent,
  ReportStatus,
  ReportVersion,
} from '../../core/models';
import { apiErrorMessage } from '../../core/services/api-error';
import { AuthService } from '../../core/services/auth.service';
import { StatusBadge } from '../../shared/components/status-badge/status-badge';
import { ReportChat } from './report-chat';
import { ReportExportService } from './report-export.service';
import { ReportsService } from './reports.service';

/** One editable section row. */
interface SectionForm {
  heading: FormControl<string>;
  body: FormControl<string>;
}

@Component({
  selector: 'app-report-detail-page',
  imports: [DatePipe, RouterLink, ReactiveFormsModule, StatusBadge, ReportChat],
  templateUrl: './report-detail-page.html',
  styleUrl: './report-detail-page.scss',
})
export class ReportDetailPage implements OnInit {
  /** Route parameter, bound by withComponentInputBinding(). */
  readonly id = input.required<string>();

  private readonly reports = inject(ReportsService);
  private readonly exporter = inject(ReportExportService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  protected readonly report = signal<Report | null>(null);
  protected readonly versions = signal<ReportVersion[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  protected readonly statuses = REPORT_STATUSES;

  /** Editing is a write — analyst and admin only; the backend answers 403 otherwise. */
  protected readonly canEdit = computed(() => {
    const role = this.auth.role();
    return role === 'admin' || role === 'analyst';
  });

  protected readonly editing = signal(false);
  protected readonly saving = signal(false);
  protected readonly saveError = signal<string | null>(null);
  protected readonly saved = signal(false);
  protected readonly exporting = signal(false);

  protected readonly editForm = this.fb.nonNullable.group({
    title: ['', [Validators.required, Validators.maxLength(500)]],
    summary: [''],
    status: ['draft' as ReportStatus, [Validators.required]],
    sections: this.fb.nonNullable.array<FormGroup<SectionForm>>([]),
  });

  protected get sectionForms(): FormArray<FormGroup<SectionForm>> {
    return this.editForm.controls.sections;
  }

  /** When set, the page is showing an older snapshot instead of the current one. */
  protected readonly viewingVersion = signal<ReportVersion | null>(null);

  /** Content of whichever version is on screen. */
  protected readonly content = computed<ReportContent>(() => {
    const older = this.viewingVersion();
    return (older ? older.content : this.report()?.content) ?? {};
  });

  protected readonly shownTitle = computed(
    () => this.viewingVersion()?.title ?? this.report()?.title ?? '',
  );

  protected readonly shownSummary = computed(
    () => this.viewingVersion()?.summary ?? this.report()?.summary ?? null,
  );

  protected readonly sections = computed(() => this.content().sections ?? []);
  protected readonly citations = computed(() => this.content().citations ?? []);
  protected readonly warnings = computed(() => this.content().warnings ?? []);

  /**
   * `generated_by` is free-form JSON, so read it defensively — every field here
   * is genuinely optional and must stay typed as nullable.
   */
  protected readonly provenance = computed(() => {
    const raw = this.content().generated_by as Record<string, unknown> | undefined;
    if (!raw) {
      return null;
    }
    const usage = raw['usage'] as Record<string, unknown> | undefined;
    return {
      provider: asString(raw['provider']),
      model: asString(raw['model']),
      totalTokens: asNumber(usage?.['totalTokenCount']),
    };
  });

  /** The compliance tool records whether it ran and what it removed. */
  protected readonly compliance = computed(
    () => this.content()['compliance'] as { scanned?: boolean; pii_redacted?: number } | undefined,
  );

  ngOnInit(): void {
    this.reports.get(this.id()).subscribe({
      next: (report) => {
        this.report.set(report);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(apiErrorMessage(err));
        this.loading.set(false);
      },
    });

    // Unpaginated by design — the endpoint returns the full history.
    this.reports.versions(this.id()).subscribe({
      next: (versions) => this.versions.set([...versions].sort((a, b) => b.version - a.version)),
      error: () => this.versions.set([]),
    });
  }

  protected showVersion(version: ReportVersion): void {
    this.viewingVersion.set(version);
  }

  protected showCurrent(): void {
    this.viewingVersion.set(null);
  }

  // --- editing ---------------------------------------------------------

  /** One form group per section, so headings and bodies edit in place. */
  private newSection(heading = '', body = '') {
    return this.fb.nonNullable.group({
      heading: [heading, [Validators.required]],
      body: [body],
    });
  }

  protected startEditing(): void {
    const report = this.report();
    if (!report) {
      return;
    }

    // Always edit the current report, never a historical snapshot.
    this.showCurrent();
    this.saveError.set(null);
    this.saved.set(false);

    this.sectionForms.clear();
    for (const section of report.content.sections ?? []) {
      this.sectionForms.push(this.newSection(section.heading, section.body));
    }

    this.editForm.patchValue({
      title: report.title,
      // The column is what the report view reads; content.summary mirrors it.
      summary: report.summary ?? report.content.summary ?? '',
      status: report.status,
    });

    this.editing.set(true);
  }

  protected cancelEditing(): void {
    this.editing.set(false);
    this.saveError.set(null);
  }

  protected addSection(): void {
    this.sectionForms.push(this.newSection());
  }

  protected removeSection(index: number): void {
    this.sectionForms.removeAt(index);
  }

  protected moveSection(index: number, delta: number): void {
    const target = index + delta;
    if (target < 0 || target >= this.sectionForms.length) {
      return;
    }
    const control = this.sectionForms.at(index);
    this.sectionForms.removeAt(index);
    this.sectionForms.insert(target, control);
  }

  protected save(): void {
    const report = this.report();
    if (!report || this.editForm.invalid) {
      this.editForm.markAllAsTouched();
      return;
    }

    this.saving.set(true);
    this.saveError.set(null);

    const value = this.editForm.getRawValue();

    // Spread the existing content so citations, warnings, compliance and
    // generated_by survive an edit — they are not editable here.
    //
    // title and summary live BOTH as columns and inside content, and the two
    // drift if only one is written: the report view reads the columns while the
    // body comes from content. Write both.
    const content: ReportContent = {
      ...report.content,
      title: value.title,
      summary: value.summary || undefined,
      sections: value.sections.map((section) => ({
        heading: section.heading,
        body: section.body,
      })),
    };

    this.reports
      .update(report.id, {
        title: value.title,
        summary: value.summary || null,
        status: value.status,
        content,
      })
      .subscribe({
        next: (updated) => {
          this.report.set(updated);
          this.editing.set(false);
          this.saving.set(false);
          this.saved.set(true);
          // Every PATCH snapshots a version server-side, so refresh the list.
          this.loadVersions();
        },
        error: (err) => {
          this.saveError.set(apiErrorMessage(err));
          this.saving.set(false);
        },
      });
  }

  /**
   * Restore an old snapshot by saving it as a NEW version — history is never
   * rewritten, so the restore itself is recorded too.
   */
  protected restore(version: ReportVersion): void {
    const report = this.report();
    if (!report) {
      return;
    }
    if (!confirm(`Restore version ${version.version}? This is saved as a new version.`)) {
      return;
    }

    this.saving.set(true);
    this.saveError.set(null);

    this.reports
      .update(report.id, {
        title: version.title,
        summary: version.summary,
        content: version.content,
      })
      .subscribe({
        next: (updated) => {
          this.report.set(updated);
          this.viewingVersion.set(null);
          this.saving.set(false);
          this.saved.set(true);
          this.loadVersions();
        },
        error: (err) => {
          this.saveError.set(apiErrorMessage(err));
          this.saving.set(false);
        },
      });
  }

  private loadVersions(): void {
    this.reports.versions(this.id()).subscribe({
      next: (versions) => this.versions.set([...versions].sort((a, b) => b.version - a.version)),
      error: () => undefined,
    });
  }

  // --- export ----------------------------------------------------------

  protected async downloadDocx(): Promise<void> {
    const report = this.report();
    if (!report) {
      return;
    }
    this.exporting.set(true);
    try {
      await this.exporter.downloadDocx(report, this.content());
    } catch {
      this.saveError.set('The DOCX could not be generated.');
    } finally {
      this.exporting.set(false);
    }
  }

  protected printPdf(): void {
    this.exporter.printPdf();
  }
}

function asString(value: unknown): string | null {
  return typeof value === 'string' && value ? value : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === 'number' ? value : null;
}
