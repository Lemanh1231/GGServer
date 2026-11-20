import{test}from'node:test';
import assert from'node:assert/strict';
import{mailPayload,settingsPayload}from'../src/api.mjs';
test('mail preserves request identity and validates rewards',()=>{
 assert.equal(mailPayload({uuid:'test',cp:'12',items:'[]'},'stable-id').request_id,'stable-id');
 assert.equal(mailPayload({uuid:'test',cp:'12',items:'[]'},'id').cp,12);
 assert.throws(()=>mailPayload({uuid:'',items:'[]'},'id'));
 assert.throws(()=>mailPayload({cp:'-1'},'id'));
 assert.throws(()=>mailPayload({items:'{}'},'id'));
});
test('player settings omit blank adjustments and reject conflicting likes',()=>{
 assert.deepEqual(settingsPayload('test',{add_cp:'',add_like:'1.5A',set_like:''}),{uuid:'test',add_like:'1.5A'});
 assert.throws(()=>settingsPayload('test',{add_like:'1A',set_like:'2A'}));
});
