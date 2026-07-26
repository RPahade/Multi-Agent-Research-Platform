import { Component } from '@angular/core';

import { Placeholder } from '../../shared/components/placeholder/placeholder';

@Component({
  selector: 'app-reports-page',
  imports: [Placeholder],
  template: `
    <app-placeholder
      title="Reports"
      note="Read generated reports with their sections, citations and versions."
    />
  `,
})
export class ReportsPage {}
