import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { authApi, meApi, userRolesApi } from "@/services/api";
import type { UserResponse, UserRoleResponse, EmployeeResponse } from "@/types";
import { Role } from "@/types";

interface AuthState {
  user: UserResponse | null;
  roles: UserRoleResponse[];
  employee: EmployeeResponse | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAdmin: boolean;
  isManager: boolean;
  isManagerOrAdmin: boolean;
  highestRole: Role;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    roles: [],
    employee: null,
    isLoading: true,
    isAuthenticated: false,
  });

  const loadUser = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setState((s) => ({ ...s, isLoading: false }));
      return;
    }

    try {
      const [userRes, rolesRes] = await Promise.all([
        meApi.getUser(),
        null as unknown, // roles need user id first
      ]);

      const user: UserResponse = userRes.data;

      const rolesResult = await meApi.getRoles().catch(() => null);
      const roles: UserRoleResponse[] = rolesResult?.data ?? [];

      let employee: EmployeeResponse | null = null;
      try {
        const empRes = await meApi.getEmployee();
        employee = empRes.data;
      } catch {
        // user may not have employee record (e.g. pure admin)
      }

      setState({
        user,
        roles,
        employee,
        isLoading: false,
        isAuthenticated: true,
      });
    } catch {
      localStorage.removeItem("access_token");
      setState({
        user: null,
        roles: [],
        employee: null,
        isLoading: false,
        isAuthenticated: false,
      });
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = async (email: string, password: string) => {
    const res = await authApi.login(email, password);
    localStorage.setItem("access_token", res.data.access_token);
    await loadUser();
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    setState({
      user: null,
      roles: [],
      employee: null,
      isLoading: false,
      isAuthenticated: false,
    });
  };

  const isAdmin = state.roles.some(
    (r) => r.role === Role.ADMIN && r.store_id === null
  );
  const isManager = state.roles.some((r) => r.role === Role.MANAGER);
  const isManagerOrAdmin = isAdmin || isManager;

  const highestRole = isAdmin
    ? Role.ADMIN
    : isManager
      ? Role.MANAGER
      : Role.EMPLOYEE;

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        logout,
        isAdmin,
        isManager,
        isManagerOrAdmin,
        highestRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
