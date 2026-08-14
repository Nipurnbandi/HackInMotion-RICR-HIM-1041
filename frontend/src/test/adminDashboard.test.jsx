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
    updateStatus: vi.fn(),
    getAnalytics: vi.fn(),
    getMapIssues: vi.fn(),
  },
}));

vi.mock("../shared/components/CityMap", () => ({
  default: ({ issues, colorMode }) => (
    <div data-testid="city-map" data-color-mode={colorMode}>
      {issues.length} markers
    </div>
  ),
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
      sent_at: "2026-08-12T09:05:00Z",
      created_at: "2026-08-12T09:00:00Z",
      department_name: "Roads Department",
      department_email: "roads@city.gov",
    },
    {
      id: 12,
      message: "A new problem has been assigned to Sanitation Department.\nCase: CASE-000005",
      is_read: true,
      sent_at: null,
      created_at: "2026-08-12T10:00:00Z",
      department_name: "Sanitation Department",
      department_email: "sanitation@city.gov",
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

const MAP_ISSUES = [
  {
    id: 1,
    tracking_id: "SMC-2026-000001",
    category: "POTHOLE",
    status: "SUBMITTED",
    latitude: 23.2599,
    longitude: 77.4126,
    address: "Main Road, Bhopal",
    created_at: "2026-08-09T09:00:00Z",
    report_count: 3,
    citizen_count: 3,
    department_name: "Roads Department",
  },
  {
    id: 5,
    tracking_id: "SMC-2026-000005",
    category: "GARBAGE_OVERFLOW",
    status: "RESOLVED",
    latitude: 23.26,
    longitude: 77.41,
    address: "Market Street",
    created_at: "2026-08-12T09:00:00Z",
    report_count: 1,
    citizen_count: 1,
    department_name: "Sanitation Department",
  },
];

const ANALYTICS = {
  total_issues: 2,
  open_issues: 1,
  closed_issues: 1,
  total_citizens: 4,
  total_reports: 5,
  avg_resolution_days: 2.5,
  by_category: [
    { category: "POTHOLE", label: "Pothole", count: 2 },
    { category: "GARBAGE_OVERFLOW", label: "Overflowing Garbage", count: 1 },
    { category: "WATER_LEAKAGE", label: "Water Leakage", count: 0 },
  ],
  by_status: [
    { status: "SUBMITTED", count: 1 },
    { status: "UNDER_REVIEW", count: 0 },
    { status: "IN_PROGRESS", count: 0 },
    { status: "RESOLVED", count: 1 },
    { status: "REJECTED", count: 0 },
  ],
  departments: [
    {
      code: "ROADS",
      name: "Roads Department",
      total_cases: 2,
      open_cases: 1,
      resolved_cases: 1,
      avg_resolution_days: 2.5,
    },
    {
      code: "WATER",
      name: "Water & Drainage",
      total_cases: 0,
      open_cases: 0,
      resolved_cases: 0,
      avg_resolution_days: null,
    },
  ],
  hotspots: [
    {
      latitude: 23.26,
      longitude: 77.413,
      case_count: 2,
      report_count: 4,
      address: "Hotspot Junction, Bhopal",
      top_category: "POTHOLE",
      top_category_label: "Pothole",
    },
  ],
};

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
    adminService.getMapIssues.mockResolvedValue(MAP_ISSUES);
    adminService.getAnalytics.mockResolvedValue(ANALYTICS);
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

  it("shows who each email went to and its delivery state", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(
      await screen.findByRole("button", { name: /1 unread notifications/i })
    );

    expect(
      await screen.findByText(/To Roads Department <roads@city.gov>/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Email delivered/i)).toBeInTheDocument();
    expect(
      screen.getByText(/To Sanitation Department <sanitation@city.gov>/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Email pending — will retry/i)).toBeInTheDocument();
  });

  it("lets the admin change a case's status", async () => {
    adminService.updateStatus.mockResolvedValue({});
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Pothole");

    const select = screen.getByLabelText(/Update status for Pothole/i);
    expect(select).toHaveValue("SUBMITTED");

    await user.selectOptions(select, "IN_PROGRESS");

    await waitFor(() => {
      expect(adminService.updateStatus).toHaveBeenCalledWith(1, "IN_PROGRESS");
    });
    expect(adminService.listCases.mock.calls.length).toBeGreaterThan(1);
  });

  it("does not fetch map or analytics data until those views open", async () => {
    renderPage();
    await screen.findByText("Pothole");

    expect(adminService.getMapIssues).not.toHaveBeenCalled();
    expect(adminService.getAnalytics).not.toHaveBeenCalled();
  });

  it("opens the live city map view with markers from the API", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Pothole");

    await user.click(screen.getByRole("button", { name: /Live City Map/i }));

    const map = await screen.findByTestId("city-map");
    expect(map).toHaveTextContent("2 markers");
    expect(map).toHaveAttribute("data-color-mode", "status");
    expect(adminService.getMapIssues).toHaveBeenCalledTimes(1);
  });

  it("opens the analytics view with metrics computed from real data", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Pothole");

    await user.click(screen.getByRole("button", { name: /Analytics/i }));

    expect(await screen.findByText("Cases by status")).toBeInTheDocument();
    expect(adminService.getAnalytics).toHaveBeenCalledTimes(1);

    const avgCard = screen.getByText("Avg. time to resolve").closest("li");
    expect(avgCard).toHaveTextContent("2.5 days");

    expect(screen.getByText("Cases by category")).toBeInTheDocument();
    expect(screen.getByText("Department performance")).toBeInTheDocument();
    expect(
      screen.getByRole("rowheader", { name: "Roads Department" })
    ).toBeInTheDocument();

    expect(screen.getByText("Hotspot Junction, Bhopal")).toBeInTheDocument();
    expect(screen.getByText(/Mostly Pothole · 2 problems/i)).toBeInTheDocument();
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
