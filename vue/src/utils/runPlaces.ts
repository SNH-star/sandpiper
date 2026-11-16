// The places a set of runs was collected at, as the API's `lat_lons` gives them, turned into what a map needs.

/** One coordinate and the runs collected there, listed under their study's title. */
export interface RunPlace {
  lat_lon: [number, number]
  samples: Record<string, string[]>
}

export interface PlaceFeature {
  type: 'Feature'
  geometry: { type: 'Point', coordinates: [number, number] }
  /** `place` is the index into the list the feature was made from; `runs` is how many runs it holds. */
  properties: { place: number, runs: number }
}

export interface PlaceCollection {
  type: 'FeatureCollection'
  features: PlaceFeature[]
}

export interface StudyRuns {
  title: string
  runs: string[]
}

export interface RunsSummary {
  /** Runs in total, and the number of places they come from. */
  total: number
  places: number
  studies: StudyRuns[]
}

/** [[west, south], [east, north]] */
export type Bounds = [[number, number], [number, number]]

function runCount (place: RunPlace): number {
  return Object.values(place.samples).reduce((total, runs) => total + runs.length, 0)
}

function hasCoordinates (place: RunPlace): boolean {
  return Array.isArray(place.lat_lon) && Number.isFinite(place.lat_lon[0]) && Number.isFinite(place.lat_lon[1])
}

/** One point per place that has coordinates, carrying its index and its number of runs. */
export function placesToGeoJson (places: RunPlace[]): PlaceCollection {
  const features = places.flatMap((place, index): PlaceFeature[] => (hasCoordinates(place)
    ? [{
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [place.lat_lon[1], place.lat_lon[0]] },
        properties: { place: index, runs: runCount(place) }
      }]
    : []))
  return { type: 'FeatureCollection', features }
}

/** The runs of the places at `indexes`, with those of one study at several places listed together. */
export function runsAt (places: RunPlace[], indexes: number[]): RunsSummary {
  const chosen = indexes.map(index => places[index]).filter(Boolean)
  const byStudy = new Map<string, string[]>()
  chosen.forEach(place => Object.entries(place.samples).forEach(([title, runs]) => {
    byStudy.set(title, [...(byStudy.get(title) || []), ...runs])
  }))
  const studies = [...byStudy].map(([title, runs]) => ({ title, runs }))
  return { total: studies.reduce((total, study) => total + study.runs.length, 0), places: chosen.length, studies }
}

/** The box holding every place that has coordinates; null when there is none. */
export function boundsOf (places: RunPlace[]): Bounds | null {
  const located = places.filter(hasCoordinates)
  if (!located.length) return null
  const lats = located.map(place => place.lat_lon[0])
  const lons = located.map(place => place.lat_lon[1])
  return [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]]
}

/** "1 run", "1,204 runs". */
export function plural (count: number, noun: string): string {
  return `${count.toLocaleString('en-US')} ${noun}${count === 1 ? '' : 's'}`
}

/** A place drawn on a flat map: its index, its number of runs, and where it falls on the map. */
export interface PlacePoint {
  place: number
  runs: number
  x: number
  y: number
}

/** One marker: a place on its own, or several places too close together to tell apart. */
export interface PlaceMarker {
  key: string
  x: number
  y: number
  runs: number
  places: number[]
}

/**
 * Gathers the places within `radius` of each other under one marker, as the globe does. The places with the
 * most runs are taken first, each with every place not yet taken within `radius` of it; the marker sits at
 * the middle of its places, weighted by their runs.
 */
export function mergePlaces (points: PlacePoint[], radius: number): PlaceMarker[] {
  const waiting = [...points].sort((a, b) => b.runs - a.runs || a.place - b.place)
  const markers: PlaceMarker[] = []
  while (waiting.length) {
    const centre = waiting[0]
    const isNear = (point: PlacePoint) => Math.hypot(point.x - centre.x, point.y - centre.y) <= radius
    const group = waiting.filter(isNear)
    waiting.splice(0, waiting.length, ...waiting.filter(point => !isNear(point)))
    const runs = group.reduce((total, point) => total + point.runs, 0)
    // A place with no runs still counts towards the middle, so the weights never sum to nothing.
    const weight = (point: PlacePoint) => (runs > 0 ? point.runs / runs : 1 / group.length)
    markers.push({
      key: `${centre.place}:${group.length}`,
      x: group.reduce((sum, point) => sum + point.x * weight(point), 0),
      y: group.reduce((sum, point) => sum + point.y * weight(point), 0),
      runs,
      places: group.map(point => point.place)
    })
  }
  return markers
}
