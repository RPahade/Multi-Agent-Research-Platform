import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { debounceTime, distinctUntilChanged } from 'rxjs';

import { USER_ROLES, User, UserRole } from '../../core/models';
import { apiErrorMessage } from '../../core/services/api-error';
import { AuthService } from '../../core/services/auth.service';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { Paginator } from '../../shared/components/paginator/paginator';
import { StatusBadge } from '../../shared/components/status-badge/status-badge';
import { UsersService } from './users.service';

@Component({
  selector: 'app-users-page',
  imports: [ReactiveFormsModule, RouterLink, DatePipe, StatusBadge, Paginator, EmptyState],
  templateUrl: './users-page.html',
  styleUrl: './users-page.scss',
})
export class UsersPage implements OnInit {
  private readonly users = inject(UsersService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  protected readonly roles = USER_ROLES;

  /** The signed-in account, so we never offer to lock ourselves out. */
  protected readonly currentUserId = computed(() => this.auth.user()?.id ?? null);

  protected readonly qControl = this.fb.nonNullable.control('');
  protected readonly roleControl = this.fb.nonNullable.control<UserRole | ''>('');
  protected readonly activeControl = this.fb.nonNullable.control<'' | 'true' | 'false'>('');

  protected readonly items = signal<User[]>([]);
  protected readonly total = signal(0);
  protected readonly page = signal(1);
  protected readonly size = signal(10);
  protected readonly pages = signal(0);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly notice = signal<string | null>(null);

  protected readonly editing = signal<User | null>(null);
  protected readonly saving = signal(false);
  protected readonly saveError = signal<string | null>(null);

  protected readonly form = this.fb.nonNullable.group({
    full_name: [''],
    role: ['analyst' as UserRole, [Validators.required]],
    is_active: [true],
    // Optional: only sent when filled in, and then it resets the password.
    password: ['', [Validators.minLength(8), Validators.maxLength(72)]],
  });

  constructor() {
    this.qControl.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed())
      .subscribe(() => this.reload());
    this.roleControl.valueChanges.pipe(takeUntilDestroyed()).subscribe(() => this.reload());
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

    this.users
      .list({
        page: this.page(),
        size: this.size(),
        q: this.qControl.value || undefined,
        role: this.roleControl.value || undefined,
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

  /** True for the account you are signed in as — editing it is fine, locking it out is not. */
  protected isSelf(user: User): boolean {
    return user.id === this.currentUserId();
  }

  protected startEdit(user: User): void {
    this.saveError.set(null);
    this.form.reset({
      full_name: user.full_name ?? '',
      role: user.role,
      is_active: user.is_active,
      password: '',
    });
    this.editing.set(user);
  }

  protected cancel(): void {
    this.editing.set(null);
    this.saveError.set(null);
  }

  protected save(): void {
    const user = this.editing();
    if (!user || this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.saving.set(true);
    this.saveError.set(null);

    const value = this.form.getRawValue();

    // Only send a password when one was typed — an empty string would be
    // rejected, and PATCH only changes the fields it receives.
    const payload = {
      full_name: value.full_name.trim() || null,
      role: value.role,
      is_active: value.is_active,
      ...(value.password ? { password: value.password } : {}),
    };

    this.users.update(user.id, payload).subscribe({
      next: () => {
        this.saving.set(false);
        this.editing.set(null);
        this.notice.set(`${user.email} updated.`);
        this.load();
      },
      error: (err) => {
        this.saveError.set(apiErrorMessage(err));
        this.saving.set(false);
      },
    });
  }

  protected remove(user: User): void {
    if (this.isSelf(user)) {
      return;
    }
    if (!confirm(`Delete ${user.email}? This is a soft delete.`)) {
      return;
    }
    this.users.remove(user.id).subscribe({
      next: () => {
        this.notice.set(`${user.email} deleted.`);
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
