<template>
  <div class="barcode-renderer" :class="containerClass">
    <!-- Barcode SVG target -->
    <svg ref="barcodeEl" v-show="isValid"></svg>

    <!-- Fallback when no value or invalid -->
    <div v-if="!value" class="barcode-placeholder">
      <span class="text-xs text-gray-400">No barcode</span>
    </div>
    <div v-else-if="!isValid" class="barcode-error">
      <span class="text-xs text-red-400">Invalid barcode</span>
    </div>

    <!-- Optional text label below barcode -->
    <p v-if="showLabel && value && isValid" class="barcode-label">
      {{ label || value }}
    </p>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import JsBarcode from 'jsbarcode'

const props = defineProps({
  /** The barcode value to encode */
  value: {
    type: String,
    default: ''
  },
  /** Barcode format - matches Desk's CODE128 default */
  format: {
    type: String,
    default: 'CODE128'
  },
  /** Width of each bar (narrowest element) */
  width: {
    type: Number,
    default: 2
  },
  /** Height of the barcode bars in px */
  height: {
    type: Number,
    default: 40
  },
  /** Show text value below bars */
  displayValue: {
    type: Boolean,
    default: true
  },
  /** Font size for the text below bars */
  fontSize: {
    type: Number,
    default: 12
  },
  /** Font for the text below bars */
  font: {
    type: String,
    default: 'monospace'
  },
  /** Text alignment */
  textAlign: {
    type: String,
    default: 'center'
  },
  /** Text position */
  textPosition: {
    type: String,
    default: 'bottom'
  },
  /** Text margin from bars */
  textMargin: {
    type: Number,
    default: 2
  },
  /** Bar color */
  lineColor: {
    type: String,
    default: '#000000'
  },
  /** Background color */
  background: {
    type: String,
    default: '#FFFFFF'
  },
  /** Margin around the barcode */
  margin: {
    type: Number,
    default: 5
  },
  /** Show a text label below the component (separate from JsBarcode's displayValue) */
  showLabel: {
    type: Boolean,
    default: false
  },
  /** Custom label text (defaults to value) */
  label: {
    type: String,
    default: ''
  },
  /** Additional CSS class for the container */
  containerClass: {
    type: String,
    default: ''
  },
  /** Compact mode - smaller dimensions for inline/table use */
  compact: {
    type: Boolean,
    default: false
  }
})

const barcodeEl = ref(null)
const isValid = ref(true)

const renderBarcode = () => {
  if (!props.value || !barcodeEl.value) {
    isValid.value = false
    return
  }

  try {
    const options = {
      format: props.format,
      width: props.compact ? 1 : props.width,
      height: props.compact ? 25 : props.height,
      displayValue: props.displayValue,
      fontSize: props.compact ? 10 : props.fontSize,
      font: props.font,
      textAlign: props.textAlign,
      textPosition: props.textPosition,
      textMargin: props.textMargin,
      lineColor: props.lineColor,
      background: props.background,
      margin: props.compact ? 2 : props.margin,
      valid: (valid) => {
        isValid.value = valid
      }
    }

    JsBarcode(barcodeEl.value, props.value, options)
    isValid.value = true
  } catch (err) {
    console.warn('BarcodeRenderer: Failed to render barcode', props.value, err)
    isValid.value = false
  }
}

// Re-render whenever value or format changes
watch(
  () => [props.value, props.format, props.width, props.height, props.compact],
  () => {
    nextTick(() => renderBarcode())
  }
)

onMounted(() => {
  nextTick(() => renderBarcode())
})
</script>

<style scoped>
.barcode-renderer {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
}

.barcode-renderer svg {
  max-width: 100%;
  height: auto;
}

.barcode-placeholder,
.barcode-error {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  border: 1px dashed #d1d5db;
  border-radius: 4px;
  min-height: 30px;
}

.barcode-error {
  border-color: #fca5a5;
  background-color: #fef2f2;
}

.barcode-label {
  margin-top: 2px;
  font-size: 10px;
  color: #6b7280;
  text-align: center;
}

/* Print styles - make barcodes crisp and visible */
@media print {
  .barcode-renderer svg {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
}
</style>
