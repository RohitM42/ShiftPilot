import { useAuth } from "@/contexts/AuthContext";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Calendar, Clock, ClipboardCheck, Users, CalendarDays, BookOpen, Store, UserCog } from "lucide-react";
import { Link } from "react-router-dom";

export default function Dashboard() {
  const { user, highestRole, isManagerOrAdmin, isAdmin, employee } = useAuth();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Welcome back, {user?.firstname}</h1>
        <p className="text-muted-foreground">Here's your overview for today</p>
      </div>

      {/* Personal section */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Personal</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Link to="/my-shifts">
            <Card className="transition-shadow hover:shadow-md cursor-pointer">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  My Shifts
                </CardTitle>
                <Calendar size={18} className="text-primary" />
              </CardHeader>
              <CardContent>
                <p className="text-lg font-semibold">View this week's schedule</p>
              </CardContent>
            </Card>
          </Link>

          <Link to="/my-availability">
            <Card className="transition-shadow hover:shadow-md cursor-pointer">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  My Availability
                </CardTitle>
                <Clock size={18} className="text-primary" />
              </CardHeader>
              <CardContent>
                <p className="text-lg font-semibold">
                  {employee?.contracted_weekly_hours ?? "—"}h contracted
                </p>
              </CardContent>
            </Card>
          </Link>
        </div>
      </div>

      {/* Management section */}
      {isManagerOrAdmin && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Management</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Link to="/schedule">
              <Card className="transition-shadow hover:shadow-md cursor-pointer">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Schedule
                  </CardTitle>
                  <CalendarDays size={18} className="text-primary" />
                </CardHeader>
                <CardContent>
                  <p className="text-lg font-semibold">Generate & publish shifts</p>
                </CardContent>
              </Card>
            </Link>

            <Link to="/scheduling-rules">
              <Card className="transition-shadow hover:shadow-md cursor-pointer">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Scheduling Rules
                  </CardTitle>
                  <BookOpen size={18} className="text-primary" />
                </CardHeader>
                <CardContent>
                  <p className="text-lg font-semibold">Manage coverage & roles</p>
                </CardContent>
              </Card>
            </Link>

            <Link to="/proposals">
              <Card className="transition-shadow hover:shadow-md cursor-pointer">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Proposals
                  </CardTitle>
                  <ClipboardCheck size={18} className="text-primary" />
                </CardHeader>
                <CardContent>
                  <p className="text-lg font-semibold">Review pending changes</p>
                </CardContent>
              </Card>
            </Link>

            <Link to="/employees">
              <Card className="transition-shadow hover:shadow-md cursor-pointer">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Employees
                  </CardTitle>
                  <Users size={18} className="text-primary" />
                </CardHeader>
                <CardContent>
                  <p className="text-lg font-semibold">Manage your team</p>
                </CardContent>
              </Card>
            </Link>
          </div>
        </div>
      )}

      {/* Admin section */}
      {isAdmin && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Admin</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Link to="/admin/users">
              <Card className="transition-shadow hover:shadow-md cursor-pointer">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    User Management
                  </CardTitle>
                  <UserCog size={18} className="text-primary" />
                </CardHeader>
                <CardContent>
                  <p className="text-lg font-semibold">Create and manage users</p>
                </CardContent>
              </Card>
            </Link>

            <Link to="/admin/stores">
              <Card className="transition-shadow hover:shadow-md cursor-pointer">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Store Management
                  </CardTitle>
                  <Store size={18} className="text-primary" />
                </CardHeader>
                <CardContent>
                  <p className="text-lg font-semibold">Create and configure stores</p>
                </CardContent>
              </Card>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
