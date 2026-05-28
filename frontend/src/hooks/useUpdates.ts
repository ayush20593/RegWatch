import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../api/client";
import type { UpdatesResponse, StatsResponse } from "../api/types";

interface Filters {
  regulator?: string[];
  risk_level?: string[];
  status?: string;
  limit?: number;
  offset?: number;
}

export function useUpdates(filters: Filters = {}) {
  const params = new URLSearchParams();
  if (filters.regulator) filters.regulator.forEach((r) => params.append("regulator", r));
  if (filters.risk_level) filters.risk_level.forEach((r) => params.append("risk_level", r));
  if (filters.status && filters.status !== "all") params.set("status", filters.status);
  if (filters.limit) params.set("limit", String(filters.limit));
  if (filters.offset) params.set("offset", String(filters.offset));

  return useQuery<UpdatesResponse>({
    queryKey: ["updates", filters],
    queryFn: () => api.get(`/updates?${params}`).then((r) => r.data),
    refetchInterval: 60_000,
  });
}

export function useStats() {
  return useQuery<StatsResponse>({
    queryKey: ["stats"],
    queryFn: () => api.get("/updates/stats").then((r) => r.data),
    refetchInterval: 60_000,
  });
}

export function useMarkReviewed() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.patch(`/updates/${id}/reviewed`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["updates"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });
}
