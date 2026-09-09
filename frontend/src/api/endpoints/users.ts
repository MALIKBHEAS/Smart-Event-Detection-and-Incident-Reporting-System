import { apiClient } from "../client";
import type { ManagedUser } from "../types";

export const usersApi = {
  list: async (): Promise<ManagedUser[]> => (await apiClient.get<ManagedUser[]>("/users")).data,
  get: async (id: number): Promise<ManagedUser> => (await apiClient.get<ManagedUser>(`/users/${id}`)).data,
  setActive: async (id: number, isActive: boolean): Promise<ManagedUser> =>
    (await apiClient.put<ManagedUser>(`/users/${id}/active`, { is_active: isActive })).data,
  setRoles: async (id: number, roles: string[]): Promise<ManagedUser> =>
    (await apiClient.put<ManagedUser>(`/users/${id}/roles`, { roles })).data,
};
