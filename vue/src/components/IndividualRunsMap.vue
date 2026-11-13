<template>
  <div class="individual-runs">
    <div id="individual-runs-map" class="individual-runs-map">
      <l-map ref="map" style="width: 100%; height: 100%;" :zoom.sync="zoom" :center.sync="center">
        <l-tile-layer :url="url" :attribution="attribution" :options="tile_layer_options" />
        <!-- The selected cluster's dot, copied from the summary map: same colour, outline and ground size, but more opaque so it stands out over the map tiles, so it is small zoomed out and grows as you zoom in. -->
        <l-circle v-if="cluster" :lat-lng="[cluster.lat, cluster.lon]" :radius="cluster.radius"
          :color="cluster.colour" :weight="cluster.strokeWidth" :fill-color="cluster.colour" :fill-opacity="0.5" />
        <l-marker v-for="markerLatLng in lat_lons" v-bind:key="markerLatLng[0]" :lat-lng="markerLatLng['lat_lon']">
          <l-popup :content="html_for_map_popup(markerLatLng)" :options="{ interactive: true }">
          </l-popup>
        </l-marker>
      </l-map>
    </div>
    <div class="map-reset-row">
      <button type="button" class="map-reset" @click="reset_map()"><b-icon icon="refresh" size="is-small" /> reset zoom</button>
      <slot name="actions"></slot>
    </div>
  </div>
</template>

<script>
// The "Individual runs" map: one marker per place, each opening a list of the runs (by study) found there.
// Used on the taxonomy page and on the project page, so the two look and behave the same.
import { LMap, LTileLayer, LMarker, LPopup, LCircle } from '@vue-leaflet/vue-leaflet'
import { Icon, latLng } from 'leaflet'

// Import marker icon images as modules
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

// Make the marker appear https://vue-leaflet.github.io/vue-leaflet/#/quick-start#marker-icons-are-missing
delete Icon.Default.prototype._getIconUrl
Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow
})

const default_zoom = 1.5

export default {
  name: 'IndividualRunsMap',
  components: { LMap, LTileLayer, LMarker, LPopup, LCircle },
  props: {
    // [{ lat_lon: [lat, lon], samples: { study title: [run accession, ...] } }, ...]
    lat_lons: { type: Array, default: () => [] },
    // A map cluster the page has selected: { lat, lon, radius (metres), colour, strokeWidth }
    cluster: { type: Object, default: null }
  },
  data () {
    return {
      // Use the plain tile.openstreetmap.org host - the a/b/c subdomains are
      // deprecated by the OSM operations working group and just cost extra TLS
      // handshakes now that tiles are served over HTTP/2.
      url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      // OSM's tile servers refuse requests that arrive without a Referer
      // header, serving an "Access blocked" tile instead of the map. Some
      // browsers (notably privacy-hardened mobile ones and in-app webviews)
      // default to no-referrer, so set the policy explicitly on the tile
      // images rather than relying on the browser default. 'origin' sends
      // only https://sandpiper.qut.edu.au/, not the page being viewed.
      tile_layer_options: { referrerPolicy: 'origin' },
      attribution:
        '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors',
      defaultCenter: latLng(0, 0),
      center: latLng(0, 0),
      zoom: default_zoom
    }
  },
  watch: {
    // New data arrives (a different taxon, filter or page): back to the whole world, unless a cluster has the view.
    // Not while a cluster is selected: this runs again when its scoped data
    // arrives, and would pull the map back off the cluster it just zoomed to.
    lat_lons () {
      if (!this.cluster) this.center = latLng(this.defaultCenter.lat, this.defaultCenter.lng)
    }
  },
  methods: {
    reset_map () {
      this.center = latLng(this.defaultCenter.lat, this.defaultCenter.lng)
      this.zoom = default_zoom
    },
    // Jump straight to a cluster (no animation). Done once, directly on the Leaflet instance, rather than by
    // also setting the :zoom.sync/:center.sync props: those apply later and would fight this move.
    fitCluster (cluster) {
      const mapComponent = this.$refs.map
      if (mapComponent && mapComponent.leafletObject) {
        // Fit the circle (its radius is in metres, so ask Leaflet for its bounds).
        const bounds = latLng(cluster.lat, cluster.lon).toBounds(cluster.radius * 2)
        mapComponent.leafletObject.fitBounds(bounds, { padding: [30, 30], animate: false })
      }
    },
    html_for_map_popup (markerLatLng) {
      let toReturn = ''
      Object.entries(markerLatLng.samples).forEach((description_samples) => {
        toReturn += '<p>' + description_samples[0] + '</p>'
        toReturn += '<ul>'
        description_samples[1].forEach((sample) => {
          toReturn += '<li><a href="/run/' + sample + '">' + sample + '</a></li>'
        })
        toReturn += '</ul>'
      })
      return toReturn
    }
  }
}
</script>

<style scoped>
.individual-runs-map {
  width: 100%;
  height: 900px;
  max-width: 100%;
}
.map-reset-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1.25rem;
}
.map-reset {
  appearance: none;
  min-height: 44px;
  border: 0;
  padding: 0.4rem 0;
  background: transparent;
  color: #3273dc;
  cursor: pointer;
  font: inherit;
}
.map-reset:focus-visible {
  outline: 2px solid #3273dc;
  outline-offset: 2px;
}
@media (max-width: 768px) {
  .individual-runs-map {
    height: clamp(320px, 60vh, 500px);
    height: clamp(320px, 60dvh, 500px);
  }
}
</style>
