import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <p style={{ padding: "2rem", textAlign: "center" }}>Loading...</p>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
