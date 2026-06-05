import type { Plugin } from 'vite'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  appType: 'mpa',
  root: 'src',
  base: './',
  publicDir: '../public',
  cacheDir: '../node_modules/.vite',
  resolve: {
    extensions: ['.js', '.ts', '.json', '.vue']
  },
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    target: 'esnext',
    modulePreload: false,
    cssCodeSplit: false,
    minify: false,
    rollupOptions: {
      output: {
        minifyInternalExports: false
      }
    }
  },
  plugins: [
    vue(),
    {
      name: 'view-ui-plus',
      enforce: 'pre',
      apply: 'build',
      resolveId(source, importer, options) {
        if (source === 'view-ui-plus') { return source }
      },
      load(id) {
        if (id === 'view-ui-plus') {
          return `\
export * from 'view-ui-plus/src/components/index'
import pkg from 'view-ui-plus/package.json'
export const version = pkg.version`
        }
      }
    },
    {
      name: 'html-transform',
      transformIndexHtml(html, { chunk, bundle }) {
        if (chunk == null || bundle == null) { return }
        return {
          html: html.replace(/(?<=\<script type="module"\s+)crossorigin\s+/g, ''),
          tags: [...function* () {
            for (const href of chunk.dynamicImports) {
              yield {
                tag: 'link',
                attrs: { rel: 'modulepreload', href: `./${href}` },
                injectTo: 'head' as 'head'
              }
            }
          }()]
        }
      }
    }
  ]
})
