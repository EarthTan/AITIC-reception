// frontend/src/api/types.ts
export type IdentityType =
  "企业领导" | "企业员工" | "学校老师" | "大学生" | "中小学生" | "政府官员";

export type TemplateIdentityType = IdentityType | "默认";

export type WelcomeSource = "ai" | "fallback_template";
export type EntrySource = "auto" | "manual";
export type VisitStatus =
  "pending" | "welcome_ready" | "card_written" | "verified" | "rejected";

export interface VisitOut {
  id: number;
  visit_date: string;
  session_time: string;
  name: string;
  phone: string | null;
  nationality: string | null;
  id_number: string | null;
  gender: string | null;
  organization: string | null;
  identity_type: IdentityType;
  welcome_text: string | null;
  welcome_source: WelcomeSource | null;
  entry_source: EntrySource;
  import_batch_id: string;
  status: VisitStatus;
  created_at: string;
  updated_at: string;
}

export interface VisitUpdate {
  name?: string;
  phone?: string;
  nationality?: string;
  gender?: string;
  organization?: string;
  identity_type?: IdentityType;
}

export interface ImportPreviewRow {
  row_number: number;
  data: Record<string, unknown>;
  errors: string[];
  is_valid: boolean;
}

export interface ImportPreviewResponse {
  preview_id: string;
  rows: ImportPreviewRow[];
  valid_count: number;
  invalid_count: number;
}

export interface ImportCommitResponse {
  import_batch_id: string;
  visit_ids: number[];
}

export interface VisitSummaryRow {
  visit_date: string;
  session_time: string;
  visit_count: number;
  visits: VisitOut[];
}

export interface TemplateOut {
  id: number;
  identity_type: TemplateIdentityType;
  template_text: string;
  updated_at: string;
}

export type WriteStatus = "success" | "failed" | "pending";

export interface CardWriteResult {
  visit_id: number;
  status: string;
  error_message: string | null;
}

export interface CardWriteLogOut {
  id: number;
  visit_id: number;
  card_uid: string | null;
  write_status: WriteStatus;
  error_message: string | null;
  written_at: string;
}

export type VerifyResult = "pass" | "fail";
export type FailReason = "name_mismatch" | "date_mismatch" | "card_not_found";

export interface VerifyLogOut {
  id: number;
  card_uid: string;
  visit_id: number | null;
  verify_result: VerifyResult;
  fail_reason: FailReason | null;
  verified_at: string;
}

export type LogModule =
  | "registration"
  | "ai_writeup"
  | "card_write"
  | "verify"
  | "led"
  | "tts"
  | "system";
export type LogStatus = "success" | "failure" | "warning";

export interface WorkLogOut {
  id: number;
  module: LogModule;
  action: string;
  status: LogStatus;
  detail: string | null;
  created_at: string;
}

export type AdapterHealthStatus = "online" | "offline" | "error";

export interface AdapterStatusOut {
  adapter_name: string;
  status: AdapterHealthStatus;
  last_heartbeat: string;
  detail: string | null;
}

export interface SettingsOut {
  excel_watch_dir: string;
  ai_provider: string;
  has_ai_api_key: boolean;
  cors_origins: string[];
  message?: string | null;
}

export interface SettingsUpdate {
  excel_watch_dir?: string;
  ai_provider?: string;
  ai_api_key?: string;
}

export type RealtimeEventType =
  | "card.verify.passed"
  | "card.verify.failed"
  | "adapter.heartbeat"
  | "led.content";

export interface LEDContent {
  name: string;
  welcome_text: string;
  is_rejection: boolean;
  reason: string;
}

export interface RealtimeEvent {
  type: RealtimeEventType;
  timestamp: string;
  payload:
    | { visit_id: number; card_uid: string }
    | { adapter_name: string; status: string }
    | LEDContent;
}
