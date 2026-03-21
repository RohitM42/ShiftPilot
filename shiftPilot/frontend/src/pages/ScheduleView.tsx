import { useState, useEffect, useMemo } from "react";
import { format, addDays, isToday, parseISO } from "date-fns";
import { ChevronLeft, ChevronRight, Plus, Trash2, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  shiftsApi,
  employeesApi,
  departmentsApi,
  storesApi,
  employeeDepartmentsApi,
  scheduleApi,
} from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import type {
  ShiftResponse,
  EmployeeWithUserResponse,
  Department,
  Store,
  EmployeeDepartmentResponse,
  GenerateScheduleResponse,
} from "@/types";
import { ShiftStatus } from "@/types";
import { cn } from "@/lib/utils";
import { EmployeeGantt, type ParsedShift, type PreviewShift } from "@/components/EmployeeGantt";

// ── Constants ────────────────────────────────────────────────────────

const DAY_NAMES_FULL = [
  "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
];

function GeneratePanel({
  storeId,
  expanded,
  onToggle,
  generating,
  setGenerating,
  generatedShiftIds,
  setGeneratedShiftIds,
  generateResult,
  setGenerateResult,
  onShiftsChanged,
  onViewSummary,
  onCancelDrafts,
}: {
  storeId: number | null;
  expanded: boolean;
  onToggle: () => void;
  generating: boolean;
  setGenerating: (v: boolean) => void;
  generatedShiftIds: number[];
  setGeneratedShiftIds: (ids: number[]) => void;
  generateResult: GenerateScheduleResponse | null;
  setGenerateResult: (r: GenerateScheduleResponse | null) => void;
  onShiftsChanged: () => void;
  onViewSummary: (weekStart: string, shiftIds: number[]) => void;
  onCancelDrafts: (shiftIds: number[]) => Promise<void>;
}) {
  const [selectedWeekStart, setSelectedWeekStart] = useState<string | null>(null);
  const [mode, setMode] = useState<"add" | "replace">("add");
  const [existingPublishedCount, setExistingPublishedCount] = useState<number | null>(null);
  const [pendingDraftIds, setPendingDraftIds] = useState<number[]>([]);
  const [checkingExisting, setCheckingExisting] = useState(false);

  // Compute preset week starts (Mondays)
  const nextMonday = useMemo(() => {
    const d = new Date();
    const day = d.getDay(); // 0=Sun
    const daysUntilMonday = day === 0 ? 1 : 8 - day;
    const m = addDays(d, daysUntilMonday);
    m.setHours(0, 0, 0, 0);
    return m;
  }, []);

  const weekAfterMonday = useMemo(() => addDays(nextMonday, 7), [nextMonday]);

  const presets = useMemo(
    () => [
      {
        label: "Next Week",
        date: nextMonday,
        range: `${format(nextMonday, "d MMM")} – ${format(addDays(nextMonday, 6), "d MMM")}`,
      },
      {
        label: "Week After",
        date: weekAfterMonday,
        range: `${format(weekAfterMonday, "d MMM")} – ${format(
          addDays(weekAfterMonday, 6),
          "d MMM"
        )}`,
      },
    ],
    [nextMonday, weekAfterMonday]
  );

  // When week changes, check for existing shifts (separated into drafts vs published)
  useEffect(() => {
    if (!selectedWeekStart || !storeId) {
      setExistingPublishedCount(null);
      setPendingDraftIds([]);
      return;
    }
    setCheckingExisting(true);
    const weekStart = new Date(selectedWeekStart);
    const weekEnd = addDays(weekStart, 7);
    shiftsApi
      .list({
        store_id: storeId,
        start_date: weekStart.toISOString(),
        end_date: weekEnd.toISOString(),
        limit: 500,
      })
      .then((r) => {
        const all = r.data as ShiftResponse[];
        const drafts = all.filter((s) => s.status === ShiftStatus.DRAFT);
        const published = all.filter((s) => s.status === ShiftStatus.PUBLISHED);
        setExistingPublishedCount(published.length);
        // Only surface pending drafts when we haven't just run a generation this session
        if (generatedShiftIds.length === 0) {
          setPendingDraftIds(drafts.map((s) => s.id));
        }
      })
      .catch(() => {
        setExistingPublishedCount(null);
        setPendingDraftIds([]);
      })
      .finally(() => setCheckingExisting(false));
  }, [selectedWeekStart, storeId]); // eslint-disable-line react-hooks/exhaustive-deps

  const canGenerate = !!selectedWeekStart && !!storeId && !generating;

  async function handleGenerate() {
    if (!selectedWeekStart || !storeId) return;
    setGenerating(true);
    setGenerateResult(null);
    setGeneratedShiftIds([]);
    setPendingDraftIds([]); // clear stale DB-detected drafts; new ones tracked via generatedShiftIds
    try {
      const res = await scheduleApi.generate({
        store_id: storeId,
        week_start: selectedWeekStart,
        mode,
      });
      const data = res.data as GenerateScheduleResponse;
      setGenerateResult(data);
      setGeneratedShiftIds(data.shift_ids);
      onShiftsChanged();
    } catch {
      // error toast could go here
    } finally {
      setGenerating(false);
    }
  }


  return (
    <div className="rounded-lg border bg-card">
      <div className="flex items-center justify-between px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold">Generate Schedule</h2>
          <p className="text-xs text-muted-foreground">
            Run the OR-Tools solver to produce a draft schedule
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={onToggle}>
          {expanded ? "Collapse" : "Generate Schedule"}
        </Button>
      </div>

      {expanded && (
        <div className="border-t px-4 py-4 space-y-4">
          {/* Week presets */}
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">
              Select week
            </p>
            <div className="flex flex-wrap gap-2">
              {presets.map((p) => {
                const val = format(p.date, "yyyy-MM-dd");
                return (
                  <button
                    key={val}
                    onClick={() => setSelectedWeekStart(val)}
                    className={cn(
                      "rounded-md border px-3 py-2 text-left text-sm transition-colors",
                      selectedWeekStart === val
                        ? "border-primary bg-primary/10 text-primary"
                        : "hover:bg-accent"
                    )}
                  >
                    <div className="font-medium">{p.label}</div>
                    <div className="text-xs text-muted-foreground">{p.range}</div>
                  </button>
                );
              })}

              {/* Manual input */}
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground mb-1">
                  Custom week
                </span>
                <input
                  type="date"
                  className="h-9 rounded-md border bg-background px-3 text-sm"
                  value={selectedWeekStart ?? ""}
                  onChange={(e) => {
                    if (!e.target.value) { setSelectedWeekStart(null); return; }
                    const picked = new Date(e.target.value + "T00:00:00");
                    const day = picked.getDay(); // 0=Sun
                    const diff = day === 0 ? -6 : 1 - day;
                    picked.setDate(picked.getDate() + diff);
                    const yyyy = picked.getFullYear();
                    const mm = String(picked.getMonth() + 1).padStart(2, "0");
                    const dd = String(picked.getDate()).padStart(2, "0");
                    setSelectedWeekStart(`${yyyy}-${mm}-${dd}`);
                  }}
                />
                {selectedWeekStart && !presets.some(p => format(p.date, "yyyy-MM-dd") === selectedWeekStart) && (
                  <span className="text-xs text-muted-foreground mt-1">
                    Week of {format(new Date(selectedWeekStart + "T00:00:00"), "d MMM yyyy")}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Pending drafts notice — shown when DB has unreviewed drafts from a previous session */}
          {selectedWeekStart && !checkingExisting && pendingDraftIds.length > 0 && generatedShiftIds.length === 0 && (
            <div className="rounded-md border border-blue-300 bg-blue-50 p-3 text-sm space-y-2">
              <p className="font-medium text-blue-800">
                {pendingDraftIds.length} unpublished draft shift{pendingDraftIds.length !== 1 ? "s" : ""} from a previous generation
              </p>
              <p className="text-xs text-blue-700">
                These haven't been published yet. Review and publish them, or discard and regenerate.
              </p>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  className="bg-blue-600 hover:bg-blue-700 text-white h-7 text-xs px-3"
                  onClick={() => onViewSummary(selectedWeekStart, pendingDraftIds)}
                >
                  Review & Publish ({pendingDraftIds.length})
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="text-destructive border-destructive/50 hover:bg-destructive/10 h-7 text-xs px-3"
                  onClick={async () => {
                    await onCancelDrafts(pendingDraftIds);
                    setPendingDraftIds([]);
                    setExistingPublishedCount((c) => c); // keep published count intact
                  }}
                >
                  Discard Drafts
                </Button>
              </div>
            </div>
          )}

          {/* Published shifts warning — only when published shifts exist */}
          {selectedWeekStart && !checkingExisting && existingPublishedCount !== null && existingPublishedCount > 0 && (
            <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm space-y-2">
              <p className="font-medium text-amber-800">
                {existingPublishedCount} published shift{existingPublishedCount !== 1 ? "s" : ""} already exist for this week
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setMode("add")}
                  className={cn(
                    "rounded border px-3 py-1 text-xs font-medium transition-colors",
                    mode === "add"
                      ? "border-amber-600 bg-amber-600 text-white"
                      : "border-amber-400 text-amber-800 hover:bg-amber-100"
                  )}
                >
                  Add to existing
                </button>
                <button
                  onClick={() => setMode("replace")}
                  className={cn(
                    "rounded border px-3 py-1 text-xs font-medium transition-colors",
                    mode === "replace"
                      ? "border-red-600 bg-red-600 text-white"
                      : "border-red-300 text-red-700 hover:bg-red-50"
                  )}
                >
                  Replace existing
                </button>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3">
            <Button onClick={handleGenerate} disabled={!canGenerate} size="sm">
              {generating ? "Generating… (may take up to 2 min)" : "Run Generator"}
            </Button>

            {generatedShiftIds.length > 0 && selectedWeekStart && (
              <>
                <Button
                  onClick={() => onViewSummary(selectedWeekStart, generatedShiftIds)}
                  variant="default"
                  size="sm"
                  className="bg-green-600 hover:bg-green-700"
                >
                  View Summary ({generatedShiftIds.length} shifts)
                </Button>
                <Button
                  onClick={() => onCancelDrafts(generatedShiftIds)}
                  variant="outline"
                  size="sm"
                  className="text-destructive border-destructive/50 hover:bg-destructive/10"
                >
                  Cancel Drafts
                </Button>
              </>
            )}
          </div>

          {/* Result summary */}
          {generateResult && (
            <p className="text-xs text-muted-foreground">
              Generated {generateResult.shifts_created} shifts.{" "}
              {generateResult.success ? "All constraints met." : "Some constraints unmet — see below."}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Shared time input ─────────────────────────────────────────────────

function SplitTimeInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const parts = value ? value.split(":").map(Number) : [0, 0];
  const h = isNaN(parts[0]) ? 0 : parts[0];
  const m = isNaN(parts[1]) ? 0 : [0, 15, 30, 45].reduce((a, b) => (Math.abs(b - parts[1]) < Math.abs(a - parts[1]) ? b : a));

  const setH = (raw: string) => {
    const n = parseInt(raw);
    const clamped = isNaN(n) ? 0 : Math.max(0, Math.min(23, n));
    onChange(`${clamped.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`);
  };
  const setM = (raw: string) => {
    onChange(`${h.toString().padStart(2, "0")}:${raw.padStart(2, "0")}`);
  };

  const base = "rounded-md border bg-background px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring";
  return (
    <div className="flex items-center gap-1">
      <input
        type="number" min={0} max={23} value={h}
        onChange={(e) => setH(e.target.value)}
        className={`${base} w-14 text-center [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none`}
        placeholder="HH"
      />
      <span className="text-muted-foreground text-sm font-medium">:</span>
      <select value={m} onChange={(e) => setM(e.target.value)} className={`${base} w-16`}>
        {[0, 15, 30, 45].map((min) => (
          <option key={min} value={min}>{min.toString().padStart(2, "0")}</option>
        ))}
      </select>
    </div>
  );
}

// ── Manual shift panel ────────────────────────────────────────────────

interface ManualRow {
  id: number;
  employeeId: string;
  day: string; // "yyyy-MM-dd"
  startTime: string; // "HH:MM"
  endTime: string;   // "HH:MM"
  departmentId: string;
}

function makeRow(id: number, defaultDay: string): ManualRow {
  return { id, employeeId: "", day: defaultDay, startTime: "09:00", endTime: "17:00", departmentId: "" };
}

function ManualShiftPanel({
  storeId,
  employees,
  empDepts,
  empPrimaryDepts,
  departments,
  selectedDate,
  expanded,
  onToggle,
  onShiftsChanged,
  onPreviewChange,
}: {
  storeId: number | null;
  employees: EmployeeWithUserResponse[];
  empDepts: Map<number, number[]>;
  empPrimaryDepts: Map<number, number>;
  departments: Department[];
  selectedDate: Date;
  expanded: boolean;
  onToggle: () => void;
  onShiftsChanged: () => void;
  onPreviewChange: (previews: PreviewShift[]) => void;
}) {
  const [rows, setRows] = useState<ManualRow[]>([makeRow(1, format(selectedDate, "yyyy-MM-dd"))]);
  const [submitting, setSubmitting] = useState(false);
  const [nextId, setNextId] = useState(2);

  // Reset rows with current date whenever panel opens or closes
  useEffect(() => {
    setRows([makeRow(1, format(selectedDate, "yyyy-MM-dd"))]);
    setNextId(2);
    if (!expanded) onPreviewChange([]);
  }, [expanded]); // eslint-disable-line react-hooks/exhaustive-deps

  const deptMap = useMemo(() => new Map(departments.map((d) => [d.id, d.name])), [departments]);

  const updateRow = (id: number, patch: Partial<ManualRow>) =>
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));

  const addRow = () => {
    const day = format(selectedDate, "yyyy-MM-dd");
    setRows((prev) => [...prev, makeRow(nextId, day)]);
    setNextId((n) => n + 1);
  };

  const removeRow = (id: number) => setRows((prev) => prev.filter((r) => r.id !== id));

  // Build preview shifts from complete rows and push up to parent
  useEffect(() => {
    const previews: PreviewShift[] = [];
    for (const row of rows) {
      if (!row.employeeId || !row.day || !row.startTime || !row.endTime || !row.departmentId) continue;
      const start = new Date(`${row.day}T${row.startTime}:00`);
      const end = new Date(`${row.day}T${row.endTime}:00`);
      if (isNaN(start.getTime()) || isNaN(end.getTime()) || end <= start) continue;
      previews.push({
        employeeId: Number(row.employeeId),
        start,
        end,
        departmentName: deptMap.get(Number(row.departmentId)) ?? "",
      });
    }
    onPreviewChange(previews);
  }, [rows, deptMap]); // eslint-disable-line react-hooks/exhaustive-deps

  async function submit(shiftStatus: "DRAFT" | "PUBLISHED") {
    if (!storeId) return;
    const complete = rows.filter(
      (r) => r.employeeId && r.day && r.startTime && r.endTime && r.departmentId
    );
    if (complete.length === 0) return;

    setSubmitting(true);
    try {
      await Promise.all(
        complete.map((r) =>
          shiftsApi.create({
            store_id: storeId,
            employee_id: Number(r.employeeId),
            department_id: Number(r.departmentId),
            start_datetime_utc: new Date(`${r.day}T${r.startTime}:00`).toISOString(),
            end_datetime_utc: new Date(`${r.day}T${r.endTime}:00`).toISOString(),
            status: shiftStatus,
            source: "MANUAL",
          })
        )
      );
      onShiftsChanged();
      onToggle(); // collapse panel (effect above will clear rows + preview)
    } finally {
      setSubmitting(false);
    }
  }

  const selectClass = "rounded-md border bg-background px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring";

  // Week days for the day selector
  const weekDays = useMemo(() => {
    const monday = new Date(selectedDate);
    const day = monday.getDay();
    const diff = day === 0 ? -6 : 1 - day;
    monday.setDate(monday.getDate() + diff);
    monday.setHours(0, 0, 0, 0);
    return Array.from({ length: 7 }, (_, i) => {
      const d = addDays(monday, i);
      return { value: format(d, "yyyy-MM-dd"), label: format(d, "EEE d MMM") };
    });
  }, [selectedDate]);

  const completeCount = rows.filter(
    (r) => r.employeeId && r.day && r.startTime && r.endTime && r.departmentId
  ).length;

  return (
    <div className="rounded-lg border bg-card">
      <div className="flex items-center justify-between px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold">Add Shifts Manually</h2>
          <p className="text-xs text-muted-foreground">
            Build individual shifts — preview updates live on the gantt above
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={onToggle}>
          {expanded ? <X size={14} /> : "Add Shifts"}
        </Button>
      </div>

      {expanded && (
        <div className="border-t px-4 py-4 space-y-4">
          <div className="space-y-2">
            {rows.map((row) => {
              const empDeptIds = row.employeeId ? (empDepts.get(Number(row.employeeId)) ?? []) : [];
              const availableDepts = departments.filter((d) => empDeptIds.includes(d.id));

              return (
                <div key={row.id} className="flex flex-wrap items-center gap-2 rounded-md border bg-background/50 px-3 py-2">
                  {/* Employee */}
                  <select
                    className={selectClass}
                    value={row.employeeId}
                    onChange={(e) => {
                      const empId = e.target.value;
                      const primaryDeptId = empId ? empPrimaryDepts.get(Number(empId)) : undefined;
                      updateRow(row.id, {
                        employeeId: empId,
                        departmentId: primaryDeptId ? String(primaryDeptId) : "",
                      });
                    }}
                  >
                    <option value="">Employee…</option>
                    {employees.map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.firstname} {e.surname}
                      </option>
                    ))}
                  </select>

                  {/* Day */}
                  <select
                    className={selectClass}
                    value={row.day}
                    onChange={(e) => updateRow(row.id, { day: e.target.value })}
                  >
                    {weekDays.map((d) => (
                      <option key={d.value} value={d.value}>{d.label}</option>
                    ))}
                  </select>

                  {/* Times */}
                  <SplitTimeInput value={row.startTime} onChange={(v) => updateRow(row.id, { startTime: v })} />
                  <span className="text-xs text-muted-foreground">to</span>
                  <SplitTimeInput value={row.endTime} onChange={(v) => updateRow(row.id, { endTime: v })} />

                  {/* Department — filtered to employee's depts */}
                  <select
                    className={selectClass}
                    value={row.departmentId}
                    onChange={(e) => updateRow(row.id, { departmentId: e.target.value })}
                    disabled={!row.employeeId}
                  >
                    <option value="">Department…</option>
                    {availableDepts.map((d) => (
                      <option key={d.id} value={d.id}>{d.name}</option>
                    ))}
                  </select>

                  <Button
                    variant="ghost"
                    size="icon"
                    className="ml-auto text-muted-foreground hover:text-destructive h-7 w-7"
                    onClick={() => removeRow(row.id)}
                    disabled={rows.length === 1}
                  >
                    <Trash2 size={13} />
                  </Button>
                </div>
              );
            })}
          </div>

          <div className="flex items-center justify-between">
            <Button variant="outline" size="sm" className="gap-1.5" onClick={addRow}>
              <Plus size={13} />
              Add row
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={onToggle} disabled={submitting}>
                Cancel
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={submitting || completeCount === 0}
                onClick={() => submit("DRAFT")}
              >
                Save as Draft ({completeCount})
              </Button>
              <Button
                size="sm"
                disabled={submitting || completeCount === 0}
                onClick={() => submit("PUBLISHED")}
              >
                Publish ({completeCount})
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function UnmetRulesPanel({
  result,
  employees,
  deptMap,
}: {
  result: GenerateScheduleResponse;
  employees: EmployeeWithUserResponse[];
  deptMap: Map<number, string>;
}) {
  const hasUnmetCoverage = result.unmet_coverage.length > 0;
  const hasUnmetRole = result.unmet_role_requirements.length > 0;
  const unmetHoursEntries = Object.entries(result.unmet_contracted_hours).filter(
    ([, shortfall]) => shortfall > 0
  );
  const hasUnmetHours = unmetHoursEntries.length > 0;

  if (!hasUnmetCoverage && !hasUnmetRole && !hasUnmetHours && result.warnings.length === 0) {
    return null;
  }

  const empMap = new Map(employees.map((e) => [e.id, e]));

  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 space-y-4">
      <h2 className="text-sm font-semibold text-amber-900">
        Unmet Constraints
      </h2>

      {hasUnmetCoverage && (
        <div>
          <p className="text-xs font-semibold text-amber-800 mb-1">
            Unmet Coverage Requirements
          </p>
          <ul className="space-y-1">
            {result.unmet_coverage.map((u, i) => (
              <li key={i} className="text-xs text-amber-800">
                {deptMap.get(u.department_id) ?? `Dept ${u.department_id}`} ·{" "}
                {DAY_NAMES_FULL[u.day_of_week]} ·{" "}
                {u.start_time.slice(0, 5)} – {u.end_time.slice(0, 5)} ·{" "}
                needs {u.min_staff} staff
              </li>
            ))}
          </ul>
        </div>
      )}

      {hasUnmetRole && (
        <div>
          <p className="text-xs font-semibold text-amber-800 mb-1">
            Unmet Role Requirements
          </p>
          <ul className="space-y-1">
            {result.unmet_role_requirements.map((u, i) => (
              <li key={i} className="text-xs text-amber-800">
                {u.department_id !== null
                  ? `${deptMap.get(u.department_id) ?? `Dept ${u.department_id}`} · `
                  : ""}
                {u.day_of_week !== null ? DAY_NAMES_FULL[u.day_of_week] : "Every day"} ·{" "}
                {u.start_time.slice(0, 5)} – {u.end_time.slice(0, 5)} ·{" "}
                {u.requires_manager
                  ? `≥${u.min_manager_count} manager`
                  : u.requires_keyholder
                  ? "keyholder needed"
                  : "role constraint"}
              </li>
            ))}
          </ul>
        </div>
      )}

      {hasUnmetHours && (
        <div>
          <p className="text-xs font-semibold text-amber-800 mb-1">
            Contracted Hours Shortfalls
          </p>
          <ul className="space-y-1">
            {unmetHoursEntries.map(([empIdStr, shortfall]) => {
              const emp = empMap.get(Number(empIdStr));
              const name = emp
                ? `${emp.firstname} ${emp.surname}`
                : `Employee ${empIdStr}`;
              return (
                <li key={empIdStr} className="text-xs text-amber-800">
                  {name} · {shortfall.toFixed(1)}h below contracted hours
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {result.warnings.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-amber-800 mb-1">Warnings</p>
          <ul className="space-y-1">
            {result.warnings.map((w, i) => (
              <li key={i} className="text-xs text-amber-800">
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────

export default function ScheduleView() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();

  // Navigation
  const [selectedDate, setSelectedDate] = useState(new Date());

  // Filters
  const [showDrafts, setShowDrafts] = useState(false);
  const [selectedDeptId, setSelectedDeptId] = useState<number | null>(null);
  const [selectedStoreId, setSelectedStoreId] = useState<number | null>(null);

  // Data
  const [employees, setEmployees] = useState<EmployeeWithUserResponse[]>([]);
  const [shifts, setShifts] = useState<ShiftResponse[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [empDepts, setEmpDepts] = useState<Map<number, number[]>>(new Map());
  const [empPrimaryDepts, setEmpPrimaryDepts] = useState<Map<number, number>>(new Map());
  const [loading, setLoading] = useState(true);

  // Generate state
  const [generateExpanded, setGenerateExpanded] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generatedShiftIds, setGeneratedShiftIds] = useState<number[]>([]);
  const [generateResult, setGenerateResult] = useState<GenerateScheduleResponse | null>(null);

  // Manual shift state
  const [manualExpanded, setManualExpanded] = useState(false);
  const [previewShifts, setPreviewShifts] = useState<PreviewShift[]>([]);

  // Delete confirmation
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function confirmDelete() {
    if (!pendingDeleteId || !resolvedStoreId) return;
    setDeleting(true);
    try {
      await shiftsApi.delete(pendingDeleteId);
      const dayStart = new Date(selectedDate);
      dayStart.setHours(0, 0, 0, 0);
      const dayEnd = new Date(selectedDate);
      dayEnd.setHours(23, 59, 59, 999);
      const r = await shiftsApi.list({
        store_id: resolvedStoreId,
        start_date: dayStart.toISOString(),
        end_date: dayEnd.toISOString(),
        limit: 500,
      });
      setShifts(r.data);
    } finally {
      setDeleting(false);
      setPendingDeleteId(null);
    }
  }

  // Load static data once
  useEffect(() => {
    departmentsApi.list().then((r) => setDepartments(r.data));
    if (isAdmin) {
      storesApi.list().then((r) => setStores(r.data));
    }
  }, [isAdmin]);

  // Load employees when store context is available
  useEffect(() => {
    if (isAdmin && !selectedStoreId) return;
    const storeParam = isAdmin ? selectedStoreId! : undefined;
    employeesApi.list(storeParam).then((r) => setEmployees(r.data));
  }, [isAdmin, selectedStoreId]);

  // Resolve store ID: admin picks explicitly; managers derive from their employees
  const resolvedStoreId = useMemo(() => {
    if (isAdmin) return selectedStoreId;
    return employees[0]?.store_id ?? null;
  }, [isAdmin, selectedStoreId, employees]);

  // Load employee-department assignments once store is resolved (single effect, no race)
  useEffect(() => {
    if (!resolvedStoreId) return;
    employeeDepartmentsApi.listByStore(resolvedStoreId).then((r) => {
      const map = new Map<number, number[]>();
      const primaryMap = new Map<number, number>();
      for (const ed of r.data as EmployeeDepartmentResponse[]) {
        if (!map.has(ed.employee_id)) map.set(ed.employee_id, []);
        map.get(ed.employee_id)!.push(ed.department_id);
        if (ed.is_primary) primaryMap.set(ed.employee_id, ed.department_id);
      }
      setEmpDepts(map);
      setEmpPrimaryDepts(primaryMap);
    });
  }, [resolvedStoreId]);

  // Load shifts for selected day
  useEffect(() => {
    if (!resolvedStoreId) {
      if (!isAdmin) setLoading(false);
      return;
    }
    setLoading(true);
    const dayStart = new Date(selectedDate);
    dayStart.setHours(0, 0, 0, 0);
    const dayEnd = new Date(selectedDate);
    dayEnd.setHours(23, 59, 59, 999);

    shiftsApi
      .list({
        store_id: resolvedStoreId,
        start_date: dayStart.toISOString(),
        end_date: dayEnd.toISOString(),
        limit: 500,
      })
      .then((r) => setShifts(r.data))
      .catch(() => setShifts([]))
      .finally(() => setLoading(false));
  }, [selectedDate, resolvedStoreId, isAdmin]);

  // Dept map for name lookup
  const deptMap = useMemo(() => {
    const m = new Map<number, string>();
    for (const d of departments) m.set(d.id, d.name);
    return m;
  }, [departments]);

  // Parse shifts
  const parsedShifts: ParsedShift[] = useMemo(() => {
    return shifts
      .filter(
        (s) =>
          s.status === ShiftStatus.PUBLISHED ||
          (showDrafts && s.status === ShiftStatus.DRAFT)
      )
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
  }, [shifts, showDrafts, deptMap]);

  // Shifts grouped by employee
  const shiftsByEmployee = useMemo(() => {
    const m = new Map<number, ParsedShift[]>();
    for (const s of parsedShifts) {
      if (!m.has(s.employeeId)) m.set(s.employeeId, []);
      m.get(s.employeeId)!.push(s);
    }
    return m;
  }, [parsedShifts]);

  // Filter employees by department
  const filteredEmployees = useMemo(() => {
    if (!selectedDeptId) return employees;
    return employees.filter((e) => {
      const depts = empDepts.get(e.id) ?? [];
      return depts.includes(selectedDeptId);
    });
  }, [employees, selectedDeptId, empDepts]);

  // Navigation — week-based
  const weekMonday = useMemo(() => {
    const d = new Date(selectedDate);
    const day = d.getDay();
    const diff = day === 0 ? -6 : 1 - day; // shift to Monday
    d.setDate(d.getDate() + diff);
    d.setHours(0, 0, 0, 0);
    return d;
  }, [selectedDate]);

  const prevWeek = () => setSelectedDate((d) => addDays(d, -7));
  const nextWeek = () => setSelectedDate((d) => addDays(d, 7));
  const goToday = () => setSelectedDate(new Date());

  const dateLabel = format(selectedDate, "EEEE, d MMMM yyyy");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Schedule</h1>
          <p className="text-sm text-muted-foreground mt-0.5">{dateLabel}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Store selector — admin only */}
          {isAdmin && (
            <select
              className="h-9 rounded-md border bg-background px-3 text-sm"
              value={selectedStoreId ?? ""}
              onChange={(e) =>
                setSelectedStoreId(e.target.value ? Number(e.target.value) : null)
              }
            >
              <option value="">Select store…</option>
              {stores.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          )}

          {/* Department filter */}
          <select
            className="h-9 rounded-md border bg-background px-3 text-sm"
            value={selectedDeptId ?? ""}
            onChange={(e) =>
              setSelectedDeptId(e.target.value ? Number(e.target.value) : null)
            }
          >
            <option value="">All Departments</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>

          {/* Draft toggle */}
          <Button
            variant={showDrafts ? "default" : "outline"}
            size="sm"
            onClick={() => setShowDrafts((v) => !v)}
          >
            {showDrafts ? "Drafts: On" : "Drafts: Off"}
          </Button>
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

      {/* Delete confirmation dialog */}
      <AlertDialog open={pendingDeleteId !== null} onOpenChange={(open) => { if (!open) setPendingDeleteId(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete shift?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove the shift. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Admin: prompt to select store */}
      {isAdmin && !selectedStoreId && (
        <div className="rounded-lg border bg-card p-8 text-center text-muted-foreground text-sm">
          Select a store above to view the schedule.
        </div>
      )}

      {/* Gantt + generate panel */}
      {(resolvedStoreId || !isAdmin) && (
        <>
          {loading ? (
            <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
              Loading schedule…
            </div>
          ) : (
            <EmployeeGantt
              employees={filteredEmployees}
              shiftsByEmployee={shiftsByEmployee}
              previewShifts={previewShifts.filter(
                (p) => format(p.start, "yyyy-MM-dd") === format(selectedDate, "yyyy-MM-dd")
              )}
              onDeleteShift={setPendingDeleteId}
            />
          )}

          {/* Generate panel */}
          <GeneratePanel
            storeId={resolvedStoreId}
            expanded={generateExpanded}
            onToggle={() => setGenerateExpanded((v) => !v)}
            generating={generating}
            setGenerating={setGenerating}
            generatedShiftIds={generatedShiftIds}
            setGeneratedShiftIds={setGeneratedShiftIds}
            generateResult={generateResult}
            setGenerateResult={setGenerateResult}
            onShiftsChanged={() => {
              const dayStart = new Date(selectedDate);
              dayStart.setHours(0, 0, 0, 0);
              const dayEnd = new Date(selectedDate);
              dayEnd.setHours(23, 59, 59, 999);
              shiftsApi
                .list({
                  store_id: resolvedStoreId!,
                  start_date: dayStart.toISOString(),
                  end_date: dayEnd.toISOString(),
                  limit: 500,
                })
                .then((r) => setShifts(r.data));
            }}
            onViewSummary={(weekStart, shiftIds) =>
              navigate("/schedule/summary", {
                state: {
                  shiftIds,
                  weekStart,
                  storeId: resolvedStoreId,
                  generateResult,
                },
              })
            }
            onCancelDrafts={async (shiftIds) => {
              await scheduleApi.cancelBulk(shiftIds);
              setGeneratedShiftIds([]);
              setGenerateResult(null);
            }}
          />

          {/* Manual shift entry */}
          <ManualShiftPanel
            storeId={resolvedStoreId}
            employees={employees}
            empDepts={empDepts}
            empPrimaryDepts={empPrimaryDepts}
            departments={departments}
            selectedDate={selectedDate}
            expanded={manualExpanded}
            onToggle={() => setManualExpanded((v) => !v)}
            onShiftsChanged={() => {
              const dayStart = new Date(selectedDate);
              dayStart.setHours(0, 0, 0, 0);
              const dayEnd = new Date(selectedDate);
              dayEnd.setHours(23, 59, 59, 999);
              shiftsApi
                .list({
                  store_id: resolvedStoreId!,
                  start_date: dayStart.toISOString(),
                  end_date: dayEnd.toISOString(),
                  limit: 500,
                })
                .then((r) => setShifts(r.data));
            }}
            onPreviewChange={setPreviewShifts}
          />

          {/* Unmet rules */}
          {generateResult && (
            <UnmetRulesPanel
              result={generateResult}
              employees={employees}
              deptMap={deptMap}
            />
          )}
        </>
      )}
    </div>
  );
}
