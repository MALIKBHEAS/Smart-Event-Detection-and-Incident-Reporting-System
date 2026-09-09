import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usersApi } from "../../api/endpoints/users";
import { authApi } from "../../api/endpoints/auth";

export function useUsersList() {
  return useQuery({ queryKey: ["users"], queryFn: usersApi.list });
}

export function useSetUserActive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, isActive }: { id: number; isActive: boolean }) => usersApi.setActive(id, isActive),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
}

export function useSetUserRoles() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, roles }: { id: number; roles: string[] }) => usersApi.setRoles(id, roles),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { username: string; email: string; password: string; role: string }) => authApi.register(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
}
