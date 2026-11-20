import {build} from 'esbuild';
import {execFileSync} from 'node:child_process';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const temp=mkdtempSync(join(tmpdir(),'gg-admin-'));
try {
 execFileSync('./node_modules/.bin/tailwindcss',['-i','src/style.css','-o',join(temp,'style.css'),'--minify'],{stdio:'inherit'});
 const result=await build({entryPoints:['src/main.jsx'],bundle:true,minify:true,write:false,charset:'utf8',format:'iife',define:{'process.env.NODE_ENV':'"production"'}});
 const css=readFileSync(join(temp,'style.css'),'utf8');
 const js=result.outputFiles[0].text.replaceAll('</script','<\\/script');
 for(const page of ['login','dashboard','download']) {
  const html=`<!doctype html><html lang="vi" data-theme="guitar"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#171820"><title>Guitar Girl · ${page==='download'?'Tải game':'Quản trị'}</title><style>${css}</style></head><body data-page="${page}"><div id="root"></div><noscript>Vui lòng bật JavaScript để sử dụng trang web.</noscript><script>${js}</script></body></html>`;
  writeFileSync(page==='download'?'../src/main/java/emu/leman/ggserver/server/download.html':`../src/main/java/emu/leman/ggserver/server/admin/${page}.html`,html);
 }
} finally {rmSync(temp,{recursive:true,force:true});}
