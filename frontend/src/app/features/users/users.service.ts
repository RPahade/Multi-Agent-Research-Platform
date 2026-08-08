import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { Page, User, UserCreate, UserQuery, UserUpdate } from '../../core/models';
import { ApiService } from '../../core/services/api.service';

/** Calls for the /users endpoints. Admin-only — the backend answers 403 otherwise. */
@Injectable({ providedIn: 'root' })
export class UsersService {
  private readonly api = inject(ApiService);

  list(query: UserQuery = {}): Observable<Page<User>> {
    return this.api.getPage<User>('/users', {
      page: query.page,
      size: query.size,
      role: query.role,
      is_active: query.is_active,
      q: query.q,
    });
  }

  get(id: string): Observable<User> {
    return this.api.get<User>(`/users/${id}`);
  }

  create(payload: UserCreate): Observable<User> {
    return this.api.post<User>('/users', payload);
  }

  /** Only the provided fields change; sending `password` resets it. */
  update(id: string, payload: UserUpdate): Observable<User> {
    return this.api.patch<User>(`/users/${id}`, payload);
  }

  /** Soft delete on the backend. */
  remove(id: string): Observable<void> {
    return this.api.delete<void>(`/users/${id}`);
  }
}
