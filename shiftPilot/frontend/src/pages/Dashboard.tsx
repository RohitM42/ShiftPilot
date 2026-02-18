import { useAuth } from "@/contexts/AuthContext";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Calendar, Clock, ClipboardCheck, Users } from "lucide-react";
import { Link } from "react-router-dom";

export default function Dashboard() {
  const { user, highestRole, isManagerOrAdmin, employee } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">
          Welcome back, {user?.firstname}
        </h1>
        <p className="text-muted-foreground">
          Here's your overview for today
        </p>
      </div>

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

        {isManagerOrAdmin && (
          <>
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
          </>
        )}
      </div>
    </div>
  );
}
