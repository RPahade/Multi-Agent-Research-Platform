import { Component, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

interface NavLink {
  path: string;
  label: string;
}

/**
 * The application frame: sidebar + top bar + the routed page.
 *
 * Every link is visible for now. Milestone 10 adds authentication and hides
 * links the signed-in role is not allowed to use.
 */
@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
})
export class Shell {
  /** Sidebar visibility on narrow screens. */
  readonly menuOpen = signal(false);

  readonly links: NavLink[] = [
    { path: '/dashboard', label: 'Dashboard' },
    { path: '/documents', label: 'Documents' },
    { path: '/jobs', label: 'Research Jobs' },
    { path: '/reports', label: 'Reports' },
    { path: '/users', label: 'Users' },
    { path: '/agents', label: 'Agents' },
    { path: '/tools', label: 'Tools' },
  ];

  toggleMenu(): void {
    this.menuOpen.update((open) => !open);
  }

  closeMenu(): void {
    this.menuOpen.set(false);
  }
}
