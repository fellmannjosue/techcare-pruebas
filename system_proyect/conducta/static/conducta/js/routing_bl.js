/* routing_bl.js — Ruteo de reportes Bilingüe
   <--- hecho por claude code: extraído del template (nada de JS en el HTML).
   Las URLs y banderas de Django llegan por #routing-bl-config (data-*)
   y los JSON por {{ ...|json_script }}. */
const CFG_ROUTING_BL = (function () {
  var d = document.getElementById("routing-bl-config").dataset;
  return {
    urlGuardar:   d.urlGuardar,
    urlRefrescar: d.urlRefrescar,
    urlCargar:    d.urlCargar,
    urlGrupos:    d.urlGrupos,
    urlPermisos:  d.urlPermisos,
    soloLectura:  d.soloLectura === "1",
  };
})();

(function(){
  const CSRF = document.getElementById('csrf').value;
  const COORD_NOMBRES = JSON.parse(document.getElementById("coord-nombres-data").textContent);
  // <--- hecho por claude code: los overrides ya NO se manejan aquí; se derivan en el
  // servidor a partir del catálogo de docentes (ver routing_bl_guardar).

  function post(url, opts){
    return fetch(url, Object.assign({method:'POST', headers:{'X-CSRFToken':CSRF}}, opts)).then(r=>r.json());
  }
  function jpost(url, body){
    return post(url, {headers:{'X-CSRFToken':CSRF,'Content-Type':'application/json'}, body:JSON.stringify(body)});
  }

  // ── Autoguardado del mapeo (materias C3/C4, grados C1/C2) ──
  const statusMapeo = document.getElementById('autosave-status');
  function setStatusMapeo(s){
    if(!statusMapeo) return;
    if(s==='saving') statusMapeo.innerHTML='<span class="spinner-border spinner-border-sm me-1"></span>Guardando…';
    else if(s==='saved') statusMapeo.innerHTML='<i class="ti ti-check me-1 text-green"></i>Guardado';
    else statusMapeo.innerHTML='<i class="ti ti-alert-triangle me-1 text-danger"></i>Error al guardar';
  }
  let tMapeo=null;
  // <--- hecho por claude code: el mapeo (materias/grados) NO toca overrides
  window.guardarMapeo = function(){
    setStatusMapeo('saving');
    jpost(CFG_ROUTING_BL.urlGuardar, {
      materias_c3: document.getElementById('materias_c3').value,
      materias_c4: document.getElementById('materias_c4').value,
      grados_c1:   document.getElementById('grados_c1').value,
      grados_c2:   document.getElementById('grados_c2').value,
    }).then(d=>{
      if(d.ok){
        const a=document.getElementById('actualizado'); if(a) a.textContent=d.actualizado;
        if(d.norm) ['materias_c3','materias_c4','grados_c1','grados_c2'].forEach(id=>{
          const el=document.getElementById(id);
          if(el && el!==document.activeElement && d.norm[id]!==undefined) el.value=d.norm[id];
        });
        setStatusMapeo('saved');
      } else setStatusMapeo('error');
    }).catch(()=>setStatusMapeo('error'));
  };
  function scheduleMapeo(){ clearTimeout(tMapeo); tMapeo=setTimeout(window.guardarMapeo, 700); }
  ['materias_c3','materias_c4','grados_c1','grados_c2'].forEach(id=>{
    const el=document.getElementById(id); if(el) el.addEventListener('input', scheduleMapeo);
  });

  // ── Refrescar alumnado ──
  document.getElementById('btn-refrescar').addEventListener('click', function(){
    const btn=this; btn.disabled=true; btn.innerHTML='<span class="spinner-border spinner-border-sm me-1"></span>Consultando SQL Server...';
    post(CFG_ROUTING_BL.urlRefrescar, {}).then(d=>{
      btn.disabled=false; btn.innerHTML='<i class="ti ti-refresh me-1"></i>Refrescar alumnado desde SQL Server';
      if(d.ok){ Swal.fire({icon:'success',title:`${d.n_alumnos} alumnos cargados`,timer:1200,showConfirmButton:false}).then(()=>location.reload()); }
      else Swal.fire('Error', d.error||'No se pudo refrescar','error');
    }).catch(()=>{btn.disabled=false;btn.innerHTML='<i class="ti ti-refresh me-1"></i>Refrescar alumnado desde SQL Server';Swal.fire('Error','Conexión','error');});
  });

  // ── Cargar JSON ──
  document.getElementById('file-json').addEventListener('change', function(){
    if(!this.files.length) return;
    const fd = new FormData(); fd.append('archivo', this.files[0]);
    post(CFG_ROUTING_BL.urlCargar, {body: fd}).then(d=>{
      if(d.ok){ Swal.fire({icon:'success',title:'JSON cargado',text:`${d.n_alumnos} alumnos`,timer:1500,showConfirmButton:false}).then(()=>location.reload()); }
      else Swal.fire('Error', d.error||'No se pudo cargar','error');
    }).catch(()=>Swal.fire('Error','Conexión','error'));
  });

  // ── Docentes: catálogo de CARGAS (lista de entradas) — hecho por claude code ──
  // Cada entrada = {docente, materias, coord}. Un mismo docente puede tener VARIAS.
  window.DOC_ENTRIES = JSON.parse(document.getElementById("doc-entries-data").textContent);
  const docTbody = document.getElementById('doc-tbody');
  const docEmpty = document.getElementById('doc-empty');
  const docSel = document.getElementById('doc-sel');
  const docMat = document.getElementById('doc-mat');
  const docCoord = document.getElementById('doc-coord');
  const docAddBtn = document.getElementById('doc-add');
  let docEdit = -1;   // índice en edición (-1 = agregar nueva)

  // Mapa docente→materias (unión de todas sus cargas) para el auto-relleno en Grupos
  function rebuildDocMap(){
    const m = {}, cm = {};
    window.DOC_ENTRIES.forEach(e=>{
      const d = (e.docente||'').trim(); if(!d) return;
      const acc = m[d] ? m[d].split(',').map(s=>s.trim()).filter(Boolean) : [];
      (e.materias||'').split(',').map(s=>s.trim()).forEach(x=>{ if(x && !acc.includes(x)) acc.push(x); });
      m[d] = acc.join(', ');
      // <--- hecho por claude code: coordinadores por docente (para el multi-select de clases en Grupos)
      if(e.coord){ cm[d] = cm[d] || []; if(!cm[d].includes(e.coord)) cm[d].push(e.coord); }
    });
    window.DOCENTE_MATERIAS = m;
    window.DOCENTE_COORDS = cm;
  }
  const COORD_ORDEN = {C1:1, C2:2, C3:3, C4:4, '':5};
  function docRender(){
    docTbody.querySelectorAll('tr[data-idx], tr.doc-group-hdr').forEach(r=>r.remove());
    if(docEmpty) docEmpty.style.display = window.DOC_ENTRIES.length ? 'none' : '';
    // <--- hecho por claude code: agrupar por coordinador (C1, C2, C3, C4, Auto) sin perder el índice original
    const filas = window.DOC_ENTRIES.map((e,idx)=>({e, idx}));
    filas.sort((a,b)=>{
      const d = (COORD_ORDEN[a.e.coord||'']||9) - (COORD_ORDEN[b.e.coord||'']||9);
      return d !== 0 ? d : (a.e.docente||'').localeCompare(b.e.docente||'');
    });
    let coordActual = null;
    filas.forEach(({e, idx})=>{
      const cc = e.coord || '';
      if(cc !== coordActual){
        coordActual = cc;
        const titulo = cc ? `${cc} · ${COORD_NOMBRES[cc]||''}` : 'Auto (sin coordinador · por materia/grado)';
        const hdr = document.createElement('tr'); hdr.className = 'doc-group-hdr';
        hdr.innerHTML = `<td colspan="4" class="bg-light fw-semibold small text-uppercase text-muted py-1">${titulo}</td>`;
        docTbody.appendChild(hdr);
      }
      const coordHtml = cc
        ? `<span class="badge bg-orange-lt text-orange" title="${COORD_NOMBRES[cc]||''}">${cc}</span>`
        : '<span class="badge bg-secondary-lt text-muted">Auto</span>';
      const tr = document.createElement('tr'); tr.dataset.idx = idx; tr.style.cursor='pointer';
      if(idx===docEdit) tr.classList.add('table-active');
      tr.innerHTML = `<td class="fw-medium">${e.docente||''}</td>`+
        `<td class="text-muted small">${e.materias || '<span class="text-secondary">—</span>'}</td>`+
        `<td class="text-center">${coordHtml}</td>`+
        `<td class="text-end"><button type="button" class="btn btn-sm btn-ghost-danger doc-del" data-idx="${idx}"><i class="ti ti-x"></i></button></td>`;
      docTbody.appendChild(tr);
    });
  }
  function docGuardar(){
    setStatusMapeo('saving');
    jpost(CFG_ROUTING_BL.urlGuardar, { docentes_catalogo: window.DOC_ENTRIES })
      .then(d=>setStatusMapeo(d.ok?'saved':'error')).catch(()=>setStatusMapeo('error'));
  }
  function resetForm(){
    docSel.value=''; docMat.value=''; docCoord.value=''; docEdit=-1;
    docAddBtn.innerHTML='<i class="ti ti-plus me-1"></i>Agregar';
  }
  function aplicarCambios(){
    rebuildDocMap(); docRender(); docGuardar();
    if(window.refreshGrupoDocentes) window.refreshGrupoDocentes();
  }
  docAddBtn.addEventListener('click', function(){
    const doc = (docSel.value||'').trim();
    const mat = (docMat.value||'').trim();
    const coord = docCoord.value;
    if(!doc){ Swal.fire('Falta docente','Elige un docente','info'); return; }
    if(!mat && !coord){ Swal.fire('Nada que guardar','Escribe materias o elige un coordinador','info'); return; }
    // <--- hecho por claude code: ';' = CARGAS separadas (varias filas) · ',' = un solo paquete (una fila)
    const paquetes = mat ? mat.split(';').map(s=>s.trim()).filter(Boolean) : [''];
    const entradas = (paquetes.length ? paquetes : ['']).map(p=>({docente:doc, materias:p, coord:coord}));
    if(docEdit>=0 && docEdit<window.DOC_ENTRIES.length){
      window.DOC_ENTRIES[docEdit] = entradas[0];                                        // actualizar la fila editada
      for(let i=1;i<entradas.length;i++) window.DOC_ENTRIES.splice(docEdit+i, 0, entradas[i]);  // extras como filas nuevas
    } else {
      entradas.forEach(en=>window.DOC_ENTRIES.push(en));
    }
    resetForm(); aplicarCambios();
  });
  docTbody.addEventListener('click', function(e){
    const del = e.target.closest('.doc-del');
    if(del){
      const i = parseInt(del.dataset.idx,10);
      window.DOC_ENTRIES.splice(i,1);
      if(docEdit===i) resetForm(); else if(docEdit>i) docEdit--;
      aplicarCambios(); return;
    }
    // clic en fila → cargar en el editor para modificarla
    const tr = e.target.closest('tr[data-idx]'); if(!tr) return;
    const i = parseInt(tr.dataset.idx,10);
    const en = window.DOC_ENTRIES[i]; if(!en) return;
    docEdit = i; docSel.value = en.docente||''; docMat.value = en.materias||''; docCoord.value = en.coord||'';
    docAddBtn.innerHTML='<i class="ti ti-check me-1"></i>Actualizar';
    docRender();
  });
  rebuildDocMap(); docRender();
})();

/* ───────────────────────────────────────────── */

(function(){
  const CSRF = document.getElementById('csrf').value;
  // <--- hecho por claude code: el desplegable de docentes se alimenta del CATÁLOGO (window.DOCENTE_MATERIAS)
  function escapeHtml(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
  function docenteOptions(selected){
    const cat = Object.keys(window.DOCENTE_MATERIAS||{}).sort((a,b)=>a.localeCompare(b));
    const list = cat.slice();
    // preserva un docente ya elegido aunque no esté (aún) en el catálogo
    if(selected && !list.includes(selected)) list.unshift(selected);
    let o = '<option value="">— Docente —</option>';
    list.forEach(m => { const e = escapeHtml(m); o += `<option value="${e}"${m===selected?' selected':''}>${e}</option>`; });
    return o;
  }
  function docenteSelectHTML(){
    return `<select class="form-select form-select-sm grp-docente">${docenteOptions('')}</select>`;
  }
  // reconstruye TODOS los <select> de docente desde el catálogo, conservando su valor actual
  window.refreshGrupoDocentes = function(){
    document.querySelectorAll('.grp-docente').forEach(sel=>{
      const cur = sel.value;
      sel.innerHTML = docenteOptions(cur);
      sel.value = cur;
    });
    if(window.renderAllMat) window.renderAllMat();
  };

  // ── Multi-select de clases (dropdown con checkboxes) por docente ──  hecho por claude code
  function partes(s){ return (s||'').split(',').map(x=>x.trim()).filter(Boolean); }
  function setLabel(row){
    const label = row.querySelector('.grp-mat-label');
    const activos = partes(row.querySelector('.grp-materia').value);
    if(label) label.textContent = activos.length ? activos.join(', ') : 'Elegir clases…';
  }
  function renderMat(row){
    const sel = row.querySelector('.grp-docente');
    const hidden = row.querySelector('.grp-materia');
    const menu = row.querySelector('.grp-mat-menu');
    const btn = row.querySelector('.grp-mat-btn');
    if(!menu || !hidden) return;
    const doc = (sel && sel.value.trim()) || '';
    const activos = partes(hidden.value);
    const cat = partes((window.DOCENTE_MATERIAS||{})[doc] || '');
    const opciones = cat.slice();
    activos.forEach(a=>{ if(!opciones.includes(a)) opciones.push(a); });   // incluye seleccionadas no catalogadas
    if(!doc){ menu.innerHTML = '<div class="text-muted small px-2 py-1">Elige un docente…</div>'; if(btn) btn.disabled = true; }
    else if(!opciones.length){ menu.innerHTML = '<div class="text-muted small px-2 py-1">Sin materias en el catálogo</div>'; if(btn) btn.disabled = false; }
    else {
      if(btn) btn.disabled = false;
      menu.innerHTML = opciones.map(m=>{
        const on = activos.includes(m);
        return `<label class="dropdown-item d-flex align-items-center gap-2 px-2 py-1" style="cursor:pointer">`+
               `<input type="checkbox" class="form-check-input m-0 grp-mat-check" data-mat="${escapeHtml(m)}" ${on?'checked':''}>`+
               `<span>${escapeHtml(m)}</span></label>`;
      }).join('');
    }
    setLabel(row);
  }
  function hiddenFromChecks(row){
    const activos = [];
    row.querySelectorAll('.grp-mat-check:checked').forEach(c=>activos.push(c.dataset.mat));
    row.querySelector('.grp-materia').value = activos.join(', ');
    setLabel(row);
  }
  window.renderAllMat = function(){ document.querySelectorAll('.grp-clase-row').forEach(renderMat); };
  // marcar/desmarcar una clase en el dropdown → actualiza el valor y guarda
  document.addEventListener('change', function(e){
    const chk = e.target.closest('.grp-mat-check'); if(!chk) return;
    const row = chk.closest('.grp-clase-row'); const card = chk.closest('.grupo-card');
    hiddenFromChecks(row);
    if(card) schedule(card);
  });

  document.addEventListener('click', function(e){
    const add = e.target.closest('.grp-add-clase');
    if(add){
      const wrap = add.closest('.card-body').querySelector('.grp-clases');
      const row = document.createElement('div');
      row.className = 'd-flex gap-1 mb-1 grp-clase-row align-items-center';
      row.innerHTML = docenteSelectHTML()+
        `<input type="hidden" class="grp-materia">`+
        `<div class="dropdown flex-grow-1 grp-mat-dd">`+
          `<button type="button" class="btn btn-sm btn-outline-secondary w-100 text-start text-truncate grp-mat-btn" data-bs-toggle="dropdown" data-bs-auto-close="outside"><span class="grp-mat-label">Elegir clases…</span></button>`+
          `<div class="dropdown-menu p-1 grp-mat-menu" style="max-height:240px;overflow:auto;min-width:220px;"></div>`+
        `</div>`+
        `<span class="d-flex gap-1 grp-coord-badges" style="white-space:nowrap;"><span class="badge bg-secondary-lt text-muted">?</span></span>`+
        `<button type="button" class="btn btn-sm btn-ghost-danger grp-del-clase"><i class="ti ti-x"></i></button>`;
      wrap.appendChild(row);
      renderMat(row);
      return;
    }
    const del = e.target.closest('.grp-del-clase');
    if(del){
      // <--- hecho por claude code: capturar la tarjeta y AGENDAR el guardado ANTES de quitar la fila
      // (si se quita primero, el nodo se desconecta y closest('.grupo-card') da null → no se guardaba)
      const card = del.closest('.grupo-card');
      del.closest('.grp-clase-row').remove();
      if(card) schedule(card);
    }
  });

  const status = document.getElementById('autosave-status');
  function setStatus(state){
    if(!status) return;
    if(state==='saving') status.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando…';
    else if(state==='saved') status.innerHTML = '<i class="ti ti-check me-1 text-green"></i>Guardado';
    else if(state==='error') status.innerHTML = '<i class="ti ti-alert-triangle me-1 text-danger"></i>Error al guardar';
  }
  function collect(card){
    const clases = [];
    card.querySelectorAll('.grp-clase-row').forEach(r=>{
      const doc = r.querySelector('.grp-docente').value.trim();
      const mat = r.querySelector('.grp-materia').value.trim();
      if(doc || mat) clases.push({docente:doc, materia:mat});
    });
    return {coordinador: card.querySelector('.grp-coord').value, clases};
  }
  function pintarBadges(card, filas){
    if(!filas) return;
    let i = 0;
    card.querySelectorAll('.grp-clase-row').forEach(r=>{
      const doc = r.querySelector('.grp-docente').value.trim();
      const mat = r.querySelector('.grp-materia').value.trim();
      const span = r.querySelector('.grp-coord-badges');
      if(!span) return;
      if(!(doc||mat)){ span.innerHTML = '<span class="badge bg-secondary-lt text-muted">—</span>'; return; }
      const cs = filas[i] || []; i++;
      span.innerHTML = cs.length
        ? cs.map(c=>`<span class="badge bg-orange-lt text-orange" title="${c.nombre}">${c.code}</span>`).join('')
        : '<span class="badge bg-secondary-lt text-muted">—</span>';
    });
  }
  const timers = {};
  function saveCard(card){
    const key = card.dataset.key;
    const payload = collect(card);
    setStatus('saving');
    fetch(CFG_ROUTING_BL.urlGrupos, {
      method:'POST', headers:{'X-CSRFToken':CSRF,'Content-Type':'application/json'},
      body: JSON.stringify({grupos:{[key]:payload}})
    }).then(r=>r.json()).then(d=>{
      if(d.ok){ pintarBadges(card, (d.coords||{})[key]); setStatus('saved'); }
      else setStatus('error');
    }).catch(()=>setStatus('error'));
  }
  function schedule(card){
    const key = card.dataset.key;
    clearTimeout(timers[key]);
    timers[key] = setTimeout(()=>saveCard(card), 700);
  }
  document.addEventListener('change', function(e){
    const card = e.target.closest('.grupo-card');
    if(!card) return;
    // <--- hecho por claude code: al elegir docente, arma los chips de sus materias
    if(e.target.matches('.grp-docente')){
      const row = e.target.closest('.grp-clase-row');
      const doc = e.target.value.trim();
      const hidden = row.querySelector('.grp-materia');
      const cat = (window.DOCENTE_MATERIAS||{})[doc] || '';
      const coords = (window.DOCENTE_COORDS||{})[doc] || [];
      // dual-coordinador → sin selección (tú eliges las clases); un solo coordinador → todas marcadas
      hidden.value = (coords.length > 1) ? '' : cat;
      renderMat(row);
    }
    if(e.target.matches('.grp-docente') || e.target.matches('.grp-coord')) schedule(card);
  });
  // El borrado ya agenda su propio guardado arriba; aquí solo el "Agregar clase".
  document.addEventListener('click', function(e){
    const card = e.target.closest('.grupo-card');
    if(card && e.target.closest('.grp-add-clase')) schedule(card);
  });

  // <--- hecho por claude code: al cargar, poblar los desplegables y los chips desde el catálogo
  window.refreshGrupoDocentes();
  window.renderAllMat();
})();

/* ───────────────────────────────────────────── */

(function(){
  const CSRF = document.getElementById('csrf').value;
  // Permisos por coordinador (solo admin): none / lectura / edit
  const ETIQUETA = {none:'Sin acceso', lectura:'Solo lectura', edit:'Puede editar'};
  document.querySelectorAll('.perm-sel').forEach(sel=>{
    let prev = sel.value;
    sel.addEventListener('change', function(){
      const coord = sel.dataset.coord, permiso = sel.value;
      fetch(CFG_ROUTING_BL.urlPermisos, {
        method:'POST', headers:{'X-CSRFToken':CSRF,'Content-Type':'application/json'},
        body: JSON.stringify({coord: coord, permiso: permiso})
      }).then(r=>r.json()).then(d=>{
        if(d.ok){ prev = permiso; Swal.fire({icon:'success',title:`${coord}: ${ETIQUETA[permiso]}`,timer:1100,showConfirmButton:false}); }
        else { sel.value = prev; Swal.fire('Error', d.error||'No se pudo cambiar','error'); }
      }).catch(()=>{ sel.value = prev; Swal.fire('Error','Conexión','error'); });
    });
  });
  // Modo SOLO LECTURA para coordinadores: deshabilita controles y oculta acciones
  if(CFG_ROUTING_BL.soloLectura){
    document.querySelectorAll('.card input, .card select, .card textarea').forEach(el=>{ el.disabled = true; });
    // <--- hecho por claude code: en solo-lectura, el dropdown de materias no se puede tocar
    document.querySelectorAll('.grp-mat-btn, .grp-mat-check').forEach(b=>{ b.disabled = true; });
    const ocultar = ['#btn-refrescar','#btn-guardar','#btn-add-ov','#autosave-status'];
    ocultar.forEach(s=>{ const e=document.querySelector(s); if(e) e.style.display='none'; });
    document.querySelectorAll('.grp-add-clase, .grp-del-clase, .ov-del, .btn-cargar-json, .btn-descargar-json').forEach(e=>e.style.display='none');
  }
})();
