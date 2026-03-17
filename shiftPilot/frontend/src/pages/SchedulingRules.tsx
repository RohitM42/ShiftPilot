import { useState, useEffect, useMemo } from "react";
import { Send, Pencil, Loader2, Plus, Trash2, X, ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/contexts/AuthContext";
import { aiInputsApi, aiProposalsApi, coverageApi, roleRequirementsApi, departmentsApi, storesApi } from "@/services/api";
import api from "@/services/api";
import { cn } from "@/lib/utils";
import { ProposalType, ProposalStatus } from "@/types";
import type { CoverageRequirementResponse, RoleRequirementResponse, AIProposalResponse, Department, Store } from "@/types";

// ── Constants ─────────────────────────────────────────────────────────

const GRID_START = 0;
const GRID_END = 24;
const GRID_HOURS = GRID_END - GRID_START;

const DAY_LABELS_SHORT = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];
const DAY_LABELS_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const PROPOSAL_STATUS_VARIANT: Record<ProposalStatus, "default" | "success" | "destructive" | "warning"> = {
  [ProposalStatus.PENDING]: "warning",
  [ProposalStatus.APPROVED]: "success",
  [ProposalStatus.REJECTED]: "destructive",
  [ProposalStatus.CANCELLED]: "default",
};

// ── Time helpers ──────────────────────────────────────────────────────

const is24Hour = (() => {
  const formatted = new Intl.DateTimeFormat(undefined, { hour: "numeric" }).format(new Date(2000, 0, 1, 13));
  return formatted.includes("13");
})();

function formatHourLabel(hour: number): string {
  if (hour === 24) return is24Hour ? "00:00" : "12am";
  if (is24Hour) return `${hour.toString().padStart(2, "0")}:00`;
  const period = hour >= 12 ? "pm" : "am";
  const h = hour % 12 || 12;
  return `${h}${period}`;
}

function formatRuleTime(timeStr: string | null): string {
  if (!timeStr) return "";
  const [h, m] = timeStr.split(":").map(Number);
  if (is24Hour) return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`;
  const period = h >= 12 ? "pm" : "am";
  const hour = h % 12 || 12;
  return m === 0 ? `${hour}${period}` : `${hour}:${m.toString().padStart(2, "0")}${period}`;
}

function timeToHours(timeStr: string | null): number {
  if (!timeStr) return 0;
  const [h, m] = timeStr.split(":").map(Number);
  return h + m / 60;
}

// ── Aggregate helpers ─────────────────────────────────────────────────

interface AggregateInterval {
  startHour: number;
  endHour: number;
  totalStaff: number;
}

function computeAggregateIntervals(rules: CoverageRequirementResponse[]): AggregateInterval[] {
  if (rules.length === 0) return [];

  const points = new Set<number>();
  for (const r of rules) {
    points.add(r.start_time_local ? timeToHours(r.start_time_local) : 0);
    points.add(r.end_time_local ? timeToHours(r.end_time_local) : 24);
  }

  const sorted = Array.from(points).sort((a, b) => a - b);
  const raw: AggregateInterval[] = [];

  for (let i = 0; i < sorted.length - 1; i++) {
    const s = sorted[i];
    const e = sorted[i + 1];
    const total = rules.reduce((sum, r) => {
      const rs = r.start_time_local ? timeToHours(r.start_time_local) : 0;
      const re = r.end_time_local ? timeToHours(r.end_time_local) : 24;
      return rs <= s && re >= e ? sum + r.min_staff : sum;
    }, 0);
    if (total > 0) raw.push({ startHour: s, endHour: e, totalStaff: total });
  }

  // merge consecutive intervals with same total
  const merged: AggregateInterval[] = [];
  for (const interval of raw) {
    const last = merged[merged.length - 1];
    if (last && last.totalStaff === interval.totalStaff && last.endHour === interval.startHour) {
      last.endHour = interval.endHour;
    } else {
      merged.push({ ...interval });
    }
  }
  return merged;
}

function coverageIntensityClass(staff: number): string {
  if (staff >= 4) return "bg-blue-400 border-blue-500 text-blue-900";
  if (staff === 3) return "bg-blue-300 border-blue-400 text-blue-900";
  if (staff === 2) return "bg-blue-200 border-blue-300 text-blue-800";
  return "bg-blue-100 border-blue-200 text-blue-700";
}

function roleBlockClass(requiresManager: boolean, requiresKeyholder: boolean): string {
  if (requiresManager && requiresKeyholder) return "bg-indigo-100 border-indigo-300 text-indigo-700";
  if (requiresManager) return "bg-purple-100 border-purple-300 text-purple-700";
  return "bg-amber-100 border-amber-300 text-amber-700";
}

function roleBlockLabel(r: RoleRequirementResponse): string {
  const parts: string[] = [];
  if (r.requires_manager) parts.push("Manager");
  if (r.requires_keyholder) parts.push("Keyholder");
  return parts.join(" + ") || "Role req";
}

// ── Grid lines (shared) ───────────────────────────────────────────────

function GridLines() {
  return (
    <>
      {Array.from({ length: GRID_HOURS + 1 }, (_, i) => {
        const pct = (i / GRID_HOURS) * 100;
        const isMajor = i % 2 === 0;
        return (
          <div
            key={i}
            className={cn("absolute top-0 bottom-0", isMajor ? "bg-border" : "bg-border/50")}
            style={{ left: `${pct}%`, width: isMajor ? "2px" : "1px" }}
          />
        );
      })}
    </>
  );
}

// ── Hour label header (shared) ────────────────────────────────────────

function HourLabelHeader() {
  const hourLabels = Array.from({ length: GRID_HOURS / 2 + 1 }, (_, i) => GRID_START + i * 2).filter(
    (h) => h < GRID_END
  );
  return (
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
  );
}

// ── Manual Scheduling Modal ───────────────────────────────────────────

interface ManualRow {
  id: number;
  ruleType: "COVERAGE" | "ROLE_REQUIREMENT";
  deptId: string;
  dayOfWeek: string;
  startTime: string;
  endTime: string;
  minStaff: number;
  requiresManager: boolean;
  requiresKeyholder: boolean;
}

function buildSummary(rows: ManualRow[], deptMap: Map<number, Department>): string {
  return rows
    .map((r) => {
      const day = r.dayOfWeek === "" ? "every day" : DAY_LABELS_FULL[parseInt(r.dayOfWeek)];
      const time = `${r.startTime}–${r.endTime}`;
      if (r.ruleType === "COVERAGE") {
        const dept = r.deptId ? (deptMap.get(parseInt(r.deptId))?.name ?? `Dept ${r.deptId}`) : "store";
        return `Coverage ${dept} ${day} ${time} ×${r.minStaff}`;
      }
      const roles = [r.requiresManager && "manager", r.requiresKeyholder && "keyholder"]
        .filter(Boolean)
        .join("+");
      return `${roles || "role"} req ${day} ${time}`;
    })
    .join(", ");
}

function ManualSchedulingModal({
  storeId,
  departments,
  onClose,
  onSubmit,
  submitting,
}: {
  storeId: number;
  departments: Department[];
  onClose: () => void;
  onSubmit: (rows: ManualRow[], storeId: number) => void;
  submitting: boolean;
}) {
  const [rows, setRows] = useState<ManualRow[]>([
    {
      id: Date.now(),
      ruleType: "COVERAGE",
      deptId: departments[0]?.id.toString() ?? "",
      dayOfWeek: "0",
      startTime: "09:00",
      endTime: "17:00",
      minStaff: 1,
      requiresManager: false,
      requiresKeyholder: false,
    },
  ]);

  const addRow = () =>
    setRows((prev) => [
      ...prev,
      {
        id: Date.now(),
        ruleType: "COVERAGE",
        deptId: departments[0]?.id.toString() ?? "",
        dayOfWeek: "0",
        startTime: "09:00",
        endTime: "17:00",
        minStaff: 1,
        requiresManager: false,
        requiresKeyholder: false,
      },
    ]);

  const removeRow = (id: number) => setRows((prev) => prev.filter((r) => r.id !== id));
  const updateRow = (id: number, patch: Partial<ManualRow>) =>
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));

  const deptMap = useMemo(
    () => new Map(departments.map((d) => [d.id, d])),
    [departments]
  );

  const selectClass =
    "rounded-md border bg-background px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring";
  const inputClass =
    "rounded-md border bg-background px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring w-24";

  return (
    <div className="rounded-lg border bg-card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold">Edit scheduling rules manually</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Changes will be submitted as proposals for review.
          </p>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} disabled={submitting}>
          <X size={16} />
        </Button>
      </div>

      <div className="space-y-2">
        {rows.map((row) => (
            <div
              key={row.id}
              className="flex flex-wrap items-center gap-2 rounded-lg border px-3 py-2.5 bg-muted/20"
            >
              {/* Rule type */}
              <select
                className={selectClass}
                value={row.ruleType}
                onChange={(e) =>
                  updateRow(row.id, {
                    ruleType: e.target.value as "COVERAGE" | "ROLE_REQUIREMENT",
                    requiresManager: false,
                    requiresKeyholder: false,
                  })
                }
              >
                <option value="COVERAGE">Coverage</option>
                <option value="ROLE_REQUIREMENT">Role Requirement</option>
              </select>

              {/* Department */}
              <select
                className={selectClass}
                value={row.deptId}
                onChange={(e) => updateRow(row.id, { deptId: e.target.value })}
              >
                {row.ruleType === "ROLE_REQUIREMENT" && (
                  <option value="">Store-wide</option>
                )}
                {departments.map((d) => (
                  <option key={d.id} value={d.id.toString()}>
                    {d.name}
                  </option>
                ))}
              </select>

              {/* Day */}
              <select
                className={selectClass}
                value={row.dayOfWeek}
                onChange={(e) => updateRow(row.id, { dayOfWeek: e.target.value })}
              >
                {row.ruleType === "ROLE_REQUIREMENT" && (
                  <option value="">Every day</option>
                )}
                {DAY_LABELS_FULL.map((d, idx) => (
                  <option key={idx} value={idx.toString()}>
                    {d}
                  </option>
                ))}
              </select>

              {/* Time range */}
              <input
                type="time"
                className={inputClass}
                value={row.startTime}
                onChange={(e) => updateRow(row.id, { startTime: e.target.value })}
              />
              <span className="text-xs text-muted-foreground">to</span>
              <input
                type="time"
                className={inputClass}
                value={row.endTime}
                onChange={(e) => updateRow(row.id, { endTime: e.target.value })}
              />

              {/* Coverage: min staff */}
              {row.ruleType === "COVERAGE" && (
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">Min staff</span>
                  <input
                    type="number"
                    min={1}
                    className="rounded-md border bg-background px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring w-16"
                    value={row.minStaff}
                    onChange={(e) => updateRow(row.id, { minStaff: Math.max(1, parseInt(e.target.value) || 1) })}
                  />
                </div>
              )}

              {/* Role: toggles */}
              {row.ruleType === "ROLE_REQUIREMENT" && (
                <>
                  <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={row.requiresManager}
                      onChange={(e) => updateRow(row.id, { requiresManager: e.target.checked })}
                      className="rounded"
                    />
                    Manager
                  </label>
                  <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={row.requiresKeyholder}
                      onChange={(e) => updateRow(row.id, { requiresKeyholder: e.target.checked })}
                      className="rounded"
                    />
                    Keyholder
                  </label>
                </>
              )}

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
          ))}
        </div>

      <div className="flex items-center justify-between">
        <Button variant="outline" size="sm" className="gap-1.5" onClick={addRow}>
          <Plus size={13} />
          Add row
        </Button>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={() => onSubmit(rows, storeId)}
            disabled={submitting || rows.length === 0}
          >
            {submitting && <Loader2 size={13} className="animate-spin mr-1.5" />}
            Submit for review
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Clarify Dialog ────────────────────────────────────────────────────

function ClarifyDialog({
  onConfirm,
  onCancel,
  loading,
}: {
  onConfirm: (clarification: string) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [text, setText] = useState("");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-background rounded-xl border shadow-xl w-full max-w-md mx-4 p-6 space-y-4">
        <div>
          <h2 className="text-base font-semibold">Request unclear</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Your request wasn't specific enough. Please add more detail so we can process it correctly.
          </p>
        </div>
        <textarea
          className="w-full rounded-md border bg-muted/30 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring resize-none"
          rows={3}
          placeholder='e.g. "I need 3 staff in the bakery on Saturday mornings from 7am to 1pm"'
          value={text}
          autoFocus
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (text.trim()) onConfirm(text.trim());
            }
          }}
        />
        <div className="flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onCancel} disabled={loading}>
            Cancel
          </Button>
          <Button size="sm" onClick={() => onConfirm(text.trim())} disabled={!text.trim() || loading}>
            {loading ? <Loader2 size={14} className="animate-spin mr-1.5" /> : null}
            Resubmit
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Coverage Grid (desktop) ───────────────────────────────────────────

function CoverageGrid({
  coverageRules,
  deptFilter,
  deptMap,
  expandedDays,
  onToggleExpand,
}: {
  coverageRules: CoverageRequirementResponse[];
  deptFilter: number | null;
  deptMap: Map<number, Department>;
  expandedDays: Set<number>;
  onToggleExpand: (day: number) => void;
}) {
  const activeRules = useMemo(() => coverageRules.filter((r) => r.active), [coverageRules]);

  // When a dept filter is active, show per-dept blocks for the full week (like MyAvailability)
  const filteredRules = useMemo(
    () => (deptFilter != null ? activeRules.filter((r) => r.department_id === deptFilter) : activeRules),
    [activeRules, deptFilter]
  );

  // Unique department IDs present in the active rules
  const deptIds = useMemo(
    () => Array.from(new Set(activeRules.map((r) => r.department_id))).sort((a, b) => a - b),
    [activeRules]
  );

  return (
    <div className="hidden lg:block rounded-lg border bg-card">
      <HourLabelHeader />
      <div className="space-y-0">
        {Array.from({ length: 7 }, (_, dayIdx) => {
          const dayRules = filteredRules.filter((r) => r.day_of_week === dayIdx);
          const allDayRules = activeRules.filter((r) => r.day_of_week === dayIdx);
          const aggregateIntervals = deptFilter == null ? computeAggregateIntervals(allDayRules) : [];
          const isExpanded = expandedDays.has(dayIdx) && deptFilter == null;

          return (
            <div key={dayIdx}>
              {/* Day row */}
              <div
                className={cn(
                  "flex min-h-[3.5rem] border-t border-border/80",
                  deptFilter == null && "cursor-pointer hover:bg-muted/20 transition-colors"
                )}
                style={{ borderTopWidth: "2px" }}
                onClick={deptFilter == null ? () => onToggleExpand(dayIdx) : undefined}
              >
                <div className="w-20 shrink-0 flex items-center gap-1.5 px-3">
                  {deptFilter == null && (
                    isExpanded
                      ? <ChevronDown size={12} className="text-muted-foreground shrink-0" />
                      : <ChevronRight size={12} className="text-muted-foreground shrink-0" />
                  )}
                  <span className="text-xs font-semibold text-foreground">
                    {DAY_LABELS_SHORT[dayIdx]}
                  </span>
                </div>

                <div className="flex-1 relative py-2.5 px-1 pr-6">
                  <GridLines />

                  {/* Aggregate heatmap mode */}
                  {deptFilter == null && aggregateIntervals.map((interval, i) => {
                    const left = ((interval.startHour - GRID_START) / GRID_HOURS) * 100;
                    const width = ((interval.endHour - interval.startHour) / GRID_HOURS) * 100;
                    return (
                      <div
                        key={i}
                        className={cn(
                          "absolute top-1.5 bottom-1.5 rounded-md border flex items-center px-2 overflow-hidden",
                          coverageIntensityClass(interval.totalStaff)
                        )}
                        style={{ left: `${left}%`, width: `${width}%` }}
                        title={`${interval.totalStaff} staff required (aggregate)`}
                      >
                        <span className="text-xs font-semibold truncate">
                          {interval.totalStaff}
                        </span>
                      </div>
                    );
                  })}

                  {/* Department-filtered mode */}
                  {deptFilter != null && dayRules.map((rule) => {
                    const startHour = timeToHours(rule.start_time_local);
                    const endHour = timeToHours(rule.end_time_local);
                    const left = ((startHour - GRID_START) / GRID_HOURS) * 100;
                    const width = ((endHour - startHour) / GRID_HOURS) * 100;
                    const timeLabel = `${formatRuleTime(rule.start_time_local)}–${formatRuleTime(rule.end_time_local)}`;
                    return (
                      <div
                        key={rule.id}
                        className="absolute top-1.5 bottom-1.5 rounded-md border bg-violet-100 border-violet-300 flex items-center px-2 overflow-hidden"
                        style={{ left: `${left}%`, width: `${width}%` }}
                        title={`${timeLabel} · ${rule.min_staff} staff`}
                      >
                        <span className="text-xs font-medium text-violet-700 truncate">
                          {timeLabel}
                          <span className="ml-1.5 font-normal opacity-80">· {rule.min_staff}</span>
                        </span>
                      </div>
                    );
                  })}

                  {deptFilter != null && dayRules.length === 0 && (
                    <div className="absolute top-1.5 bottom-1.5 left-0 right-6 rounded-md bg-muted/30 border border-border/40 flex items-center justify-center">
                      <span className="text-xs text-muted-foreground">No rules</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Expanded dept sub-rows */}
              {isExpanded && deptIds.map((deptId) => {
                const deptRules = activeRules.filter(
                  (r) => r.day_of_week === dayIdx && r.department_id === deptId
                );
                if (deptRules.length === 0) return null;
                const dept = deptMap.get(deptId);
                const deptCode = dept?.code ?? `D${deptId}`;
                const deptName = dept?.name ?? `Dept ${deptId}`;

                return (
                  <div
                    key={deptId}
                    className="flex min-h-[3rem] border-t border-border/40 bg-muted/10"
                  >
                    <div className="w-20 shrink-0 flex items-center px-3 pl-7">
                      <span className="text-xs text-muted-foreground font-medium truncate" title={deptName}>
                        {deptCode}
                      </span>
                    </div>
                    <div className="flex-1 relative py-2 px-1 pr-6">
                      <GridLines />
                      {deptRules.map((rule) => {
                        const startHour = timeToHours(rule.start_time_local);
                        const endHour = timeToHours(rule.end_time_local);
                        const left = ((startHour - GRID_START) / GRID_HOURS) * 100;
                        const width = ((endHour - startHour) / GRID_HOURS) * 100;
                        const timeLabel = `${formatRuleTime(rule.start_time_local)}–${formatRuleTime(rule.end_time_local)}`;
                        return (
                          <div
                            key={rule.id}
                            className="absolute top-1 bottom-1 rounded-md border bg-violet-100 border-violet-300 flex items-center px-2 overflow-hidden"
                            style={{ left: `${left}%`, width: `${width}%` }}
                            title={`${deptName} · ${timeLabel} · ${rule.min_staff} staff`}
                          >
                            <span className="text-xs font-medium text-violet-700 truncate">
                              {timeLabel}
                              <span className="ml-1 font-normal opacity-80">· {rule.min_staff}</span>
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>

      {/* Heatmap legend (aggregate mode only) */}
      {deptFilter == null && (
        <div className="flex flex-wrap items-center gap-4 text-xs px-4 py-2 border-t">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="flex items-center gap-1.5">
              <div className={cn("w-4 h-3 rounded-sm border", coverageIntensityClass(n))} />
              <span className="text-muted-foreground">{n === 4 ? "4+" : n} staff</span>
            </div>
          ))}
          <span className="text-muted-foreground ml-1">· Click a day to expand by department</span>
        </div>
      )}
    </div>
  );
}

// ── Coverage compact (mobile) ─────────────────────────────────────────

function CompactCoverageView({
  coverageRules,
  deptFilter,
  deptMap,
}: {
  coverageRules: CoverageRequirementResponse[];
  deptFilter: number | null;
  deptMap: Map<number, Department>;
}) {
  const activeRules = coverageRules.filter((r) => r.active);

  return (
    <div className="lg:hidden space-y-2">
      {Array.from({ length: 7 }, (_, dayIdx) => {
        const dayRules = activeRules.filter(
          (r) => r.day_of_week === dayIdx && (deptFilter == null || r.department_id === deptFilter)
        );

        return (
          <div key={dayIdx} className="rounded-lg border bg-card p-3">
            <p className="text-sm font-semibold mb-2">{DAY_LABELS_FULL[dayIdx]}</p>
            {dayRules.length === 0 ? (
              <span className="text-xs text-muted-foreground">No rules</span>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {dayRules.map((rule) => {
                  const dept = deptMap.get(rule.department_id);
                  const deptLabel = dept?.code ?? `D${rule.department_id}`;
                  const deptName = dept?.name ?? `Dept ${rule.department_id}`;
                  const timeLabel = `${formatRuleTime(rule.start_time_local)}–${formatRuleTime(rule.end_time_local)}`;
                  return (
                    <Badge
                      key={rule.id}
                      className="text-[11px] bg-violet-100 text-violet-700 border-violet-300"
                      title={deptFilter == null ? deptName : undefined}
                    >
                      {deptFilter == null ? `${deptLabel} · ` : ""}{timeLabel} · {rule.min_staff}
                    </Badge>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Role Requirements Grid (desktop) ─────────────────────────────────

function RoleGrid({
  roleRules,
  deptFilter,
  deptMap,
}: {
  roleRules: RoleRequirementResponse[];
  deptFilter: number | null;
  deptMap: Map<number, Department>;
}) {
  const activeRules = useMemo(() => roleRules.filter((r) => r.active), [roleRules]);

  const filteredRules = useMemo(
    () =>
      activeRules.filter(
        (r) => deptFilter == null || r.department_id == null || r.department_id === deptFilter
      ),
    [activeRules, deptFilter]
  );

  const allDayRules = filteredRules.filter((r) => r.day_of_week == null);
  const daySpecificRules = filteredRules.filter((r) => r.day_of_week != null);

  function renderRoleBlock(rule: RoleRequirementResponse) {
    const startHour = timeToHours(rule.start_time_local);
    const endHour = timeToHours(rule.end_time_local);
    const left = ((startHour - GRID_START) / GRID_HOURS) * 100;
    const width = ((endHour - startHour) / GRID_HOURS) * 100;
    const timeLabel = `${formatRuleTime(rule.start_time_local)}–${formatRuleTime(rule.end_time_local)}`;
    const label = roleBlockLabel(rule);
    const blockClass = roleBlockClass(rule.requires_manager, rule.requires_keyholder);
    const deptName = rule.department_id != null ? (deptMap.get(rule.department_id)?.name ?? `Dept ${rule.department_id}`) : null;

    return (
      <div
        key={rule.id}
        className={cn(
          "absolute top-1.5 bottom-1.5 rounded-md border flex items-center px-2 overflow-hidden",
          blockClass
        )}
        style={{ left: `${left}%`, width: `${width}%` }}
        title={`${label}${deptName ? ` · ${deptName}` : ""} · ${timeLabel}`}
      >
        <span className="text-xs font-medium truncate">
          {timeLabel}
          <span className="ml-1.5 font-normal opacity-80">{label}</span>
        </span>
      </div>
    );
  }

  return (
    <div className="hidden lg:block rounded-lg border bg-card">
      <HourLabelHeader />
      <div className="space-y-0">

        {/* "All days" banner row */}
        {allDayRules.length > 0 && (
          <div
            className="flex min-h-[3.5rem] border-t border-border/80 bg-muted/10"
            style={{ borderTopWidth: "2px" }}
          >
            <div className="w-20 shrink-0 flex flex-col justify-center px-3">
              <span className="text-xs font-semibold text-foreground">ALL</span>
              <span className="text-[10px] text-muted-foreground">DAYS</span>
            </div>
            <div className="flex-1 relative py-2.5 px-1 pr-6">
              <GridLines />
              {allDayRules.map(renderRoleBlock)}
            </div>
          </div>
        )}

        {/* Per-day rows */}
        {Array.from({ length: 7 }, (_, dayIdx) => {
          const dayRules = daySpecificRules.filter((r) => r.day_of_week === dayIdx);
          return (
            <div
              key={dayIdx}
              className="flex min-h-[3.5rem] border-t border-border/80"
              style={{ borderTopWidth: "2px" }}
            >
              <div className="w-20 shrink-0 flex flex-col justify-center px-3">
                <span className="text-xs font-semibold text-foreground">
                  {DAY_LABELS_SHORT[dayIdx]}
                </span>
              </div>
              <div className="flex-1 relative py-2.5 px-1 pr-6">
                <GridLines />
                {dayRules.length === 0 && (
                  <div className="absolute top-1.5 bottom-1.5 left-0 right-6 rounded-md bg-muted/20 border border-border/40 flex items-center justify-center">
                    <span className="text-xs text-muted-foreground">No rules</span>
                  </div>
                )}
                {dayRules.map(renderRoleBlock)}
              </div>
            </div>
          );
        })}
      </div>

      {/* Role legend */}
      <div className="flex flex-wrap items-center gap-4 text-xs px-4 py-2 border-t">
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-3 rounded-sm bg-purple-100 border border-purple-300" />
          <span className="text-muted-foreground">Manager</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-3 rounded-sm bg-amber-100 border border-amber-300" />
          <span className="text-muted-foreground">Keyholder</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-3 rounded-sm bg-indigo-100 border border-indigo-300" />
          <span className="text-muted-foreground">Manager + Keyholder</span>
        </div>
      </div>
    </div>
  );
}

// ── Role Requirements compact (mobile) ───────────────────────────────

function CompactRoleView({
  roleRules,
  deptFilter,
  deptMap,
}: {
  roleRules: RoleRequirementResponse[];
  deptFilter: number | null;
  deptMap: Map<number, Department>;
}) {
  const activeRules = roleRules.filter((r) => r.active);
  const filteredRules = activeRules.filter(
    (r) => deptFilter == null || r.department_id == null || r.department_id === deptFilter
  );
  const allDayRules = filteredRules.filter((r) => r.day_of_week == null);

  function roleBadgeClass(r: RoleRequirementResponse): string {
    if (r.requires_manager && r.requires_keyholder)
      return "bg-indigo-100 text-indigo-700 border-indigo-300";
    if (r.requires_manager) return "bg-purple-100 text-purple-700 border-purple-300";
    return "bg-amber-100 text-amber-700 border-amber-300";
  }

  return (
    <div className="lg:hidden space-y-2">
      {allDayRules.length > 0 && (
        <div className="rounded-lg border bg-card p-3">
          <p className="text-sm font-semibold mb-2">All days</p>
          <div className="flex flex-wrap gap-1.5">
            {allDayRules.map((r) => (
              <Badge key={r.id} className={cn("text-[11px]", roleBadgeClass(r))}>
                {roleBlockLabel(r)} · {formatRuleTime(r.start_time_local)}–{formatRuleTime(r.end_time_local)}
              </Badge>
            ))}
          </div>
        </div>
      )}
      {Array.from({ length: 7 }, (_, dayIdx) => {
        const dayRules = filteredRules.filter((r) => r.day_of_week === dayIdx);
        return (
          <div key={dayIdx} className="rounded-lg border bg-card p-3">
            <p className="text-sm font-semibold mb-2">{DAY_LABELS_FULL[dayIdx]}</p>
            {dayRules.length === 0 ? (
              <span className="text-xs text-muted-foreground">No rules</span>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {dayRules.map((r) => (
                  <Badge key={r.id} className={cn("text-[11px]", roleBadgeClass(r))}>
                    {roleBlockLabel(r)} · {formatRuleTime(r.start_time_local)}–{formatRuleTime(r.end_time_local)}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────

interface EnrichedProposal extends AIProposalResponse {
  summary?: string;
}

export default function SchedulingRules() {
  const { employee, roles, isAdmin } = useAuth();

  // For non-admin: derive store from employee record or role
  const derivedStoreId: number | null = useMemo(
    () => employee?.store_id ?? roles.find((r) => r.store_id != null)?.store_id ?? null,
    [employee, roles]
  );

  // Admins can select any store; others use their derived store
  const [stores, setStores] = useState<Store[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<number | null>(null);

  const storeId: number | null = isAdmin ? selectedStoreId : derivedStoreId;

  useEffect(() => {
    if (!isAdmin) return;
    storesApi.list().then((res) => {
      const list: Store[] = res.data;
      setStores(list);
      // Pre-select first store if none chosen yet
      if (selectedStoreId == null && list.length > 0) {
        setSelectedStoreId(list[0].id);
      }
    }).catch(() => {});
  }, [isAdmin]);

  const [coverageRules, setCoverageRules] = useState<CoverageRequirementResponse[]>([]);
  const [roleRules, setRoleRules] = useState<RoleRequirementResponse[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [proposals, setProposals] = useState<EnrichedProposal[]>([]);
  const [loading, setLoading] = useState(true);

  const [activeTab, setActiveTab] = useState<"coverage" | "role">("coverage");
  const [deptFilter, setDeptFilter] = useState<number | null>(null);
  const [expandedDays, setExpandedDays] = useState<Set<number>>(new Set());

  // AI input
  const [aiText, setAiText] = useState("");
  const [aiSending, setAiSending] = useState(false);
  const [aiResult, setAiResult] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const [showClarify, setShowClarify] = useState(false);

  // AI preview confirmation
  const [aiPreview, setAiPreview] = useState<{
    outputId: number;
    summary: string;
    intentType: string;
    departmentId: number | null;
    changes: Array<Record<string, unknown>>;
  } | null>(null);
  const [confirmingSend, setConfirmingSend] = useState(false);
  const [originalText, setOriginalText] = useState("");

  // Manual modal
  const [showManualEdit, setShowManualEdit] = useState(false);
  const [manualSubmitting, setManualSubmitting] = useState(false);

  const [cancellingId, setCancellingId] = useState<number | null>(null);

  // Department map for name lookups
  const deptMap = useMemo(
    () => new Map(departments.map((d) => [d.id, d])),
    [departments]
  );

  // Departments present in coverage/role rules for the filter dropdown
  const relevantDepts = useMemo(() => {
    const ids = new Set<number>();
    coverageRules.forEach((r) => ids.add(r.department_id));
    roleRules.forEach((r) => { if (r.department_id != null) ids.add(r.department_id); });
    return departments.filter((d) => ids.has(d.id));
  }, [coverageRules, roleRules, departments]);

  const enrichProposals = async (raw: AIProposalResponse[]): Promise<EnrichedProposal[]> => {
    return Promise.all(
      raw
        .filter(
          (p) =>
            (p.type === ProposalType.COVERAGE || p.type === ProposalType.ROLE_REQUIREMENT) &&
            p.status !== ProposalStatus.CANCELLED
        )
        .slice(0, 8)
        .map(async (p): Promise<EnrichedProposal> => {
          const isManual = !p.ai_output_id;
          if (isManual) {
            const cj = (p as AIProposalResponse & { changes_json?: { summary?: string } }).changes_json;
            return { ...p, summary: cj?.summary };
          }
          try {
            const outRes = await api.get(`/ai-outputs/${p.ai_output_id}`);
            return { ...p, summary: outRes.data.summary };
          } catch {
            return { ...p };
          }
        })
    );
  };

  const load = async () => {
    setLoading(true);
    try {
      const [coverageRes, roleRes, deptsRes] = await Promise.all([
        coverageApi.list(storeId != null ? { store_id: storeId } : {}),
        roleRequirementsApi.list(storeId != null ? { store_id: storeId } : {}),
        departmentsApi.list(),
      ]);
      setCoverageRules(coverageRes.data);
      setRoleRules(roleRes.data);
      setDepartments(deptsRes.data);

      const proposalsRes = storeId != null
        ? await aiProposalsApi.getByStore(storeId).catch(() => ({ data: [] }))
        : await aiProposalsApi.getAll().catch(() => ({ data: [] }));
      setProposals(await enrichProposals(proposalsRes.data));
    } catch {
      // leave empty
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [storeId]);

  const refreshProposals = async () => {
    const res = storeId != null
      ? await aiProposalsApi.getByStore(storeId).catch(() => ({ data: [] }))
      : await aiProposalsApi.getAll().catch(() => ({ data: [] }));
    setProposals(await enrichProposals(res.data));
  };

  const toggleExpand = (day: number) => {
    setExpandedDays((prev) => {
      const next = new Set(prev);
      next.has(day) ? next.delete(day) : next.add(day);
      return next;
    });
  };

  const handleDeptFilter = (id: number | null) => {
    setDeptFilter(id);
    if (id != null) setExpandedDays(new Set()); // collapse all when filtering
  };

  // Format a single change from result_json into a readable bullet string
  const formatChangeBullet = (change: Record<string, unknown>, intentType: string): string => {
    const action = String(change.action ?? "ADD");
    const day = change.day_of_week == null ? "every day" : DAY_LABELS_FULL[change.day_of_week as number];
    const start = change.start_time ? formatRuleTime(String(change.start_time)) : "—";
    const end = change.end_time ? formatRuleTime(String(change.end_time)) : "—";
    const time = `${start}–${end}`;

    if (intentType === "COVERAGE") {
      const dept = change.department_id != null ? (deptMap.get(change.department_id as number)?.name ?? `Dept ${change.department_id}`) : "store";
      const staff = change.min_staff != null ? `min ${change.min_staff}` : "";
      const maxStaff = change.max_staff != null ? ` / max ${change.max_staff}` : "";
      return `${action} · Coverage · ${dept} · ${day} · ${time}${staff ? ` · ${staff}${maxStaff} staff` : ""}`;
    }
    // ROLE_REQUIREMENT
    const roles: string[] = [];
    if (change.requires_manager) roles.push("Manager");
    if (change.requires_keyholder) roles.push("Keyholder");
    const roleLabel = roles.length > 0 ? roles.join(" + ") : "Role req";
    return `${action} · ${roleLabel} · ${day} · ${time}`;
  };

  // AI submit
  const handleAiSubmit = async (text: string) => {
    if (!text.trim()) return;
    setAiSending(true);
    setAiResult(null);
    setAiError(null);

    const contextTables = activeTab === "coverage"
      ? ["coverage_requirements"]
      : ["role_requirements"];

    try {
      const res = await aiInputsApi.create(text.trim(), contextTables, storeId, true);
      const summary: string = res.data.summary ?? "";
      const isUnclear =
        summary.toLowerCase().includes("unclear") || res.data.status === "INVALID";

      if (isUnclear) {
        setOriginalText(text.trim());
        setShowClarify(true);
        setAiText("");
      } else {
        const result = res.data.result_json ?? {};
        setAiPreview({
          outputId: res.data.id,
          summary,
          intentType: result.intent_type ?? "",
          departmentId: result.department_id ?? null,
          changes: Array.isArray(result.changes) ? result.changes : [],
        });
        setAiText("");
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setAiError(msg ?? "Failed to process request");
    } finally {
      setAiSending(false);
    }
  };

  const handleConfirmProposal = async () => {
    if (!aiPreview) return;
    setConfirmingSend(true);
    try {
      await aiProposalsApi.confirmPreview(aiPreview.outputId);
      setAiResult(aiPreview.summary);
      setAiPreview(null);
      await refreshProposals();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setAiError(msg ?? "Failed to send proposal");
    } finally {
      setConfirmingSend(false);
    }
  };

  const handleDiscardPreview = () => setAiPreview(null);

  const handleClarifyConfirm = async (clarification: string) => {
    const combined = `${originalText}. To clarify: ${clarification}`;
    setShowClarify(false);
    setOriginalText("");
    await handleAiSubmit(combined);
  };

  // Manual modal submit
  const handleManualSubmit = async (rows: ManualRow[], sid: number) => {
    setManualSubmitting(true);
    try {
      // Group by (ruleType, deptId) — one proposal per group
      const groups = new Map<string, ManualRow[]>();
      for (const row of rows) {
        const key = `${row.ruleType}:${row.deptId}`;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key)!.push(row);
      }

      for (const [key, groupRows] of groups) {
        const [ruleType, deptIdStr] = key.split(":");
        const department_id = deptIdStr ? parseInt(deptIdStr) : null;
        const changes = groupRows.map((r) => {
          if (ruleType === "COVERAGE") {
            return {
              action: "ADD",
              day_of_week: parseInt(r.dayOfWeek),
              start_time: r.startTime,
              end_time: r.endTime,
              min_staff: r.minStaff,
            };
          }
          return {
            action: "ADD",
            day_of_week: r.dayOfWeek === "" ? null : parseInt(r.dayOfWeek),
            start_time: r.startTime,
            end_time: r.endTime,
            requires_manager: r.requiresManager,
            requires_keyholder: r.requiresKeyholder,
            min_manager_count: r.requiresManager ? 1 : 0,
          };
        });

        await aiProposalsApi.proposeManualScheduling(
          ruleType as "COVERAGE" | "ROLE_REQUIREMENT",
          sid,
          department_id,
          changes,
          buildSummary(groupRows, deptMap)
        );
      }

      setShowManualEdit(false);
      await refreshProposals();
    } catch {
      // could add toast here
    } finally {
      setManualSubmitting(false);
    }
  };

  const handleCancel = async (id: number) => {
    setCancellingId(id);
    try {
      await aiProposalsApi.cancel(id);
      setProposals((prev) =>
        prev.map((p) => (p.id === id ? { ...p, status: ProposalStatus.CANCELLED } : p))
      );
    } finally {
      setCancellingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">Scheduling Rules</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Coverage and role requirements used to generate schedules.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Store filter — admin only */}
          {isAdmin && stores.length > 0 && (
            <select
              className="rounded-md border bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring"
              value={selectedStoreId ?? ""}
              onChange={(e) => setSelectedStoreId(e.target.value === "" ? null : parseInt(e.target.value))}
            >
              {stores.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          )}
          {/* Department filter */}
          <select
            className="rounded-md border bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring"
            value={deptFilter ?? ""}
            onChange={(e) => handleDeptFilter(e.target.value === "" ? null : parseInt(e.target.value))}
          >
            <option value="">All departments</option>
            {relevantDepts.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
          <Button
            variant={showManualEdit ? "secondary" : "outline"}
            size="sm"
            className="gap-1.5"
            onClick={() => setShowManualEdit((v) => !v)}
            disabled={storeId == null}
          >
            <Pencil size={14} />
            Edit manually
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b">
        {(["coverage", "role"] as const).map((tab) => (
          <button
            key={tab}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
              activeTab === tab
                ? "border-foreground text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
            onClick={() => setActiveTab(tab)}
          >
            {tab === "coverage" ? "Coverage Requirements" : "Role Requirements"}
          </button>
        ))}
      </div>

      {showManualEdit && storeId != null && (
        <ManualSchedulingModal
          storeId={storeId}
          departments={departments}
          onClose={() => setShowManualEdit(false)}
          onSubmit={handleManualSubmit}
          submitting={manualSubmitting}
        />
      )}

      {loading ? (
        <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
          <Loader2 size={16} className="animate-spin mr-2" />
          Loading rules…
        </div>
      ) : (
        <>
          {activeTab === "coverage" && (
            <>
              {coverageRules.filter((r) => r.active).length === 0 ? (
                <div className="rounded-lg border bg-card p-8 text-center text-sm text-muted-foreground">
                  No coverage requirements set. Use the AI input or edit manually to add some.
                </div>
              ) : (
                <>
                  <CoverageGrid
                    coverageRules={coverageRules}
                    deptFilter={deptFilter}
                    deptMap={deptMap}
                    expandedDays={expandedDays}
                    onToggleExpand={toggleExpand}
                  />
                  <CompactCoverageView
                    coverageRules={coverageRules}
                    deptFilter={deptFilter}
                    deptMap={deptMap}
                  />
                </>
              )}
            </>
          )}

          {activeTab === "role" && (
            <>
              {roleRules.filter((r) => r.active).length === 0 ? (
                <div className="rounded-lg border bg-card p-8 text-center text-sm text-muted-foreground">
                  No role requirements set. Use the AI input or edit manually to add some.
                </div>
              ) : (
                <>
                  <RoleGrid
                    roleRules={roleRules}
                    deptFilter={deptFilter}
                    deptMap={deptMap}
                  />
                  <CompactRoleView
                    roleRules={roleRules}
                    deptFilter={deptFilter}
                    deptMap={deptMap}
                  />
                </>
              )}
            </>
          )}
        </>
      )}

      {/* AI input */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Request a change</CardTitle>
          <p className="text-xs text-muted-foreground">
            Describe a rule change in plain text. A proposal will be created for review.
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <textarea
              value={aiText}
              onChange={(e) => setAiText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleAiSubmit(aiText);
                }
              }}
              placeholder={
                activeTab === "coverage"
                  ? 'e.g. "We need 3 staff in the bakery on Saturdays from 8am to 2pm"'
                  : 'e.g. "A manager must be present every day from 9am to 6pm"'
              }
              rows={2}
              disabled={aiPreview != null}
              className="flex-1 rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring resize-none disabled:opacity-50"
            />
            <Button
              size="icon"
              className="shrink-0 self-end"
              onClick={() => handleAiSubmit(aiText)}
              disabled={!aiText.trim() || aiSending || aiPreview != null}
            >
              {aiSending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </Button>
          </div>

          {aiPreview && (
            <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-3 space-y-3">
              <div className="space-y-1.5">
                <p className="text-xs font-semibold text-amber-800 uppercase tracking-wide">Preview — not yet submitted</p>
                <p className="text-sm text-amber-900">{aiPreview.summary}</p>
                {aiPreview.changes.length > 0 && (
                  <ul className="space-y-1 pt-1">
                    {aiPreview.changes.map((c, i) => (
                      <li key={i} className="text-xs text-amber-800 flex gap-1.5">
                        <span className="opacity-50 shrink-0">•</span>
                        <span>{formatChangeBullet(c, aiPreview.intentType)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button size="sm" className="gap-1.5" onClick={handleConfirmProposal} disabled={confirmingSend}>
                  {confirmingSend ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                  Send proposal
                </Button>
                <Button size="sm" variant="outline" onClick={handleDiscardPreview} disabled={confirmingSend}>
                  Discard
                </Button>
              </div>
            </div>
          )}

          {!aiPreview && aiResult && (
            <div className="rounded-md bg-emerald-50 border border-emerald-200 px-3 py-2 text-sm text-emerald-800">
              {aiResult}
            </div>
          )}
          {aiError && (
            <div className="rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
              {aiError}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent proposals */}
      {proposals.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Recent proposals</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {proposals.map((p) => (
                <div
                  key={p.id}
                  className="rounded-md border px-3 py-2.5 flex items-center justify-between gap-3"
                >
                  <div className="space-y-1 min-w-0">
                    <span className="text-sm font-medium truncate block">
                      {p.summary ?? `Proposal #${p.id}`}
                    </span>
                    <p className="text-xs text-muted-foreground">
                      {p.type === ProposalType.COVERAGE ? "Coverage" : "Role Requirement"} ·{" "}
                      {new Date(p.created_at).toLocaleDateString(undefined, {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge variant={PROPOSAL_STATUS_VARIANT[p.status] ?? "default"}>
                      {p.status}
                    </Badge>
                    {p.status === ProposalStatus.PENDING && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 px-2 text-xs text-muted-foreground hover:text-destructive"
                        onClick={() => handleCancel(p.id)}
                        disabled={cancellingId === p.id}
                      >
                        {cancellingId === p.id ? (
                          <Loader2 size={11} className="animate-spin" />
                        ) : (
                          "Cancel"
                        )}
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Clarify dialog */}
      {showClarify && (
        <ClarifyDialog
          onConfirm={handleClarifyConfirm}
          onCancel={() => {
            setShowClarify(false);
            setOriginalText("");
          }}
          loading={aiSending}
        />
      )}
    </div>
  );
}
