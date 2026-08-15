"use client";

import { api } from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.login(email, password);
      router.push("/dashboard");
    } catch {
      // Deliberately generic — never reveal whether the email exists.
      setError("Invalid email or password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg)",
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          background: "var(--paper)",
          border: "1px solid var(--line)",
          borderRadius: "10px",
          padding: "32px",
          width: "340px",
          boxShadow: "0 4px 16px rgba(20,33,61,0.08)",
        }}
      >
        <h1 style={{ fontSize: "20px", marginBottom: "4px", color: "var(--navy-primary)" }}>
          Kathwada High School
        </h1>
        <p style={{ fontSize: "13px", color: "var(--ink)", opacity: 0.7, marginTop: 0, marginBottom: "24px" }}>
          ERP sign in
        </p>

        <label style={{ fontSize: "13px", display: "block", marginBottom: "6px" }}>Email</label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{
            width: "100%",
            padding: "9px 10px",
            marginBottom: "14px",
            borderRadius: "6px",
            border: "1px solid var(--line-strong)",
          }}
        />

        <label style={{ fontSize: "13px", display: "block", marginBottom: "6px" }}>Password</label>
        <input
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{
            width: "100%",
            padding: "9px 10px",
            marginBottom: "18px",
            borderRadius: "6px",
            border: "1px solid var(--line-strong)",
          }}
        />

        {error && (
          <p role="alert" style={{ color: "var(--red)", fontSize: "13px", marginBottom: "14px" }}>
            {error}
          </p>
        )}

        <Button type="submit" disabled={loading} style={{ width: "100%" }}>
          {loading ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </main>
  );
}
