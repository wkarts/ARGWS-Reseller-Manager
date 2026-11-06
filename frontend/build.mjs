// Adapted from the user's template: Vue compiled in Node, without eval in the browser.
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const decode=v=>v.replace(/&(#x[0-9a-f]+|#\d+|amp|lt|gt|quot|apos|nbsp);/gi,(_,key)=>key[0]==='#'?String.fromCodePoint(key[1].toLowerCase()==='x'?parseInt(key.slice(2),16):parseInt(key.slice(1),10)):({amp:'&',lt:'<',gt:'>',quot:'"',apos:"'",nbsp:'\u00a0'})[key.toLowerCase()]);
const sandbox={console,document:{createElement(){return {textContent:'',get innerHTML(){return this.textContent},set innerHTML(value){this.textContent=decode(value);this.children=[{getAttribute(){return decode(value.slice(10,-2))}}]}}}}};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(path.join(root,'vendor/vue.js'),'utf8'),sandbox);
const errors=[];const render=sandbox.Vue.compile(fs.readFileSync(path.join(root,'app.html'),'utf8'),{hoistStatic:false,onError:e=>errors.push(String(e))});
if(errors.length)throw Error(errors.join('\n'));
const code='/* Template pré-compilado; não requer eval ou CDN. */\nvar _Vue=Vue;var ResellerRender='+render.toString()+';\n';
const target=path.join(root,'../app/static/render.js');
if(process.argv.includes('--check')){if(fs.readFileSync(target,'utf8')!==code)throw Error('Execute node frontend/build.mjs e versione o resultado.');}else fs.writeFileSync(target,code);
console.log('Interface compilada sem CDN.');
