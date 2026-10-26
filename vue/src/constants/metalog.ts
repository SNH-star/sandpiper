// Fallback Metalog release facts, used only when the API does not supply them.
//
// The live values come from the API (`metalog_release` on /sandpiper_stats and
// on each run's metadata), scraped from https://metalog.embl.de/ at fetch time
// by metalog_custom/scripts/fetch_metalog.py and carried into the database with
// the rest of the Metalog provenance. Databases built before that existed -- or
// a build where the site was unreachable -- carry no release block, and these
// values stand in.
//
// They are Metalog's own published numbers, not counts derived from the
// downloaded files: the extended-wide files only cover samples that carry
// extended metadata, so their row counts are legitimately lower.
export const METALOG_LAST_UPDATE = '2026-08-21'

export const METALOG_SAMPLE_COUNTS = {
  human: 114861,
  animal: 11243,
  ocean: 6062,
  environmental: 27122,
  total: 159288
}

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
]

/**
 * An ISO date as "21 August 2026", matching how the run page writes dates in
 * prose. Split by hand rather than parsed with Date, which reads a bare ISO
 * date as UTC and so shows the previous day for anyone west of UTC. Returns
 * the input unchanged if it isn't a plain ISO date.
 */
export function metalogLongDate (iso: string): string {
  const parts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '')
  if (!parts) return iso
  const [, year, month, day] = parts
  return `${Number(day)} ${MONTHS[Number(month) - 1]} ${year}`
}

/** Thousands-separated, matching how the About page has always written these. */
export function metalogCount (value: number | null | undefined): string {
  return typeof value === 'number' ? value.toLocaleString('en-US') : '—'
}
