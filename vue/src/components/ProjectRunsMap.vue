<template>
  <map-view-frame :actions="ACTIONS" @action="zoom">
    <template #default="{ view, base }">
      <project-runs-flat-map v-if="view === 'flat'" ref="shown" :lat_lons="lat_lons" :label="aria(view)" />
      <project-runs-globe v-else ref="shown" :lat_lons="lat_lons" :base="base" :label="aria(view)" />
    </template>
  </map-view-frame>
</template>

<script>
// The project page's map: one numbered marker per place the project's runs were collected at, on a flat
// map or a globe (see MapViewFrame), as on the run page.
import MapViewFrame, { lazyGlobe } from '@/components/MapViewFrame.vue'
import ProjectRunsFlatMap from '@/components/ProjectRunsFlatMap.vue'
import { placesToGeoJson, plural } from '@/utils/runPlaces'

// Each button calls the method of its name on whichever view is shown.
const ACTIONS = [{ name: 'fit_runs', label: 'All runs' }, { name: 'zoom_world', label: 'World' }]

export default {
  name: 'ProjectRunsMap',
  components: {
    MapViewFrame,
    ProjectRunsFlatMap,
    ProjectRunsGlobe: lazyGlobe(() => import('@/components/ProjectRunsGlobe.vue'))
  },
  props: {
    // [{ lat_lon: [lat, lon], samples: { study title: [run accession, ...] } }, ...]
    lat_lons: { type: Array, default: () => [] }
  },
  data () {
    return { ACTIONS }
  },
  methods: {
    aria (view) {
      const places = placesToGeoJson(this.lat_lons).features
      const runs = places.reduce((total, feature) => total + feature.properties.runs, 0)
      return `${view === 'flat' ? 'Map' : 'Globe'} of where this project's runs were collected: ${plural(runs, 'run')} at ${plural(places.length, 'place')}. The runs are also listed in the table below.`
    },
    // Nothing happens while the globe is still loading.
    zoom (method) {
      const shown = this.$refs.shown
      if (shown && typeof shown[method] === 'function') shown[method]()
    }
  }
}
</script>
