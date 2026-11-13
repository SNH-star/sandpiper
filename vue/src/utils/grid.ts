// The `grid:` search value: semicolon-separated "latitude/longitude[/type]"
// corners of the map's squares, e.g. "10/-60/host;15/-60/ecological" (see
// backend/api/grid.py). The type says which sample type that square searches.

export type SampleEnvironment = 'host' | 'ecological'
export type Corner = [number, number, SampleEnvironment?]
export type MapView = 'host_associated' | 'ecological'

export const ENVIRONMENT_FOR_VIEW: Record<MapView, SampleEnvironment> = {
  host_associated: 'host',
  ecological: 'ecological'
}

function isEnvironment (text: string | undefined): text is SampleEnvironment {
  return text === 'host' || text === 'ecological'
}

function sameCorner (a: Corner, b: Corner): boolean {
  return a[0] === b[0] && a[1] === b[1] && a[2] === b[2]
}

/** '10/-60/host;15/-60' -> [[10, -60, 'host'], [15, -60]]; malformed pieces are skipped. */
export function parseGrid (text: string): Corner[] {
  const corners: Corner[] = []
  for (const piece of (text || '').split(';')) {
    const [lat, lon, type, extra] = piece.trim().split('/')
    if (!lat || !lon || extra !== undefined) continue
    if (type !== undefined && !isEnvironment(type)) continue
    const corner: Corner = type === undefined ? [Number(lat), Number(lon)] : [Number(lat), Number(lon), type]
    if (Number.isInteger(corner[0]) && Number.isInteger(corner[1]) && !corners.some(c => sameCorner(c, corner))) {
      corners.push(corner)
    }
  }
  return corners
}

export function formatGrid (corners: Corner[]): string {
  return corners.map(([lat, lon, type]) => (type ? `${lat}/${lon}/${type}` : `${lat}/${lon}`)).join(';')
}

/** The squares after clicking circle `key` ("lat:lon") while `view` is showing:
 *  picks a square for that view's sample type, or drops it if already picked.
 *  Squares picked under the other view are kept. */
export function toggleCorner (corners: Corner[], key: string, view: MapView): Corner[] {
  const [lat, lon] = key.split(':').map(Number)
  const clicked: Corner = [lat, lon, ENVIRONMENT_FOR_VIEW[view]]
  return corners.some(c => sameCorner(c, clicked))
    ? corners.filter(c => !sameCorner(c, clicked))
    : [...corners, clicked]
}

/** Keys ("lat:lon") of the squares to mark on `view`: those picked under its
 *  sample type, plus any untyped square (it searches both types). */
export function chosenKeys (corners: Corner[], view: MapView): string[] {
  return corners
    .filter(([, , type]) => !type || type === ENVIRONMENT_FOR_VIEW[view])
    .map(([lat, lon]) => `${lat}:${lon}`)
}

// --- Hexagons ---
// A piece written "h<latitude>/<longitude>/<type>" picks one hexagon of the statistics map by its centre,
// as the map gives it (three decimals). Squares and hexagons can share one `grid:` value.

const HEX_PREFIX = 'h'

/** A picked hexagon: its centre's latitude and longitude, and the sample type it searches. */
export type Hex = [number, number, SampleEnvironment]

function sameHex (a: Hex, b: Hex): boolean {
  return a[0] === b[0] && a[1] === b[1] && a[2] === b[2]
}

/** 'h51.962/-2/host;10/-60' -> [[51.962, -2, 'host']]; squares and malformed pieces are skipped. */
export function parseHexes (text: string): Hex[] {
  const hexes: Hex[] = []
  for (const piece of (text || '').split(';')) {
    const trimmed = piece.trim()
    if (!trimmed.startsWith(HEX_PREFIX)) continue
    const [lat, lon, type, extra] = trimmed.slice(HEX_PREFIX.length).split('/')
    if (!lat || !lon || extra !== undefined || !isEnvironment(type)) continue
    const hex: Hex = [Number(lat), Number(lon), type]
    if (Number.isFinite(hex[0]) && Number.isFinite(hex[1]) && !hexes.some(h => sameHex(h, hex))) hexes.push(hex)
  }
  return hexes
}

/** The whole `grid:` value: any squares first, then the hexagons. */
export function formatPicks (corners: Corner[], hexes: Hex[]): string {
  const pieces = hexes.map(([lat, lon, type]) => `${HEX_PREFIX}${lat}/${lon}/${type}`)
  return [formatGrid(corners), ...pieces].filter(Boolean).join(';')
}

/** The hexagons after clicking hexagon `key` ("lat:lon") while `view` is showing: picks it for that
 *  view's sample type, or drops it if already picked. Hexagons picked under the other view are kept. */
export function toggleHex (hexes: Hex[], key: string, view: MapView): Hex[] {
  const [lat, lon] = key.split(':').map(Number)
  const clicked: Hex = [lat, lon, ENVIRONMENT_FOR_VIEW[view]]
  return hexes.some(h => sameHex(h, clicked)) ? hexes.filter(h => !sameHex(h, clicked)) : [...hexes, clicked]
}

/** Keys ("lat:lon") of the hexagons to mark on `view`: those picked under its sample type. */
export function chosenHexKeys (hexes: Hex[], view: MapView): string[] {
  return hexes.filter(([, , type]) => type === ENVIRONMENT_FOR_VIEW[view]).map(([lat, lon]) => `${lat}:${lon}`)
}
