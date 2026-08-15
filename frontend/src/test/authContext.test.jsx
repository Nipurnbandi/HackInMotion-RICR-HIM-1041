import { describe, expect, it, vi, beforeEach } from "vitest";
import { useState } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AuthProvider, useAuth } from "../auth/AuthContext";
import * as apiModule from "../services/api";

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

function LoginProbe() {
  const { login } = useAuth();
  const [outcome, setOutcome] = useState("");
  return (
    <>
      <button
        onClick={async () => {
          try {
            setOutcome(`path:${await login("c@example.com", "pw")}`);
          } catch (err) {
            setOutcome(`threw:${err.message}`);
          }
        }}
      >
        sign in
      </button>
      <p data-testid="outcome">{outcome}</p>
    </>
  );
}

describe("AuthContext login resilience", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // getMe rejects both on mount and right after login (a transient blip),
    // so refreshUser() returns null even though the login cookie was set.
    apiModule.api.getMe.mockRejectedValue(new Error("unauthenticated"));
  });

  it("resolves to a valid path instead of crashing when the post-login profile fetch fails", async () => {
    apiModule.api.login.mockResolvedValue({});

    render(
      <AuthProvider>
        <LoginProbe />
      </AuthProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "sign in" }));

    // Old code called getDashboardPath(me.role) with me === null and threw
    // "Cannot read properties of null (reading 'role')". The fix defaults to
    // the citizen path so a genuinely-logged-in user is never stranded.
    await waitFor(() =>
      expect(screen.getByTestId("outcome")).toHaveTextContent("path:/citizen")
    );
  });
});
