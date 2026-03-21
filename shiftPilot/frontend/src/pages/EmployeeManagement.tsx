import { useState, useEffect, useMemo, useCallback } from "react";
import { Search, Pencil, UserPlus, X, Plus, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";
import api from "@/services/api";
import { usersApi, employeesApi } from "@/services/api";
import { EmploymentStatus, Role } from "@/types";
import type {
  EmployeeDepartmentResponse,
  UserResponse,
  StoreResponse,
  UserRoleResponse,
} from "@/types";

// ── Types ────────────────────────────────────────────────────────────

interface EmployeeWithUser {
  id: number;
  user_id: number;
  store_id: number;
  is_keyholder: boolean;
  is_manager: boolean;
  employment_status: EmploymentStatus;
  contracted_weekly_hours: number;
  dob: string;
  firstname: string;
  surname: string;
  email: string;
}

interface DeptOption {
  id: number;
  name: string;
}

interface DeptAssignment {
  department_id: number;
  is_primary: boolean;
}

interface FormState {
  firstname: string;
  surname: string;
  dob: string;
  contracted_weekly_hours: number;
  is_keyholder: boolean;
  is_manager: boolean;
  employment_status: EmploymentStatus;
  store_id: number;
}

// ── Helpers ──────────────────────────────────────────────────────────

function capitalizeName(s: string): string {
  if (!s) return s;
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

// ── Status helpers ───────────────────────────────────────────────────

const STATUS_VARIANT: Record<EmploymentStatus, "success" | "destructive" | "warning"> = {
  [EmploymentStatus.ACTIVE]: "success",
  [EmploymentStatus.LEAVER]: "destructive",
  [EmploymentStatus.ON_LEAVE]: "warning",
};

const STATUS_LABEL: Record<EmploymentStatus, string> = {
  [EmploymentStatus.ACTIVE]: "Active",
  [EmploymentStatus.LEAVER]: "Leaver",
  [EmploymentStatus.ON_LEAVE]: "On Leave",
};

const STATUS_OPTIONS: { value: EmploymentStatus; label: string }[] = [
  { value: EmploymentStatus.ACTIVE, label: "Active" },
  { value: EmploymentStatus.ON_LEAVE, label: "On Leave" },
  { value: EmploymentStatus.LEAVER, label: "Leaver" },
];

// ── Shared form helpers ──────────────────────────────────────────────

function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}

function FormInput({
  value,
  onChange,
  type = "text",
}: {
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
    />
  );
}

function ReadOnly({ value }: { value: string }) {
  return (
    <div className="rounded-md border bg-muted/50 px-3 py-2 text-sm text-muted-foreground">
      {value}
    </div>
  );
}

function FormSelect({
  value,
  options,
  onChange,
}: {
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer select-none">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative inline-flex h-5 w-9 items-center rounded-full transition-colors cursor-pointer",
          checked ? "bg-primary" : "bg-border"
        )}
      >
        <span
          className={cn(
            "inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform",
            checked ? "translate-x-[1.125rem]" : "translate-x-0.5"
          )}
        />
      </button>
      <span className="text-sm">{label}</span>
    </label>
  );
}

// ── Add Employee Panel ────────────────────────────────────────────────

interface AddEmployeePanelProps {
  stores: StoreResponse[];
  allDepts: DeptOption[];
  defaultStoreId?: number;
  onClose: () => void;
  onCreated: () => void;
}

function AddEmployeePanel({
  stores,
  allDepts,
  defaultStoreId,
  onClose,
  onCreated,
}: AddEmployeePanelProps) {
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [storeId, setStoreId] = useState<string>(defaultStoreId ? String(defaultStoreId) : "");
  const [status, setStatus] = useState<EmploymentStatus>(EmploymentStatus.ACTIVE);
  const [hours, setHours] = useState("20");
  const [dob, setDob] = useState("");
  const [isKeyholder, setIsKeyholder] = useState(false);
  const [isManager, setIsManager] = useState(false);
  const [depts, setDepts] = useState<DeptAssignment[]>([]);
  const [addDeptId, setAddDeptId] = useState<number | "">("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      setLoadingUsers(true);
      try {
        const res = await usersApi.listUnassigned();
        setUsers(res.data as UserResponse[]);
      } finally {
        setLoadingUsers(false);
      }
    };
    load();
  }, []);

  const availableDepts = allDepts.filter(
    (d) => !depts.some((assigned) => assigned.department_id === d.id)
  );

  const addDept = () => {
    if (addDeptId === "") return;
    setDepts((prev) => [
      ...prev,
      { department_id: addDeptId as number, is_primary: prev.length === 0 },
    ]);
    setAddDeptId("");
  };

  const removeDept = (deptId: number) => {
    setDepts((prev) => {
      const next = prev.filter((d) => d.department_id !== deptId);
      if (next.length > 0 && !next.some((d) => d.is_primary)) next[0].is_primary = true;
      return next;
    });
  };

  const setPrimary = (deptId: number) => {
    setDepts((prev) => prev.map((d) => ({ ...d, is_primary: d.department_id === deptId })));
  };

  const deptName = (deptId: number) =>
    allDepts.find((d) => d.id === deptId)?.name ?? `Dept ${deptId}`;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId || !storeId || !dob) return;
    setSubmitting(true);
    setError("");
    try {
      const empRes = await employeesApi.create({
        user_id: Number(selectedUserId),
        store_id: Number(storeId),
        employment_status: status,
        contracted_weekly_hours: Number(hours),
        dob,
        is_keyholder: isKeyholder,
        is_manager: isManager,
      });
      const newEmpId = (empRes.data as { id: number }).id;
      for (const dept of depts) {
        await api.post("/employee-departments", {
          employee_id: newEmpId,
          department_id: dept.department_id,
          is_primary: dept.is_primary,
        });
      }
      onCreated();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to create employee");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="p-5 space-y-4 sticky top-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold">Add Employee</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Link a user account to a store as an employee.
          </p>
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground shrink-0">
          <X size={18} />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-xs font-medium text-muted-foreground">User account</label>
          {loadingUsers ? (
            <p className="text-sm text-muted-foreground mt-1">Loading users…</p>
          ) : users.length === 0 ? (
            <p className="text-sm text-muted-foreground mt-1">
              No users available — all existing users already have employee records.
            </p>
          ) : (
            <select
              value={selectedUserId}
              onChange={(e) => setSelectedUserId(e.target.value)}
              required
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">Select a user…</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.firstname} {u.surname} ({u.email})
                </option>
              ))}
            </select>
          )}
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground">Store</label>
          <select
            value={storeId}
            onChange={(e) => setStoreId(e.target.value)}
            required
            disabled={!!defaultStoreId}
            className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring disabled:opacity-60"
          >
            <option value="">Select a store…</option>
            {stores.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground">Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as EmploymentStatus)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            >
              {Object.values(EmploymentStatus).map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Weekly hours</label>
            <input
              type="number"
              value={hours}
              onChange={(e) => setHours(e.target.value)}
              min={1}
              max={48}
              required
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground">Date of birth</label>
          <input
            type="date"
            value={dob}
            onChange={(e) => setDob(e.target.value)}
            required
            className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="flex gap-6 pt-1">
          <Toggle label="Keyholder" checked={isKeyholder} onChange={setIsKeyholder} />
          <Toggle label="Manager" checked={isManager} onChange={setIsManager} />
        </div>

        {/* Department assignments */}
        <div className="border-t pt-4 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Department Assignments
          </p>

          {depts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No departments assigned yet.</p>
          ) : (
            <div className="space-y-2">
              {depts.map((d) => (
                <div
                  key={d.department_id}
                  className="flex items-center justify-between rounded-md border px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{deptName(d.department_id)}</span>
                    {d.is_primary && <Badge variant="default">Primary</Badge>}
                  </div>
                  <div className="flex items-center gap-1">
                    {!d.is_primary && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs gap-1"
                        onClick={() => setPrimary(d.department_id)}
                      >
                        <Star size={12} /> Primary
                      </Button>
                    )}
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                      onClick={() => removeDept(d.department_id)}
                    >
                      <X size={14} />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {availableDepts.length > 0 && (
            <div className="flex items-center gap-2">
              <select
                value={addDeptId}
                onChange={(e) =>
                  setAddDeptId(e.target.value === "" ? "" : Number(e.target.value))
                }
                className="rounded-md border bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring flex-1"
              >
                <option value="">Select department…</option>
                {availableDepts.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="gap-1"
                onClick={addDept}
                disabled={addDeptId === ""}
              >
                <Plus size={14} /> Add
              </Button>
            </div>
          )}
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={submitting || users.length === 0}>
            {submitting ? "Adding…" : "Add Employee"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

// ── Employee Edit Panel ──────────────────────────────────────────────

interface EmployeeEditPanelProps {
  employeeId: number;
  isAdmin: boolean;
  stores: StoreResponse[];
  allDepts: DeptOption[];
  onClose: () => void;
  onSaved: () => void;
}

function EmployeeEditPanel({
  employeeId,
  isAdmin,
  stores,
  allDepts,
  onClose,
  onSaved,
}: EmployeeEditPanelProps) {
  const [employee, setEmployee] = useState<EmployeeWithUser | null>(null);
  const [form, setFormState] = useState<FormState | null>(null);
  const [depts, setDepts] = useState<DeptAssignment[]>([]);
  const [initialDepts, setInitialDepts] = useState<DeptAssignment[]>([]);
  const [userRoles, setUserRoles] = useState<UserRoleResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [addDeptId, setAddDeptId] = useState<number | "">("");

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [empRes, empDeptsRes] = await Promise.all([
          api.get(`/employees/${employeeId}`),
          api.get(`/employee-departments/employee/${employeeId}`),
        ]);

        const emp: EmployeeWithUser = empRes.data;
        const empDepts: EmployeeDepartmentResponse[] = empDeptsRes.data;
        const assignments = empDepts.map((d) => ({
          department_id: d.department_id,
          is_primary: d.is_primary,
        }));

        setEmployee(emp);
        setFormState({
          firstname: emp.firstname,
          surname: emp.surname,
          dob: emp.dob,
          contracted_weekly_hours: emp.contracted_weekly_hours,
          is_keyholder: emp.is_keyholder,
          is_manager: emp.is_manager,
          employment_status: emp.employment_status,
          store_id: emp.store_id,
        });
        setDepts(assignments);
        setInitialDepts(assignments.map((a) => ({ ...a })));

        if (isAdmin) {
          const rolesRes = await api.get(`/user-roles/user/${emp.user_id}`);
          setUserRoles(rolesRes.data);
        }
      } catch {
        setError("Failed to load employee");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [employeeId, isAdmin]);

  const isDirty = useMemo(() => {
    if (!form || !employee) return false;
    const formChanged =
      form.firstname !== employee.firstname ||
      form.surname !== employee.surname ||
      form.dob !== employee.dob ||
      form.contracted_weekly_hours !== employee.contracted_weekly_hours ||
      form.is_keyholder !== employee.is_keyholder ||
      form.is_manager !== employee.is_manager ||
      form.employment_status !== employee.employment_status ||
      form.store_id !== employee.store_id;
    const deptsChanged =
      JSON.stringify([...depts].sort((a, b) => a.department_id - b.department_id)) !==
      JSON.stringify([...initialDepts].sort((a, b) => a.department_id - b.department_id));
    return formChanged || deptsChanged;
  }, [form, employee, depts, initialDepts]);

  const setField = useCallback(<K extends keyof FormState>(key: K, value: FormState[K]) => {
    setFormState((f) => (f ? { ...f, [key]: value } : f));
  }, []);

  const addDept = () => {
    if (addDeptId === "" || depts.some((d) => d.department_id === addDeptId)) return;
    setDepts((prev) => [
      ...prev,
      { department_id: addDeptId as number, is_primary: prev.length === 0 },
    ]);
    setAddDeptId("");
  };

  const removeDept = (deptId: number) => {
    setDepts((prev) => {
      const next = prev.filter((d) => d.department_id !== deptId);
      if (next.length > 0 && !next.some((d) => d.is_primary)) {
        next[0].is_primary = true;
      }
      return next;
    });
  };

  const setPrimary = (deptId: number) => {
    setDepts((prev) => prev.map((d) => ({ ...d, is_primary: d.department_id === deptId })));
  };

  const deptName = useCallback(
    (deptId: number) => allDepts.find((d) => d.id === deptId)?.name ?? `Dept ${deptId}`,
    [allDepts]
  );

  const availableDepts = useMemo(() => {
    const assigned = new Set(depts.map((d) => d.department_id));
    return allDepts.filter((d) => !assigned.has(d.id));
  }, [allDepts, depts]);

  const handleCancel = () => {
    if (isDirty) {
      if (!window.confirm("You have unsaved changes. Are you sure you want to close?")) return;
    }
    onClose();
  };

  const handleSave = async () => {
    if (!form || !employee) return;

    setSaving(true);
    setError(null);

    try {
      // 1. Department additions
      const initialIds = new Set(initialDepts.map((d) => d.department_id));
      const currentIds = new Set(depts.map((d) => d.department_id));

      const added = depts.filter((d) => !initialIds.has(d.department_id));
      const removed = initialDepts.filter((d) => !currentIds.has(d.department_id));

      for (const dept of added) {
        await api.post("/employee-departments", {
          employee_id: employeeId,
          department_id: dept.department_id,
          is_primary: dept.is_primary,
        });
      }

      // 2. Set primary if changed
      const newPrimary = depts.find((d) => d.is_primary);
      const oldPrimary = initialDepts.find((d) => d.is_primary);
      if (newPrimary && newPrimary.department_id !== oldPrimary?.department_id) {
        await api.put(
          `/employee-departments/employee/${employeeId}/department/${newPrimary.department_id}/set-primary`
        );
      }

      // 3. Department removals
      for (const dept of removed) {
        await api.delete(
          `/employee-departments/employee/${employeeId}/department/${dept.department_id}`
        );
      }

      // 4. Update employee fields
      const empUpdate: Record<string, unknown> = {};
      if (form.contracted_weekly_hours !== employee.contracted_weekly_hours)
        empUpdate.contracted_weekly_hours = form.contracted_weekly_hours;
      if (form.dob !== employee.dob) empUpdate.dob = form.dob;
      if (form.is_keyholder !== employee.is_keyholder)
        empUpdate.is_keyholder = form.is_keyholder;
      if (isAdmin) {
        if (form.is_manager !== employee.is_manager) empUpdate.is_manager = form.is_manager;
        if (form.employment_status !== employee.employment_status)
          empUpdate.employment_status = form.employment_status;
        if (form.store_id !== employee.store_id) empUpdate.store_id = form.store_id;
      }
      if (Object.keys(empUpdate).length > 0) {
        await api.put(`/employees/${employeeId}`, empUpdate);
      }

      // 5. Update user fields (admin only)
      if (isAdmin) {
        const userUpdate: Record<string, unknown> = {};
        if (form.firstname !== employee.firstname) userUpdate.firstname = form.firstname;
        if (form.surname !== employee.surname) userUpdate.surname = form.surname;
        if (Object.keys(userUpdate).length > 0) {
          await api.put(`/users/${employee.user_id}`, userUpdate);
        }
      }

      // 6. Sync is_manager role (admin only)
      if (isAdmin && form.is_manager !== employee.is_manager) {
        const existingManagerRole = userRoles.find(
          (r) => r.role === Role.MANAGER && r.store_id === employee.store_id
        );
        if (form.is_manager && !existingManagerRole) {
          await api.post("/user-roles", {
            user_id: employee.user_id,
            store_id: employee.store_id,
            role: Role.MANAGER,
          });
        } else if (!form.is_manager && existingManagerRole) {
          await api.delete(`/user-roles/${existingManagerRole.id}`);
        }
      }

      // Reload to sync local state (clears dirty tracking)
      const empRes = await api.get(`/employees/${employeeId}`);
      const emp: EmployeeWithUser = empRes.data;
      setEmployee(emp);
      setFormState({
        firstname: emp.firstname,
        surname: emp.surname,
        dob: emp.dob,
        contracted_weekly_hours: emp.contracted_weekly_hours,
        is_keyholder: emp.is_keyholder,
        is_manager: emp.is_manager,
        employment_status: emp.employment_status,
        store_id: emp.store_id,
      });
      setInitialDepts(depts.map((d) => ({ ...d })));

      onSaved();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to save changes");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card className="p-5 sticky top-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold">Edit Employee</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X size={18} />
          </button>
        </div>
        <p className="text-sm text-muted-foreground">Loading…</p>
      </Card>
    );
  }

  if (!employee || !form) return null;

  return (
    <div className="space-y-4 sticky top-4">
      {/* Header */}
      <Card className="p-5">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h2 className="text-base font-semibold truncate">
              {employee.firstname} {employee.surname}
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">Employee #{employee.id}</p>
          </div>
          <button
            onClick={handleCancel}
            className="text-muted-foreground hover:text-foreground shrink-0"
          >
            <X size={18} />
          </button>
        </div>
        {error && (
          <div className="mt-3 rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}
      </Card>

      {/* Personal Information */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Personal Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <FieldGroup label="First name">
              {isAdmin ? (
                <FormInput
                  value={form.firstname}
                  onChange={(v) => setField("firstname", capitalizeName(v))}
                />
              ) : (
                <ReadOnly value={form.firstname} />
              )}
            </FieldGroup>
            <FieldGroup label="Surname">
              {isAdmin ? (
                <FormInput
                  value={form.surname}
                  onChange={(v) => setField("surname", capitalizeName(v))}
                />
              ) : (
                <ReadOnly value={form.surname} />
              )}
            </FieldGroup>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <FieldGroup label="Date of birth">
              <FormInput
                type="date"
                value={form.dob}
                onChange={(v) => setField("dob", v)}
              />
            </FieldGroup>
            <FieldGroup label="Email">
              <ReadOnly value={employee.email} />
            </FieldGroup>
          </div>
        </CardContent>
      </Card>

      {/* Employment Details */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Employment Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <FieldGroup label="Contracted hours (weekly)">
              <FormInput
                type="number"
                value={form.contracted_weekly_hours.toString()}
                onChange={(v) => setField("contracted_weekly_hours", parseInt(v) || 0)}
              />
            </FieldGroup>
            <FieldGroup label="Employment status">
              {isAdmin ? (
                <FormSelect
                  value={form.employment_status}
                  options={STATUS_OPTIONS}
                  onChange={(v) => setField("employment_status", v as EmploymentStatus)}
                />
              ) : (
                <Badge variant={STATUS_VARIANT[form.employment_status]} className="mt-1">
                  {STATUS_OPTIONS.find((o) => o.value === form.employment_status)?.label}
                </Badge>
              )}
            </FieldGroup>
          </div>

          {isAdmin && (
            <FieldGroup label="Store">
              <FormSelect
                value={form.store_id.toString()}
                options={stores.map((s) => ({ value: s.id.toString(), label: s.name }))}
                onChange={(v) => setField("store_id", parseInt(v))}
              />
            </FieldGroup>
          )}

          <div className="flex gap-6 pt-1">
            <Toggle
              label="Keyholder"
              checked={form.is_keyholder}
              onChange={(v) => setField("is_keyholder", v)}
            />
            {isAdmin ? (
              <Toggle
                label="Manager"
                checked={form.is_manager}
                onChange={(v) => setField("is_manager", v)}
              />
            ) : (
              form.is_manager && (
                <span className="text-sm text-muted-foreground flex items-center gap-2">
                  <span className="w-4 h-4 rounded border bg-primary/20 flex items-center justify-center text-primary text-xs">
                    ✓
                  </span>
                  Manager
                </span>
              )
            )}
          </div>
        </CardContent>
      </Card>

      {/* Department Assignments */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Department Assignments</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {depts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No departments assigned</p>
          ) : (
            <div className="space-y-2">
              {depts.map((d) => (
                <div
                  key={d.department_id}
                  className="flex items-center justify-between rounded-md border px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{deptName(d.department_id)}</span>
                    {d.is_primary && <Badge variant="default">Primary</Badge>}
                  </div>
                  <div className="flex items-center gap-1">
                    {!d.is_primary && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs gap-1"
                        onClick={() => setPrimary(d.department_id)}
                        title="Set as primary"
                      >
                        <Star size={12} /> Primary
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                      onClick={() => removeDept(d.department_id)}
                    >
                      <X size={14} />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {availableDepts.length > 0 && (
            <div className="flex items-center gap-2 pt-1">
              <select
                value={addDeptId}
                onChange={(e) =>
                  setAddDeptId(e.target.value === "" ? "" : Number(e.target.value))
                }
                className="rounded-md border bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring flex-1"
              >
                <option value="">Select department…</option>
                {availableDepts.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
              <Button
                size="sm"
                variant="outline"
                className="gap-1"
                onClick={addDept}
                disabled={addDeptId === ""}
              >
                <Plus size={14} /> Add
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex items-center justify-end gap-3 pb-6">
        <Button variant="outline" size="sm" onClick={handleCancel}>
          Cancel
        </Button>
        <Button size="sm" onClick={handleSave} disabled={!isDirty || saving}>
          {saving ? "Saving…" : "Save changes"}
        </Button>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────

export default function EmployeeManagement() {
  const { isAdmin, isManagerOrAdmin, employee: currentEmployee } = useAuth();

  const [employees, setEmployees] = useState<EmployeeWithUser[]>([]);
  const [empDepts, setEmpDepts] = useState<Map<number, EmployeeDepartmentResponse[]>>(new Map());
  const [departments, setDepartments] = useState<DeptOption[]>([]);
  const [stores, setStores] = useState<StoreResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  // Filters
  const [search, setSearch] = useState("");
  const [storeFilter, setStoreFilter] = useState<number | "all">("all");
  const [deptFilter, setDeptFilter] = useState<number | "all">("all");

  // Panel
  const [panelMode, setPanelMode] = useState<"create" | "edit" | null>(null);
  const [activeEmployeeId, setActiveEmployeeId] = useState<number | null>(null);

  const managerStoreId = currentEmployee?.store_id;

  // Load reference data
  useEffect(() => {
    const fetchRef = async () => {
      try {
        const [deptRes, storeRes] = await Promise.all([
          api.get("/departments"),
          api.get("/stores"),
        ]);
        setDepartments(deptRes.data);
        setStores(storeRes.data);
      } catch {
        // silent
      }
    };
    fetchRef();
  }, []);

  // Manager default dept filter
  useEffect(() => {
    if (!isAdmin && currentEmployee && empDepts.size > 0) {
      const myDepts = empDepts.get(currentEmployee.id);
      const primary = myDepts?.find((d) => d.is_primary);
      if (primary) setDeptFilter(primary.department_id);
    }
  }, [isAdmin, currentEmployee, empDepts]);

  // Load employees
  useEffect(() => {
    const fetchEmployees = async () => {
      setLoading(true);
      try {
        const storeId = isAdmin
          ? storeFilter !== "all"
            ? storeFilter
            : undefined
          : managerStoreId;

        const params: Record<string, unknown> = {};
        if (storeId) params.store_id = storeId;

        const empRes = await api.get("/employees", { params });
        const emps: EmployeeWithUser[] = empRes.data;
        setEmployees(emps);

        const deptResults = await Promise.all(
          emps.map((e) =>
            api
              .get(`/employee-departments/employee/${e.id}`)
              .then((r) => ({ id: e.id, depts: r.data as EmployeeDepartmentResponse[] }))
              .catch(() => ({ id: e.id, depts: [] as EmployeeDepartmentResponse[] }))
          )
        );
        const map = new Map<number, EmployeeDepartmentResponse[]>();
        for (const { id, depts } of deptResults) map.set(id, depts);
        setEmpDepts(map);
      } catch {
        setEmployees([]);
      } finally {
        setLoading(false);
      }
    };
    fetchEmployees();
  }, [isAdmin, storeFilter, managerStoreId, refreshKey]);

  const filtered = useMemo(() => {
    let list = employees;

    if (deptFilter !== "all") {
      const empIdsInDept = new Set<number>();
      empDepts.forEach((depts, empId) => {
        if (depts.some((d) => d.department_id === deptFilter)) empIdsInDept.add(empId);
      });
      list = list.filter((e) => empIdsInDept.has(e.id));
    }

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(
        (e) =>
          e.firstname.toLowerCase().includes(q) ||
          e.surname.toLowerCase().includes(q) ||
          `${e.firstname} ${e.surname}`.toLowerCase().includes(q) ||
          e.id.toString().includes(q)
      );
    }

    let sorted = list.sort((a, b) =>
      `${a.surname} ${a.firstname}`.localeCompare(`${b.surname} ${b.firstname}`)
    );

    // Pinch active employee to top
    if (activeEmployeeId) {
      sorted = [...sorted].sort((a, b) => {
        if (a.id === activeEmployeeId) return -1;
        if (b.id === activeEmployeeId) return 1;
        return 0;
      });
    }

    return sorted;
  }, [employees, empDepts, deptFilter, search, activeEmployeeId]);

  const deptMap = useMemo(() => {
    const m = new Map<number, string>();
    for (const d of departments) m.set(d.id, d.name);
    return m;
  }, [departments]);

  const hasNoDepts = (empId: number): boolean => (empDepts.get(empId) ?? []).length === 0;

  const openCreate = () => {
    setActiveEmployeeId(null);
    setPanelMode("create");
  };

  const openEdit = (empId: number) => {
    if (panelMode === "edit" && activeEmployeeId === empId) {
      closePanel();
      return;
    }
    setActiveEmployeeId(empId);
    setPanelMode("edit");
  };

  const closePanel = () => {
    setPanelMode(null);
    setActiveEmployeeId(null);
  };

  const isOpen = panelMode !== null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Employees</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {filtered.length} employee{filtered.length !== 1 ? "s" : ""}
          </p>
        </div>
        {isManagerOrAdmin && (
          <Button onClick={openCreate} className="gap-2">
            <UserPlus size={16} />
            Add Employee
          </Button>
        )}
      </div>

      <div className="flex gap-4 items-start">
        {/* List column */}
        <div className={`${isOpen ? "flex-[0_0_55%]" : "w-full"} min-w-0 space-y-3`}>
          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px] max-w-sm">
              <Search
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <input
                type="text"
                placeholder="Search name or ID…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-md border bg-background px-9 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            {isAdmin && stores.length > 0 && (
              <select
                value={storeFilter}
                onChange={(e) =>
                  setStoreFilter(e.target.value === "all" ? "all" : Number(e.target.value))
                }
                className="rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="all">All stores</option>
                {stores.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            )}

            {departments.length > 0 && (
              <select
                value={deptFilter}
                onChange={(e) =>
                  setDeptFilter(e.target.value === "all" ? "all" : Number(e.target.value))
                }
                className="rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="all">All departments</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Employee list */}
          {loading ? (
            <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
              Loading employees…
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
              No employees found
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map((emp) => {
                const depts = empDepts.get(emp.id) ?? [];
                const primaryDept = depts.find((d) => d.is_primary);
                const primaryDeptName = primaryDept
                  ? deptMap.get(primaryDept.department_id)
                  : null;
                const isActive = emp.id === activeEmployeeId && panelMode === "edit";

                return (
                  <Card
                    key={emp.id}
                    className={`flex items-center justify-between px-4 py-3 transition-all ${
                      isActive ? "ring-2 ring-primary" : ""
                    }`}
                  >
                    <div className="flex items-center gap-4 min-w-0">
                      <div className="w-10 h-10 rounded-full bg-primary/15 flex items-center justify-center shrink-0">
                        <span className="text-sm font-semibold text-primary">
                          {emp.firstname[0]}
                          {emp.surname[0]}
                        </span>
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-semibold">
                            {emp.firstname} {emp.surname}
                          </span>
                          <Badge variant={STATUS_VARIANT[emp.employment_status]}>
                            {STATUS_LABEL[emp.employment_status]}
                          </Badge>
                          {hasNoDepts(emp.id) && (
                            <Badge variant="warning">No Departments</Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                          <span>#{emp.id}</span>
                          <span>·</span>
                          <span>{emp.contracted_weekly_hours}h/week</span>
                          {primaryDeptName && (
                            <>
                              <span>·</span>
                              <span>{primaryDeptName}</span>
                            </>
                          )}
                          {emp.is_keyholder && (
                            <>
                              <span>·</span>
                              <span className="text-primary">Keyholder</span>
                            </>
                          )}
                          {emp.is_manager && (
                            <>
                              <span>·</span>
                              <span className="text-primary">Manager</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <Button
                      variant={isActive ? "secondary" : "ghost"}
                      size="sm"
                      className="shrink-0 gap-1.5"
                      onClick={() => openEdit(emp.id)}
                    >
                      <Pencil size={14} />
                      <span className="hidden sm:inline">Edit</span>
                    </Button>
                  </Card>
                );
              })}
            </div>
          )}
        </div>

        {/* Panel column */}
        {isOpen && (
          <div className="flex-1 min-w-0">
            {panelMode === "create" ? (
              <AddEmployeePanel
                stores={stores}
                allDepts={departments}
                defaultStoreId={!isAdmin && managerStoreId ? managerStoreId : undefined}
                onClose={closePanel}
                onCreated={() => {
                  closePanel();
                  setRefreshKey((k) => k + 1);
                }}
              />
            ) : activeEmployeeId ? (
              <EmployeeEditPanel
                key={activeEmployeeId}
                employeeId={activeEmployeeId}
                isAdmin={isAdmin}
                stores={stores}
                allDepts={departments}
                onClose={closePanel}
                onSaved={() => setRefreshKey((k) => k + 1)}
              />
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
