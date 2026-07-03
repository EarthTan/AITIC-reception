// frontend/src/pages/TemplatesPage.tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { fetchTemplates, updateTemplate } from "../api/templates";

export function TemplatesPage() {
  const queryClient = useQueryClient();
  const templatesQuery = useQuery({
    queryKey: queryKeys.templates(),
    queryFn: fetchTemplates,
  });
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  const updateMutation = useMutation({
    mutationFn: ({
      identityType,
      text,
    }: {
      identityType: string;
      text: string;
    }) => updateTemplate(identityType, text),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.templates() });
    },
  });

  return (
    <div>
      <h1>欢迎词模板</h1>
      <table>
        <thead>
          <tr>
            <th>身份类型</th>
            <th>模板文案</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {(templatesQuery.data ?? []).map((template) => {
            const draft =
              drafts[template.identity_type] ?? template.template_text;
            return (
              <tr key={template.id}>
                <td>{template.identity_type}</td>
                <td>
                  <input
                    value={draft}
                    onChange={(event) =>
                      setDrafts((current) => ({
                        ...current,
                        [template.identity_type]: event.target.value,
                      }))
                    }
                  />
                </td>
                <td>
                  <button
                    onClick={() =>
                      updateMutation.mutate({
                        identityType: template.identity_type,
                        text: draft,
                      })
                    }
                  >
                    保存
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
