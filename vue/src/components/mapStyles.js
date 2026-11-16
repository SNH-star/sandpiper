// Free base maps for the MapLibre maps (run page and Statistics page); neither needs a key.
//   Map: OpenFreeMap streets, from OpenStreetMap data.
//   Satellite: EOX Sentinel-2 cloudless.
// Both show their own attribution on the map.
export const MAP_STYLE = 'https://tiles.openfreemap.org/styles/liberty'

export const SATELLITE_STYLE = {
  version: 8,
  glyphs: 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf',
  sources: {
    satellite: {
      type: 'raster',
      tiles: ['https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/g/{z}/{y}/{x}.jpg'],
      tileSize: 256,
      maxzoom: 12,
      attribution: 'Sentinel-2 cloudless &ndash; <a href="https://s2maps.eu" target="_blank" rel="noopener">s2maps.eu</a> by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2021)'
    }
  },
  layers: [{ id: 'satellite', type: 'raster', source: 'satellite' }]
}

export const BASE_STYLES = { map: MAP_STYLE, satellite: SATELLITE_STYLE }

// One world, seen once. The window runs from the Bering Strait eastwards right round to the Bering Strait again,
// so its edges fall between Alaska and Russia, where they cross almost no land, and not on the date line, which
// would cut Oceania in two. The east edge stops just short of a full turn: a window of exactly 360° reads as empty.
const ONE_WORLD_BOUNDS = [[-169, -85.051129], [190.999, 85.051129]]

// Keeps a map to that one world: it cannot be dragged or zoomed out far enough to show a second copy. Call it on
// a map that already exists; passing the bounds to the map's constructor fails in this version of MapLibre.
export function showOneWorld (map) {
  map.setMaxBounds(ONE_WORLD_BOUNDS)
}

// The red of the markers that show where runs were collected (run page and project page).
export const SAMPLE_MARKER_COLOUR = '#d32f2f'

// The street map draws its oceans a pale blue over a grey relief picture, which reads as white at world scale.
// This hides the relief and paints the water a clear blue, leaving the land the style's cream.
export const WATER_BLUE = '#6fb1e4'
export function blueWater (map) {
  if (map.getLayer('natural_earth')) map.setPaintProperty('natural_earth', 'raster-opacity', 0)
  if (map.getLayer('water')) map.setPaintProperty('water', 'fill-color', WATER_BLUE)
}

const PLACE_NAME = ['coalesce', ['get', 'name_en'], ['get', 'name']]
const PLACES_SOURCE = { type: 'vector', url: 'https://tiles.openfreemap.org/planet' }

function labelPaint (onImagery) {
  return {
    'text-color': onImagery ? '#ffffff' : '#1b2a3a',
    'text-halo-color': onImagery ? 'rgba(0, 0, 0, 0.8)' : 'rgba(255, 255, 255, 0.92)',
    'text-halo-width': 1.6,
    'text-halo-blur': 0.5
  }
}

// Names for the continents (and, on imagery, the countries, states, cities and oceans) so the map says where it is
// from the first view. The street map already names most places once you zoom in; imagery has no names at all.
function placeLabelLayers (onImagery) {
  const paint = labelPaint(onImagery)
  const place = (id, klass, layout, extra = {}) => ({
    id,
    type: 'symbol',
    source: 'openmaptiles',
    'source-layer': 'place',
    filter: ['==', ['get', 'class'], klass],
    layout: { 'text-field': PLACE_NAME, ...layout },
    paint,
    ...extra
  })
  const layers = [
    place('sp_continent', 'continent', {
      'text-font': ['Noto Sans Bold'],
      'text-size': ['interpolate', ['linear'], ['zoom'], 0, 15, 3, 22],
      'text-max-width': 8
    }, { maxzoom: 4 })
  ]
  if (onImagery) {
    layers.push(
      place('sp_country', 'country', {
        'text-font': ['Noto Sans Bold'],
        'text-size': ['interpolate', ['linear'], ['zoom'], 1, 11, 5, 18],
        'text-max-width': 6.25
      }, { maxzoom: 9 }),
      place('sp_state', 'state', {
        'text-font': ['Noto Sans Italic'],
        'text-size': ['interpolate', ['linear'], ['zoom'], 4, 10, 8, 14],
        'text-max-width': 9
      }, { minzoom: 4, maxzoom: 8 }),
      place('sp_city', 'city', {
        'text-font': ['Noto Sans Regular'],
        'text-size': ['interpolate', ['linear'], ['zoom'], 3, 11, 8, 14, 12, 18],
        'text-max-width': 8
      }, { minzoom: 3 }),
      {
        id: 'sp_ocean',
        type: 'symbol',
        source: 'openmaptiles',
        'source-layer': 'water_name',
        filter: ['match', ['geometry-type'], ['MultiPoint', 'Point'], true, false],
        layout: { 'text-field': PLACE_NAME, 'text-font': ['Noto Sans Italic'], 'text-size': ['interpolate', ['linear'], ['zoom'], 0, 12, 8, 16], 'text-letter-spacing': 0.2, 'text-max-width': 5 },
        paint: { ...paint, 'text-color': '#cfe6ff' }
      }
    )
  }
  return layers
}

// Called when a base map has loaded: blue water and names on the street map; names on the imagery.
export function decorateBase (map, base) {
  if (base === 'satellite') {
    if (!map.getSource('openmaptiles')) map.addSource('openmaptiles', PLACES_SOURCE)
  } else {
    blueWater(map)
    // Name more countries at world scale, larger and darker, and the oceans too.
    const bigger = ['interpolate', ['linear'], ['zoom'], 0, 11, 4, 18]
    ;['label_country_1', 'label_country_2', 'label_country_3'].forEach(id => {
      if (!map.getLayer(id)) return
      map.setLayoutProperty(id, 'text-size', bigger)
      map.setLayerZoomRange(id, id === 'label_country_3' ? 1 : 0, 9)
    })
    if (map.getLayer('water_name_point_label')) {
      map.setLayoutProperty('water_name_point_label', 'text-size', ['interpolate', ['linear'], ['zoom'], 0, 12, 8, 16])
    }
  }
  placeLabelLayers(base === 'satellite').forEach(layer => { if (!map.getLayer(layer.id)) map.addLayer(layer) })
}

// Countries' boundaries at sea (around islands and along coasts), which the street style leaves out and the
// OpenStreetMap tiles of the earlier Leaflet maps drew. Call after `decorateBase`, which gives the imagery
// its 'openmaptiles' source. Drawn under the names, in the purple OpenStreetMap uses for boundaries.
const MARITIME_LAYER = {
  id: 'sp_maritime_boundary',
  type: 'line',
  source: 'openmaptiles',
  'source-layer': 'boundary',
  filter: ['all', ['==', ['get', 'admin_level'], 2], ['==', ['get', 'maritime'], 1]],
  paint: {
    'line-color': 'hsl(300, 38%, 42%)',
    'line-opacity': 0.75,
    'line-dasharray': [4, 2],
    'line-width': ['interpolate', ['linear'], ['zoom'], 1, 0.8, 6, 1.4, 12, 2]
  }
}
// The first of these the style has is the layer the sea boundaries go beneath.
const LAYERS_ABOVE_MARITIME = ['boundary_2', 'sp_continent']

export function maritimeBorders (map, onImagery) {
  if (map.getLayer(MARITIME_LAYER.id) || !map.getSource('openmaptiles')) return
  const paint = onImagery ? { ...MARITIME_LAYER.paint, 'line-color': 'hsl(300, 60%, 82%)' } : MARITIME_LAYER.paint
  map.addLayer({ ...MARITIME_LAYER, paint }, LAYERS_ABOVE_MARITIME.find(id => map.getLayer(id)))
}
