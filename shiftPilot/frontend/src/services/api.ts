import axios from "axios";
import type {
  StoreResponse,
  StoreDepartmentResponse,
  DepartmentResponse,
  LabourBudgetResponse,
} from "@/types";

const API_BASE = "/api";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;

// Auth
export const authApi = {
  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }),
};

// Me
export const meApi = {
  getUser: () => api.get("/users/me"),
  getRoles: () => api.get("/me/roles"),
  getEmployee: () => api.get("/me/employee"),
  getShifts: (params?: { start_date?: string; end_date?: string }) =>
    api.get("/me/shifts", { params }),
  getAvailabilityRules: () => api.get("/me/availability-rules"),
  getDepartments: () => api.get("/me/departments"),
  getAIInputs: () => api.get("/me/ai-inputs"),
  getAIOutputs: () => api.get("/me/ai-outputs"),
  getAIProposals: (status?: string) =>
    api.get("/me/ai-proposals", { params: status ? { status } : {} }),
};

// AI Inputs
export const aiInputsApi = {
  create: (input_text: string, context_tables?: string[], store_id?: number | null, as_preview = false) =>
    api.post("/ai-inputs", { input_text, context_tables, ...(store_id != null && { store_id }), as_preview }),
};

// AI Proposals
export const aiProposalsApi = {
  getPending: (type?: string) =>
    api.get("/ai-proposals/pending", { params: type ? { type } : {} }),
  getPendingByStore: (storeId: number, type?: string) =>
    api.get(`/ai-proposals/pending/store/${storeId}`, {
      params: type ? { type } : {},
    }),
  getByStore: (storeId: number, params?: { status?: string; type?: string }) =>
    api.get(`/ai-proposals/store/${storeId}`, { params }),
  getAll: (params?: { status?: string; type?: string }) =>
    api.get("/ai-proposals/all", { params }),
  approve: (id: number) => api.patch(`/ai-proposals/${id}/approve`),
  reject: (id: number, rejection_reason?: string) =>
    api.patch(`/ai-proposals/${id}/reject`, null, {
      params: rejection_reason ? { rejection_reason } : {},
    }),
  cancel: (id: number) => api.patch(`/ai-proposals/${id}/cancel`),
  confirmPreview: (outputId: number) => api.post(`/ai-proposals/from-output/${outputId}`),
  proposeManual: (changes: object[], summary: string) =>
    api.post("/ai-proposals/propose/manual", { changes, summary }),
  proposeManualScheduling: (
    intent_type: "COVERAGE" | "ROLE_REQUIREMENT",
    store_id: number,
    department_id: number | null,
    changes: object[],
    summary: string
  ) =>
    api.post("/ai-proposals/propose/manual/scheduling", {
      intent_type,
      store_id,
      department_id,
      changes,
      summary,
    }),
};

// Availability Rules
export const availabilityRulesApi = {
  getForEmployee: (employeeId: number) =>
    api.get(`/availability-rules/employee/${employeeId}`),
  create: (data: Record<string, unknown>) =>
    api.post("/availability-rules", data),
  update: (id: number, data: Record<string, unknown>) =>
    api.put(`/availability-rules/${id}`, data),
  delete: (id: number) => api.delete(`/availability-rules/${id}`),
};

// Coverage Requirements
export const coverageApi = {
  list: (params?: { store_id?: number; department_id?: number }) =>
    api.get("/coverage-requirements", { params }),
  create: (data: Record<string, unknown>) =>
    api.post("/coverage-requirements", data),
  update: (id: number, data: Record<string, unknown>) =>
    api.put(`/coverage-requirements/${id}`, data),
  delete: (id: number) => api.delete(`/coverage-requirements/${id}`),
};

// Role Requirements
export const roleRequirementsApi = {
  list: (params?: { store_id?: number }) =>
    api.get("/role-requirements", { params }),
  create: (data: Record<string, unknown>) =>
    api.post("/role-requirements", data),
  update: (id: number, data: Record<string, unknown>) =>
    api.put(`/role-requirements/${id}`, data),
  delete: (id: number) => api.delete(`/role-requirements/${id}`),
};

// Employees
export const employeesApi = {
  list: (storeId?: number) =>
    api.get("/employees", { params: storeId ? { store_id: storeId } : {} }),
  get: (id: number) => api.get(`/employees/${id}`),
  create: (data: {
    user_id: number;
    store_id: number;
    employment_status: string;
    contracted_weekly_hours: number;
    dob: string;
    is_keyholder?: boolean;
    is_manager?: boolean;
  }) => api.post("/employees", data),
};

// Shifts
export const shiftsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get("/shifts", { params }),
};

// Departments
export const departmentsApi = {
  list: () => api.get("/departments"),
};

// Departments (admin)
export const departmentsAdminApi = {
  list: (includeInactive = false) =>
    api.get<DepartmentResponse[]>('/departments', {
      params: { include_inactive: includeInactive },
    }),
  create: (data: { name: string; code: string; has_manager_role: boolean }) =>
    api.post<DepartmentResponse>('/departments', data),
  update: (id: number, data: { name?: string; code?: string; has_manager_role?: boolean }) =>
    api.put<DepartmentResponse>(`/departments/${id}`, data),
  deactivate: (id: number) =>
    api.delete<{ id: number; warnings: Array<{ employee_id: number; name: string }> }>(
      `/departments/${id}`
    ),
};

// Labour Budgets
export const labourBudgetsApi = {
  listForStore: (storeId: number) =>
    api.get<LabourBudgetResponse[]>('/labour-budgets', { params: { store_id: storeId } }),
  create: (data: {
    store_id: number;
    department_id: number;
    week_start_date: string;
    budget_hours: number;
  }) => api.post<LabourBudgetResponse>('/labour-budgets', data),
  update: (id: number, data: { budget_hours: number }) =>
    api.put<LabourBudgetResponse>(`/labour-budgets/${id}`, data),
};

// Users (admin)
export const usersApi = {
  list: (filter?: number | "unassigned") =>
    api.get("/users", {
      params: typeof filter === "number" ? { store_id: filter } : filter === "unassigned" ? { unassigned: true } : {},
    }),
  listUnassigned: () => api.get("/users/unassigned"),
  create: (data: { email: string; firstname: string; surname: string; password: string }) =>
    api.post("/users", data),
  update: (id: number, data: { email?: string; firstname?: string; surname?: string; is_active?: boolean }) =>
    api.put(`/users/${id}`, data),
  resetPassword: (id: number, new_password: string) =>
    api.post(`/users/${id}/reset-password`, { new_password }),
};

// User Roles
export const userRolesApi = {
  getForUser: (userId: number) => api.get(`/user-roles/user/${userId}`),
  add: (data: { user_id: number; role: string; store_id?: number | null }) =>
    api.post("/user-roles", data),
  remove: (roleId: number) => api.delete(`/user-roles/${roleId}`),
};

// Stores
export const storesApi = {
  list: () => api.get<StoreResponse[]>('/stores'),
  get: (id: number) => api.get<StoreResponse>(`/stores/${id}`),
  create: (data: { name: string; location: string; timezone: string; opening_time?: string; closing_time?: string }) =>
    api.post<StoreResponse>('/stores', data),
  update: (id: number, data: { name?: string; location?: string; timezone?: string; opening_time?: string; closing_time?: string }) =>
    api.put<StoreResponse>(`/stores/${id}`, data),
};

// Store Departments
export const storeDepartmentsApi = {
  listForStore: (storeId: number) =>
    api.get<StoreDepartmentResponse[]>(`/store-departments/store/${storeId}`),
  add: (storeId: number, departmentId: number) =>
    api.post('/store-departments', { store_id: storeId, department_id: departmentId }),
  remove: (storeId: number, departmentId: number) =>
    api.delete<{ warnings: Array<{ employee_id: number; name: string }> }>(
      `/store-departments/store/${storeId}/department/${departmentId}`
    ),
};

// Employee Departments
export const employeeDepartmentsApi = {
  listByStore: (storeId: number) =>
    api.get("/employee-departments", { params: { store_id: storeId } }),
};

// Schedule
export const scheduleApi = {
  generate: (payload: {
    store_id: number;
    week_start: string; // "YYYY-MM-DD"
    mode: "add" | "replace";
  }) => api.post("/schedule/generate", payload),
  publishBulk: (shiftIds: number[]) =>
    api.post("/schedule/publish-bulk", { shift_ids: shiftIds }),
  cancelBulk: (shiftIds: number[]) =>
    api.post("/schedule/cancel-bulk", { shift_ids: shiftIds }),
};