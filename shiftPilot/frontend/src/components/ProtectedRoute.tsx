import { Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Role } from "@/types";

interface Props {
  children: React.ReactNode;
  requiredRole?: Role;
  requireManagerOrAdmin?: boolean;
}

export function ProtectedRoute({
  children,
  requiredRole,
  requireManagerOrAdmin,
}: Props) {
  const { isAuthenticated, isLoading, highestRole, isManagerOrAdmin } =
    useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requireManagerOrAdmin && !isManagerOrAdmin) {
    return <Navigate to="/" replace />;
  }

  if (requiredRole === Role.ADMIN && highestRole !== Role.ADMIN) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
