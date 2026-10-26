<template>
  <div v-if="error_message !== null">
    <section class="section container">
      <b-message 
        title="Error" 
        type="is-warning" 
        :closable="false"
        has-icon>
        <p>{{ error_message }}</p>
      </b-message>
    </section>
  </div>

  <div v-else>
      <section class="section container">
        Searching for accession {{ accession }} ..
      </section>
  </div>
</template>

<script>

import { fetchAccession } from '@/api'
import { fetchAmpliconRun, fetchAmpliconUniversalSearch } from '@/api/amplicon'
import { stopPageLoading } from '@/store/pageLoading'

export default {
  name: 'Accession',
  title: 'Accession search - Sandpiper',
  created () {
    // The template always shows something (an error, or "Searching for
    // accession X.."), so it's never actually a blank page.
    stopPageLoading()
    this.fetchData()
  },
  data () {
    return {
      error_message: null
    }
  },
  props: [
    'accession'
  ],
  methods: {
    // Amplicon runs live in their own section, so a run or BioProject the
    // metagenome lookup doesn't know is checked there before giving up.
    // replace() rather than push() so Back doesn't land here and redirect again.
    async findAmplicon (metagenomeError) {
      const acc = this.accession.trim().toUpperCase()
      try {
        if (/^[SED]RR\d+$/.test(acc)) {
          await fetchAmpliconRun(acc)
          this.$router.replace({ name: 'AmpliconRun', params: { accession: acc } })
          return
        }
        // No amplicon project page: open one of its runs with the project as
        // the side-tab search, so "Next" walks through the rest of it.
        const q = `bioproject: ${acc}`
        const res = await fetchAmpliconUniversalSearch(q)
        if (res.data.random_acc) {
          this.$router.replace({ name: 'AmpliconRun', params: { accession: res.data.random_acc }, query: { q } })
          return
        }
      } catch (err) {
        if (err.response?.status !== 404) {
          console.error('Amplicon accession lookup failed', err)
        }
      }
      this.error_message = metagenomeError
    },
    fetchData () {
      fetchAccession(this.accession)
        .then(response => {
          const result_type = response.data.result_type
          if (result_type === 'fail') {
            // Not a metagenome run or project -- it may be an amplicon one.
            this.findAmplicon(response.data.error)
          } else {
            const acc = response.data.accession
            if (result_type === 'run') {
              this.$router.push({ name: 'Run', params: { accession: acc } })
            } else if (result_type === 'project') {
              this.$router.push({ name: 'Project', query: { model_bioproject: acc } })
            } else {
              console.log("Failed result_type: " + result_type)
            }
          }
        })
    }
  },
  watch: {
    // call again the method if the route changes
    $route: 'fetchData'
  }
}
</script>
