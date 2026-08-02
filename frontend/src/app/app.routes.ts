import { Routes } from '@angular/router';

import { authGuard, guestGuard, roleGuard } from './core/guards/auth-guard';
import { Shell } from './layout/shell/shell';

/**
 * Every page is loaded lazily (loadComponent), so a route's code is only
 * downloaded when it is first visited.
 *
 * Two groups: /login stands alone, everything else renders inside the Shell and
 * requires a signed-in user. All three roles may READ every section, so only
 * user management is role-restricted here; write permissions are enforced
 * inside each screen (and by the backend, which always answers 403 itself).
 */
export const routes: Routes = [
  {
    path: 'login',
    title: 'Sign in',
    canActivate: [guestGuard],
    loadComponent: () =>
      import('./features/auth/login-page').then((m) => m.LoginPage),
  },
  {
    path: '',
    component: Shell,
    canActivate: [authGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        title: 'Dashboard',
        loadComponent: () =>
          import('./features/dashboard/dashboard-page').then((m) => m.DashboardPage),
      },
      {
        path: 'documents',
        title: 'Documents',
        loadComponent: () =>
          import('./features/documents/documents-page').then((m) => m.DocumentsPage),
      },
      {
        path: 'jobs',
        title: 'Research Jobs',
        loadComponent: () =>
          import('./features/jobs/jobs-page').then((m) => m.JobsPage),
      },
      {
        // Creating a job and uploading documents both require analyst or admin
        // (the backend's require_job_writer), so leadership must not get here.
        path: 'jobs/new',
        title: 'New research job',
        canActivate: [roleGuard(['admin', 'analyst'])],
        loadComponent: () =>
          import('./features/jobs/new-job-page').then((m) => m.NewJobPage),
      },
      {
        // Must stay AFTER 'jobs/new', or 'new' would be matched as an :id.
        // Readable by every role; the cancel button is gated inside the page.
        path: 'jobs/:id',
        title: 'Job progress',
        loadComponent: () =>
          import('./features/jobs/job-detail-page').then((m) => m.JobDetailPage),
      },
      {
        path: 'reports',
        title: 'Reports',
        loadComponent: () =>
          import('./features/reports/reports-page').then((m) => m.ReportsPage),
      },
      {
        path: 'users',
        title: 'Users',
        canActivate: [roleGuard(['admin'])],
        loadComponent: () =>
          import('./features/users/users-page').then((m) => m.UsersPage),
      },
      {
        // Registration: admin-only, because the backend has no public sign-up.
        path: 'users/new',
        title: 'Create user',
        canActivate: [roleGuard(['admin'])],
        loadComponent: () =>
          import('./features/users/create-user-page').then((m) => m.CreateUserPage),
      },
      {
        path: 'agents',
        title: 'Agents',
        loadComponent: () =>
          import('./features/agents/agents-page').then((m) => m.AgentsPage),
      },
      {
        path: 'tools',
        title: 'Tools',
        loadComponent: () =>
          import('./features/tools/tools-page').then((m) => m.ToolsPage),
      },
      {
        path: 'forbidden',
        title: 'Not allowed',
        loadComponent: () =>
          import('./features/forbidden/forbidden-page').then((m) => m.ForbiddenPage),
      },
    ],
  },
  {
    path: '**',
    title: 'Not found',
    loadComponent: () =>
      import('./features/not-found/not-found-page').then((m) => m.NotFoundPage),
  },
];
