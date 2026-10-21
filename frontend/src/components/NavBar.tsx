import { useMemo } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { COLA_KEY } from "../types";

function colaCount(): number {
  try {
    const raw = sessionStorage.getItem(COLA_KEY);
    if (!raw) return 0;
    return (JSON.parse(raw) as unknown[]).length;
  } catch {
    return 0;
  }
}

export function NavBar() {
  const location = useLocation();
  const pending = useMemo(() => colaCount(), [location.pathname, location.key]);
  return (
    <nav className="nav-bar" aria-label="Principal">
      <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : undefined)}>
        Captura
      </NavLink>
      <NavLink
        to="/confirmar"
        className={({ isActive }) => (isActive ? "active" : undefined)}
      >
        Resultados{pending > 0 ? ` (${pending})` : ""}
      </NavLink>
      <NavLink
        to="/registros"
        className={({ isActive }) => (isActive ? "active" : undefined)}
      >
        Registros
      </NavLink>
    </nav>
  );
}
