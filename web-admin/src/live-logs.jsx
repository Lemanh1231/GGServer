import React,{useEffect,useRef,useState}from'react';
import{api}from'./api.mjs';
import{visibleLogs,clearMarker}from'./logs.mjs';
export function LiveLogs({onStatus}){
 const[snapshot,setSnapshot]=useState(null),[paused,setPaused]=useState(false),[cleared,setCleared]=useState(null),[error,setError]=useState(''),[updated,setUpdated]=useState(null),[follow,setFollow]=useState(true);
 const box=useRef(null),statusCallback=useRef(onStatus);statusCallback.current=onStatus;
 useEffect(()=>{
  if(paused)return;
  let stopped=false,timer;
  async function refresh(){
   try{
    if(!document.hidden){const data=await api('status');if(!stopped){setSnapshot(data);statusCallback.current?.(data.status);setUpdated(new Date());setError('');}}
   }catch(e){if(!stopped)setError(e.message);}
   finally{if(!stopped)timer=setTimeout(refresh,2000);}
  }
  refresh();return()=>{stopped=true;clearTimeout(timer);};
 },[paused]);
 const lines=visibleLogs(snapshot,cleared);
 useEffect(()=>{if(follow&&box.current)box.current.scrollTop=box.current.scrollHeight;},[snapshot,cleared,follow]);
 return <section className="card panel bg-base-100 min-w-0"><div className="card-body p-5 md:p-7"><div className="flex flex-wrap justify-between items-center gap-3"><div><p className="eyebrow">Server activity</p><h2 className="text-xl font-semibold mt-2">Nhật ký vận hành</h2></div><span className={`badge badge-soft ${error?'badge-error':paused?'badge-warning':'badge-accent'}`}>{error?'Mất kết nối':paused?'Tạm dừng':'Tự cập nhật · 2 giây'}</span></div><p className="muted text-xs mt-2">Chỉ hiển thị tóm tắt an toàn. Xóa hiển thị không xóa file log server. Tạm ngừng tải khi tab trình duyệt bị ẩn.</p><div className="flex flex-wrap gap-2 items-center mt-3"><button type="button" className="btn btn-sm btn-outline" aria-pressed={paused} onClick={()=>setPaused(!paused)}>{paused?'Tiếp tục':'Tạm dừng'}</button><button type="button" className="btn btn-sm btn-outline" disabled={!snapshot||!lines.length} onClick={()=>setCleared(clearMarker(snapshot))}>Xóa log hiển thị</button><label className="flex items-center gap-2 text-xs muted"><input className="checkbox checkbox-sm" type="checkbox" checked={follow} onChange={e=>setFollow(e.target.checked)}/>Theo dòng mới</label></div>{error&&<p className="text-error text-sm" role="status">{error} · Tự thử lại.</p>}<div ref={box} className="log-console mt-4" role="region" aria-label="Nhật ký server" tabIndex="0">{lines.length?lines.map((line,i)=><div key={i} className={line.includes('[WARN]')?'log-warn':''}>{line}</div>):<p className="muted">{snapshot?'Chưa có log mới.':'Đang tải log…'}</p>}</div><p className="muted text-xs">{lines.length} dòng · Cập nhật: {updated?updated.toLocaleTimeString('vi-VN'):'—'}</p></div></section>;
}
