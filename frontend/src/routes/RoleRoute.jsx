import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { getDashboardPath } from "../services/api";

export default function RoleRoute({ allowedRole, children }) {
  const { role, loading } = useAuth();

  if (loading) {
    return <p style={{ padding: "2rem", textAlign: "center" }}>Loading...</p>;
  }

  if (role !== allowedRole) {
    return <Navigate to={getDashboardPath(role)} replace />;
  }

  return children;
}
