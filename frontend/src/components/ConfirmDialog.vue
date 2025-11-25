<template>
  <Teleport to="body">
    <Transition name="dialog-fade">
      <div v-if="isOpen" class="dialog-overlay" @click="handleOverlayClick">
        <div class="dialog-container" @click.stop>
          <div class="dialog-header">
            <div class="dialog-icon" :class="iconClass">
              <span v-html="icon"></span>
            </div>
            <h3 class="dialog-title">{{ title }}</h3>
          </div>

          <div class="dialog-body">
            <p class="dialog-message">{{ message }}</p>
          </div>

          <div class="dialog-footer">
            <button
              class="btn btn-cancel"
              @click="handleCancel"
              :disabled="isProcessing"
            >
              {{ cancelText }}
            </button>
            <button
              class="btn btn-confirm"
              :class="confirmClass"
              @click="handleConfirm"
              :disabled="isProcessing"
            >
              <span v-if="isProcessing" class="spinner"></span>
              {{ isProcessing ? processingText : confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Props {
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  processingText?: string
  variant?: 'danger' | 'warning' | 'info' | 'success'
  isOpen?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Confirm Action',
  confirmText: 'Confirm',
  cancelText: 'Cancel',
  processingText: 'Processing...',
  variant: 'warning',
  isOpen: false
})

const emit = defineEmits<{
  confirm: []
  cancel: []
  'update:isOpen': [value: boolean]
}>()

const isProcessing = ref(false)

const icon = computed(() => {
  switch (props.variant) {
    case 'danger':
      return '⚠️'
    case 'warning':
      return '⚠️'
    case 'info':
      return 'ℹ️'
    case 'success':
      return '✓'
    default:
      return '⚠️'
  }
})

const iconClass = computed(() => `icon-${props.variant}`)

const confirmClass = computed(() => {
  switch (props.variant) {
    case 'danger':
      return 'btn-danger'
    case 'warning':
      return 'btn-warning'
    case 'info':
      return 'btn-info'
    case 'success':
      return 'btn-success'
    default:
      return 'btn-warning'
  }
})

const handleConfirm = () => {
  isProcessing.value = true
  emit('confirm')
  // Note: Parent should close dialog after async operation completes
}

const handleCancel = () => {
  if (isProcessing.value) return
  emit('cancel')
  emit('update:isOpen', false)
}

const handleOverlayClick = () => {
  if (!isProcessing.value) {
    handleCancel()
  }
}

// Expose method to reset processing state
defineExpose({
  resetProcessing: () => {
    isProcessing.value = false
  }
})
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 1rem;
}

.dialog-container {
  background: #1e1e1e;
  border: 1px solid #404040;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  max-width: 480px;
  width: 100%;
  overflow: hidden;
  animation: slideUp 0.2s ease-out;
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.dialog-header {
  padding: 1.5rem;
  text-align: center;
  border-bottom: 1px solid #333;
}

.dialog-icon {
  font-size: 3rem;
  margin-bottom: 0.75rem;
  line-height: 1;
}

.icon-danger {
  filter: drop-shadow(0 0 8px rgba(239, 68, 68, 0.4));
}

.icon-warning {
  filter: drop-shadow(0 0 8px rgba(251, 191, 36, 0.4));
}

.icon-info {
  filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.4));
}

.icon-success {
  color: #10b981;
  filter: drop-shadow(0 0 8px rgba(16, 185, 129, 0.4));
}

.dialog-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #e0e0e0;
}

.dialog-body {
  padding: 1.5rem;
}

.dialog-message {
  margin: 0;
  font-size: 0.95rem;
  color: #b0b0b0;
  line-height: 1.6;
  text-align: center;
}

.dialog-footer {
  padding: 1rem 1.5rem 1.5rem;
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

.btn {
  padding: 0.625rem 1.25rem;
  border: none;
  border-radius: 6px;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 100px;
  justify-content: center;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-cancel {
  background: #2a2a2a;
  color: #b0b0b0;
  border: 1px solid #404040;
}

.btn-cancel:hover:not(:disabled) {
  background: #333;
  border-color: #505050;
}

.btn-confirm {
  color: white;
  font-weight: 600;
}

.btn-danger {
  background: #ef4444;
}

.btn-danger:hover:not(:disabled) {
  background: #dc2626;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.btn-warning {
  background: #f59e0b;
}

.btn-warning:hover:not(:disabled) {
  background: #d97706;
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

.btn-info {
  background: #3b82f6;
}

.btn-info:hover:not(:disabled) {
  background: #2563eb;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.btn-success {
  background: #10b981;
}

.btn-success:hover:not(:disabled) {
  background: #059669;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Transition animations */
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.2s ease;
}

.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}

.dialog-fade-enter-active .dialog-container {
  animation: slideUp 0.2s ease-out;
}

.dialog-fade-leave-active .dialog-container {
  animation: slideDown 0.2s ease-in;
}

@keyframes slideDown {
  from {
    transform: translateY(0);
    opacity: 1;
  }
  to {
    transform: translateY(20px);
    opacity: 0;
  }
}

/* Responsive */
@media (max-width: 640px) {
  .dialog-container {
    max-width: 100%;
    margin: 0 1rem;
  }

  .dialog-footer {
    flex-direction: column-reverse;
  }

  .btn {
    width: 100%;
  }
}
</style>
