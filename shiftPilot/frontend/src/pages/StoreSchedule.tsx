import { useState, useEffect, useMemo } from "react";
import { format, addDays, parseISO, isToday } from "date-fns";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { shiftsApi, employeesApi, departmentsApi } from "@/services/api";
import type { ShiftResponse, EmployeeWithUserResponse, Department } from "@/types";
import { ShiftStatus } from "@/types";
import { EmployeeGantt, type ParsedShift } from "@/components/EmployeeGantt";

export default function StoreSchedule() {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [employees, setEmployees] = useState<EmployeeWithUserResponse[]>([]);
  const [shifts, setShifts] = useState<ShiftResponse[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedDeptId, setSelectedDeptId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const weekMonday = useMemo(() => {
    const d = new Date(selectedDate);
    const day = d.getDay();
    d.setDate(d.getDate() + (day === 0 ? -6 : 1 - day));
    d.setHours(0, 0, 0, 0);
    return d;
  }, [selectedDate]);

  const prevWeek = () => setSelectedDate((d) => addDays(d, -7));
  const nextWeek = () => setSelectedDate((d) => addDays(d, 7));
  const goToday = () => setSelectedDate(new Date());

  const dateLabel = format(selectedDate, "EEEE, d MMMM yyyy");

  useEffect(() => {
    Promise.all([
      employeesApi.listStoreColleagues(),
      departmentsApi.list(),
    ]).then(([empRes, deptRes]) => {
      setEmployees(empRes.data);
      setDepartments(deptRes.data);
    });
  }, []);

  useEffect(() => {
    setSelectedDeptId(null);
  }, [selectedDate]);

  useEffect(() => {
    setLoading(true);
    const dayStart = new Date(selectedDate);
    dayStart.setHours(0, 0, 0, 0);
    const dayEnd = new Date(selectedDate);
    dayEnd.setHours(23, 59, 59, 999);

    shiftsApi
      .listStoreSchedule({
        start_date: dayStart.toISOString(),
        end_date: dayEnd.toISOString(),
      })
      .then((r) => setShifts(r.data))
      .catch(() => setShifts([]))
      .finally(() => setLoading(false));
  }, [selectedDate]);

  const deptMap = useMemo(() => {
    const m = new Map<number, string>();
    for (const d of departments) m.set(d.id, d.name);
    return m;
  }, [departments]);

  const parsedShifts: ParsedShift[] = useMemo(() =>
    shifts.map((s) => {
      const start = parseISO(s.start_datetime_utc);
      const end = parseISO(s.end_datetime_utc);
      return {
        id: s.id,
        employeeId: s.employee_id,
        start,
        end,
        departmentId: s.department_id,
        departmentName: deptMap.get(s.department_id) ?? `Dept ${s.department_id}`,
        hours: Math.round(((end.getTime() - start.getTime()) / 3600000) * 10) / 10,
        status: s.status as ShiftStatus,
      };
    }),
    [shifts, deptMap]
  );

  const shiftsByEmployee = useMemo(() => {
    const m = new Map<number, ParsedShift[]>();
    for (const s of parsedShifts) {
      if (!m.has(s.employeeId)) m.set(s.employeeId, []);
      m.get(s.employeeId)!.push(s);
    }
    return m;
  }, [parsedShifts]);

  const storeDepts = useMemo(() => {
    const deptIds = new Set(parsedShifts.map((s) => s.departmentId));
    return departments.filter((d) => deptIds.has(d.id));
  }, [departments, parsedShifts]);

  const filteredEmployees = useMemo(() => {
    if (!selectedDeptId) return employees;
    return employees.filter((e) =>
      (shiftsByEmployee.get(e.id) ?? []).some((s) => s.departmentId === selectedDeptId)
    );
  }, [employees, selectedDeptId, shiftsByEmployee]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Store Schedule</h1>
          <p className="text-sm text-muted-foreground mt-0.5">{dateLabel}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            className="h-9 rounded-md border bg-background px-3 text-sm"
            value={selectedDeptId ?? ""}
            onChange={(e) =>
              setSelectedDeptId(e.target.value ? Number(e.target.value) : null)
            }
          >
            <option value="">All Departments</option>
            {storeDepts.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Week day tabs */}
      <div className="flex items-center gap-1 flex-wrap">
        <Button variant="outline" size="icon" onClick={prevWeek}>
          <ChevronLeft size={16} />
        </Button>

        {Array.from({ length: 7 }, (_, i) => {
          const date = addDays(weekMonday, i);
          const isSelected =
            format(date, "yyyy-MM-dd") === format(selectedDate, "yyyy-MM-dd");
          const todayDate = isToday(date);
          return (
            <button
              key={i}
              onClick={() => setSelectedDate(date)}
              className={`w-16 rounded-md border py-1.5 text-center text-sm transition-colors ${
                isSelected
                  ? "border-primary bg-primary/10 text-primary font-medium"
                  : todayDate
                  ? "border-primary/40 bg-primary/5 text-foreground hover:bg-primary/10"
                  : "hover:bg-accent text-muted-foreground"
              }`}
            >
              <span className="block text-xs font-semibold">
                {format(date, "EEE").toUpperCase()}
              </span>
              <span className="block text-xs">{format(date, "d MMM")}</span>
            </button>
          );
        })}

        <Button variant="outline" size="icon" onClick={nextWeek}>
          <ChevronRight size={16} />
        </Button>

        <Button
          variant={isToday(selectedDate) ? "default" : "outline"}
          size="sm"
          className="text-xs ml-1"
          onClick={goToday}
        >
          Today
        </Button>
      </div>

      {/* Gantt */}
      {loading ? (
        <div className="flex items-center justify-center py-16 text-muted-foreground text-sm">
          Loading…
        </div>
      ) : (
        <EmployeeGantt
          employees={filteredEmployees}
          shiftsByEmployee={shiftsByEmployee}
          activeDeptId={selectedDeptId}
        />
      )}
    </div>
  );
}
