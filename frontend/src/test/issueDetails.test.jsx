import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../citizen/services/citizenService", () => ({
  citizenService: {
    getIssue: vi.fn(),
    confirmIssue: vi.fn(),
    reopenIssue: vi.fn(),
  },
}));

vi.mock("../citizen/components/IssueLocationMap", () => ({
  default: () => <div data-testid="issue-map" />,
}));

import IssueDetails from "../citizen/pages/IssueDetails";
import { citizenService } from "../citizen/services/citizenService";

const HISTORY = [
  {
    id: 1,
    old_status: null,
    new_status: "SUBMITTED",
    note: "Report submitted.",
    photo_url: null,
    changed_by_role: "CITIZEN",
    created_at: "2026-08-09T09:00:00Z",
  },
  {
    id: 2,
    old_status: "SUBMITTED",
    new_status: "RESOLVED",
    note: "Filled and re-surfaced.",
    photo_url: null,
    changed_by_role: "ADMIN",
    created_at: "2026-08-12T10:00:00Z",
  },
];

const RESOLVED_ISSUE = {
  id: 7,
  tracking_id: "SMC-2026-000007",
  category: "POTHOLE",
  description: "Deep pothole near the junction.",
  latitude: 23.2599,
  longitude: 77.4126,
  address: "Main Road, Bhopal",
  photo_url: null,
  status: "RESOLVED",
  resolution_note: "Filled and re-surfaced.",
  resolution_photo_url: "/uploads/resolutions/proof.png",
  created_at: "2026-08-09T09:00:00Z",
  updated_at: "2026-08-12T10:00:00Z",
  history: HISTORY,
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/citizen/issues/7"]}>
      <Routes>
        <Route path="/citizen/issues/:issueId" element={<IssueDetails />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("IssueDetails lifecycle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    citizenService.getIssue.mockResolvedValue(RESOLVED_ISSUE);
  });

  it("shows the resolution note, proof photo and activity history", async () => {
    renderPage();

    expect(await screen.findByText("Resolution")).toBeInTheDocument();
    expect(screen.getAllByText("Filled and re-surfaced.").length).toBeGreaterThan(0);
    expect(
      screen.getByAltText(/Proof of resolution for report SMC-2026-000007/i)
    ).toBeInTheDocument();

    expect(screen.getByText("Activity history")).toBeInTheDocument();
    expect(screen.getByText("Report submitted")).toBeInTheDocument();
    expect(screen.getByText("Submitted → Resolved")).toBeInTheDocument();
  });

  it("lets the reporter confirm the fix", async () => {
    citizenService.confirmIssue.mockResolvedValue(RESOLVED_ISSUE);
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: "Yes, it's fixed" }));

    await waitFor(() => {
      expect(citizenService.confirmIssue).toHaveBeenCalledWith("7");
    });
    expect(await screen.findByText(/You confirmed this fix/i)).toBeInTheDocument();
  });

  it("lets the reporter reopen a report that isn't actually fixed", async () => {
    citizenService.reopenIssue.mockResolvedValue({
      ...RESOLVED_ISSUE,
      status: "UNDER_REVIEW",
      history: [
        ...HISTORY,
        {
          id: 3,
          old_status: "RESOLVED",
          new_status: "UNDER_REVIEW",
          note: "Reporter reopened the report — the problem is not fixed.",
          photo_url: null,
          changed_by_role: "CITIZEN",
          created_at: "2026-08-13T08:00:00Z",
        },
      ],
    });
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: "No, reopen it" }));

    await waitFor(() => {
      expect(citizenService.reopenIssue).toHaveBeenCalledWith("7");
    });
    expect(
      screen.queryByRole("button", { name: "Yes, it's fixed" })
    ).not.toBeInTheDocument();
    expect(screen.getByText(/reopened the report/i)).toBeInTheDocument();
  });
});
