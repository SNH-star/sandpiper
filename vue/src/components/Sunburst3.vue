<template>
  <div class="sunburst-block">
    <div class="sunburst-toolbar">
      <div class="sunburst-search">
        <b-field>
          <b-input
            id="sunburst-taxa-search"
            name="sunburst-taxa-search"
            v-model="search_query"
            type="search"
            icon="magnify"
            placeholder="Highlight taxa e.g. Bacteroidota or p__Bacillota" />
        </b-field>
        <p class="help">{{ search_help }}</p>
      </div>
    </div>

    <nav class="sunburst-breadcrumb" aria-label="Taxonomic zoom level">
      <div class="sunburst-crumbs">
        <button
          v-for="(node, index) in breadcrumb"
          :key="index"
          type="button"
          class="sunburst-crumb"
          :class="{ 'is-current': index === breadcrumb.length - 1 }"
          :disabled="index === breadcrumb.length - 1"
          @click="zoom_to_breadcrumb(index)">
          {{ node.name }}
          <span v-if="index < breadcrumb.length - 1" class="sunburst-crumb-sep" aria-hidden="true">›</span>
        </button>
      </div>
      <button
        v-if="breadcrumb.length > 1"
        type="button"
        class="sunburst-reset"
        @click="reset_zoom">
        <svg class="sunburst-reset-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <polyline points="1 4 1 10 7 10" />
          <path d="M3.51 15a9 9 0 1 0 .49-6.36L1 10" />
        </svg>
        Reset view
      </button>
    </nav>

    <div class="sunburst-figure">
      <div class="sunburst-canvas">
        <svg id="dataviz_area" class="sunburst" viewBox="0 0 600 600" preserveAspectRatio="xMidYMid meet"></svg>
        <p class="sunburst-hint">Click a wedge to zoom in and see its details. Use the breadcrumb, the centre arrow, or Reset view to go back.</p>
        <p v-if="scope_note" class="sunburst-hint">{{ scope_note }}</p>
      </div>

      <div class="sunburst-side">
        <div class="sunburst-known-fraction">
          <p class="sunburst-known-fraction-label">Known species fraction</p>
          <svg id="known_fraction_area" class="sunburst-donut" viewBox="0 0 220 220" preserveAspectRatio="xMidYMid meet"></svg>
        </div>

        <div class="sunburst-detail">
          <template v-if="selected !== null">
            <h4 class="sunburst-detail-title">{{ selected.name }}</h4>
            <ol v-if="selected.taxonomy.length" class="sunburst-detail-taxonomy">
              <li v-for="crumb in selected.taxonomy" :key="crumb.rank">
                <span class="sunburst-detail-rank">{{ crumb.rank }}</span>
                <router-link :to="crumb.link">{{ crumb.name }}</router-link>
              </li>
            </ol>
            <dl class="sunburst-detail-stats">
              <div>
                <dt>
                  Genome coverage
                  <InfoTooltipButton
                    label="What is genome coverage?"
                    controls="coverage-help"
                    :expanded="coverage_help_open"
                    @open="coverage_help_open = true"
                    @close-delayed="coverage_help_open = false"
                    @close="coverage_help_open = false" />
                </dt>
                <dd>{{ selected.coverage }}</dd>
              </div>
              <div v-if="!selected.is_initial">
                <dt>Relative abundance</dt>
                <dd>{{ selected.relative_abundance }}%</dd>
              </div>
            </dl>
            <div v-if="coverage_help_open" id="coverage-help" class="sunburst-coverage-help" role="dialog" aria-label="What is genome coverage?">
              <p><strong>Genome coverage</strong> is the estimated average number of reads covering each position of a genome from this lineage, inferred from single-copy marker genes. It rises with sequencing depth and falls with genome size, so it is not a cell count.</p>
              <p>For a genus or any group above species, the figure is the sum over every species beneath it, including reads that match no named species. Relative abundance divides it by the total across all bacteria and archaea in the run.</p>
              <p>How much of the sample is bacterial or archaeal at all is shown separately as the prokaryotic fraction.</p>
            </div>
          </template>
          <p v-else class="sunburst-detail-empty">Tap or click a wedge to see its taxonomy, genome coverage, and relative abundance here.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import * as d3 from 'd3'
import { scaleLinear } from 'd3-scale'
import InfoTooltipButton from './InfoTooltipButton.vue'

// Taxon names arrive from the API with their rank prefix stripped off, so the
// rank of a node is only recoverable from its depth in the condensed tree
// (the root is 0). These maps let a search term like "p__Bacillota" be
// restricted to the phylum ring.
const RANK_DEPTHS = { d: 1, p: 2, c: 3, o: 4, f: 5, g: 6, s: 7 }
const RANK_NAMES = {
  1: 'domain', 2: 'phylum', 3: 'class', 4: 'order', 5: 'family', 6: 'genus', 7: 'species'
}
const RANK_PREFIXES = ['d__', 'p__', 'c__', 'o__', 'f__', 'g__', 's__']
const RANK_LABELS = ['Domain', 'Phylum', 'Class', 'Order', 'Family', 'Genus', 'Species']
// Short search terms match nearly everything, which highlights the whole
// sunburst and tells the user nothing, so require a few letters first.
const MIN_SEARCH_LETTERS = 4

// All arcs currently participate in the layout (no windowing), kept as a
// named predicate so intent stays clear at every call site.
function arcVisible () {
  return true
}
function labelVisible (d) {
  return (d.y1 - d.y0) * (d.x1 - d.x0) > 0.05
}
function labelTransform (d, radius) {
  const x = (d.x0 + d.x1) / 2 * 180 / Math.PI
  const y = (d.y0 + d.y1) / 2 * radius
  return `rotate(${x - 90}) translate(${y},0) rotate(20) rotate(${x - 90 + 20 < 90 || x - 90 + 20 > 270 ? 0 : 180})`
}

export default {
  name: 'Sunburst3',
  components: { InfoTooltipButton },
  props: {
    json_tree: { required: true },
    known_species_fraction: { default: null },
    // Name of the root of the tree.
    root_label: { type: String, default: 'All taxa' },
    scope_note: { type: String, default: '' }
  },
  data () {
    return {
      search_query: '',
      match_count: 0,
      breadcrumb: [{ name: this.root_label }],
      coverage_help_open: false,
      selected: null
    }
  },
  created () {
    // d3 selections and hierarchy nodes held outside of data() so that Vue
    // does not attempt to deep-proxy the DOM nodes and (potentially huge)
    // taxonomy tree they hold.
    this.path_selection = null
    this.label_selection = null
    this.redraw_pending = false
    this.root = null
    this.g = null
    this.arc = null
    this.parent_circle = null
    this.center_icon = null
    this.radius = 0
    this.overall_coverage = 0
    this.breadcrumb_nodes = []
  },
  mounted () {
    this.sunburst(this.json_tree, this.known_species_fraction)
  },
  computed: {
    // Split a query such as "p__Bacillota" into the rank it restricts to and
    // the text to match, and decide whether it is long enough to act on.
    parsed_search () {
      const raw = (this.search_query || '').trim()
      if (raw === '') {
        return { state: 'empty', rank: null, term: '' }
      }
      const prefix_match = /^([dpcofgs])__(.*)$/i.exec(raw)
      let rank = null
      let term = raw
      if (prefix_match !== null) {
        rank = RANK_DEPTHS[prefix_match[1].toLowerCase()]
        term = prefix_match[2]
      }
      term = term.trim()
      // Count letters/digits only, so "p__ " or "e. " do not count as a search
      const letters = term.replace(/[^\p{L}\p{N}]/gu, '')
      if (letters.length < MIN_SEARCH_LETTERS) {
        return { state: 'too_short', rank: rank, term: term }
      }
      return { state: 'ready', rank: rank, term: term.toLowerCase() }
    },
    search_help () {
      const query = this.parsed_search
      if (query.state === 'empty') {
        return `Type at least ${MIN_SEARCH_LETTERS} letters to highlight matching parts of the profile. Rank prefixes are respected, so p__Bacillota only matches phyla.`
      }
      if (query.state === 'too_short') {
        return `Type at least ${MIN_SEARCH_LETTERS} letters to highlight matching taxa.`
      }
      const at_rank = query.rank === null ? '' : ` at ${RANK_NAMES[query.rank]} level`
      if (this.match_count === 0) {
        return `No taxa${at_rank} in this profile match "${query.term}".`
      }
      if (this.match_count === 1) {
        return `1 taxon${at_rank} highlighted.`
      }
      return `${this.match_count} taxa${at_rank} highlighted.`
    }
  },
  watch: {
    // Redraw only when the profile being shown actually changes. Redrawing on
    // every component update would throw away the zoom state (and the arcs)
    // each time the search box is typed in.
    json_tree: 'redraw',
    known_species_fraction: 'redraw',
    search_query () {
      this.apply_highlight()
    }
  },

  methods: {
    round (value, precision) {
      const multiplier = Math.pow(10, precision || 0)
      return Math.round(value * multiplier) / multiplier
    },

    // Both watched props change together when the taxonomy database is
    // switched, so coalesce them into a single redraw.
    redraw () {
      if (this.redraw_pending) {
        return
      }
      this.redraw_pending = true
      this.$nextTick(() => {
        this.redraw_pending = false
        this.sunburst(this.json_tree, this.known_species_fraction)
      })
    },
    partition (sunburstData) {
      const root = d3.hierarchy(sunburstData)
        .sum(d => d.size)
        .sort((a, b) => b.order - a.order)
      return d3.partition()
        .size([2 * Math.PI, root.height + 1])(root)
    },

    phylogenyColor (order, depth) {
      const baseColors = ['#a6cee3', '#1f78b4', '#b2df8a', '#33a02c', '#fb9a99', '#e31a1c', '#fdbf6f', '#ff7f00', '#cab2d6', '#6a3d9a']

      const base = baseColors[order % baseColors.length]
      const colorScale = scaleLinear()
        .domain([1, 12])
        .range([base, 'white'])
      if (depth === 0) {
        return 'white'
      } else {
        return colorScale(depth)
      }
    },

    // The opacity an arc has when no search is in effect.
    base_opacity (d) {
      return d.children ? 0.6 : 0.4
    },

    node_matches (d, query) {
      if (query.state !== 'ready') {
        return false
      }
      const name = d.data.name
      if (!name) {
        return false
      }
      if (query.rank !== null && d.data.condensed_depth !== query.rank) {
        return false
      }
      return name.toLowerCase().includes(query.term)
    },

    // Restyle the arcs (and their labels) to reflect the current search. Also
    // used to restore the resting appearance after a mouseout or a zoom.
    apply_highlight () {
      const path = this.path_selection
      const label = this.label_selection
      if (path === null) {
        return
      }
      const query = this.parsed_search

      if (query.state !== 'ready') {
        this.match_count = 0
        path
          .attr('stroke', 'none')
          .attr('stroke-width', null)
          .attr('fill-opacity', d => this.base_opacity(d))
        if (label !== null) {
          label.attr('font-weight', null)
        }
        return
      }

      let matches = 0
      path.each(d => { if (this.node_matches(d, query)) { matches++ } })
      this.match_count = matches

      path
        .attr('stroke', d => this.node_matches(d, query) ? '#000' : 'none')
        .attr('stroke-width', d => this.node_matches(d, query) ? '1.5px' : null)
        .attr('fill-opacity', d => this.node_matches(d, query) ? 0.95 : 0.1)
      if (label !== null) {
        label.attr('font-weight', d => this.node_matches(d, query) ? 'bold' : null)
      }
    },

    // Rebuild the breadcrumb trail from the root down to the given (focused)
    // node. The d3 nodes themselves are kept outside reactive data; only the
    // plain names are, so Vue never has to proxy the whole taxonomy tree.
    update_breadcrumb (node) {
      const ancestors = node.ancestors().reverse()
      this.breadcrumb_nodes = ancestors
      this.breadcrumb = ancestors.map(d => ({ name: d.data.name || this.root_label }))
    },

    zoom_to_breadcrumb (index) {
      const node = this.breadcrumb_nodes[index]
      if (node) {
        this.zoom_to_node(node)
      }
    },

    reset_zoom () {
      if (this.root) {
        this.zoom_to_node(this.root)
      }
    },

    // Show the centre "back one level" control only once actually zoomed in
    // (there's nowhere to go back to from the root), and keep its click
    // target pointed at the newly-focused node's parent.
    update_center_control (p) {
      if (!this.parent_circle || !this.center_icon || !this.root) {
        return
      }
      const at_root = !p || p === this.root
      this.parent_circle
        .datum(at_root ? this.root : (p.parent || this.root))
        .attr('pointer-events', at_root ? 'none' : 'all')
        .style('opacity', at_root ? 0 : 1)
      this.center_icon.style('opacity', at_root ? 0 : 1)
    },

    // Populate the detail panel for the node just zoomed to. A plain
    // summary is stored in reactive data so Vue never has to proxy the d3
    // hierarchy node itself.
    select_node (p, is_initial = false) {
      const ancestors = []
      let current = p
      while (current.parent) {
        ancestors.push(current)
        current = current.parent
      }
      ancestors.reverse()

      const taxonomy = ancestors.map((node, i) => ({
        rank: RANK_LABELS[i] || `Level ${i + 1}`,
        name: node.data.name,
        link: '/taxonomy/' + (RANK_PREFIXES[i] || '') + node.data.name
      }))

      const total_coverage = p.sum(d => d.size).value

      this.selected = {
        name: p.data.name || this.root_label,
        // Only the initial load hides relative abundance (it is trivially
        // 100% there); zooming back out to the root via Reset view still shows it.
        is_initial,
        taxonomy,
        coverage: this.round(total_coverage, 2),
        relative_abundance: this.round(total_coverage / this.overall_coverage * 100, 2)
      }
    },

    // Zoom the arcs and labels to focus on node p (any ancestor of the
    // current view, reached by clicking the centre "back one level" control
    // or a breadcrumb, or any descendant reached by clicking a wedge).
    zoom_to_node (p) {
      const g = this.g
      const path = this.path_selection
      const label = this.label_selection
      const arc = this.arc
      const root = this.root
      const radius = this.radius
      if (!g || !path || !root) {
        return
      }

      root.each(d => {
        d.target = {
          x0: Math.max(0, Math.min(1, (d.x0 - p.x0) / (p.x1 - p.x0))) * 2 * Math.PI,
          x1: Math.max(0, Math.min(1, (d.x1 - p.x0) / (p.x1 - p.x0))) * 2 * Math.PI,
          y0: Math.max(0, d.y0 - p.depth),
          y1: Math.max(0, d.y1 - p.depth)
        }
      })

      const t = g.transition().duration(550)

      // Transition the data on all arcs, even the ones that aren't visible,
      // so that if this transition is interrupted, entering arcs will start
      // the next transition from the desired position.
      path.transition(t)
        .tween('data', d => {
          const i = d3.interpolate(d.current, d.target)
          return time => { d.current = i(time) }
        })
        .filter(function (d) {
          return +this.getAttribute('fill-opacity') || arcVisible(d.target)
        })
        .attr('fill-opacity', d => arcVisible(d.target) ? this.base_opacity(d) : 0)
        .attr('pointer-events', d => arcVisible(d.target) ? 'auto' : 'none')
        .attrTween('d', d => () => arc(d.current))

      label.filter(function (d) {
        return +this.getAttribute('fill-opacity') || labelVisible(d.target)
      }).transition(t)
        .attr('fill-opacity', d => +labelVisible(d.target))
        .attrTween('transform', d => () => labelTransform(d.current, radius))

      // The zoom transition rewrites fill-opacity, so put the search
      // highlighting back once it has finished, and sync the breadcrumb and
      // detail panel to the new focus.
      t.end().then(() => {
        this.apply_highlight()
        this.update_breadcrumb(p)
        this.update_center_control(p)
        this.select_node(p)
      }, () => {})
    },

    sunburst (sunburstData, known_species_fraction) {
      const width = 600
      const radius = width / 18
      this.radius = radius

      const arc = d3.arc()
        .startAngle(d => d.x0)
        .endAngle(d => d.x1)
        .padAngle(d => Math.min((d.x1 - d.x0) / 2, 0.005))
        .padRadius(radius * 1.5)
        .innerRadius(d => d.y0 * radius)
        .outerRadius(d => Math.max(d.y0 * radius, d.y1 * radius - 1))
      this.arc = arc

      const root = this.partition(sunburstData)
      root.each(d => { d.current = d })
      this.root = root
      // The partition's own sum (not a second, separate hierarchy walk) is
      // the total coverage; descendant .sum() calls made later (in
      // select_node) only recompute their own subtree, so this stays valid.
      this.overall_coverage = root.value

      this.update_breadcrumb(root)
      // Start on the root totals box (100%), same as after zooming back out.
      this.select_node(root, true)

      // clear SVG contents first
      d3.selectAll('#dataviz_area > *').remove()
      d3.selectAll('#known_fraction_area > *').remove()
      const svg = d3.select('#dataviz_area')
        .attr('viewBox', [0, 0, width, width])

      const g = svg.append('g')
        .attr('transform', `translate(${width / 2},${width / 2})`)
      this.g = g

      const path = g.append('g')
        .selectAll('path')
        .data(root.descendants())
        .join('path')
        .attr('fill', d => this.phylogenyColor(d.data.order, d.data.condensed_depth))
        .attr('fill-opacity', d => (arcVisible(d.current) ? this.base_opacity(d) : 0))
        .attr('pointer-events', d => (arcVisible(d.current) ? 'auto' : 'none'))
        .attr('d', d => arc(d.current))

      path
        .style('cursor', 'pointer')
        .attr('tabindex', 0)
        .attr('role', 'button')
        .attr('aria-label', d => d.data.name || 'taxon')
        .on('click', (_event, p) => this.zoom_to_node(p))
        .on('keydown', (event, p) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            this.zoom_to_node(p)
          }
        })
        .on('mouseover', function (_event, p) {
          path.filter(d => d.data.name === p.data.name)
            .attr('stroke', '#000')
            .attr('stroke-width', '2px')
            .attr('fill-opacity', 0.1)
        })
        // Restore whatever the resting appearance is - which is the search
        // highlighting when a search is in effect, and the plain colouring
        // otherwise.
        .on('mouseout', () => this.apply_highlight())

      path.append('title')
        .text(d => `${d.ancestors().map(a => a.data.name).reverse().join(' ')}\ncoverage: ${d3.format('.2f')(d.sum(s => s.size).value)}\n`)

      const label = g.append('g')
        .attr('pointer-events', 'none')
        .attr('text-anchor', 'middle')
        .style('user-select', 'none')
        .selectAll('text')
        .data(root.descendants().slice())
        .join('text')
        .attr('dy', '0.35em')
        .attr('fill-opacity', d => +labelVisible(d.current))
        .attr('transform', d => labelTransform(d.current, radius))
        .text(d => d.data.name)

      this.path_selection = path
      this.label_selection = label

      // Clicking the centre steps back up one level (to whatever is
      // currently the focused node's parent); the bound datum is kept in
      // sync with that on every zoom in zoom_to_node/update_center_control.
      const parent_circle = g.append('circle')
        .datum(root)
        .attr('r', radius)
        .attr('fill', '#fafafa')
        .attr('stroke', '#dbdbdb')
        .attr('stroke-width', 1)
        .attr('pointer-events', 'none')
        .attr('role', 'button')
        .attr('aria-label', 'Back one level')
        .style('cursor', 'pointer')
        .on('click', (_event, d) => this.zoom_to_node(d))
        .on('mouseenter', function () {
          d3.select(this).attr('fill', '#eef4fc').attr('stroke', '#3273dc')
        })
        .on('mouseleave', function () {
          d3.select(this).attr('fill', '#fafafa').attr('stroke', '#dbdbdb')
        })
      parent_circle.append('title').text('Back one level')
      this.parent_circle = parent_circle

      // A small backwards/undo arrow drawn in the otherwise-empty centre
      // hole, so the "back one level" affordance is visible rather than an
      // invisible hotspot. Sized off the same centre radius so it scales
      // with the chart. Only shown once zoomed in - see update_center_control.
      const reset_icon_scale = (radius * 1.15) / 24
      this.center_icon = g.append('g')
        .attr('class', 'sunburst-center-icon')
        .attr('pointer-events', 'none')
        .attr('transform', `translate(${-reset_icon_scale * 12},${-reset_icon_scale * 12}) scale(${reset_icon_scale})`)
        .attr('fill', 'none')
        .attr('stroke', '#6b6b6b')
        .attr('stroke-width', 2.5)
        .attr('stroke-linecap', 'round')
        .attr('stroke-linejoin', 'round')
        .call(iconGroup => {
          iconGroup.append('polyline').attr('points', '1 4 1 10 7 10')
          iconGroup.append('path').attr('d', 'M3.51 15a9 9 0 1 0 .49-6.36L1 10')
        })
      this.update_center_control(root)

      this.draw_known_fraction(known_species_fraction)

      // Apply any active search highlighting to the freshly drawn arcs.
      this.apply_highlight()

      return svg.node()
    },

    draw_known_fraction (known_species_fraction) {
      const width = 220
      const outer_radius = 95
      const inner_radius = 55

      const gpie = d3.select('#known_fraction_area')
        .attr('viewBox', [0, 0, width, width])
        .append('g')
        .attr('transform', `translate(${width / 2},${width / 2})`)

      const pie = d3.pie()
        // Sort so that the known species slice is first going clockwise
        .value(d => d.value)
        .sort(a => (a.type === 'inc' ? -1 : 1))

      const data_ready = pie([
        { type: 'inc', colour: '#48c78e', value: known_species_fraction },
        { type: 'not inc', colour: '#e8e8e8', value: 100 - known_species_fraction }
      ])

      gpie.selectAll('path')
        .data(data_ready)
        .join('path')
        .attr('d', d3.arc().innerRadius(inner_radius).outerRadius(outer_radius))
        .attr('fill', d => d.data.colour)
        .attr('stroke', 'white')
        .style('stroke-width', d => (d.data.type === 'inc' ? '2px' : '0.5px'))
        .style('opacity', 1)

      gpie.append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', '0.35em')
        .attr('class', 'sunburst-donut-label')
        .text(`${this.round(known_species_fraction, 0)}%`)
    }
  }
}
</script>

<style scoped>
.sunburst-block {
  width: 100%;
}

.sunburst-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: var(--space-4);
}

.sunburst-search {
  flex: 1 1 20rem;
  max-width: 30rem;
}

.sunburst-breadcrumb {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-top: var(--space-4);
  padding: var(--space-2) 0;
  border-bottom: 1px solid #ededed;
}

.sunburst-crumbs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1);
  min-width: 0;
}

.sunburst-crumb {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  background: none;
  border: none;
  padding: var(--space-1) var(--space-2);
  min-height: 2rem;
  font-size: 0.9rem;
  color: #3273dc;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.15s ease;
}

.sunburst-crumb:hover:not(:disabled) {
  background-color: rgba(50, 115, 220, 0.1);
  text-decoration: underline;
}

.sunburst-crumb:focus-visible {
  outline: 2px solid #3273dc;
  outline-offset: 2px;
}

.sunburst-crumb.is-current {
  color: #363636;
  font-weight: 600;
  cursor: default;
}

.sunburst-crumb-sep {
  color: #b5b5b5;
  margin-left: var(--space-1);
}

.sunburst-reset {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  flex: none;
  border: 1px solid #dbdbdb;
  background: #fff;
  color: #4a4a4a;
  border-radius: 999px;
  padding: 0.35rem 0.85rem;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.sunburst-reset:hover {
  border-color: #3273dc;
  color: #3273dc;
  background-color: rgba(50, 115, 220, 0.06);
}

.sunburst-reset:focus-visible {
  outline: 2px solid #3273dc;
  outline-offset: 2px;
}

.sunburst-reset-icon {
  flex: none;
}

.sunburst-figure {
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(16rem, 2fr);
  gap: var(--space-8);
  align-items: start;
  margin-top: var(--space-4);
}

.sunburst-canvas {
  min-width: 0;
}

.sunburst-known-fraction {
  text-align: center;
  margin-bottom: var(--space-2);
}

.sunburst-donut {
  display: block;
  width: 100%;
  max-width: 140px;
  height: auto;
  margin: 0 auto;
}

.sunburst-block :deep(.sunburst-donut-label) {
  font-size: 26px;
  font-weight: 700;
  fill: #363636;
}

/* Both SVGs have a square viewBox, so giving them a width and letting the
   height follow keeps them inside their column instead of overflowing onto
   the sections below, which is what a fixed pixel height did once the
   layout stacked on narrow screens. */
.sunburst {
  display: block;
  width: 100%;
  height: auto;
  max-width: 720px;
  margin: 0 auto;
  font-size: 10px;
}

/* Wedges are keyboard-focusable (Enter/Space selects), but the browser's
   default SVG focus ring is a rectangle around the bounding box rather than
   the wedge shape, so it's suppressed here in favour of the mouseover-style
   stroke highlight the click/select handler already applies. */
.sunburst-block :deep(#dataviz_area path) {
  outline: none;
}

.sunburst-block :deep(#dataviz_area circle) {
  transition: fill 0.15s ease, stroke 0.15s ease;
}

.sunburst-hint {
  text-align: center;
  font-size: 0.8rem;
  color: #7a7a7a;
  margin-top: var(--space-2);
}

.sunburst-side {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  min-width: 0;
}

.sunburst-known-fraction-label {
  margin: 0 0 var(--space-1);
  font-size: 1.3rem;
  font-weight: 700;
  color: #363636;
}

.sunburst-detail {
  border: 1px solid #ededed;
  border-radius: 6px;
  padding: var(--space-4);
  background: #fafafa;
}

.sunburst-detail-title {
  margin: 0 0 var(--space-3);
  font-size: 1.1rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.sunburst-detail-taxonomy {
  list-style: none;
  margin: 0 0 var(--space-4);
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.sunburst-detail-taxonomy li {
  display: flex;
  gap: var(--space-2);
  font-size: 0.85rem;
  overflow-wrap: anywhere;
}

.sunburst-detail-rank {
  flex: none;
  width: 3.6rem;
  color: #7a7a7a;
}

.sunburst-detail-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2) var(--space-4);
  margin: 0 0 var(--space-4);
}

.sunburst-detail-stats dt {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: #7a7a7a;
}

.sunburst-detail-stats dd {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.sunburst-coverage-help {
  margin-bottom: var(--space-4);
  padding: var(--space-3);
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
  font-size: 0.8rem;
  line-height: 1.45;
}

.sunburst-coverage-help p + p {
  margin-top: var(--space-2);
}

.sunburst-detail-empty {
  font-size: 0.85rem;
  color: #7a7a7a;
}

.sunburst-block :deep(.svg-link) {
  fill: #3273dc;
}

@media (max-width: 768px) {
  .sunburst-figure {
    grid-template-columns: 1fr;
    gap: var(--space-6);
  }

  .sunburst-crumb,
  .sunburst-reset {
    min-height: 44px;
  }
}
</style>
