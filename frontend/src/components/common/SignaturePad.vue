<template>
  <div class="signature-pad-wrapper">
    <label v-if="label" class="block text-sm font-medium text-gray-700 mb-2">{{ label }}</label>
    <div
      class="border-2 border-dashed border-gray-300 rounded-lg bg-gray-50 relative"
      :class="{ 'border-blue-400 bg-blue-50': isDrawing }"
    >
      <canvas
        ref="canvasRef"
        class="w-full rounded-lg"
        :style="{ height: height + 'px' }"
      />
      <!-- Clear button overlay -->
      <button
        v-if="hasSignature"
        @click="clear"
        type="button"
        class="absolute top-2 right-2 p-1 bg-white rounded-full shadow-sm border border-gray-200 hover:bg-red-50 hover:border-red-200 transition-colors"
        title="Clear signature"
      >
        <svg class="w-4 h-4 text-gray-500 hover:text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
    <p v-if="!hasSignature" class="text-xs text-gray-400 mt-1 text-center">Draw your signature above</p>
    <p v-else class="text-xs text-green-600 mt-1 text-center">Signature captured</p>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: '' },
  height: { type: Number, default: 150 },
  penColor: { type: String, default: '#000000' },
  backgroundColor: { type: String, default: 'rgba(255,255,255,0)' }
})

const emit = defineEmits(['update:modelValue'])

const canvasRef = ref(null)
const hasSignature = ref(false)
const isDrawing = ref(false)

let signaturePadInstance = null

const initPad = async () => {
  if (!canvasRef.value) return

  // Dynamically import signature_pad
  try {
    const { default: SignaturePad } = await import('signature_pad')

    // Set canvas resolution for retina
    const canvas = canvasRef.value
    const ratio = Math.max(window.devicePixelRatio || 1, 1)
    canvas.width = canvas.offsetWidth * ratio
    canvas.height = props.height * ratio
    canvas.getContext('2d').scale(ratio, ratio)

    signaturePadInstance = new SignaturePad(canvas, {
      penColor: props.penColor,
      backgroundColor: props.backgroundColor,
      minWidth: 0.5,
      maxWidth: 2.5
    })

    signaturePadInstance.addEventListener('beginStroke', () => {
      isDrawing.value = true
    })

    signaturePadInstance.addEventListener('endStroke', () => {
      isDrawing.value = false
      hasSignature.value = !signaturePadInstance.isEmpty()
      emit('update:modelValue', signaturePadInstance.toDataURL('image/png'))
    })

    // Restore existing signature
    if (props.modelValue) {
      signaturePadInstance.fromDataURL(props.modelValue)
      hasSignature.value = true
    }
  } catch (e) {
    console.error('Failed to load signature_pad:', e)
  }
}

const clear = () => {
  if (signaturePadInstance) {
    signaturePadInstance.clear()
    hasSignature.value = false
    emit('update:modelValue', '')
  }
}

const handleResize = () => {
  if (!canvasRef.value || !signaturePadInstance) return
  const data = signaturePadInstance.toData()
  const canvas = canvasRef.value
  const ratio = Math.max(window.devicePixelRatio || 1, 1)
  canvas.width = canvas.offsetWidth * ratio
  canvas.height = props.height * ratio
  canvas.getContext('2d').scale(ratio, ratio)
  signaturePadInstance.clear()
  signaturePadInstance.fromData(data)
}

onMounted(async () => {
  await nextTick()
  initPad()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (signaturePadInstance) {
    signaturePadInstance.off()
  }
})

defineExpose({ clear })
</script>
