import Link from "next/link";

const PAGES = [
  { href: "/", label: "Home" },
  { href: "/about", label: "About" },
  { href: "/academics", label: "Academics" },
  { href: "/admissions", label: "Admissions" },
  { href: "/gallery", label: "Gallery" },
  { href: "/news", label: "News & Events" },
  { href: "/contact", label: "Contact" },
];

const ERP_URL = process.env.NEXT_PUBLIC_ERP_URL ?? "http://localhost:3001";

export function SiteNav() {
  return (
    <nav
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "16px 32px",
        borderBottom: "1px solid var(--line)",
        background: "var(--paper)",
      }}
    >
      <Link
        href="/"
        style={{
          fontFamily: "var(--font-display)",
          fontWeight: 600,
          fontSize: "18px",
          color: "var(--navy-primary)",
          textDecoration: "none",
        }}
      >
        Kathwada High School
      </Link>

      <div style={{ display: "flex", gap: "20px", alignItems: "center" }}>
        {PAGES.map((page) => (
          <Link
            key={page.href}
            href={page.href}
            style={{ fontSize: "14px", color: "var(--ink)", textDecoration: "none" }}
          >
            {page.label}
          </Link>
        ))}
        <a
          href={ERP_URL}
          style={{
            fontSize: "14px",
            fontWeight: 600,
            color: "#fff",
            background: "var(--navy-primary)",
            padding: "8px 16px",
            borderRadius: "6px",
            textDecoration: "none",
          }}
        >
          ERP Login
        </a>
      </div>
    </nav>
  );
}
