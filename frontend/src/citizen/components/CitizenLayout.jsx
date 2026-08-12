import { useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import "../../styles/tokens.css";
import "../../styles/citizen.css";

const NAV_ITEMS = [
  { to: "/citizen", label: "Home", end: true },
  { to: "/citizen/report", label: "Report" },
  { to: "/citizen/issues", label: "My Reports" },
  { to: "/citizen/help", label: "Help" },
  { to: "/citizen/profile", label: "Profile" },
];

export default function CitizenLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="citizen-shell">
      <a className="skip-link" href="#citizen-main">
        Skip to main content
      </a>

      <header className="citizen-header">
        <div className="citizen-header__inner">
          <Link to="/citizen" className="brand">
            <span className="brand__mark" aria-hidden="true">
              🏙
            </span>
            <span className="brand__text">
              SmartCity<span className="brand__sub">Citizen Portal</span>
            </span>
          </Link>

          <button
            type="button"
            className="nav-toggle"
            aria-expanded={menuOpen}
            aria-controls="citizen-nav"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span className="visually-hidden">
              {menuOpen ? "Close navigation" : "Open navigation"}
            </span>
            <span aria-hidden="true">{menuOpen ? "✕" : "☰"}</span>
          </button>

          <nav
            id="citizen-nav"
            className={`citizen-nav${menuOpen ? " citizen-nav--open" : ""}`}
            aria-label="Citizen portal"
          >
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `citizen-nav__link${isActive ? " citizen-nav__link--active" : ""}`
                }
                onClick={() => setMenuOpen(false)}
              >
                {item.label}
              </NavLink>
            ))}

            <div className="citizen-nav__account">
              <span className="citizen-nav__email" title={user?.email}>
                {user?.email}
              </span>
              <button type="button" className="button button--ghost" onClick={handleLogout}>
                Log out
              </button>
            </div>
          </nav>
        </div>
      </header>

      <main id="citizen-main" className="citizen-main" key={location.pathname}>
        <Outlet />
      </main>

      <footer className="citizen-footer">
        <p>
          SmartCity Civic Issue Reporting · Reports are reviewed by your city
          administration.
        </p>
      </footer>
    </div>
  );
}
