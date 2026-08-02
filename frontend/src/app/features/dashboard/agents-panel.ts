import { Component, OnInit, inject, signal } from '@angular/core';

import { Agent, McpStatus } from '../../core/models';
import { apiErrorMessage } from '../../core/services/api-error';
import { SystemService } from '../../core/services/system.service';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { StatusBadge } from '../../shared/components/status-badge/status-badge';
import { AgentsService } from '../agents/agents.service';

/**
 * Agent status: the configured agents, plus the MCP server that actually
 * serves their tools — an agent is only as available as its toolbox.
 */
@Component({
  selector: 'app-agents-panel',
  imports: [StatusBadge, EmptyState],
  templateUrl: './agents-panel.html',
  styleUrl: './agents-panel.scss',
})
export class AgentsPanel implements OnInit {
  private readonly agents = inject(AgentsService);
  private readonly system = inject(SystemService);

  protected readonly items = signal<Agent[]>([]);
  protected readonly mcp = signal<McpStatus | null>(null);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.error.set(null);

    this.agents.list({ page: 1, size: 20 }).subscribe({
      next: (result) => {
        this.items.set(result.items);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(apiErrorMessage(err));
        this.loading.set(false);
      },
    });

    // Reported separately — agents can be configured while MCP is unreachable.
    this.system.mcp().subscribe({
      next: (status) => this.mcp.set(status),
      error: () => this.mcp.set(null),
    });
  }
}
