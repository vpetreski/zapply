<template>
  <div class="admin-container">
    <!-- Profile Warning Banner -->
    <ProfileWarningBanner />

    <h1>Admin</h1>

    <!-- Settings -->
    <section class="admin-section">
      <h2>Settings</h2>

      <div class="setting-item">
        <label for="run-frequency" class="setting-label">
          <span class="label-text">Run Frequency</span>
          <span class="label-description">Configure how often the automation pipeline runs (scraping, matching)</span>
          <span class="label-tip">Recommended: Daily for production use</span>
        </label>
        <select
          id="run-frequency"
          v-model="runFrequency"
          @change="saveRunFrequency"
          class="setting-select"
          :disabled="savingFrequency"
          style="padding-right: 3rem;"
        >
          <option value="manual">Manual</option>
          <option value="daily">Daily (6am Colombian time)</option>
          <option value="hourly">Hourly (at the start of every hour)</option>
        </select>
      </div>

      <div v-if="frequencyResult" class="result-message" :class="frequencyResult.success ? 'success' : 'error'">
        {{ frequencyResult.message }}
      </div>

      <div class="setting-item">
        <label for="scrape-limit" class="setting-label">
          <span class="label-text">Scrape Job Limit</span>
          <span class="label-description">Limit the number of jobs scraped per run (useful for testing to reduce cost and time)</span>
          <span class="label-tip">Recommended: Unlimited for production use</span>
        </label>
        <select
          id="scrape-limit"
          v-model.number="scrapeLimit"
          @change="saveScrapeLimit"
          class="setting-select"
          :disabled="savingLimit"
          style="padding-right: 3rem;"
        >
          <option :value="0">Unlimited</option>
          <option :value="10">10 jobs</option>
          <option :value="20">20 jobs</option>
          <option :value="50">50 jobs</option>
        </select>
      </div>

      <div v-if="limitResult" class="result-message" :class="limitResult.success ? 'success' : 'error'">
        {{ limitResult.message }}
      </div>
    </section>

    <!-- Scraper Sources -->
    <section class="admin-section">
      <div class="section-header">
        <h2>Scraper Sources</h2>
        <button @click="syncSources" :disabled="syncingSources" class="btn btn-secondary btn-sm">
          {{ syncingSources ? 'Syncing...' : 'Sync Sources' }}
        </button>
      </div>

      <div v-if="syncResult" class="result-message" :class="syncResult.success ? 'success' : 'error'">
        {{ syncResult.message }}
      </div>

      <div v-if="loadingSources" class="loading-message">Loading sources...</div>

      <div v-else-if="sources.length === 0" class="empty-message">
        No sources configured. Click "Sync Sources" to initialize from registry.
      </div>

      <div v-else class="sources-list">
        <div v-for="source in sources" :key="source.id" class="source-card">
          <div class="source-header">
            <div class="source-info">
              <h3>{{ source.label }}</h3>
              <span class="source-name">{{ source.name }}</span>
            </div>
            <label class="toggle-switch">
              <input
                type="checkbox"
                :checked="source.enabled"
                @change="toggleSource(source)"
                :disabled="updatingSource === source.name"
              />
              <span class="toggle-slider"></span>
            </label>
          </div>

          <p v-if="source.description" class="source-description">{{ source.description }}</p>

          <div class="source-details">
            <div class="detail-item">
              <span class="detail-label">Priority:</span>
              <span class="detail-value">{{ source.priority }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Status:</span>
              <span :class="['badge', source.enabled ? 'badge-enabled' : 'badge-disabled']">
                {{ source.enabled ? 'Enabled' : 'Disabled' }}
              </span>
            </div>
          </div>

          <div class="credentials-section">
            <span class="credentials-label">Credentials:</span>
            <div class="credentials-status">
              <template v-if="source.credentials_configured && Object.keys(source.credentials_configured).length > 0">
                <span
                  v-for="(configured, key) in source.credentials_configured"
                  :key="key"
                  :class="['credential-badge', configured ? 'credential-ok' : 'credential-missing']"
                  :title="configured ? `${key} is configured` : `${key} is missing - set ${source.credentials_env_prefix}_${key.toUpperCase()}`"
                >
                  {{ key }}
                </span>
              </template>
              <span v-else class="credential-badge credential-none">No credentials required</span>
            </div>
          </div>

          <div v-if="source.settings && Object.keys(source.settings).length > 0" class="settings-section">
            <span class="settings-label">Settings:</span>
            <div class="settings-tags">
              <span v-for="(value, key) in source.settings" :key="key" class="setting-tag">
                {{ formatSettingKey(key) }}: {{ formatSettingValue(value) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import ProfileWarningBanner from '@/components/ProfileWarningBanner.vue'

// Types
interface ScraperSource {
  id: number
  name: string
  label: string
  description: string | null
  enabled: boolean
  priority: number
  credentials_env_prefix: string | null
  settings: Record<string, any> | null
  credentials_configured: Record<string, boolean> | null
  created_at: string
  updated_at: string
}

const runFrequency = ref<string>('manual')
const savingFrequency = ref(false)
const frequencyResult = ref<{ success: boolean; message: string } | null>(null)

const scrapeLimit = ref<number>(0)
const savingLimit = ref(false)
const limitResult = ref<{ success: boolean; message: string } | null>(null)

// Sources state
const sources = ref<ScraperSource[]>([])
const loadingSources = ref(false)
const syncingSources = ref(false)
const updatingSource = ref<string | null>(null)
const syncResult = ref<{ success: boolean; message: string } | null>(null)

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
      message: `Run frequency set to: ${runFrequency.value}`
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

async function loadScrapeLimit() {
  try {
    const response = await axios.get('/api/admin/settings/scrape-job-limit')
    scrapeLimit.value = response.data.limit
  } catch (error) {
    console.error('Failed to load scrape limit:', error)
  }
}

async function saveScrapeLimit() {
  savingLimit.value = true
  limitResult.value = null

  try {
    await axios.post('/api/admin/settings/scrape-job-limit', {
      limit: scrapeLimit.value
    })
    const limitText = scrapeLimit.value === 0 ? 'Unlimited' : `${scrapeLimit.value} jobs`
    limitResult.value = {
      success: true,
      message: `Scrape limit set to: ${limitText}`
    }
    // Clear success message after 3 seconds
    setTimeout(() => {
      limitResult.value = null
    }, 3000)
  } catch (error: any) {
    limitResult.value = {
      success: false,
      message: error.response?.data?.detail || 'Failed to save scrape limit'
    }
  } finally {
    savingLimit.value = false
  }
}

// Sources functions
async function loadSources() {
  loadingSources.value = true
  try {
    const response = await axios.get('/api/sources')
    sources.value = response.data
  } catch (error) {
    console.error('Failed to load sources:', error)
  } finally {
    loadingSources.value = false
  }
}

async function syncSources() {
  syncingSources.value = true
  syncResult.value = null
  try {
    const response = await axios.post('/api/sources/sync')
    syncResult.value = {
      success: true,
      message: response.data.message
    }
    // Reload sources to show any new ones
    await loadSources()
    // Clear success message after 5 seconds
    setTimeout(() => {
      syncResult.value = null
    }, 5000)
  } catch (error: any) {
    syncResult.value = {
      success: false,
      message: error.response?.data?.detail || 'Failed to sync sources'
    }
  } finally {
    syncingSources.value = false
  }
}

async function toggleSource(source: ScraperSource) {
  updatingSource.value = source.name
  try {
    const response = await axios.patch(`/api/sources/${source.name}`, {
      enabled: !source.enabled
    })
    // Update the source in the list
    const index = sources.value.findIndex(s => s.name === source.name)
    if (index !== -1) {
      sources.value[index] = response.data
    }
  } catch (error: any) {
    console.error('Failed to update source:', error)
    // Show error briefly
    syncResult.value = {
      success: false,
      message: error.response?.data?.detail || `Failed to update ${source.label}`
    }
    setTimeout(() => {
      syncResult.value = null
    }, 3000)
  } finally {
    updatingSource.value = null
  }
}

function formatSettingKey(key: string): string {
  return key
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function formatSettingValue(value: any): string {
  if (Array.isArray(value)) {
    return value.join(', ')
  }
  return String(value)
}

onMounted(() => {
  loadRunFrequency()
  loadScrapeLimit()
  loadSources()
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

.label-tip {
  font-size: 0.8rem;
  color: #999;
  font-style: italic;
  margin-top: 0.25rem;
}

.setting-select {
  padding: 0.75rem;
  padding-right: 3rem !important;
  background-color: #2a2a2a;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23888' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 1rem center;
  border: 1px solid #404040;
  border-radius: 4px;
  color: #e0e0e0;
  font-size: 0.95rem;
  cursor: pointer;
  transition: border-color 0.2s;
  max-width: 400px;
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
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

/* Sources Section */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-header h2 {
  margin: 0;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background-color 0.2s;
}

.btn-secondary {
  background-color: #404040;
  color: #e0e0e0;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #505050;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.8rem;
}

.loading-message,
.empty-message {
  color: #888;
  text-align: center;
  padding: 2rem;
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.source-card {
  background: #2a2a2a;
  border: 1px solid #404040;
  border-radius: 8px;
  padding: 1.25rem;
}

.source-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
}

.source-info h3 {
  margin: 0 0 0.25rem 0;
  font-size: 1.1rem;
  color: #e0e0e0;
}

.source-name {
  font-size: 0.8rem;
  color: #666;
  font-family: monospace;
}

.source-description {
  margin: 0 0 1rem 0;
  font-size: 0.9rem;
  color: #999;
}

.source-details {
  display: flex;
  gap: 2rem;
  margin-bottom: 1rem;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.detail-label {
  font-size: 0.8rem;
  color: #888;
}

.detail-value {
  font-size: 0.9rem;
  color: #e0e0e0;
}

.badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.badge-enabled {
  background-color: rgba(34, 197, 94, 0.2);
  color: #86efac;
}

.badge-disabled {
  background-color: rgba(100, 116, 139, 0.2);
  color: #94a3b8;
}

/* Toggle Switch */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 26px;
  cursor: pointer;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #404040;
  border-radius: 13px;
  transition: 0.3s;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 20px;
  width: 20px;
  left: 3px;
  bottom: 3px;
  background-color: #e0e0e0;
  border-radius: 50%;
  transition: 0.3s;
}

.toggle-switch input:checked + .toggle-slider {
  background-color: #22c55e;
}

.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(22px);
}

.toggle-switch input:disabled + .toggle-slider {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Credentials Section */
.credentials-section {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.credentials-label {
  font-size: 0.8rem;
  color: #888;
}

.credentials-status {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.credential-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.credential-ok {
  background-color: rgba(34, 197, 94, 0.2);
  color: #86efac;
}

.credential-missing {
  background-color: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
}

.credential-none {
  background-color: rgba(100, 116, 139, 0.15);
  color: #94a3b8;
}

/* Settings Section */
.settings-section {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.settings-label {
  font-size: 0.8rem;
  color: #888;
  padding-top: 0.25rem;
}

.settings-tags {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.setting-tag {
  padding: 0.25rem 0.5rem;
  background-color: rgba(6, 182, 212, 0.15);
  border-radius: 4px;
  font-size: 0.75rem;
  color: #67e8f9;
}
</style>
