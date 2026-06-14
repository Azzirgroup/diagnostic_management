// Local re-export shim for the `frappe-ui` import name used by ShiftList.vue
// (and any other ported pages). Maps the symbols to the local replacements
// already present under @/components/ui — so the SPA can build without the
// external `frappe-ui` package as a runtime dep.
export { call } from '@/api/client'
export { default as FeatherIcon } from '@/components/ui/FeatherIcon.vue'
export { default as Input } from '@/components/ui/FInput.vue'
// Button + Dialog: lightweight passthroughs (Button = a styled <button>,
// Dialog = a basic teleported overlay). They mimic the frappe-ui API
// loosely — enough for the ported ShiftList screens to render.
export { default as Button } from '@/shims/Button.vue'
export { default as Dialog } from '@/shims/Dialog.vue'
