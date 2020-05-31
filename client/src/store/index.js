import Vue from 'vue'
import Vuex from 'vuex'
import VuexPersistence from 'vuex-persist'
import localforage from 'localforage'
import Fuse from 'fuse.js'

const vuexLocal = new VuexPersistence({
  storage: localforage,
})

Vue.use(Vuex)

const fuseOptions = {
  // isCaseSensitive: false,
  // includeScore: false,
  // shouldSort: true,
  // includeMatches: false,
  // findAllMatches: false,
  // minMatchCharLength: 1,
  // location: 0,
  // threshold: 0.6,
  // distance: 100,
  // useExtendedSearch: false,
  keys: [
    { name: 'abstract', weight: 0.5 },
    { name: 'authors', weight: 1.2 },
    { name: 'disciplines', weight: 1.8 },
    { name: 'source', weight: 1.5 },
    { name: 'title', weight: 2.0 },
    { name: 'year', weight: 1.0 },
  ],
}

let index = Fuse.createIndex(
  fuseOptions.keys.map(({ name }) => name),
  [],
)

export default new Vuex.Store({
  state: {
    loaded: false,
    publications: [],
    pageSize: 20,
  },
  mutations: {
    MUTATE_PUBLICATIONS: (state, publications) => {
      publications = publications.map(pub => ({
        ...pub,
        authorNames: pub.authors.map(a => `${a.first_name} ${a.last_name}`),
      }))
      Vue.set(state, 'publications', publications)
      Vue.set(state, 'loaded', true)

      setTimeout(() => {
        index = Fuse.createIndex(
          fuseOptions.keys.map(({ name }) => name),
          publications,
        )
      })
    },
  },
  actions: {
    loadPublications: context => {
      fetch('http://localhost:5000/documents.json')
        .then(res => res.json())
        .then(data => context.commit('MUTATE_PUBLICATIONS', data))
    },
    localLocalPublication: () => {
      const initialPublicationStringified = window.initialPublication
      if (initialPublicationStringified) {
        try {
          const document = JSON.parse(initialPublicationStringified)
          context.commit('MUTATE_PUBLICATIONS', [document])
        } catch (e) {
          console.error('Error parsing initial publication')
          console.error(e)
        }
      }
    },
  },
  modules: {},
  getters: {
    getPublications: state => state.publications,
    queryPublications: function(state, getters, rootState) {
      const { page = 1, search } = rootState.route.query
      let basePublications = state.publications

      let hasFused = false
      if (search) {
        const fuse = new Fuse(basePublications, fuseOptions, index)

        basePublications = fuse.search(search)
        hasFused = true
      }

      const pageIndex = page - 1
      // console.log(pageIndex, pageIndex + state.pageSize)
      basePublications = basePublications.slice(pageIndex, pageIndex + 20)
      if (hasFused) {
        basePublications = basePublications.map(result => result.item)
      }
      return basePublications
    },
  },

  plugins: [vuexLocal.plugin],
})
