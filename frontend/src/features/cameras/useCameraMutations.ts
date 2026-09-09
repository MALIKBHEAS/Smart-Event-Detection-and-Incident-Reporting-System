import { useMutation, useQueryClient } from "@tanstack/react-query";
import { camerasApi } from "../../api/endpoints/cameras";
import { workersApi } from "../../api/endpoints/workers";
import { qk } from "../../api/queries";
import type { CameraInput } from "../../api/types";

export function useCreateCamera() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CameraInput) => camerasApi.create(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.cameras }),
  });
}

export function useUpdateCamera() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: Partial<CameraInput> }) => camerasApi.update(id, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.cameras }),
  });
}

export function useDeleteCamera() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => camerasApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.cameras }),
  });
}

export function useStartWorker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cameraId: number) => workersApi.start(cameraId),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.workersHealth }),
  });
}

export function useStopWorker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cameraId: number) => workersApi.stop(cameraId),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.workersHealth }),
  });
}
