import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { debounceTime, distinctUntilChanged } from 'rxjs';

import { TOOL_CATEGORIES, Tool, ToolCategory } from '../../core/models';
import { apiErrorMessage } from '../../core/services/api-error';
import { AuthService } from '../../core/services/auth.service';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { Paginator } from '../../shared/components/paginator/paginator';
import { StatusBadge } from '../../shared/components/status-badge/status-badge';
import { ToolsService } from './tools.service';

@Component({
  selector: 'app-tools-page',
  imports: [ReactiveFormsModule, StatusBadge, Paginator, EmptyState],
  templateUrl: './tools-page.html',
  styleUrl: './tools-page.scss',
})
export class ToolsPage implements OnInit {
  private readonly tools = inject(ToolsService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  protected readonly categories = TOOL_CATEGORIES;

  /** Writes are admin-only; the backend enforces it regardless of the UI. */
  protected readonly canWrite = computed(() => this.auth.role() === 'admin');

  protected readonly qControl = this.fb.nonNullable.control('');
  protected readonly categoryControl = this.fb.nonNullable.control<ToolCategory | ''>('');
  protected readonly enabledControl = this.fb.nonNullable.control<'' | 'true' | 'false'>('');

  protected readonly items = signal<Tool[]>([]);
  protected readonly total = signal(0);
  protected readonly page = signal(1);
  protected readonly size = signal(10);
  protected readonly pages = signal(0);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  /** null = closed, 'new' = creating, otherwise the tool being edited. */
  protected readonly editing = signal<Tool | 'new' | null>(null);
  protected readonly saving = signal(false);
  protected readonly saveError = signal<string | null>(null);
  protected readonly notice = signal<string | null>(null);

  protected readonly form = this.fb.nonNullable.group({
    key: ['', [Validators.required, Validators.maxLength(100)]],
    name: ['', [Validators.required, Validators.maxLength(255)]],
    description: [''],
    category: ['retrieval' as ToolCategory, [Validators.required]],
    enabled: [true],
    config: ['{}', [jsonValidator]],
  });

  protected readonly isNew = computed(() => this.editing() === 'new');

  constructor() {
    this.qControl.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed())
      .subscribe(() => this.reload());
    this.categoryControl.valueChanges.pipe(takeUntilDestroyed()).subscribe(() => this.reload());
    this.enabledControl.valueChanges.pipe(takeUntilDestroyed()).subscribe(() => this.reload());
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

    const enabled = this.enabledControl.value;

    this.tools
      .list({
        page: this.page(),
        size: this.size(),
        q: this.qControl.value || undefined,
        category: this.categoryControl.value || undefined,
        enabled: enabled === '' ? undefined : enabled === 'true',
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

  // --- create / edit ---------------------------------------------------

  protected startCreate(): void {
    this.saveError.set(null);
    this.form.reset({
      key: '',
      name: '',
      description: '',
      category: 'retrieval',
      enabled: true,
      config: '{}',
    });
    this.form.controls.key.enable();
    this.editing.set('new');
  }

  protected startEdit(tool: Tool): void {
    this.saveError.set(null);
    this.form.reset({
      key: tool.key,
      name: tool.name,
      description: tool.description ?? '',
      category: tool.category,
      enabled: tool.enabled,
      config: JSON.stringify(tool.config ?? {}, null, 2),
    });
    // The key is the stable machine identifier — immutable once created.
    this.form.controls.key.disable();
    this.editing.set(tool);
  }

  protected cancel(): void {
    this.editing.set(null);
    this.saveError.set(null);
  }

  protected save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.saving.set(true);
    this.saveError.set(null);

    const value = this.form.getRawValue();
    const config = JSON.parse(value.config || '{}') as Record<string, unknown>;
    const target = this.editing();

    const done = (message: string) => {
      this.saving.set(false);
      this.editing.set(null);
      this.notice.set(message);
      this.load();
    };
    const fail = (err: unknown) => {
      this.saveError.set(apiErrorMessage(err));
      this.saving.set(false);
    };

    if (target === 'new') {
      this.tools
        .create({
          key: value.key,
          name: value.name,
          description: value.description || null,
          category: value.category,
          enabled: value.enabled,
          config,
        })
        .subscribe({ next: () => done(`Tool "${value.name}" created.`), error: fail });
    } else if (target) {
      this.tools
        .update(target.id, {
          name: value.name,
          description: value.description || null,
          category: value.category,
          enabled: value.enabled,
          config,
        })
        .subscribe({ next: () => done(`Tool "${value.name}" updated.`), error: fail });
    }
  }

  /** Quick enable/disable straight from the table. */
  protected toggleEnabled(tool: Tool): void {
    this.tools.update(tool.id, { enabled: !tool.enabled }).subscribe({
      next: () => {
        this.notice.set(`"${tool.name}" ${tool.enabled ? 'disabled' : 'enabled'}.`);
        this.load();
      },
      error: (err) => this.error.set(apiErrorMessage(err)),
    });
  }

  protected remove(tool: Tool): void {
    if (!confirm(`Delete the tool "${tool.name}"? This is a soft delete.`)) {
      return;
    }
    this.tools.remove(tool.id).subscribe({
      next: () => {
        this.notice.set(`Tool "${tool.name}" deleted.`);
        this.load();
      },
      error: (err) => this.error.set(apiErrorMessage(err)),
    });
  }

  protected showError(field: string): boolean {
    const control = this.form.get(field);
    return !!control && control.invalid && control.touched;
  }
}

/** `config` is free-form JSON, so reject anything that will not parse. */
function jsonValidator(control: AbstractControl): ValidationErrors | null {
  const value = (control.value ?? '').trim();
  if (!value) {
    return null;
  }
  try {
    const parsed = JSON.parse(value);
    return typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)
      ? null
      : { json: 'Must be a JSON object.' };
  } catch {
    return { json: 'Not valid JSON.' };
  }
}
