import { Component } from '@angular/core';

import { Placeholder } from '../../shared/components/placeholder/placeholder';

@Component({
  selector: 'app-agents-page',
  imports: [Placeholder],
  template: `
    <app-placeholder
      title="Agents"
      note="Configure the research agents: prompt, model and settings."
    />
  `,
})
export class AgentsPage {}
