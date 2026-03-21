import { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Check, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import api, { aiProposalsApi, availabilityRulesApi, coverageApi, roleRequirementsApi } from "@/services/api";
import { ProposalStatus, ProposalType, AvailabilityRuleType } from "@/types";
import type { AIProposalResponse, AvailabilityRuleResponse, CoverageRequirementResponse, RoleRequirementResponse } from "@/types";

// ── Constants ────────────────────────────────────────────────────────

const DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const GRID_START = 0;
const GRID_END = 24;
const GRID_HOURS = GRID_END - GRID_START;

const STATUS_VARIANT: Record<ProposalStatus, "default" | "success" | "destructive" | "warning"> = {
  [ProposalStatus.PENDING]: "warning",
  [ProposalStatus.APPROVED]: "success",
  [ProposalStatus.REJECTED]: "destructive",
  [ProposalStatus.CANCELLED]: "default",
};

const TYPE_LABEL: Record<ProposalType, string> = {
  [ProposalType.AVAILABILITY]: "Availability",
  [ProposalType.COVERAGE]: "Coverage",
  [ProposalType.ROLE_REQUIREMENT]: "Role Requirement",
  [ProposalType.LABOUR_BUDGET]: "Labour Budget",
};

const TYPE_COLOURS: Record<ProposalType, string> = {
  [ProposalType.AVAILABILITY]: "bg-blue-100 text-blue-700 border-blue-200",
  [ProposalType.COVERAGE]: "bg-violet-100 text-violet-700 border-violet-200",
  [ProposalType.ROLE_REQUIREMENT]: "bg-amber-100 text-amber-700 border-amber-200",
  [ProposalType.LABOUR_BUDGET]: "bg-emerald-100 text-emerald-700 border-emerald-200",
};

const AVAIL_COLORS: Record<AvailabilityRuleType, string> = {
  [AvailabilityRuleType.AVAILABLE]: "bg-gray-100 border border-gray-300 text-gray-600",
  [AvailabilityRuleType.PREFERRED]: "bg-emerald-100 border border-emerald-300 text-emerald-700",
  [AvailabilityRuleType.UNAVAILABLE]: "bg-red-100 border border-red-300 text-red-700",
};

// ── Time helpers ─────────────────────────────────────────────────────

function timeToHours(t: string | null | undefined): number {
  if (!t) return 0;
  const [h, m] = t.split(":").map(Number);
  return h + m / 60;
}

function formatHourLabel(hour: number): string {
  if (hour === 24) return "00:00";
  return `${String(hour).padStart(2, "0")}:00`;
}

// ── Types ────────────────────────────────────────────────────────────

interface TimelineSegment {
  startHour: number;
  endHour: number;
  label: string;
  colorClass: string;
  isNew?: boolean;
}

interface AvailChange {
  action: string;
  day_of_week: number;
  start_time: string | null;
  end_time: string | null;
  rule_type: AvailabilityRuleType;
}

interface CoverageChange {
  action: string;
  day_of_week?: number;
  start_time?: string;
  end_time?: string;
  min_staff?: number;
  coverage_id?: number;
}

interface RoleChange {
  action: string;
  day_of_week?: number | null;
  start_time?: string;
  end_time?: string;
  requires_keyholder?: boolean;
  requires_manager?: boolean;
  min_manager_count?: number;
  role_requirement_id?: number;
}

interface ChangesJson {
  intent_type: string;
  employee_id?: number;
  store_id?: number;
  department_id?: number | null;
  summary?: string;
  changes: (AvailChange | CoverageChange | RoleChange)[];
}

// ── Mini timeline ────────────────────────────────────────────────────

const HOUR_TICKS = [0, 6, 12, 18, 24];

function MiniTimeline({
  segments,
  label,
  emptyLabel = "Nothing set",
}: {
  segments: TimelineSegment[];
  label: string;
  emptyLabel?: string;
}) {
  return (
    <div className="space-y-1.5">
      <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">{label}</p>
      <div className="rounded-md border bg-muted/20">
        {/* Hour labels */}
        <div className="relative h-4 mx-2 mt-1.5">
          {HOUR_TICKS.map((h) => (
            <span
              key={h}
              className="absolute text-[9px] text-muted-foreground -translate-x-1/2"
              style={{ left: `${((h - GRID_START) / GRID_HOURS) * 100}%` }}
            >
              {formatHourLabel(h)}
            </span>
          ))}
        </div>
        {/* Timeline row */}
        <div className="relative h-9 mx-2 mb-2 mt-0.5">
          {/* Gridlines */}
          {HOUR_TICKS.map((h) => (
            <div
              key={h}
              className="absolute top-0 bottom-0 bg-border"
              style={{ left: `${((h - GRID_START) / GRID_HOURS) * 100}%`, width: "1px" }}
            />
          ))}

          {segments.length === 0 ? (
            <div className="absolute inset-0 rounded-sm bg-card border border-dashed border-border flex items-center justify-center">
              <span className="text-[10px] text-muted-foreground">{emptyLabel}</span>
            </div>
          ) : (
            segments.map((seg, i) => {
              const left = ((seg.startHour - GRID_START) / GRID_HOURS) * 100;
              const width = ((seg.endHour - seg.startHour) / GRID_HOURS) * 100;
              return (
                <div
                  key={i}
                  className={cn(
                    "absolute top-1 bottom-1 rounded-sm flex items-center px-1.5 overflow-hidden",
                    seg.colorClass,
                    seg.isNew && "ring-2 ring-primary ring-offset-0"
                  )}
                  style={{ left: `${left}%`, width: `${width}%` }}
                  title={seg.label}
                >
                  <span className="text-[10px] font-medium truncate">{seg.label}</span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

// ── Availability simulation ──────────────────────────────────────────

interface TmpAvailRule {
  startH: number;
  endH: number;
  rule_type: AvailabilityRuleType;
  isNew?: boolean;
}

function simulateAvailChanges(
  existing: AvailabilityRuleResponse[],
  day: number,
  changes: AvailChange[]
): TmpAvailRule[] {
  let rules: TmpAvailRule[] = existing
    .filter((r) => r.active && r.day_of_week === day)
    .map((r) => ({
      startH: timeToHours(r.start_time_local),
      endH: timeToHours(r.end_time_local) || 24,
      rule_type: r.rule_type as AvailabilityRuleType,
    }));

  for (const change of changes) {
    if (change.action === "ADD") {
      const ns = timeToHours(change.start_time);
      const ne = timeToHours(change.end_time) || 24;
      const kept: TmpAvailRule[] = [];
      for (const r of rules) {
        const { startH: es, endH: ee } = r;
        if (!(ns < ee && ne > es)) { kept.push(r); continue; }
        if (ns <= es && ne >= ee) { /* discard — fully covered */ }
        else if (ns <= es) { kept.push({ ...r, startH: ne }); }
        else if (ne >= ee) { kept.push({ ...r, endH: ns }); }
        else { kept.push({ ...r, endH: ns }); kept.push({ ...r, startH: ne }); }
      }
      kept.push({ startH: ns, endH: ne, rule_type: change.rule_type, isNew: true });
      rules = kept;
    } else if (change.action === "REMOVE") {
      const ns = timeToHours(change.start_time);
      const ne = timeToHours(change.end_time) || 24;
      rules = rules.filter((r) => !(Math.abs(r.startH - ns) < 0.01 && Math.abs(r.endH - ne) < 0.01));
    }
  }

  // Merge adjacent same-type
  rules.sort((a, b) => a.startH - b.startH);
  const merged: TmpAvailRule[] = [];
  for (const r of rules) {
    const prev = merged[merged.length - 1];
    if (prev && prev.rule_type === r.rule_type && Math.abs(prev.endH - r.startH) < 0.01) {
      prev.endH = r.endH;
      if (r.isNew) prev.isNew = true;
    } else {
      merged.push({ ...r });
    }
  }
  return merged;
}

function availToSegments(rules: TmpAvailRule[]): TimelineSegment[] {
  return rules.map((r) => ({
    startHour: r.startH,
    endHour: r.endH,
    label: r.rule_type.charAt(0) + r.rule_type.slice(1).toLowerCase(),
    colorClass: AVAIL_COLORS[r.rule_type] ?? "bg-gray-100 border border-gray-300",
    isNew: r.isNew,
  }));
}

function existingAvailToSegments(rules: AvailabilityRuleResponse[], day: number): TimelineSegment[] {
  return rules
    .filter((r) => r.active && r.day_of_week === day)
    .map((r) => ({
      startHour: timeToHours(r.start_time_local),
      endHour: timeToHours(r.end_time_local) || 24,
      label: (r.rule_type as string).charAt(0).toUpperCase() + (r.rule_type as string).slice(1).toLowerCase(),
      colorClass: AVAIL_COLORS[r.rule_type as AvailabilityRuleType] ?? "bg-gray-100 border border-gray-300",
    }));
}

// ── Coverage simulation ──────────────────────────────────────────────

function covToSegments(reqs: CoverageRequirementResponse[], day: number): TimelineSegment[] {
  return reqs
    .filter((r) => r.active && r.day_of_week === day)
    .map((r) => ({
      startHour: timeToHours(r.start_time_local),
      endHour: timeToHours(r.end_time_local) || 24,
      label: `${r.min_staff} staff`,
      colorClass: "bg-violet-100 border border-violet-300 text-violet-700",
    }));
}

function simulateCoverageChanges(
  existing: CoverageRequirementResponse[],
  day: number,
  changes: CoverageChange[]
): TimelineSegment[] {
  let reqs = existing.filter((r) => r.active && r.day_of_week === day);
  const newSegs: TimelineSegment[] = [];

  for (const change of changes) {
    if (change.action === "ADD") {
      newSegs.push({
        startHour: timeToHours(change.start_time),
        endHour: timeToHours(change.end_time) || 24,
        label: `${change.min_staff ?? 1} staff`,
        colorClass: "bg-violet-100 border border-violet-300 text-violet-700",
        isNew: true,
      });
    } else if (change.action === "REMOVE" && change.coverage_id) {
      reqs = reqs.filter((r) => r.id !== change.coverage_id);
    }
  }

  return [
    ...reqs.map((r) => ({
      startHour: timeToHours(r.start_time_local),
      endHour: timeToHours(r.end_time_local) || 24,
      label: `${r.min_staff} staff`,
      colorClass: "bg-violet-100 border border-violet-300 text-violet-700",
    })),
    ...newSegs,
  ];
}

// ── Role simulation ──────────────────────────────────────────────────

function roleLabel(r: { requires_manager?: boolean; min_manager_count?: number }) {
  return r.requires_manager ? `≥${r.min_manager_count ?? 1} manager` : "Keyholder";
}

function roleColor(r: { requires_manager?: boolean }) {
  return r.requires_manager
    ? "bg-blue-100 border border-blue-300 text-blue-700"
    : "bg-amber-100 border border-amber-300 text-amber-700";
}

function roleToSegments(reqs: RoleRequirementResponse[], day: number): TimelineSegment[] {
  return reqs
    .filter((r) => r.active && (r.day_of_week === day || r.day_of_week === null))
    .map((r) => ({
      startHour: timeToHours(r.start_time_local),
      endHour: timeToHours(r.end_time_local) || 24,
      label: roleLabel(r),
      colorClass: roleColor(r),
    }));
}

function simulateRoleChanges(
  existing: RoleRequirementResponse[],
  day: number,
  changes: RoleChange[]
): TimelineSegment[] {
  let reqs = existing.filter((r) => r.active && (r.day_of_week === day || r.day_of_week === null));
  const newSegs: TimelineSegment[] = [];

  for (const change of changes) {
    if (change.action === "ADD") {
      newSegs.push({
        startHour: timeToHours(change.start_time),
        endHour: timeToHours(change.end_time) || 24,
        label: roleLabel(change),
        colorClass: roleColor(change),
        isNew: true,
      });
    } else if (change.action === "REMOVE" && change.role_requirement_id) {
      reqs = reqs.filter((r) => r.id !== change.role_requirement_id);
    }
  }

  return [
    ...reqs.map((r) => ({
      startHour: timeToHours(r.start_time_local),
      endHour: timeToHours(r.end_time_local) || 24,
      label: roleLabel(r),
      colorClass: roleColor(r),
    })),
    ...newSegs,
  ];
}

// ── Reject dialog ────────────────────────────────────────────────────

function RejectDialog({
  onConfirm,
  onCancel,
  loading,
}: {
  onConfirm: (reason: string) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [reason, setReason] = useState("");
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-background rounded-xl border shadow-xl w-full max-w-md mx-4 p-6 space-y-4">
        <div>
          <h2 className="text-base font-semibold">Reject proposal</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Provide an optional reason below.
          </p>
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium">
            Reason <span className="text-muted-foreground font-normal">(optional)</span>
          </label>
          <textarea
            className="w-full rounded-md border bg-muted/30 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring resize-none"
            rows={3}
            placeholder="Explain why this proposal is being rejected…"
            value={reason}
            autoFocus
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
        <div className="flex justify-end gap-2 pt-1">
          <Button variant="outline" size="sm" onClick={onCancel} disabled={loading}>
            Cancel
          </Button>
          <Button variant="destructive" size="sm" onClick={() => onConfirm(reason)} disabled={loading}>
            {loading ? <Loader2 size={14} className="animate-spin mr-1.5" /> : <X size={14} className="mr-1.5" />}
            Reject
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────

export default function ProposalView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [proposal, setProposal] = useState<AIProposalResponse & { changes_json?: ChangesJson; source?: string } | null>(null);
  const [changesJson, setChangesJson] = useState<ChangesJson | null>(null);
  const [availRules, setAvailRules] = useState<AvailabilityRuleResponse[]>([]);
  const [coverageReqs, setCoverageReqs] = useState<CoverageRequirementResponse[]>([]);
  const [roleReqs, setRoleReqs] = useState<RoleRequirementResponse[]>([]);
  const [summary, setSummary] = useState("");
  const [affectedName, setAffectedName] = useState("");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showReject, setShowReject] = useState(false);

  useEffect(() => {
    if (!id) return;
    const load = async () => {
      setLoading(true);
      try {
        const propRes = await api.get(`/ai-proposals/${id}`);
        const prop = propRes.data;
        setProposal(prop);

        // Resolve changes_json — manual proposals have it directly, AI proposals need ai_output fetch
        let cj: ChangesJson | null = null;
        if (prop.changes_json) {
          cj = prop.changes_json;
          setSummary(prop.changes_json.summary ?? "");
        } else if (prop.ai_output_id) {
          const outRes = await api.get(`/ai-outputs/${prop.ai_output_id}`);
          cj = outRes.data.result_json;
          setSummary(outRes.data.summary ?? "");
          if (outRes.data.affects_user_id) {
            try {
              const empRes = await api.get("/employees", { params: { store_id: prop.store_id } });
              const match = empRes.data.find(
                (e: { user_id: number; firstname: string; surname: string }) =>
                  e.user_id === outRes.data.affects_user_id
              );
              if (match) setAffectedName(`${match.firstname} ${match.surname}`);
            } catch {}
          }
        }
        setChangesJson(cj);
        if (!cj) return;

        if (cj.intent_type === "AVAILABILITY" && cj.employee_id) {
          try {
            const empRes = await api.get(`/employees/${cj.employee_id}`);
            setAffectedName(`${empRes.data.firstname} ${empRes.data.surname}`);
          } catch {}
          const rulesRes = await availabilityRulesApi.getForEmployee(cj.employee_id);
          setAvailRules(rulesRes.data);
        } else if (cj.intent_type === "COVERAGE") {
          const covRes = await coverageApi.list({
            store_id: cj.store_id,
            department_id: cj.department_id ?? undefined,
          });
          setCoverageReqs(covRes.data);
        } else if (cj.intent_type === "ROLE_REQUIREMENT") {
          const roleRes = await roleRequirementsApi.list({ store_id: cj.store_id });
          setRoleReqs(roleRes.data);
        }
      } catch {
        // leave empty
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  // Collect affected days from changes
  const affectedDays = useMemo(() => {
    if (!changesJson) return [];
    const days = new Set<number>();
    for (const c of changesJson.changes) {
      const d = (c as AvailChange).day_of_week ?? (c as RoleChange).day_of_week;
      if (d !== null && d !== undefined) days.add(d as number);
    }
    return Array.from(days).sort();
  }, [changesJson]);

  const handleApprove = async () => {
    if (!proposal) return;
    setActionLoading(true);
    try {
      await aiProposalsApi.approve(proposal.id);
      navigate("/proposals");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (reason: string) => {
    if (!proposal) return;
    setActionLoading(true);
    try {
      await aiProposalsApi.reject(proposal.id, reason || undefined);
      navigate("/proposals");
    } finally {
      setActionLoading(false);
      setShowReject(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
        <Loader2 size={18} className="animate-spin mr-2" /> Loading proposal…
      </div>
    );
  }

  if (!proposal || !changesJson) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
        Proposal not found.
      </div>
    );
  }

  const isPending = proposal.status === ProposalStatus.PENDING;
  const isAvailability = changesJson.intent_type === "AVAILABILITY";
  const isCoverage = changesJson.intent_type === "COVERAGE";
  const isRole = changesJson.intent_type === "ROLE_REQUIREMENT";

  const renderDay = (day: number) => {
    let beforeSegs: TimelineSegment[] = [];
    let afterSegs: TimelineSegment[] = [];

    if (isAvailability) {
      const changes = (changesJson.changes as AvailChange[]).filter((c) => c.day_of_week === day);
      beforeSegs = existingAvailToSegments(availRules, day);
      afterSegs = availToSegments(simulateAvailChanges(availRules, day, changes));
    } else if (isCoverage) {
      const changes = (changesJson.changes as CoverageChange[]).filter((c) => c.day_of_week === day);
      beforeSegs = covToSegments(coverageReqs, day);
      afterSegs = simulateCoverageChanges(coverageReqs, day, changes);
    } else if (isRole) {
      const changes = (changesJson.changes as RoleChange[]).filter(
        (c) => c.day_of_week === day || c.day_of_week === null
      );
      beforeSegs = roleToSegments(roleReqs, day);
      afterSegs = simulateRoleChanges(roleReqs, day, changes);
    }

    const emptyLabel = isAvailability ? "All day available" : "None";

    return (
      <div key={day} className="rounded-lg border bg-card p-4 space-y-3">
        <h3 className="text-sm font-semibold">{DAY_NAMES[day]}</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <MiniTimeline segments={beforeSegs} label="Before" emptyLabel={emptyLabel} />
          <MiniTimeline segments={afterSegs} label="After" emptyLabel={emptyLabel} />
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => navigate("/proposals")}>
          <ArrowLeft size={16} />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">View Proposal</h1>
          <p className="text-sm text-muted-foreground mt-0.5">#{proposal.id}</p>
        </div>
      </div>

      {/* Proposal info card */}
      <div className="rounded-lg border bg-card px-4 py-3 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium", TYPE_COLOURS[proposal.type])}>
            {TYPE_LABEL[proposal.type]}
          </span>
          {proposal.source === "MANUAL" && (
            <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium bg-slate-100 text-slate-600 border-slate-200">
              Manual
            </span>
          )}
          <Badge variant={STATUS_VARIANT[proposal.status]}>{proposal.status}</Badge>
        </div>
        {summary && <p className="text-sm text-foreground">{summary}</p>}
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          {affectedName && (
            <span>Affects: <span className="text-foreground font-medium">{affectedName}</span></span>
          )}
          {proposal.rejection_reason && (
            <span className="text-destructive">Rejected: {proposal.rejection_reason}</span>
          )}
        </div>
      </div>

      {/* Before / After per affected day */}
      {affectedDays.length > 0 ? (
        <div className="space-y-3">
          {affectedDays.map((day) => renderDay(day))}
        </div>
      ) : (
        <div className="flex items-center justify-center h-32 text-muted-foreground text-sm rounded-lg border border-dashed">
          No day-specific changes to preview.
        </div>
      )}

      {/* Action bar — pending only */}
      {isPending && (
        <div className="flex items-center justify-end gap-2 pt-2 border-t">
          <Button
            variant="destructive"
            size="sm"
            className="gap-1.5"
            onClick={() => setShowReject(true)}
            disabled={actionLoading}
          >
            <X size={14} />
            Reject
          </Button>
          <Button
            size="sm"
            className="gap-1.5 bg-emerald-600 hover:bg-emerald-700"
            onClick={handleApprove}
            disabled={actionLoading}
          >
            {actionLoading
              ? <Loader2 size={14} className="animate-spin" />
              : <Check size={14} />}
            Approve
          </Button>
        </div>
      )}

      {showReject && (
        <RejectDialog
          onConfirm={handleReject}
          onCancel={() => setShowReject(false)}
          loading={actionLoading}
        />
      )}
    </div>
  );
}
