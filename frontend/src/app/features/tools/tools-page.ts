import { Component } from '@angular/core';

import { Placeholder } from '../../shared/components/placeholder/placeholder';

@Component({
  selector: 'app-tools-page',
  imports: [Placeholder],
  template: `
    <app-placeholder
      title="Tools"
      note="Manage the tools an agent can call, and enable or disable them."
    />
  `,
})
export class ToolsPage {}
