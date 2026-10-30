import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({plugins:[vue()],server:{proxy:{'/api':{target:'http://127.0.0.1:8081',rewrite:p=>p.replace(/^\/api/,'')},'/imgs':'http://127.0.0.1:8081'}},build:{outDir:'dist'}})
