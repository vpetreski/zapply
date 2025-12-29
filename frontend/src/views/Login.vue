<template>
  <div class="login-container">
    <div class="login-card">
      <h1>⚡ Zapply ⚡</h1>
      <p class="subtitle">AI-powered job application automation</p>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            placeholder="Enter your email"
            class="form-control"
            required
          />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="Enter your password"
            class="form-control"
            required
            autofocus
          />
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <button type="submit" class="btn-login" :disabled="loading">
          {{ loading ? 'Logging in...' : 'Log In' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const handleLogin = async () => {
  error.value = ''
  loading.value = true

  try {
    // Create form data for OAuth2PasswordRequestForm
    const formData = new FormData()
    formData.append('username', email.value)
    formData.append('password', password.value)

    const response = await axios.post('/api/auth/login', formData)

    // Store the token
    localStorage.setItem('auth_token', response.data.access_token)

    // Redirect to dashboard
    router.push('/')
  } catch (err) {
    console.error('Login error:', err)
    if (err.response?.status === 401) {
      error.value = 'Incorrect password'
    } else {
      error.value = 'Login failed. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #0f172a;
  padding: 20px;
}

.login-card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 40px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
}

h1 {
  margin: 0 0 8px 0;
  font-size: 32px;
  color: #3b82f6;
  text-align: center;
}

.subtitle {
  margin: 0 0 32px 0;
  color: #94a3b8;
  text-align: center;
  font-size: 14px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

label {
  font-weight: 600;
  color: #e2e8f0;
  font-size: 14px;
}

.form-control {
  padding: 12px 16px;
  border: 2px solid #334155;
  border-radius: 8px;
  font-size: 14px;
  background-color: #0f172a;
  color: #e2e8f0;
  transition: border-color 0.2s;
}

.form-control:focus {
  outline: none;
  border-color: #3b82f6;
}

.form-control:read-only {
  background-color: #1e293b;
  color: #64748b;
  cursor: not-allowed;
}

.error-message {
  padding: 12px;
  background-color: #450a0a;
  border: 1px solid #dc2626;
  border-radius: 8px;
  color: #fca5a5;
  font-size: 14px;
}

.btn-login {
  padding: 14px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s, transform 0.2s;
}

.btn-login:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-2px);
}

.btn-login:active:not(:disabled) {
  transform: translateY(0);
}

.btn-login:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
