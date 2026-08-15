import type { Metadata } from "next";
import { Card, CardGrid, PageHero, Section } from "../_components";

export const metadata: Metadata = {
  title: "News & Events — Kathwada High School",
  description: "Announcements, circulars, celebrations and achievements from Kathwada High School.",
  alternates: { canonical: "/news" },
  openGraph: { title: "News & Events — Kathwada High School", url: "/news", type: "website" },
};

export default function NewsPage() {
  return (
    <main>
      <PageHero eyebrow="News & Events" title="Stay up to date with the school" description="Announcements, circulars, celebrations and achievements — all in one place." />

      <Section eyebrow="Announcements" title="Latest updates">
        <CardGrid>
          <Card title="Admissions open for 2026–27" description="Applications now open across Std 9–12, including Arts and Commerce streams. [Date to confirm]" />
          <Card title="Revised school timings from next term" description="Please note the updated timings for Std 9–10 and Std 11–12 sections. [Date to confirm]" />
          <Card title="Std 10 & 12 board result announcement" description="Congratulations to our students on another year of strong results. [Date to confirm]" />
        </CardGrid>
      </Section>

      <Section eyebrow="Circulars" title="Notices for parents & students">
        <p style={{ fontSize: "13px", color: "var(--ink)", opacity: 0.6, marginBottom: "16px" }}>
          [PLACEHOLDER — link these to real PDF circulars once available]
        </p>
        <CardGrid>
          <Card icon="📄" title="Parent-Teacher Meeting schedule" description="Std 6–10, Main Auditorium — full schedule" />
          <Card icon="📄" title="Uniform & ID card guidelines" description="Updated dress code and ID policy for the new term" />
          <Card icon="📄" title="Fee payment deadline reminder" description="Last date for term fee payment without late charges" />
        </CardGrid>
      </Section>

      <Section eyebrow="Achievements" title="Moments we're proud of">
        <CardGrid>
          <Card icon="🏆" title="District Science Fair — 1st Place" description="Std 10 student project recognised for innovation." />
          <Card icon="🥇" title="Inter-School Athletics Champions" description="Our team brought home the overall trophy this season." />
          <Card icon="🎼" title="State-level Elocution Winner" description="Std 8 student secured first place at the state competition." />
        </CardGrid>
      </Section>
    </main>
  );
}
