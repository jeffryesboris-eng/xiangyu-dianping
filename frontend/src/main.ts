import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import Page from './Page.vue'
import './style.css'
const router=createRouter({history:createWebHashHistory(),routes:[{path:'/',component:Page},{path:'/shops',component:Page},{path:'/shop/:id',component:Page},{path:'/notes',component:Page},{path:'/note/:id',component:Page},{path:'/feed',component:Page},{path:'/me',component:Page},{path:'/write',component:Page},{path:'/:pathMatch(.*)*',redirect:'/'}],scrollBehavior:()=>({top:0})})
createApp(App).use(createPinia()).use(router).mount('#app')
