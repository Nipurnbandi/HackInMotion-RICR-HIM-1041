import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("leaflet/dist/leaflet.css", () => ({}));
vi.mock("leaflet/dist/images/marker-icon.png", () => ({ default: "marker.png" }));
vi.mock("leaflet/dist/images/marker-icon-2x.png", () => ({ default: "marker-2x.png" }));
vi.mock("leaflet/dist/images/marker-shadow.png", () => ({ default: "shadow.png" }));
vi.mock("leaflet", () => ({ default: { icon: () => ({}) } }));
vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }) => <div data-testid="map">{children}</div>,
  TileLayer: () => null,
  Marker: ({ position }) => (
    <div data-testid="marker" data-position={position?.join(",")} />
  ),
}));

vi.mock("../citizen/services/issueService", () => ({
  issueService: {
    listIssues: vi.fn(),
    getIssue: vi.fn(),
    getDashboard: vi.fn(),
    getStats: vi.fn(),
    createIssue: vi.fn(),
  },
}));

import CitizenDashboard from "../citizen/pages/CitizenDashboard";
import IssueDetails from "../citizen/pages/IssueDetails";
import MyReports from "../citizen/pages/MyReports";
import { issueService } from "../citizen/services/issueService";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    user: { id: 1, email: "citizen@example.com", role: "CITIZEN" },
    role: "CITIZEN",
    isAuthenticated: true,
    loading: false,
    logout: vi.fn(),
  }),
}));

const ISSUE = {
  id: 7,
  tracking_id: "SMC-2026-000007",
  category: "POTHOLE",
  description: "Large pothole near the main road.",
  latitude: 23.2599,
  longitude: 77.4126,
  address: "Example Street, Bhopal",
  photo_url: "/uploads/issues/abc.png",
  status: "IN_PROGRESS",
  created_at: "2026-08-12T09:30:00Z",
  updated_at: "2026-08-12T09:30:00Z",
};

function renderReports() {
  return render(
    <MemoryRouter initialEntries={["/citizen/issues"]}>
      <Routes>
        <Route path="/citizen/issues" element={<MyReports />} />
        <Route path="/citizen/issues/:issueId" element={<IssueDetails />} />
      </Routes>
    </MemoryRouter>
  );
}

function renderDetails(id = 7) {
  return render(
    <MemoryRouter initialEntries={[`/citizen/issues/${id}`]}>
      <Routes>
        <Route path="/citizen/issues/:issueId" element={<IssueDetails />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("MyReports", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows a loading state while fetching", () => {
    issueService.listIssues.mockReturnValue(new Promise(() => {}));
    renderReports();

    expect(screen.getByRole("status")).toHaveTextContent(/Loading your reports/i);
  });

  it("renders reports returned by the API", async () => {
    issueService.listIssues.mockResolvedValue({
      items: [ISSUE],
      total: 1,
      page: 1,
      page_size: 10,
    });

    renderReports();

    expect(await screen.findByText("Pothole")).toBeInTheDocument();
    expect(screen.getByText("SMC-2026-000007")).toBeInTheDocument();
    expect(screen.getByText("Example Street, Bhopal")).toBeInTheDocument();

    // "In Progress" is also a filter chip, so scope the badge check to the card.
    const card = screen.getByRole("link", { name: /Pothole/i });
    expect(within(card).getByText("In Progress")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Pothole/i })).toHaveAttribute(
      "href",
      "/citizen/issues/7"
    );
  });

  it("shows an empty state when the citizen has no reports", async () => {
    issueService.listIssues.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
    });

    renderReports();

    expect(await screen.findByText("No reports yet")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Report your first issue/i })
    ).toBeInTheDocument();
  });

  it("shows an error state with a retry action", async () => {
    issueService.listIssues.mockRejectedValue(new Error("Network is unavailable."));
    renderReports();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /Network is unavailable/i
    );

    issueService.listIssues.mockResolvedValue({
      items: [ISSUE],
      total: 1,
      page: 1,
      page_size: 10,
    });
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("Pothole")).toBeInTheDocument();
  });

  it("filters by status through the API", async () => {
    issueService.listIssues.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
    });

    renderReports();
    await screen.findByText("No reports yet");

    await userEvent.click(screen.getByRole("button", { name: "Resolved" }));

    await waitFor(() => {
      expect(issueService.listIssues).toHaveBeenLastCalledWith(
        expect.objectContaining({ status: "RESOLVED" })
      );
    });
  });

  it("searches through the API", async () => {
    issueService.listIssues.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
    });

    renderReports();
    await screen.findByText("No reports yet");

    await userEvent.type(screen.getByLabelText("Search reports"), "nehru");

    await waitFor(
      () => {
        expect(issueService.listIssues).toHaveBeenLastCalledWith(
          expect.objectContaining({ search: "nehru" })
        );
      },
      { timeout: 2000 }
    );
  });
});

describe("IssueDetails", () => {
  beforeEach(() => vi.clearAllMocks());

  it("loads a single report from the API", async () => {
    issueService.getIssue.mockResolvedValue(ISSUE);
    renderDetails();

    expect(await screen.findByText("SMC-2026-000007")).toBeInTheDocument();
    expect(issueService.getIssue).toHaveBeenCalledWith("7");
    expect(screen.getByText("Large pothole near the main road.")).toBeInTheDocument();
    expect(screen.getByText("23.259900, 77.412600")).toBeInTheDocument();
    expect(screen.getByTestId("marker")).toHaveAttribute(
      "data-position",
      "23.2599,77.4126"
    );
  });

  it("renders the photo evidence with meaningful alt text", async () => {
    issueService.getIssue.mockResolvedValue(ISSUE);
    renderDetails();

    const photo = await screen.findByRole("img", { name: /Photo evidence submitted/i });
    expect(photo).toHaveAttribute("src", "/uploads/issues/abc.png");
  });

  it("marks the current status on the timeline", async () => {
    issueService.getIssue.mockResolvedValue(ISSUE);
    renderDetails();

    const timeline = await screen.findByRole("list", { name: "Report progress" });
    const current = timeline.querySelector('[aria-current="step"]');
    expect(current).toHaveTextContent("In Progress");
  });

  it("shows a not-found state for someone else's report", async () => {
    const error = new Error("Issue not found");
    error.status = 404;
    issueService.getIssue.mockRejectedValue(error);

    renderDetails(999);

    expect(await screen.findByText("Report not found")).toBeInTheDocument();
    expect(screen.getByText(/isn't one of yours/i)).toBeInTheDocument();
  });
});

describe("CitizenDashboard", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows a loading state, then real statistics", async () => {
    issueService.getDashboard.mockResolvedValue({
      message: "Welcome",
      role: "CITIZEN",
      email: "citizen@example.com",
      issue_count: 3,
      stats: {
        total: 3,
        submitted: 1,
        under_review: 0,
        in_progress: 1,
        resolved: 1,
        rejected: 0,
      },
      recent_issues: [ISSUE],
    });

    render(
      <MemoryRouter>
        <CitizenDashboard />
      </MemoryRouter>
    );

    expect(screen.getByRole("status")).toHaveTextContent(/Loading your dashboard/i);

    expect(await screen.findByText("Good to know")).toBeInTheDocument();
    const stats = screen.getByText("Total reports").closest("li");
    expect(stats).toHaveTextContent("3");
    expect(screen.getByText("SMC-2026-000007")).toBeInTheDocument();
  });

  it("shows an empty state when nothing has been reported", async () => {
    issueService.getDashboard.mockResolvedValue({
      message: "Welcome",
      role: "CITIZEN",
      email: "citizen@example.com",
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
    });

    render(
      <MemoryRouter>
        <CitizenDashboard />
      </MemoryRouter>
    );

    expect(
      await screen.findByText("You haven't reported anything yet")
    ).toBeInTheDocument();
  });
});
