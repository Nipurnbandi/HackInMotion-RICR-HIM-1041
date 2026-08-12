import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

// jsdom cannot render a real Leaflet map; stub the pieces LocationPicker uses.
vi.mock("leaflet/dist/leaflet.css", () => ({}));
vi.mock("leaflet/dist/images/marker-icon.png", () => ({ default: "marker.png" }));
vi.mock("leaflet/dist/images/marker-icon-2x.png", () => ({ default: "marker-2x.png" }));
vi.mock("leaflet/dist/images/marker-shadow.png", () => ({ default: "shadow.png" }));
vi.mock("leaflet", () => ({ default: { icon: () => ({}) } }));

vi.mock("react-leaflet", async () => {
  const { mapHandlers } = await import("./mapHandlers.js");
  return {
    MapContainer: ({ children }) => <div data-testid="map">{children}</div>,
    TileLayer: () => null,
    Marker: ({ position }) => (
      <div data-testid="marker" data-position={position?.join(",")} />
    ),
    useMap: () => ({ setView: () => {}, getZoom: () => 13 }),
    useMapEvents: (handlers) => {
      Object.assign(mapHandlers, handlers);
      return null;
    },
  };
});

vi.mock("../citizen/services/geocoding", async () => {
  const actual = await vi.importActual("../citizen/services/geocoding");
  return { ...actual, reverseGeocode: vi.fn() };
});

vi.mock("../citizen/services/issueService", () => ({
  issueService: {
    createIssue: vi.fn(),
    listIssues: vi.fn(),
    getIssue: vi.fn(),
    getDashboard: vi.fn(),
    getStats: vi.fn(),
  },
}));

import ReportIssue from "../citizen/pages/ReportIssue";
import { issueService } from "../citizen/services/issueService";
import { reverseGeocode } from "../citizen/services/geocoding";
import { mapHandlers } from "./mapHandlers.js";

const DESCRIPTION = "Large pothole near the main road, dangerous for two-wheelers.";

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/citizen/report"]}>
      <Routes>
        <Route path="/citizen/report" element={<ReportIssue />} />
        <Route path="/citizen/issues" element={<p>My reports page</p>} />
      </Routes>
    </MemoryRouter>
  );
}

/**
 * Step titles appear twice (stepper + form heading), so always target the
 * form's own heading.
 */
function findStepHeading(title) {
  return screen.findByRole("heading", {
    level: 2,
    name: (accessibleName) => accessibleName.includes(title),
  });
}

async function pickMapLocation(latitude = 23.2599, longitude = 77.4126) {
  await act(async () => {
    mapHandlers.click({ latlng: { lat: latitude, lng: longitude } });
  });
}

/** Walk the wizard from step 1 to the review step with valid input. */
async function completeForm(user, { withPhoto = false } = {}) {
  await user.click(screen.getByRole("radio", { name: /Pothole/i }));
  await user.click(screen.getByRole("button", { name: "Continue" }));

  await findStepHeading("Where is the problem?");
  await pickMapLocation();
  await user.click(screen.getByRole("button", { name: "Continue" }));

  await findStepHeading("Add photo evidence");
  if (withPhoto) {
    const file = new File(["binary"], "pothole.png", { type: "image/png" });
    await user.upload(screen.getByLabelText(/Photo evidence/i), file);
  }
  await user.click(screen.getByRole("button", { name: "Continue" }));

  await findStepHeading("Describe the problem");
  await user.type(screen.getByLabelText("Describe the problem"), DESCRIPTION);
  await user.click(screen.getByRole("button", { name: "Continue" }));

  await findStepHeading("Review & submit");
}

describe("ReportIssue", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const key of Object.keys(mapHandlers)) delete mapHandlers[key];
    reverseGeocode.mockResolvedValue("Example Street, Bhopal");
    globalThis.URL.createObjectURL = vi.fn(() => "blob:preview");
    globalThis.URL.revokeObjectURL = vi.fn();
  });

  it("renders the first step of the form", () => {
    renderPage();

    expect(
      screen.getByRole("heading", { level: 1, name: /Report an issue/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        level: 2,
        name: (name) => name.includes("What is the problem?"),
      })
    ).toBeInTheDocument();
    expect(screen.getByText("Step 1 of 5")).toBeInTheDocument();
  });

  it("offers every issue category as a single-choice option", () => {
    renderPage();

    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(7);
    expect(screen.getByRole("radio", { name: /Streetlight/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Broken Drainage/i })).toBeInTheDocument();
  });

  it("selects a category", async () => {
    const user = userEvent.setup();
    renderPage();

    const pothole = screen.getByRole("radio", { name: /Pothole/i });
    await user.click(pothole);

    expect(pothole).toBeChecked();
    expect(screen.getByRole("radio", { name: /Streetlight/i })).not.toBeChecked();
  });

  it("blocks step 1 until a category is chosen", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /choose the type of problem/i
    );
    expect(screen.getByText("Step 1 of 5")).toBeInTheDocument();
  });

  it("records a location picked on the map and resolves its address", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("radio", { name: /Pothole/i }));
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await findStepHeading("Where is the problem?");

    expect(screen.getByText(/No location selected yet/i)).toBeInTheDocument();

    await pickMapLocation(23.2599, 77.4126);

    expect(await screen.findByText("23.259900, 77.412600")).toBeInTheDocument();
    expect(await screen.findByText("Example Street, Bhopal")).toBeInTheDocument();
    expect(screen.getByTestId("marker")).toHaveAttribute("data-position", "23.2599,77.4126");
  });

  it("blocks step 2 until a location is selected", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("radio", { name: /Pothole/i }));
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await findStepHeading("Where is the problem?");

    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/select the location/i);
  });

  it("still accepts a location when reverse geocoding fails", async () => {
    reverseGeocode.mockResolvedValue(null);
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("radio", { name: /Pothole/i }));
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await findStepHeading("Where is the problem?");
    await pickMapLocation();

    expect(
      await screen.findByText(/No address found .* coordinates will be used/i)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Continue" }));
    expect(await findStepHeading("Add photo evidence")).toBeInTheDocument();
  });

  it("previews an attached photo and allows removing it", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("radio", { name: /Pothole/i }));
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await findStepHeading("Where is the problem?");
    await pickMapLocation();
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await findStepHeading("Add photo evidence");

    const file = new File(["binary"], "pothole.png", { type: "image/png" });
    await user.upload(screen.getByLabelText(/Photo evidence/i), file);

    const preview = await screen.findByRole("img", { name: /pothole\.png/i });
    expect(preview).toHaveAttribute("src", "blob:preview");
    expect(screen.getByText("pothole.png")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Remove" }));
    expect(screen.queryByRole("img", { name: /pothole\.png/i })).not.toBeInTheDocument();
  });

  it("rejects an unsupported file type before uploading", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("radio", { name: /Pothole/i }));
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await findStepHeading("Where is the problem?");
    await pickMapLocation();
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await findStepHeading("Add photo evidence");

    // `user.upload` honours the accept attribute, but that attribute is only a
    // hint in real browsers — fire the change directly to exercise our guard.
    const file = new File(["%PDF"], "notes.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText(/Photo evidence/i), {
      target: { files: [file] },
    });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /isn't supported.*JPEG, PNG, or WEBP/i
    );
  });

  it("requires a description of a reasonable length", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("radio", { name: /Pothole/i }));
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await findStepHeading("Where is the problem?");
    await pickMapLocation();
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await findStepHeading("Add photo evidence");
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await findStepHeading("Describe the problem");

    await user.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/describe the problem/i);

    await user.type(screen.getByLabelText("Describe the problem"), "hole");
    await user.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/at least 10 characters/i);
  });

  it("summarises the report on the review step", async () => {
    const user = userEvent.setup();
    const { container } = renderPage();

    await completeForm(user, { withPhoto: true });

    const review = container.querySelector(".review");
    expect(within(review).getByText("Pothole")).toBeInTheDocument();
    expect(within(review).getByText("Example Street, Bhopal")).toBeInTheDocument();
    expect(within(review).getByText("23.259900, 77.412600")).toBeInTheDocument();
    expect(within(review).getByText("pothole.png")).toBeInTheDocument();
    expect(within(review).getByText(DESCRIPTION)).toBeInTheDocument();
  });

  it("never submits before the review step is shown", async () => {
    const user = userEvent.setup();
    const { container } = renderPage();

    await completeForm(user);

    // Regression guard: when the primary action was a type="submit" button the
    // browser fired the form's default submit as soon as step 4 advanced,
    // skipping review entirely. No action button may be a submit button.
    const submitButtons = container.querySelectorAll(
      '.form-card__actions button[type="submit"]'
    );
    expect(submitButtons).toHaveLength(0);
    expect(issueService.createIssue).not.toHaveBeenCalled();
    expect(
      await screen.findByRole("button", { name: "Submit report" })
    ).toBeInTheDocument();
  });

  it("submits the report and shows the tracking ID", async () => {
    issueService.createIssue.mockResolvedValue({
      id: 42,
      tracking_id: "SMC-2026-000042",
      status: "SUBMITTED",
    });

    const user = userEvent.setup();
    renderPage();
    await completeForm(user, { withPhoto: true });

    await user.click(screen.getByRole("button", { name: "Submit report" }));

    expect(
      await screen.findByRole("heading", { name: /Issue reported successfully/i })
    ).toBeInTheDocument();
    expect(screen.getByText("SMC-2026-000042")).toBeInTheDocument();
    expect(screen.getByText("Submitted")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /View my reports/i })).toHaveAttribute(
      "href",
      "/citizen/issues"
    );

    const [values] = issueService.createIssue.mock.calls[0];
    expect(values).toMatchObject({
      category: "POTHOLE",
      description: DESCRIPTION,
      latitude: 23.2599,
      longitude: 77.4126,
      address: "Example Street, Bhopal",
    });
    expect(values.photo).toBeInstanceOf(File);
    // Ownership and status are the backend's decision, never sent by the client.
    expect(values).not.toHaveProperty("citizen_id");
    expect(values).not.toHaveProperty("status");
  });

  it("shows a recoverable error when submission fails", async () => {
    const networkError = new Error(
      "We couldn't submit your report. Please check your connection and try again."
    );
    networkError.isNetworkError = true;
    issueService.createIssue.mockRejectedValue(networkError);

    const user = userEvent.setup();
    renderPage();
    await completeForm(user);

    await user.click(screen.getByRole("button", { name: "Submit report" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/couldn't submit your report/i);
    // The user stays on the review step so they can retry without re-entering.
    expect(screen.getByRole("button", { name: "Submit report" })).toBeEnabled();
  });

  it("surfaces backend field validation errors on the right step", async () => {
    const validationError = new Error("Please correct the highlighted fields.");
    validationError.status = 422;
    validationError.fieldErrors = { description: "Description is too short." };
    issueService.createIssue.mockRejectedValue(validationError);

    const user = userEvent.setup();
    renderPage();
    await completeForm(user);

    await user.click(screen.getByRole("button", { name: "Submit report" }));

    // The wizard jumps back to the step that owns the rejected field.
    await waitFor(async () => {
      expect(await findStepHeading("Describe the problem")).toBeInTheDocument();
    });
    expect(await screen.findByText("Description is too short.")).toBeInTheDocument();
  });
});

