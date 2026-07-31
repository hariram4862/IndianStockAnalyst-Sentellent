export function formatInr(value: number | null): string {
  if (value == null) return "N/A"
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatPercent(value: number | null): string {
  if (value == null) return "N/A"
  return `${value.toFixed(2)}%`
}

/** Large rupee figures (market cap) in crores, the convention Indian
 * equity research uses -- "Rs. 2,01,50,000.00" is unreadable at a glance,
 * "Rs. 20,15,000 Cr" isn't. */
export function formatInrCrores(value: number | null): string {
  if (value == null) return "N/A"
  const crores = value / 1e7
  return `${new Intl.NumberFormat("en-IN", { maximumFractionDigits: crores >= 100 ? 0 : 2 }).format(crores)} Cr`
}

export function initialsFromName(name?: string): string {
  if (!name) return "?"
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("")
}

export function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diffMs / 60000)
  if (minutes < 1) return "just now"
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return new Date(iso).toLocaleDateString()
}
