import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link, type LinkProps } from "react-router";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

const base =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-full font-semibold transition " +
  "disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-3";

const variants: Record<Variant, string> = {
  // DESIGN.md: text on --academy-primary is computed (dark on #00BF63), never hard-coded white.
  primary: "bg-primary text-on-primary hover:brightness-95 active:brightness-90 shadow-soft",
  secondary: "border-2 border-secondary bg-surface text-link hover:bg-primary/10",
  ghost: "text-link hover:bg-primary/10",
  danger: "bg-danger text-white hover:brightness-110",
};

const sizes: Record<Size, string> = {
  sm: "min-h-9 px-3 text-sm",
  md: "px-5 text-[0.95rem]",
  lg: "px-7 text-base",
};

export function buttonClasses(variant: Variant = "primary", size: Size = "md", extra = ""): string {
  return `${base} ${variants[variant]} ${sizes[size]} ${extra}`.trim();
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
}

export function Button({ variant = "primary", size = "md", loading = false, icon, className = "", children,
  disabled, type = "button", ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={buttonClasses(variant, size, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? <span className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" /> : icon}
      {children}
    </button>
  );
}

interface ButtonLinkProps extends LinkProps {
  variant?: Variant;
  size?: Size;
  icon?: ReactNode;
}

export function ButtonLink({ variant = "primary", size = "md", icon, className = "", children, ...props }: ButtonLinkProps) {
  return (
    <Link className={buttonClasses(variant, size, `no-underline ${className}`)} {...props}>
      {icon}
      {children}
    </Link>
  );
}
