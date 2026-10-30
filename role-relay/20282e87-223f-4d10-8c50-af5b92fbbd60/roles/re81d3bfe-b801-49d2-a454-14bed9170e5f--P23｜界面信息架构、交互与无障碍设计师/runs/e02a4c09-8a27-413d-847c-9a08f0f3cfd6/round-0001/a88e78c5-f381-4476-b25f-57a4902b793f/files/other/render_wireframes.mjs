/** P23 author design renderer. No game/Anki/remote service access. */
import fs from 'node:fs';
import crypto from 'node:crypto';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../../..');
const require=createRequire(import.meta.url);
const runtimeModules=process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES;
const {chromium}=require(process.env.P23_PLAYWRIGHT_MODULE || (runtimeModules ? path.join(runtimeModules,'playwright') : 'playwright'));
const args=process.argv.slice(2);
const outArg=args.indexOf('--output');
if(outArg<0||!args[outArg+1])throw new Error('Use --output NEW_DIRECTORY [--publish-previews]');
const output=path.resolve(args[outArg+1]);
if(fs.existsSync(output))throw new Error('Output directory must not exist');
fs.mkdirSync(output,{recursive:true});
const publish=args.includes('--publish-previews');
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const catalog=JSON.parse(fs.readFileSync(path.join(root,'design/ux/wireframe_catalog.json'),'utf8'));
const observed={layer:'AUTHOR_STATIC_SVG_RENDER',game_ui_executed:false,start_utc:new Date().toISOString(),node:process.version,platform:process.platform,argv:process.argv.slice(2),browser:null,renderer_sha256:sha(fileURLToPath(import.meta.url)),catalog_sha256:sha(path.join(root,'design/ux/wireframe_catalog.json')),cases:[],errors:[]};
let browser;
try{
 browser=await chromium.launch({executablePath:process.env.P23_BROWSER_EXECUTABLE||undefined,headless:true,args:process.platform==='linux'?['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--no-zygote','--single-process','--use-gl=angle','--use-angle=swiftshader']:[]});
 observed.browser=await browser.version();
 const context=await browser.newContext({viewport:{width:1280,height:856},deviceScaleFactor:1,reducedMotion:'reduce'});
 const page=await context.newPage();
 let errors=[],external=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.route('**/*',route=>{const u=route.request().url();if(!u.startsWith('file:')&&!u.startsWith('data:')){external.push(u);return route.abort();}return route.continue()});
 for(const item of catalog.items){
  errors=[];external=[];
  await page.setViewportSize({width:item.board_size[0],height:item.board_size[1]});
  await page.goto(pathToFileURL(path.join(root,item.svg_relative_path)).href);
  await page.evaluate(async()=>{if(document.fonts){await Promise.all([document.fonts.load('20px P23SC','言灵旅团'),document.fonts.load('20px P23JP','次の行動'),document.fonts.load('20px P23Symbols','→↔≠▾')]);await document.fonts.ready}});
  const geometry=await page.evaluate(()=>{
   const svg=document.querySelector('svg'),W=Number(svg.getAttribute('width')),H=Number(svg.getAttribute('height'));
   const texts=[...svg.querySelectorAll('text')].map(e=>{const r=e.getBBox();return{text:e.textContent,x:r.x,y:r.y,width:r.width,height:r.height,font_size:Number(e.getAttribute('font-size')),lang:e.getAttribute('lang'),family:getComputedStyle(e).fontFamily,in_bounds:r.x>=-0.1&&r.y>=-0.1&&r.x+r.width<=W+0.1&&r.y+r.height<=H+0.1}});
   const controls=[...svg.querySelectorAll('[data-control]')].map(e=>({anchor:e.getAttribute('data-anchor-id'),w:Number(e.getAttribute('width')),h:Number(e.getAttribute('height'))}));
   return {text_count:texts.length,out_of_board:texts.filter(t=>!t.in_bounds),texts,controls,fonts:{sc:document.fonts.check('20px P23SC','言灵旅团'),jp:document.fonts.check('20px P23JP','次の行動'),symbols:document.fonts.check('20px P23Symbols','→↔≠▾')}};
  });
  const imagePath=path.join(output,item.wireframe_id+'.png');await page.screenshot({path:imagePath,timeout:20000});
  if(publish)fs.copyFileSync(imagePath,path.join(root,item.png_relative_path));
  const result={wireframe_id:item.wireframe_id,input_svg_sha256:sha(path.join(root,item.svg_relative_path)),output_png_sha256:sha(imagePath),result:errors.length===0&&external.length===0&&geometry.out_of_board.length===0&&geometry.controls.every(c=>c.w>=44&&c.h>=44)&&geometry.fonts.sc&&geometry.fonts.jp&&geometry.fonts.symbols?'PASS':'FAIL',viewport:item.board_size,device_scale_factor:1,errors,blocked_external_requests:external,...geometry};
  observed.cases.push(result);console.log(item.wireframe_id,result.result,'texts='+result.text_count,'out='+result.out_of_board.length);
 }
 // Verify offline gallery headings and real navigation links. SVG drawings are not product controls.
 await page.setViewportSize({width:1280,height:900});
 await page.goto(pathToFileURL(path.join(root,'design/ux/P23_wireframe_review.html')).href);
 await page.evaluate(async()=>{await document.fonts.ready});
 observed.gallery=await page.evaluate(()=>({sections:document.querySelectorAll('main>section').length,links:[...document.querySelectorAll('nav a')].map(a=>({href:a.getAttribute('href'),resolves:!!document.getElementById(a.getAttribute('href').slice(1))})),duplicate_ids:[...document.querySelectorAll('[id]')].map(e=>e.id).filter((v,i,a)=>a.indexOf(v)!==i)}));
 observed.gallery.result=observed.gallery.links.every(x=>x.resolves)&&!observed.gallery.duplicate_ids.length?'PASS':'FAIL';

}catch(e){observed.errors.push(String(e));console.error(String(e));}
finally{if(browser)await browser.close();observed.end_utc=new Date().toISOString();observed.result=!observed.errors.length&&observed.cases.length===catalog.items.length&&observed.cases.every(x=>x.result==='PASS')&&observed.gallery?.result==='PASS'?'PASS':'FAIL';fs.writeFileSync(path.join(output,'render_results.json'),JSON.stringify(observed,null,2)+'\n');}
process.exitCode=observed.result==='PASS'?0:1;
