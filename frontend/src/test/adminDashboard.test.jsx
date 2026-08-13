import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("../admin/services/adminService", () => ({
  adminService: {
    getDashboard: vi.fn(),
    getDepartments: vi.fn(),
    listCases: vi.fn(),
    getNotifications: vi.fn(),
    markNotificationRead: vi.fn(),
  },
}));

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    user: { id: 9, email: "admin@example.com", role: "ADMIN" },
    role: "ADMIN",
    isAuthenticated: true,
    loading: false,
    logout: vi.fn(),
  }),
}));

import AdminDashboard from "../admin/pages/AdminDashboard";
import { adminService } from "../admin/services/adminService";

const SUMMARY = { message: "Welcome", role: "ADMIN", total_issues: 2, total_citizens: 4 };

const DEPARTMENTS = [
  { code: "ROADS", name: "Roads Department", email: "roads@city.gov", open_cases: 1 },
  { code: "SANITATION", name: "Sanitation Department", email: "sanitation@city.gov", open_cases: 1 },
];

const NOTIFICATIONS = {
  unread: 1,
  items: [
    {
      id: 11,
      message: "A new problem has been assigned to Roads Department.\nCase: CASE-000001",
      is_read: false,
      sent_at: null,
      created_at: "2026-08-12T09:00:00Z",
    },
  ],
};

const CASES = [
  {
    id: 1,
    tracking_id: "SMC-2026-000001",
    title: "Pothole",
    citizen_id: 2,
    category: "POTHOLE",
    description: "Deep pothole near the junction.",
    latitude: 23.2599,
    longitude: 77.4126,
    address: "Main Road, Bhopal",
    photo_url: null,
    status: "SUBMITTED",
    created_at: "2026-08-09T09:00:00Z",
    updated_at: "2026-08-09T09:00:00Z",
    citizen_count: 3,
    days_open: 3,
    priority_score: 17.1,
    department_code: "ROADS",
    department_name: "Roads Department",
  },
  {
    id: 5,
    tracking_id: "SMC-2026-000005",
    title: "Overflowing Garbage",
    citizen_id: 3,
    category: "GARBAGE_OVERFLOW",
    description: "Bin overflowing at the corner.",
    latitude: 23.26,
    longitude: 77.41,
    address: "Market Street",
    photo_url: null,
    status: "UNDER_REVIEW",
    created_at: "2026-08-12T09:00:00Z",
    updated_at: "2026-08-12T09:00:00Z",
    citizen_count: 1,
    days_open: 0,
    priority_score: 2.0,
    department_code: "SANITATION",
    department_name: "Sanitation Department",
  },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminDashboard />
    </MemoryRouter>
  );
}

describe("AdminDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    adminService.getDashboard.mockResolvedValue(SUMMARY);
    adminService.getDepartments.mockResolvedValue(DEPARTMENTS);
    adminService.getNotifications.mockResolvedValue(NOTIFICATIONS);
    adminService.listCases.mockResolvedValue(CASES);
  });

  it("shows a loading state, then the priority-ordered work queue", async () => {
    renderPage();
    expect(screen.getByRole("status")).toHaveTextContent(/Loading the city overview/i);

    expect(await screen.findByText("Pothole")).toBeInTheDocument();

    const rows = screen.getAllByRole("listitem").filter((li) =>
      li.className.includes("issue-card")
    );
    expect(rows).toHaveLength(2);
    expect(within(rows[0]).getByText("Pothole")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Overflowing Garbage")).toBeInTheDocument();
  });

  it("shows citizen count, age and priority for each case", async () => {
    renderPage();

    expect(await screen.findByText("👥 3 citizens")).toBeInTheDocument();
    expect(screen.getByText("👥 1 citizen")).toBeInTheDocument();
    expect(screen.getByText("open 3 days")).toBeInTheDocument();
    expect(screen.getByText("reported today")).toBeInTheDocument();
    expect(screen.getByText("17.1")).toBeInTheDocument();
  });

  it("shows city-wide totals from the API", async () => {
    renderPage();

    const casesCard = (await screen.findByText("Open problems (cases)")).closest("li");
    expect(casesCard).toHaveTextContent("2");
    const reportsCard = screen.getByText("Reports received").closest("li");
    expect(reportsCard).toHaveTextContent("4");
  });

  it("shows an empty state when there are no cases", async () => {
    adminService.listCases.mockResolvedValue([]);
    renderPage();

    expect(await screen.findByText("No open problems")).toBeInTheDocument();
  });

  it("shows an error state with retry when the API fails", async () => {
    adminService.getDashboard.mockRejectedValue(new Error("Server unavailable."));
    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent(/Server unavailable/i);
  });

  it("shows department chips and each case's department badge", async () => {
    renderPage();

    expect(
      await screen.findByRole("button", { name: "Roads Department (1)" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Sanitation Department (1)" })
    ).toBeInTheDocument();

    const rows = screen.getAllByRole("listitem").filter((li) =>
      li.className.includes("issue-card")
    );
    expect(within(rows[0]).getByText("Roads Department")).toBeInTheDocument();
  });

  it("filters the queue by department through the API", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Pothole");

    await user.click(screen.getByRole("button", { name: "Roads Department (1)" }));

    await waitFor(() => {
      expect(adminService.listCases).toHaveBeenLastCalledWith("ROADS");
    });
  });

  it("shows the unread notification count and marks one as read", async () => {
    adminService.markNotificationRead.mockResolvedValue({});
    const user = userEvent.setup();
    renderPage();

    const bell = await screen.findByRole("button", {
      name: /1 unread notifications/i,
    });
    await user.click(bell);

    const item = await screen.findByRole("button", {
      name: /assigned to Roads Department/i,
    });
    expect(item).toHaveTextContent("unread");

    await user.click(item);

    await waitFor(() => {
      expect(adminService.markNotificationRead).toHaveBeenCalledWith(11);
    });
    expect(item).not.toHaveTextContent("unread");
  });
});
