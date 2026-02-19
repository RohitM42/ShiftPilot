import { useState, useEffect, useMemo } from "react";
import {
  startOfWeek,
  endOfWeek,
  addWeeks,
  format,
  eachDayOfInterval,
  isThisWeek,
  parseISO,
  getDay,
} from "date-fns";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { meApi } from "@/services/api";
import type { ShiftResponse } from "@/types";
import { ShiftStatus } from "@/types";
import { cn } from "@/lib/utils";

// ── Constants ────────────────────────────────────────────────────────

const DEPT_MAP: Record<number, string> = {
  100001: "Tills",
  100002: "Shop Floor",
  100003: "CS",
};

const GRID_START = 0; // midnight
const GRID_END = 24; // midnight
const GRID_HOURS = GRID_END - GRID_START;

const DAY_LABELS_SHORT = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];

// ── Time formatting ──────────────────────────────────────────────────

const is24Hour = (() => {
  const formatted = new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
  }).format(new Date(2000, 0, 1, 13));
  return formatted.includes("13");
})();

function formatHourLabel(hour: number): string {
  if (hour === 24) return is24Hour ? "00:00" : "12am";
  if (is24Hour) return `${hour.toString().padStart(2, "0")}:00`;
  const period = hour >= 12 ? "pm" : "am";
  const h = hour % 12 || 12;
  return `${h}${period}`;
}

function formatShiftTime(dt: Date): string {
  if (is24Hour) return format(dt, "HH:mm");
  return format(dt, "h:mma").toLowerCase();
}

// ── Helpers ──────────────────────────────────────────────────────────

function getWeekStart(d: Date): Date {
  return startOfWeek(d, { weekStartsOn: 1 });
}

function getWeekEnd(d: Date): Date {
  return endOfWeek(d, { weekStartsOn: 1 });
}

/** Convert day_of_week from JS (0=Sun) to our grid index (0=Mon) */
function dayIndex(dt: Date): number {
  const d = getDay(dt); // 0=Sun, 1=Mon...
  return d === 0 ? 6 : d - 1;
}

// ── Types ────────────────────────────────────────────────────────────

interface ParsedShift {
  id: number;
  start: Date;
  end: Date;
  departmentName: string;
  dayIdx: number;
  hours: number;
}

// ── Component ────────────────────────────────────────────────────────

export default function MyShifts() {
  const [weekOffset, setWeekOffset] = useState(0);
  const [shifts, setShifts] = useState<ShiftResponse[]>([]);
  const [loading, setLoading] = useState(true);

  const weekStart = useMemo(() => getWeekStart(addWeeks(new Date(), weekOffset)), [weekOffset]);
  const weekEnd = useMemo(() => getWeekEnd(weekStart), [weekStart]);
  const days = useMemo(() => eachDayOfInterval({ start: weekStart, end: weekEnd }), [weekStart, weekEnd]);
  const isCurrentWeek = isThisWeek(weekStart, { weekStartsOn: 1 });

  // Fetch shifts
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    meApi
      .getShifts({
        start_date: weekStart.toISOString(),
        end_date: weekEnd.toISOString(),
      })
      .then((res) => {
        if (!cancelled) setShifts(res.data);
      })
      .catch(() => {
        if (!cancelled) setShifts([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [weekStart, weekEnd]);

  // Parse + filter
  const parsed: ParsedShift[] = useMemo(() => {
    return shifts
      .filter((s) => s.status === ShiftStatus.PUBLISHED)
      .map((s) => {
        const start = parseISO(s.start_datetime_utc);
        const end = parseISO(s.end_datetime_utc);
        return {
          id: s.id,
          start,
          end,
          departmentName: DEPT_MAP[s.department_id] ?? `Dept ${s.department_id}`,
          dayIdx: dayIndex(start),
          hours: Math.round(((end.getTime() - start.getTime()) / 3600000) * 10) / 10,
        };
      });
  }, [shifts]);

  // Group by day index
  const shiftsByDay = useMemo(() => {
    const map = new Map<number, ParsedShift[]>();
    for (let i = 0; i < 7; i++) map.set(i, []);
    for (const s of parsed) {
      map.get(s.dayIdx)?.push(s);
    }
    return map;
  }, [parsed]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">My Shifts</h1>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-sm text-muted-foreground">
              {format(weekStart, "d MMM")} – {format(weekEnd, "d MMM yyyy")}
            </span>
            {isCurrentWeek && (
              <span className="text-xs text-muted-foreground/70">This week</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="outline" size="icon" onClick={() => setWeekOffset((o) => o - 1)}>
            <ChevronLeft size={18} />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-xs"
            onClick={() => setWeekOffset(0)}
            disabled={isCurrentWeek}
          >
            Today
          </Button>
          <Button variant="outline" size="icon" onClick={() => setWeekOffset((o) => o + 1)}>
            <ChevronRight size={18} />
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
          Loading shifts…
        </div>
      ) : (
        <>
          {/* Gantt view — desktop */}
          <GanttGrid days={days} shiftsByDay={shiftsByDay} />

          {/* Compact view — mobile */}
          <CompactView days={days} shiftsByDay={shiftsByDay} />
        </>
      )}
    </div>
  );
}

// ── Gantt Grid ───────────────────────────────────────────────────────

function GanttGrid({
  days,
  shiftsByDay,
}: {
  days: Date[];
  shiftsByDay: Map<number, ParsedShift[]>;
}) {
  const hourLabels = Array.from({ length: GRID_HOURS / 2 + 1 }, (_, i) => GRID_START + i * 2).filter(
    (h) => h < GRID_END
  );

  return (
    <div className="hidden lg:block rounded-lg border bg-card overflow-hidden">
      {/* Hour labels row */}
      <div className="flex border-b">
        <div className="w-20 shrink-0" />
        <div className="flex-1 relative h-8 pr-6">
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

      {/* Day rows */}
      {days.map((day, idx) => {
        const dayShifts = shiftsByDay.get(idx) ?? [];
        const isToday = format(day, "yyyy-MM-dd") === format(new Date(), "yyyy-MM-dd");

        return (
          <div
            key={idx}
            className={cn(
              "flex border-b last:border-b-0 min-h-[3.25rem]",
              isToday && "bg-primary/[0.03]"
            )}
          >
            {/* Day label */}
            <div className="w-20 shrink-0 flex flex-col justify-center px-3 border-r">
              <span className={cn("text-xs font-medium", isToday ? "text-primary" : "text-foreground")}>
                {DAY_LABELS_SHORT[idx]}
              </span>
              <span className="text-[11px] text-muted-foreground">{format(day, "d MMM")}</span>
            </div>

            {/* Grid area */}
            <div className="flex-1 relative py-2 px-1 pr-6">
              {/* Hour gridlines */}
              {Array.from({ length: GRID_HOURS + 1 }, (_, i) => {
                const pct = (i / GRID_HOURS) * 100;
                const isMajor = i % 2 === 0;
                return (
                  <div
                    key={i}
                    className={cn(
                      "absolute top-0 bottom-0 w-px",
                      isMajor ? "bg-border/60" : "bg-border/30"
                    )}
                    style={{ left: `${pct}%` }}
                  />
                );
              })}

              {/* Shift bars */}
              {dayShifts.map((shift) => {
                const startH = shift.start.getHours() + shift.start.getMinutes() / 60;
                const endH = shift.end.getHours() + shift.end.getMinutes() / 60;
                const left = ((startH - GRID_START) / GRID_HOURS) * 100;
                const width = ((endH - startH) / GRID_HOURS) * 100;

                return (
                  <div
                    key={shift.id}
                    className="absolute top-1.5 bottom-1.5 rounded-md bg-primary border border-primary flex items-center justify-between px-2 overflow-hidden"
                    style={{ left: `${left}%`, width: `${width}%` }}
                    title={`${formatShiftTime(shift.start)} – ${formatShiftTime(shift.end)} · ${shift.departmentName}`}
                  >
                    <span className="text-xs font-semibold text-primary-foreground truncate">
                      {formatShiftTime(shift.start)} – {formatShiftTime(shift.end)}
                      <span className="ml-1.5 font-normal text-primary-foreground/80">
                        {shift.departmentName}
                      </span>
                    </span>
                    <span className="text-xs font-medium text-primary-foreground/70 ml-2 shrink-0">
                      {shift.hours}h
                    </span>
                  </div>
                );
              })}

              {/* Empty state for no shifts */}
              {dayShifts.length === 0 && (
                <div className="h-full min-h-[1.25rem]" />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Compact View ─────────────────────────────────────────────────────

function CompactView({
  days,
  shiftsByDay,
}: {
  days: Date[];
  shiftsByDay: Map<number, ParsedShift[]>;
}) {
  return (
    <div className="lg:hidden space-y-2">
      {days.map((day, idx) => {
        const dayShifts = shiftsByDay.get(idx) ?? [];
        const isToday = format(day, "yyyy-MM-dd") === format(new Date(), "yyyy-MM-dd");

        return (
          <div key={idx} className={cn("rounded-lg border bg-card p-3", isToday && "ring-1 ring-primary/30")}>
            <div className="flex items-baseline gap-2 mb-2">
              <span className={cn("text-sm font-semibold", isToday ? "text-primary" : "text-foreground")}>
                {DAY_LABELS_SHORT[idx]}
              </span>
              <span className="text-xs text-muted-foreground">{format(day, "d MMM")}</span>
            </div>

            {dayShifts.length === 0 ? (
              <p className="text-xs text-muted-foreground/60">No shifts</p>
            ) : (
              <div className="space-y-1.5">
                {dayShifts.map((shift) => (
                  <div
                    key={shift.id}
                    className="w-full rounded-md bg-primary border border-primary px-3 py-2 flex items-center justify-between"
                  >
                    <div>
                      <span className="text-xs font-semibold text-primary-foreground">
                        {formatShiftTime(shift.start)} – {formatShiftTime(shift.end)}
                      </span>
                      <span className="ml-2 text-xs text-primary-foreground/80">
                        {shift.departmentName}
                      </span>
                    </div>
                    <span className="text-xs font-medium text-primary-foreground/70 shrink-0">
                      {shift.hours}h
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}