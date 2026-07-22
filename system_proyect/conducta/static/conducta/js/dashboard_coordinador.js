/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #dashboard_coordinador-config (un .js no lo procesa Django). */
const CFG = (function(){
  var d = document.getElementById("dashboard_coordinador-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
    v2: d.v2,
    j2: j(d.v2),
    v3: d.v3,
    j3: j(d.v3),
    v4: d.v4,
    j4: j(d.v4),
    v5: d.v5,
    j5: j(d.v5),
  };
})();

// Edición de períodos: llena el formulario con los datos de la fila
  (function () {
    document.querySelectorAll('.per-edit').forEach(function (b) {
      b.addEventListener('click', function () {
        var d = this.dataset;
        var set = function (id, v) { var el = document.getElementById(id); if (el) el.value = v; };
        set('per-pk', d.pk); set('per-nombre', d.nombre); set('per-parcial', d.parcial);
        set('per-anio', d.anio); set('per-area', d.area); set('per-inicio', d.inicio); set('per-fin', d.fin);
        var chk = document.getElementById('per-activo'); if (chk) chk.checked = d.activo === '1';
        var t = document.getElementById('per-form-title'); if (t) t.innerHTML = '<i class="ti ti-pencil me-1"></i>Editar período';
        var c = document.getElementById('per-cancelar'); if (c) c.classList.remove('d-none');
      });
    });
    var cancel = document.getElementById('per-cancelar');
    if (cancel) cancel.addEventListener('click', function () {
      ['per-pk','per-nombre','per-inicio','per-fin'].forEach(function (id) { var el = document.getElementById(id); if (el) el.value = ''; });
      var chk = document.getElementById('per-activo'); if (chk) chk.checked = false;
      var t = document.getElementById('per-form-title'); if (t) t.innerHTML = '<i class="ti ti-plus me-1"></i>Nuevo período';
      this.classList.add('d-none');
    });
  })();

  // Carga perezosa del Historial de alumnado (una sola vez, al abrir el tab)
  (function () {
    var btn = document.getElementById('tab-historial-btn');
    var wrap = document.getElementById('historial-wrap');
    var cargado = false;
    if (!btn || !wrap) return;
    btn.addEventListener('shown.bs.tab', function () {
      if (cargado) return;
      cargado = true;
      fetch(wrap.dataset.url, { credentials: 'same-origin' })
        .then(function (r) { return r.text(); })
        .then(function (html) { wrap.innerHTML = html; })
        .catch(function () {
          wrap.innerHTML = '<div class="alert alert-danger m-3">No se pudo cargar el historial. Recarga la página.</div>';
          cargado = false;
        });
    });
  })();

window._PAGE = {
    csrf:           CFG.v0,
    isSuperuser:    CFG.j5,
    urlReenviar:    CFG.v1,
    urlSetCoord:    CFG.v2,
    urlEditarAjax:  CFG.v3,
    urlBulkDelete:  CFG.v4,
    coordsBL:  ['Mr. Martinez','Miss Alcerro','Mr. Ruiz','Mrs. Varela'],
    coordsCOL: ['Profe. Licona','Profe. Felipe','Profe. Gabriela'],
  };

(function () {
    // ════════ Toast de descarga ════════
    var toast = document.getElementById('zip-toast');
    var elTitle = document.getElementById('zip-toast-title');
    var elText  = document.getElementById('zip-toast-text');
    var elBar   = document.getElementById('zip-toast-bar');
    var elIcon  = document.getElementById('zip-toast-icon');
    document.getElementById('zip-toast-close').addEventListener('click', function(){ toast.style.display='none'; });
    function fmt(b){ if(!b) return '0 MB'; return (b/1024/1024).toFixed(2)+' MB'; }
    function tShow(){ toast.style.display='block'; }
    function tPrep(){
      tShow(); elIcon.className='ti ti-loader text-success'; elTitle.textContent='Preparando descarga…';
      elText.textContent='Generando el ZIP en el servidor, espera un momento…';
      elBar.className='progress-bar progress-bar-striped progress-bar-animated bg-success'; elBar.style.width='100%';
    }
    function tProgress(loaded, total){
      elIcon.className='ti ti-download text-success'; elTitle.textContent='Descargando ZIP…';
      if(total){ var p=Math.round(loaded/total*100); elBar.style.width=p+'%'; elBar.classList.remove('progress-bar-animated');
        elText.textContent=fmt(loaded)+' de '+fmt(total)+' ('+p+'%)'; }
      else { elText.textContent=fmt(loaded)+' descargados…'; }
    }
    function tDone(size, name){
      elIcon.className='ti ti-circle-check text-success'; elTitle.textContent='Descarga lista ✓';
      elBar.className='progress-bar bg-success'; elBar.style.width='100%';
      elText.innerHTML='<strong>'+name+'</strong> — '+fmt(size);
      setTimeout(function(){ toast.style.display='none'; }, 6000);
    }
    function tError(msg){
      elIcon.className='ti ti-alert-circle text-danger'; elTitle.textContent='Error en la descarga';
      elBar.className='progress-bar bg-danger'; elBar.style.width='100%'; elText.textContent=msg||'Intenta de nuevo.';
    }

    var btn = document.getElementById('btn-zip-download');
    if (btn) btn.addEventListener('click', async function(){
      var base = btn.dataset.url;
      var params = new URLSearchParams();
      var fd = document.getElementById('filtro-docente');
      var fc = document.getElementById('filtro-coord');
      if (fd && fd.value) params.set('docente', fd.value);
      if (fc && fc.value) params.set('coord', fc.value);
      var url = base + (params.toString() ? ('?'+params.toString()) : '');
      btn.disabled = true; tPrep();
      try {
        var resp = await fetch(url, { credentials:'same-origin' });
        if (!resp.ok) throw new Error('El servidor respondió '+resp.status);
        var total = parseInt(resp.headers.get('Content-Length')||'0', 10);
        var disp  = resp.headers.get('Content-Disposition')||'';
        var mm = disp.match(/filename="?([^"]+)"?/);
        var fname = mm ? mm[1] : 'reportes.zip';
        var reader = resp.body.getReader(); var chunks=[]; var loaded=0;
        while (true) {
          var rd = await reader.read();
          if (rd.done) break;
          chunks.push(rd.value); loaded += rd.value.length;
          tProgress(loaded, total);
        }
        var blob = new Blob(chunks, { type:'application/zip' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob); a.download = fname;
        document.body.appendChild(a); a.click();
        setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); }, 1000);
        tDone(blob.size, fname);
      } catch (e) {
        tError(e.message);
      } finally {
        btn.disabled = false;
      }
    });

    // ════════ Filtros Docente / Coordinador ════════
    function dt(id){ try { return $('#'+id).DataTable(); } catch(e){ return null; } }
    // Poblar opciones de docente desde las filas
    var selDoc = document.getElementById('filtro-docente');
    if (selDoc) {
      // Catálogo server-side ya cargado; agregar solo docentes de filas que falten
      var existentes = new Set([...selDoc.options].map(function(o){ return o.value; }));
      var docs = new Set();
      document.querySelectorAll('#tabla-academicos tbody tr[data-docente], #tabla-conductuales tbody tr[data-docente]')
        .forEach(function(tr){ if (tr.dataset.docente) docs.add(tr.dataset.docente.trim()); });
      Array.from(docs).sort().forEach(function(d){
        if (existentes.has(d)) return;
        var o=document.createElement('option'); o.value=d; o.textContent=d; selDoc.appendChild(o);
      });
    }
    // Filtro custom de DataTables (solo tablas de reportes)
    if ($.fn.dataTable) {
      $.fn.dataTable.ext.search.push(function(settings, data, dataIndex){
        var id = settings.nTable.id;
        if (id !== 'tabla-academicos' && id !== 'tabla-conductuales') return true;
        var tr = settings.aoData[dataIndex].nTr;
        var fdv = (document.getElementById('filtro-docente')||{}).value || '';
        var fcv = (document.getElementById('filtro-coord')||{}).value || '';
        if (fdv && (tr.dataset.docente||'') !== fdv) return false;
        if (fcv && (tr.dataset.coord||'') !== fcv) return false;
        return true;
      });
    }
    function aplicarFiltros(){ ['tabla-academicos','tabla-conductuales'].forEach(function(id){ var t=dt(id); if(t) t.draw(); }); }
    if (selDoc) selDoc.addEventListener('change', aplicarFiltros);
    var selCoord = document.getElementById('filtro-coord');
    if (selCoord) selCoord.addEventListener('change', aplicarFiltros);
    var btnLimpiar = document.getElementById('btn-limpiar-filtros');
    if (btnLimpiar) btnLimpiar.addEventListener('click', function(){
      if (selDoc) selDoc.value=''; if (selCoord) selCoord.value=''; aplicarFiltros();
    });
  })();
