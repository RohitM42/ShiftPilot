import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Layout } from "@/components/Layout";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import MyShifts from "@/pages/MyShifts";
import MyAvailability from "@/pages/MyAvailability";
import SchedulingRules from "@/pages/SchedulingRules";
import ProposalReview from "@/pages/ProposalReview";
import EmployeeManagement from "@/pages/EmployeeManagement";
import EmployeeEdit from "@/pages/EmployeeEdit";
import ScheduleView from "@/pages/ScheduleView";
import ScheduleSummaryView from "@/pages/ScheduleSummaryView";
import ProposalView from "@/pages/ProposalView";

function LoginGuard() {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return null;
  if (isAuthenticated) return <Navigate to="/" replace />;
  return <Login />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginGuard />} />

          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="my-shifts" element={<MyShifts />} />
            <Route path="my-availability" element={<MyAvailability />} />
            <Route
              path="schedule"
              element={
                <ProtectedRoute requireManagerOrAdmin>
                  <ScheduleView />
                </ProtectedRoute>
              }
            />
            <Route
              path="schedule/summary"
              element={
                <ProtectedRoute requireManagerOrAdmin>
                  <ScheduleSummaryView />
                </ProtectedRoute>
              }
            />
            <Route
              path="scheduling-rules"
              element={
                <ProtectedRoute requireManagerOrAdmin>
                  <SchedulingRules />
                </ProtectedRoute>
              }
            />
            <Route
              path="proposals"
              element={
                <ProtectedRoute requireManagerOrAdmin>
                  <ProposalReview />
                </ProtectedRoute>
              }
            />
            <Route
              path="proposals/:id"
              element={
                <ProtectedRoute requireManagerOrAdmin>
                  <ProposalView />
                </ProtectedRoute>
              }
            />
            <Route
              path="employees"
              element={
                <ProtectedRoute requireManagerOrAdmin>
                  <EmployeeManagement />
                </ProtectedRoute>
              }
            />
            <Route
              path="employees/:id/edit"
              element={
                <ProtectedRoute requireManagerOrAdmin>
                  <EmployeeEdit />
                </ProtectedRoute>
              }
            />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
