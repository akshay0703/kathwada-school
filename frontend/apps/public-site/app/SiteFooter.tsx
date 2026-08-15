import Link from "next/link";

// Content below is carried over from the existing prototype (see
// docs/prototype-analysis.md §16) wherever the prototype had real text.
// The prototype's own footer literally said: "Design preview — replace
// placeholder text, photos and contact details with real school
// information." Anything still marked [PLACEHOLDER] below is exactly that —
// carried forward unchanged, not invented here, and needs your input.

export function SiteFooter() {
  return (
    <footer
      style={{
        background: "var(--navy-primary)",
        color: "#fff",
        padding: "48px 32px 24px",
        marginTop: "64px",
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "40px",
          maxWidth: "1100px",
          margin: "0 auto",
        }}
      >
        <div style={{ flex: "1 1 240px" }}>
          <div style={{ fontFamily: "var(--font-display)", fontSize: "18px", marginBottom: "8px" }}>
            Kathwada High School
          </div>
          <p style={{ fontSize: "13px", opacity: 0.8, lineHeight: 1.6 }}>
            A center of academic excellence in Kathwada, Ahmedabad — nurturing curious minds and confident
            character.
          </p>
        </div>

        <div style={{ flex: "1 1 140px" }}>
          <div style={{ fontSize: "12px", opacity: 0.6, marginBottom: "10px", letterSpacing: "1px" }}>
            EXPLORE
          </div>
          <FooterLinks
            links={[
              ["/about", "About Us"],
              ["/academics", "Academics"],
              ["/admissions", "Admissions"],
              ["/gallery", "Gallery"],
            ]}
          />
        </div>

        <div style={{ flex: "1 1 140px" }}>
          <div style={{ fontSize: "12px", opacity: 0.6, marginBottom: "10px", letterSpacing: "1px" }}>
            RESOURCES
          </div>
          <FooterLinks
            links={[
              ["/news", "News & Events"],
              ["/contact", "Contact"],
            ]}
          />
        </div>

        <div style={{ flex: "1 1 200px" }}>
          <div style={{ fontSize: "12px", opacity: 0.6, marginBottom: "10px", letterSpacing: "1px" }}>
            CONTACT
          </div>
          <p style={{ fontSize: "13px", opacity: 0.85, margin: "0 0 6px" }}>Kathwada, Ahmedabad, Gujarat</p>
          <p style={{ fontSize: "13px", opacity: 0.85, margin: "0 0 6px" }}>
            [PLACEHOLDER — school phone number]
          </p>
          <p style={{ fontSize: "13px", opacity: 0.85, margin: 0 }}>[PLACEHOLDER — school email address]</p>
        </div>
      </div>

      <div
        style={{
          maxWidth: "1100px",
          margin: "32px auto 0",
          paddingTop: "20px",
          borderTop: "1px solid rgba(255,255,255,0.15)",
          fontSize: "12px",
          opacity: 0.6,
          display: "flex",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <span>© {new Date().getFullYear()} Kathwada High School. All rights reserved.</span>
      </div>
    </footer>
  );
}

function FooterLinks({ links }: { links: [string, string][] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {links.map(([href, label]) => (
        <Link key={href} href={href} style={{ fontSize: "13px", color: "#fff", opacity: 0.85, textDecoration: "none" }}>
          {label}
        </Link>
      ))}
    </div>
  );
}
