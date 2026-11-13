import * as d3 from 'd3'
import { feature } from 'topojson-client'

// Coastlines and borders get finer as a map zooms in. The coarse set ships with
// the page; the finer ones load the first time they are needed.
export const DETAIL_LEVELS = [
  { name: '10m', minZoom: 8, load: () => import('world-atlas/countries-10m.json') },
  { name: '50m', minZoom: 2.5, load: () => import('world-atlas/countries-50m.json') }
]

const HALF_SPHERE = 2 * Math.PI

// d3 reads a polygon's outer ring as the area it encloses only when the ring is wound the right way.
// A few small islands in the 10m world-atlas data (the Maldives) are wound the other way, so d3 takes
// each as "everything except this island" and paints the whole map as land. Any polygon whose area is
// more than half the sphere is such a mistake, so it is reversed here.
function rewindPolygon (coordinates) {
  if (d3.geoArea({ type: 'Polygon', coordinates }) <= HALF_SPHERE) return coordinates
  return coordinates.map(ring => ring.slice().reverse())
}

export function rewindGeometry (geometry) {
  if (!geometry) return geometry
  if (geometry.type === 'Polygon') return { ...geometry, coordinates: rewindPolygon(geometry.coordinates) }
  if (geometry.type === 'MultiPolygon') return { ...geometry, coordinates: geometry.coordinates.map(rewindPolygon) }
  if (geometry.type === 'GeometryCollection') return { ...geometry, geometries: geometry.geometries.map(rewindGeometry) }
  return geometry
}

// The land of a world-atlas topology as GeoJSON that d3 draws correctly at every detail level.
export function landOf (topology) {
  const land = feature(topology, topology.objects.land || topology.objects.countries)
  if (land.type === 'FeatureCollection') return { ...land, features: land.features.map(f => ({ ...f, geometry: rewindGeometry(f.geometry) })) }
  return { ...land, geometry: rewindGeometry(land.geometry) }
}

// The countries of a world-atlas topology, rewound the same way.
export function countriesOf (topology) {
  const countries = feature(topology, topology.objects.countries)
  return { ...countries, features: countries.features.map(f => ({ ...f, geometry: rewindGeometry(f.geometry) })) }
}

// From this zoom on, countries are named (where the name fits inside); below it the continents and oceans are.
export const COUNTRY_LABEL_ZOOM = 2

// Where each continent and ocean is named at world scale, as [name, longitude, latitude].
export const CONTINENT_LABELS = [
  ['North America', -102, 46], ['South America', -60, -14], ['Europe', 16, 52], ['Africa', 20, 4],
  ['Asia', 90, 46], ['Oceania', 134, -25], ['Antarctica', 0, -80]
]
export const OCEAN_LABELS = [
  ['Pacific Ocean', -150, 5], ['Pacific Ocean', 165, 10], ['Atlantic Ocean', -35, 8], ['Indian Ocean', 80, -22],
  ['Arctic Ocean', 0, 84], ['Southern Ocean', -110, -63]
]

// The continent and ocean names placed on a projection: [{ name, x, y, ocean }].
export function worldLabels (projection) {
  const place = (list, ocean) => list.map(([name, lon, lat]) => {
    const [x, y] = projection([lon, lat])
    return { name: `${name}${ocean ? ' ' + lon : ''}`, text: name, x, y, ocean }
  })
  return [...place(CONTINENT_LABELS, false), ...place(OCEAN_LABELS, true)]
}

// Each country's name, placed on the middle of its largest piece (so the United States is not named in the
// Pacific between Alaska and Hawaii), with the width of that piece in map units.
export function countryLabelsOf (topology, projection) {
  const path = d3.geoPath(projection)
  const labels = []
  countriesOf(topology).features.forEach(country => {
    const name = country.properties && country.properties.name
    const geometry = country.geometry
    if (!name || !geometry) return
    const polygons = geometry.type === 'MultiPolygon' ? geometry.coordinates : geometry.type === 'Polygon' ? [geometry.coordinates] : []
    let largest = null
    let largestArea = -1
    polygons.forEach(coordinates => {
      const polygon = { type: 'Polygon', coordinates }
      const area = path.area(polygon)
      if (area > largestArea) { largest = polygon; largestArea = area }
    })
    if (!largest) return
    const [x, y] = path.centroid(largest)
    const [[x0, y0], [x1, y1]] = path.bounds(largest)
    // contains(px, py): whether a point of the map (in map units) lies inside the country.
    const contains = (px, py) => d3.geoContains(country, projection.invert([px, py]))
    if (Number.isFinite(x) && Number.isFinite(y)) labels.push({ name, text: name, x, y, width: x1 - x0, x0, x1, y0, y1, contains })
  })
  return labels
}

// The country a point lies in, or null at sea.
export function countryAt (topology, lon, lat) {
  const found = countriesOf(topology).features.find(country => d3.geoContains(country, [lon, lat]))
  return found ? found.properties.name : null
}

// The country names to draw for the current view of a map of width `width` and height `height`, at zoom
// {k, x, y}. A name goes on the middle of the country's largest piece when that is in view. When it is not (a
// large country such as Russia or Antarctica, zoomed in), it goes on the middle of the part of that piece
// that is in view, provided that point is on land and the name fits there.
export function visibleCountryLabels (labels, zoom, width, height, size, charWidth) {
  const { k, x, y } = zoom
  const left = -x / k
  const right = (width - x) / k
  const top = -y / k
  const bottom = (height - y) / k
  const visible = []
  labels.forEach(label => {
    const needed = label.text.length * size * charWidth
    if (label.x >= left && label.x <= right && label.y >= top && label.y <= bottom) {
      if (label.width * k >= needed) visible.push(label)
      return
    }
    const x0 = Math.max(label.x0, left)
    const x1 = Math.min(label.x1, right)
    const y0 = Math.max(label.y0, top)
    const y1 = Math.min(label.y1, bottom)
    if (x1 <= x0 || y1 <= y0 || (x1 - x0) * k < needed) return
    const cx = (x0 + x1) / 2
    const cy = (y0 + y1) / 2
    if (label.contains(cx, cy)) visible.push({ ...label, x: cx, y: cy })
  })
  return visible
}
