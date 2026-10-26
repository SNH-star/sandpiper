// Only explicit habitat labels are compared; ambiguous organism names are omitted.
const recordedHabitats = new Map(Object.entries({
  'soil metagenome': 'soil',
  'wastewater metagenome': 'wastewater',
  'human oral metagenome': 'human oral',
  'human saliva metagenome': 'human oral',
  'human skin metagenome': 'human skin',
  'human vaginal metagenome': 'human vaginal',
  'marine sediment metagenome': 'marine sediment',
  'glacier metagenome': 'glacier',
  'hydrothermal vent metagenome': 'hydrothermal vent',
  'freshwater sediment metagenome': 'freshwater sediment',
  'freshwater metagenome': 'freshwater water',
  'freshwater water metagenome': 'freshwater water',
  'phyllosphere metagenome': 'phyllosphere',
  'rhizosphere metagenome': 'soil',
  ...Object.fromEntries(['human', 'pig', 'bovine', 'sheep', 'canine', 'goat', 'mammalian']
    .map(host => [`${host} gut metagenome`, 'mammalian gut'])),
}))

export function indicpiperMismatch(organism, habitats = []) {
  if (typeof organism !== 'string') return null
  const canonical = organism.toLowerCase().replace(/_/g, ' ')
    .replace(/\s+/g, ' ').trim().replace(/(metagenome).*$/, '$1')
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
