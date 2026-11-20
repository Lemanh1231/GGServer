export async function api(path,body) {
 const response=await fetch('/admin/api/'+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});
 let data;try{data=await response.json();}catch{throw new Error('Máy chủ trả dữ liệu không hợp lệ.');}
 if(response.status===401 && path!=='login'){location.assign('/admin');throw new Error('Phiên đăng nhập hết hạn.');}
 if(!response.ok || data.success===false)throw new Error(data.error||'Yêu cầu thất bại.');
 return data;
}
export function mailPayload(form,requestId){
 if(!form.uuid)throw new Error('Hãy chọn người nhận hoặc toàn server.');
 const p={...form,request_id:requestId};
 for(const key of ['cp','candy','cookies']){p[key]=Number(form[key]||0);if(!Number.isFinite(p[key])||p[key]<0)throw new Error('Quà phải là số không âm.');}
 p.items=JSON.parse(form.items||'[]');if(!Array.isArray(p.items))throw new Error('Danh sách vật phẩm phải là mảng JSON.');
 return p;
}
export function settingsPayload(uuid,settings){
 const payload={uuid,...settings};
 for(const key of ['add_cp','add_candy','set_like','add_like'])if(payload[key]===''||payload[key]===undefined)delete payload[key];
 if(payload.set_like!==undefined&&payload.add_like!==undefined)throw new Error('Chỉ chọn đặt hoặc thêm lượt thích, không dùng cả hai.');
 return payload;
}
