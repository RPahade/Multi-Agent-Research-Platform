import { Component } from '@angular/core';

import { Placeholder } from '../../shared/components/placeholder/placeholder';

@Component({
  selector: 'app-documents-page',
  imports: [Placeholder],
  template: `
    <app-placeholder
      title="Documents"
      note="Upload source documents and follow them through ingestion."
    />
  `,
})
export class DocumentsPage {}
