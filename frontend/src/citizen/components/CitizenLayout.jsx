import { useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { LANGUAGES, useI18n } from "../../shared/i18n";
import "../../styles/tokens.css";
import "../../styles/citizen.css";

const NAV_ITEMS = [
  { to: "/citizen", key: "nav.home", fallback: "Home", end: true },
  { to: "/citizen/map", key: "nav.citymap", fallback: "City Map" },
  { to: "/citizen/report", key: "nav.report", fallback: "Report" },
  { to: "/citizen/issues", key: "nav.myreports", fallback: "My Reports" },
  { to: "/citizen/help", key: "nav.help", fallback: "Help" },
  { to: "/citizen/profile", key: "nav.profile", fallback: "Profile" },
];

export default function CitizenLayout() {
  const { user, logout } = useAuth();
  const { lang, setLang, t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  const nextLanguage = LANGUAGES.find((item) => item.code !== lang) ?? LANGUAGES[0];

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
              SmartCity
              <span className="brand__sub">{t("brand.sub", "Citizen Portal")}</span>
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
                {t(item.key, item.fallback)}
              </NavLink>
            ))}

            <div className="citizen-nav__account">
              <button
                type="button"
                className="lang-toggle"
                onClick={() => setLang(nextLanguage.code)}
                title={`Switch language to ${nextLanguage.label}`}
              >
                🌐 {nextLanguage.label}
              </button>
              <span className="citizen-nav__email" title={user?.email}>
                {user?.email}
              </span>
              <button type="button" className="button button--ghost" onClick={handleLogout}>
                {t("nav.logout", "Log out")}
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
          {t(
            "footer.note",
            "SmartCity Civic Issue Reporting · Reports are reviewed by your city administration."
          )}
        </p>
        <p>
          <Link to="/transparency" className="link">
            {t("footer.transparency", "City transparency report card")}
          </Link>
        </p>
      </footer>
    </div>
  );
}
