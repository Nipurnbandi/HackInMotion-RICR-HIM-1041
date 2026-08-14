import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("leaflet/dist/leaflet.css", () => ({}));
vi.mock("leaflet", () => ({
  default: {
    divIcon: (options) => options,
    latLngBounds: () => ({ pad: () => ({}) }),
    icon: () => ({}),
  },
}));
vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }) => <div data-testid="map-container">{children}</div>,
  TileLayer: () => null,
  Marker: ({ children }) => <div data-testid="marker">{children}</div>,
  Popup: ({ children }) => <div data-testid="popup">{children}</div>,
  useMap: () => ({ fitBounds: vi.fn() }),
}));

import CityMap from "../shared/components/CityMap";
import CitizenLayout from "../citizen/components/CitizenLayout";
import TransparencyPage from "../public/TransparencyPage";
import { LanguageProvider } from "../shared/i18n";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    user: { id: 1, email: "citizen@example.com", role: "CITIZEN" },
    role: "CITIZEN",
    isAuthenticated: true,
    loading: false,
    logout: vi.fn(),
  }),
}));

const MAP_ISSUE = {
  id: 1,
  tracking_id: "SMC-2026-000001",
  category: "POTHOLE",
  status: "SUBMITTED",
  latitude: 23.2599,
  longitude: 77.4126,
  address: "Main Road, Bhopal",
  created_at: "2026-08-09T09:00:00Z",
  report_count: 2,
  citizen_count: 2,
  vote_count: 3,
  has_voted: false,
  escalated: true,
  department_name: "Roads Department",
};

const TRANSPARENCY = {
  generated_at: "2026-08-14T12:00:00Z",
  city: {
    code: "CITY",
    name: "City-wide",
    total_cases: 4,
    open_cases: 2,
    resolved_cases: 2,
    escalated_cases: 1,
    resolution_rate: 50,
    on_time_rate: 100,
    avg_resolution_days: 2.5,
    score: 76,
    grade: "A",
  },
  departments: [
    {
      code: "ROADS",
      name: "Roads Department",
      total_cases: 2,
      open_cases: 1,
      resolved_cases: 1,
      escalated_cases: 0,
      resolution_rate: 50,
      on_time_rate: 100,
      avg_resolution_days: 2.0,
      score: 72,
      grade: "A",
    },
    {
      code: "WATER",
      name: "Water & Drainage",
      total_cases: 0,
      open_cases: 0,
      resolved_cases: 0,
      escalated_cases: 0,
      resolution_rate: null,
      on_time_rate: null,
      avg_resolution_days: null,
      score: null,
      grade: null,
    },
  ],
  methodology: "Score = 50% resolution rate + 30% resolved-within-SLA rate…",
};

describe("Citizen upvoting on the map", () => {
  it("shows a support button with the vote count and escalation flag", async () => {
    const onVote = vi.fn();
    const user = userEvent.setup();
    render(<CityMap issues={[MAP_ISSUE]} onVote={onVote} />);

    expect(screen.getByText(/⚠/)).toBeInTheDocument();
    const voteButton = screen.getByRole("button", { name: /Support · 3/ });
    await user.click(voteButton);
    expect(onVote).toHaveBeenCalledWith(expect.objectContaining({ id: 1 }));
  });

  it("shows supporters read-only when voting is not available (admin)", () => {
    render(<CityMap issues={[MAP_ISSUE]} />);
    expect(screen.queryByRole("button", { name: /Support/ })).not.toBeInTheDocument();
    expect(screen.getByText(/👍 3/)).toBeInTheDocument();
  });
});

describe("Public transparency report card", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => TRANSPARENCY,
    });
  });

  it("renders city score and department grades from the public API", async () => {
    render(
      <MemoryRouter>
        <TransparencyPage />
      </MemoryRouter>
    );

    expect(await screen.findByText("City report card")).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledWith("/api/public/transparency");

    expect(screen.getByText("76/100")).toBeInTheDocument();
    const roads = screen.getByText("Roads Department").closest("li");
    expect(within(roads).getByText("A")).toBeInTheDocument();
    expect(within(roads).getByText("72/100")).toBeInTheDocument();

    const water = screen.getByText("Water & Drainage").closest("li");
    expect(within(water).getByText("No data")).toBeInTheDocument();
  });
});

describe("Multi-language citizen portal", () => {
  it("switches the citizen navigation to Hindi and back", async () => {
    const user = userEvent.setup();
    render(
      <LanguageProvider>
        <MemoryRouter>
          <CitizenLayout />
        </MemoryRouter>
      </LanguageProvider>
    );

    expect(screen.getByText("My Reports")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /हिन्दी/ }));

    expect(await screen.findByText("मेरी रिपोर्टें")).toBeInTheDocument();
    expect(screen.getByText("शहर का नक्शा")).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("hi");

    await user.click(screen.getByRole("button", { name: /English/ }));
    expect(await screen.findByText("My Reports")).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("en");
  });
});
