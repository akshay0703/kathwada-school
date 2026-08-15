"use client";

import { api, type CurrentUser } from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => router.replace("/login"))
      .finally(() => setChecking(false));
  }, [router]);

  async function handleLogout() {
    await api.logout();
    router.replace("/login");
  }

  if (checking) return null; // avoid a flash of protected content before the auth check resolves

  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body)" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid var(--line)",
          paddingBottom: "16px",
          marginBottom: "24px",
        }}
      >
        <h1 style={{ color: "var(--navy-primary)", fontSize: "22px" }}>Kathwada High School — ERP</h1>
        <Button variant="secondary" onClick={handleLogout}>
          Sign out
        </Button>
      </header>

      <p>
        Signed in as <strong>{user?.email}</strong> — role: <strong>{user?.role ?? "(none assigned)"}</strong>
      </p>
      <p style={{ color: "var(--ink)", opacity: 0.7, fontSize: "14px" }}>
        This is the Phase 0 dashboard shell. Students, Marks, Attendance, Fees, Library, and Report Card
        modules are built in Phase 1 per the approved architecture.
      </p>
    </main>
  );
}
