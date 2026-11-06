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
