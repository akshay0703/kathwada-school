import type { Metadata } from "next";
import { Card, CardGrid, PageHero, Section } from "../_components";

export const metadata: Metadata = {
  title: "About Us — Kathwada High School",
  description:
    "The history, mission and people behind Kathwada High School — a Secondary and Higher Secondary school in Kathwada, Ahmedabad.",
  alternates: { canonical: "/about" },
  openGraph: { title: "About Kathwada High School", url: "/about", type: "website" },
};

export default function AboutPage() {
  return (
    <main>
      <PageHero
        eyebrow="About Us"
        title="A school built around every child's potential"
        description="Our story, what we stand for, and the people and places behind it."
      />

      <Section eyebrow="Our History" title="How Kathwada High School came to be">
        <p style={{ color: "var(--ink)", opacity: 0.8, lineHeight: 1.7, fontSize: "14.5px", marginBottom: "24px" }}>
          Founded with a simple goal — to give children in Kathwada access to quality education without having
          to travel far from home — the school has grown steadily in reputation, results and reach over the
          years.
        </p>
        <CardGrid>
          <Card title="1975 — School founded" description="Began as a Secondary school starting with Std 9, with a commitment to academic discipline from day one." />
          <Card title="[Year to confirm] — First board batch" description="Our first Std 10 batch appeared for the board examination." />
          <Card title="[Year to confirm] — Higher Secondary added" description="Introduced Arts and Commerce streams for Std 11–12." />
          <Card title="Today" description="A growing community — now home to over a thousand students across Std 9–12, including Arts and Commerce streams." />
        </CardGrid>
      </Section>

      <Section title="Vision & Mission">
        <CardGrid>
          <Card
            icon="🔭"
            title="Our Vision"
            description="To be a school where every child discovers their strengths, builds real character, and leaves prepared — academically and personally — for whatever path they choose."
          />
          <Card
            icon="🧭"
            title="Our Mission"
            description="To deliver a rigorous, well-rounded education through dedicated teachers, modern facilities and a safe, disciplined environment — while treating every student as an individual, not a number."
          />
        </CardGrid>
      </Section>

      <Section eyebrow="Management" title="The people guiding Kathwada High School">
        <p style={{ fontSize: "13px", color: "var(--ink)", opacity: 0.6, marginBottom: "16px" }}>
          Names and photos below are placeholders in the source content — replace with real names/titles.
        </p>
        <CardGrid>
          <Card title="[PLACEHOLDER — name]" description="Chairman, Managing Trust" />
          <Card title="[PLACEHOLDER — name]" description="Principal" />
          <Card title="[PLACEHOLDER — name]" description="Vice Principal" />
          <Card title="[PLACEHOLDER — name]" description="Academic Coordinator" />
        </CardGrid>
      </Section>

      <Section eyebrow="Infrastructure" title="A campus designed for learning">
        <CardGrid>
          <Card title="Classrooms" description="Spacious, well-lit classrooms across Std 9–12." />
          <Card title="Science Labs" description="Dedicated Physics, Chemistry and Biology laboratories." />
          <Card title="Library" description="A quiet, spacious library with a growing collection." />
        </CardGrid>
      </Section>
    </main>
  );
}
