// frontend/src/api/templates.ts
import { apiClient } from "./client";
import type { TemplateOut } from "./types";

export async function fetchTemplates(): Promise<TemplateOut[]> {
  const response = await apiClient.get<TemplateOut[]>("/templates");
  return response.data;
}

export async function updateTemplate(
  identityType: string,
  templateText: string
): Promise<TemplateOut> {
  const response = await apiClient.put<TemplateOut>(
    `/templates/${encodeURIComponent(identityType)}`,
    { template_text: templateText }
  );
  return response.data;
}
