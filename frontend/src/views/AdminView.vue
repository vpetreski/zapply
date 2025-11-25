<template>
  <div class="admin-container">
    <h1>🔧 Admin</h1>

    <!-- Settings -->
    <section class="admin-section">
      <h2>⚙️ Settings</h2>

      <div class="setting-item">
        <label for="run-frequency" class="setting-label">
          <span class="label-text">Run Frequency</span>
          <span class="label-description">Configure how often the job scraper runs automatically</span>
        </label>
        <select
          id="run-frequency"
          v-model="runFrequency"
          @change="saveRunFrequency"
          class="setting-select"
          :disabled="savingFrequency"
        >
          <option value="manual">Manual</option>
          <option value="daily">Daily (9pm Colombian time)</option>
          <option value="hourly">Hourly (at the start of every hour)</option>
        </select>
      </div>

      <div v-if="frequencyResult" class="result-message" :class="frequencyResult.success ? 'success' : 'error'">
        {{ frequencyResult.message }}
      </div>
    </section>

    <!-- Database Cleanup -->
    <section class="admin-section danger-zone">
      <h2>🗑️ Database Cleanup</h2>

      <!-- Database Statistics -->
      <div class="db-stats-box">
        <h3>📊 Current Database State</h3>
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">Jobs</div>
            <div class="stat-value">{{ dbStats.jobs.toLocaleString() }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Runs</div>
            <div class="stat-value">{{ dbStats.runs.toLocaleString() }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Application Logs</div>
            <div class="stat-value">{{ dbStats.application_logs.toLocaleString() }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">User Profiles</div>
            <div class="stat-value">{{ dbStats.user_profiles.toLocaleString() }}</div>
          </div>
        </div>
        <p class="auto-refresh-note">📡 Auto-refreshes every 5 seconds</p>
      </div>

      <p class="warning-text">
        ⚠️ Warning: This will permanently delete data from selected tables!
      </p>

      <div class="cleanup-options">
        <label class="checkbox-label">
          <input type="checkbox" v-model="cleanupOptions.clean_jobs" />
          <span>Delete all Jobs ({{ dbStats.jobs }} rows)</span>
        </label>

        <label class="checkbox-label">
          <input type="checkbox" v-model="cleanupOptions.clean_runs" />
          <span>Delete all Runs ({{ dbStats.runs }} rows)</span>
        </label>

        <label class="checkbox-label">
          <input type="checkbox" v-model="cleanupOptions.clean_application_logs" />
          <span>Delete all Application Logs ({{ dbStats.application_logs }} rows)</span>
        </label>

        <label class="checkbox-label danger">
          <input type="checkbox" v-model="cleanupOptions.clean_user_profiles" />
          <span>⚠️ Delete User Profiles ({{ dbStats.user_profiles }} rows) - Use with caution!</span>
        </label>
      </div>

      <div v-if="hasSelectedOptions" class="cleanup-actions">
        <p class="confirmation-text">
          You are about to delete: {{ selectedOptionsText }}
        </p>
        <button @click="confirmCleanup" class="btn-danger" :disabled="loading">
          {{ loading ? '🔄 Cleaning...' : '🗑️ Confirm & Clean Database' }}
        </button>
      </div>
      <div v-else class="cleanup-actions">
        <p class="info-text">Select at least one option above to enable cleanup</p>
      </div>

      <!-- Result message -->
      <div v-if="cleanupResult" class="result-message" :class="cleanupResult.success ? 'success' : 'error'">
        {{ cleanupResult.message }}
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

interface DatabaseStats {
  jobs: number
  runs: number
  application_logs: number
  user_profiles: number
}

interface CleanupOptions {
  clean_jobs: boolean
  clean_runs: boolean
  clean_application_logs: boolean
  clean_user_profiles: boolean
}

interface CleanupResult {
  success: boolean
  message: string
  deleted_counts: Record<string, number>
}

const loading = ref(false)
const dbStats = ref<DatabaseStats>({
  jobs: 0,
  runs: 0,
  application_logs: 0,
  user_profiles: 0
})

const cleanupOptions = ref<CleanupOptions>({
  clean_jobs: false,
  clean_runs: false,
  clean_application_logs: false,
  clean_user_profiles: false
})

const cleanupResult = ref<CleanupResult | null>(null)

const runFrequency = ref<string>('manual')
const savingFrequency = ref(false)
const frequencyResult = ref<{ success: boolean; message: string } | null>(null)

const hasSelectedOptions = computed(() => {
  return Object.values(cleanupOptions.value).some(v => v)
})

const selectedOptionsText = computed(() => {
  const selected = []
  if (cleanupOptions.value.clean_jobs) selected.push('Jobs')
  if (cleanupOptions.value.clean_runs) selected.push('Runs')
  if (cleanupOptions.value.clean_application_logs) selected.push('Application Logs')
  if (cleanupOptions.value.clean_user_profiles) selected.push('⚠️ User Profiles')
  return selected.join(', ')
})

async function loadRunFrequency() {
  try {
    const response = await axios.get('/api/admin/settings/run-frequency')
    runFrequency.value = response.data.frequency
  } catch (error) {
    console.error('Failed to load run frequency:', error)
  }
}

async function saveRunFrequency() {
  savingFrequency.value = true
  frequencyResult.value = null

  try {
    await axios.post('/api/admin/settings/run-frequency', {
      frequency: runFrequency.value
    })
    frequencyResult.value = {
      success: true,
      message: `✓ Run frequency set to: ${runFrequency.value}`
    }
    // Clear success message after 3 seconds
    setTimeout(() => {
      frequencyResult.value = null
    }, 3000)
  } catch (error: any) {
    frequencyResult.value = {
      success: false,
      message: error.response?.data?.detail || 'Failed to save run frequency'
    }
  } finally {
    savingFrequency.value = false
  }
}

async function loadDatabaseStats() {
  loading.value = true
  try {
    const response = await axios.get('/api/admin/database-stats')
    dbStats.value = response.data
  } catch (error) {
    console.error('Failed to load database stats:', error)
  } finally {
    loading.value = false
  }
}

async function confirmCleanup() {
  if (!hasSelectedOptions.value) return

  // Extra confirmation for user profiles
  if (cleanupOptions.value.clean_user_profiles) {
    const confirmed = confirm(
      '⚠️ WARNING: You are about to delete User Profiles!\n\n' +
      'This will remove all user profile data including CVs, skills, and preferences.\n\n' +
      'Are you absolutely sure?'
    )
    if (!confirmed) return
  }

  // Final confirmation
  const confirmed = confirm(
    `Are you sure you want to delete:\n\n${selectedOptionsText.value}\n\n` +
    'This action cannot be undone!'
  )
  if (!confirmed) return

  loading.value = true
  cleanupResult.value = null

  try {
    const response = await axios.post('/api/admin/cleanup', cleanupOptions.value)
    cleanupResult.value = response.data

    if (response.data.success) {
      // Reset checkboxes
      cleanupOptions.value = {
        clean_jobs: false,
        clean_runs: false,
        clean_application_logs: false,
        clean_user_profiles: false
      }
      // Reload stats
      await loadDatabaseStats()
    }
  } catch (error: any) {
    cleanupResult.value = {
      success: false,
      message: error.response?.data?.detail || 'Cleanup failed',
      deleted_counts: {}
    }
  } finally {
    loading.value = false
  }
}

// Auto-refresh interval
let refreshInterval: number | null = null

onMounted(() => {
  loadRunFrequency()
  loadDatabaseStats()
  // Auto-refresh stats every 5 seconds
  refreshInterval = setInterval(() => {
    loadDatabaseStats()
  }, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.admin-container {
  max-width: 900px;
  margin: 0 auto;
}

h1 {
  margin-bottom: 2rem;
  color: #e0e0e0;
}

.admin-section {
  background: #1e1e1e;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  border: 1px solid #333;
}

.admin-section h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #e0e0e0;
  font-size: 1.3rem;
}

/* Settings Section */
.setting-item {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.setting-label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.label-text {
  font-weight: 600;
  color: #e0e0e0;
  font-size: 1rem;
}

.label-description {
  font-size: 0.85rem;
  color: #888;
}

.setting-select {
  padding: 0.75rem;
  background: #2a2a2a;
  border: 1px solid #404040;
  border-radius: 4px;
  color: #e0e0e0;
  font-size: 0.95rem;
  cursor: pointer;
  transition: border-color 0.2s;
  max-width: 400px;
}

.setting-select:hover:not(:disabled) {
  border-color: #4a9eff;
}

.setting-select:focus {
  outline: none;
  border-color: #4a9eff;
  box-shadow: 0 0 0 2px rgba(74, 158, 255, 0.2);
}

.setting-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.setting-select option {
  background: #2a2a2a;
  color: #e0e0e0;
}

/* Database Stats Box */
.db-stats-box {
  background: #2a2a2a;
  border-radius: 6px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  border: 1px solid #404040;
}

.db-stats-box h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #4a9eff;
  font-size: 1.1rem;
}

.auto-refresh-note {
  text-align: center;
  color: #888;
  font-size: 0.85rem;
  margin-top: 1rem;
  margin-bottom: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 0;
}

.stat-card {
  background: #2a2a2a;
  padding: 1rem;
  border-radius: 6px;
  text-align: center;
  border: 1px solid #404040;
}

.stat-label {
  font-size: 0.85rem;
  color: #888;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.8rem;
  font-weight: bold;
  color: #4a9eff;
}

/* Danger Zone */
.danger-zone {
  border-color: #ff4444;
  background: #1a1515;
}

.warning-text {
  color: #ff9999;
  font-weight: bold;
  margin-bottom: 1.5rem;
  padding: 0.75rem;
  background: #2a1a1a;
  border-radius: 4px;
  border-left: 4px solid #ff4444;
}

.cleanup-options {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: #2a2a2a;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.checkbox-label:hover {
  background: #333;
}

.checkbox-label.danger {
  background: #2a1a1a;
  border: 1px solid #ff4444;
}

.checkbox-label.danger:hover {
  background: #331a1a;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.checkbox-label span {
  color: #e0e0e0;
  font-size: 0.95rem;
}

.cleanup-actions {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #333;
}

.confirmation-text {
  color: #ffaa44;
  font-weight: bold;
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: #2a2410;
  border-radius: 4px;
  border-left: 4px solid #ffaa44;
}

.info-text {
  color: #888;
  font-style: italic;
}

.btn-danger {
  background: #ff4444;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
  transition: background 0.2s;
}

.btn-danger:hover:not(:disabled) {
  background: #ff6666;
}

.btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #404040;
  color: white;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.2s;
}

.btn-secondary:hover:not(:disabled) {
  background: #555;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.result-message {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 4px;
  font-weight: bold;
}

.result-message.success {
  background: #1a3a1a;
  color: #66ff66;
  border: 1px solid #44aa44;
}

.result-message.error {
  background: #3a1a1a;
  color: #ff6666;
  border: 1px solid #aa4444;
}
</style>
