<template>
  <div class="rich-text-editor">
    <div class="editor-toolbar" v-if="editor">
      <button
        type="button"
        @click="editor.chain().focus().toggleBold().run()"
        :class="{ active: editor.isActive('bold') }"
        title="Bold"
      >
        <strong>B</strong>
      </button>
      <button
        type="button"
        @click="editor.chain().focus().toggleHeading({ level: 2 }).run()"
        :class="{ active: editor.isActive('heading', { level: 2 }) }"
        title="Heading 2"
      >
        H2
      </button>
      <button
        type="button"
        @click="editor.chain().focus().toggleHeading({ level: 3 }).run()"
        :class="{ active: editor.isActive('heading', { level: 3 }) }"
        title="Heading 3"
      >
        H3
      </button>
      <button
        type="button"
        @click="editor.chain().focus().toggleBulletList().run()"
        :class="{ active: editor.isActive('bulletList') }"
        title="Bullet List"
      >
        &bull; List
      </button>
      <button
        type="button"
        @click="editor.chain().focus().toggleOrderedList().run()"
        :class="{ active: editor.isActive('orderedList') }"
        title="Numbered List"
      >
        1. List
      </button>
      <button
        type="button"
        @click="setLink"
        :class="{ active: editor.isActive('link') }"
        title="Add Link"
      >
        Link
      </button>
      <button
        type="button"
        v-if="editor.isActive('link')"
        @click="editor.chain().focus().unsetLink().run()"
        title="Remove Link"
      >
        Unlink
      </button>
    </div>
    <EditorContent :editor="editor" class="editor-content" />
  </div>
</template>

<script setup lang="ts">
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import { watch, onBeforeUnmount } from 'vue'

interface Props {
  modelValue?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: ''
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const editor = useEditor({
  content: props.modelValue,
  extensions: [
    StarterKit.configure({
      heading: {
        levels: [2, 3]
      }
    }),
    Link.configure({
      openOnClick: false,
      HTMLAttributes: {
        target: '_blank',
        rel: 'noopener noreferrer'
      }
    })
  ],
  onUpdate: () => {
    if (editor.value) {
      emit('update:modelValue', editor.value.getHTML())
    }
  }
})

watch(() => props.modelValue, (value) => {
  if (editor.value && value !== editor.value.getHTML()) {
    editor.value.commands.setContent(value || '', false)
  }
})

onBeforeUnmount(() => {
  if (editor.value) {
    editor.value.destroy()
  }
})

const setLink = () => {
  if (!editor.value) return

  const previousUrl = editor.value.getAttributes('link').href
  const url = window.prompt('Enter URL:', previousUrl)

  if (url === null) {
    return
  }

  if (url === '') {
    editor.value.chain().focus().extendMarkRange('link').unsetLink().run()
    return
  }

  // Validate URL protocol to prevent javascript: XSS
  if (!url.match(/^(https?:|mailto:)/i)) {
    alert('Only http, https, and mailto links are allowed')
    return
  }

  editor.value.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
}
</script>

<style scoped>
.rich-text-editor {
  border: 1px solid #404040;
  border-radius: 8px;
  background-color: #1a1a1a;
  overflow: hidden;
}

.editor-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 8px;
  border-bottom: 1px solid #404040;
  background-color: #252525;
}

.editor-toolbar button {
  padding: 6px 10px;
  background: transparent;
  border: 1px solid #404040;
  border-radius: 4px;
  color: #b0b0b0;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.editor-toolbar button:hover {
  background-color: #333;
  border-color: #505050;
  color: #e0e0e0;
}

.editor-toolbar button.active {
  background-color: #3b82f6;
  border-color: #3b82f6;
  color: white;
}

.editor-content {
  padding: 12px;
  min-height: 200px;
  max-height: 400px;
  overflow-y: auto;
}

.editor-content :deep(.ProseMirror) {
  outline: none;
  min-height: 180px;
  color: #e0e0e0;
  font-size: 14px;
  line-height: 1.6;
}

.editor-content :deep(.ProseMirror p) {
  margin: 0 0 0.75em 0;
}

.editor-content :deep(.ProseMirror h2) {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 1em 0 0.5em 0;
  color: #f0f0f0;
}

.editor-content :deep(.ProseMirror h3) {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 1em 0 0.5em 0;
  color: #f0f0f0;
}

.editor-content :deep(.ProseMirror ul),
.editor-content :deep(.ProseMirror ol) {
  padding-left: 1.5em;
  margin: 0.5em 0;
}

.editor-content :deep(.ProseMirror li) {
  margin: 0.25em 0;
}

.editor-content :deep(.ProseMirror a) {
  color: #3b82f6;
  text-decoration: underline;
  cursor: pointer;
}

.editor-content :deep(.ProseMirror a:hover) {
  color: #60a5fa;
}

.editor-content :deep(.ProseMirror strong) {
  font-weight: 600;
  color: #f0f0f0;
}

.editor-content :deep(.ProseMirror p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  color: #666;
  pointer-events: none;
  height: 0;
}
</style>
