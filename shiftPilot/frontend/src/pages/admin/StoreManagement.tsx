import { useState, useEffect, useCallback, useMemo } from "react";
import { Plus, ChevronRight, ChevronDown, Store, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
  storesApi,
  storeDepartmentsApi,
  departmentsAdminApi,
} from "@/services/api";
import type {
  StoreResponse,
  DepartmentResponse,
  StoreDepartmentResponse,
} from "@/types";

// ── Constants ─────────────────────────────────────────────────────────

const TIMEZONES = [
  "UTC",
  "Europe/London",
  "Europe/Paris",
  "Europe/Berlin",
  "Europe/Amsterdam",
  "Europe/Madrid",
  "Europe/Rome",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Toronto",
  "Asia/Dubai",
  "Asia/Singapore",
  "Asia/Tokyo",
  "Australia/Sydney",
  "Pacific/Auckland",
];

// ── Component ─────────────────────────────────────────────────────────

export default function StoreManagement() {
  // Store list
  const [stores, setStores] = useState<StoreResponse[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<
    number | "new" | null
  >(null);

  // Details form
  const [detailsForm, setDetailsForm] = useState({
    name: "",
    location: "",
    timezone: "UTC",
    opening_time: "07:00",
    closing_time: "22:00",
  });

  // Departments
  const [allDepts, setAllDepts] = useState<DepartmentResponse[]>([]);
  const [storeDepts, setStoreDepts] = useState<StoreDepartmentResponse[]>([]);
  const [expandedDeptId, setExpandedDeptId] = useState<number | null>(null);
  const [deptEditForms, setDeptEditForms] = useState<
    Record<number, { name: string; code: string; has_manager_role: boolean }>
  >({});
  const [showCreateDept, setShowCreateDept] = useState(false);
  const [newDeptForm, setNewDeptForm] = useState({
    name: "",
    code: "",
    has_manager_role: false,
  });

  // UI state
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmRemoveDept, setConfirmRemoveDept] = useState<number | null>(
    null
  );
  const [confirmDeactivateDeptId, setConfirmDeactivateDeptId] = useState<number | null>(null);
  const [deactivateWarnings, setDeactivateWarnings] = useState<Array<{ employee_id: number; name: string }> | null>(null);
  const [removeWarnings, setRemoveWarnings] = useState<Array<{ employee_id: number; name: string }> | null>(null);

  // ── Data fetching ───────────────────────────────────────────────────

  const fetchStores = useCallback(async () => {
    try {
      const res = await storesApi.list();
      setStores(res.data);
    } catch {
      setError('Failed to load stores. Please try again.');
      setTimeout(() => setError(null), 3000);
    }
  }, []);

  const fetchAllDepts = useCallback(async () => {
    try {
      const res = await departmentsAdminApi.list(false);
      setAllDepts(res.data);
    } catch {
      setError('Failed to load departments. Please try again.');
      setTimeout(() => setError(null), 3000);
    }
  }, []);

  const fetchStoreDepts = useCallback(async (storeId: number) => {
    try {
      const res = await storeDepartmentsApi.listForStore(storeId);
      setStoreDepts(res.data);
    } catch {
      setStoreDepts([]);
    }
  }, []);

  // On mount
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([fetchStores(), fetchAllDepts()]);
      setLoading(false);
    };
    init();
  }, [fetchStores, fetchAllDepts]);

  // When selected store changes
  useEffect(() => {
    if (typeof selectedStoreId === "number") {
      const store = stores.find((s) => s.id === selectedStoreId);
      if (store) {
        setDetailsForm({
          name: store.name,
          location: store.location,
          timezone: store.timezone,
          // Python serialises time as "HH:MM:SS" — strip seconds for the time input
          opening_time: store.opening_time?.slice(0, 5) ?? "07:00",
          closing_time: store.closing_time?.slice(0, 5) ?? "22:00",
        });
      }
      fetchStoreDepts(selectedStoreId);
    } else if (selectedStoreId === "new") {
      setDetailsForm({ name: "", location: "", timezone: "UTC", opening_time: "07:00", closing_time: "22:00" });
      setStoreDepts([]);
    }
    setExpandedDeptId(null);
    setShowCreateDept(false);
  }, [selectedStoreId, stores, fetchStoreDepts]);

  // ── Helpers ─────────────────────────────────────────────────────────

  const storeDeptIds = useMemo(
    () => new Set(storeDepts.map((sd) => sd.department_id)),
    [storeDepts]
  );

  const selectedStore =
    typeof selectedStoreId === "number"
      ? stores.find((s) => s.id === selectedStoreId) ?? null
      : null;

  // ── Handlers ────────────────────────────────────────────────────────

  const handleSaveDetails = async () => {
    if (!detailsForm.name.trim() || !detailsForm.location.trim()) return;
    setSaving(true);
    try {
      if (selectedStoreId === "new") {
        const res = await storesApi.create(detailsForm);
        await fetchStores();
        setSelectedStoreId(res.data.id);
      } else if (typeof selectedStoreId === "number") {
        await storesApi.update(selectedStoreId, detailsForm);
        await fetchStores();
      }
    } catch {
      setError('Failed to save. Please try again.');
      setTimeout(() => setError(null), 3000);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleDept = async (deptId: number, isAssigned: boolean) => {
    if (typeof selectedStoreId !== "number") return;
    if (isAssigned) {
      // Show confirmation before removing
      setConfirmRemoveDept(deptId);
    } else {
      // Add
      try {
        await storeDepartmentsApi.add(selectedStoreId, deptId);
        await fetchStoreDepts(selectedStoreId);
      } catch {
        // silent
      }
    }
  };

  const handleConfirmRemoveDept = async () => {
    if (typeof selectedStoreId !== "number" || confirmRemoveDept === null)
      return;
    try {
      const res = await storeDepartmentsApi.remove(selectedStoreId, confirmRemoveDept);
      await fetchStoreDepts(selectedStoreId);
      if (res.data.warnings && res.data.warnings.length > 0) {
        setRemoveWarnings(res.data.warnings);
      }
    } catch {
      // silent
    } finally {
      setConfirmRemoveDept(null);
    }
  };

  const handleExpandDept = (deptId: number) => {
    if (expandedDeptId === deptId) {
      setExpandedDeptId(null);
    } else {
      setExpandedDeptId(deptId);
      const dept = allDepts.find((d) => d.id === deptId);
      if (dept) {
        setDeptEditForms((prev) => ({
          ...prev,
          [deptId]: {
            name: dept.name,
            code: dept.code,
            has_manager_role: dept.has_manager_role,
          },
        }));
      }
    }
  };

  const handleSaveDept = async (deptId: number) => {
    const form = deptEditForms[deptId];
    if (!form) return;
    setSaving(true);
    try {
      await departmentsAdminApi.update(deptId, form);
      await fetchAllDepts();
    } catch {
      setError('Failed to save. Please try again.');
      setTimeout(() => setError(null), 3000);
    } finally {
      setSaving(false);
    }
  };


  const handleCreateDept = async () => {
    if (!newDeptForm.name.trim() || !newDeptForm.code.trim()) return;
    if (typeof selectedStoreId !== "number") return;
    setSaving(true);
    try {
      const res = await departmentsAdminApi.create(newDeptForm);
      await storeDepartmentsApi.add(selectedStoreId, res.data.id);
      await Promise.all([fetchAllDepts(), fetchStoreDepts(selectedStoreId)]);
      setNewDeptForm({ name: "", code: "", has_manager_role: false });
      setShowCreateDept(false);
    } catch {
      setError('Failed to save. Please try again.');
      setTimeout(() => setError(null), 3000);
    } finally {
      setSaving(false);
    }
  };

  const handleConfirmDeactivate = async () => {
    if (!confirmDeactivateDeptId) return;
    setSaving(true);
    try {
      const res = await departmentsAdminApi.deactivate(confirmDeactivateDeptId);
      await fetchAllDepts();
      if (typeof selectedStoreId === "number") {
        await fetchStoreDepts(selectedStoreId);
      }
      setExpandedDeptId(null);
      if (res.data.warnings && res.data.warnings.length > 0) {
        setDeactivateWarnings(res.data.warnings);
      }
    } catch {
      setError('Failed to save. Please try again.');
      setTimeout(() => setError(null), 3000);
    } finally {
      setSaving(false);
      setConfirmDeactivateDeptId(null);
    }
  };

  // ── Render ──────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
        Loading stores...
      </div>
    );
  }

  return (
    <div className="flex gap-6 h-[calc(100vh-8rem)]">
      {/* ── Left panel: Store list ── */}
      <div className="w-72 shrink-0 flex flex-col gap-2">
        <Button
          className="w-full gap-2"
          onClick={() => setSelectedStoreId("new")}
        >
          <Plus size={16} />
          New Store
        </Button>

        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {stores.map((store) => (
            <Card
              key={store.id}
              className={`cursor-pointer px-4 py-3 transition-colors ${
                selectedStoreId === store.id
                  ? "border-primary bg-primary/5"
                  : "hover:bg-accent"
              }`}
              onClick={() => setSelectedStoreId(store.id)}
            >
              <div className="flex items-center gap-3">
                <Store size={16} className="text-muted-foreground shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-semibold truncate">{store.name}</p>
                  <p className="text-xs text-muted-foreground truncate">
                    {store.location}
                  </p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* ── Right panel ── */}
      <div className="flex-1 overflow-y-auto space-y-6 pr-1">
        {error && (
          <div className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive mb-4">
            {error}
          </div>
        )}
        {selectedStoreId === null ? (
          <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
            Select a store or create a new one
          </div>
        ) : (
          <>
            {/* Section 1: Store Details */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">
                  {selectedStoreId === "new" ? "New Store" : "Store Details"}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium">Name *</label>
                    <input
                      type="text"
                      value={detailsForm.name}
                      onChange={(e) =>
                        setDetailsForm((f) => ({ ...f, name: e.target.value }))
                      }
                      className="w-full mt-1 rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                      placeholder="Store name"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Location *</label>
                    <input
                      type="text"
                      value={detailsForm.location}
                      onChange={(e) =>
                        setDetailsForm((f) => ({
                          ...f,
                          location: e.target.value,
                        }))
                      }
                      className="w-full mt-1 rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                      placeholder="City, Country"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium">Timezone</label>
                  <select
                    value={detailsForm.timezone}
                    onChange={(e) =>
                      setDetailsForm((f) => ({
                        ...f,
                        timezone: e.target.value,
                      }))
                    }
                    className="w-full mt-1 rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                  >
                    {TIMEZONES.map((tz) => (
                      <option key={tz} value={tz}>
                        {tz}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium">Opening Time</label>
                    <input
                      type="time"
                      value={detailsForm.opening_time}
                      onChange={(e) =>
                        setDetailsForm((f) => ({ ...f, opening_time: e.target.value }))
                      }
                      className="w-full mt-1 rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Closing Time</label>
                    <input
                      type="time"
                      value={detailsForm.closing_time}
                      onChange={(e) =>
                        setDetailsForm((f) => ({ ...f, closing_time: e.target.value }))
                      }
                      className="w-full mt-1 rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                </div>
                <Button
                  onClick={handleSaveDetails}
                  disabled={
                    saving ||
                    !detailsForm.name.trim() ||
                    !detailsForm.location.trim()
                  }
                >
                  {saving
                    ? "Saving..."
                    : selectedStoreId === "new"
                      ? "Create Store"
                      : "Save Details"}
                </Button>
              </CardContent>
            </Card>

            {/* Section 2: Departments (only for existing stores) */}
            {typeof selectedStoreId === "number" && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Departments</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {allDepts.map((dept) => {
                    const isAssigned = storeDeptIds.has(dept.id);
                    const isExpanded = expandedDeptId === dept.id;
                    const editForm = deptEditForms[dept.id];

                    return (
                      <div
                        key={dept.id}
                        className="border rounded-md overflow-hidden"
                      >
                        <div className="flex items-center gap-3 px-3 py-2">
                          {/* Assignment checkbox */}
                          <button
                            type="button"
                            onClick={() => handleToggleDept(dept.id, isAssigned)}
                            className={`w-5 h-5 rounded border flex items-center justify-center shrink-0 transition-colors ${
                              isAssigned
                                ? "bg-primary border-primary text-primary-foreground"
                                : "border-input hover:border-primary"
                            }`}
                          >
                            {isAssigned && <Check size={14} />}
                          </button>

                          {/* Dept info */}
                          <div className="flex-1 min-w-0">
                            <span className="text-sm font-medium">
                              {dept.name}
                            </span>
                            <span className="text-xs text-muted-foreground ml-2">
                              ({dept.code})
                            </span>
                            {!dept.active && (
                              <Badge variant="destructive" className="ml-2">
                                Inactive
                              </Badge>
                            )}
                          </div>

                          {/* Expand toggle */}
                          <button
                            type="button"
                            onClick={() => handleExpandDept(dept.id)}
                            className="p-1 rounded hover:bg-accent text-muted-foreground"
                          >
                            {isExpanded ? (
                              <ChevronDown size={16} />
                            ) : (
                              <ChevronRight size={16} />
                            )}
                          </button>
                        </div>

                        {/* Expanded edit form */}
                        {isExpanded && editForm && (
                          <div className="px-3 pb-3 pt-1 border-t bg-muted/30 space-y-3">
                            <div className="grid grid-cols-2 gap-3">
                              <div>
                                <label className="text-xs font-medium">
                                  Name
                                </label>
                                <input
                                  type="text"
                                  value={editForm.name}
                                  onChange={(e) =>
                                    setDeptEditForms((prev) => ({
                                      ...prev,
                                      [dept.id]: {
                                        ...prev[dept.id],
                                        name: e.target.value,
                                      },
                                    }))
                                  }
                                  className="w-full mt-1 rounded-md border bg-background px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring"
                                />
                              </div>
                              <div>
                                <label className="text-xs font-medium">
                                  Code
                                </label>
                                <input
                                  type="text"
                                  value={editForm.code}
                                  onChange={(e) =>
                                    setDeptEditForms((prev) => ({
                                      ...prev,
                                      [dept.id]: {
                                        ...prev[dept.id],
                                        code: e.target.value,
                                      },
                                    }))
                                  }
                                  className="w-full mt-1 rounded-md border bg-background px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring"
                                />
                              </div>
                            </div>
                            <label className="flex items-center gap-2 text-sm">
                              <input
                                type="checkbox"
                                checked={editForm.has_manager_role}
                                onChange={(e) =>
                                  setDeptEditForms((prev) => ({
                                    ...prev,
                                    [dept.id]: {
                                      ...prev[dept.id],
                                      has_manager_role: e.target.checked,
                                    },
                                  }))
                                }
                                className="rounded border"
                              />
                              Has manager role
                            </label>
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                onClick={() => handleSaveDept(dept.id)}
                                disabled={saving}
                              >
                                Save
                              </Button>
                              {dept.active && (
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => setConfirmDeactivateDeptId(dept.id)}
                                  disabled={saving}
                                >
                                  Deactivate
                                </Button>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {/* Create new department */}
                  <div className="border rounded-md overflow-hidden">
                    <button
                      type="button"
                      onClick={() => setShowCreateDept(!showCreateDept)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                    >
                      <Plus size={14} />
                      Create new department
                    </button>
                    {showCreateDept && (
                      <div className="px-3 pb-3 pt-1 border-t bg-muted/30 space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="text-xs font-medium">Name</label>
                            <input
                              type="text"
                              value={newDeptForm.name}
                              onChange={(e) =>
                                setNewDeptForm((f) => ({
                                  ...f,
                                  name: e.target.value,
                                }))
                              }
                              className="w-full mt-1 rounded-md border bg-background px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring"
                              placeholder="Department name"
                            />
                          </div>
                          <div>
                            <label className="text-xs font-medium">Code</label>
                            <input
                              type="text"
                              value={newDeptForm.code}
                              onChange={(e) =>
                                setNewDeptForm((f) => ({
                                  ...f,
                                  code: e.target.value,
                                }))
                              }
                              className="w-full mt-1 rounded-md border bg-background px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring"
                              placeholder="DEPT_CODE"
                            />
                          </div>
                        </div>
                        <label className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={newDeptForm.has_manager_role}
                            onChange={(e) =>
                              setNewDeptForm((f) => ({
                                ...f,
                                has_manager_role: e.target.checked,
                              }))
                            }
                            className="rounded border"
                          />
                          Has manager role
                        </label>
                        <Button
                          size="sm"
                          onClick={handleCreateDept}
                          disabled={
                            saving ||
                            !newDeptForm.name.trim() ||
                            !newDeptForm.code.trim()
                          }
                        >
                          {saving ? "Creating..." : "Create & Assign"}
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

          </>
        )}
      </div>

      {/* ── Alert Dialogs ── */}

      {/* Remove department from store */}
      <AlertDialog
        open={confirmRemoveDept !== null}
        onOpenChange={(open) => !open && setConfirmRemoveDept(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Department</AlertDialogTitle>
            <AlertDialogDescription>
              This will deactivate coverage rules for this department. Some
              employees may lose their primary department assignment.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmRemoveDept}>
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Pre-confirm: Deactivate department */}
      <AlertDialog
        open={confirmDeactivateDeptId !== null}
        onOpenChange={(open) => !open && setConfirmDeactivateDeptId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Deactivate Department</AlertDialogTitle>
            <AlertDialogDescription>
              This will deactivate this department globally across all stores. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={handleConfirmDeactivate}
            >
              Deactivate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Post-result: warnings after deactivation */}
      <AlertDialog
        open={deactivateWarnings !== null}
        onOpenChange={(open) => !open && setDeactivateWarnings(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Department Deactivated</AlertDialogTitle>
            <AlertDialogDescription>
              The following employees have no primary department assigned and need attention:
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="max-h-48 overflow-y-auto space-y-1 py-2">
            {deactivateWarnings?.map(w => (
              <div key={w.employee_id} className="text-sm px-1">{w.name} (#{w.employee_id})</div>
            ))}
          </div>
          <AlertDialogFooter>
            <AlertDialogAction onClick={() => setDeactivateWarnings(null)}>OK</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Post-result: warnings after removing department from store */}
      <AlertDialog open={removeWarnings !== null} onOpenChange={(open) => !open && setRemoveWarnings(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Department Removed</AlertDialogTitle>
            <AlertDialogDescription>
              The following employees have no primary department assigned and need attention:
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="max-h-48 overflow-y-auto space-y-1 py-2">
            {removeWarnings?.map(w => (
              <div key={w.employee_id} className="text-sm px-1">{w.name} (#{w.employee_id})</div>
            ))}
          </div>
          <AlertDialogFooter>
            <AlertDialogAction onClick={() => setRemoveWarnings(null)}>OK</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
