import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Search from '../views/Search.vue'
import Run from '../views/Run.vue'
import SearchResults from '../views/SearchResult.vue'
import About from '../views/About.vue'
import RunRandom from '../views/RunRandom.vue'
import Project from '../views/Project.vue'
import Accession from '../views/Accession.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/search',
    name: 'Search',
    component: Search
  },
  {
    path: '/taxonomy/:taxonomy',
    name: 'SearchResults',
    component: SearchResults,
    props: true
  },
  {
    path: '/run/:accession',
    name: 'Run',
    component: Run,
    props: true
  },
  {
    path: '/project',
    name: 'Project',
    component: Project,
    props: true
  },
  {
    path: '/random_run',
    name: 'RunRandom',
    component: RunRandom
  },
  {
    path: '/accession/:accession',
    name: 'Accession',
    component: Accession,
    props: true
  },
  {
    // Same page as the metagenome taxonomy page, on amplicon data.
    path: '/amplicon/taxonomy/:taxonomy',
    name: 'AmpliconTaxonomy',
    component: SearchResults,
    props: route => ({ taxonomy: route.params.taxonomy, dataset: 'amplicon' })
  },
  {
    // Same run page, on amplicon data.
    path: '/amplicon/run/:accession',
    name: 'AmpliconRun',
    component: Run,
    props: route => ({ accession: route.params.accession, dataset: 'amplicon' })
  },
  {
    // "Explore tabled results": the taxonomy page, but for every run
    // matching an advanced-search query (?q=) instead of one taxon.
    path: '/search/results',
    name: 'QueryResults',
    component: SearchResults,
    props: route => ({ query: route.query.q, dataset: 'metagenome' })
  },
  {
    path: '/amplicon/search/results',
    name: 'AmpliconQueryResults',
    component: SearchResults,
    props: route => ({ query: route.query.q, dataset: 'amplicon' })
  },
  {
    path: '/about',
    name: 'About',
    component: About
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

export default router
