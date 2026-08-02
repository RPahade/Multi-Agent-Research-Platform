import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { UserRole } from '../models';
import { AuthService } from '../services/auth.service';

/**
 * Requires a signed-in user. Remembers where they were heading so login can
 * send them back there.
 */
export const authGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isAuthenticated()) {
    return true;
  }

  return router.createUrlTree(['/login'], {
    queryParams: { returnUrl: state.url },
  });
};

/**
 * Requires one of the given roles. Use it after authGuard:
 *   canActivate: [authGuard, roleGuard(['admin'])]
 *
 * This is a convenience only — the backend enforces RBAC itself and answers
 * 403 regardless of what the UI allows.
 */
export const roleGuard = (allowed: UserRole[]): CanActivateFn => {
  return () => {
    const auth = inject(AuthService);
    const router = inject(Router);
    const role = auth.role();

    if (role && allowed.includes(role)) {
      return true;
    }

    return router.createUrlTree(['/forbidden']);
  };
};

/** Keeps an already signed-in user off the login screen. */
export const guestGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  return auth.isAuthenticated() ? router.createUrlTree(['/dashboard']) : true;
};
