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
    bg: "bg-gray-100",
    border: "border-gray-300",
    text: "text-gray-600",
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

function formatHourLabel(hour: number): string {
  if (hour === 24) return "00:00";
  return `${hour.toString().padStart(2, "0")}:00`;
}

function formatRuleTime(timeStr: string | null): string {
  if (!timeStr) return "";
  const [h, m] = timeStr.split(":").map(Number);
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`;
}

function timeToHours(timeStr: string | null): number {
  if (!timeStr) return 0;
  const [h, m] = timeStr.split(":").map(Number);
  return h + m / 60;
}

function hoursToTimeStr(h: number): string {
  const hours = Math.floor(h);
  const mins = Math.round((h - hours) * 60);
  return `${hours.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}`;
}

function mergeAdjacentRules(rules: ParsedRule[]): ParsedRule[] {
  if (rules.length < 2) return rules;
  const sorted = [...rules].sort((a, b) => a.startHour - b.startHour);
  const result: ParsedRule[] = [];
  let cur = { ...sorted[0] };
  for (let i = 1; i < sorted.length; i++) {
    const nxt = sorted[i];
    if (nxt.ruleType === cur.ruleType && nxt.startHour === cur.endHour) {
      cur = { ...cur, endHour: nxt.endHour, endStr: nxt.endStr, isFullDay: cur.startHour === 0 && nxt.endHour === 24 };
    } else {
      result.push(cur);
      cur = { ...nxt };
    }
  }
  result.push(cur);
  return result;
}

function computeGaps(rules: ParsedRule[]): Array<{ startHour: number; endHour: number }> {
  if (rules.length === 0) return [];
  const sorted = [...rules].sort((a, b) => a.startHour - b.startHour);
  const gaps: Array<{ startHour: number; endHour: number }> = [];
  let cursor = GRID_START;
  for (const rule of sorted) {
    if (rule.startHour > cursor) gaps.push({ startHour: cursor, endHour: rule.startHour });
    cursor = Math.max(cursor, rule.endHour);
  }
  if (cursor < GRID_END) gaps.push({ startHour: cursor, endHour: GRID_END });
  return gaps;
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
  pending_changes?: Array<{ day_of_week: number; start_time: string | null; end_time: string | null; rule_type: AvailabilityRuleType }>;
}

interface PendingOverlayRule {
  dayOfWeek: number;
  startHour: number;
  endHour: number;
  ruleType: AvailabilityRuleType;
  isPreview: boolean; // true = unsaved form row, false = submitted pending proposal
}

const DEFAULT_FORM_ROW: ManualChange = {
  day_of_week: 0, start_time: "09:00", end_time: "17:00",
  rule_type: AvailabilityRuleType.AVAILABLE, all_day: false,
};


// ── Manual Edit Card ─────────────────────────────────────────────────

const DAY_LABELS_FULL_MODAL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function SplitTimeInput({ value, onChange, className }: { value: string; onChange: (v: string) => void; className?: string }) {
  const parts = value ? value.split(":").map(Number) : [9, 0];
  const h = isNaN(parts[0]) ? 9 : parts[0];
  const m = isNaN(parts[1]) ? 0 : [0, 15, 30, 45].reduce((a, b) => (Math.abs(b - parts[1]) < Math.abs(a - parts[1]) ? b : a));

  const setH = (raw: string) => {
    const n = parseInt(raw);
    const clamped = isNaN(n) ? 0 : Math.max(0, Math.min(23, n));
    onChange(`${clamped.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`);
  };
  const setM = (raw: string) => {
    onChange(`${h.toString().padStart(2, "0")}:${raw.padStart(2, "0")}`);
  };

  const base = `rounded-md border bg-background px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring${className ? ` ${className}` : ""}`;
  return (
    <div className="flex items-center gap-1">
      <input
        type="number"
        min={0}
        max={23}
        value={h}
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

function ManualEditCard({
  onClose,
  onSubmit,
  submitting,
  changes,
  onChangesChange,
}: {
  onClose: () => void;
  onSubmit: (changes: ManualChangePayload[], summary: string) => void;
  submitting: boolean;
  changes: ManualChange[];
  onChangesChange: (changes: ManualChange[]) => void;
}) {
  const addRow = () =>
    onChangesChange([
      ...changes,
      { day_of_week: 0, start_time: "09:00", end_time: "17:00", rule_type: AvailabilityRuleType.AVAILABLE, all_day: false },
    ]);

  const removeRow = (i: number) => onChangesChange(changes.filter((_, idx) => idx !== i));

  const updateRow = (i: number, patch: Partial<ManualChange>) =>
    onChangesChange(changes.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));

  const buildSummary = () =>
    changes
      .map((c) => {
        const day = DAY_LABELS_FULL_MODAL[c.day_of_week];
        const time = c.all_day ? "all day" : `${c.start_time}–${c.end_time}`;
        return `${c.rule_type.toLowerCase()} ${day} ${time}`;
      })
      .join(", ");

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

  return (
    <div className="rounded-lg border bg-card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold">Edit availability manually</h2>
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
            <select
              className={selectClass}
              value={row.day_of_week}
              onChange={(e) => updateRow(i, { day_of_week: Number(e.target.value) })}
            >
              {DAY_LABELS_FULL_MODAL.map((d, idx) => (
                <option key={idx} value={idx}>{d}</option>
              ))}
            </select>

            <select
              className={selectClass}
              value={row.rule_type}
              onChange={(e) => updateRow(i, { rule_type: e.target.value as AvailabilityRuleType })}
            >
              {RULE_TYPE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>

            <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer select-none">
              <input
                type="checkbox"
                checked={row.all_day}
                onChange={(e) => updateRow(i, { all_day: e.target.checked })}
                className="rounded"
              />
              All day
            </label>

            {!row.all_day && (
              <>
                <SplitTimeInput
                  value={row.start_time ?? "09:00"}
                  onChange={(v) => updateRow(i, { start_time: v })}
                />
                <span className="text-xs text-muted-foreground">to</span>
                <SplitTimeInput
                  value={row.end_time ?? "17:00"}
                  onChange={(v) => updateRow(i, { end_time: v })}
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

      <div className="flex items-center justify-between">
        <Button variant="outline" size="sm" className="gap-1.5" onClick={addRow}>
          <Plus size={13} />
          Add row
        </Button>
        <div className="flex gap-2">
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

  // Manual edit card
  const [showManualEdit, setShowManualEdit] = useState(false);
  const [showPending, setShowPending] = useState(true);
  const [formChanges, setFormChanges] = useState<ManualChange[]>([{ ...DEFAULT_FORM_ROW }]);
  const [manualSubmitting, setManualSubmitting] = useState(false);
  const [cancellingId, setCancellingId] = useState<number | null>(null);

  // AI preview confirmation
  const [aiPreview, setAiPreview] = useState<{
    outputId: number;
    summary: string;
    changes: Array<{ day_of_week: number; start_time: string | null; end_time: string | null; rule_type: AvailabilityRuleType }>;
  } | null>(null);
  const [confirmingSend, setConfirmingSend] = useState(false);

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
            const cj = (p as AIProposalResponse & { changes_json?: { summary?: string; changes?: EnrichedProposal["pending_changes"] } }).changes_json;
            return { ...p, summary: cj?.summary, pending_changes: cj?.changes };
          }
          try {
            const outRes = await api.get(`/ai-outputs/${p.ai_output_id}`);
            return { ...p, summary: outRes.data.summary, pending_changes: outRes.data.result_json?.changes };
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
          endHour: isFullDay ? 24 : (timeToHours(r.end_time_local) || 24),
          startStr: r.start_time_local,
          endStr: r.end_time_local,
          ruleType: r.rule_type,
          isFullDay,
        };
      });
  }, [rules]);

  // Group by day, merging any adjacent same-type rules
  const rulesByDay = useMemo(() => {
    const map = new Map<number, ParsedRule[]>();
    for (let i = 0; i < 7; i++) map.set(i, []);
    for (const r of parsed) {
      map.get(r.dayOfWeek)?.push(r);
    }
    for (const [day, rules] of map) {
      map.set(day, mergeAdjacentRules(rules));
    }
    return map;
  }, [parsed]);

  // Pending overlay: form preview + submitted pending proposals
  const pendingOverlayRules = useMemo<PendingOverlayRule[]>(() => {
    const result: PendingOverlayRule[] = [];

    if (showManualEdit) {
      for (const c of formChanges) {
        const startH = c.all_day ? 0 : timeToHours(c.start_time ?? "00:00");
        const endH = c.all_day ? 24 : timeToHours(c.end_time ?? "24:00");
        result.push({ dayOfWeek: c.day_of_week, startHour: startH, endHour: endH, ruleType: c.rule_type, isPreview: true });
      }
    }

    for (const p of proposals) {
      if (p.status !== ProposalStatus.PENDING) continue;
      if (!p.pending_changes) continue;
      for (const c of p.pending_changes) {
        const startH = c.start_time ? timeToHours(c.start_time) : 0;
        const endH = c.end_time ? timeToHours(c.end_time) : 24;
        result.push({ dayOfWeek: c.day_of_week, startHour: startH, endHour: endH, ruleType: c.rule_type, isPreview: false });
      }
    }

    if (aiPreview) {
      for (const c of aiPreview.changes) {
        const startH = c.start_time ? timeToHours(c.start_time) : 0;
        const endH = c.end_time ? timeToHours(c.end_time) : 24;
        result.push({ dayOfWeek: c.day_of_week, startHour: startH, endHour: endH, ruleType: c.rule_type, isPreview: true });
      }
    }

    return result;
  }, [showManualEdit, formChanges, proposals, aiPreview]);

  const handleAiSubmit = async (text: string) => {
    if (!text.trim()) return;
    setAiSending(true);
    setAiResult(null);
    setAiError(null);

    try {
      const res = await aiInputsApi.create(text.trim(), ["availability_rules"], undefined, true);
      const summary: string = res.data.summary ?? "";
      const isUnclear = summary.toLowerCase().includes("unclear") || res.data.status === "INVALID";

      if (isUnclear) {
        setOriginalText(text.trim());
        setShowClarify(true);
        setAiText("");
      } else {
        // Enter preview mode — show the proposed changes before submitting
        const changes = (res.data.result_json?.changes ?? []) as Array<{
          day_of_week: number;
          start_time: string | null;
          end_time: string | null;
          rule_type: AvailabilityRuleType;
        }>;
        setAiPreview({ outputId: res.data.id, summary, changes });
        setShowPending(true);
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
      setAiPreview(null);
      setAiResult(aiPreview.summary);
      await refreshProposals();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setAiError(msg ?? "Failed to send proposal");
    } finally {
      setConfirmingSend(false);
    }
  };

  const handleDiscardPreview = () => {
    setAiPreview(null);
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
      setFormChanges([{ ...DEFAULT_FORM_ROW }]);
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
        <Button
          variant={showManualEdit ? "secondary" : "outline"}
          size="sm"
          className="gap-1.5"
          onClick={() => { setShowManualEdit((v) => !v); if (showManualEdit) setFormChanges([{ ...DEFAULT_FORM_ROW }]); }}
        >
          <Pencil size={14} />
          Edit manually
        </Button>
      </div>

      {/* Legend + pending toggle */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-3 rounded-sm bg-gray-100 border border-gray-300" />
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
          {pendingOverlayRules.length > 0 && showPending && (
            <div className="flex items-center gap-1.5">
              <div className="w-4 h-3 rounded-sm bg-amber-100 border border-amber-400" />
              <span className="text-muted-foreground">Pending</span>
            </div>
          )}
        </div>
        {pendingOverlayRules.length > 0 && (
          <Button
            variant={showPending ? "secondary" : "outline"}
            size="sm"
            className="text-xs h-7 px-2.5"
            onClick={() => setShowPending((v) => !v)}
          >
            {showPending ? "Hide pending" : "Show pending"}
          </Button>
        )}
      </div>

      {showManualEdit && (
        <ManualEditCard
          onClose={() => { setShowManualEdit(false); setFormChanges([{ ...DEFAULT_FORM_ROW }]); }}
          onSubmit={handleManualSubmit}
          submitting={manualSubmitting}
          changes={formChanges}
          onChangesChange={setFormChanges}
        />
      )}

      {loading ? (
        <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
          Loading availability…
        </div>
      ) : (
        <>
          <AvailabilityGrid rulesByDay={rulesByDay} pendingRules={showPending ? pendingOverlayRules : []} />
          <CompactAvailability rulesByDay={rulesByDay} pendingRules={showPending ? pendingOverlayRules : []} />
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
              <div className="flex items-start gap-2">
                <div className="flex-1 space-y-1">
                  <p className="text-xs font-semibold text-amber-800 uppercase tracking-wide">Preview — not yet submitted</p>
                  <p className="text-sm text-amber-900">{aiPreview.summary}</p>
                  <p className="text-xs text-amber-700">The amber blocks on the grid show what this change would look like.</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  className="gap-1.5"
                  onClick={handleConfirmProposal}
                  disabled={confirmingSend}
                >
                  {confirmingSend ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                  Send proposal
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleDiscardPreview}
                  disabled={confirmingSend}
                >
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

function AvailabilityGrid({ rulesByDay, pendingRules }: { rulesByDay: Map<number, ParsedRule[]>; pendingRules: PendingOverlayRule[] }) {
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

                {(() => {
                  const blockingRules = dayRules.filter(r => r.ruleType !== AvailabilityRuleType.AVAILABLE);
                  const availRegions = blockingRules.length === 0 ? [] : computeGaps(blockingRules);
                  const s = RULE_STYLES[AvailabilityRuleType.AVAILABLE];
                  return (
                    <>
                      {blockingRules.length === 0 && (
                        <div className="absolute top-1.5 bottom-1.5 left-0 right-0 rounded-md bg-gray-100 border border-gray-300 flex items-center justify-center">
                          <span className="text-xs font-semibold text-gray-600">All day available</span>
                        </div>
                      )}
                      {availRegions.map((seg, i) => {
                        const left = ((seg.startHour - GRID_START) / GRID_HOURS) * 100;
                        const width = ((seg.endHour - seg.startHour) / GRID_HOURS) * 100;
                        const label = `${formatRuleTime(hoursToTimeStr(seg.startHour))} – ${formatRuleTime(hoursToTimeStr(seg.endHour))}`;
                        return (
                          <div
                            key={`avail-${i}`}
                            className={cn("absolute top-1.5 bottom-1.5 rounded-md border flex items-center px-2 overflow-hidden", s.border, s.bg)}
                            style={{ left: `${left}%`, width: `${width}%` }}
                            title={`Available: ${label}`}
                          >
                            <span className={cn("text-xs font-semibold truncate", s.text)}>
                              {label}
                              <span className="ml-1.5 font-normal opacity-70">Available</span>
                            </span>
                          </div>
                        );
                      })}
                      {blockingRules.map((rule) => {
                        const left = ((rule.startHour - GRID_START) / GRID_HOURS) * 100;
                        const width = ((rule.endHour - rule.startHour) / GRID_HOURS) * 100;
                        const style = RULE_STYLES[rule.ruleType];
                        const timeLabel = rule.isFullDay ? "All day" : `${formatRuleTime(rule.startStr)} – ${formatRuleTime(rule.endStr)}`;
                        return (
                          <div
                            key={rule.id}
                            className={cn(
                              "absolute top-1.5 bottom-1.5 rounded-md border flex items-center px-2 overflow-hidden",
                              rule.isFullDay && "justify-center",
                              style.border,
                              rule.ruleType === AvailabilityRuleType.UNAVAILABLE ? "unavailable-block" : style.bg
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
                    </>
                  );
                })()}

                {pendingRules.filter((pr) => pr.dayOfWeek === dayIdx).map((pr, i) => {
                  const left = ((pr.startHour - GRID_START) / GRID_HOURS) * 100;
                  const width = ((pr.endHour - pr.startHour) / GRID_HOURS) * 100;
                  const timeLabel = `${formatRuleTime(hoursToTimeStr(pr.startHour))} – ${formatRuleTime(hoursToTimeStr(pr.endHour))}`;
                  const typeLabel = RULE_STYLES[pr.ruleType].label;
                  return (
                    <div
                      key={`pending-${i}`}
                      className={cn(
                        "absolute top-0.5 bottom-0.5 rounded-md border flex flex-col justify-center px-2 overflow-hidden opacity-85",
                        pr.isPreview
                          ? "bg-amber-50 border-amber-400 border-dashed"
                          : "bg-amber-100 border-amber-500"
                      )}
                      style={{ left: `${left}%`, width: `${width}%` }}
                      title={`Pending: ${typeLabel} ${timeLabel}`}
                    >
                      <span className="text-[9px] font-semibold text-amber-600 leading-none truncate">Pending</span>
                      <span className="text-xs font-medium text-amber-800 truncate leading-tight mt-0.5">
                        {timeLabel}
                        <span className="ml-1 font-normal opacity-70">· {typeLabel}</span>
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

function CompactAvailability({ rulesByDay, pendingRules }: { rulesByDay: Map<number, ParsedRule[]>; pendingRules: PendingOverlayRule[] }) {
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

            {(() => {
              const blockingRules = dayRules.filter(r => r.ruleType !== AvailabilityRuleType.AVAILABLE);
              if (blockingRules.length === 0) {
                return (
                  <div className="rounded-md bg-gray-100 border border-gray-300 px-3 py-2">
                    <span className="text-xs font-semibold text-gray-600">All day available</span>
                  </div>
                );
              }
              type Segment = { startHour: number; kind: "avail"; endHour: number } | { startHour: number; kind: "rule"; rule: ParsedRule };
              const segments: Segment[] = [
                ...computeGaps(blockingRules).map(seg => ({ startHour: seg.startHour, endHour: seg.endHour, kind: "avail" as const })),
                ...blockingRules.map(rule => ({ startHour: rule.startHour, kind: "rule" as const, rule })),
              ].sort((a, b) => a.startHour - b.startHour);
              return (
                <div className="space-y-1.5">
                  {segments.map((seg, i) => {
                    if (seg.kind === "avail") {
                      const label = `${formatRuleTime(hoursToTimeStr(seg.startHour))} – ${formatRuleTime(hoursToTimeStr(seg.endHour))}`;
                      return (
                        <div key={`avail-${i}`} className={cn("w-full rounded-md border px-3 py-2 flex items-center justify-between", RULE_STYLES[AvailabilityRuleType.AVAILABLE].border, RULE_STYLES[AvailabilityRuleType.AVAILABLE].bg)}>
                          <span className={cn("text-xs font-semibold", RULE_STYLES[AvailabilityRuleType.AVAILABLE].text)}>{label}</span>
                          <Badge className="text-[10px] bg-gray-100 text-gray-600 border-gray-300">Available</Badge>
                        </div>
                      );
                    }
                    const { rule } = seg;
                    const style = RULE_STYLES[rule.ruleType];
                    const isUnavailable = rule.ruleType === AvailabilityRuleType.UNAVAILABLE;
                    const timeLabel = rule.isFullDay ? "All day" : `${formatRuleTime(rule.startStr)} – ${formatRuleTime(rule.endStr)}`;
                    return (
                      <div key={rule.id} className={cn("w-full rounded-md border px-3 py-2 flex items-center justify-between", style.border, isUnavailable ? "unavailable-block" : style.bg)}>
                        <span className={cn("text-xs font-medium", style.text)}>{timeLabel}</span>
                        <Badge className={cn("text-[10px]", isUnavailable ? "bg-red-100 text-red-700 border-red-300" : "bg-emerald-100 text-emerald-700 border-emerald-300")}>{style.label}</Badge>
                      </div>
                    );
                  })}
                </div>
              );
            })()}

            {pendingRules.filter((pr) => pr.dayOfWeek === dayIdx).map((pr, i) => {
              const timeLabel = `${formatRuleTime(hoursToTimeStr(pr.startHour))} – ${formatRuleTime(hoursToTimeStr(pr.endHour))}`;
              const typeLabel = RULE_STYLES[pr.ruleType].label;
              return (
                <div
                  key={`pending-${i}`}
                  className={cn(
                    "mt-1.5 w-full rounded-md border px-3 py-2",
                    pr.isPreview ? "bg-amber-50 border-amber-400 border-dashed" : "bg-amber-100 border-amber-500"
                  )}
                >
                  <p className="text-[10px] font-semibold text-amber-600 leading-none mb-1">Pending</p>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-medium text-amber-800">{timeLabel}</span>
                    <span className="text-xs text-amber-700 opacity-70">· {typeLabel}</span>
                  </div>
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}