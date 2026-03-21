import { Badge } from "@/components/ui/badge";
import type { EmployeeWithUserResponse } from "@/types";
import { ShiftStatus } from "@/types";
import { cn } from "@/lib/utils";

// ── Constants ────────────────────────────────────────────────────────

export const GRID_START = 0;
export const GRID_END = 24;
export const GRID_HOURS = GRID_END - GRID_START;

// ── Time helpers ─────────────────────────────────────────────────────

export function formatHourLabel(hour: number): string {
  if (hour === 24) return "00:00";
  return `${hour.toString().padStart(2, "0")}:00`;
}

export function formatShiftTime(dt: Date): string {
  return `${dt.getHours().toString().padStart(2, "0")}:${dt.getMinutes().toString().padStart(2, "0")}`;
}

// ── Types ────────────────────────────────────────────────────────────

export interface ParsedShift {
  id: number;
  employeeId: number;
  start: Date;
  end: Date;
  departmentId: number;
  departmentName: string;
  hours: number;
  status: ShiftStatus;
}

// ── Component ────────────────────────────────────────────────────────

export function EmployeeGantt({
  employees,
  shiftsByEmployee,
}: {
  employees: EmployeeWithUserResponse[];
  shiftsByEmployee: Map<number, ParsedShift[]>;
}) {
  const sortedEmployees = [...employees].sort((a, b) => {
    const aHas = (shiftsByEmployee.get(a.id) ?? []).length > 0 ? 0 : 1;
    const bHas = (shiftsByEmployee.get(b.id) ?? []).length > 0 ? 0 : 1;
    return aHas - bHas;
  });

  const hourLabels = Array.from(
    { length: GRID_HOURS / 2 + 1 },
    (_, i) => GRID_START + i * 2
  ).filter((h) => h < GRID_END);

  return (
    <div className="rounded-lg border bg-card">
      {/* Timeline header */}
      <div className="flex pb-2 pt-3 px-1">
        <div className="w-40 shrink-0" />
        <div className="flex-1 relative h-5 pr-6">
          {hourLabels.map((h) => {
            const pct = ((h - GRID_START) / GRID_HOURS) * 100;
            return (
              <span
                key={h}
                className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 text-xs text-muted-foreground"
                style={{ left: `${pct}%` }}
              >
                {formatHourLabel(h)}
              </span>
            );
          })}
        </div>
      </div>

      {/* Employee rows */}
      <div className="space-y-0">
        {sortedEmployees.length === 0 && (
          <div className="flex items-center justify-center py-12 text-muted-foreground text-sm border-t">
            No employees found.
          </div>
        )}
        {sortedEmployees.map((emp) => {
          const empShifts = shiftsByEmployee.get(emp.id) ?? [];
          const hasShifts = empShifts.length > 0;

          return (
            <div
              key={emp.id}
              className={cn(
                "flex border-t border-border/80",
                hasShifts ? "min-h-[3.5rem]" : "min-h-[1.75rem]"
              )}
            >
              {/* Employee label */}
              <div className="w-40 shrink-0 flex flex-col justify-center px-3 py-1">
                <span
                  className={cn(
                    "text-xs font-medium truncate",
                    hasShifts ? "text-foreground" : "text-muted-foreground"
                  )}
                >
                  {emp.firstname} {emp.surname}
                </span>
                {hasShifts && (emp.is_keyholder || emp.is_manager) && (
                  <div className="flex gap-1 mt-0.5">
                    {emp.is_manager && (
                      <Badge variant="outline" className="text-[9px] px-1 py-0 h-4">
                        Mgr
                      </Badge>
                    )}
                    {emp.is_keyholder && !emp.is_manager && (
                      <Badge variant="outline" className="text-[9px] px-1 py-0 h-4">
                        KH
                      </Badge>
                    )}
                  </div>
                )}
              </div>

              {/* Timeline area */}
              <div className="flex-1 relative py-1.5 px-1 pr-6">
                {/* Gridlines */}
                {Array.from({ length: GRID_HOURS + 1 }, (_, i) => {
                  const pct = (i / GRID_HOURS) * 100;
                  const isMajor = i % 2 === 0;
                  return (
                    <div
                      key={i}
                      className={cn(
                        "absolute top-0 bottom-0",
                        isMajor ? "bg-border" : "bg-border/50"
                      )}
                      style={{ left: `${pct}%`, width: isMajor ? "2px" : "1px" }}
                    />
                  );
                })}

                {/* Shift badges */}
                {empShifts.map((shift) => {
                  const startH =
                    shift.start.getHours() + shift.start.getMinutes() / 60;
                  const endH = shift.end.getHours() + shift.end.getMinutes() / 60;
                  const left = ((startH - GRID_START) / GRID_HOURS) * 100;
                  const width = ((endH - startH) / GRID_HOURS) * 100;
                  const isDraft = shift.status === ShiftStatus.DRAFT;

                  return (
                    <div
                      key={shift.id}
                      className={cn(
                        "absolute top-1 bottom-1 rounded-md flex items-center justify-between px-2 overflow-hidden",
                        isDraft
                          ? "bg-primary/20 border border-dashed border-primary/60"
                          : "bg-primary border border-primary"
                      )}
                      style={{ left: `${left}%`, width: `${width}%` }}
                      title={`${emp.firstname} ${emp.surname} · ${shift.departmentName} · ${shift.status}`}
                    >
                      <span
                        className={cn(
                          "text-xs font-semibold truncate",
                          isDraft ? "text-primary" : "text-primary-foreground"
                        )}
                      >
                        {formatShiftTime(shift.start)} – {formatShiftTime(shift.end)}
                        <span
                          className={cn(
                            "ml-1.5 font-normal",
                            isDraft
                              ? "text-primary/70"
                              : "text-primary-foreground/80"
                          )}
                        >
                          {shift.departmentName}
                        </span>
                      </span>
                      <span
                        className={cn(
                          "text-xs font-medium ml-2 shrink-0",
                          isDraft ? "text-primary/70" : "text-primary-foreground/70"
                        )}
                      >
                        {shift.hours}h
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
