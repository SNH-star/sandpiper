import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'

// Every view except the landing page loads on first visit to its route, so the
// first page does not download the code (maps, charts) of pages not yet opened.

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/search',
    name: 'Search',
    component: () => import('../views/Search.vue')
  },
  {
    path: '/taxonomy/:taxonomy',
    name: 'SearchResults',
    component: () => import('../views/SearchResult.vue'),
    props: true
  },
  {
    path: '/run/:accession',
    name: 'Run',
    component: () => import('../views/Run.vue'),
    props: true
  },
  {
    path: '/project',
    name: 'Project',
    component: () => import('../views/Project.vue'),
    props: true
  },
  {
    path: '/random_run',
    name: 'RunRandom',
    component: () => import('../views/RunRandom.vue')
  },
  {
    path: '/accession/:accession',
    name: 'Accession',
    component: () => import('../views/Accession.vue'),
    props: true
  },
  {
    // "Explore tabled results": the taxonomy page, but for every run
    // matching an advanced-search query (?q=) instead of one taxon.
    path: '/search/results',
    name: 'QueryResults',
    component: () => import('../views/SearchResult.vue'),
    props: route => ({ query: route.query.q })
  },
  {
    path: '/statistics',
    name: 'Statistics',
    component: () => import('../views/Statistics.vue')
  },
  {
    path: '/about',
    name: 'About',
    component: () => import('../views/About.vue')
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

export default router
