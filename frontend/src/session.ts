import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, type User } from './api'
export const useSession=defineStore('session',()=>{
 const user=ref<User|null>(null),loginOpen=ref(false),message=ref('');let timer:ReturnType<typeof setTimeout>
 function toast(s:string){message.value=s;clearTimeout(timer);timer=setTimeout(()=>message.value='',4500)}
 function requireLogin(){if(user.value)return true;loginOpen.value=true;return false}
 async function restore(){if(localStorage.getItem('xiangyu-token')){try{user.value=await api<User>('/user/me')}catch{user.value=null}}}
 async function login(phone:string,code:string){const token=await api<string>('/user/login','POST',{phone,code});localStorage.setItem('xiangyu-token',token);await restore();loginOpen.value=false;toast('欢迎回来，开启今天的城市探索')}
 async function logout(){try{await api('/user/logout','POST')}finally{localStorage.removeItem('xiangyu-token');user.value=null;toast('已退出登录')}}
 return {user,loginOpen,message,toast,requireLogin,restore,login,logout}
})
