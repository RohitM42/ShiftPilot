import { useState, useEffect, useMemo } from "react";
import { Send, Pencil, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/contexts/AuthContext";
import { meApi, aiInputsApi } from "@/services/api";
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

// ── Component ────────────────────────────────────────────────────────

export default function MyAvailability() {
  const { employee } = useAuth();

  const [rules, setRules] = useState<AvailabilityRuleResponse[]>([]);
  const [proposals, setProposals] = useState<AIProposalResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [aiText, setAiText] = useState("");
  const [aiSending, setAiSending] = useState(false);
  const [aiResult, setAiResult] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

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
        setProposals(proposalsRes.data);
      } catch {
        setRules([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

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

  // Send AI input
  const handleAiSubmit = async () => {
    if (!aiText.trim()) return;
    setAiSending(true);
    setAiResult(null);
    setAiError(null);

    try {
      const res = await aiInputsApi.create(aiText.trim(), ["availability_rules"]);
      setAiResult(res.data.summary);
      setAiText("");
      // Refresh proposals
      const proposalsRes = await meApi.getAIProposals().catch(() => ({ data: [] }));
      setProposals(proposalsRes.data);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setAiError(msg ?? "Failed to process request");
    } finally {
      setAiSending(false);
    }
  };

  // Filter to availability-related proposals, most recent first
  const recentProposals = useMemo(() => {
    return proposals
      .filter((p) => p.type === ProposalType.AVAILABILITY)
      .slice(0, 5);
  }, [proposals]);

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
        <Button variant="outline" size="sm" className="gap-1.5" onClick={() => {}}>
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
          {/* Grid view — desktop */}
          <AvailabilityGrid rulesByDay={rulesByDay} />

          {/* Compact view — mobile */}
          <CompactAvailability rulesByDay={rulesByDay} />
        </>
      )}

      {/* AI Input Section */}
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
              placeholder='e.g. "I cannot work Saturdays anymore" or "I would prefer morning shifts on Wednesdays"'
              rows={2}
              className="flex-1 rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring resize-none"
            />
            <Button
              size="icon"
              className="shrink-0 self-end"
              onClick={handleAiSubmit}
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
      {recentProposals.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Recent proposals</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {recentProposals.map((p) => (
                <div key={p.id} className="flex items-center justify-between rounded-md border px-3 py-2">
                  <span className="text-sm text-muted-foreground">
                    Proposal #{p.id}
                  </span>
                  <Badge variant={PROPOSAL_STATUS_VARIANT[p.status] ?? "default"}>
                    {p.status}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
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
      {/* Hour labels */}
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

      {/* Day rows */}
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

                {/* No rules = all day available */}
                {!hasRules && (
                  <div
                    className="absolute top-1.5 bottom-1.5 left-0 right-6 rounded-md bg-muted/40 border border-border/60 flex items-center justify-center"
                  >
                    <span className="text-xs text-muted-foreground">All day</span>
                  </div>
                )}

                {/* Rule blocks */}
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