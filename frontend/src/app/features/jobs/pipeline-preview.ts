import { Component, OnInit, computed, inject, signal } from '@angular/core';

import { McpStatus } from '../../core/models';
import { SystemService } from '../../core/services/system.service';

/**
 * The tool pipeline, exactly as the backend runs it.
 *
 * Read-only on purpose: `build_pipeline()` takes no arguments and the `tools`
 * table is never consulted at runtime, so the sequence cannot be changed per
 * job. Showing it makes the fixed pipeline visible instead of implying control
 * the UI does not have.
 */
const PIPELINE = [
  {
    key: 'retrieval',
    name: 'Retrieval',
    detail: 'Embeds your topic and finds the closest passages in the selected documents.',
    mcpTool: null,
  },
  {
    key: 'research',
    name: 'Research',
    detail: 'Gathers findings from the retrieved sources.',
    mcpTool: 'web_research',
  },
  {
    key: 'synthesis',
    name: 'Synthesis',
    detail: 'The language model writes the cited report.',
    mcpTool: null,
  },
  {
    key: 'citation',
    name: 'Citation check',
    detail: 'Verifies claims against the sources.',
    mcpTool: 'verify_citations',
  },
  {
    key: 'compliance',
    name: 'Compliance',
    detail: 'Redacts personal data from the finished report.',
    mcpTool: 'redact_pii',
  },
];

@Component({
  selector: 'app-pipeline-preview',
  template: `
    <ol class="pipeline">
      @for (step of steps(); track step.key) {
        <li>
          <span class="step-head">
            <span class="step-name">{{ step.name }}</span>
            <code>{{ step.key }}</code>
            @if (step.viaMcp) {
              <span class="badge">MCP</span>
            } @else {
              <span class="badge badge-neutral">local</span>
            }
            @if (step.optional) {
              <span class="badge badge-warning">optional</span>
            }
          </span>
          <span class="muted detail">{{ step.detail }}</span>
        </li>
      }
    </ol>

    <p class="field-hint">
      Every research job runs these five tools in this order. The sequence is
      fixed by the backend and cannot be changed per job. A failure in a
      <strong>required</strong> step stops the run; an optional step's failure is
      recorded and the job continues.
    </p>
  `,
  styles: `
    .pipeline {
      margin: 0 0 var(--space-3);
      padding-left: var(--space-5);
    }
    .pipeline li {
      padding: var(--space-1) 0;
    }
    .step-head {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--space-2);
    }
    .step-name {
      font-weight: 500;
    }
    .detail {
      display: block;
      font-size: 13px;
    }
  `,
})
export class PipelinePreview implements OnInit {
  private readonly system = inject(SystemService);

  private readonly mcp = signal<McpStatus | null>(null);

  protected readonly steps = computed(() => {
    const status = this.mcp();
    const mcpOn = !!status?.enabled;

    return PIPELINE.map((step) => ({
      ...step,
      viaMcp: mcpOn && !!step.mcpTool,
      // The MCP citation tool is the only step declared optional, so citation
      // is only optional while MCP is serving it.
      optional: mcpOn && step.key === 'citation',
    }));
  });

  ngOnInit(): void {
    this.system.mcp().subscribe({
      next: (status) => this.mcp.set(status),
      error: () => this.mcp.set(null),
    });
  }
}
