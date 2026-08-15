"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

// Static-export-safe redirect: this app has no server at runtime (see
// next.config.js), so the redirect happens client-side on load, the same
// pattern the dashboard page already uses for its own auth check.
export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/login");
  }, [router]);

  return null;
}
