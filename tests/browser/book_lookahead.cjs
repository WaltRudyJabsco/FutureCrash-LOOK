// Real helper, deterministic I/O: stale responses must never become playable URLs.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const context={AbortController,URL,location:{href:'https://reader.test/'},open:()=>{}};vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),context);
const {createBookAhead,bookPosition,booksCommand}=context.FabricBrowserViews;
(async()=>{
 const pending=[],created=[],revoked=[];
 const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve}};
 const ahead=createBookAhead({read:(route,signal)=>{const d=deferred();pending.push({route,signal,...d});return d.promise},audio:async route=>({route}),createURL:blob=>{const url='blob:'+blob.route;created.push(url);return url},revokeURL:url=>revoked.push(url)});
 const a=ahead.prepare('a','read-a','audio-a');assert.equal(ahead.prepare('a','read-a','audio-a'),a);assert.equal(pending.length,1);
 pending[0].resolve({paragraph:1});await a;const warm=await ahead.take('a');assert.equal(warm.url,'blob:audio-a');assert.equal(warm.value.paragraph,1);
 ahead.clear();assert.equal(revoked.length,0); // Consumer now owns its URL.
 const b=ahead.prepare('b','read-b','audio-b');ahead.clear();assert.equal(pending[1].signal.aborted,true);pending[1].resolve({paragraph:2});assert.equal(await b,null);assert.equal(created.length,1);
 const c=ahead.prepare('c','read-c','audio-c');pending[2].resolve({paragraph:3});await c;ahead.prepare('d','read-d','audio-d');assert.deepEqual(revoked,['blob:audio-c']);
 const consuming=ahead.take('d');assert.equal(ahead.take('different-voice'),null);pending[3].resolve({paragraph:4});assert.equal(await consuming,null);
 const failure=createBookAhead({read:async()=>{throw Error('offline')},audio:async()=>({}),createURL:()=>assert.fail('Failed preload must not allocate a URL')});assert.equal(await failure.prepare('e','',''),null);assert.equal(failure.take('e'),null);
 const chapters=[{paragraphs:2},{paragraphs:1}];assert.equal(JSON.stringify(bookPosition(chapters,0,1)),JSON.stringify({chapter:1,paragraph:0}));assert.equal(bookPosition(chapters,1,0),null);assert.equal(bookPosition(chapters,0,0,-1),null);
 for(const text of ['/books','/reader','/mercury-reader','Mercury Reader','open Mercury Reader'])assert.equal(booksCommand(text).resume,false);
 const opened=new URL(context.FabricBrowserViews.openBooks({query:'Island',resume:true}));assert.equal(opened.pathname,'/reader');assert.equal(opened.searchParams.get('query'),'Island');assert.equal(opened.searchParams.get('resume'),'1');
 console.log('Lookahead reuse, cancellation, consumed-request invalidation, URL ownership, failure, chapter boundary, and branding command checks passed.');
})().catch(error=>{console.error(error);process.exitCode=1});
