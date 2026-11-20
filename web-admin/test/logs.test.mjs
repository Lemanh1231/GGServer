import{test}from'node:test';
import assert from'node:assert/strict';
import{visibleLogs,clearMarker}from'../src/logs.mjs';
test('clear hides old log entries but retains newly appended identical lines',()=>{
 const first={logs:['same','same'],log_offsets:[10,20],log_generation:'a'};
 const marker=clearMarker(first);assert.deepEqual(visibleLogs(first,marker),[]);
 assert.deepEqual(visibleLogs({...first,logs:['same','same','same'],log_offsets:[10,20,30]},marker),['same']);
 assert.deepEqual(visibleLogs({logs:['rotated'],log_offsets:[5],log_generation:'b'},marker),['rotated']);
});
