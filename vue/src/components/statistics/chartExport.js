import { toPng, toSvg } from 'html-to-image'
import sandpiperLogo from '@/assets/sandpiper_logo.png'
import { withPngDpi } from '@/components/statistics/pngDpi'

export const FORMATS = { svg: { label: 'SVG', make: toSvg }, png: { label: 'PNG', make: toPng } }

const LOGO_WIDTH_PX = 90
// The logo sits in a band added under the figure, so it never covers any of the figure.
const LOGO_BAND_PX = 80
const LOGO_EDGE_PX = 12
// A PNG is saved at this resolution for the size the figure has on screen, where a CSS inch is 96 pixels,
// and the file states it, so image software and journal checks read 200 dpi and not a default of 72 or 96.
const PNG_DPI = 200
const CSS_PIXELS_PER_INCH = 96
const PNG_SCALE = PNG_DPI / CSS_PIXELS_PER_INCH
const OBJECT_URL_LIFETIME_MS = 60000
// Room added to the left and right of every download. Parts of a figure stick out past its box (the last x-axis
// label, such as 100, is centred on the plot's right edge), and a copy is cut off at the box, so without this
// those parts are clipped whenever the figure has no padding of its own.
const SIDE_PADDING_PX = 24
const FALLBACK_BACKGROUND = '#ffffff'
// Left out of every download: the button itself, the toggles, selects and filters that set what the figure shows
// (their effect stays), the map's zoom buttons, the heading's # link, the screen-reader copy of each chart,
// the hover tooltips and hints marked export-skip.
const SKIPPED = [
  '.chart-download', '.map-zoom', '.maplibregl-ctrl-group', '.maplibregl-ctrl-scale', '.maplibregl-ctrl-bottom-left', '.maplibregl-ctrl-top-right', '.section-anchor', '.is-sr-only', '.hover-tip', '.trend-tip', '.chart-mark-tip', '.coverage-tip',
  '.switch', '.field', '.lag-filters', '.density-reset', '.trend-reset', '.export-skip'
]

// What an SVG element's CSS classes and variables give it. The copy of the figure is a standalone image that has
// none of the page's stylesheets, and html-to-image only carries the styles of HTML elements across, so these
// are written onto the page's own SVG elements (as the browser has worked them out) for the moment of the copy.
const SVG_PROPERTIES = [
  'fill', 'fill-opacity', 'fill-rule', 'stroke', 'stroke-width', 'stroke-opacity', 'stroke-dasharray', 'stroke-linecap',
  'stroke-linejoin', 'opacity', 'visibility', 'font-family', 'font-size', 'font-weight', 'font-style', 'letter-spacing',
  'text-anchor', 'dominant-baseline', 'paint-order', 'vector-effect', 'shape-rendering'
]

// Returns a function that puts every SVG element's style back as it was.
function inlineSvgStyles (node) {
  const changed = [...node.querySelectorAll('svg, svg *')].map(element => {
    const before = element.getAttribute('style')
    const computed = getComputedStyle(element)
    SVG_PROPERTIES.forEach(property => element.style.setProperty(property, computed.getPropertyValue(property)))
    return [element, before]
  })
  return () => changed.forEach(([element, before]) => {
    if (before === null) element.removeAttribute('style')
    else element.setAttribute('style', before)
  })
}

let logoPromise = null

// The logo scaled down and as a data URI, so the exported file carries it with no outside link.
function logoDataUri () {
  if (!logoPromise) {
    logoPromise = new Promise((resolve, reject) => {
      const image = new Image()
      image.onload = () => {
        const canvas = document.createElement('canvas')
        canvas.width = Math.round(LOGO_WIDTH_PX * PNG_SCALE)
        canvas.height = Math.round(canvas.width * image.naturalHeight / image.naturalWidth)
        canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height)
        resolve(canvas.toDataURL('image/png'))
      }
      image.onerror = () => { logoPromise = null; reject(new Error('The Sandpiper logo could not be loaded')) }
      image.src = sandpiperLogo
    })
  }
  return logoPromise
}

// html-to-image's filter: true keeps a node (text nodes always stay).
// How much taller the figure is on screen than its copy, because of the left out parts that take up room on
// the page: their rows (with margins) joined where they overlap, as two switches sit on one row.
function leftOutHeight (node) {
  const found = [...node.querySelectorAll(SKIPPED.join(','))]
  const rows = found
    .filter(el => !found.some(other => other !== el && other.contains(el)))
    .map(el => ({ el, style: getComputedStyle(el) }))
    .filter(({ style }) => style.display !== 'none' && !['absolute', 'fixed'].includes(style.position) && style.float === 'none')
    .map(({ el, style }) => {
      const top = el.getBoundingClientRect().top - parseFloat(style.marginTop)
      return [top, el.getBoundingClientRect().bottom + parseFloat(style.marginBottom)]
    })
    .sort((a, b) => a[0] - b[0])
  let total = 0
  let end = -Infinity
  rows.forEach(([top, bottom]) => {
    total += Math.max(0, bottom - Math.max(top, end))
    end = Math.max(end, bottom)
  })
  return Math.round(total)
}

const isKept = node => node.nodeType !== Node.ELEMENT_NODE || !SKIPPED.some(selector => node.matches(selector))

// The PNG behind a data URI, with its resolution written in, as an object URL to download.
async function stampedPngUrl (dataUri) {
  const bytes = new Uint8Array(await (await fetch(dataUri)).arrayBuffer())
  return URL.createObjectURL(new Blob([withPngDpi(bytes, PNG_DPI)], { type: 'image/png' }))
}

// 'sandpiper-<figure>-2026-11-11.svg'
export function downloadName (name, format, date = new Date()) {
  return `sandpiper-${name}-${date.toISOString().slice(0, 10)}.${format}`
}

// Saves the figure as it looks right now (highlighted lines, selected years, chosen toggles) as an SVG or PNG,
// with the Sandpiper logo in its bottom right corner, in a band under the figure.
export async function exportFigure (node, { format, name }) {
  const { make } = FORMATS[format]
  const logo = await logoDataUri()
  const height = node.offsetHeight - leftOutHeight(node) + LOGO_BAND_PX
  const width = node.offsetWidth + 2 * SIDE_PADDING_PX
  // The figure's own padding stays; the extra room is added on top of it.
  const nodeStyle = getComputedStyle(node)
  const background = getComputedStyle(document.body).backgroundColor
  const restoreSvgStyles = inlineSvgStyles(node)
  let url
  try {
    url = await make(node, {
      pixelRatio: PNG_SCALE,
      backgroundColor: background && background !== 'rgba(0, 0, 0, 0)' ? background : FALLBACK_BACKGROUND,
      skipFonts: true,
      width,
      height,
      filter: isKept,
      // Applied to the copy only. The figure's own top margin would push the picture down; the logo is a
      // background in the extra band, so it is drawn behind the figure and cannot hide anything.
      style: {
        margin: '0',
        // Border-box, so the figure's own layout keeps its width and the padding is the extra room around it.
        boxSizing: 'border-box',
        width: `${width}px`,
        paddingLeft: `${SIDE_PADDING_PX + parseFloat(nodeStyle.paddingLeft)}px`,
        paddingRight: `${SIDE_PADDING_PX + parseFloat(nodeStyle.paddingRight)}px`,
        height: `${height}px`,
        blockSize: `${height}px`,
        backgroundImage: `url(${logo})`,
        backgroundRepeat: 'no-repeat',
        backgroundPosition: `right ${LOGO_EDGE_PX}px bottom ${LOGO_EDGE_PX}px`,
        backgroundSize: `${LOGO_WIDTH_PX}px auto`
      }
    })
  } finally {
    restoreSvgStyles()
  }
  const isPng = format === 'png'
  const link = document.createElement('a')
  link.href = isPng ? await stampedPngUrl(url) : url
  link.download = downloadName(name, format)
  link.click()
  // Freed once the browser has had time to start the download.
  if (isPng) setTimeout(() => URL.revokeObjectURL(link.href), OBJECT_URL_LIFETIME_MS)
}
