import { Component } from '@angular/core';

import { Placeholder } from '../../shared/components/placeholder/placeholder';

@Component({
  selector: 'app-users-page',
  imports: [Placeholder],
  template: `
    <app-placeholder
      title="Users"
      note="Create, edit and deactivate accounts. Admin only."
    />
  `,
})
export class UsersPage {}
