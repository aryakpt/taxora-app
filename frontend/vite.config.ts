import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { darkTheme } from './theme/darkTheme'

export default defineConfig({ plugins: [react()], css: { postcss: { plugins: [darkTheme()] } } })
