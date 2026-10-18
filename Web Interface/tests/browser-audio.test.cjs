const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const ts = require('typescript');
const source = ts.transpileModule(fs.readFileSync('src/browser-audio.ts','utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;

function runtime() {
  let instance;
  class Recognition {
    constructor() { instance=this; }
    start() {}
    abort() { this.onend?.(); }
  }
  const context={exports:{},window:{SpeechRecognition:Recognition,speechSynthesis:{cancel(){},speak(){}}},
    SpeechSynthesisUtterance:class {},setTimeout,clearTimeout,Promise,Error};
  vm.runInNewContext(source,context);
  return {api:context.exports,instance:()=>instance};
}
test('browser speech returns transcript and releases the microphone for a second request',async()=>{
  const r=runtime();
  for (const text of ['Tanish','What is next?']) {
    const promise=r.api.listenInBrowser();
    r.instance().onresult({results:[[{transcript:text}]]});
    assert.equal(await promise,text);
  }
});
test('permission denial shows a useful error',async()=>{
  const r=runtime(), promise=r.api.listenInBrowser();
  r.instance().onerror({error:'not-allowed'});
  await assert.rejects(promise,/Allow microphone access/);
});
test('stop listening rejects the active request and allows another request',async()=>{
  const r=runtime(), promise=r.api.listenInBrowser();
  r.api.stopBrowserListening();
  await assert.rejects(promise,/No speech received/);
  const next=r.api.listenInBrowser();
  r.instance().onresult({results:[[{transcript:'Tanish'}]]});
  assert.equal(await next,'Tanish');
});
