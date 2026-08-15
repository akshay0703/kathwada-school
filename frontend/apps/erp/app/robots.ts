import type { MetadataRoute } from "next";

export const dynamic = "force-static";

// Blocks every crawler from every path in the ERP app. There is no
// legitimate reason for this app to appear in search results — it's an
// authenticated portal, not public content. See docs/deployment.md.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      disallow: "/",
    },
  };
}
