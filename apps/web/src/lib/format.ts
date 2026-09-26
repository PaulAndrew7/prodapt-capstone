const dateFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });
const timeFmt = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit" });

export function formatDate(iso: string) {
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  return Number.isNaN(d.getTime()) ? iso : dateFmt.format(d);
}

export function formatTime(iso: string) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : timeFmt.format(d);
}

export function relativeDay(iso: string, now = new Date()) {
  const d = new Date(iso);
  const startOf = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const days = Math.round((startOf(now) - startOf(d)) / 86_400_000);
  if (days <= 0) return `Today, ${formatTime(iso)}`;
  if (days === 1) return "Yesterday";
  return formatDate(iso);
}

export function todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
