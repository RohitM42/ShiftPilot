// Enums

export enum Role {
  ADMIN = "ADMIN",
  MANAGER = "MANAGER",
  EMPLOYEE = "EMPLOYEE",
}

export enum EmploymentStatus {
  ACTIVE = "ACTIVE",
  LEAVER = "LEAVER",
  ON_LEAVE = "ON_LEAVE",
}

export enum ShiftStatus {
  DRAFT = "DRAFT",
  PUBLISHED = "PUBLISHED",
  CANCELLED = "CANCELLED",
}

export enum ShiftSource {
  MANUAL = "MANUAL",
  AI = "AI",
  IMPORT = "IMPORT",
}

export enum AvailabilityRuleType {
  AVAILABLE = "AVAILABLE",
  UNAVAILABLE = "UNAVAILABLE",
  PREFERRED = "PREFERRED",
}

export enum AIOutputStatus {
  COMPLETE = "COMPLETE",
  NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION",
  INVALID = "INVALID",
}

export enum ProposalType {
  AVAILABILITY = "AVAILABILITY",
  COVERAGE = "COVERAGE",
  ROLE_REQUIREMENT = "ROLE_REQUIREMENT",
}

export enum ProposalStatus {
  PENDING = "PENDING",
  APPROVED = "APPROVED",
  REJECTED = "REJECTED",
  CANCELLED = "CANCELLED",
}

export enum ProposalSource {
  AI = "AI",
  MANUAL = "MANUAL",
}

// Auth

export interface Token {
  access_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

// Users

export interface UserResponse {
  id: number;
  email: string;
  firstname: string;
  surname: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// User Roles

export interface UserRoleResponse {
  id: number;
  user_id: number;
  store_id: number | null;
  role: Role;
  created_at: string;
  updated_at: string;
}

// Employees

export interface EmployeeResponse {
  id: number;
  user_id: number;
  store_id: number;
  is_keyholder: boolean;
  is_manager: boolean;
  employment_status: EmploymentStatus;
  contracted_weekly_hours: number;
  dob: string;
  created_at: string;
  updated_at: string;
}

export interface EmployeeWithUserResponse extends EmployeeResponse {
  firstname: string;
  surname: string;
  email: string;
}

// Employee Departments

export interface EmployeeDepartmentResponse {
  employee_id: number;
  department_id: number;
  is_primary: boolean;
}

// Shifts

export interface ShiftResponse {
  id: number;
  store_id: number;
  department_id: number;
  employee_id: number;
  start_datetime_utc: string;
  end_datetime_utc: string;
  status: ShiftStatus;
  source: ShiftSource;
  created_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

// Availability Rules

export interface AvailabilityRuleResponse {
  id: number;
  employee_id: number;
  day_of_week: number;
  start_time_local: string | null;
  end_time_local: string | null;
  rule_type: AvailabilityRuleType;
  priority: number;
  active: boolean;
  updated_at: string | null;
}

export interface AvailabilityRuleCreate {
  employee_id: number;
  day_of_week: number;
  start_time_local?: string | null;
  end_time_local?: string | null;
  rule_type: AvailabilityRuleType;
  priority?: number;
  active?: boolean;
}

// Coverage Requirements

export interface CoverageRequirementResponse {
  id: number;
  store_id: number;
  department_id: number;
  day_of_week: number;
  start_time_local: string | null;
  end_time_local: string | null;
  min_staff: number;
  max_staff: number | null;
  active: boolean;
  created_at: string;
  updated_at: string;
  last_modified_by_user_id: number | null;
}

// Role Requirements

export interface RoleRequirementResponse {
  id: number;
  store_id: number;
  department_id: number | null;
  day_of_week: number | null;
  start_time_local: string;
  end_time_local: string;
  requires_manager: boolean;
  requires_keyholder: boolean;
  min_manager_count: number;
  active: boolean;
  created_at: string;
  updated_at: string;
  last_modified_by_user_id: number | null;
}

// AI Inputs

export interface AIInputCreate {
  input_text: string;
  context_tables?: string[] | null;
}

export interface AIInputResponse {
  id: number;
  req_by_user_id: number;
  input_text: string;
  context_tables: string[] | null;
  processed: boolean;
  created_at: string;
}

// AI Outputs

export interface AIOutputResponse {
  id: number;
  input_id: number;
  result_json: Record<string, unknown>;
  summary: string;
  status: AIOutputStatus;
  model_used: string | null;
  affects_user_id: number | null;
  created_at: string;
  updated_at: string;
}

// AI Proposals

export interface AIProposalResponse {
  id: number;
  ai_output_id: number;
  type: ProposalType;
  store_id: number | null;
  department_id: number | null;
  status: ProposalStatus;
  rejection_reason: string | null;
  last_actioned_by: number | null;
  created_at: string;
  updated_at: string;
}

// Departments (inferred from seed data)

export interface Department {
  id: number;
  name: string;
  code: string;
}

export interface DepartmentResponse {
  id: number;
  name: string;
  code: string;
  has_manager_role: boolean;
  active: boolean;
}

// Stores (inferred from seed data)

export interface Store {
  id: number;
  name: string;
  location: string;
  timezone: string;
}

export interface StoreResponse {
  id: number;
  name: string;
  location: string;
  allowed_shift_hours: number[];
  timezone: string;
  opening_time: string; // "HH:MM:SS" from Python time
  closing_time: string;
}

// Store Departments

export interface StoreDepartmentResponse {
  store_id: number;
  department_id: number;
}

// Shift with WTR violations (create/update response)

export interface ShiftWithViolationsResponse extends ShiftResponse {
  violations: string[];
}

// Schedule generation

export interface UnmetCoverageItem {
  department_id: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  min_staff: number;
}

export interface UnmetRoleItem {
  department_id: number | null;
  day_of_week: number | null;
  start_time: string;
  end_time: string;
  requires_keyholder: boolean;
  requires_manager: boolean;
  min_manager_count: number;
}

export interface GenerateScheduleResponse {
  success: boolean;
  shifts_created: number;
  shift_ids: number[];
  unmet_coverage: UnmetCoverageItem[];
  unmet_role_requirements: UnmetRoleItem[];
  unmet_contracted_hours: Record<string, number>; // str(employee_id) -> shortfall hours
  warnings: string[];
}

export interface PublishBulkResponse {
  published_count: number;
}

// Day of week helpers

export const DAY_NAMES = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
] as const;

export const DAY_NAMES_SHORT = [
  "Mon",
  "Tue",
  "Wed",
  "Thu",
  "Fri",
  "Sat",
  "Sun",
] as const;
