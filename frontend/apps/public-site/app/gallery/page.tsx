import type { Metadata } from "next";
import { Card, CardGrid, PageHero, Section } from "../_components";

export const metadata: Metadata = {
  title: "Gallery — Kathwada High School",
  description: "Photos and events from life at Kathwada High School.",
  alternates: { canonical: "/gallery" },
  openGraph: { title: "Gallery — Kathwada High School", url: "/gallery", type: "website" },
};

export default function GalleryPage() {
  return (
    <main>
      <PageHero eyebrow="Gallery" title="Life at Kathwada High School" description="Moments from our classrooms, events and celebrations." />

      <Section title="Photos">
        <p style={{ fontSize: "13px", color: "var(--ink)", opacity: 0.6, marginBottom: "16px" }}>
          [PLACEHOLDER — replace the tiles below with real campus, classroom and event photography]
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "12px" }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} style={{ aspectRatio: "4/3", background: "var(--line)", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--ink)", opacity: 0.4, fontSize: "13px" }}>
              Photo
            </div>
          ))}
        </div>
      </Section>

      <Section title="Videos">
        <p style={{ fontSize: "13px", color: "var(--ink)", opacity: 0.6, marginBottom: "16px" }}>
          [PLACEHOLDER — embed real video links (YouTube/Vimeo) once available]
        </p>
      </Section>

      <Section title="Events">
        <CardGrid>
          <Card title="Annual Day 2026" description="Performances, prize distribution and celebration. [Date to confirm]" />
          <Card title="Sports Day" description="Inter-house athletics and team events. [Date to confirm]" />
          <Card title="Science Exhibition" description="Student projects across Physics, Chemistry and Biology. [Date to confirm]" />
        </CardGrid>
      </Section>
    </main>
  );
}
