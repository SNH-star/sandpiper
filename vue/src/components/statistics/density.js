import * as d3 from 'd3'

// About this many gridlines on the density axis; d3 picks a round step near it.
const Y_TICK_TARGET = 5
// Each bin takes a quarter of itself from each neighbour, so the line is not jagged.
const SMOOTHING = [0.25, 0.5, 0.25]

// Weighted average of each value with its neighbours, renormalised at the ends.
function smooth (values) {
  return values.map((_, i) => {
    let total = 0
    let weight = 0
    SMOOTHING.forEach((w, k) => {
      const value = values[i + k - 1]
      if (value !== undefined) { total += w * value; weight += w }
    })
    return total / weight
  })
}

// Bases as a short label: 1.5e8 -> "150 Mb", 3e9 -> "3 Gb".
export function basesLabel (bases) {
  if (bases >= 1e9) return `${+(bases / 1e9).toPrecision(2)} Gb`
  return `${Math.round(bases / 1e6)} Mb`
}

// Everything DensityChart.vue draws, from histograms of the share of runs per bin.
//
// series: [{ colour (any CSS colour), label, histogram: { start, percent, median } }]
// x_ticks: [{ value, label }] in the histograms' own units.
// point_label: value => text for the x position a hover lands on.
// x_step: how finely the hover snaps along x, in the histograms' own units (default: one bin).
// marks: [{ x, density, symbol, text }] drawn at a position in the chart's own units (clamped to the plot).
// footnote: text shown below the chart.
export function buildDensityChart ({
  key, title, note, x_title: xTitle, unit, x_ticks: xTicks, series, missing = [],
  point_label: pointLabel = value => String(value), x_step: xStep = null,
  marks = [], footnote = ''
}) {
  const first = series.length ? series[0].histogram : null
  const step = first ? first.start[1] - first.start[0] : 1
  const low = first ? first.start[0] : 0
  const high = first ? first.start[first.start.length - 1] + step : 1
  const place = value => (100 * (value - low)) / (high - low)
  const snapTo = xStep || step
  const centres = first ? first.start.map(start => start + step / 2) : []
  // The line through a series' bin densities, carried on straight from its two
  // end bins to the ends of the axis (never below zero), as [x, density] points.
  const carryOn = (values, from, to) => {
    if (values.length < 2) return [[from, values[0]], [to, values[0]]]
    const slope = (a, b) => (values[b] - values[a]) / step
    const last = values.length - 1
    return [
      [from, Math.max(0, values[0] + slope(0, 1) * (from - centres[0]))],
      ...values.map((value, i) => [centres[i], value]),
      [to, Math.max(0, values[last] + slope(last - 1, last) * (to - centres[last]))]
    ]
  }
  // The line's density at x, straight between its points.
  const densityAt = (line, x) => {
    const next = line.findIndex(point => point[0] >= x)
    if (next <= 0) return line[Math.max(next, 0)][1]
    const [x0, y0] = line[next - 1]
    const [x1, y1] = line[next]
    return y0 + ((x - x0) / (x1 - x0)) * (y1 - y0)
  }
  // Density: a bin's share of the runs per unit of x, so the area under each curve is 1.
  const lines = series.map(item => carryOn(smooth(item.histogram.percent).map(percent => percent / 100 / step), low, high))
  const most = Math.max(0, ...lines.flatMap(line => line.map(point => point[1])))
  const yStep = d3.tickStep(0, most * 1.05, Y_TICK_TARGET)
  const yMax = Math.ceil((most * 1.05) / yStep) * yStep
  const yDigits = d3.precisionFixed(yStep)
  const curve = d3.line().x(point => point[0]).y(point => point[1]).curve(d3.curveCatmullRom.alpha(0.5))
  const area = d3.area().x(point => point[0]).y0(100).y1(point => point[1]).curve(d3.curveCatmullRom.alpha(0.5))
  return {
    key,
    title,
    note,
    x_title: xTitle,
    unit,
    missing,
    footnote,
    marks: marks.map(mark => ({
      symbol: mark.symbol,
      text: mark.text || '',
      left: Math.min(Math.max(place(mark.x), 0), 100),
      bottom: Math.min(Math.max((100 * mark.density) / yMax, 0), 100)
    })),
    aria: `Density chart of ${title.toLowerCase()} for ${series.map(item => item.label).join(', ')}.`,
    // The exact point `along` (0 to 1) of the way across the plot, for the hover.
    at: along => {
      if (!first) return null
      const x = +(Math.min(Math.max(Math.round((low + along * (high - low)) / snapTo) * snapTo, low), high)).toFixed(4)
      return {
        label: pointLabel(x),
        centre: place(x),
        values: lines.map(line => {
          const density = densityAt(line, x)
          return { density: density.toFixed(yDigits + 1), height: (100 * density) / yMax }
        })
      }
    },
    lines: series.map((item, n) => {
      const points = lines[n].map(([x, density]) => [place(x), 100 - (100 * density) / yMax])
      return { colour: item.colour, label: item.label, median: item.histogram.median, curve: curve(points), area: area(points) }
    }),
    x_ticks: xTicks.map(tick => ({ label: tick.label, percent: place(tick.value) })),
    y_ticks: d3.range(0, yMax + yStep / 2, yStep).map(value => ({
      label: value.toFixed(yDigits), percent: (100 * value) / yMax
    }))
  }
}

// Legend highlighting shared by the statistics charts. `selected` is the list of
// highlighted keys; while it is empty nothing is greyed out.
export function toggleKey (selected, key) {
  return selected.includes(key) ? selected.filter(item => item !== key) : [...selected, key]
}

export function isDimmed (selected, key) {
  return selected.length > 0 && !selected.includes(key)
}
