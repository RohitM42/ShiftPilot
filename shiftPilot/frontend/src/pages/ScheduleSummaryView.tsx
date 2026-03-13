import { useState, useEffect, useMemo } from "react";
import { addDays, format, parseISO } from "date-fns";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { shiftsApi, employeesApi, departmentsApi, scheduleApi } from "@/services/api";
import type { ShiftResponse, EmployeeWithUserResponse, Department, GenerateScheduleResponse } from "@/types";
import { ShiftStatus } from "@/types";
import { EmployeeGantt, type ParsedShift } from "@/components/EmployeeGantt";

// ── Types ────────────────────────────────────────────────────────────

interface SummaryRouteState {
  shiftIds: number[];
  weekStart: string; // "YYYY-MM-DD"
  storeId: number;
  generateResult?: GenerateScheduleResponse;
}

const DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

// ── Component ────────────────────────────────────────────────────────

export default function ScheduleSummaryView() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as SummaryRouteState | null;

  // Redirect if navigated directly without state
  useEffect(() => {
    if (!state?.shiftIds || !state?.weekStart || state?.storeId == null) {
      navigate("/schedule", { replace: true });
    }
  }, [state, navigate]);

  const { shiftIds, weekStart, storeId, generateResult } = state ?? {
    shiftIds: [],
    weekStart: "",
    storeId: 0,
    generateResult: undefined,
  };

  // Per-day unmet constraints derived from generateResult (day_of_week: 0=Mon … 6=Sun)
  const unmetByDay = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => ({
      coverage: generateResult?.unmet_coverage.filter((u) => u.day_of_week === i) ?? [],
      role: generateResult?.unmet_role_requirements.filter(
        (u) => u.day_of_week === i || u.day_of_week === null
      ) ?? [],
    }));
  }, [generateResult]);

  // Day navigation within the week (0 = Monday … 6 = Sunday)
  const [dayIndex, setDayIndex] = useState(0);

  // Data
  const [allShifts, setAllShifts] = useState<ShiftResponse[]>([]);
  const [employees, setEmployees] = useState<EmployeeWithUserResponse[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    if (!weekStart || !storeId) return;

    const start = new Date(weekStart);
    const end = addDays(start, 7);

    setLoading(true);
    Promise.all([
      shiftsApi.list({
        store_id: storeId,
        start_date: start.toISOString(),
        end_date: end.toISOString(),
        limit: 500,
      }),
      employeesApi.list(storeId),
      departmentsApi.list(),
    ])
      .then(([shiftsRes, empsRes, deptsRes]) => {
        setAllShifts(shiftsRes.data);
        setEmployees(empsRes.data);
        setDepartments(deptsRes.data);
      })
      .finally(() => setLoading(false));
  }, [weekStart, storeId]);

  const deptMap = useMemo(() => {
    const m = new Map<number, string>();
    for (const d of departments) m.set(d.id, d.name);
    return m;
  }, [departments]);

  // Shifts for the currently selected day, filtered to only generated IDs
  const shiftIdSet = useMemo(() => new Set(shiftIds), [shiftIds]);

  const selectedDate = useMemo(
    () => addDays(new Date(weekStart), dayIndex),
    [weekStart, dayIndex]
  );

  const parsedShifts: ParsedShift[] = useMemo(() => {
    const dayStart = new Date(selectedDate);
    dayStart.setHours(0, 0, 0, 0);
    const dayEnd = new Date(selectedDate);
    dayEnd.setHours(23, 59, 59, 999);

    return allShifts
      .filter((s) => {
        if (!shiftIdSet.has(s.id)) return false;
        if (s.status === ShiftStatus.CANCELLED) return false;
        const dt = parseISO(s.start_datetime_utc);
        return dt >= dayStart && dt <= dayEnd;
      })
      .map((s) => {
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
          status: s.status,
        };
      });
  }, [allShifts, shiftIdSet, selectedDate, deptMap]);

  const shiftsByEmployee = useMemo(() => {
    const m = new Map<number, ParsedShift[]>();
    for (const s of parsedShifts) {
      if (!m.has(s.employeeId)) m.set(s.employeeId, []);
      m.get(s.employeeId)!.push(s);
    }
    return m;
  }, [parsedShifts]);

  // Only show employees who have at least one shift this day
  const activeEmployees = useMemo(
    () => employees.filter((e) => (shiftsByEmployee.get(e.id) ?? []).length > 0),
    [employees, shiftsByEmployee]
  );

  // Shift counts per day for the badge
  const shiftsPerDay = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => {
      const d = addDays(new Date(weekStart), i);
      const dayStart = new Date(d);
      dayStart.setHours(0, 0, 0, 0);
      const dayEnd = new Date(d);
      dayEnd.setHours(23, 59, 59, 999);
      return allShifts.filter((s) => {
        if (!shiftIdSet.has(s.id)) return false;
        if (s.status === ShiftStatus.CANCELLED) return false;
        const dt = parseISO(s.start_datetime_utc);
        return dt >= dayStart && dt <= dayEnd;
      }).length;
    });
  }, [allShifts, shiftIdSet, weekStart]);

  async function handlePublish() {
    setPublishing(true);
    try {
      await scheduleApi.publishBulk(shiftIds);
      navigate("/schedule", { replace: true });
    } finally {
      setPublishing(false);
    }
  }

  async function handleCancel() {
    setCancelling(true);
    try {
      await scheduleApi.cancelBulk(shiftIds);
      navigate("/schedule", { replace: true });
    } finally {
      setCancelling(false);
    }
  }

  const weekLabel = weekStart
    ? `${format(new Date(weekStart), "d MMM")} – ${format(addDays(new Date(weekStart), 6), "d MMM yyyy")}`
    : "";

  if (!state) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Schedule Summary</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Week of {weekLabel} · {shiftIds.length} draft shifts
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCancel}
            disabled={cancelling || publishing}
            className="text-destructive border-destructive/50 hover:bg-destructive/10"
          >
            {cancelling ? "Cancelling…" : "Cancel Drafts"}
          </Button>
          <Button
            size="sm"
            onClick={handlePublish}
            disabled={publishing || cancelling}
            className="bg-green-600 hover:bg-green-700"
          >
            {publishing ? "Publishing…" : `Publish All (${shiftIds.length})`}
          </Button>
        </div>
      </div>

      {/* Day tabs */}
      <div className="flex items-center gap-1 flex-wrap">
        <Button
          variant="outline"
          size="icon"
          onClick={() => setDayIndex((i) => Math.max(0, i - 1))}
          disabled={dayIndex === 0}
        >
          <ChevronLeft size={16} />
        </Button>

        {DAY_NAMES.map((name, i) => {
          const date = addDays(new Date(weekStart), i);
          const count = shiftsPerDay[i];
          const hasUnmet = generateResult &&
            (unmetByDay[i].coverage.length > 0 || unmetByDay[i].role.length > 0);
          const isSelected = dayIndex === i;
          return (
            <button
              key={i}
              onClick={() => setDayIndex(i)}
              className={`relative w-16 rounded-md border py-1.5 text-center text-sm transition-colors ${
                isSelected
                  ? "border-primary bg-primary/10 text-primary font-medium"
                  : "hover:bg-accent text-muted-foreground"
              }`}
            >
              {generateResult && (
                <span className={`absolute top-1 right-1 text-[10px] font-bold leading-none ${
                  hasUnmet ? "text-red-500" : "text-green-500"
                }`}>
                  {hasUnmet ? "✗" : "✓"}
                </span>
              )}
              <span className="block text-xs font-semibold">{name.slice(0, 3)}</span>
              <span className="block text-xs">{format(date, "d MMM")}</span>
              {count > 0 && (
                <span
                  className={`block text-[10px] font-medium mt-0.5 ${
                    isSelected ? "text-primary/70" : "text-muted-foreground"
                  }`}
                >
                  {count} shift{count !== 1 ? "s" : ""}
                </span>
              )}
            </button>
          );
        })}

        <Button
          variant="outline"
          size="icon"
          onClick={() => setDayIndex((i) => Math.min(6, i + 1))}
          disabled={dayIndex === 6}
        >
          <ChevronRight size={16} />
        </Button>
      </div>

      {/* Day heading */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">
          {DAY_NAMES[dayIndex]}, {format(selectedDate, "d MMMM")}
        </h2>
        <span className="text-sm text-muted-foreground">
          {parsedShifts.length} shift{parsedShifts.length !== 1 ? "s" : ""} scheduled
        </span>
      </div>

      {/* Gantt */}
      {loading ? (
        <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
          Loading shifts…
        </div>
      ) : (
        <EmployeeGantt
          employees={activeEmployees}
          shiftsByEmployee={shiftsByEmployee}
        />
      )}

      {/* Unmet constraints for selected day */}
      {generateResult && (unmetByDay[dayIndex].coverage.length > 0 || unmetByDay[dayIndex].role.length > 0) && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 space-y-3">
          <p className="text-sm font-semibold text-red-800">Unmet constraints — {DAY_NAMES[dayIndex]}</p>

          {unmetByDay[dayIndex].coverage.length > 0 && (
            <div>
              <p className="text-xs font-medium text-red-700 mb-1">Coverage</p>
              <ul className="space-y-0.5">
                {unmetByDay[dayIndex].coverage.map((u, i) => (
                  <li key={i} className="text-xs text-red-700">
                    {deptMap.get(u.department_id) ?? `Dept ${u.department_id}`} · {u.start_time.slice(0, 5)}–{u.end_time.slice(0, 5)} · needs {u.min_staff} staff
                  </li>
                ))}
              </ul>
            </div>
          )}

          {unmetByDay[dayIndex].role.length > 0 && (
            <div>
              <p className="text-xs font-medium text-red-700 mb-1">Role requirements</p>
              <ul className="space-y-0.5">
                {unmetByDay[dayIndex].role.map((u, i) => (
                  <li key={i} className="text-xs text-red-700">
                    {u.department_id != null ? `${deptMap.get(u.department_id) ?? `Dept ${u.department_id}`} · ` : ""}
                    {u.day_of_week === null ? "Every day" : DAY_NAMES[u.day_of_week]} · {u.start_time.slice(0, 5)}–{u.end_time.slice(0, 5)} ·{" "}
                    {u.requires_manager ? `≥${u.min_manager_count} manager` : u.requires_keyholder ? "keyholder needed" : "role constraint"}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Bottom action bar */}
      <div className="flex items-center justify-end gap-2 pt-2 border-t">
        <Button
          variant="outline"
          size="sm"
          onClick={handleCancel}
          disabled={cancelling || publishing}
          className="text-destructive border-destructive/50 hover:bg-destructive/10"
        >
          {cancelling ? "Cancelling…" : "Cancel Drafts"}
        </Button>
        <Button
          size="sm"
          onClick={handlePublish}
          disabled={publishing || cancelling}
          className="bg-green-600 hover:bg-green-700"
        >
          {publishing ? "Publishing…" : `Publish All (${shiftIds.length})`}
        </Button>
      </div>
    </div>
  );
}
