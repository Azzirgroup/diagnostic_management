// Vue SFC shim — declares the .vue module shape so vue-tsc resolves imports
// of single-file components whose <script> blocks aren't TypeScript.
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const component: DefineComponent<{}, {}, any>
  export default component
}
