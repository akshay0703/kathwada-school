import type { Metadata } from "next";
import { Card, CardGrid, PageHero, Placeholder, Section } from "../_components";

export const metadata: Metadata = {
  title: "Contact — Kathwada High School",
  description: "Get in touch with Kathwada High School — phone, email, and office hours.",
  alternates: { canonical: "/contact" },
  openGraph: { title: "Contact — Kathwada High School", url: "/contact", type: "website" },
};

export default function ContactPage() {
  return (
    <main>
      <PageHero
        eyebrow="Contact"
        title="We'd love to hear from you"
        description="Questions about admissions, academics or anything else — reach out any way that's convenient."
      />

      <Section title="Get in touch">
        <CardGrid>
          <Card icon="📞" title="Call Us" description="[PLACEHOLDER — school phone number]" />
          <Card icon="✉️" title="Email" description="[PLACEHOLDER — school email address]" />
          <Card icon="📍" title="Visit Us" description="Kathwada, Ahmedabad, Gujarat" />
        </CardGrid>
      </Section>

      <Section title="Office Hours">
        <p style={{ fontSize: "14px", color: "var(--ink)", marginBottom: "4px" }}>Monday – Saturday: 9:00 AM – 4:00 PM</p>
        <p style={{ fontSize: "14px", color: "var(--ink)" }}>Sunday &amp; public holidays: Closed</p>
      </Section>

      <Section title="Find us">
        <div
          style={{
            border: "1px dashed var(--line-strong)",
            borderRadius: "10px",
            padding: "32px",
            textAlign: "center",
            color: "var(--ink)",
            opacity: 0.6,
            fontSize: "13px",
          }}
        >
          <Placeholder>
            [PLACEHOLDER — embed the school&apos;s actual campus location here (Google Maps → Share → Embed a map)]
          </Placeholder>
        </div>
      </Section>
    </main>
  );
}
