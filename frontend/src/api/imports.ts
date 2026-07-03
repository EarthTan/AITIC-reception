// frontend/src/api/imports.ts
import { apiClient } from "./client";
import type { ImportCommitResponse, ImportPreviewResponse } from "./types";

export async function previewImport(file: File): Promise<ImportPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post<ImportPreviewResponse>(
    "/import/preview",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return response.data;
}

export async function commitImport(previewId: string): Promise<ImportCommitResponse> {
  const response = await apiClient.post<ImportCommitResponse>("/import/commit", {
    preview_id: previewId,
  });
  return response.data;
}
