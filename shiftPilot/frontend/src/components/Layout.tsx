import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import {
  LayoutDashboard,
  Calendar,
  CalendarRange,
  Clock,
  Settings,
  ClipboardCheck,
  Users,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-primary/10 text-primary"
      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
  );

export function Layout() {
  const { user, logout, isManagerOrAdmin, highestRole } = useAuth();

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="flex w-60 flex-col border-r bg-card">
        {/* Logo */}
        <div className="flex h-14 items-center border-b px-4">
          <span className="text-lg font-bold text-primary">ShiftPilot</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-1 p-3">
          <NavLink to="/" end className={navLinkClass}>
            <LayoutDashboard size={18} />
            Dashboard
          </NavLink>

          <NavLink to="/my-shifts" className={navLinkClass}>
            <Calendar size={18} />
            My Shifts
          </NavLink>

          <NavLink to="/my-availability" className={navLinkClass}>
            <Clock size={18} />
            My Availability
          </NavLink>

          {isManagerOrAdmin && (
            <>
              <div className="pt-4 pb-1 px-3 text-xs font-semibold uppercase text-muted-foreground tracking-wider">
                Management
              </div>

              <NavLink to="/schedule" className={navLinkClass}>
                <CalendarRange size={18} />
                Schedule
              </NavLink>

              <NavLink to="/scheduling-rules" className={navLinkClass}>
                <Settings size={18} />
                Scheduling Rules
              </NavLink>

              <NavLink to="/proposals" className={navLinkClass}>
                <ClipboardCheck size={18} />
                Proposals
              </NavLink>

              <NavLink to="/employees" className={navLinkClass}>
                <Users size={18} />
                Employees
              </NavLink>
            </>
          )}
        </nav>

        {/* User info + logout */}
        <div className="border-t p-3">
          <div className="mb-2 px-3">
            <p className="text-sm font-medium truncate">
              {user?.firstname} {user?.surname}
            </p>
            <p className="text-xs text-muted-foreground capitalize">
              {highestRole.toLowerCase()}
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-3 text-muted-foreground"
            onClick={logout}
          >
            <LogOut size={18} />
            Sign out
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="mx-auto max-w-6xl p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
