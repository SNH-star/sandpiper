// When each Sandpiper version was released, read from the changelog on the About page.
import { CHANGELOG } from '@/views/About.vue'

const MONTH_YEAR = new Intl.DateTimeFormat('en-GB', { month: 'long', year: 'numeric', timeZone: 'UTC' })
const RANGE_SEPARATOR = ' to '
// A name ending in either of these stands for every release of its series: '2.1.x', 'v1.1.*'.
const WILDCARDS = ['x', '*']
const MONTH_ONLY_LENGTH = 'YYYY-MM'.length

const bare = version => version.replace(/^v/, '')
// The part of a wildcard name every release of the series starts with ('1.1.' for 'v1.1.*'); null otherwise.
const seriesPrefix = name => (WILDCARDS.some(mark => name.endsWith(mark)) ? name.slice(0, -1) : null)

// A 'YYYY-MM-DD' or 'YYYY-MM' date as "July 2026"; null when there is no date.
export function monthYear (date) {
  if (!date) return null
  const day = date.length === MONTH_ONLY_LENGTH ? `${date}-01` : date
  return MONTH_YEAR.format(new Date(`${day}T00:00:00Z`))
}

// Whether two version names are the same release, or one is a series the other belongs to.
function sameRelease (a, b) {
  const [prefixA, prefixB] = [seriesPrefix(a), seriesPrefix(b)]
  if (prefixA !== null) return b.startsWith(prefixA)
  if (prefixB !== null) return a.startsWith(prefixB)
  return a === b
}

// The changelog date of a version such as '2.1.1', 'v2.1.1' or '2.1.x' (any release of 2.1). An entry named
// as a series ('v1.1.*') dates every release in it. Null when the changelog has no dated entry for it.
function releaseDate (version) {
  const entry = CHANGELOG.find(item => item.date && sameRelease(bare(version), bare(item.version || item.heading)))
  return entry ? entry.date : null
}

// The release month of a version label, or of both ends of a label such as '2.0.0 to 2.1.x'
// ("May 2026 to July 2026"). Null when any part has no date in the changelog.
export function releasedLabel (label) {
  const months = label.split(RANGE_SEPARATOR).map(part => monthYear(releaseDate(part)))
  if (months.includes(null)) return null
  return [...new Set(months)].join(RANGE_SEPARATOR)
}
