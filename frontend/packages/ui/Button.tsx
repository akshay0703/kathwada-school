import type { ButtonHTMLAttributes } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
};

export function Button({ variant = "primary", style, ...props }: ButtonProps) {
  const base: React.CSSProperties = {
    fontFamily: "var(--font-body)",
    fontWeight: 600,
    fontSize: "14px",
    padding: "10px 18px",
    borderRadius: "6px",
    border: "1px solid transparent",
    cursor: "pointer",
  };

  const variants: Record<string, React.CSSProperties> = {
    primary: {
      background: "var(--navy-primary)",
      color: "#fff",
    },
    secondary: {
      background: "transparent",
      color: "var(--navy-primary)",
      borderColor: "var(--navy-primary)",
    },
  };

  return <button {...props} style={{ ...base, ...variants[variant], ...style }} />;
}
