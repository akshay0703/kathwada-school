import type { Metadata } from "next";
import { Card, CardGrid, PageHero, Placeholder, Section } from "../_components";

export const metadata: Metadata = {
  title: "Admissions 2026–27 — Kathwada High School",
  description:
    "Admissions are open across Std 9–12 (Secondary and Higher Secondary, Arts & Commerce, Gujarati medium) at Kathwada High School. Process, required documents and FAQs.",
  alternates: { canonical: "/admissions" },
  openGraph: { title: "Admissions — Kathwada High School", url: "/admissions", type: "website" },
};

const DOCUMENTS = [
  { icon: "📄", title: "Birth Certificate", description: "Original + photocopy" },
  { icon: "📋", title: "Previous Marksheet", description: "Last academic year's report card" },
  { icon: "🔁", title: "Transfer Certificate", description: "If moving from another school" },
  { icon: "🖼️", title: "Passport Photos", description: "4 recent passport-size photos" },
  { icon: "🪪", title: "Aadhaar Card", description: "Student & parent, photocopy" },
  { icon: "🏠", title: "Address Proof", description: "Any valid government ID" },
  { icon: "🩺", title: "Medical Record", description: "Basic health & vaccination record" },
  { icon: "💳", title: "Caste Certificate", description: "If applicable, for reserved category" },
];

const FAQS = [
  {
    q: "What is the age/eligibility criteria for Std 9 admission?",
    a: "[PLACEHOLDER — add your school's exact eligibility policy here, typically based on having completed Std 8 at a recognised school]",
  },
  {
    q: "Is there an entrance test?",
    a: "[PLACEHOLDER — add details, e.g. a short interaction for younger grades, a basic assessment for Std 9 and above]",
  },
  {
    q: "What are the school timings?",
    a: "[PLACEHOLDER — add your actual timings, e.g. Std 9–10: 8:00 AM – 1:30 PM, Std 11–12: 8:00 AM – 2:00 PM]",
  },
  {
    q: "Do you provide transport?",
    a: "Yes — school transport covers key routes across Kathwada and nearby areas. [PLACEHOLDER — add route list and fees]",
  },
  {
    q: "Is the school Gujarati medium or English medium?",
    a: "Kathwada High School is a Gujarati-medium school across all standards, Std 9–12. English is taught as a subject throughout.",
  },
];

export default function AdmissionsPage() {
  return (
    <main>
      <PageHero
        eyebrow="Admissions 2026–27"
        title="Join Kathwada High School"
        description="Admissions are open across Std 9–12 — Secondary and Higher Secondary (Arts, Commerce), Gujarati medium. Here's everything you need to apply."
      />

      <Section eyebrow="Admission Process" title="Four simple steps">
        <CardGrid>
          <Card title="1. Submit an inquiry" description="Fill out the form on this page or visit the school office directly." />
          <Card title="2. Document verification" description="Our admissions team reviews the required documents (see list below)." />
          <Card title="3. Interaction / assessment" description="A short, friendly interaction with the student (and an entrance check for select standards)." />
          <Card title="4. Confirmation & fee payment" description="Once confirmed, complete the admission formalities and fee payment to secure the seat." />
        </CardGrid>
      </Section>

      <Section eyebrow="Required Documents" title="What to bring">
        <CardGrid>
          {DOCUMENTS.map((d) => (
            <Card key={d.title} icon={d.icon} title={d.title} description={d.description} />
          ))}
        </CardGrid>
      </Section>

      <Section title="Contact admissions">
        <p style={{ fontSize: "14px", color: "var(--ink)", marginBottom: "6px" }}>
          📞 <Placeholder>[PLACEHOLDER — school phone number]</Placeholder>
        </p>
        <p style={{ fontSize: "14px", color: "var(--ink)", marginBottom: "6px" }}>
          ✉️ <Placeholder>[PLACEHOLDER — admissions email address]</Placeholder>
        </p>
        <p style={{ fontSize: "14px", color: "var(--ink)" }}>🕘 Mon–Sat, 9:00 AM – 4:00 PM</p>
      </Section>

      <Section eyebrow="FAQs" title="Common questions from parents">
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {FAQS.map((f) => (
            <div key={f.q} style={{ borderBottom: "1px solid var(--line)", paddingBottom: "14px" }}>
              <h3 style={{ fontSize: "15px", color: "var(--navy-primary)", margin: "0 0 6px" }}>{f.q}</h3>
              <p style={{ fontSize: "13.5px", color: "var(--ink)", opacity: 0.8, margin: 0, lineHeight: 1.6 }}>{f.a}</p>
            </div>
          ))}
        </div>
      </Section>
    </main>
  );
}
