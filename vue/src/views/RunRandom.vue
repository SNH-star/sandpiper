<template>
  <div>
    <section class="section container">
      Randomly choosing an accession ..
    </section>
  </div>
</template>

<script>

import { fetchRandomAccession } from '@/api'

export default {
  name: 'Random',
  created () {
    // fetch the data when the view is created and the data is
    // already being observed
    this.fetchData()
  },
  computed: {
    host() {
      return this.$route.query.host
    },
    ecological() {
      return this.$route.query.ecological
    },
    two_gbp() {
      return this.$route.query.two_gbp
    },
    exclude_strict_low_complexity() {
      return this.$route.query.exclude_strict_low_complexity
    },
    non_human_host() {
      return this.$route.query.non_human_host
    }
  },
  methods: {
    fetchData () {
      fetchRandomAccession(this.host, this.ecological, this.two_gbp, this.exclude_strict_low_complexity, this.non_human_host)
        .then(response => {
          const acc = response.data.run
          // Keep the filters in the run URL so drawing another random run from
          // the sticky search bar reuses the same criteria.
          this.$router.push({ name: 'Run', params: { accession: acc }, query: { ...this.$route.query } })
        })
        .catch(() => {
          this.$buefy.toast.open({
            message: 'Could not pick a random run, please try again',
            type: 'is-danger'
          })
          this.$router.push({ name: 'Search' })
        })
    }
  },
  watch: {
    // call again the method if the route changes
    $route: 'fetchData'
  }
}
</script>
