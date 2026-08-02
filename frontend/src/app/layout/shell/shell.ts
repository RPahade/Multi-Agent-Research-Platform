import { Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { UserRole } from '../../core/models';
import { AuthService } from '../../core/services/auth.service';

interface NavLink {
  path: string;
  label: string;
  /** Roles allowed to see the link. Omitted = every signed-in role. */
  roles?: UserRole[];
}

/** Sidebar + top bar + the routed page. */
@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
})
export class Shell {
  protected readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  /** Sidebar visibility on narrow screens. */
  readonly menuOpen = signal(false);
  readonly signingOut = signal(false);

  /**
   * All three roles can read every section, so only user management is
   * restricted. Write actions are hidden inside each screen, not here.
   */
  private readonly allLinks: NavLink[] = [
    { path: '/dashboard', label: 'Dashboard' },
    { path: '/documents', label: 'Documents' },
    { path: '/jobs', label: 'Research Jobs' },
    { path: '/jobs/new', label: 'New research', roles: ['admin', 'analyst'] },
    { path: '/reports', label: 'Reports' },
    { path: '/users', label: 'Users', roles: ['admin'] },
    { path: '/users/new', label: 'Create user', roles: ['admin'] },
    { path: '/agents', label: 'Agents' },
    { path: '/tools', label: 'Tools' },
  ];

  /** Only the links the signed-in role is allowed to see. */
  readonly links = computed(() => {
    const role = this.auth.role();
    return this.allLinks.filter((link) => !link.roles || (role && link.roles.includes(role)));
  });

  toggleMenu(): void {
    this.menuOpen.update((open) => !open);
  }

  closeMenu(): void {
    this.menuOpen.set(false);
  }

  signOut(): void {
    this.signingOut.set(true);
    this.auth.logout().subscribe({
      next: () => this.router.navigate(['/login']),
      error: () => this.router.navigate(['/login']),
    });
  }
}
