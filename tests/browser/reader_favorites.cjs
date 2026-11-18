// Exercise the actual Reader page with deterministic ownership and outage data.
const {chromium}=require('playwright'),fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:820,height:1180}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const rows=[{id:'gatsby',title:'The Great Gatsby',author:'F. Scott Fitzgerald',node:'owner',starter_managed:false},
              {id:'starter',title:'Starter Book',node:'owner',starter_managed:true}];
  const calls=[];
  await page.route('**/*',async route=>{
   const request=route.request(),path=new URL(request.url()).pathname;
   if(path==='/reader')return route.fulfill({body:fs.readFileSync(process.argv[2],'utf8'),contentType:'text/html'});
   if(path==='/browser-views.js')return route.fulfill({body:fs.readFileSync('signal-window/browser-views.js','utf8'),contentType:'application/javascript'});
   if(path==='/api/books')return route.fulfill({json:{entries:rows,collections:[]}});
   if(path==='/api/books/favorite'){
    const payload=request.postDataJSON();calls.push(payload);
    rows.find(r=>r.id===payload.id).favorite=payload.selected;
    return route.fulfill({json:{ok:true}});
   }
   if(path==='/api/books/discover')return route.fulfill({json:{entries:[{title:'Cached Gatsby',url:'https://www.gutenberg.org/ebooks/64317.epub.images'}],cached:true,warning:'Gutenberg is unavailable · browsing cached catalog.',next_index:null}});
   return route.fulfill({status:404,body:''});
  });
  await page.goto('https://reader.test/reader');
  const card=()=>page.locator('.book-card').filter({hasText:'The Great Gatsby'});
  await card().waitFor();
  assert(await card().getByRole('button',{name:'Removal unavailable: manually imported book'}).isDisabled());
  await card().getByRole('button',{name:'Add to Favorites',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#collection-filter').value==='favorites');
  await card().waitFor();
  assert((await page.locator('#status').innerText()).includes('not deleted'));
  assert.equal(await page.locator('#favorites').innerText(),'👍 Favorites (1)');
  await page.locator('#collection-filter').selectOption('pool');assert.equal(await card().count(),0);
  await page.locator('#query').fill('Gatsby');await page.getByRole('button',{name:'Search shelf',exact:true}).click();
  await card().waitFor();assert.equal(await page.locator('#collection-filter').inputValue(),'all');
  await page.locator('#discover').click();await page.getByRole('button',{name:'Cached Gatsby'}).waitFor();
  assert((await page.locator('#status').innerText()).includes('browsing cached catalog'));
  await page.locator('#favorites').click();await card().waitFor();
  assert.equal(calls.length,1);assert.equal(calls[0].selected,true);
  assert.deepEqual(errors,[]);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  console.log('Reader favorite retention, protected removal, shelf search, cached discovery and tablet layout passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
