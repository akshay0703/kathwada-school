import type { Metadata } from "next";
import { Card, CardGrid, PageHero, Section } from "../_components";

export const metadata: Metadata = {
  title: "Academics — Kathwada High School",
  description:
    "Secondary (Std 9–10) and Higher Secondary (Std 11–12, Arts & Commerce) academics at Kathwada High School — curriculum, streams and subjects.",
  alternates: { canonical: "/academics" },
  openGraph: { title: "Academics — Kathwada High School", url: "/academics", type: "website" },
};

const CORE_SUBJECTS = ["Gujarati", "English", "Mathematics", "Science", "Social Science", "Sanskrit / Computer"];

export default function AcademicsPage() {
  return (
    <main>
      <PageHero
        eyebrow="Academics"
        title="A clear academic path from Std 9 to Std 12"
        description="Structured stages, a strong curriculum, and streams that let students specialise when they're ready."
      />

      <Section title="Two stages">
        <CardGrid>
          <Card icon="📖" title="Secondary (Std 9–10)" description="A structured, subject-wise curriculum that builds depth and exam readiness, leading up to the Std 10 board examination." />
          <Card icon="🎓" title="Higher Secondary (Std 11–12)" description="Specialised Arts and Commerce streams that prepare students for board exams, entrance tests and beyond." />
        </CardGrid>
      </Section>

      <Section eyebrow="Higher Secondary Streams" title="Choose a path that fits where you're headed">
        <CardGrid>
          <Card title="Commerce" description="For students interested in business, finance and economics — Accounting, Statistics, Business Administration, Economics, English, Gujarati, Geography." />
          <Card title="Arts" description="For students drawn to the humanities, languages and social sciences — Psychology, Philosophy, Hindi, Economics, English, Gujarati, Geography." />
        </CardGrid>
      </Section>

      <Section eyebrow="Curriculum" title="Structured, board-aligned, and assessment-ready">
        <p style={{ color: "var(--ink)", opacity: 0.8, lineHeight: 1.7, fontSize: "14.5px", marginBottom: "24px" }}>
          Our academic calendar is built around continuous assessment rather than a single high-stakes exam —
          so students build steadily toward the board exam instead of cramming for it.
        </p>
        <CardGrid>
          <Card title="1. First School Test" description="Early checkpoint to gauge understanding of foundational topics." />
          <Card title="2. Second School Test" description="Follow-up assessment covering the next block of syllabus." />
          <Card title="3. Unit Test 1 & Unit Test 2" description="Broader tests covering multiple units, building exam stamina." />
          <Card title="4. Main Examination" description="Comprehensive term/annual exam aligned with board patterns." />
        </CardGrid>
      </Section>

      <Section eyebrow="Subjects" title="Std 9–10 core subjects">
        <CardGrid>
          {CORE_SUBJECTS.map((subject) => (
            <Card key={subject} title={subject} description="" />
          ))}
        </CardGrid>
      </Section>
    </main>
  );
}
