import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { USER_ROLES, UserRole } from '../../core/models';
import { apiErrorMessage } from '../../core/services/api-error';
import { UsersService } from './users.service';

/**
 * Account registration.
 *
 * The backend has no public sign-up endpoint — `POST /users` is admin-only —
 * so registration is an administrator creating the account. The route is
 * guarded with roleGuard(['admin']).
 */
@Component({
  selector: 'app-create-user-page',
  imports: [ReactiveFormsModule],
  templateUrl: './create-user-page.html',
  styleUrl: './create-user-page.scss',
})
export class CreateUserPage {
  private readonly fb = inject(FormBuilder);
  private readonly users = inject(UsersService);

  readonly roles = USER_ROLES;
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly created = signal<string | null>(null);

  readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    full_name: [''],
    // The backend hashes with bcrypt, which caps the input at 72 bytes.
    password: ['', [Validators.required, Validators.minLength(8), Validators.maxLength(72)]],
    role: ['analyst' as UserRole, [Validators.required]],
  });

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.loading.set(true);
    this.error.set(null);
    this.created.set(null);

    const value = this.form.getRawValue();

    this.users
      .create({
        email: value.email,
        password: value.password,
        role: value.role,
        // Send null rather than an empty string for an omitted name.
        full_name: value.full_name.trim() || null,
      })
      .subscribe({
        next: (user) => {
          this.created.set(user.email);
          this.loading.set(false);
          this.form.reset({ role: 'analyst' });
        },
        error: (err) => {
          this.error.set(apiErrorMessage(err));
          this.loading.set(false);
        },
      });
  }

  showError(field: 'email' | 'password' | 'role'): boolean {
    const control = this.form.controls[field];
    return control.invalid && control.touched;
  }
}
