import type { ReactNode } from "react";

export function PageHero({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <section
      style={{
        padding: "56px 32px 48px",
        background: "linear-gradient(180deg, var(--navy-soft), var(--bg))",
      }}
    >
      <div style={{ maxWidth: "760px", margin: "0 auto", textAlign: "center" }}>
        <p style={{ fontFamily: "var(--font-mono)", color: "var(--gold)", letterSpacing: "2px", fontSize: "12px", marginBottom: "10px" }}>
          {eyebrow.toUpperCase()}
        </p>
        {/* Single h1 per page, right at the top — this is the page's one and
            only h1, satisfying proper heading hierarchy for SEO/accessibility. */}
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: "clamp(28px,4vw,40px)", color: "var(--navy-primary)", margin: "0 0 12px" }}>
          {title}
        </h1>
        <p style={{ color: "var(--ink)", opacity: 0.75, fontSize: "15px", lineHeight: 1.6 }}>{description}</p>
      </div>
    </section>
  );
}

export function Section({ eyebrow, title, children }: { eyebrow?: string; title: string; children: ReactNode }) {
  return (
    <section style={{ padding: "40px 32px", maxWidth: "1000px", margin: "0 auto" }}>
      {eyebrow && (
        <p style={{ fontFamily: "var(--font-mono)", color: "var(--gold)", letterSpacing: "1.5px", fontSize: "11px", marginBottom: "8px" }}>
          {eyebrow.toUpperCase()}
        </p>
      )}
      <h2 style={{ fontFamily: "var(--font-display)", fontSize: "26px", color: "var(--navy-primary)", marginBottom: "20px" }}>
        {title}
      </h2>
      {children}
    </section>
  );
}

export function CardGrid({ children }: { children: ReactNode }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "18px" }}>
      {children}
    </div>
  );
}

export function Card({ icon, title, description }: { icon?: string; title: string; description: string }) {
  return (
    <div style={{ border: "1px solid var(--line)", borderRadius: "10px", padding: "20px", background: "var(--paper)" }}>
      {icon && <div style={{ fontSize: "22px", marginBottom: "10px" }}>{icon}</div>}
      <h3 style={{ fontFamily: "var(--font-display)", fontSize: "16px", color: "var(--navy-primary)", margin: "0 0 6px" }}>
        {title}
      </h3>
      <p style={{ fontSize: "13.5px", color: "var(--ink)", opacity: 0.75, lineHeight: 1.5, margin: 0 }}>{description}</p>
    </div>
  );
}

export function Placeholder({ children }: { children: ReactNode }) {
  return (
    <span style={{ background: "#fff3cd", color: "#7a5c00", padding: "1px 6px", borderRadius: "4px", fontSize: "0.95em" }}>
      {children}
    </span>
  );
}
