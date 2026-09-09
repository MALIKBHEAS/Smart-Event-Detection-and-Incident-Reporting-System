import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { reportsApi } from "../../api/endpoints/reports";
import type { ReportInput, ReportListParams } from "../../api/types";

export const reportsQueryKey = (params: ReportListParams) => ["reports", params] as const;
export const reportQueryKey = (id: number) => ["reports", id] as const;

export function useReportsList(params: ReportListParams) {
  return useQuery({
    queryKey: reportsQueryKey(params),
    queryFn: () => reportsApi.list(params),
  });
}

export function useReport(id: number | null) {
  return useQuery({
    queryKey: reportQueryKey(id ?? -1),
    queryFn: () => reportsApi.get(id as number),
    enabled: id !== null,
  });
}

export function useCreateReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ReportInput) => reportsApi.create(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reports"] }),
  });
}

export function useUpdateReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: Partial<ReportInput> }) => reportsApi.update(id, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reports"] }),
  });
}

export function useDeleteReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => reportsApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reports"] }),
  });
}
