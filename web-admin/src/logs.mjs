export function visibleLogs(snapshot,cleared){
 return (snapshot?.logs||[]).filter((line,i)=>!cleared||snapshot.log_generation!==cleared.generation||snapshot.log_offsets[i]>cleared.offset);
}
export function clearMarker(snapshot){
 return snapshot?{generation:snapshot.log_generation,offset:Math.max(0,...(snapshot.log_offsets||[]))}:null;
}
