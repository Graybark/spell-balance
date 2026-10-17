/* Load the preserved rules/filter layer before the independent reader UI.
 * Kept at the existing script URL so the original HTML stays unchanged.
 */
(() => {
  'use strict';
  const root=new URL('.',document.currentScript.src);
  const revision='reader-20261017-d20-2';
  const style=document.createElement('link');
  style.rel='stylesheet'; style.href=new URL('spell-reader.css?v='+revision,root).href;
  document.head.append(style);
  function load(name) {
    return new Promise((resolve,reject)=> {
      const script=document.createElement('script'); script.src=new URL(name+'?v='+revision,root).href;
      script.async=false; script.onload=resolve; script.onerror=()=>reject(new Error('Unable to load '+name));
      document.body.append(script);
    });
  }
  load('rules-core.js').then(()=>load('spell-reader.js')).catch(error=> {
    console.error('Spell Balance:',error);
    const notice=document.createElement('p'); notice.setAttribute('role','alert');
    notice.textContent='The enhanced spell view could not load. Refresh the page to retry.';
    document.querySelector('.content').prepend(notice);
  });
})();
