// The flat world map shared by the run page and the project page, in the Equal Earth projection.
// Equal Earth is equal-area: every country takes up the share of the map that it takes up of the Earth,
// where the usual web map (Mercator) swells the land towards the poles.
import * as d3 from 'd3'

// The map's own units: it is drawn this wide and tall, then scaled to whatever room the page gives it.
export const MAP_WIDTH = 720
// Equal Earth is 2.05 times as wide as it is tall; this height fits it with a narrow margin all round.
export const MAP_HEIGHT = 354
const MARGIN = 3

export const PROJECTION = d3.geoEqualEarth().fitExtent([[MARGIN, MARGIN], [MAP_WIDTH - MARGIN, MAP_HEIGHT - MARGIN]], { type: 'Sphere' })

/** Where a place falls on the map, in map units: [x, y]. */
export function mapPoint (lon, lat) {
  return PROJECTION([lon, lat])
}
