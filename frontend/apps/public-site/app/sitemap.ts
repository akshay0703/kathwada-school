import type { MetadataRoute } from "next";

export const dynamic = "force-static";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

// Only public marketing routes belong here. The ERP is a completely separate
// Next.js app/deployment (see docs/architecture.md) — it has no route in
// this app's router at all, so there is no way for it to end up in this
// sitemap by accident. Its own exclusion (robots.ts, noindex metadata,
// X-Robots-Tag) lives in frontend/apps/erp/.
const PUBLIC_ROUTES = ["", "/about", "/academics", "/admissions", "/gallery", "/news", "/contact"];

export default function sitemap(): MetadataRoute.Sitemap {
  return PUBLIC_ROUTES.map((route) => ({
    url: `${SITE_URL}${route}`,
    lastModified: new Date(),
  }));
}
