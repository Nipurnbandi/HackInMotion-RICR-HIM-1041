import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

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
  TileLayer: ({ url }) => <div data-testid="tile-layer" data-url={url} />,
  Marker: ({ children, icon }) => (
    <div data-testid="marker" data-icon-html={icon?.html}>
      {children}
    </div>
  ),
  Popup: ({ children }) => <div data-testid="popup">{children}</div>,
  useMap: () => ({ fitBounds: vi.fn() }),
}));

import CityMap from "../shared/components/CityMap";

const ISSUES = [
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
    id: 2,
    tracking_id: "SMC-2026-000002",
    category: "WATER_LEAKAGE",
    status: "RESOLVED",
    latitude: 23.27,
    longitude: 77.42,
    address: "Lake View",
    created_at: "2026-08-10T09:00:00Z",
    report_count: 1,
    citizen_count: 1,
    department_name: "Water & Drainage",
  },
];

describe("CityMap", () => {
  it("renders one color-coded marker per issue with popup details", () => {
    render(<CityMap issues={ISSUES} colorMode="status" />);

    const markers = screen.getAllByTestId("marker");
    expect(markers).toHaveLength(2);

    // Status mode: submitted = blue ring, resolved = dimmed green marker.
    expect(markers[0].dataset.iconHtml).toContain("#3987e5");
    expect(markers[1].dataset.iconHtml).toContain("#0ca30c");
    expect(markers[1].dataset.iconHtml).toContain("map-pin--closed");

    const popup = within(markers[0]).getByTestId("popup");
    expect(popup).toHaveTextContent("Pothole");
    expect(popup).toHaveTextContent("Main Road, Bhopal");
    expect(popup).toHaveTextContent("3 reports");
    expect(popup).toHaveTextContent("Roads Department");
  });

  it("colors markers by category when asked", () => {
    render(<CityMap issues={ISSUES} colorMode="category" />);

    const markers = screen.getAllByTestId("marker");
    expect(markers[0].dataset.iconHtml).toContain("#d95926");
    expect(markers[1].dataset.iconHtml).toContain("#3987e5");
  });

  it("shows a legend limited to what is on the map and toggles color mode", async () => {
    const onColorModeChange = vi.fn();
    const user = userEvent.setup();
    render(
      <CityMap
        issues={ISSUES}
        colorMode="status"
        onColorModeChange={onColorModeChange}
      />
    );

    const legend = screen.getByRole("list", { name: "Map legend" });
    expect(within(legend).getByText("Submitted")).toBeInTheDocument();
    expect(within(legend).getByText("Resolved")).toBeInTheDocument();
    expect(within(legend).queryByText("Rejected")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Category" }));
    expect(onColorModeChange).toHaveBeenCalledWith("category");
  });

  it("uses dark tiles for the dark theme", () => {
    render(<CityMap issues={ISSUES} theme="dark" />);
    expect(screen.getByTestId("tile-layer").dataset.url).toContain("dark_all");
  });
});
