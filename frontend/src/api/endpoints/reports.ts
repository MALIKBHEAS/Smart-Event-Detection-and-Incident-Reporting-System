import { apiClient } from "../client";
import type { PaginatedReports, Report, ReportInput, ReportListParams } from "../types";

export const reportsApi = {
  list: async (params: ReportListParams = {}): Promise<PaginatedReports> =>
    (await apiClient.get<PaginatedReports>("/reports", { params })).data,
  get: async (id: number): Promise<Report> => (await apiClient.get<Report>(`/reports/${id}`)).data,
  create: async (input: ReportInput): Promise<Report> => (await apiClient.post<Report>("/reports", input)).data,
  update: async (id: number, input: Partial<ReportInput>): Promise<Report> =>
    (await apiClient.put<Report>(`/reports/${id}`, input)).data,
  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/reports/${id}`);
  },
  downloadPdf: async (id: number): Promise<Blob> =>
    (await apiClient.get(`/reports/${id}/download/pdf`, { responseType: "blob" })).data,
  downloadCsv: async (id: number): Promise<Blob> =>
    (await apiClient.get(`/reports/${id}/download/csv`, { responseType: "blob" })).data,
};

/** Triggers a browser download for a blob the way a real <a download> click would. */
export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
