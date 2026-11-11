/* Local draft storage. No network calls; corrupt data is preserved for recovery. */
(function(root){
  const key = 'zephyr.workspace.v1';
  function validate(workspace){
    if(!workspace || !Array.isArray(workspace.files) || !workspace.files.length)
      throw Error('Saved workspace has no files');
    const ids = new Set();
    for(const file of workspace.files){
      if(!Number.isSafeInteger(file.id) || file.id<1 || file.id>=Number.MAX_SAFE_INTEGER || ids.has(file.id) || typeof file.name !== 'string' || typeof file.yaml !== 'string')
        throw Error('Saved workspace contains invalid files');
      ids.add(file.id);
    }
    if(!ids.has(workspace.activeFileId)) throw Error('Saved workspace has no active file');
  }
  function load(storage){
    try{
      const text = storage.getItem(key);
      if(!text)return {workspace:null,error:null};
      const workspace = JSON.parse(text);
      if(workspace.version !== 1)throw Error('Unsupported saved workspace version');
      validate(workspace);
      return {workspace,error:null};
    }catch(error){return {workspace:null,error:'Draft recovery failed: '+error.message};}
  }
  function save(storage,workspace){
    try{
      validate(workspace);
      const files=workspace.files.map(({id,name,yaml})=>({id,name,yaml}));
      const text=JSON.stringify({version:1,files,activeFileId:workspace.activeFileId});
      if(typeof storage.getItem!=="function" || storage.getItem(key)!==text)storage.setItem(key,text);
      return null;
    }catch(error){return 'Draft saving failed: '+error.message;}
  }
  root.ZephyrDrafts={key,load,save};
})(typeof window === 'undefined' ? globalThis : window);
