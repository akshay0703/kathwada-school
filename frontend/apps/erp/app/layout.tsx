import "@kathwada/ui/globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "Kathwada High School — ERP",
  description: "Staff/teacher/student portal for Kathwada High School.",
  // This app must never appear in search results — it's an authenticated
  // portal to student records, not public content. See docs/deployment.md
  // "Static ERP security" section for the full defense (this is layer 1 of
  // 3: noindex meta tag, robots.txt disallow, and an X-Robots-Tag header).
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: { index: false, follow: false },
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
