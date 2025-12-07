<template>
  <div id="app" class="app">
    <header v-if="!isLoginPage" class="header">
      <RouterLink to="/" class="logo-link">
        <h1>⚡ Zapply</h1>
      </RouterLink>
      <nav class="nav">
        <RouterLink to="/">Jobs</RouterLink>
        <RouterLink to="/runs">Runs</RouterLink>
        <RouterLink to="/profile">Profile</RouterLink>
        <RouterLink to="/admin">Admin</RouterLink>
        <button @click="handleLogout" class="logout-btn">Logout</button>
      </nav>
    </header>
    <main class="main" :class="{ 'no-header': isLoginPage }">
      <RouterView />
    </main>
    <footer v-if="!isLoginPage" class="footer">
      <p>Zapply v0.1.0 - AI-Powered Job Application Automation</p>
    </footer>
  </div>
</template>

<script setup>
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()
const router = useRouter()

const isLoginPage = computed(() => route.name === 'login')

const handleLogout = () => {
  localStorage.removeItem('auth_token')
  router.push('/login')
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background-color: #0f172a;
  color: #e2e8f0;
}

.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background-color: #1e293b;
  padding: 1rem 2rem;
  border-bottom: 1px solid #334155;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo-link {
  text-decoration: none;
  transition: opacity 0.2s;
}

.logo-link:hover {
  opacity: 0.8;
}

.header h1 {
  font-size: 1.5rem;
  color: #3b82f6;
  cursor: pointer;
}

.nav {
  display: flex;
  gap: 2rem;
  align-items: center;
}

.nav a {
  color: #94a3b8;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}

.nav a:hover,
.nav a.router-link-active {
  color: #3b82f6;
}

.logout-btn {
  background-color: transparent;
  border: 1px solid #475569;
  color: #94a3b8;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.logout-btn:hover {
  background-color: #1e293b;
  border-color: #64748b;
  color: #e2e8f0;
}

.main {
  flex: 1;
  padding: 2rem;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
}

.main.no-header {
  padding: 0;
  max-width: none;
}

.footer {
  background-color: #1e293b;
  border-top: 1px solid #334155;
  padding: 1rem 2rem;
  text-align: center;
  color: #64748b;
  font-size: 0.875rem;
}
</style>
