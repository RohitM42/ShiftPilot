import { useState, useEffect, useCallback, useMemo } from "react";
import { UserPlus, Pencil, Search, X, Eye, EyeOff, Check, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { usersApi, userRolesApi, storesApi } from "@/services/api";
import { PageLoader } from "@/components/PageLoader";
import type { UserResponse, UserRoleResponse, StoreResponse } from "@/types";
import { Role } from "@/types";

// ── Helpers ───────────────────────────────────────────────────────────

const ROLE_VARIANT: Record<Role, "default" | "secondary" | "outline"> = {
  [Role.ADMIN]: "default",
  [Role.MANAGER]: "secondary",
  [Role.EMPLOYEE]: "outline",
};

function capitalizeName(s: string): string {
  if (!s) return s;
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

function generateEmail(firstname: string, surname: string): string {
  const clean = (s: string) => s.trim().toLowerCase().replace(/[^a-z0-9]/g, "");
  const f = clean(firstname);
  const s = clean(surname);
  if (!f && !s) return "";
  return `${f}.${s}@shiftpilot.work`;
}

interface PwReq {
  label: string;
  met: (pw: string, confirm: string) => boolean;
}

const PW_REQUIREMENTS: PwReq[] = [
  { label: "At least 8 characters", met: (pw) => pw.length >= 8 },
  { label: "Contains a number", met: (pw) => /\d/.test(pw) },
  { label: "Contains a letter", met: (pw) => /[a-zA-Z]/.test(pw) },
  { label: "Passwords match", met: (pw, c) => pw.length > 0 && pw === c },
];

// ── Create Panel ──────────────────────────────────────────────────────

interface CreatePanelProps {
  onClose: () => void;
  onCreated: (user: UserResponse) => void;
}

function CreatePanel({ onClose, onCreated }: CreatePanelProps) {
  const [firstname, setFirstname] = useState("");
  const [surname, setSurname] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const email = generateEmail(firstname, surname);
  const allMet = PW_REQUIREMENTS.every((r) => r.met(password, confirm));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!allMet || !firstname || !surname) return;
    setSubmitting(true);
    setError("");
    try {
      const res = await usersApi.create({ email, firstname, surname, password });
      onCreated(res.data as UserResponse);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to create user");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="p-5 space-y-4 sticky top-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold">Create User</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Creates a login account. Assign roles and an employee record afterwards.
          </p>
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground shrink-0">
          <X size={18} />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4" autoComplete="off">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground">First name</label>
            <input
              value={firstname}
              onChange={(e) => setFirstname(capitalizeName(e.target.value))}
              required
              autoComplete="off"
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Surname</label>
            <input
              value={surname}
              onChange={(e) => setSurname(capitalizeName(e.target.value))}
              required
              autoComplete="off"
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground">
            Email <span className="font-normal">(auto-generated)</span>
          </label>
          <div className="mt-1 w-full rounded-md border bg-muted px-3 py-2 text-sm text-muted-foreground select-none">
            {email || <span className="italic">Enter a name above…</span>}
          </div>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground">Temporary password</label>
          <div className="relative mt-1">
            <input
              type={showPw ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="new-password"
              className="w-full rounded-md border bg-background px-3 py-2 pr-10 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
            <button
              type="button"
              onClick={() => setShowPw((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground">Confirm password</label>
          <div className="relative mt-1">
            <input
              type={showConfirm ? "text" : "password"}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              autoComplete="new-password"
              className="w-full rounded-md border bg-background px-3 py-2 pr-10 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
            <button
              type="button"
              onClick={() => setShowConfirm((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>

        {(password.length > 0 || confirm.length > 0) && (
          <ul className="space-y-1">
            {PW_REQUIREMENTS.map((r) => {
              const met = r.met(password, confirm);
              return (
                <li
                  key={r.label}
                  className={`flex items-center gap-2 text-xs ${met ? "text-green-600" : "text-muted-foreground"}`}
                >
                  {met ? <Check size={12} /> : <X size={12} />}
                  {r.label}
                </li>
              );
            })}
          </ul>
        )}

        {error && <p className="text-sm text-destructive">{error}</p>}

        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={submitting || !allMet || !firstname || !surname}>
            {submitting ? "Creating…" : "Create User"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

// ── Edit Panel ────────────────────────────────────────────────────────

interface EditPanelProps {
  user: UserResponse;
  stores: StoreResponse[];
  onClose: () => void;
  onUpdated: (user: UserResponse) => void;
}

function EditPanel({ user, stores, onClose, onUpdated }: EditPanelProps) {
  const [roles, setRoles] = useState<UserRoleResponse[]>([]);
  const [rolesLoading, setRolesLoading] = useState(true);

  // Password state
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [pwSaving, setPwSaving] = useState(false);
  const [pwSuccess, setPwSuccess] = useState(false);
  const [pwError, setPwError] = useState("");

  // Role state
  const [addRole, setAddRole] = useState<Role>(Role.EMPLOYEE);
  const [addStoreId, setAddStoreId] = useState<string>("global");
  const [roleAdding, setRoleAdding] = useState(false);
  const [roleError, setRoleError] = useState("");

  const allPwMet = PW_REQUIREMENTS.every((r) => r.met(newPassword, confirmPassword));

  const loadRoles = useCallback(async () => {
    const res = await userRolesApi.getForUser(user.id);
    setRoles(res.data);
  }, [user.id]);

  useEffect(() => {
    setRolesLoading(true);
    loadRoles().finally(() => setRolesLoading(false));
  }, [loadRoles]);

  const handlePasswordReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!allPwMet) return;
    setPwSaving(true);
    setPwError("");
    setPwSuccess(false);
    try {
      await usersApi.resetPassword(user.id, newPassword);
      setPwSuccess(true);
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setPwError(msg ?? "Failed to reset password");
    } finally {
      setPwSaving(false);
    }
  };

  const handleAddRole = async () => {
    setRoleAdding(true);
    setRoleError("");
    try {
      const store_id = addStoreId === "global" ? null : Number(addStoreId);
      await userRolesApi.add({ user_id: user.id, role: addRole, store_id });
      await loadRoles();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setRoleError(msg ?? "Failed to add role");
    } finally {
      setRoleAdding(false);
    }
  };

  const handleRemoveRole = async (roleId: number) => {
    try {
      await userRolesApi.remove(roleId);
      setRoles((prev) => prev.filter((r) => r.id !== roleId));
    } catch {
      setRoleError("Failed to remove role");
    }
  };

  const toggleActive = async () => {
    if (user.is_active) {
      if (!window.confirm(`Disable ${user.firstname} ${user.surname}? They will no longer be able to log in.`)) return;
    }
    try {
      const res = await usersApi.update(user.id, { is_active: !user.is_active });
      onUpdated(res.data as UserResponse);
    } catch {
      // silent
    }
  };

  const storeName = (storeId: number | null) => {
    if (storeId === null) return "Global";
    return stores.find((s) => s.id === storeId)?.name ?? `Store ${storeId}`;
  };

  return (
    <div className="space-y-4 sticky top-4">
      {/* User header */}
      <Card className="p-5">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h2 className="text-base font-semibold truncate">
              {user.firstname} {user.surname}
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5 truncate">{user.email}</p>
            {!user.is_active && (
              <Badge variant="destructive" className="mt-2">
                Disabled
              </Badge>
            )}
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground shrink-0">
            <X size={18} />
          </button>
        </div>
        <div className="mt-3 pt-3 border-t">
          <Button
            variant="ghost"
            size="sm"
            className={user.is_active ? "text-muted-foreground" : "text-primary"}
            onClick={toggleActive}
          >
            {user.is_active ? "Disable account" : "Enable account"}
          </Button>
        </div>
      </Card>

      {/* Reset Password */}
      <Card className="p-5 space-y-4">
        <h2 className="text-sm font-semibold">Reset Password</h2>
        <form onSubmit={handlePasswordReset} className="space-y-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground">New password</label>
            <div className="relative mt-1">
              <input
                type={showNew ? "text" : "password"}
                value={newPassword}
                onChange={(e) => {
                  setNewPassword(e.target.value);
                  setPwSuccess(false);
                }}
                autoComplete="new-password"
                className="w-full rounded-md border bg-background px-3 py-2 pr-10 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
              <button
                type="button"
                onClick={() => setShowNew((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showNew ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground">Confirm password</label>
            <div className="relative mt-1">
              <input
                type={showConfirm ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value);
                  setPwSuccess(false);
                }}
                autoComplete="new-password"
                className="w-full rounded-md border bg-background px-3 py-2 pr-10 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
              <button
                type="button"
                onClick={() => setShowConfirm((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {(newPassword.length > 0 || confirmPassword.length > 0) && (
            <ul className="space-y-1">
              {PW_REQUIREMENTS.map((r) => {
                const met = r.met(newPassword, confirmPassword);
                return (
                  <li
                    key={r.label}
                    className={`flex items-center gap-2 text-xs ${met ? "text-green-600" : "text-muted-foreground"}`}
                  >
                    {met ? <Check size={12} /> : <X size={12} />}
                    {r.label}
                  </li>
                );
              })}
            </ul>
          )}

          {pwError && <p className="text-sm text-destructive">{pwError}</p>}
          {pwSuccess && <p className="text-sm text-green-600">Password updated.</p>}

          <div className="flex justify-end">
            <Button type="submit" size="sm" disabled={pwSaving || !allPwMet}>
              {pwSaving ? "Saving…" : "Reset Password"}
            </Button>
          </div>
        </form>
      </Card>

      {/* Roles */}
      <Card className="p-5 space-y-4">
        <h2 className="text-sm font-semibold">Roles</h2>

        {rolesLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : (
          <div className="space-y-2">
            {roles.length === 0 ? (
              <p className="text-sm text-muted-foreground">No roles assigned</p>
            ) : (
              roles.map((r) => (
                <div
                  key={r.id}
                  className="flex items-center justify-between rounded-md border px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <Badge variant={ROLE_VARIANT[r.role]}>{r.role}</Badge>
                    <span className="text-sm text-muted-foreground">{storeName(r.store_id)}</span>
                  </div>
                  <button
                    onClick={() => handleRemoveRole(r.id)}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <X size={14} />
                  </button>
                </div>
              ))
            )}
          </div>
        )}

        <div className="border-t pt-4 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Add Role
          </p>
          <div className="flex gap-2">
            <select
              value={addRole}
              onChange={(e) => setAddRole(e.target.value as Role)}
              className="flex-1 rounded-md border bg-background px-2 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            >
              {Object.values(Role).map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <select
              value={addStoreId}
              onChange={(e) => setAddStoreId(e.target.value)}
              className="flex-1 rounded-md border bg-background px-2 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="global">Global</option>
              {stores.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
            <Button size="sm" onClick={handleAddRole} disabled={roleAdding}>
              <Plus size={14} />
            </Button>
          </div>
          {roleError && <p className="text-sm text-destructive">{roleError}</p>}
          <p className="text-xs text-muted-foreground">
            Use <strong>Global</strong> scope only for the ADMIN role.
          </p>
        </div>
      </Card>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────

export default function UserManagement() {
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [stores, setStores] = useState<StoreResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [storeFilter, setStoreFilter] = useState<number | "all" | "unassigned">("all");
  const [panelMode, setPanelMode] = useState<"create" | "edit" | null>(null);
  const [activeUserId, setActiveUserId] = useState<number | null>(null);

  useEffect(() => {
    const loadStores = async () => {
      const res = await storesApi.list();
      setStores(res.data);
    };
    loadStores();
  }, []);

  useEffect(() => {
    const loadUsers = async () => {
      setLoading(true);
      try {
        const res = await usersApi.list(storeFilter !== "all" ? storeFilter : undefined);
        setUsers(res.data);
      } finally {
        setLoading(false);
      }
    };
    loadUsers();
  }, [storeFilter]);

  const activeUser = useMemo(
    () => users.find((u) => u.id === activeUserId) ?? null,
    [users, activeUserId]
  );

  const filtered = useMemo(() => {
    let list = users;
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (u) =>
          u.firstname.toLowerCase().includes(q) ||
          u.surname.toLowerCase().includes(q) ||
          u.email.toLowerCase().includes(q)
      );
    }
    if (activeUserId) {
      list = [...list].sort((a, b) => {
        if (a.id === activeUserId) return -1;
        if (b.id === activeUserId) return 1;
        return 0;
      });
    }
    return list;
  }, [users, search, activeUserId]);

  const openCreate = () => {
    setActiveUserId(null);
    setPanelMode("create");
  };

  const openEdit = (userId: number) => {
    if (panelMode === "edit" && activeUserId === userId) {
      closePanel();
      return;
    }
    setActiveUserId(userId);
    setPanelMode("edit");
  };

  const closePanel = () => {
    setPanelMode(null);
    setActiveUserId(null);
  };

  const toggleActive = async (user: UserResponse) => {
    if (user.is_active) {
      if (!window.confirm(`Disable ${user.firstname} ${user.surname}? They will no longer be able to log in.`)) return;
    }
    try {
      const res = await usersApi.update(user.id, { is_active: !user.is_active });
      setUsers((prev) => prev.map((u) => (u.id === user.id ? (res.data as UserResponse) : u)));
    } catch {
      // silent
    }
  };

  const isOpen = panelMode !== null;

  if (loading) return <PageLoader />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">User Management</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {users.length} user{users.length !== 1 ? "s" : ""}
          </p>
        </div>
        <Button onClick={openCreate} className="gap-2">
          <UserPlus size={16} />
          Create User
        </Button>
      </div>

      <div className="flex gap-4 items-start">
        {/* List column */}
        <div className={`${isOpen ? "flex-[0_0_55%]" : "w-full"} min-w-0 space-y-3`}>
          <div className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-[200px] max-w-sm">
              <Search
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <input
                type="text"
                placeholder="Search name or email…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-md border bg-background px-9 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            {stores.length > 0 && (
              <select
                value={storeFilter}
                onChange={(e) => {
                  const v = e.target.value;
                  setStoreFilter(v === "all" || v === "unassigned" ? v : Number(v));
                }}
                className="rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="all">All stores</option>
                <option value="unassigned">Unassigned</option>
                {stores.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            )}
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
              Loading users…
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
              No users found
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map((user) => (
                <Card
                  key={user.id}
                  className={`flex items-center justify-between px-4 py-3 transition-all ${
                    user.id === activeUserId && panelMode === "edit"
                      ? "ring-2 ring-primary"
                      : ""
                  }`}
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-10 h-10 rounded-full bg-primary/15 flex items-center justify-center shrink-0">
                      <span className="text-sm font-semibold text-primary">
                        {user.firstname[0]}
                        {user.surname[0]}
                      </span>
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold">
                          {user.firstname} {user.surname}
                        </span>
                        {!user.is_active && (
                          <Badge variant="destructive">Disabled</Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5 truncate">
                        {user.email}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant={
                        user.id === activeUserId && panelMode === "edit"
                          ? "secondary"
                          : "ghost"
                      }
                      size="sm"
                      className="gap-1.5"
                      onClick={() => openEdit(user.id)}
                    >
                      <Pencil size={14} />
                      <span className="hidden sm:inline">Edit</span>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className={user.is_active ? "text-muted-foreground" : "text-primary"}
                      onClick={() => toggleActive(user)}
                    >
                      {user.is_active ? "Disable" : "Enable"}
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Panel column */}
        {isOpen && (
          <div className="flex-1 min-w-0">
            {panelMode === "create" ? (
              <CreatePanel
                onClose={closePanel}
                onCreated={(user) => {
                  setUsers((prev) => [...prev, user]);
                  closePanel();
                }}
              />
            ) : activeUser ? (
              <EditPanel
                key={activeUser.id}
                user={activeUser}
                stores={stores}
                onClose={closePanel}
                onUpdated={(updated) =>
                  setUsers((prev) =>
                    prev.map((u) => (u.id === updated.id ? updated : u))
                  )
                }
              />
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
