import { describe, expect, it, vi, beforeEach } from "vitest";
import { MemoryRouter, Navigate, Route, Routes } from "react-router-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import { AuthProvider, useAuth } from "../auth/AuthContext";
import Login from "../auth/Login";
import Signup from "../auth/Signup";
import ProtectedRoute from "../routes/ProtectedRoute";
import RoleRoute from "../routes/RoleRoute";
import CitizenLayout from "../citizen/components/CitizenLayout";
import CitizenDashboard from "../citizen/pages/CitizenDashboard";
import AdminDashboard from "../admin/pages/AdminDashboard";
import { getDashboardPath } from "../services/api";
import * as apiModule from "../services/api";
import { citizenService } from "../citizen/services/citizenService";

vi.mock("../services/api", async () => {
  const actual = await vi.importActual("../services/api");
  return {
    ...actual,
    api: {
      signup: vi.fn(),
      login: vi.fn(),
      logout: vi.fn(),
      getMe: vi.fn(),
    },
  };
});

vi.mock("../citizen/services/citizenService", () => ({
  citizenService: {
    getDashboard: vi.fn(),
    getStats: vi.fn(),
    listIssues: vi.fn(),
    getIssue: vi.fn(),
    createIssue: vi.fn(),
  },
}));

const EMPTY_DASHBOARD = {
  message: "Welcome",
  role: "CITIZEN",
  email: "c@example.com",
  issue_count: 0,
  stats: {
    total: 0,
    submitted: 0,
    under_review: 0,
    in_progress: 0,
    resolved: 0,
    rejected: 0,
  },
  recent_issues: [],
};

function HomeRedirect() {
  const { isAuthenticated, role, loading } = useAuth();
  if (loading) return <p>Loading...</p>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Navigate to={getDashboardPath(role)} replace />;
}

function TestApp({ initialPath = "/" }) {
  return (
    <AuthProvider>
      <MemoryRouter initialEntries={[initialPath]}>
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
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("Frontend routing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiModule.api.getMe.mockRejectedValue(new Error("unauthenticated"));
    citizenService.getDashboard.mockResolvedValue(EMPTY_DASHBOARD);
  });

  it("redirects unauthenticated user from /citizen to /login", async () => {
    render(<TestApp initialPath="/citizen" />);
    expect(await screen.findByRole("heading", { name: "Login" })).toBeInTheDocument();
  });

  it("redirects unauthenticated user from /admin to /login", async () => {
    render(<TestApp initialPath="/admin" />);
    expect(await screen.findByRole("heading", { name: "Login" })).toBeInTheDocument();
  });

  it("redirects citizen login to /citizen", async () => {
    apiModule.api.login.mockResolvedValue({});
    apiModule.api.getMe
      .mockRejectedValueOnce(new Error("unauthenticated"))
      .mockResolvedValue({ id: 1, email: "c@example.com", role: "CITIZEN" });

    render(<TestApp initialPath="/login" />);
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "c@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("heading", { name: "Good to know" })).toBeInTheDocument();
  });

  it("redirects admin login to /admin", async () => {
    apiModule.api.login.mockResolvedValue({});
    apiModule.api.getMe
      .mockRejectedValueOnce(new Error("unauthenticated"))
      .mockResolvedValue({ id: 2, email: "a@example.com", role: "ADMIN" });

    render(<TestApp initialPath="/login" />);
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "a@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("heading", { name: "Admin Dashboard" })).toBeInTheDocument();
  });

  it("redirects citizen away from /admin", async () => {
    apiModule.api.getMe.mockResolvedValue({
      id: 1,
      email: "c@example.com",
      role: "CITIZEN",
    });

    render(<TestApp initialPath="/admin" />);
    expect(await screen.findByRole("heading", { name: "Good to know" })).toBeInTheDocument();
  });

  it("allows admin to access /admin", async () => {
    apiModule.api.getMe.mockResolvedValue({
      id: 2,
      email: "a@example.com",
      role: "ADMIN",
    });

    render(<TestApp initialPath="/admin" />);
    expect(await screen.findByRole("heading", { name: "Admin Dashboard" })).toBeInTheDocument();
  });
});
