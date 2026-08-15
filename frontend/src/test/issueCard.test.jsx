import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import IssueCard from "../citizen/components/IssueCard";

function renderCard(issue) {
  return render(
    <MemoryRouter>
      <ul>
        <IssueCard issue={issue} />
      </ul>
    </MemoryRouter>
  );
}

const BASE = {
  id: 3,
  tracking_id: "SMC-2026-000003",
  category: "POTHOLE",
  description: "Deep pothole near the crossing.",
  status: "SUBMITTED",
  created_at: "2026-08-12T09:30:00Z",
  address: null,
  latitude: null,
  longitude: null,
};

describe("IssueCard location", () => {
  it("renders coordinates when both are present", () => {
    renderCard({ ...BASE, latitude: 23.2599, longitude: 77.4126 });
    expect(screen.getByText("23.2599, 77.4126")).toBeInTheDocument();
  });

  it("does not crash when longitude is null but latitude is set", () => {
    // Regression: the ternary guarded only latitude, then called
    // issue.longitude.toFixed(4), which threw and killed the whole card render.
    renderCard({ ...BASE, latitude: 23.2599, longitude: null });
    expect(screen.getByText("Location not recorded")).toBeInTheDocument();
  });

  it("prefers a human-readable address when present", () => {
    renderCard({
      ...BASE,
      address: "Nehru Nagar, Bhopal",
      latitude: 23.2599,
      longitude: 77.4126,
    });
    expect(screen.getByText("Nehru Nagar, Bhopal")).toBeInTheDocument();
  });
});
