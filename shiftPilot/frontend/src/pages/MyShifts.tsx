import { useState, useEffect, useMemo, useCallback } from "react";
import {
  startOfWeek,
  endOfWeek,
  startOfMonth,
  endOfMonth,
  addWeeks,
  addMonths,
  differenceInWeeks,
  format,
  eachDayOfInterval,
  isThisWeek,
  isThisMonth,
  isSameMonth,
  isSameDay,
  parseISO,
  getDay,
} from "date-fns";
import { ChevronLeft, ChevronRight, Calendar, LayoutList } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageLoader } from "@/components/PageLoader";
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

const GRID_START = 0;
const GRID_END = 24;
const GRID_HOURS = GRID_END - GRID_START;

const DAY_LABELS_SHORT = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];

type ViewMode = "week" | "month";

// ── Time formatting ──────────────────────────────────────────────────

function formatHourLabel(hour: number): string {
  if (hour === 24) return "00:00";
  return `${hour.toString().padStart(2, "0")}:00`;
}

function formatShiftTime(dt: Date): string {
  return format(dt, "HH:mm");
}

function formatShiftTimeShort(dt: Date): string {
  return format(dt, "HH:mm");
}

// ── Helpers ──────────────────────────────────────────────────────────

function getWeekStart(d: Date): Date {
  return startOfWeek(d, { weekStartsOn: 1 });
}

function getWeekEnd(d: Date): Date {
  return endOfWeek(d, { weekStartsOn: 1 });
}

function dayIndex(dt: Date): number {
  const d = getDay(dt);
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
  updatedAt: Date;
}

// ── Component ────────────────────────────────────────────────────────

export default function MyShifts() {
  const [view, setView] = useState<ViewMode>("week");
  const [weekOffset, setWeekOffset] = useState(0);
  const [monthOffset, setMonthOffset] = useState(0);
  const [shifts, setShifts] = useState<ShiftResponse[]>([]);
  const [loading, setLoading] = useState(true);

  // Week view dates
  const weekStart = useMemo(() => getWeekStart(addWeeks(new Date(), weekOffset)), [weekOffset]);
  const weekEnd = useMemo(() => getWeekEnd(weekStart), [weekStart]);
  const weekDays = useMemo(() => eachDayOfInterval({ start: weekStart, end: weekEnd }), [weekStart, weekEnd]);
  const isCurrentWeek = isThisWeek(weekStart, { weekStartsOn: 1 });

  // Month view dates
  const monthDate = useMemo(() => addMonths(new Date(), monthOffset), [monthOffset]);
  const monthStart = useMemo(() => startOfMonth(monthDate), [monthDate]);
  const monthEnd = useMemo(() => endOfMonth(monthDate), [monthDate]);
  const isCurrMonth = isThisMonth(monthDate);

  // Fetch range depends on view
  const fetchStart = view === "week" ? weekStart : getWeekStart(monthStart);
  const fetchEnd = view === "week" ? weekEnd : getWeekEnd(monthEnd);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    meApi
      .getShifts({
        start_date: fetchStart.toISOString(),
        end_date: fetchEnd.toISOString(),
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
  }, [fetchStart.toISOString(), fetchEnd.toISOString()]);

  // Parse + filter published
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
          updatedAt: parseISO(s.updated_at),
        };
      });
  }, [shifts]);

  // Group by day index (week view)
  const shiftsByDay = useMemo(() => {
    const map = new Map<number, ParsedShift[]>();
    for (let i = 0; i < 7; i++) map.set(i, []);
    for (const s of parsed) {
      map.get(s.dayIdx)?.push(s);
    }
    return map;
  }, [parsed]);

  // Navigate from month day click → week view
  const goToWeekOf = useCallback((date: Date) => {
    const targetWeekStart = getWeekStart(date);
    const currentWeekStart = getWeekStart(new Date());
    const diff = differenceInWeeks(targetWeekStart, currentWeekStart);
    setWeekOffset(diff);
    setView("week");
  }, []);

  // Nav handlers
  const prev = () => view === "week" ? setWeekOffset((o) => o - 1) : setMonthOffset((o) => o - 1);
  const next = () => view === "week" ? setWeekOffset((o) => o + 1) : setMonthOffset((o) => o + 1);
  const goToday = () => view === "week" ? setWeekOffset(0) : setMonthOffset(0);
  const isTodayDisabled = view === "week" ? isCurrentWeek : isCurrMonth;

  // Header subtitle
  const subtitle = view === "week"
    ? `${format(weekStart, "d MMM")} – ${format(weekEnd, "d MMM yyyy")}`
    : format(monthDate, "MMMM yyyy");

  const todayLabel = view === "week" && isCurrentWeek
    ? "This week"
    : view === "month" && isCurrMonth
      ? "This month"
      : null;

  if (loading) return <PageLoader />;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">My Shifts</h1>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-sm text-muted-foreground">{subtitle}</span>
            {todayLabel && (
              <span className="text-xs text-muted-foreground/70">{todayLabel}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* View toggle */}
          <div className="flex items-center rounded-md border">
            <Button
              variant={view === "week" ? "default" : "ghost"}
              size="sm"
              className="rounded-r-none gap-1.5"
              onClick={() => setView("week")}
            >
              <LayoutList size={15} />
              <span className="hidden sm:inline">Week</span>
            </Button>
            <Button
              variant={view === "month" ? "default" : "ghost"}
              size="sm"
              className="rounded-l-none gap-1.5"
              onClick={() => setView("month")}
            >
              <Calendar size={15} />
              <span className="hidden sm:inline">Month</span>
            </Button>
          </div>

          {/* Navigation */}
          <div className="flex items-center gap-1">
            <Button variant="outline" size="icon" onClick={prev}>
              <ChevronLeft size={18} />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs"
              onClick={goToday}
              disabled={isTodayDisabled}
            >
              Today
            </Button>
            <Button variant="outline" size="icon" onClick={next}>
              <ChevronRight size={18} />
            </Button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
          Loading shifts…
        </div>
      ) : view === "week" ? (
        <>
          <GanttGrid days={weekDays} shiftsByDay={shiftsByDay} />
          <CompactView days={weekDays} shiftsByDay={shiftsByDay} />
        </>
      ) : (
        <MonthView
          monthDate={monthDate}
          monthStart={monthStart}
          monthEnd={monthEnd}
          shifts={parsed}
          onDayClick={goToWeekOf}
        />
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
    <div className="hidden lg:block rounded-lg border bg-card">
      <div className="flex pb-2 pt-3 px-1">
        <div className="w-20 shrink-0" />
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

      <div className="space-y-0">
        {days.map((day, idx) => {
          const dayShifts = shiftsByDay.get(idx) ?? [];
          const isToday = isSameDay(day, new Date());

          return (
            <div
              key={idx}
              className={cn(
                "flex min-h-[3.5rem] border-t border-border/80",
                isToday && "bg-primary/[0.03]"
              )}
              style={{ borderTopWidth: "2px" }}
            >
              <div className="w-20 shrink-0 flex flex-col justify-center px-3">
                <span className={cn("text-xs font-semibold", isToday ? "text-primary" : "text-foreground")}>
                  {DAY_LABELS_SHORT[idx]}
                </span>
                <span className="text-[11px] text-muted-foreground">{format(day, "d MMM")}</span>
              </div>

              <div className="flex-1 relative py-2.5 px-1 pr-6">
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
                      title={`Last updated: ${format(shift.updatedAt, "d MMM yyyy, HH:mm")}`}
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

                {dayShifts.length === 0 && (
                  <div className="h-full min-h-[1.25rem]" />
                )}
              </div>
            </div>
          );
        })}
      </div>
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
        const isToday = isSameDay(day, new Date());

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

// ── Month View ───────────────────────────────────────────────────────

function MonthView({
  monthDate,
  monthStart,
  monthEnd,
  shifts,
  onDayClick,
}: {
  monthDate: Date;
  monthStart: Date;
  monthEnd: Date;
  shifts: ParsedShift[];
  onDayClick: (date: Date) => void;
}) {
  const shiftsByDate = useMemo(() => {
    const map = new Map<string, ParsedShift[]>();
    for (const s of shifts) {
      const key = format(s.start, "yyyy-MM-dd");
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(s);
    }
    return map;
  }, [shifts]);

  // Calendar grid: Monday of week containing monthStart → Sunday of week containing monthEnd
  const gridStart = getWeekStart(monthStart);
  const gridEnd = getWeekEnd(monthEnd);
  const allDays = eachDayOfInterval({ start: gridStart, end: gridEnd });

  const weeks: Date[][] = [];
  for (let i = 0; i < allDays.length; i += 7) {
    weeks.push(allDays.slice(i, i + 7));
  }

  const today = new Date();

  return (
    <div className="rounded-lg border bg-card p-3 sm:p-5">
      {/* Day headers */}
      <div className="grid grid-cols-7 mb-2">
        {DAY_LABELS_SHORT.map((d) => (
          <div key={d} className="text-center text-xs font-semibold text-muted-foreground py-1">
            {d}
          </div>
        ))}
      </div>

      {/* Weeks */}
      <div className="space-y-1">
        {weeks.map((week, wi) => (
          <div key={wi} className="grid grid-cols-7">
            {week.map((day) => {
              const key = format(day, "yyyy-MM-dd");
              const dayShifts = shiftsByDate.get(key) ?? [];
              const inMonth = isSameMonth(day, monthDate);
              const isToday = isSameDay(day, today);
              const hasShifts = dayShifts.length > 0;

              return (
                <div
                  key={key}
                  className={cn(
                    "flex flex-col items-center py-1.5 sm:py-2 min-h-[3.5rem] sm:min-h-[4.5rem]",
                    !inMonth && "opacity-30"
                  )}
                >
                  {hasShifts ? (
                    <button
                      onClick={() => onDayClick(day)}
                      className={cn(
                        "w-8 h-8 sm:w-9 sm:h-9 rounded-full flex items-center justify-center text-sm font-semibold transition-colors cursor-pointer",
                        "bg-primary text-primary-foreground hover:bg-primary/85",
                        isToday && "ring-2 ring-primary ring-offset-2"
                      )}
                    >
                      {format(day, "d")}
                    </button>
                  ) : (
                    <div
                      className={cn(
                        "w-8 h-8 sm:w-9 sm:h-9 rounded-full flex items-center justify-center text-sm",
                        isToday
                          ? "font-semibold text-primary ring-2 ring-primary/30 ring-offset-1"
                          : "text-foreground"
                      )}
                    >
                      {format(day, "d")}
                    </div>
                  )}

                  {hasShifts && (
                    <div className="mt-0.5 flex flex-col items-center">
                      {dayShifts.map((s) => (
                        <span key={s.id} className="text-[10px] sm:text-xs text-muted-foreground leading-tight">
                          {formatShiftTimeShort(s.start)}–{formatShiftTimeShort(s.end)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}