import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { User, UserCreate } from '../../core/models';
import { ApiService } from '../../core/services/api.service';

/**
 * Calls for the /users endpoints. Only account creation is needed so far —
 * the list/edit/delete calls arrive with the user management milestone.
 */
@Injectable({ providedIn: 'root' })
export class UsersService {
  private readonly api = inject(ApiService);

  /** Admin-only. The backend answers 403 for anyone else. */
  create(payload: UserCreate): Observable<User> {
    return this.api.post<User>('/users', payload);
  }
}
