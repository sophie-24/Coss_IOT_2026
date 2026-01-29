import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      // '@'를 'src' 폴더의 절대 경로로 연결합니다.
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})