import axios from "axios";

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
  create: (input_text: string, context_tables?: string[]) =>
    api.post("/ai-inputs", { input_text, context_tables }),
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
  proposeManual: (changes: object[], summary: string) =>
    api.post("/ai-proposals/propose/manual", { changes, summary }),
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
};

// Shifts
export const shiftsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get("/shifts", { params }),
};

// User Roles
export const userRolesApi = {
  getForUser: (userId: number) => api.get(`/user-roles/user/${userId}`),
};