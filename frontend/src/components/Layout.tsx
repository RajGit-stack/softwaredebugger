import { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";

type Props = {
  children: ReactNode;
};

export function Layout({ children }: Props) {
  return (
    <div className="app-root">
      <aside className="sidebar">
        <Link to="/" className="logo">
          AI Software Debugger
        </Link>
        <nav className="nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}>
            Dashboard
          </NavLink>
          <NavLink to="/jobs" className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}>
            Jobs
          </NavLink>
        </nav>
      </aside>
      <main className="main">
        <header className="topbar">
          <div />
        </header>
        <section className="content">{children}</section>
      </main>
    </div>
  );
}

