import { useState, useEffect, useMemo } from "react";
import { Search, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";
import api from "@/services/api";
import { EmploymentStatus } from "@/types";
import type {
  EmployeeResponse,
  EmployeeDepartmentResponse,
} from "@/types";

// ── Types ────────────────────────────────────────────────────────────

interface EmployeeWithUser extends EmployeeResponse {
  firstname: string;
  surname: string;
  email: string;
}

interface DepartmentOption {
  id: number;
  name: string;
}

interface StoreOption {
  id: number;
  name: string;
}

// ── Status badge styling ─────────────────────────────────────────────

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

// ── Component ────────────────────────────────────────────────────────

export default function EmployeeManagement() {
  const { isAdmin, employee: currentEmployee } = useAuth();

  const [employees, setEmployees] = useState<EmployeeWithUser[]>([]);
  const [empDepts, setEmpDepts] = useState<Map<number, EmployeeDepartmentResponse[]>>(new Map());
  const [departments, setDepartments] = useState<DepartmentOption[]>([]);
  const [stores, setStores] = useState<StoreOption[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState("");
  const [storeFilter, setStoreFilter] = useState<number | "all">("all");
  const [deptFilter, setDeptFilter] = useState<number | "all">("all");

  // Determine the effective store for managers
  const managerStoreId = currentEmployee?.store_id;

  // Fetch reference data
  useEffect(() => {
    const fetchRef = async () => {
      try {
        const [deptRes, storeRes] = await Promise.all([
          api.get("/departments"),
          isAdmin ? api.get("/stores") : Promise.resolve(null),
        ]);
        setDepartments(deptRes.data);
        if (storeRes) setStores(storeRes.data);
      } catch {
        // silent — filters just won't populate
      }
    };
    fetchRef();
  }, [isAdmin]);

  // Set manager default dept filter
  useEffect(() => {
    if (!isAdmin && currentEmployee && empDepts.size > 0) {
      const myDepts = empDepts.get(currentEmployee.id);
      const primary = myDepts?.find((d) => d.is_primary);
      if (primary) setDeptFilter(primary.department_id);
    }
  }, [isAdmin, currentEmployee, empDepts]);

  // Fetch employees + their department links
  useEffect(() => {
    const fetchEmployees = async () => {
      setLoading(true);
      try {
        const storeId = isAdmin
          ? storeFilter !== "all" ? storeFilter : undefined
          : managerStoreId;

        const params: Record<string, unknown> = {};
        if (storeId) params.store_id = storeId;

        const empRes = await api.get("/employees", { params });
        const emps: EmployeeWithUser[] = empRes.data;
        setEmployees(emps);

        // Fetch department links for all employees
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
  }, [isAdmin, storeFilter, managerStoreId]);

  // Filter employees
  const filtered = useMemo(() => {
    let list = employees;

    // Department filter
    if (deptFilter !== "all") {
      const empIdsInDept = new Set<number>();
      empDepts.forEach((depts, empId) => {
        if (depts.some((d) => d.department_id === deptFilter)) empIdsInDept.add(empId);
      });
      list = list.filter((e) => empIdsInDept.has(e.id));
    }

    // Search
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

    return list.sort((a, b) => `${a.surname} ${a.firstname}`.localeCompare(`${b.surname} ${b.firstname}`));
  }, [employees, empDepts, deptFilter, search]);

  // Department name lookup
  const deptMap = useMemo(() => {
    const m = new Map<number, string>();
    for (const d of departments) m.set(d.id, d.name);
    return m;
  }, [departments]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Employees</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {filtered.length} employee{filtered.length !== 1 ? "s" : ""}
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search name or ID…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-md border bg-background px-9 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        {/* Store filter — admin only */}
        {isAdmin && stores.length > 0 && (
          <select
            value={storeFilter}
            onChange={(e) => setStoreFilter(e.target.value === "all" ? "all" : Number(e.target.value))}
            className="rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="all">All stores</option>
            {stores.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        )}

        {/* Department filter */}
        {departments.length > 0 && (
          <select
            value={deptFilter}
            onChange={(e) => setDeptFilter(e.target.value === "all" ? "all" : Number(e.target.value))}
            className="rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="all">All departments</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
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
            const primaryDeptName = primaryDept ? deptMap.get(primaryDept.department_id) : null;

            return (
              <Card key={emp.id} className="flex items-center justify-between px-4 py-3">
                <div className="flex items-center gap-4 min-w-0">
                  {/* Avatar placeholder */}
                  <div className="w-10 h-10 rounded-full bg-primary/15 flex items-center justify-center shrink-0">
                    <span className="text-sm font-semibold text-primary">
                      {emp.firstname[0]}{emp.surname[0]}
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

                <Button variant="ghost" size="sm" className="shrink-0 gap-1.5">
                  <Pencil size={14} />
                  <span className="hidden sm:inline">Edit</span>
                </Button>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}