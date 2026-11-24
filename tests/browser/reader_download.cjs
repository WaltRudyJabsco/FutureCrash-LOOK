// Actual Reader page: choose an owner, acquire a book, and verify visible success.
const {chromium}=require('playwright'),fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:820,height:1180}}),errors=[],downloads=[];
  page.on('pageerror',e=>errors.push(e.message));
  const rows=[{id:'favorite','title':'A kept book',favorite:true,node:'library-owner'}];
  let fail=false;
  await page.route('**/*',async route=>{
   const req=route.request(),url=new URL(req.url()),path=url.pathname;
   if(path==='/reader')return route.fulfill({body:fs.readFileSync(process.argv[2],'utf8'),contentType:'text/html'});
   if(path==='/browser-views.js')return route.fulfill({body:fs.readFileSync('signal-window/browser-views.js','utf8'),contentType:'application/javascript'});
   if(path==='/api/books')return route.fulfill({json:{entries:rows,node:'client',owners:['client','library-owner'],download_owner:'client'}});
   if(path==='/api/books/discover')return route.fulfill({json:{entries:[{title:'Gay-Neck',author:'Dhan Gopal Mukerji',url:'https://www.gutenberg.org/ebooks/72086.epub.images'}]}});
   if(path==='/api/books/fetch'){
    downloads.push({target:url.searchParams.get('target'),body:req.postDataJSON()});
    if(fail)return route.fulfill({status:503,json:{error:'Source unavailable; no download confirmed'}});
    const book={id:'gay-neck',title:'Gay-Neck: The Story of a Pigeon',node:'library-owner',gutenberg_id:'72086'};
    rows.push(book);return route.fulfill({json:{book,node:'library-owner',ok:true}});
   }
   return route.fulfill({status:404,body:''});
  });
  page.on('dialog',dialog=>{assert(dialog.message().includes('library-owner'));dialog.accept()});
  await page.goto('https://reader.test/reader');
  await page.locator('#download-owner option').first().waitFor({state:'attached'});
  await page.locator('#download-owner').selectOption('library-owner');
  await page.locator('#favorites').click();await page.getByRole('button',{name:'A kept book',exact:true}).waitFor();
  await page.locator('#discover').click();await page.getByRole('button',{name:/^Gay-Neck/}).click();
  await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Verified on library-owner:'));
  assert.equal(await page.locator('#collection-filter').inputValue(),'all');
  assert.equal(await page.locator('#query').inputValue(),'Gay-Neck: The Story of a Pigeon');
  assert.equal(await page.locator('.book-card').count(),1);
  assert((await page.locator('.book-card').innerText()).includes('Gay-Neck'));
  assert.deepEqual(downloads,[{target:'library-owner',body:{url:'https://www.gutenberg.org/ebooks/72086.epub.images'}}]);
  await page.locator('#discover').click();
  await page.locator('#items button.owned').waitFor();
  assert.equal(await page.locator('#items button.owned').count(),1);
  // Failed requests must not show success or leave a disabled retry button.
  rows.pop();fail=true;await page.locator('#discover').click();
  await page.waitForFunction(()=>!document.querySelector('#items button.owned')&&document.querySelector('#status').textContent.startsWith('Project Gutenberg'));
  const result=page.getByRole('button',{name:/^Gay-Neck/});await result.click();
  await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('no download confirmed'));
  assert(await result.isEnabled());assert.equal(rows.length,1);assert.deepEqual(errors,[]);
  console.log('Reader owner selection, verified download visibility, owned identity and failure feedback passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
