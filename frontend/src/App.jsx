import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import Login from "./auth/Login";
import Signup from "./auth/Signup";
import AdminDashboard from "./admin/pages/AdminDashboard";
import CitizenLayout from "./citizen/components/CitizenLayout";
import CitizenDashboard from "./citizen/pages/CitizenDashboard";
import Help from "./citizen/pages/Help";
import IssueDetails from "./citizen/pages/IssueDetails";
import MyReports from "./citizen/pages/MyReports";
import Profile from "./citizen/pages/Profile";
import ReportIssue from "./citizen/pages/ReportIssue";
import ProtectedRoute from "./routes/ProtectedRoute";
import RoleRoute from "./routes/RoleRoute";
import { getDashboardPath } from "./services/api";

function HomeRedirect() {
  const { isAuthenticated, role, loading } = useAuth();

  if (loading) {
    return <p style={{ padding: "2rem", textAlign: "center" }}>Loading...</p>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Navigate to={getDashboardPath(role)} replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          <Route element={<ProtectedRoute />}>
            <Route
              path="/citizen"
              element={
                <RoleRoute allowedRole="CITIZEN">
                  <CitizenLayout />
                </RoleRoute>
              }
            >
              <Route index element={<CitizenDashboard />} />
              <Route path="report" element={<ReportIssue />} />
              <Route path="issues" element={<MyReports />} />
              <Route path="issues/:issueId" element={<IssueDetails />} />
              <Route path="profile" element={<Profile />} />
              <Route path="help" element={<Help />} />
            </Route>

            <Route
              path="/admin"
              element={
                <RoleRoute allowedRole="ADMIN">
                  <AdminDashboard />
                </RoleRoute>
              }
            />
          </Route>

          <Route path="/" element={<HomeRedirect />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
