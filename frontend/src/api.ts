import axios from 'axios'
export interface User {id:number;nickName?:string;icon?:string}
export interface Shop {id:number;name:string;typeId:number;images:string;address:string;area?:string;score:number;sold:number;avgPrice?:number;openHours?:string;distance?:number}
export interface Note {id:number;shopId:number;userId:number;title:string;content:string;images:string;name:string;liked:number;isLike:boolean;createTime:string}
export interface Voucher {id:number;title:string;subTitle?:string;payValue:number;actualValue:number;stock?:number;beginTime?:string;endTime?:string;type:number;status:number}
export const http=axios.create({baseURL:import.meta.env.DEV?'/api':'',timeout:15000})
http.interceptors.request.use(c=>{const t=localStorage.getItem('xiangyu-token');if(t)c.headers.authorization=t;return c})
export async function api<T>(url:string,method='GET',data?:unknown):Promise<T>{
 try{const r=await http.request({url,method,data});if(!r.data.success)throw new Error(r.data.errorMsg||'操作失败');return r.data.data as T}
 catch(e:any){if(e.response?.status===401){localStorage.removeItem('xiangyu-token');window.dispatchEvent(new Event('auth-expired'));throw new Error('请先登录后再操作')}throw new Error(e.response?.data?.detail && typeof e.response.data.detail==='string'?e.response.data.detail:e.message||'网络请求失败')}
}
export function image(raw?:string){const p=raw?.split(',')[0]?.trim();if(!p)return '';if(/^https?:\/\//.test(p))return p.replace(/^http:/,'https:');if(p.startsWith('/imgs/')||p.startsWith('/assets/'))return p;return p.startsWith('/')?'/imgs'+p:''}
