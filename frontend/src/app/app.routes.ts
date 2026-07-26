import { Routes } from '@angular/router';

import { Shell } from './layout/shell/shell';

/**
 * Every page is loaded lazily (loadComponent), so a route's code is only
 * downloaded when it is first visited.
 *
 * Two groups: /login stands alone, everything else renders inside the Shell.
 * Route guards are added in the authentication milestone.
 */
export const routes: Routes = [
  {
    path: 'login',
    title: 'Sign in',
    loadComponent: () =>
      import('./features/auth/login-page').then((m) => m.LoginPage),
  },
  {
    path: '',
    component: Shell,
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
        path: 'reports',
        title: 'Reports',
        loadComponent: () =>
          import('./features/reports/reports-page').then((m) => m.ReportsPage),
      },
      {
        path: 'users',
        title: 'Users',
        loadComponent: () =>
          import('./features/users/users-page').then((m) => m.UsersPage),
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
    ],
  },
  {
    path: '**',
    title: 'Not found',
    loadComponent: () =>
      import('./features/not-found/not-found-page').then((m) => m.NotFoundPage),
  },
];
