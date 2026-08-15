import type { Metadata } from "next";
import Link from "next/link";
import { Card, CardGrid } from "./_components";
import { OrganizationJsonLd } from "./OrganizationJsonLd";

export const metadata: Metadata = {
  title: "Kathwada High School — Home",
  description:
    "Kathwada High School offers Secondary and Higher Secondary education (Std 9–12) in Kathwada, Ahmedabad — academic rigour, character and modern learning.",
  alternates: { canonical: "/" },
  openGraph: {
    title: "Kathwada High School",
    description: "Secondary and Higher Secondary education (Std 9–12) in Kathwada, Ahmedabad.",
    url: "/",
    type: "website",
  },
};

// Stats below (1200+ students, 60+ faculty, 50+ years, 97% board result) are
// carried over from the prototype's own animated-counter values (see
// docs/prototype-analysis.md). They read as plausible, deliberately chosen
// demo figures rather than "1234"-style filler, but they are NOT verified
// real statistics — confirm/replace with the school's actual current numbers.
const STATS = [
  { value: "1200+", label: "Students" },
  { value: "60+", label: "Faculty & Staff" },
  { value: "50+", label: "Years of Excellence" },
  { value: "97%", label: "Board Result (last year)" },
];

export default function HomePage() {
  return (
    <main>
      <OrganizationJsonLd />

      <section
        style={{
          padding: "72px 32px 40px",
          textAlign: "center",
          background: "linear-gradient(180deg, var(--navy-soft), var(--bg))",
        }}
      >
        <p style={{ fontFamily: "var(--font-mono)", color: "var(--gold)", letterSpacing: "2px", fontSize: "12px", marginBottom: "12px" }}>
          ADMISSIONS OPEN · 2026–27
        </p>
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: "clamp(28px,4vw,42px)", color: "var(--navy-primary)", maxWidth: "720px", margin: "0 auto 16px", lineHeight: 1.2 }}>
          Where every student is prepared for tomorrow, not just tested on yesterday.
        </h1>
        <p style={{ color: "var(--ink)", opacity: 0.75, maxWidth: "580px", margin: "0 auto 28px" }}>
          Kathwada High School offers Secondary and Higher Secondary education (Std 9–12) with a focus on
          academic rigour, character and modern learning — right here in Kathwada, Ahmedabad.
        </p>
        <div style={{ display: "flex", gap: "12px", justifyContent: "center", flexWrap: "wrap" }}>
          <Link href="/admissions" style={{ background: "var(--navy-primary)", color: "#fff", padding: "11px 22px", borderRadius: "6px", textDecoration: "none", fontSize: "14px", fontWeight: 600 }}>
            Apply for Admission
          </Link>
          <Link href="/about" style={{ border: "1px solid var(--navy-primary)", color: "var(--navy-primary)", padding: "11px 22px", borderRadius: "6px", textDecoration: "none", fontSize: "14px", fontWeight: 600 }}>
            Explore the School
          </Link>
        </div>
      </section>

      <section style={{ padding: "40px 32px", display: "flex", gap: "20px", justifyContent: "center", flexWrap: "wrap" }}>
        {STATS.map((s) => (
          <div key={s.label} style={{ border: "1px solid var(--line)", borderRadius: "10px", padding: "18px 28px", textAlign: "center", background: "var(--paper)", minWidth: "140px" }}>
            <div style={{ fontFamily: "var(--font-display)", fontSize: "24px", color: "var(--navy-primary)" }}>{s.value}</div>
            <div style={{ fontSize: "12.5px", color: "var(--ink)", opacity: 0.6 }}>{s.label}</div>
          </div>
        ))}
      </section>

      <section style={{ padding: "40px 32px", maxWidth: "760px", margin: "0 auto" }}>
        <p style={{ fontFamily: "var(--font-mono)", color: "var(--gold)", letterSpacing: "1.5px", fontSize: "11px", marginBottom: "8px" }}>
          ABOUT THE SCHOOL
        </p>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: "24px", color: "var(--navy-primary)", marginBottom: "14px" }}>
          A learning community built on discipline, curiosity and care
        </h2>
        <p style={{ color: "var(--ink)", opacity: 0.8, lineHeight: 1.7, fontSize: "14.5px" }}>
          Kathwada High School has grown into one of the trusted names in Kathwada for a reason: small class
          attention, well-qualified teachers, and a culture that pushes students to think for themselves — not
          just memorise for exams. From Secondary through Higher Secondary (Arts and Commerce), every stage is
          designed to build on the last.
        </p>
        <Link href="/about" style={{ color: "var(--navy-primary)", fontSize: "14px", fontWeight: 600, textDecoration: "none" }}>
          Read our full story →
        </Link>
      </section>

      <section style={{ padding: "40px 32px", maxWidth: "1000px", margin: "0 auto" }}>
        <p style={{ fontFamily: "var(--font-mono)", color: "var(--gold)", letterSpacing: "1.5px", fontSize: "11px", marginBottom: "8px" }}>
          FACILITIES
        </p>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: "24px", color: "var(--navy-primary)", marginBottom: "20px" }}>
          Everything a growing mind needs, on one campus
        </h2>
        <CardGrid>
          <Card icon="📚" title="Well-Stocked Library" description="A quiet, spacious library with a growing collection across subjects and reading levels." />
          <Card icon="🔬" title="Science Laboratories" description="Dedicated Physics, Chemistry and Biology labs for hands-on, experiment-led learning." />
          <Card icon="💻" title="Computer Lab" description="Modern systems and structured computer literacy classes from an early age." />
          <Card icon="🏀" title="Sports & Playground" description="Ample outdoor space for athletics, football, kho-kho and daily physical education." />
          <Card icon="🎭" title="Auditorium" description="A dedicated space for assemblies, cultural events and inter-house competitions." />
          <Card icon="🚌" title="Transport" description="Safe, supervised school transport covering key routes across Kathwada and nearby areas." />
        </CardGrid>
      </section>

      <section style={{ padding: "40px 32px", maxWidth: "1000px", margin: "0 auto" }}>
        <p style={{ fontFamily: "var(--font-mono)", color: "var(--gold)", letterSpacing: "1.5px", fontSize: "11px", marginBottom: "8px" }}>
          WHY CHOOSE US
        </p>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: "24px", color: "var(--navy-primary)", marginBottom: "20px" }}>
          The Kathwada High School difference
        </h2>
        <CardGrid>
          <Card icon="🎯" title="Individual Attention" description="Manageable class sizes so no student is just a roll number." />
          <Card icon="👩‍🏫" title="Experienced Faculty" description="Qualified, long-tenured teachers invested in every student's progress." />
          <Card icon="🛡️" title="Safe Campus" description="Secure premises with clear safety protocols parents can trust." />
          <Card icon="📈" title="Consistent Results" description="A steady track record of strong board results year after year." />
        </CardGrid>
      </section>

      <section style={{ padding: "48px 32px", background: "var(--navy-primary)", color: "#fff", textAlign: "center" }}>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: "24px", marginBottom: "12px" }}>
          Ready to join Kathwada High School?
        </h2>
        <p style={{ opacity: 0.8, maxWidth: "480px", margin: "0 auto 22px", fontSize: "14px" }}>
          Admissions for 2026–27 are open across all standards and streams. Start your application today.
        </p>
        <div style={{ display: "flex", gap: "12px", justifyContent: "center", flexWrap: "wrap" }}>
          <Link href="/admissions" style={{ background: "var(--gold)", color: "var(--navy-dark)", padding: "11px 22px", borderRadius: "6px", textDecoration: "none", fontSize: "14px", fontWeight: 600 }}>
            Start Admission
          </Link>
          <Link href="/contact" style={{ border: "1px solid rgba(255,255,255,0.5)", color: "#fff", padding: "11px 22px", borderRadius: "6px", textDecoration: "none", fontSize: "14px", fontWeight: 600 }}>
            Contact Us
          </Link>
        </div>
      </section>
    </main>
  );
}
