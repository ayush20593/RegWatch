import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../api/client";
import type { AuthUser } from "../api/types";

export function useAuth() {
  const qc = useQueryClient();
  const query = useQuery<AuthUser>({
    queryKey: ["me"],
    queryFn: () => api.get("/auth/me").then((r) => r.data),
    retry: false,
  });

  const login = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      api.post("/auth/login", { email, password }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });

  const logout = useMutation({
    mutationFn: () => api.post("/auth/logout"),
    onSuccess: () => {
      qc.clear();
      window.location.href = "/login";
    },
  });

  return { user: query.data, isLoading: query.isLoading, login, logout };
}
