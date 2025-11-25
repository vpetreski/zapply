<template>
  <div class="profile-container">
    <!-- Profile Warning Banner -->
    <ProfileWarningBanner ref="profileBannerRef" />

    <h1>👤 User Profile</h1>

    <!-- Loading State -->
    <div v-if="loading && !profile" class="loading">
      <p>🔄 Loading profile...</p>
    </div>

    <!-- No Profile State -->
    <div v-else-if="!profile && !editMode" class="no-profile">
      <h2>No Profile Found</h2>
      <p>Create your profile to start matching jobs with AI.</p>
      <button @click="startCreate" class="btn-primary">
        ➕ Create Profile
      </button>
    </div>

    <!-- View Mode -->
    <div v-else-if="!editMode && profile" class="profile-view">
      <!-- Basic Info -->
      <section class="profile-section">
        <div class="section-header">
          <h2>📋 Basic Information</h2>
          <div class="action-buttons">
            <button @click="startEdit" class="btn-primary">
              ✏️ Edit Profile
            </button>
            <button @click="confirmDelete" class="btn-danger-outline">
              🗑️ Delete
            </button>
          </div>
        </div>

        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">Name:</span>
            <span class="info-value">{{ profile.name }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Email:</span>
            <span class="info-value">{{ profile.email }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Phone:</span>
            <span class="info-value">{{ profile.phone || 'Not provided' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Location:</span>
            <span class="info-value">{{ profile.location }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Rate:</span>
            <span class="info-value">{{ profile.rate }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">CV File:</span>
            <span class="info-value">{{ profile.cv_filename || 'Not uploaded' }}</span>
          </div>
        </div>
      </section>

      <!-- Custom Instructions -->
      <section class="profile-section">
        <h2>📝 Custom Instructions</h2>
        <div class="instructions-text">{{ profile.custom_instructions || 'No custom instructions provided' }}</div>
      </section>

      <!-- AI-Generated Profile -->
      <section class="profile-section ai-section">
        <h2>🤖 AI-Generated Profile (Used for Job Matching)</h2>

        <div v-if="profile.ai_generated_summary" class="ai-summary">
          <strong>Summary:</strong> {{ profile.ai_generated_summary }}
        </div>

        <div class="ai-subsection">
          <h3>Skills ({{ profile.skills?.length || 0 }})</h3>
          <div class="skills-container">
            <span v-for="skill in profile.skills" :key="skill" class="skill-badge">
              {{ skill }}
            </span>
          </div>
        </div>

        <div class="ai-subsection">
          <h3>Preferences</h3>
          <pre class="json-display">{{ JSON.stringify(profile.preferences, null, 2) }}</pre>
        </div>

        <div class="ai-subsection">
          <h3>Profile Text</h3>
          <div class="cv-text">{{ profile.cv_text }}</div>
        </div>
      </section>

      <!-- Timestamps -->
      <section class="profile-section timestamps">
        <div class="timestamp-item">
          <span class="info-label">Created:</span>
          <span class="info-value">{{ formatDate(profile.created_at) }}</span>
        </div>
        <div class="timestamp-item">
          <span class="info-label">Updated:</span>
          <span class="info-value">{{ formatDate(profile.updated_at) }}</span>
        </div>
      </section>
    </div>

    <!-- Edit / Create Mode -->
    <div v-else class="profile-edit">
      <h2>{{ profile ? '✏️ Edit Profile' : '➕ Create Profile' }}</h2>

      <!-- Step 1: Basic Information -->
      <section class="profile-section">
        <h3>Step 1: Basic Information</h3>
        <div class="form-grid">
          <div class="form-field">
            <label>Name *</label>
            <input v-model="formData.name" type="text" required />
          </div>
          <div class="form-field">
            <label>Email *</label>
            <input v-model="formData.email" type="email" required />
          </div>
          <div class="form-field">
            <label>Phone</label>
            <input v-model="formData.phone" type="text" placeholder="e.g. +573001419270" />
          </div>
          <div class="form-field">
            <label>Location *</label>
            <input v-model="formData.location" type="text" required />
          </div>
          <div class="form-field">
            <label>Rate *</label>
            <input v-model="formData.rate" type="text" placeholder="e.g. $10,000/month" required />
          </div>
        </div>
      </section>

      <!-- Step 2: Upload CV PDF -->
      <section class="profile-section">
        <h3>Step 2: Upload Your CV (PDF)</h3>
        <p class="help-text">
          Upload your CV as a PDF file. The text will be extracted and used for AI profile generation.
        </p>
        <div class="upload-section">
          <button @click="$refs.fileInput.click()" class="btn-secondary">
            📎 {{ uploadedFile ? 'Change PDF File' : 'Choose PDF File' }}
          </button>
          <input
            type="file"
            accept=".pdf"
            @change="handleFileUpload"
            ref="fileInput"
            style="display: none"
          />
          <span v-if="uploadedFile" class="file-info">
            <span class="file-name">{{ uploadedFile.name }}</span>
            <span class="file-size">({{ formatFileSize(uploadedFile.size) }})</span>
          </span>
          <span v-else-if="profile?.cv_filename" class="file-name">
            Current: {{ profile.cv_filename }}
          </span>
        </div>
        <div v-if="uploadError" class="error-inline">{{ uploadError }}</div>
      </section>

      <!-- Step 3: Custom Instructions -->
      <section class="profile-section">
        <h3>Step 3: Custom Instructions for AI</h3>
        <p class="help-text">
          Provide all your preferences, requirements, and constraints here. This is where you specify everything: remote-only, contractor status, work authorization restrictions, preferred industries, roles, etc. The AI will use this to generate your profile and match jobs.
        </p>
        <textarea
          v-model="formData.customInstructions"
          rows="12"
          placeholder="Example:&#10;&#10;- I'm located in Colombia with Colombian and Serbian citizenship&#10;- NO US work authorization - can only work for companies that hire international contractors or in Latam&#10;- 100% remote work only - no hybrid or office-based positions&#10;- Contractor arrangement only&#10;- Looking for Principal/Staff Engineer roles in backend, architecture, or tech leadership&#10;- Strong preference for companies in fintech, SaaS, or developer tools&#10;- Rate expectation: $10,000-15,000/month&#10;- Focus on roles using Java, Kotlin, Spring Boot, or similar backend technologies"
          class="custom-instructions-textarea"
        ></textarea>
      </section>

      <!-- Step 4: Generate Profile -->
      <section class="profile-section">
        <h3>Step 4: Generate Profile with AI</h3>
        <p class="help-text">
          Claude will analyze your CV and custom instructions to create an optimized profile for job matching.
        </p>
        <button
          @click="generateProfile"
          class="btn-primary btn-large"
          :disabled="generating || !canGenerate"
        >
          {{ generating ? '🤖 Generating with Claude AI...' : '✨ Generate Profile' }}
        </button>
        <div v-if="!canGenerate" class="validation-message">
          Please fill in all required fields (Name, Email, Location, Rate, CV, Custom Instructions)
        </div>
      </section>

      <!-- Generated Profile Preview -->
      <section v-if="generatedProfile" class="profile-section generated-preview">
        <h3>✨ Generated Profile Preview</h3>

        <div class="generation-summary">
          <strong>Summary:</strong> {{ generatedProfile.generated_summary }}
        </div>

        <div class="preview-section">
          <h4>Skills ({{ generatedProfile.skills.length }})</h4>
          <div class="skills-container">
            <span v-for="skill in generatedProfile.skills" :key="skill" class="skill-badge">
              {{ skill }}
            </span>
          </div>
        </div>

        <div class="preview-section">
          <h4>Preferences</h4>
          <pre class="json-display">{{ JSON.stringify(generatedProfile.preferences, null, 2) }}</pre>
        </div>

        <div class="preview-section">
          <h4>Profile Text</h4>
          <div class="cv-text">{{ generatedProfile.cv_text }}</div>
        </div>

        <div class="save-section">
          <button @click="saveProfile" class="btn-primary btn-large" :disabled="saving">
            {{ saving ? '💾 Saving...' : '💾 Save Profile' }}
          </button>
          <button @click="cancelEdit" class="btn-secondary">
            Cancel
          </button>
        </div>
      </section>

      <!-- Cancel if not generated yet -->
      <div v-else class="action-buttons">
        <button @click="cancelEdit" class="btn-secondary">
          Cancel
        </button>
      </div>

      <!-- Error Message -->
      <div v-if="error" class="error-message">
        ❌ {{ error }}
      </div>
    </div>
  </div>

  <!-- Delete Confirmation Dialog -->
  <ConfirmDialog
    v-model:isOpen="showDeleteDialog"
    title="Delete Profile"
    message="This will permanently delete your profile! All profile data including CV, skills, and preferences will be removed. This action cannot be undone."
    confirmText="Delete Profile"
    cancelText="Cancel"
    processingText="Deleting..."
    variant="danger"
    @confirm="handleDeleteConfirm"
  />
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import ProfileWarningBanner from '@/components/ProfileWarningBanner.vue'

interface Profile {
  id: number
  name: string
  email: string
  phone: string | null
  location: string
  rate: string
  cv_filename: string | null
  cv_text: string | null
  custom_instructions: string | null
  skills: string[] | null
  preferences: Record<string, any> | null
  ai_generated_summary: string | null
  created_at: string
  updated_at: string
}

interface GeneratedProfile {
  cv_text: string
  skills: string[]
  preferences: Record<string, any>
  generated_summary: string
}

const route = useRoute()
const loading = ref(false)
const generating = ref(false)
const saving = ref(false)
const profile = ref<Profile | null>(null)
const editMode = ref(false)
const error = ref('')
const uploadError = ref('')
const showDeleteDialog = ref(false)
const profileBannerRef = ref(null)

const formData = ref({
  name: '',
  email: '',
  phone: '',
  location: '',
  rate: '',
  cvText: '',
  cvFileData: '',
  cvFilename: '',
  customInstructions: ''
})

const uploadedFile = ref<File | null>(null)
const generatedProfile = ref<GeneratedProfile | null>(null)

const canGenerate = computed(() => {
  return formData.value.name &&
         formData.value.email &&
         formData.value.location &&
         formData.value.rate &&
         formData.value.cvText &&
         formData.value.customInstructions
})

async function loadProfile() {
  loading.value = true
  error.value = ''
  try {
    const response = await axios.get('/api/profile')
    profile.value = response.data
  } catch (err: any) {
    if (err.response?.status !== 404) {
      error.value = 'Failed to load profile'
    }
  } finally {
    loading.value = false
  }
}

function startCreate() {
  editMode.value = true
  formData.value = {
    name: '',
    email: '',
    phone: '',
    location: '',
    rate: '',
    cvText: '',
    cvFileData: '',
    cvFilename: '',
    customInstructions: ''
  }
  uploadedFile.value = null
  generatedProfile.value = null
}

function startEdit() {
  if (!profile.value) return

  editMode.value = true
  formData.value = {
    name: profile.value.name,
    email: profile.value.email,
    phone: profile.value.phone || '',
    location: profile.value.location,
    rate: profile.value.rate,
    cvText: profile.value.cv_text || '',
    cvFileData: '',
    cvFilename: profile.value.cv_filename || '',
    customInstructions: profile.value.custom_instructions || ''
  }
  uploadedFile.value = null
  generatedProfile.value = null
}

function cancelEdit() {
  editMode.value = false
  generatedProfile.value = null
  uploadedFile.value = null
  error.value = ''
  uploadError.value = ''
}

async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]

  if (!file) return

  uploadError.value = ''
  uploadedFile.value = file

  try {
    const formDataUpload = new FormData()
    formDataUpload.append('file', file)

    const response = await axios.post('/api/profile/upload-cv', formDataUpload, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    formData.value.cvText = response.data.text
    formData.value.cvFileData = response.data.file_data
    formData.value.cvFilename = response.data.filename
  } catch (err: any) {
    uploadError.value = `Failed to upload CV: ${err.response?.data?.detail || err.message}`
    uploadedFile.value = null
  }
}

async function generateProfile() {
  if (!canGenerate.value) return

  generating.value = true
  error.value = ''

  try {
    const response = await axios.post('/api/profile/generate', {
      cv_text: formData.value.cvText,
      custom_instructions: formData.value.customInstructions,
      name: formData.value.name,
      email: formData.value.email,
      phone: formData.value.phone || null,
      location: formData.value.location,
      rate: formData.value.rate
    })

    generatedProfile.value = response.data
  } catch (err: any) {
    error.value = `Failed to generate profile: ${err.response?.data?.detail || err.message}`
  } finally {
    generating.value = false
  }
}

async function saveProfile() {
  if (!generatedProfile.value) return

  saving.value = true
  error.value = ''

  try {
    await axios.put('/api/profile', {
      name: formData.value.name,
      email: formData.value.email,
      phone: formData.value.phone || null,
      location: formData.value.location,
      rate: formData.value.rate,
      cv_filename: formData.value.cvFilename || null,
      cv_data_base64: formData.value.cvFileData || null,
      cv_text: generatedProfile.value.cv_text,
      custom_instructions: formData.value.customInstructions,
      skills: generatedProfile.value.skills,
      preferences: generatedProfile.value.preferences,
      ai_generated_summary: generatedProfile.value.generated_summary
    })

    // Reload profile and exit edit mode
    await loadProfile()
    editMode.value = false
    generatedProfile.value = null
    uploadedFile.value = null

    // Refresh banner to hide warning now that profile exists
    if (profileBannerRef.value?.refresh) {
      profileBannerRef.value.refresh()
    }
  } catch (err: any) {
    error.value = `Failed to save profile: ${err.response?.data?.detail || err.message}`
  } finally {
    saving.value = false
  }
}

function confirmDelete() {
  showDeleteDialog.value = true
}

async function handleDeleteConfirm() {
  loading.value = true
  error.value = ''

  try {
    await axios.delete('/api/profile')
    profile.value = null
    showDeleteDialog.value = false

    // Refresh banner to show warning now that profile is deleted
    if (profileBannerRef.value?.refresh) {
      profileBannerRef.value.refresh()
    }
  } catch (err: any) {
    error.value = `Failed to delete profile: ${err.response?.data?.detail || err.message}`
    showDeleteDialog.value = false
  } finally {
    loading.value = false
  }
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString()
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

onMounted(() => {
  loadProfile()

  // If route has query param 'create=true', automatically start create mode
  if (route.query.create === 'true' && !profile.value) {
    startCreate()
  }
})
</script>

<style scoped>
.profile-container {
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  margin-bottom: 2rem;
  color: #e0e0e0;
}

.loading, .no-profile {
  text-align: center;
  padding: 3rem;
  background: #1e1e1e;
  border-radius: 8px;
  border: 1px solid #333;
}

.no-profile h2 {
  color: #888;
  margin-bottom: 1rem;
}

.no-profile p {
  color: #666;
  margin-bottom: 2rem;
}

.profile-section {
  background: #1e1e1e;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  border: 1px solid #333;
}

.profile-section h2, .profile-section h3 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #e0e0e0;
}

.profile-section h3 {
  font-size: 1.2rem;
  color: #4a9eff;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-header h2 {
  margin: 0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.info-label {
  font-size: 0.85rem;
  color: #888;
  font-weight: 500;
}

.info-value {
  font-size: 1rem;
  color: #e0e0e0;
}

.instructions-text {
  background: #0a0a0a;
  color: #e0e0e0;
  padding: 1.5rem;
  border-radius: 4px;
  white-space: pre-wrap;
  line-height: 1.6;
  border: 1px solid #333;
  max-height: 400px;
  overflow-y: auto;
}

.ai-section {
  border: 2px solid #4a9eff;
  background: #1a2a3a;
}

.ai-summary {
  background: #0a1a2a;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
  color: #8bb4e0;
  border-left: 4px solid #4a9eff;
}

.ai-subsection {
  margin-bottom: 1.5rem;
}

.ai-subsection:last-child {
  margin-bottom: 0;
}

.ai-subsection h3 {
  font-size: 1rem;
  color: #4a9eff;
  margin-bottom: 0.75rem;
}

.skills-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.skill-badge {
  background: #2a4a6a;
  color: #8bb4e0;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 500;
}

.json-display {
  background: #0a0a0a;
  color: #4a9eff;
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.9rem;
  border: 1px solid #333;
}

.cv-text {
  background: #0a0a0a;
  color: #e0e0e0;
  padding: 1.5rem;
  border-radius: 4px;
  white-space: pre-wrap;
  line-height: 1.6;
  border: 1px solid #333;
  max-height: 600px;
  overflow-y: auto;
}

.timestamps {
  display: flex;
  gap: 2rem;
  background: #151515;
}

.timestamp-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.action-buttons {
  display: flex;
  gap: 1rem;
}

.btn-primary, .btn-secondary, .btn-danger-outline {
  padding: 0.6rem 1.2rem;
  border-radius: 4px;
  border: none;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #4a9eff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #6ab0ff;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #404040;
  color: white;
}

.btn-secondary:hover {
  background: #555;
}

.btn-danger-outline {
  background: transparent;
  color: #ff6666;
  border: 1px solid #ff4444;
}

.btn-danger-outline:hover {
  background: #3a1a1a;
  border-color: #ff6666;
}

.btn-large {
  padding: 1rem 2rem;
  font-size: 1.1rem;
}

/* Edit Mode Styles */
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field label {
  color: #e0e0e0;
  font-weight: 500;
  font-size: 0.9rem;
}

.form-field input {
  background: #0a0a0a;
  color: #e0e0e0;
  border: 1px solid #333;
  border-radius: 4px;
  padding: 0.7rem;
  font-size: 0.95rem;
}

.form-field input:focus {
  outline: none;
  border-color: #4a9eff;
}

.upload-section {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.file-info {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.file-name {
  color: #4a9eff;
  font-size: 0.9rem;
  font-weight: 500;
}

.file-size {
  color: #888;
  font-size: 0.85rem;
}

.help-text {
  color: #888;
  font-size: 0.9rem;
  margin-bottom: 1rem;
  line-height: 1.5;
}

.custom-instructions-textarea {
  width: 100%;
  background: #0a0a0a;
  color: #e0e0e0;
  border: 1px solid #333;
  border-radius: 4px;
  padding: 1rem;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 0.95rem;
  line-height: 1.6;
  resize: vertical;
  min-height: 300px;
}

.custom-instructions-textarea:focus {
  outline: none;
  border-color: #4a9eff;
}

.validation-message {
  color: #ff9966;
  font-size: 0.9rem;
  margin-top: 1rem;
  font-style: italic;
}

.generated-preview {
  border: 2px solid #4a9eff;
  background: #1a2a3a;
}

.generation-summary {
  background: #0a1a2a;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
  color: #8bb4e0;
  border-left: 4px solid #4a9eff;
}

.preview-section {
  margin-bottom: 1.5rem;
}

.preview-section h4 {
  color: #4a9eff;
  margin-bottom: 0.75rem;
}

.save-section {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #333;
}

.error-message {
  background: #3a1a1a;
  color: #ff6666;
  padding: 1rem;
  border-radius: 4px;
  border: 1px solid #ff4444;
  margin-top: 1rem;
}

.error-inline {
  color: #ff6666;
  font-size: 0.9rem;
  margin-top: 0.5rem;
}
</style>
