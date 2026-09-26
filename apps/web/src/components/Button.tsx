import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { Link, type LinkProps } from "react-router";
import clsx from "clsx";

type Variant = "primary" | "mark" | "outline" | "ghost";
type Size = "sm" | "md" | "lg" | "icon";

const base =
  "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap font-semibold select-none " +
  "transition-[transform,background-color,color,opacity] duration-150 ease-out " +
  "active:translate-y-px disabled:cursor-not-allowed disabled:opacity-45 disabled:active:translate-y-0";

const variants: Record<Variant, string> = {
  primary: "bg-ink text-paper hover:bg-ink/88",
  mark: "bg-mark text-on-mark hover:bg-ink hover:text-paper",
  outline: "border-2 border-ink text-ink hover:bg-ink hover:text-paper",
  ghost: "text-ink underline-offset-4 hover:underline",
};

const sizes: Record<Size, string> = {
  sm: "h-9 px-3 text-sm",
  md: "h-11 px-5 text-[0.95rem]",
  lg: "h-14 px-7 text-base",
  icon: "size-12 p-0",
};

export function buttonClass(variant: Variant = "primary", size: Size = "md", className?: string) {
  return clsx(base, variants[variant], sizes[size], variant === "ghost" && "px-1", className);
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading, icon, className, children, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      className={buttonClass(variant, size, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <span aria-hidden className="size-3 animate-pulse bg-current" /> : icon}
      {children}
    </button>
  );
});

export function ButtonLink({
  variant = "primary",
  size = "md",
  className,
  icon,
  children,
  ...rest
}: LinkProps & { variant?: Variant; size?: Size; icon?: ReactNode }) {
  return (
    <Link className={buttonClass(variant, size, className)} {...rest}>
      {icon}
      {children}
    </Link>
  );
}
