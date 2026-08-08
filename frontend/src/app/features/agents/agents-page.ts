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

import { Agent } from '../../core/models';
import { apiErrorMessage } from '../../core/services/api-error';
import { AuthService } from '../../core/services/auth.service';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { Paginator } from '../../shared/components/paginator/paginator';
import { StatusBadge } from '../../shared/components/status-badge/status-badge';
import { AgentsService } from './agents.service';

@Component({
  selector: 'app-agents-page',
  imports: [ReactiveFormsModule, StatusBadge, Paginator, EmptyState],
  templateUrl: './agents-page.html',
  styleUrl: './agents-page.scss',
})
export class AgentsPage implements OnInit {
  private readonly agents = inject(AgentsService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  /** Writes are admin-only; the backend enforces it regardless of the UI. */
  protected readonly canWrite = computed(() => this.auth.role() === 'admin');

  protected readonly qControl = this.fb.nonNullable.control('');
  protected readonly activeControl = this.fb.nonNullable.control<'' | 'true' | 'false'>('');

  protected readonly items = signal<Agent[]>([]);
  protected readonly total = signal(0);
  protected readonly page = signal(1);
  protected readonly size = signal(10);
  protected readonly pages = signal(0);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly notice = signal<string | null>(null);

  protected readonly editing = signal<Agent | 'new' | null>(null);
  protected readonly saving = signal(false);
  protected readonly saveError = signal<string | null>(null);

  protected readonly isNew = computed(() => this.editing() === 'new');

  protected readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.maxLength(255)]],
    description: [''],
    system_prompt: [''],
    model: ['', [Validators.maxLength(100)]],
    is_active: [true],
    config: ['{}', [jsonValidator]],
  });

  constructor() {
    this.qControl.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed())
      .subscribe(() => this.reload());
    this.activeControl.valueChanges.pipe(takeUntilDestroyed()).subscribe(() => this.reload());
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

    const active = this.activeControl.value;

    this.agents
      .list({
        page: this.page(),
        size: this.size(),
        q: this.qControl.value || undefined,
        is_active: active === '' ? undefined : active === 'true',
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

  protected startCreate(): void {
    this.saveError.set(null);
    this.form.reset({
      name: '',
      description: '',
      system_prompt: '',
      model: '',
      is_active: true,
      config: '{}',
    });
    this.editing.set('new');
  }

  protected startEdit(agent: Agent): void {
    this.saveError.set(null);
    this.form.reset({
      name: agent.name,
      description: agent.description ?? '',
      system_prompt: agent.system_prompt ?? '',
      model: agent.model ?? '',
      is_active: agent.is_active,
      config: JSON.stringify(agent.config ?? {}, null, 2),
    });
    this.editing.set(agent);
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
    const payload = {
      name: value.name,
      description: value.description || null,
      system_prompt: value.system_prompt || null,
      model: value.model || null,
      is_active: value.is_active,
      config: JSON.parse(value.config || '{}') as Record<string, unknown>,
    };
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
      this.agents.create(payload).subscribe({
        next: () => done(`Agent "${value.name}" created.`),
        error: fail,
      });
    } else if (target) {
      this.agents.update(target.id, payload).subscribe({
        next: () => done(`Agent "${value.name}" updated.`),
        error: fail,
      });
    }
  }

  protected remove(agent: Agent): void {
    if (!confirm(`Delete the agent "${agent.name}"? This is a soft delete.`)) {
      return;
    }
    this.agents.remove(agent.id).subscribe({
      next: () => {
        this.notice.set(`Agent "${agent.name}" deleted.`);
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
