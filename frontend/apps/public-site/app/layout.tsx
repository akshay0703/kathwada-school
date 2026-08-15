import "@kathwada/ui/globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { SiteFooter } from "./SiteFooter";
import { SiteNav } from "./SiteNav";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "Kathwada High School",
  description:
    "Kathwada High School offers Secondary and Higher Secondary education (Std 9–12) in Kathwada, Ahmedabad, with a focus on academic rigour, character and modern learning.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <SiteNav />
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
