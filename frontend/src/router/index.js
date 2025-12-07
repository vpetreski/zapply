import { createRouter, createWebHistory } from 'vue-router'
import Jobs from '../views/Jobs.vue'
import Runs from '../views/Runs.vue'
import ProfileView from '../views/ProfileView.vue'
import AdminView from '../views/AdminView.vue'
import Login from '../views/Login.vue'
import axios from 'axios'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: Login,
      meta: { public: true }
    },
    {
      path: '/',
      name: 'jobs',
      component: Jobs
    },
    {
      path: '/runs',
      name: 'runs',
      component: Runs
    },
    {
      path: '/profile',
      name: 'profile',
      component: ProfileView
    },
    {
      path: '/admin',
      name: 'admin',
      component: AdminView
    }
  ]
})

// Navigation guard to check authentication
router.beforeEach(async (to, from, next) => {
  // Allow access to login page
  if (to.meta.public) {
    next()
    return
  }

  // Check if we have a token
  const token = localStorage.getItem('auth_token')

  if (!token) {
    // No token - redirect to login
    next('/login')
    return
  }

  // We have a token - verify it's valid
  try {
    await axios.get('/api/auth/me', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
    // Token is valid
    next()
  } catch (error) {
    // Token is invalid - clear it and redirect to login
    localStorage.removeItem('auth_token')
    next('/login')
  }
})

export default router
