// Datumshilfen: Fachzeit Europe/Berlin, Wochen beginnen am Montag.

export const WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"];
export const WEEKDAYS_SHORT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];

export function todayBerlin(): string {
  // en-CA liefert YYYY-MM-DD
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Berlin" }).format(new Date());
}

function parse(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

function fmt(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function mondayOf(iso: string): string {
  const d = parse(iso);
  const wd = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - wd);
  return fmt(d);
}

export function addDays(iso: string, days: number): string {
  const d = parse(iso);
  d.setUTCDate(d.getUTCDate() + days);
  return fmt(d);
}

export function formatDate(iso: string, withYear = true): string {
  const d = parse(iso);
  return new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit", ...(withYear ? { year: "numeric" } : {}), timeZone: "UTC" }).format(d);
}

export function formatRange(start: string, end: string): string {
  return `${formatDate(start, false)}–${formatDate(end)}`;
}

export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat("de-DE", { dateStyle: "short", timeStyle: "short", timeZone: "Europe/Berlin" }).format(new Date(iso));
}

export const STATUS_LABEL: Record<string, string> = {
  planned: "Geplant",
  started: "Begonnen",
  completed: "Abgeschlossen",
};

export const STATUS_ICON: Record<string, string> = {
  planned: "○",
  started: "◐",
  completed: "●",
};

export function bytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function cls(...names: (string | false | null | undefined)[]): string {
  return names.filter(Boolean).join(" ");
}
