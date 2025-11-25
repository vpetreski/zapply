<template>
  <div class="runs">
    <!-- Profile Warning Banner -->
    <ProfileWarningBanner ref="profileBannerRef" />

    <div class="runs-header">
      <h2>Pipeline Runs ({{ total }} total)</h2>
      <div class="header-actions">
        <button
          @click="startNewRun"
          :disabled="!profileExists || hasRunningRun || startingRun"
          class="btn btn-primary start-run-btn"
          :title="!profileExists ? 'Create a profile first' : ''"
        >
          <span v-if="!profileExists">Profile Required</span>
          <span v-else-if="startingRun">Starting...</span>
          <span v-else-if="hasRunningRun">Run In Progress</span>
          <span v-else>▶ Start New Run</span>
        </button>
        <div class="filters">
        <select v-model="statusFilter" @change="resetAndFetch" class="filter-select">
          <option value="">All Statuses</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="partial">Partial</option>
        </select>
        <select v-model="phaseFilter" @change="resetAndFetch" class="filter-select">
          <option value="">All Phases</option>
          <option value="scraping">Scraping</option>
          <option value="matching">Matching</option>
          <option value="applying">Applying</option>
          <option value="reporting">Reporting</option>
        </select>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading">Loading runs...</div>

    <div v-else-if="runs.length === 0" class="empty">
      <p>No runs found. Runs will appear here after executing the pipeline.</p>
    </div>

    <div v-else>
      <div class="runs-list">
        <div v-for="run in runs" :key="run.id" class="card run-card" @click="openRunDetail(run)">
          <div class="run-header">
            <div class="run-info">
              <h3>Run #{{ run.id }}</h3>
              <div class="run-meta">
                <span :class="['badge', `badge-${run.status}`]">{{ run.status }}</span>
                <span :class="['badge', `badge-phase-${run.phase}`]">{{ run.phase }}</span>
                <span :class="['badge', 'badge-trigger']">{{ formatTriggerType(run.trigger_type) }}</span>
              </div>
            </div>
            <div class="run-times">
              <span class="text-muted">Started: {{ formatTimestamp(run.started_at) }}</span>
              <span v-if="run.completed_at" class="text-muted">
                Completed: {{ formatTimestamp(run.completed_at) }}
              </span>
              <span v-if="run.duration_seconds" class="text-muted">
                Duration: {{ formatDuration(run.duration_seconds) }}
              </span>
            </div>
          </div>

          <div v-if="run.stats" class="run-stats">
            <div class="stat-item" v-for="(value, key) in run.stats" :key="key">
              <span class="stat-label">{{ formatStatKey(key) }}:</span>
              <span class="stat-value">{{ value }}</span>
            </div>
          </div>

          <div v-if="run.error_message" class="run-error">
            <span class="error-label">Error:</span>
            {{ truncate(run.error_message, 150) }}
          </div>
        </div>
      </div>

      <!-- Infinite scroll indicators -->
      <div v-if="loadingMore" class="loading-more">
        Loading more runs...
      </div>

      <div v-if="!hasMore && runs.length > 0" class="end-message">
        No more runs to load
      </div>
    </div>

    <!-- Run Detail Modal -->
    <div v-if="selectedRun" class="modal-overlay" @click="closeRunDetail">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <div>
            <h2>Run #{{ selectedRun.id }}</h2>
            <div class="run-meta">
              <span :class="['badge', `badge-${selectedRun.status}`]">{{ selectedRun.status }}</span>
              <span :class="['badge', `badge-phase-${selectedRun.phase}`]">{{ selectedRun.phase }}</span>
              <span :class="['badge', 'badge-trigger']">{{ formatTriggerType(selectedRun.trigger_type) }}</span>
            </div>
          </div>
          <button @click="closeRunDetail" class="btn-close">×</button>
        </div>

        <div class="modal-body">
          <div class="detail-section">
            <h3>Timing</h3>
            <div class="detail-grid">
              <div>
                <span class="detail-label">Started:</span>
                <span>{{ formatTimestamp(selectedRun.started_at) }}</span>
              </div>
              <div v-if="selectedRun.completed_at">
                <span class="detail-label">Completed:</span>
                <span>{{ formatTimestamp(selectedRun.completed_at) }}</span>
              </div>
              <div v-if="selectedRun.duration_seconds">
                <span class="detail-label">Duration:</span>
                <span>{{ formatDuration(selectedRun.duration_seconds) }}</span>
              </div>
            </div>
          </div>

          <div v-if="selectedRun.stats" class="detail-section">
            <h3>Statistics</h3>
            <div class="detail-grid">
              <div v-for="(value, key) in selectedRun.stats" :key="key">
                <span class="detail-label">{{ formatStatKey(key) }}:</span>
                <span>{{ value }}</span>
              </div>
            </div>
          </div>

          <div v-if="selectedRun.logs && selectedRun.logs.length > 0" class="detail-section">
            <div class="logs-header">
              <h3>Logs ({{ selectedRun.logs.length }})</h3>
              <label class="autoscroll-toggle">
                <input type="checkbox" v-model="autoScrollEnabled" />
                <span>Auto-scroll to latest</span>
              </label>
            </div>
            <div class="logs-container">
              <div v-for="(log, index) in selectedRun.logs" :key="`${log.timestamp}-${index}`" class="log-entry">
                <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
                <span :class="['log-level', `log-level-${log.level || 'info'}`]">{{ log.level || 'INFO' }}</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </div>

          <div v-if="selectedRun.error_message" class="detail-section">
            <h3>Error Message</h3>
            <pre class="error-message">{{ selectedRun.error_message }}</pre>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeRunDetail" class="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Alert Dialog -->
  <AlertDialog
    v-model:isOpen="showAlert"
    title="Run Error"
    :message="alertMessage"
    :variant="alertVariant"
    buttonText="OK"
  />
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import AlertDialog from '@/components/AlertDialog.vue'
import ProfileWarningBanner from '@/components/ProfileWarningBanner.vue'

const runs = ref([])
const loading = ref(true)
const loadingMore = ref(false)
const statusFilter = ref('')
const phaseFilter = ref('')
const selectedRun = ref(null)
const startingRun = ref(false)
const autoScrollEnabled = ref(false)
let autoRefreshInterval = null
let listRefreshInterval = null

// Alert dialog state
const showAlert = ref(false)
const alertMessage = ref('')
const alertVariant = ref('info')

// Profile check
const profileBannerRef = ref(null)
const profileExists = ref(true) // Assume true initially to avoid flashing disabled button

// Infinite scroll
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const hasMore = computed(() => runs.value.length < total.value)
const hasRunningRun = computed(() =>
  runs.value.some(run => run.status === 'running')
)

const fetchRuns = async (append = false) => {
  if (append) {
    loadingMore.value = true
  } else {
    loading.value = true
  }

  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    if (phaseFilter.value) {
      params.phase = phaseFilter.value
    }
    const response = await axios.get('/api/runs', { params })

    if (append) {
      runs.value = [...runs.value, ...response.data.runs]
    } else {
      runs.value = response.data.runs
    }

    total.value = response.data.total
  } catch (error) {
    console.error('Failed to fetch runs:', error)
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const loadMore = () => {
  if (!loadingMore.value && hasMore.value) {
    currentPage.value++
    fetchRuns(true)
  }
}

const handleScroll = () => {
  const scrollPosition = window.innerHeight + window.scrollY
  const threshold = document.documentElement.scrollHeight - 300

  if (scrollPosition >= threshold && !loadingMore.value && hasMore.value) {
    loadMore()
  }
}

const resetAndFetch = () => {
  currentPage.value = 1
  runs.value = []
  fetchRuns()
}

const openRunDetail = (run) => {
  selectedRun.value = run
  autoScrollEnabled.value = false // Reset to unchecked when opening

  // Start auto-refresh if run is still running
  if (run.status === 'running') {
    startAutoRefresh()
  }
}

const closeRunDetail = () => {
  selectedRun.value = null
  stopAutoRefresh()
}

const startAutoRefresh = () => {
  stopAutoRefresh() // Clear any existing interval

  // Refresh immediately first
  refreshRunDetail()

  autoRefreshInterval = setInterval(async () => {
    if (selectedRun.value && selectedRun.value.status === 'running') {
      await refreshRunDetail()
    } else {
      stopAutoRefresh()
    }
  }, 2000) // Refresh every 2 seconds
}

const stopAutoRefresh = () => {
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval)
    autoRefreshInterval = null
  }
}

const truncate = (text, length) => {
  if (!text) return ''
  if (text.length <= length) return text
  return text.substring(0, length) + '...'
}

const formatTimestamp = (timestamp) => {
  if (!timestamp) return ''

  // Backend returns timezone-naive UTC timestamps - append 'Z' to parse as UTC, display in local time
  const date = new Date(timestamp + 'Z')

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

const formatDuration = (seconds) => {
  if (!seconds) return '0s'

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`
  } else {
    return `${secs}s`
  }
}

const formatStatKey = (key) => {
  // Convert snake_case to Title Case
  return key
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

const formatTriggerType = (triggerType) => {
  if (!triggerType) return 'Manual'

  const typeMap = {
    'manual': 'Manual',
    'scheduled_daily': 'Daily',
    'scheduled_hourly': 'Hourly'
  }

  return typeMap[triggerType] || triggerType
}

const formatLogTime = (timestamp) => {
  if (!timestamp) return ''

  // Backend returns timezone-naive UTC timestamps - append 'Z' to parse as UTC, display in local time
  const date = new Date(timestamp + 'Z')
  return date.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const scrollToBottomOfLogs = () => {
  if (!autoScrollEnabled.value) return

  // Wait for next tick to ensure DOM is updated
  setTimeout(() => {
    const logsContainer = document.querySelector('.logs-container')
    if (logsContainer) {
      logsContainer.scrollTop = logsContainer.scrollHeight
    }
  }, 100)
}

const refreshRunDetail = async () => {
  if (!selectedRun.value) return

  try {
    const response = await axios.get(`/api/runs/${selectedRun.value.id}`)

    // Force reactivity by creating a new object
    selectedRun.value = { ...response.data }

    // Also refresh the run in the list
    const index = runs.value.findIndex(r => r.id === selectedRun.value.id)
    if (index !== -1) {
      runs.value[index] = { ...response.data }
    }

    // Scroll to bottom of logs if enabled
    scrollToBottomOfLogs()
  } catch (error) {
    console.error('Failed to refresh run:', error)
  }
}

const startNewRun = async () => {
  if (hasRunningRun.value || startingRun.value) return

  startingRun.value = true
  try {
    const response = await axios.post('/api/scraper/run')

    // Refresh the runs list immediately to show the new run
    await resetAndFetch()

    // Find and open the newly created run
    const newRun = runs.value.find(r => r.id === response.data.run_id)
    if (newRun) {
      openRunDetail(newRun)
    }

    // Start polling for list updates
    startListRefresh()
  } catch (error) {
    if (error.response && error.response.status === 400) {
      alertMessage.value = 'No user profile found. Please create a profile before running the scraper.'
      alertVariant.value = 'danger'
      // Refresh banner to show warning
      if (profileBannerRef.value?.refresh) {
        profileBannerRef.value.refresh()
      }
    } else if (error.response && error.response.status === 409) {
      alertMessage.value = 'A run is already in progress. Please wait for it to complete.'
      alertVariant.value = 'warning'
    } else {
      alertMessage.value = 'Failed to start run: ' + (error.response?.data?.detail || error.message)
      alertVariant.value = 'danger'
    }
    showAlert.value = true
    console.error('Failed to start run:', error)
  } finally {
    startingRun.value = false
  }
}

async function checkProfile() {
  try {
    const response = await axios.get('/api/profile/exists')
    profileExists.value = response.data.exists
  } catch (error) {
    console.error('Failed to check profile:', error)
    // Assume profile exists on error
    profileExists.value = true
  }
}

const startListRefresh = () => {
  stopListRefresh()

  listRefreshInterval = setInterval(async () => {
    if (hasRunningRun.value) {
      // Just refresh page 1 to update the running run
      currentPage.value = 1
      await fetchRuns(false)
    } else {
      stopListRefresh()
    }
  }, 2000) // Refresh every 2 seconds
}

const stopListRefresh = () => {
  if (listRefreshInterval) {
    clearInterval(listRefreshInterval)
    listRefreshInterval = null
  }
}

onMounted(() => {
  checkProfile()
  fetchRuns()
  window.addEventListener('scroll', handleScroll)

  // Start list refresh if there's a running run
  if (hasRunningRun.value) {
    startListRefresh()
  }
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
  stopAutoRefresh()
  stopListRefresh()
})
</script>

<style scoped>
.runs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.runs h2 {
  font-size: 2rem;
}

.header-actions {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}

.start-run-btn {
  padding: 0.625rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  white-space: nowrap;
}

.start-run-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.filters {
  display: flex;
  gap: 1rem;
}

.filter-select {
  padding: 0.5rem 1rem;
  background-color: var(--bg-darker);
  border: 1px solid var(--border);
  border-radius: 0.375rem;
  color: var(--text);
  font-size: 0.875rem;
}

.loading, .empty {
  text-align: center;
  padding: 3rem;
  color: var(--text-muted);
}

.runs-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 2rem;
}

.run-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.run-card:hover {
  transform: translateY(-2px);
}

.run-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.run-info h3 {
  font-size: 1.25rem;
  margin-bottom: 0.5rem;
}

.run-meta {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.run-times {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.875rem;
  text-align: right;
}

.run-stats {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
  padding: 1rem;
  background-color: var(--bg-darker);
  border-radius: 0.375rem;
  margin-bottom: 1rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text);
}

.run-error {
  padding: 0.75rem;
  background-color: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 0.375rem;
  color: #fca5a5;
  font-size: 0.875rem;
}

.error-label {
  font-weight: 600;
  margin-right: 0.5rem;
}

/* Phase badges */
.badge-phase-scraping {
  background-color: rgba(59, 130, 246, 0.2);
  color: #93c5fd;
}

.badge-phase-matching {
  background-color: rgba(168, 85, 247, 0.2);
  color: #c084fc;
}

.badge-phase-applying {
  background-color: rgba(34, 197, 94, 0.2);
  color: #86efac;
}

.badge-phase-reporting {
  background-color: rgba(251, 191, 36, 0.2);
  color: #fcd34d;
}

/* Trigger type badge */
.badge-trigger {
  background-color: rgba(100, 116, 139, 0.2);
  color: #94a3b8;
}

/* Infinite Scroll */
.loading-more, .end-message {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
  font-size: 0.875rem;
}

.loading-more {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
  backdrop-filter: blur(4px);
}

.modal {
  background-color: #1a1a1a;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1.5rem;
  border-bottom: 1px solid var(--border);
}

.modal-header h2 {
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
}

.btn-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 2rem;
  cursor: pointer;
  padding: 0;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.25rem;
  transition: all 0.2s;
}

.btn-close:hover {
  background-color: var(--bg-darker);
  color: var(--text);
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
}

.detail-section {
  margin-bottom: 1.5rem;
}

.detail-section h3 {
  font-size: 1.125rem;
  margin-bottom: 0.75rem;
  color: var(--text);
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.logs-header h3 {
  margin-bottom: 0;
}

.autoscroll-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-muted);
  cursor: pointer;
  user-select: none;
}

.autoscroll-toggle input[type="checkbox"] {
  cursor: pointer;
  width: 1rem;
  height: 1rem;
}

.autoscroll-toggle:hover {
  color: var(--text);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
}

.detail-grid > div {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.logs-container {
  max-height: 400px;
  overflow-y: auto;
  background-color: #0a0a0a;
  border: 1px solid var(--border);
  border-radius: 0.375rem;
  padding: 1rem;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 0.875rem;
}

.log-entry {
  display: flex;
  gap: 0.75rem;
  padding: 0.25rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.log-entry:last-child {
  border-bottom: none;
}

.log-time {
  color: #64748b;
  flex-shrink: 0;
}

.log-level {
  flex-shrink: 0;
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.log-level-info {
  background-color: rgba(59, 130, 246, 0.2);
  color: #93c5fd;
}

.log-level-success {
  background-color: rgba(34, 197, 94, 0.2);
  color: #86efac;
}

.log-level-warning {
  background-color: rgba(251, 191, 36, 0.2);
  color: #fcd34d;
}

.log-level-error {
  background-color: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
}

.log-message {
  color: var(--text);
  flex: 1;
  word-break: break-word;
}

.error-message {
  padding: 1rem;
  background-color: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 0.375rem;
  color: #fca5a5;
  font-size: 0.875rem;
  white-space: pre-wrap;
  overflow-x: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1.5rem;
  border-top: 1px solid var(--border);
}
</style>
