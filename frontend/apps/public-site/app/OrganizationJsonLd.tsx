// EducationalOrganization structured data. Per explicit instruction: only
// fields with real, verifiable-from-the-project content are included.
// Deliberately OMITTED (not invented): telephone (prototype's own value is
// the placeholder pattern "+91 00000 00000"), email (same footer/contact
// values are presented as placeholders in the prototype, not confirmed
// real), sameAs/social profiles (none exist in the prototype), awards,
// accreditation, and enrollment/staff counts (the prototype's animated
// counter numbers — 1200 students, 60 staff, etc. — read as illustrative
// demo values, not confirmed real statistics; see docs/prototype-analysis.md
// and the Home page's own note about these).
export function OrganizationJsonLd() {
  const data = {
    "@context": "https://schema.org",
    "@type": "EducationalOrganization",
    name: "Kathwada High School",
    description:
      "Kathwada High School offers Secondary and Higher Secondary education (Std 9–12) in Kathwada, Ahmedabad, with a focus on academic rigour, character and modern learning.",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Kathwada, Ahmedabad",
      addressRegion: "Gujarat",
      addressCountry: "IN",
    },
    foundingDate: "1975",
  };

  return (
    <script
      type="application/ld+json"
      // JSON-LD requires raw script content; `data` above is static, not user input.
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
