import { Component } from '@angular/core';

import { Placeholder } from '../../shared/components/placeholder/placeholder';

@Component({
  selector: 'app-jobs-page',
  imports: [Placeholder],
  template: `
    <app-placeholder
      title="Research Jobs"
      note="Start a research run and watch its progress live."
    />
  `,
})
export class JobsPage {}
