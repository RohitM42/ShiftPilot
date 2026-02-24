import { useState, useEffect, useMemo } from "react";
import { Send, Pencil, Loader2, Plus, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/contexts/AuthContext";
import { meApi, aiInputsApi, aiProposalsApi } from "@/services/api";
import api from "@/services/api";
import { cn } from "@/lib/utils";
import { AvailabilityRuleType, ProposalType, ProposalStatus } from "@/types";
import type { AvailabilityRuleResponse, AIProposalResponse } from "@/types";

// ── Constants ────────────────────────────────────────────────────────

const GRID_START = 0;
const GRID_END = 24;
const GRID_HOURS = GRID_END - GRID_START;

const DAY_LABELS_SHORT = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];
const DAY_LABELS_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const RULE_STYLES = {
  [AvailabilityRuleType.AVAILABLE]: {
    bg: "bg-blue-100",
    border: "border-blue-300",
    text: "text-blue-700",
    label: "Available",
  },
  [AvailabilityRuleType.PREFERRED]: {
    bg: "bg-emerald-100",
    border: "border-emerald-300",
    text: "text-emerald-700",
    label: "Preferred",
  },
  [AvailabilityRuleType.UNAVAILABLE]: {
    bg: "bg-unavailable-hatched",
    border: "border-red-300",
    text: "text-red-700",
    label: "Unavailable",
  },
};

const PROPOSAL_STATUS_VARIANT: Record<ProposalStatus, "default" | "success" | "destructive" | "warning"> = {
  [ProposalStatus.PENDING]: "warning",
  [ProposalStatus.APPROVED]: "success",
  [ProposalStatus.REJECTED]: "destructive",
  [ProposalStatus.CANCELLED]: "default",
};

// ── Time formatting ──────────────────────────────────────────────────

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

// ── Types ────────────────────────────────────────────────────────────

interface ParsedRule {
  id: number;
  dayOfWeek: number;
  startHour: number;
  endHour: number;
  startStr: string | null;
  endStr: string | null;
  ruleType: AvailabilityRuleType;
  isFullDay: boolean;
}

interface EnrichedProposal extends AIProposalResponse {
  summary?: string;
}


// ── Manual Edit Modal ────────────────────────────────────────────────

const DAY_LABELS_FULL_MODAL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const RULE_TYPE_OPTIONS = [
  { value: AvailabilityRuleType.AVAILABLE, label: "Available" },
  { value: AvailabilityRuleType.UNAVAILABLE, label: "Unavailable" },
  { value: AvailabilityRuleType.PREFERRED, label: "Preferred" },
];

interface ManualChange {
  day_of_week: number;
  start_time: string | null;
  end_time: string | null;
  rule_type: AvailabilityRuleType;
  all_day: boolean;
}

interface ManualChangePayload {
  action: "ADD";
  day_of_week: number;
  start_time: string | null;
  end_time: string | null;
  rule_type: AvailabilityRuleType;
}

function ManualEditModal({
  onClose,
  onSubmit,
  submitting,
}: {
  onClose: () => void;
  onSubmit: (changes: ManualChangePayload[], summary: string) => void;
  submitting: boolean;
}) {
  const [changes, setChanges] = useState<ManualChange[]>([
    { day_of_week: 0, start_time: "09:00", end_time: "17:00", rule_type: AvailabilityRuleType.AVAILABLE, all_day: false },
  ]);

  const addRow = () =>
    setChanges((prev) => [
      ...prev,
      { day_of_week: 0, start_time: "09:00", end_time: "17:00", rule_type: AvailabilityRuleType.AVAILABLE, all_day: false },
    ]);

  const removeRow = (i: number) => setChanges((prev) => prev.filter((_, idx) => idx !== i));

  const updateRow = (i: number, patch: Partial<ManualChange>) =>
    setChanges((prev) => prev.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));

  const buildSummary = () => {
    return changes
      .map((c) => {
        const day = DAY_LABELS_FULL_MODAL[c.day_of_week];
        const time = c.all_day ? "all day" : `${c.start_time}–${c.end_time}`;
        return `${c.rule_type.toLowerCase()} ${day} ${time}`;
      })
      .join(", ");
  };

  const handleSubmit = () => {
    const payload: ManualChangePayload[] = changes.map((c) => ({
      action: "ADD" as const,
      day_of_week: c.day_of_week,
      start_time: c.all_day ? null : c.start_time,
      end_time: c.all_day ? null : c.end_time,
      rule_type: c.rule_type,
    }));
    onSubmit(payload, buildSummary());
  };

  const selectClass = "rounded-md border bg-background px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring";
  const inputClass = "rounded-md border bg-background px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring w-24";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-background rounded-xl border shadow-xl w-full max-w-2xl mx-4 p-6 space-y-5 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold">Edit availability manually</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Changes will be submitted as a proposal for manager review.
            </p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} disabled={submitting}>
            <X size={16} />
          </Button>
        </div>

        <div className="space-y-2">
          {changes.map((row, i) => (
            <div key={i} className="flex flex-wrap items-center gap-2 rounded-lg border px-3 py-2.5 bg-muted/20">
              {/* Day */}
              <select
                className={selectClass}
                value={row.day_of_week}
                onChange={(e) => updateRow(i, { day_of_week: Number(e.target.value) })}
              >
                {DAY_LABELS_FULL_MODAL.map((d, idx) => (
                  <option key={idx} value={idx}>{d}</option>
                ))}
              </select>

              {/* Rule type */}
              <select
                className={selectClass}
                value={row.rule_type}
                onChange={(e) => updateRow(i, { rule_type: e.target.value as AvailabilityRuleType })}
              >
                {RULE_TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>

              {/* All day toggle */}
              <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={row.all_day}
                  onChange={(e) => updateRow(i, { all_day: e.target.checked })}
                  className="rounded"
                />
                All day
              </label>

              {/* Time range */}
              {!row.all_day && (
                <>
                  <input
                    type="time"
                    className={inputClass}
                    value={row.start_time ?? ""}
                    onChange={(e) => updateRow(i, { start_time: e.target.value })}
                  />
                  <span className="text-xs text-muted-foreground">to</span>
                  <input
                    type="time"
                    className={inputClass}
                    value={row.end_time ?? ""}
                    onChange={(e) => updateRow(i, { end_time: e.target.value })}
                  />
                </>
              )}

              <Button
                variant="ghost"
                size="icon"
                className="ml-auto text-muted-foreground hover:text-destructive h-7 w-7"
                onClick={() => removeRow(i)}
                disabled={changes.length === 1}
              >
                <Trash2 size={13} />
              </Button>
            </div>
          ))}
        </div>

        <Button variant="outline" size="sm" className="gap-1.5" onClick={addRow}>
          <Plus size={13} />
          Add row
        </Button>

        <div className="flex justify-end gap-2 pt-1">
          <Button variant="outline" size="sm" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button size="sm" onClick={handleSubmit} disabled={submitting || changes.length === 0}>
            {submitting && <Loader2 size={13} className="animate-spin mr-1.5" />}
            Submit for review
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Clarification Dialog ─────────────────────────────────────────────

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
          placeholder='e.g. "I meant I cannot work Saturday mornings, from 8am to 1pm"'
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

// ── Component ────────────────────────────────────────────────────────

export default function MyAvailability() {
  const { employee } = useAuth();

  const [rules, setRules] = useState<AvailabilityRuleResponse[]>([]);
  const [proposals, setProposals] = useState<EnrichedProposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [aiText, setAiText] = useState("");
  const [aiSending, setAiSending] = useState(false);
  const [aiResult, setAiResult] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

  // Manual edit modal
  const [showManualEdit, setShowManualEdit] = useState(false);
  const [manualSubmitting, setManualSubmitting] = useState(false);
  const [cancellingId, setCancellingId] = useState<number | null>(null);

  // Clarification dialog
  const [showClarify, setShowClarify] = useState(false);
  const [originalText, setOriginalText] = useState("");

  const enrichProposals = async (raw: AIProposalResponse[]): Promise<EnrichedProposal[]> => {
    return Promise.all(
      raw
        .filter((p) => p.type === ProposalType.AVAILABILITY && p.status !== ProposalStatus.CANCELLED)
        .slice(0, 5)
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

  // Fetch availability rules and recent proposals
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [rulesRes, proposalsRes] = await Promise.all([
          meApi.getAvailabilityRules(),
          meApi.getAIProposals().catch(() => ({ data: [] })),
        ]);
        setRules(rulesRes.data);
        setProposals(await enrichProposals(proposalsRes.data));
      } catch {
        setRules([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const refreshProposals = async () => {
    const res = await meApi.getAIProposals().catch(() => ({ data: [] }));
    setProposals(await enrichProposals(res.data));
  };

  // Parse rules
  const parsed: ParsedRule[] = useMemo(() => {
    return rules
      .filter((r) => r.active)
      .map((r) => {
        const isFullDay = !r.start_time_local && !r.end_time_local;
        return {
          id: r.id,
          dayOfWeek: r.day_of_week,
          startHour: isFullDay ? 0 : timeToHours(r.start_time_local),
          endHour: isFullDay ? 24 : timeToHours(r.end_time_local),
          startStr: r.start_time_local,
          endStr: r.end_time_local,
          ruleType: r.rule_type,
          isFullDay,
        };
      });
  }, [rules]);

  // Group by day
  const rulesByDay = useMemo(() => {
    const map = new Map<number, ParsedRule[]>();
    for (let i = 0; i < 7; i++) map.set(i, []);
    for (const r of parsed) {
      map.get(r.dayOfWeek)?.push(r);
    }
    return map;
  }, [parsed]);

  const handleAiSubmit = async (text: string) => {
    if (!text.trim()) return;
    setAiSending(true);
    setAiResult(null);
    setAiError(null);

    try {
      const res = await aiInputsApi.create(text.trim(), ["availability_rules"]);
      const summary: string = res.data.summary ?? "";

      const isUnclear =
        summary.toLowerCase().includes("unclear") ||
        res.data.status === "INVALID";

      if (isUnclear) {
        setOriginalText(text.trim());
        setShowClarify(true);
        setAiText("");
      } else {
        setAiResult(summary);
        setAiText("");
        await refreshProposals();
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setAiError(msg ?? "Failed to process request");
    } finally {
      setAiSending(false);
    }
  };

  const handleClarifyConfirm = async (clarification: string) => {
    const combined = `${originalText}. To clarify: ${clarification}`;
    setShowClarify(false);
    setOriginalText("");
    await handleAiSubmit(combined);
  };

  const handleManualSubmit = async (changes: ManualChangePayload[], summary: string) => {
    setManualSubmitting(true);
    try {
      await aiProposalsApi.proposeManual(changes, summary);
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
        prev.map((p) => p.id === id ? { ...p, status: ProposalStatus.CANCELLED } : p)
      );
    } catch {
      // could add toast here
    } finally {
      setCancellingId(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAiSubmit(aiText);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">My Availability</h1>
          {employee && (
            <p className="text-sm text-muted-foreground mt-1">
              {employee.contracted_weekly_hours}h contracted per week
            </p>
          )}
        </div>
        <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setShowManualEdit(true)}>
          <Pencil size={14} />
          Edit manually
        </Button>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-3 rounded-sm bg-blue-100 border border-blue-300" />
          <span className="text-muted-foreground">Available</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-3 rounded-sm bg-emerald-100 border border-emerald-300" />
          <span className="text-muted-foreground">Preferred</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-3 rounded-sm border border-red-300 unavailable-swatch" />
          <span className="text-muted-foreground">Unavailable</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-3 rounded-sm border border-border bg-muted/30" />
          <span className="text-muted-foreground">No rules (available all day)</span>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
          Loading availability…
        </div>
      ) : (
        <>
          <AvailabilityGrid rulesByDay={rulesByDay} />
          <CompactAvailability rulesByDay={rulesByDay} />
        </>
      )}

      {/* AI Input */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Request a change</CardTitle>
          <p className="text-xs text-muted-foreground">
            Describe your availability change in plain text. This will create a proposal for your manager to review.
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <textarea
              value={aiText}
              onChange={(e) => setAiText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder='e.g. "I cannot work Saturdays anymore" or "I would prefer morning shifts on Wednesdays"'
              rows={2}
              className="flex-1 rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring resize-none"
            />
            <Button
              size="icon"
              className="shrink-0 self-end"
              onClick={() => handleAiSubmit(aiText)}
              disabled={!aiText.trim() || aiSending}
            >
              {aiSending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </Button>
          </div>

          {aiResult && (
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

      {/* Recent Proposals */}
      {proposals.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Recent proposals</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {proposals.map((p) => (
                <div key={p.id} className="rounded-md border px-3 py-2.5 flex items-center justify-between gap-3">
                  <div className="space-y-1 min-w-0">
                    <span className="text-sm font-medium truncate block">
                      {p.summary ?? `Proposal #${p.id}`}
                    </span>
                    <p className="text-xs text-muted-foreground">
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
                        {cancellingId === p.id ? <Loader2 size={11} className="animate-spin" /> : "Cancel"}
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Manual edit modal */}
      {showManualEdit && (
        <ManualEditModal
          onClose={() => setShowManualEdit(false)}
          onSubmit={handleManualSubmit}
          submitting={manualSubmitting}
        />
      )}

      {/* Clarification dialog */}
      {showClarify && (
        <ClarifyDialog
          onConfirm={handleClarifyConfirm}
          onCancel={() => { setShowClarify(false); setOriginalText(""); }}
          loading={aiSending}
        />
      )}
    </div>
  );
}

// ── Grid View ────────────────────────────────────────────────────────

function AvailabilityGrid({ rulesByDay }: { rulesByDay: Map<number, ParsedRule[]> }) {
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
        {Array.from({ length: 7 }, (_, dayIdx) => {
          const dayRules = rulesByDay.get(dayIdx) ?? [];
          const hasRules = dayRules.length > 0;

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

                {!hasRules && (
                  <div className="absolute top-1.5 bottom-1.5 left-0 right-6 rounded-md bg-muted/40 border border-border/60 flex items-center justify-center">
                    <span className="text-xs text-muted-foreground">All day</span>
                  </div>
                )}

                {dayRules.map((rule) => {
                  const left = ((rule.startHour - GRID_START) / GRID_HOURS) * 100;
                  const width = ((rule.endHour - rule.startHour) / GRID_HOURS) * 100;
                  const style = RULE_STYLES[rule.ruleType];
                  const isUnavailable = rule.ruleType === AvailabilityRuleType.UNAVAILABLE;
                  const timeLabel = rule.isFullDay
                    ? "All day"
                    : `${formatRuleTime(rule.startStr)} – ${formatRuleTime(rule.endStr)}`;

                  return (
                    <div
                      key={rule.id}
                      className={cn(
                        "absolute top-1.5 bottom-1.5 rounded-md border flex items-center px-2 overflow-hidden",
                        style.border,
                        isUnavailable ? "unavailable-block" : style.bg
                      )}
                      style={{ left: `${left}%`, width: `${width}%` }}
                      title={`${style.label}: ${timeLabel}`}
                    >
                      <span className={cn("text-xs font-medium truncate", style.text)}>
                        {timeLabel}
                        <span className="ml-1.5 font-normal opacity-70">{style.label}</span>
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

// ── Compact View ─────────────────────────────────────────────────────

function CompactAvailability({ rulesByDay }: { rulesByDay: Map<number, ParsedRule[]> }) {
  return (
    <div className="lg:hidden space-y-2">
      {Array.from({ length: 7 }, (_, dayIdx) => {
        const dayRules = rulesByDay.get(dayIdx) ?? [];
        const hasRules = dayRules.length > 0;

        return (
          <div key={dayIdx} className="rounded-lg border bg-card p-3">
            <div className="mb-2">
              <span className="text-sm font-semibold text-foreground">
                {DAY_LABELS_FULL[dayIdx]}
              </span>
            </div>

            {!hasRules ? (
              <div className="rounded-md bg-muted/40 border border-border/60 px-3 py-2">
                <span className="text-xs text-muted-foreground">Available all day</span>
              </div>
            ) : (
              <div className="space-y-1.5">
                {dayRules.map((rule) => {
                  const style = RULE_STYLES[rule.ruleType];
                  const isUnavailable = rule.ruleType === AvailabilityRuleType.UNAVAILABLE;
                  const timeLabel = rule.isFullDay
                    ? "All day"
                    : `${formatRuleTime(rule.startStr)} – ${formatRuleTime(rule.endStr)}`;

                  return (
                    <div
                      key={rule.id}
                      className={cn(
                        "w-full rounded-md border px-3 py-2 flex items-center justify-between",
                        style.border,
                        isUnavailable ? "unavailable-block" : style.bg
                      )}
                    >
                      <span className={cn("text-xs font-medium", style.text)}>{timeLabel}</span>
                      <Badge
                        className={cn(
                          "text-[10px]",
                          isUnavailable
                            ? "bg-red-100 text-red-700 border-red-300"
                            : rule.ruleType === AvailabilityRuleType.PREFERRED
                              ? "bg-emerald-100 text-emerald-700 border-emerald-300"
                              : "bg-blue-100 text-blue-700 border-blue-300"
                        )}
                      >
                        {style.label}
                      </Badge>
                    </div>
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