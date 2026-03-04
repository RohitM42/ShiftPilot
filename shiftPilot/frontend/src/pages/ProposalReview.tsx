import { useState, useEffect, useMemo } from "react";
import { Check, X, Eye, Loader2, ChevronDown, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/contexts/AuthContext";
import api, { aiProposalsApi } from "@/services/api";
import { ProposalStatus, ProposalType } from "@/types";
import type { AIProposalResponse } from "@/types";

// ── Types ────────────────────────────────────────────────────────────

interface EnrichedProposal extends AIProposalResponse {
  summary?: string;
  affects_user_id?: number | null;
  affectedUserName?: string;
  requestedByName?: string;
}

interface StoreOption {
  id: number;
  name: string;
}

// ── Constants ────────────────────────────────────────────────────────

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

const STATUS_FILTER_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: ProposalStatus.PENDING, label: "Pending" },
  { value: ProposalStatus.APPROVED, label: "Approved" },
  { value: ProposalStatus.REJECTED, label: "Rejected" },
  { value: ProposalStatus.CANCELLED, label: "Cancelled" },
];

const TYPE_FILTER_OPTIONS = [
  { value: "all", label: "All types" },
  { value: ProposalType.AVAILABILITY, label: "Availability" },
  { value: ProposalType.COVERAGE, label: "Coverage" },
  { value: ProposalType.ROLE_REQUIREMENT, label: "Role Requirement" },
  { value: ProposalType.LABOUR_BUDGET, label: "Labour Budget" },
];

// ── Reject Dialog ────────────────────────────────────────────────────

function RejectDialog({
  proposal,
  onConfirm,
  onCancel,
  loading,
}: {
  proposal: EnrichedProposal;
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
            Proposal #{proposal.id} · {TYPE_LABEL[proposal.type]}
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
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
        <div className="flex justify-end gap-2 pt-1">
          <Button variant="outline" size="sm" onClick={onCancel} disabled={loading}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => onConfirm(reason)}
            disabled={loading}
          >
            {loading ? <Loader2 size={14} className="animate-spin mr-1.5" /> : <X size={14} className="mr-1.5" />}
            Reject
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Proposal Card ────────────────────────────────────────────────────

function ProposalCard({
  proposal,
  storeName,
  onApprove,
  onReject,
  approving,
}: {
  proposal: EnrichedProposal;
  storeName: string;
  onApprove: (p: EnrichedProposal) => void;
  onReject: (p: EnrichedProposal) => void;
  approving: number | null;
}) {
  const isPending = proposal.status === ProposalStatus.PENDING;

  return (
    <Card className="px-4 py-3.5 space-y-2.5">
      {/* Top row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${TYPE_COLOURS[proposal.type]}`}
          >
            {TYPE_LABEL[proposal.type]}
          </span>
          {(proposal as AIProposalResponse & { source?: string }).source === "MANUAL" && (
            <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium bg-slate-100 text-slate-600 border-slate-200">
              Manual
            </span>
          )}
          <Badge variant={STATUS_VARIANT[proposal.status]}>{proposal.status}</Badge>
          <span className="text-xs text-muted-foreground">#{proposal.id}</span>
        </div>
        <span className="text-xs text-muted-foreground shrink-0">
          {new Date(proposal.created_at).toLocaleDateString(undefined, {
            day: "numeric",
            month: "short",
            year: "numeric",
          })}
        </span>
      </div>

      {/* Summary + meta + actions row */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1.5 min-w-0">
          {proposal.summary && (
            <p className="text-sm text-foreground leading-snug">{proposal.summary}</p>
          )}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span>Store: <span className="text-foreground font-medium">{storeName}</span></span>

            {proposal.affectedUserName && (
              <>
                <span>·</span>
                <span>Affects: <span className="text-foreground font-medium">{proposal.affectedUserName}</span></span>
              </>
            )}

            {proposal.requestedByName && proposal.type !== ProposalType.AVAILABILITY && (
              <>
                <span>·</span>
                <span>Requested by: <span className="text-foreground font-medium">{proposal.requestedByName}</span></span>
              </>
            )}

            {proposal.rejection_reason && (
              <>
                <span>·</span>
                <span className="text-destructive">Reason: {proposal.rejection_reason}</span>
              </>
            )}
          </div>
        </div>

        {isPending && (
          <div className="flex items-center gap-2 shrink-0">
            <Button size="sm" variant="outline" className="gap-1.5 text-xs h-8" onClick={() => {}} disabled>
              <Eye size={13} />
              View
            </Button>
            <Button
              size="sm"
              className="gap-1.5 text-xs h-8 bg-emerald-600 hover:bg-emerald-700 text-white"
              onClick={() => onApprove(proposal)}
              disabled={approving === proposal.id}
            >
              {approving === proposal.id
                ? <Loader2 size={13} className="animate-spin" />
                : <Check size={13} />}
              Approve
            </Button>
            <Button
              size="sm"
              variant="destructive"
              className="gap-1.5 text-xs h-8"
              onClick={() => onReject(proposal)}
              disabled={approving === proposal.id}
            >
              <X size={13} />
              Reject
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}

// ── Main Component ───────────────────────────────────────────────────

export default function ProposalReview() {
  const { isAdmin, employee: currentEmployee } = useAuth();

  const [proposals, setProposals] = useState<EnrichedProposal[]>([]);
  const [stores, setStores] = useState<StoreOption[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [storeFilter, setStoreFilter] = useState<number | "all">("all");
  const [statusFilter, setStatusFilter] = useState<ProposalStatus | "all">(ProposalStatus.PENDING);
  const [typeFilter, setTypeFilter] = useState<ProposalType | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Action state
  const [approving, setApproving] = useState<number | null>(null);
  const [rejectTarget, setRejectTarget] = useState<EnrichedProposal | null>(null);
  const [rejecting, setRejecting] = useState(false);

  // Fetch stores (admin only)
  useEffect(() => {
    if (!isAdmin) return;
    api.get("/stores").then((r) => setStores(r.data)).catch(() => {});
  }, [isAdmin]);

  // Fetch + enrich proposals
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        // Determine which endpoint to use
        const storeId = isAdmin
          ? storeFilter !== "all" ? storeFilter : undefined
          : currentEmployee?.store_id;

        // Managers only see AVAILABILITY proposals
        const typeParam = !isAdmin ? ProposalType.AVAILABILITY : undefined;

        let raw: AIProposalResponse[] = [];

        if (storeId) {
          const res = await aiProposalsApi.getByStore(storeId, { type: typeParam });
          raw = res.data;
        } else {
          const res = await aiProposalsApi.getAll({ type: typeParam });
          raw = res.data;
        }
        const enriched = await Promise.all(
          raw.map(async (p): Promise<EnrichedProposal> => {
            let summary: string | undefined;
            let affects_user_id: number | null | undefined;
            let affectedUserName: string | undefined;
            let requestedByName: string | undefined;

            const isManual = !p.ai_output_id;

            if (isManual) {
              // Manual proposal — read directly from changes_json
              const cj = (p as AIProposalResponse & { changes_json?: { summary?: string; employee_id?: number } }).changes_json;
              summary = cj?.summary;
              // For manual proposals we need to resolve the affected employee via changes_json.employee_id
              if (cj?.employee_id) {
                try {
                  const empRes = await api.get("/employees", { params: { store_id: p.store_id } });
                  const match = empRes.data.find(
                    (e: { id: number; firstname: string; surname: string }) => e.id === cj.employee_id
                  );
                  if (match) affectedUserName = `${match.firstname} ${match.surname}`;
                } catch {}
              }
            } else {
              // AI proposal — fetch ai_output for summary + affects_user_id
              try {
                const outRes = await api.get(`/ai-outputs/${p.ai_output_id}`);
                summary = outRes.data.summary;
                affects_user_id = outRes.data.affects_user_id;
              } catch {}

              // Resolve affected user name
              if (affects_user_id) {
                try {
                  const empRes = await api.get("/employees", { params: { store_id: p.store_id } });
                  const match = empRes.data.find(
                    (e: { user_id: number; firstname: string; surname: string }) =>
                      e.user_id === affects_user_id
                  );
                  if (match) affectedUserName = `${match.firstname} ${match.surname}`;
                } catch {}
              }

              // Resolve requested-by name (non-availability only)
              if (p.type !== ProposalType.AVAILABILITY) {
                try {
                  const outRes = await api.get(`/ai-outputs/${p.ai_output_id}`);
                  const inputRes = await api.get(`/ai-inputs/${outRes.data.input_id}`);
                  const reqUserId = inputRes.data.req_by_user_id;
                  const empRes = await api.get("/employees", { params: { store_id: p.store_id } });
                  const match = empRes.data.find(
                    (e: { user_id: number; firstname: string; surname: string }) =>
                      e.user_id === reqUserId
                  );
                  if (match) requestedByName = `${match.firstname} ${match.surname}`;
                } catch {}
              }
            }

            return { ...p, summary, affects_user_id, affectedUserName, requestedByName };
          })
        );

        setProposals(enriched);
      } catch {
        setProposals([]);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [isAdmin, currentEmployee, storeFilter]);

  // Apply status, type, and search filters client-side
  const filtered = useMemo(() => {
    let list = statusFilter === "all" ? proposals : proposals.filter((p) => p.status === statusFilter);
    if (isAdmin && typeFilter !== "all") list = list.filter((p) => p.type === typeFilter);
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      list = list.filter((p) =>
        p.summary?.toLowerCase().includes(q) ||
        p.affectedUserName?.toLowerCase().includes(q) ||
        p.requestedByName?.toLowerCase().includes(q)
      );
    }
    return list.sort((a, b) => {
      if (a.status === ProposalStatus.PENDING && b.status !== ProposalStatus.PENDING) return -1;
      if (a.status !== ProposalStatus.PENDING && b.status === ProposalStatus.PENDING) return 1;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
  }, [proposals, statusFilter, typeFilter, searchQuery, isAdmin]);

  // Store name lookup
  const storeMap = useMemo(() => {
    const m = new Map<number, string>();
    for (const s of stores) m.set(s.id, s.name);
    return m;
  }, [stores]);

  const getStoreName = (storeId: number | null | undefined) => {
    if (!storeId) return "—";
    return storeMap.get(storeId) ?? `Store ${storeId}`;
  };

  // Approve
  const handleApprove = async (proposal: EnrichedProposal) => {
    setApproving(proposal.id);
    try {
      await aiProposalsApi.approve(proposal.id);
      setProposals((prev) =>
        prev.map((p) =>
          p.id === proposal.id ? { ...p, status: ProposalStatus.APPROVED } : p
        )
      );
    } catch {
      // could add toast here
    } finally {
      setApproving(null);
    }
  };

  // Reject
  const handleRejectConfirm = async (reason: string) => {
    if (!rejectTarget) return;
    setRejecting(true);
    try {
      await aiProposalsApi.reject(rejectTarget.id, reason || undefined);
      setProposals((prev) =>
        prev.map((p) =>
          p.id === rejectTarget.id
            ? { ...p, status: ProposalStatus.REJECTED, rejection_reason: reason || null }
            : p
        )
      );
      setRejectTarget(null);
    } catch {
      // could add toast here
    } finally {
      setRejecting(false);
    }
  };

  const pendingCount = proposals.filter((p) => p.status === ProposalStatus.PENDING).length;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Proposal Review</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {pendingCount} pending proposal{pendingCount !== 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={isAdmin ? "Search name, department…" : "Search by name…"}
            className="w-full rounded-md border bg-background px-9 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        {/* Store filter — admin only */}
        {isAdmin && (
          <div className="relative">
            <select
              value={storeFilter}
              onChange={(e) =>
                setStoreFilter(e.target.value === "all" ? "all" : Number(e.target.value))
              }
              className="appearance-none rounded-md border bg-background pl-3 pr-8 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="all">All stores</option>
              {stores.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          </div>
        )}

        {/* Status filter */}
        <div className="relative">
          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as ProposalStatus | "all")
            }
            className="appearance-none rounded-md border bg-background pl-3 pr-8 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          >
            {STATUS_FILTER_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
        </div>

        {/* Type filter — admin only */}
        {isAdmin && (
          <div className="relative">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as ProposalType | "all")}
              className="appearance-none rounded-md border bg-background pl-3 pr-8 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            >
              {TYPE_FILTER_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          </div>
        )}
      </div>

      {/* List */}
      {loading ? (
        <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
          <Loader2 size={18} className="animate-spin mr-2" /> Loading proposals…
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
          No proposals found
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((p) => (
            <ProposalCard
              key={p.id}
              proposal={p}
              storeName={getStoreName(p.store_id)}
              onApprove={handleApprove}
              onReject={setRejectTarget}
              approving={approving}
            />
          ))}
        </div>
      )}

      {/* Reject dialog */}
      {rejectTarget && (
        <RejectDialog
          proposal={rejectTarget}
          onConfirm={handleRejectConfirm}
          onCancel={() => setRejectTarget(null)}
          loading={rejecting}
        />
      )}
    </div>
  );
}