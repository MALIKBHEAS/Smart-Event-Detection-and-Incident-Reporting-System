import { z } from "zod";

export const cameraSchema = z.object({
  name: z.string().min(1, "Name is required").max(128),
  rtsp_url: z.string().min(1, "RTSP URL is required").max(1024),
  location: z.string().max(255).optional().or(z.literal("")),
  enabled: z.boolean(),
});

export type CameraFormValues = z.infer<typeof cameraSchema>;
