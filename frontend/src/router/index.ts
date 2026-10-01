import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import CatalogView from '../views/CatalogView.vue'
import CategoryView from '../views/CategoryView.vue'
import ItemDetailsView from '../views/ItemDetailsView.vue'
import ItemWriteView from '../views/ItemWriteView.vue'
import RevisionView from '../views/RevisionView.vue'
import NotFoundView from '../views/NotFoundView.vue'

export const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/catalog', name: 'catalog', component: CatalogView },
  { path: '/catalog/categories/:categoryId', name: 'category', component: CategoryView },
  { path: '/catalog/items/new', name: 'item-create', component: ItemWriteView },
  { path: '/catalog/items/:itemId', name: 'item-details', component: ItemDetailsView },
  { path: '/catalog/items/:itemId/edit', name: 'item-edit', component: ItemWriteView },
  { path: '/revision', name: 'revision', component: RevisionView },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundView },
]

export default createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})
