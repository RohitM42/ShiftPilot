import { useState, useEffect, useMemo, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Plus, Star, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";
import api from "@/services/api";
import { EmploymentStatus, Role } from "@/types";
import type { EmployeeDepartmentResponse, UserRoleResponse } from "@/types";

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

interface StoreOption {
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

// ── Status helpers ───────────────────────────────────────────────────

const STATUS_OPTIONS: { value: EmploymentStatus; label: string }[] = [
  { value: EmploymentStatus.ACTIVE, label: "Active" },
  { value: EmploymentStatus.ON_LEAVE, label: "On Leave" },
  { value: EmploymentStatus.LEAVER, label: "Leaver" },
];

const STATUS_VARIANT: Record<EmploymentStatus, "success" | "destructive" | "warning"> = {
  [EmploymentStatus.ACTIVE]: "success",
  [EmploymentStatus.LEAVER]: "destructive",
  [EmploymentStatus.ON_LEAVE]: "warning",
};

// ── Component ────────────────────────────────────────────────────────

export default function EmployeeEdit() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();

  const [employee, setEmployee] = useState<EmployeeWithUser | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [depts, setDepts] = useState<DeptAssignment[]>([]);
  const [initialDepts, setInitialDepts] = useState<DeptAssignment[]>([]);
  const [allDepts, setAllDepts] = useState<DeptOption[]>([]);
  const [stores, setStores] = useState<StoreOption[]>([]);
  const [userRoles, setUserRoles] = useState<UserRoleResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [addDeptId, setAddDeptId] = useState<number | "">("");

  // Load all data
  useEffect(() => {
    if (!id) return;
    const load = async () => {
      setLoading(true);
      try {
        const [empRes, empDeptsRes, allDeptsRes] = await Promise.all([
          api.get(`/employees/${id}`),
          api.get(`/employee-departments/employee/${id}`),
          api.get("/departments"),
        ]);

        const emp: EmployeeWithUser = empRes.data;
        const empDepts: EmployeeDepartmentResponse[] = empDeptsRes.data;
        const assignments = empDepts.map((d) => ({
          department_id: d.department_id,
          is_primary: d.is_primary,
        }));

        setEmployee(emp);
        setForm({
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
        setAllDepts(allDeptsRes.data);

        // Admin-only: fetch stores and user roles (for is_manager sync)
        if (isAdmin) {
          const [storesRes, rolesRes] = await Promise.all([
            api.get("/stores"),
            api.get(`/user-roles/user/${emp.user_id}`),
          ]);
          setStores(storesRes.data);
          setUserRoles(rolesRes.data);
        }
      } catch {
        setError("Failed to load employee");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id, isAdmin]);

  // Dirty tracking
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
      JSON.stringify(depts.sort((a, b) => a.department_id - b.department_id)) !==
      JSON.stringify(initialDepts.sort((a, b) => a.department_id - b.department_id));

    return formChanged || deptsChanged;
  }, [form, employee, depts, initialDepts]);

  // Form field updater
  const setField = useCallback(<K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((f) => f ? { ...f, [key]: value } : f);
  }, []);

  // Department management
  const addDept = () => {
    if (addDeptId === "" || depts.some((d) => d.department_id === addDeptId)) return;
    setDepts((prev) => [...prev, { department_id: addDeptId as number, is_primary: prev.length === 0 }]);
    setAddDeptId("");
  };

  const removeDept = (deptId: number) => {
    setDepts((prev) => {
      const next = prev.filter((d) => d.department_id !== deptId);
      // If we removed the primary, make the first remaining one primary
      if (next.length > 0 && !next.some((d) => d.is_primary)) {
        next[0].is_primary = true;
      }
      return next;
    });
  };

  const setPrimary = (deptId: number) => {
    setDepts((prev) =>
      prev.map((d) => ({ ...d, is_primary: d.department_id === deptId }))
    );
  };

  // Department name lookup
  const deptName = useCallback(
    (deptId: number) => allDepts.find((d) => d.id === deptId)?.name ?? `Dept ${deptId}`,
    [allDepts]
  );

  // Available departments (not yet assigned)
  const availableDepts = useMemo(() => {
    const assigned = new Set(depts.map((d) => d.department_id));
    return allDepts.filter((d) => !assigned.has(d.id));
  }, [allDepts, depts]);

  // Cancel with confirmation
  const handleCancel = () => {
    if (isDirty) {
      if (!window.confirm("You have unsaved changes. Are you sure you want to leave?")) return;
    }
    navigate("/employees");
  };

  // Save
  const handleSave = async () => {
    if (!form || !employee || !id) return;
    if (!window.confirm("Save all changes to this employee?")) return;

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
          employee_id: Number(id),
          department_id: dept.department_id,
          is_primary: dept.is_primary,
        });
      }

      // 2. Set primary if changed
      const newPrimary = depts.find((d) => d.is_primary);
      const oldPrimary = initialDepts.find((d) => d.is_primary);
      if (newPrimary && newPrimary.department_id !== oldPrimary?.department_id) {
        await api.put(
          `/employee-departments/employee/${id}/department/${newPrimary.department_id}/set-primary`
        );
      }

      // 3. Department removals
      for (const dept of removed) {
        await api.delete(`/employee-departments/employee/${id}/department/${dept.department_id}`);
      }

      // 4. Update employee fields
      const empUpdate: Record<string, unknown> = {};
      if (form.contracted_weekly_hours !== employee.contracted_weekly_hours)
        empUpdate.contracted_weekly_hours = form.contracted_weekly_hours;
      if (form.dob !== employee.dob) empUpdate.dob = form.dob;
      if (form.is_keyholder !== employee.is_keyholder) empUpdate.is_keyholder = form.is_keyholder;
      if (isAdmin) {
        if (form.is_manager !== employee.is_manager) empUpdate.is_manager = form.is_manager;
        if (form.employment_status !== employee.employment_status)
          empUpdate.employment_status = form.employment_status;
        if (form.store_id !== employee.store_id) empUpdate.store_id = form.store_id;
      }

      if (Object.keys(empUpdate).length > 0) {
        await api.put(`/employees/${id}`, empUpdate);
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
          // Add MANAGER role
          await api.post("/user-roles", {
            user_id: employee.user_id,
            store_id: employee.store_id,
            role: Role.MANAGER,
          });
        } else if (!form.is_manager && existingManagerRole) {
          // Remove MANAGER role
          await api.delete(`/user-roles/${existingManagerRole.id}`);
        }
      }

      navigate("/employees");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to save changes");
    } finally {
      setSaving(false);
    }
  };

  // ── Render ───────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
        Loading employee…
      </div>
    );
  }

  if (error && !employee) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => navigate("/employees")}>
          <ArrowLeft size={16} /> Back
        </Button>
        <p className="text-destructive text-sm">{error}</p>
      </div>
    );
  }

  if (!employee || !form) return null;

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={handleCancel}>
          <ArrowLeft size={18} />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">
            {employee.firstname} {employee.surname}
          </h1>
          <p className="text-sm text-muted-foreground">
            Employee #{employee.id}
          </p>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Personal Info */}
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-base">Personal Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <FieldGroup label="First name">
              {isAdmin ? (
                <Input value={form.firstname} onChange={(v) => setField("firstname", v)} />
              ) : (
                <ReadOnly value={form.firstname} />
              )}
            </FieldGroup>
            <FieldGroup label="Surname">
              {isAdmin ? (
                <Input value={form.surname} onChange={(v) => setField("surname", v)} />
              ) : (
                <ReadOnly value={form.surname} />
              )}
            </FieldGroup>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <FieldGroup label="Date of birth">
              <Input type="date" value={form.dob} onChange={(v) => setField("dob", v)} />
            </FieldGroup>
            <FieldGroup label="Email">
              <ReadOnly value={employee.email} />
            </FieldGroup>
          </div>
        </CardContent>
      </Card>

      {/* Employment Details */}
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-base">Employment Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <FieldGroup label="Contracted hours (weekly)">
              <Input
                type="number"
                value={form.contracted_weekly_hours.toString()}
                onChange={(v) => setField("contracted_weekly_hours", parseInt(v) || 0)}
              />
            </FieldGroup>
            <FieldGroup label="Employment status">
              {isAdmin ? (
                <Select
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
              <Select
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
                  <span className="w-4 h-4 rounded border bg-primary/20 flex items-center justify-center text-primary text-xs">✓</span>
                  Manager
                </span>
              )
            )}
          </div>
        </CardContent>
      </Card>

      {/* Department Assignments */}
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-base">Department Assignments</CardTitle>
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

          {/* Add department */}
          {availableDepts.length > 0 && (
            <div className="flex items-center gap-2 pt-1">
              <select
                value={addDeptId}
                onChange={(e) => setAddDeptId(e.target.value === "" ? "" : Number(e.target.value))}
                className="rounded-md border bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring flex-1"
              >
                <option value="">Select department…</option>
                {availableDepts.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
              <Button size="sm" variant="outline" className="gap-1" onClick={addDept} disabled={addDeptId === ""}>
                <Plus size={14} /> Add
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex items-center justify-end gap-3 pb-8">
        <Button variant="outline" onClick={handleCancel}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={!isDirty || saving}>
          {saving ? "Saving…" : "Save changes"}
        </Button>
      </div>
    </div>
  );
}

// ── Shared form components ───────────────────────────────────────────

function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}

function Input({
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

function Select({
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
        <option key={o.value} value={o.value}>{o.label}</option>
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