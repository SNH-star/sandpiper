// Only explicit habitat labels are compared; ambiguous organism names are omitted. The labels are the strings of
// Table S4 of the IndicPiper paper (its exact habitat search strings); next release, read IndicPiper's own mapping.
// The same file is read by backend/bin/summarise_groups.py to group runs by habitat.
import habitatLabels from '@/constants/indicpiperHabitats.json'

const recordedHabitats = new Map(Object.entries(habitatLabels))

// The organism labels recorded as a habitat, without the trailing " metagenome": marine water -> "marine, seawater".
export function indicpiperHabitatLabels(habitat) {
  return Object.entries(habitatLabels)
    .filter(([, mapped]) => mapped === habitat)
    .map(([label]) => label.replace(/ metagenome$/, ''))
}

function canonicalOrganism(organism) {
  return organism.toLowerCase().replace(/_/g, ' ')
    .replace(/\s+/g, ' ').trim().replace(/(metagenome).*$/, '$1')
}

// The organism label when it names no habitat IndicPiper was built from, else
// null. A missing label is not a label, so it gives no warning.
export function indicpiperUncoveredOrganism(organism) {
  if (typeof organism !== 'string') return null
  const canonical = canonicalOrganism(organism)
  if (!canonical || canonical === 'unspecified') return null
  return recordedHabitats.has(canonical) ? null : canonical
}

export function indicpiperMismatch(organism, habitats = []) {
  if (typeof organism !== 'string') return null
  const canonical = canonicalOrganism(organism)
  const expectedHabitat = recordedHabitats.get(canonical)
  if (!expectedHabitat) return null
  const scored = habitats.filter(h => Number.isFinite(h.score) && h.score > 0)
  if (!scored.length) return null
  const top = scored.reduce((best, h) => h.score > best.score ? h : best)
  // Agreement tied for the highest score is not a discrepancy.
  if (scored.some(h => h.k === expectedHabitat && h.score === top.score)) return null
  return { organism, expectedHabitat, top }
}

export function formatIndicPiperPercent(fraction) {
  if (!Number.isFinite(fraction) || fraction < 0) return '—'
  if (fraction > 0 && fraction < 0.0001) return '<0.01%'
  return `${(fraction * 100).toFixed(2)}%`
}
