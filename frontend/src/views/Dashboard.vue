<template>
  <div class="dashboard">
    <!-- Profile Warning Banner -->
    <ProfileWarningBanner />

    <h2>Dashboard</h2>

    <div class="grid grid-3" style="margin-top: 2rem;">
      <div class="card stat-card">
        <h3>Total Jobs</h3>
        <p class="stat-value">{{ stats.total_jobs }}</p>
      </div>
      <div class="card stat-card">
        <h3>Matched</h3>
        <p class="stat-value text-success">{{ stats.matched_jobs }}</p>
      </div>
      <div class="card stat-card">
        <h3>Applied</h3>
        <p class="stat-value text-success">{{ stats.applied_jobs }}</p>
      </div>
    </div>

    <div class="card" style="margin-top: 2rem;">
      <div class="activity-header">
        <h3>Recent Activity</h3>
        <span class="auto-refresh-indicator">📡 Live</span>
      </div>

      <div v-if="latestRun" class="recent-activity">
        <!-- Run Status Badge -->
        <div class="run-status-bar">
          <div class="run-info">
            <span class="run-label">Run #{{ latestRun.id }}</span>
            <span :class="['status-badge', `status-${latestRun.status}`]">
              {{ latestRun.status }}
            </span>
            <span class="phase-badge">{{ latestRun.phase }}</span>
          </div>
          <div class="run-time">
            {{ formatRunTime(latestRun) }}
          </div>
        </div>

        <!-- Run Stats (if available) -->
        <div v-if="latestRun.stats" class="run-stats">
          <div v-if="latestRun.stats.jobs_scraped" class="stat-item">
            📊 Scraped: <strong>{{ latestRun.stats.jobs_scraped }}</strong>
          </div>
          <div v-if="latestRun.stats.new_jobs !== undefined" class="stat-item">
            ✨ New: <strong>{{ latestRun.stats.new_jobs }}</strong>
          </div>
          <div v-if="latestRun.stats.jobs_matched !== undefined" class="stat-item">
            ✅ Matched: <strong>{{ latestRun.stats.jobs_matched }}</strong>
          </div>
          <div v-if="latestRun.stats.jobs_rejected !== undefined" class="stat-item">
            ❌ Rejected: <strong>{{ latestRun.stats.jobs_rejected }}</strong>
          </div>
          <div v-if="latestRun.stats.average_match_score" class="stat-item">
            📈 Avg Score: <strong>{{ latestRun.stats.average_match_score }}/100</strong>
          </div>
        </div>

        <!-- Last 5 Log Entries -->
        <div v-if="latestRun.logs && latestRun.logs.length > 0" class="run-logs">
          <h4>Recent Logs</h4>
          <div v-for="(log, index) in latestRun.logs" :key="index" :class="['log-entry', `log-${log.level}`]">
            <span class="log-timestamp">{{ formatLogTime(log.timestamp) }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </div>

        <!-- Error Message (if any) -->
        <div v-if="latestRun.error_message" class="error-message">
          ⚠️ Error: {{ latestRun.error_message }}
        </div>

        <!-- Link to full run details -->
        <div class="run-actions">
          <router-link :to="`/runs`" class="btn btn-secondary btn-sm">
            View All Runs →
          </router-link>
        </div>
      </div>

      <div v-else class="no-activity">
        <p class="text-muted">
          No recent activity. System is ready. Check the Jobs page to see scraped positions.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import ProfileWarningBanner from '@/components/ProfileWarningBanner.vue'

const stats = ref({
  total_jobs: 0,
  new_jobs: 0,
  matched_jobs: 0,
  rejected_jobs: 0,
  applied_jobs: 0,
  failed_jobs: 0,
  success_rate: 0
})

const latestRun = ref(null)

const fetchStats = async () => {
  try {
    const response = await axios.get('/api/stats')
    stats.value = response.data
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  }
}

const fetchLatestRun = async () => {
  try {
    const response = await axios.get('/api/runs/latest')
    latestRun.value = response.data
  } catch (error) {
    console.error('Failed to fetch latest run:', error)
  }
}

const formatRunTime = (run) => {
  if (run.status === 'running') {
    const start = new Date(run.started_at)
    const now = new Date()
    const elapsed = Math.floor((now - start) / 1000)
    const minutes = Math.floor(elapsed / 60)
    const seconds = elapsed % 60
    return `Running for ${minutes}m ${seconds}s`
  } else if (run.completed_at) {
    return `Completed ${formatRelativeTime(run.completed_at)}`
  } else {
    return `Started ${formatRelativeTime(run.started_at)}`
  }
}

const formatRelativeTime = (timestamp) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = Math.floor((now - date) / 1000)

  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

const formatLogTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// Auto-refresh intervals
let statsInterval = null
let runInterval = null

onMounted(() => {
  fetchStats()
  fetchLatestRun()

  // Refresh stats every 10 seconds
  statsInterval = setInterval(fetchStats, 10000)

  // Refresh latest run every 3 seconds (more frequent for live updates)
  runInterval = setInterval(fetchLatestRun, 3000)
})

onUnmounted(() => {
  if (statsInterval) clearInterval(statsInterval)
  if (runInterval) clearInterval(runInterval)
})
</script>

<style scoped>
.dashboard h2 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.stat-card h3 {
  color: var(--text-muted);
  font-size: 0.875rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 2.5rem;
  font-weight: 700;
  margin-top: 0.5rem;
}

.activity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.activity-header h3 {
  margin: 0;
}

.auto-refresh-indicator {
  font-size: 0.85rem;
  color: #10b981;
  font-weight: 500;
  cursor: default;
  user-select: none;
  text-decoration: none;
}

.recent-activity {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.run-status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: #2a2a2a;
  border-radius: 6px;
  border: 1px solid #404040;
}

.run-info {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.run-label {
  font-weight: 600;
  color: #e0e0e0;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-running {
  background: #1e40af;
  color: #93c5fd;
}

.status-completed {
  background: #166534;
  color: #86efac;
}

.status-failed {
  background: #991b1b;
  color: #fca5a5;
}

.status-partial {
  background: #854d0e;
  color: #fde047;
}

.phase-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.75rem;
  background: #404040;
  color: #888;
}

.run-time {
  color: #888;
  font-size: 0.875rem;
}

.run-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 1rem;
  background: #1e1e1e;
  border-radius: 6px;
}

.stat-item {
  color: #888;
  font-size: 0.9rem;
}

.stat-item strong {
  color: #e0e0e0;
}

.run-logs {
  padding: 1rem;
  background: #1a1a1a;
  border-radius: 6px;
}

.run-logs h4 {
  margin-top: 0;
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.log-entry {
  display: flex;
  gap: 1rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid #2a2a2a;
  font-size: 0.85rem;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
}

.log-entry:last-child {
  border-bottom: none;
}

.log-timestamp {
  color: #666;
  flex-shrink: 0;
}

.log-message {
  color: #e0e0e0;
}

.log-info .log-message {
  color: #4a9eff;
}

.log-success .log-message {
  color: #10b981;
}

.log-error .log-message {
  color: #ef4444;
}

.error-message {
  padding: 1rem;
  background: #1a1515;
  border: 1px solid #ff4444;
  border-radius: 6px;
  color: #fca5a5;
}

.run-actions {
  display: flex;
  justify-content: flex-end;
}

.btn-sm {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
}

.no-activity {
  text-align: center;
  padding: 2rem;
}
</style>
