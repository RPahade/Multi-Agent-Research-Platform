import { PageQuery } from './common.model';

export type UserRole = 'admin' | 'analyst' | 'leadership';

export const USER_ROLES: UserRole[] = ['admin', 'analyst', 'leadership'];

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface UserCreate {
  email: string;
  password: string;
  full_name?: string | null;
  role?: UserRole;
}

/** PATCH sends only the fields that changed. */
export interface UserUpdate {
  full_name?: string | null;
  role?: UserRole;
  is_active?: boolean;
  password?: string;
}

export interface UserQuery extends PageQuery {
  role?: UserRole;
  is_active?: boolean;
  q?: string;
}

/* --- auth --- */

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type?: string;
}
