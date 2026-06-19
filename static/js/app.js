/* ════════════════════════════════════════════════════
   STATE & HELPERS
════════════════════════════════════════════════════ */
let EQ=[],USR=[],LOANS=[],LOANS_MASIVOS=[],MANTS=[],LICENCIAS=[],APLICATIVOS=[],CELULARES=[],SIMCARDS=[],ASIGNACIONES=[],DASH={},TIPOS=[],ROLES=[];
let editEqId=null, editUsrId=null, editMantId=null, editLoanId=null, editLicenseId=null, curHVId=null;
const TODAY=new Date().toISOString().split('T')[0];

const CACHE_KEY='activosla_v1';
const CACHE_TTL=60000;
function _saveCache(d,sec,mr){try{localStorage.setItem(CACHE_KEY,JSON.stringify({ts:Date.now(),d,sec,mr}));}catch(e){}}
function _loadCache(){try{const r=JSON.parse(localStorage.getItem(CACHE_KEY)||'null');return r&&Date.now()-r.ts<CACHE_TTL?r:null;}catch(e){return null;}}
function _invalidateCache(){try{localStorage.removeItem(CACHE_KEY);}catch(e){}}

const _dbt={};
function db(key,fn){clearTimeout(_dbt[key]);_dbt[key]=setTimeout(fn,200);}

const api=async(url,m='GET',b=null)=>{
  try{
    const r=await fetch(url,{method:m,credentials:'include',headers:{'Content-Type':'application/json'},body:b?JSON.stringify(b):null});
    const data=await r.json();
    if(!r.ok) return {error:data.error||'API Error'};
    if(m!=='GET') _invalidateCache();
    return data;
  }catch(e){
    return {error:e.message};
  }
};

const open=id=>document.getElementById(id).classList.add('open');
const close=id=>{
  document.getElementById(id).classList.remove('open');
  // Resetear flag de envío si el modal se cierra
  isSubmitting=false;
};
const $=id=>document.getElementById(id);

function toast(msg,type='info'){
  const icons={ok:'✅',err:'❌',info:'ℹ️'};
  const t=document.createElement('div');
  t.className=`toast ${type}`;
  t.textContent=`${icons[type]||'ℹ️'} ${msg}`;
  const wrap=document.getElementById('toastWrap')||document.body;
  wrap.appendChild(t);
  setTimeout(()=>t.remove(),3500);
}

const fmt=n=>n?'$'+Number(n).toLocaleString('es-CO'):'—';
const fmtDate=d=>{
  if(!d)return'—';
  // Manejar ISO timestamps (2026-03-26T15:09:57.237541)
  if(d.includes('T')){
    const[datePart,timePart]=d.split('T');
    const[y,mo,dd]=datePart.split('-');
    const[hh,mm]=timePart.split(':');
    return`${dd}/${mo}/${y} ${hh}:${mm}`;
  }
  // Si solo es YYYY-MM-DD
  const[y,mo,dd]=d.split('-');
  return`${dd}/${mo}/${y}`;
};
const daysLeft=d=>{if(!d)return null;const diff=Math.ceil((new Date(d)-new Date(TODAY))/(1000*60*60*24));return diff};

const TIPO_ICON={Computador:'💻',Teclado:'⌨️',Mouse:'🖱️',Monitor:'🖥️',UPS:'🔋',Impresora:'🖨️',Tablet:'📱','Teléfono':'☎️',Tripode:'📷',Silla:'🪑','Pantalla led':'📺',Servidor:'🗄️',Router:'📡',Switch:'🔀',Otro:'📦'};
const AV_COLORS=['#4f8ef7','#2dd4bf','#a78bfa','#fbbf24','#f87171','#34d399','#fb923c'];

function bsClass(s){
  const m={bueno:'bs-bueno',regular:'bs-regular','dañado':'bs-dañado',en_reparacion:'bs-en_reparacion',
    activo:'bs-activo',inactivo:'bs-inactivo',bloqueado:'bs-bloqueado',reserva:'bs-reserva',desactivado:'bs-desactivado',devuelto:'bs-devuelto',
    completado:'bs-completado',en_proceso:'bs-en_proceso',pendiente:'bs-pendiente',
    preventivo:'bs-preventivo',correctivo:'bs-correctivo',
    solicitado:'bs-solicitado',firmado:'bs-firmado',vencido:'bs-vencido','por_vencer':'bs-amber'};
  return m[s]||'';
}
function bsLabel(s){
  const m={bueno:'Bueno',regular:'Regular','dañado':'Dañado',en_reparacion:'En reparación',
    activo:'Activo',inactivo:'Inactivo',bloqueado:'Bloqueado',reserva:'Reserva',desactivado:'Desactivado',devuelto:'Devuelto',
    completado:'Completado',en_proceso:'En proceso',pendiente:'Pendiente',
    preventivo:'Preventivo',correctivo:'Correctivo',
    solicitado:'Solicitado',firmado:'Firmado',vencido:'Vencido','por_vencer':'Por vencer'};
  return m[s]||s;
}

/* ════════════════════════════════════════════════════
   ADVANCED FILTER SYSTEM - Búsqueda Multi-campo
════════════════════════════════════════════════════ */

// Definición de campos de búsqueda por vista
const SEARCH_FIELDS={
  eq:['nombre','serial','marca','modelo','tipo_nombre','disponibilidad'],
  usu:['nombre','email','notification_email','departamento','telefono'],
  mant:['equipo_nombre','descripcion','tecnico'],
  loan:['equipo_nombre','usuario_nombre','departamento'],
  license:['nombre','proveedor','tipo'],
  aplicativo:['nombre'],
  celular:['nombre','marca','imei','imei2'],
  simcard:['numero','operador','celular.imei'],
  asignaciones:['equipo.nombre','equipo.serial','usuario.nombre','usuario.departamento'],
  tipos:['nombre','descripcion'],
  roles:['nombre','descripcion']
};

// Función para obtener valor anidado (ej: 'equipo.nombre')
function getNestedValue(obj,path){
  if(!obj||!path)return '';
  return path.split('.').reduce((acc,part)=>acc?.[part]||'',obj);
}

// Búsqueda multi-campo mejorada
function searchMultiField(data,query,fieldsArray){
  if(!query||query.length<1)return data;
  const q=query.toLowerCase();
  return data.filter(item=>
    fieldsArray.some(field=>{
      const value=getNestedValue(item,field);
      return String(value).toLowerCase().includes(q);
    })
  );
}

// Sistema de filtros por vista
const activeFilters={};

function applyAdvancedFilters(viewType,data){
  const filters=activeFilters[viewType]||[];
  if(!filters.length)return data;
  
  return data.filter(item=>{
    return filters.every(filter=>{
      const value=getNestedValue(item,filter.field);
      switch(filter.operator){
        case'equals':return String(value)===String(filter.value);
        case'contains':return String(value).toLowerCase().includes(String(filter.value).toLowerCase());
        case'gt':return Number(value)>Number(filter.value);
        case'lt':return Number(value)<Number(filter.value);
        case'gte':return Number(value)>=Number(filter.value);
        case'lte':return Number(value)<=Number(filter.value);
        case'in':return filter.value.includes(value);
        case'date_after':return new Date(value)>=new Date(filter.value);
        case'date_before':return new Date(value)<=new Date(filter.value);
        default:return true;
      }
    });
  });
}

function addFilter(viewType,field,operator,value,label=''){
  if(!activeFilters[viewType])activeFilters[viewType]=[];
  const filterId='f_'+Math.random().toString(36).substr(2,9);
  activeFilters[viewType].push({id:filterId,field,operator,value,label});
  return filterId;
}

function removeFilter(viewType,filterId){
  if(!activeFilters[viewType])return;
  activeFilters[viewType]=activeFilters[viewType].filter(f=>f.id!==filterId);
}

function clearAllFilters(viewType){
  activeFilters[viewType]=[];
}

function getActiveFilters(viewType){
  return activeFilters[viewType]||[];
}

/* ════════════════════════════════════════════════════
   NAVIGATION
════════════════════════════════════════════════════ */
const PAGE_TITLES={dashboard:'Panel de control',equipos:'Equipos',mantenimientos:'Mantenimientos',
  usuarios:'Responsables',prestamos:'Préstamos',licencias:'Licencias',aplicativos:'Aplicativos',celulares:'Celulares',simcards:'SIM Cards',calendario:'Calendario',reportes:'Reportes','admin-tipos':'Tipos de Equipos','admin-roles':'Roles',etiquetas:'Etiquetas de Activos'};

function toggleSidebar(){
  const sb=document.querySelector('.sidebar');
  const ov=$('sidebarOverlay');
  sb.classList.toggle('open');
  ov.classList.toggle('open');
}
function closeSidebar(){
  document.querySelector('.sidebar')?.classList.remove('open');
  $('sidebarOverlay')?.classList.remove('open');
}

function nav(page){
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
  $('page-'+page).classList.add('active');
  $('pgTitle').textContent=PAGE_TITLES[page]||page;
  document.querySelectorAll('.nav-btn').forEach(b=>{if(b.getAttribute('onclick')?.includes(`'${page}'`))b.classList.add('active')});
  closeSidebar();
  const _safe=(fn,name)=>{try{fn();}catch(e){console.error('[nav:'+name+']',e);}};
  if(page==='equipos')_safe(renderEq,'equipos');
  if(page==='mantenimientos'){_safe(updateMantEquiposSelect,'updateMantSel');_safe(renderMant,'mant');}
  if(page==='usuarios'){_safe(updateDptosSelect,'updateDptos');_safe(renderUsr,'usr');}
  if(page==='prestamos'){_safe(updateLoanDptosSelect,'updateLoanDptos');_safe(renderLoan,'loan');}
  if(page==='licencias'){_safe(updateLicenseProveedoresSelect,'updateLicProv');_safe(renderLicenses,'licencias');}
  if(page==='aplicativos')_safe(renderAplicativos,'aplicativos');
  if(page==='celulares'){_safe(updateCelularMarcasSelect,'updateCelMarcas');_safe(renderCelulares,'celulares');}
  if(page==='simcards')_safe(renderSimcards,'simcards');
  if(page==='asignaciones'){_safe(actualizarFiltrosAsignaciones,'filtrosAsig');_safe(renderAsignaciones,'asignaciones');}
  if(page==='calendario')_safe(renderCal,'calendario');
  if(page==='reportes')_safe(renderReportes,'reportes');
  if(page==='admin-tipos')_safe(renderTipos,'tipos');
  if(page==='admin-roles'){_safe(loadRoles,'loadRoles');_safe(renderRoles,'roles');}
  if(page==='etiquetas')_safe(renderEtiquetas,'etiquetas');
}

/* ════════════════════════════════════════════════════
   INIT
════════════════════════════════════════════════════ */
async function init(){
  const [user]=await Promise.all([api('/api/user').catch(()=>null),loadAll()]);
  if(user&&!user.error){
    $('uName').textContent=user.nombre||'Administrador';
    $('userEmail').textContent=user.email||'email@example.com';
    $('pgDate').textContent=`Hola, ${user.nombre||'Administrador'} · ${new Date().toLocaleDateString('es-CO',{weekday:'long',day:'2-digit',month:'long',year:'numeric'})}`;
  }
  renderDashboard();
  const activePage=document.querySelector('.page.active')?.id?.replace('page-','');
  if(activePage&&activePage!=='dashboard') nav(activePage);
  const eqMatch=window.location.pathname.match(/\/equipo\/(\d+)/);
  if(eqMatch){
    const targetId=parseInt(eqMatch[1]);
    nav('equipos');
    const eq=EQ.find(e=>e.id===targetId);
    if(eq){toast(`Equipo: ${eq.nombre}`,'ok');editEq(targetId);}
    else toast('Equipo no encontrado en inventario','err');
  }
}

function _enrich(){
  const em=Object.fromEntries(EQ.map(e=>[e.id,e]));
  const um=Object.fromEntries(USR.map(u=>[u.id,u]));
  LOANS=LOANS.map(l=>{const e=em[l.equipo_id]||{},u=um[l.usuario_id]||{};return{...l,equipo_nombre:e.nombre||'Equipo desconocido',equipo_tipo:e.tipo_nombre||'Desconocido',usuario_nombre:u.nombre||'Usuario desconocido',departamento:u.departamento||''};});
  MANTS=MANTS.map(m=>{const e=em[m.equipo_id]||{};return{...m,equipo_nombre:e.nombre||'Equipo desconocido',equipo_tipo:e.tipo_nombre||'Desconocido'};});
  ASIGNACIONES=ASIGNACIONES.map(a=>({...a,equipo:em[a.equipo_id]||{},usuario:um[a.usuario_id]||{}}));
}

function computeDash(){
  const today=new Date().toISOString().split('T')[0];
  const in7=new Date(Date.now()+7*864e5).toISOString().split('T')[0];
  const estados={},tipos_count={};let valor_total=0;
  for(const eq of EQ){
    const est=eq.estado||'desconocido';estados[est]=(estados[est]||0)+1;
    const t=eq.tipo_nombre||eq.tipo||'Sin tipo';tipos_count[t]=(tipos_count[t]||0)+1;
    valor_total+=parseInt(eq.valor||0)||0;
  }
  const tipos_equipos=Object.entries(tipos_count).sort((a,b)=>b[1]-a[1]).slice(0,7).map(([k,v])=>({tipo_nombre:k,tipo:k,count:v}));
  let prestamos_activos=0,mant_en_proceso=0,preventivos_vencidos=0;
  const prestamos_vencidos=[],proximos_vencer=[];
  for(const l of LOANS){
    if(l.estado!=='devuelto'){
      prestamos_activos++;
      const fd=l.fecha_devolucion_esperada;
      if(fd){if(fd<today)prestamos_vencidos.push(l);else if(fd<=in7)proximos_vencer.push(l);}
    }
  }
  for(const l of (LOANS_MASIVOS||[])){
    if(l.estado!=='devuelto'){
      prestamos_activos++;
      const fd=l.fecha_devolucion_esperada;
      if(fd){if(fd<today)prestamos_vencidos.push(l);else if(fd<=in7)proximos_vencer.push(l);}
    }
  }
  for(const m of MANTS){
    if(m.estado!=='completado')mant_en_proceso++;
    if(m.tipo==='preventivo'&&m.proxima_revision&&m.proxima_revision<today)preventivos_vencidos++;
  }
  return{total_equipos:EQ.length,total_usuarios:USR.filter(u=>u.estado==='activo').length,prestamos_activos,mant_en_proceso,estados,tipos_equipos,preventivos_vencidos,valor_total,proximos_vencer,prestamos_vencidos};
}

async function _refreshEq(){const r=await api('/api/equipos');if(!r.error&&Array.isArray(r)){EQ=r;_enrich();}}
async function _refreshUsr(){const r=await api('/api/usuarios');if(!r.error&&Array.isArray(r)){USR=r;_enrich();}}
async function _refreshLoans(){const r=await api('/api/prestamos');if(!r.error&&Array.isArray(r)){const em=Object.fromEntries(EQ.map(e=>[e.id,e])),um=Object.fromEntries(USR.map(u=>[u.id,u]));LOANS=r.map(l=>{const e=em[l.equipo_id]||{},u=um[l.usuario_id]||{};return{...l,equipo_nombre:e.nombre||'Equipo desconocido',equipo_tipo:e.tipo_nombre||'Desconocido',usuario_nombre:u.nombre||'Usuario desconocido',departamento:u.departamento||''};});}}
async function _refreshLoansMasivos(){const r=await api('/api/prestamos/masivos');if(!r.error&&Array.isArray(r)){const um=Object.fromEntries(USR.map(u=>[u.id,u]));LOANS_MASIVOS=r.map(l=>{const u=um[l.usuario_id]||{};return{...l,_tipo:'masivo',usuario_nombre:u.nombre||'Usuario desconocido',departamento:u.departamento||''};});}}
async function _refreshMants(){const r=await api('/api/mantenimientos');if(!r.error&&Array.isArray(r)){const em=Object.fromEntries(EQ.map(e=>[e.id,e]));MANTS=r.map(m=>{const e=em[m.equipo_id]||{};return{...m,equipo_nombre:e.nombre||'Equipo desconocido',equipo_tipo:e.tipo_nombre||'Desconocido'};});}}
async function _refreshLics(){const r=await api('/api/licencias');if(!r.error&&Array.isArray(r))LICENCIAS=r;}
async function _refreshApps(){const r=await api('/api/aplicativos');if(!r.error&&Array.isArray(r))APLICATIVOS=r;}
async function _refreshCels(){const r=await api('/api/celulares');if(!r.error&&Array.isArray(r))CELULARES=r;}
async function _refreshSims(){const r=await api('/api/simcards');if(!r.error&&Array.isArray(r))SIMCARDS=r;}
async function _refreshAsigs(){const r=await api('/api/asignaciones-equipos');if(!r.error&&Array.isArray(r)){const em=Object.fromEntries(EQ.map(e=>[e.id,e])),um=Object.fromEntries(USR.map(u=>[u.id,u]));ASIGNACIONES=r.map(a=>({...a,equipo:em[a.equipo_id]||{},usuario:um[a.usuario_id]||{}}));}}

function _applyData(d,sec,mr){
  EQ=d.equipos||[];USR=d.usuarios||[];TIPOS=d.tipos||[];ROLES=d.roles||[];
  LICENCIAS=sec.licencias||[];APLICATIVOS=sec.aplicativos||[];
  CELULARES=sec.celulares||[];
  const cm=Object.fromEntries(CELULARES.map(c=>[c.id,c]));
  SIMCARDS=(sec.simcards||[]).map(s=>({...s,celular:cm[s.celular_id]||null}));
  const simsByCel={};
  SIMCARDS.forEach(s=>{if(s.celular_id)(simsByCel[s.celular_id]=simsByCel[s.celular_id]||[]).push(s);});
  CELULARES=CELULARES.map(c=>({...c,simcard:simsByCel[c.id]||[]}));
  const em=Object.fromEntries(EQ.map(e=>[e.id,e]));
  const um=Object.fromEntries(USR.map(u=>[u.id,u]));
  LOANS=(d.prestamos||[]).map(l=>{const e=em[l.equipo_id]||{},u=um[l.usuario_id]||{};return{...l,equipo_nombre:e.nombre||'Equipo desconocido',equipo_tipo:e.tipo_nombre||'Desconocido',usuario_nombre:u.nombre||'Usuario desconocido',departamento:u.departamento||''};});
  MANTS=(sec.mantenimientos||[]).map(m=>{const e=em[m.equipo_id]||{};return{...m,equipo_nombre:e.nombre||'Equipo desconocido',equipo_tipo:e.tipo_nombre||'Desconocido'};});
  ASIGNACIONES=(sec.asignaciones||[]).map(a=>({...a,equipo:em[a.equipo_id]||{},usuario:um[a.usuario_id]||{}}));
  if(!mr.error&&Array.isArray(mr))
    LOANS_MASIVOS=mr.map(l=>{const u=um[l.usuario_id]||{};return{...l,_tipo:'masivo',usuario_nombre:u.nombre||'Usuario desconocido',departamento:u.departamento||''};});
}

async function loadAll(){
  try{
    const cached=_loadCache();
    if(cached){
      _applyData(cached.d,cached.sec,cached.mr||[]);
      DASH=computeDash();updateTiposFilter();updateNavBadges();
      // Refrescar datos en background sin bloquear la UI
      Promise.all([api('/api/init'),api('/api/init/secondary'),api('/api/prestamos/masivos')])
        .then(([d,sec,mr])=>{if(!d.error){_saveCache(d,sec,mr);_applyData(d,sec,mr);DASH=computeDash();updateNavBadges();}})
        .catch(()=>{});
      return;
    }
    const [d,sec,mr]=await Promise.all([api('/api/init'),api('/api/init/secondary'),api('/api/prestamos/masivos')]);
    if(d.error){toast('Error loading data: '+d.error,'err');return;}
    _saveCache(d,sec,mr);
    _applyData(d,sec,mr);
    DASH=computeDash();
    updateTiposFilter();
    updateNavBadges();
  }catch(e){
    console.error('[loadAll] excepción:',e);
    toast('Error fatal al cargar datos','err');
  }
}

// Cargar tipos de equipos disponibles
async function loadTiposEquipos(){
  try{
    const res=await api('/api/tipos-equipos');
    if(Array.isArray(res)){
      TIPOS=res;
      // Actualizar el select de filtro
      const ftTipo=$('ftTipo');
      const oldValue=ftTipo.value;
      ftTipo.innerHTML='<option value="">Todos los tipos</option>';
      TIPOS.forEach(t=>{
        const opt=document.createElement('option');
        opt.value=t.nombre;
        opt.textContent=t.nombre;
        ftTipo.appendChild(opt);
      });
      ftTipo.value=oldValue;
    }
  }catch(e){
  }
}

// Cargar roles de empresa
async function loadRoles(){
  try{
    const res=await api('/api/roles');
    if(Array.isArray(res)){
      ROLES=res;
    }
  }catch(e){
  }
}

// Actualizar select de tipos en modal de equipos
function updateTiposInModal(){
  const sel=$('eTipo');
  const oldValue=sel.value;
  sel.innerHTML='<option value="">Seleccionar…</option>';
  TIPOS.forEach(t=>{
    const opt=document.createElement('option');
    opt.value=t.nombre;
    opt.textContent=t.nombre;
    sel.appendChild(opt);
  });
  sel.value=oldValue;
}

function updateTiposFilter(){
  const tipos=[...new Set(EQ.map(e=>e.tipo_nombre||e.tipo).filter(t=>t))].sort();
  const sel=$('ftTipo');
  const current=sel.value;
  sel.innerHTML='<option value="">Todos los tipos</option>';
  tipos.forEach(t=>{
    const opt=document.createElement('option');
    opt.value=t;
    opt.textContent=t;
    sel.appendChild(opt);
  });
  sel.value=current;
}

function updateNavBadges(){
  const nbMant=$('nb-mant'), nbLoan=$('nb-loan');
  const enProceso=MANTS.filter(m=>m.estado==='en_proceso').length;
  const alertLoans=(DASH.prestamos_vencidos||[]).length+(DASH.proximos_vencer||[]).length;
  nbMant.style.display=enProceso>0?'flex':'none'; nbMant.textContent=enProceso;
  nbLoan.style.display=alertLoans>0?'flex':'none'; nbLoan.textContent=alertLoans;
  updateDptosSelect();
  updateTiposFilter();
}

/* ════════════════════════════════════════════════════
   DASHBOARD
════════════════════════════════════════════════════ */
function renderDashboard(){
  try{_renderDashboard();}catch(e){console.error('[renderDashboard] error:',e);}
}
function _renderDashboard(){
  const d=DASH;
  const venc=d.prestamos_vencidos||[];
  const prox=d.proximos_vencer||[];

  // ── Stat cards principales ──────────────────────────────────────────
  const valorM=d.valor_total?(d.valor_total>=1000000?(d.valor_total/1000000).toFixed(1)+'M':(d.valor_total/1000).toFixed(0)+'K'):'0';
  const dispCount=(d.estados||{})['Disponible']||(EQ.filter(e=>e.disponibilidad==='Disponible').length)||0;
  const prestVenc=venc.length;

  $('statsRow').innerHTML=`
    <div class="stat-card" style="--accent-color:var(--blue);cursor:pointer" onclick="nav('equipos')">
      <div class="stat-card-row">
        <div class="stat-card-icon" style="background:var(--blue-soft)">💻</div>
        <span class="stat-trend stat-trend-neu">${dispCount} disp.</span>
      </div>
      <div class="stat-value" style="color:var(--blue)">${d.total_equipos||0}</div>
      <div class="stat-label" style="margin-top:4px">Total equipos</div>
      <div class="stat-sub">Valor: <strong style="color:var(--text)">$${valorM}</strong></div>
    </div>
    <div class="stat-card" style="--accent-color:var(--teal);cursor:pointer" onclick="nav('usuarios')">
      <div class="stat-card-row">
        <div class="stat-card-icon" style="background:var(--teal-soft)">👥</div>
        <span class="stat-trend stat-trend-up">Activos</span>
      </div>
      <div class="stat-value" style="color:var(--teal)">${d.total_usuarios||0}</div>
      <div class="stat-label" style="margin-top:4px">Responsables</div>
      <div class="stat-sub">Usuarios en el sistema</div>
    </div>
    <div class="stat-card" style="--accent-color:var(--amber);cursor:pointer" onclick="nav('prestamos')">
      <div class="stat-card-row">
        <div class="stat-card-icon" style="background:var(--amber-soft)">🔁</div>
        <span class="stat-trend ${prestVenc>0?'stat-trend-err':'stat-trend-up'}">${prestVenc>0?prestVenc+' venc.':'Al día'}</span>
      </div>
      <div class="stat-value" style="color:var(--amber)">${d.prestamos_activos||0}</div>
      <div class="stat-label" style="margin-top:4px">Préstamos activos</div>
      <div class="stat-sub">${prox.length} por vencer pronto</div>
    </div>
    <div class="stat-card" style="--accent-color:var(--${d.mant_en_proceso>0?'red':'green'});cursor:pointer" onclick="nav('mantenimientos')">
      <div class="stat-card-row">
        <div class="stat-card-icon" style="background:var(--${d.mant_en_proceso>0?'red-soft':'green-soft'})">🔧</div>
        <span class="stat-trend ${d.mant_en_proceso>0?'stat-trend-err':'stat-trend-up'}">${d.mant_en_proceso>0?'Activos':'OK'}</span>
      </div>
      <div class="stat-value" style="color:var(--${d.mant_en_proceso>0?'red':'green'})">${d.mant_en_proceso||0}</div>
      <div class="stat-label" style="margin-top:4px">Mantenimientos</div>
      <div class="stat-sub">${d.preventivos_vencidos||0} revisión(es) vencida(s)</div>
    </div>
  `;

  // ── KPI secundario: categorías adicionales ──────────────────────────
  const asigAbiertas=ASIGNACIONES.filter(a=>a.estado==='abierta').length;
  const licsActivas=LICENCIAS.filter(l=>l.estado==='activa').length;
  const licsVencen=LICENCIAS.filter(l=>{
    if(!l.fecha_caducidad||l.estado==='inactiva') return false;
    return l.fecha_caducidad>=TODAY&&l.fecha_caducidad<=new Date(Date.now()+30*864e5).toISOString().split('T')[0];
  }).length;

  $('dashKpiRow').innerHTML=`
    <div class="kpi-mini" onclick="nav('asignaciones')">
      <div class="kpi-mini-icon" style="background:var(--violet-soft)">📋</div>
      <div>
        <div class="kpi-mini-val" style="color:var(--violet)">${asigAbiertas}</div>
        <div class="kpi-mini-lbl">Asignaciones abiertas</div>
      </div>
    </div>
    <div class="kpi-mini" onclick="nav('licencias')">
      <div class="kpi-mini-icon" style="background:var(--blue-soft)">📜</div>
      <div>
        <div class="kpi-mini-val" style="color:var(--blue)">${licsActivas}</div>
        <div class="kpi-mini-lbl">Licencias activas${licsVencen>0?` <span style="color:var(--amber);font-size:10px">(${licsVencen} por vencer)</span>`:''}</div>
      </div>
    </div>
    <div class="kpi-mini" onclick="nav('celulares')">
      <div class="kpi-mini-icon" style="background:var(--green-soft)">📱</div>
      <div>
        <div class="kpi-mini-val" style="color:var(--green)">${CELULARES.length}</div>
        <div class="kpi-mini-lbl">Celulares registrados <span style="color:var(--text3);font-size:10px">(${SIMCARDS.length} SIM)</span></div>
      </div>
    </div>
  `;

  // ── Alertas de préstamos (dentro del grid) ─────────────────────────
  const alertCard=$('alertsCard');
  if(venc.length||prox.length){
    alertCard.style.display='';
    $('alertsCardSub').textContent=`${venc.length} vencido(s) · ${prox.length} por vencer`;
    let alertHTML='';
    venc.forEach(p=>{
      const dl=daysLeft(p.fecha_devolucion_esperada);
      alertHTML+=`<div class="alert-item alert-vencido" onclick="nav('prestamos')">
        <div class="alert-dot"></div>
        <div class="alert-item-info">
          <div class="alert-item-title">🔴 ${p.equipo_nombre||'Equipo desconocido'}</div>
          <div class="alert-item-sub">${p.usuario_nombre||'—'} · Venció hace ${Math.abs(dl)} día(s)</div>
        </div>
        <div class="alert-item-date">−${Math.abs(dl)}d</div>
      </div>`;
    });
    prox.forEach(p=>{
      const dl=daysLeft(p.fecha_devolucion_esperada);
      alertHTML+=`<div class="alert-item alert-proximo" onclick="nav('prestamos')">
        <div class="alert-dot"></div>
        <div class="alert-item-info">
          <div class="alert-item-title">🟡 ${p.equipo_nombre||'Equipo desconocido'}</div>
          <div class="alert-item-sub">${p.usuario_nombre||'—'} · ${fmtDate(p.fecha_devolucion_esperada)}</div>
        </div>
        <div class="alert-item-date">+${dl}d</div>
      </div>`;
    });
    $('alertsStrip').innerHTML=alertHTML;
  }else{
    alertCard.style.display='none';
  }

  // ── Gráfico de barras (equipos por tipo) ───────────────────────────
  const tipos=d.tipos_equipos||[];
  const maxC=Math.max(...tipos.map(t=>t.count||0),1);
  const barColors=['#4f8ef7','#2dd4bf','#a78bfa','#fbbf24','#f87171','#34d399','#fb923c'];
  $('barChart').innerHTML=tipos.length?tipos.map((t,i)=>`
    <div class="bar-col">
      <div class="bar" style="height:${Math.max((t.count||0)/maxC*100,6)}%;background:${barColors[i%barColors.length]}" title="${t.tipo_nombre}: ${t.count}"></div>
      <div class="bar-lbl">${t.tipo_nombre}</div>
    </div>`).join(''):'<div style="text-align:center;color:var(--text3);padding:20px">Sin datos</div>';

  // ── Donut estado de equipos ────────────────────────────────────────
  const estadosDef=[
    {k:'bueno',label:'Bueno',c:'#34d399'},{k:'regular',label:'Regular',c:'#2dd4bf'},
    {k:'dañado',label:'Dañado',c:'#f87171'},{k:'en_reparacion',label:'En reparación',c:'#fbbf24'}
  ];
  const totalEq=d.total_equipos||1, ests=d.estados||{};
  const cx=55,cy=55,r=38,stroke=14,circ=2*Math.PI*r;
  let offset=0,circles='';
  estadosDef.forEach(e=>{
    const val=ests[e.k]||0;
    const len=(val/totalEq)*circ;
    if(len>0){
      circles+=`<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${e.c}" stroke-width="${stroke}" stroke-dasharray="${len} ${circ-len}" stroke-dashoffset="${-offset}" transform="rotate(-90 ${cx} ${cy})" stroke-linecap="round"/>`;
      offset+=len;
    }
  });
  $('donutSvg').innerHTML=circles+`
    <text x="${cx}" y="${cy-4}" text-anchor="middle" dominant-baseline="middle" style="font-family:var(--font-d);font-size:18px;font-weight:800;fill:var(--text)">${d.total_equipos||0}</text>
    <text x="${cx}" y="${cy+12}" text-anchor="middle" dominant-baseline="middle" style="font-size:8px;fill:var(--text3)">equipos</text>`;
  $('donutLegend').innerHTML=estadosDef.map(e=>{
    const val=ests[e.k]||0;
    return`<div class="legend-item">
      <div class="legend-left"><span class="ldot" style="background:${e.c}"></span>${e.label}</div>
      <div class="legend-right">${val}<span class="legend-pct">(${totalEq?Math.round(val/totalEq*100):0}%)</span></div>
    </div>`;}).join('');

  // ── Indicadores operativos ─────────────────────────────────────────
  $('kpiList').innerHTML=`
    <div class="mini-list-item">
      <div class="mli-icon" style="background:var(--red-soft)">⚠️</div>
      <div class="mli-body"><div class="mli-title">Préstamos vencidos</div><div class="mli-sub">Sin devolver</div></div>
      <div class="mli-right" style="color:var(--${venc.length>0?'red':'green'})">${venc.length}</div>
    </div>
    <div class="mini-list-item">
      <div class="mli-icon" style="background:var(--amber-soft)">🔧</div>
      <div class="mli-body"><div class="mli-title">Reparaciones activas</div><div class="mli-sub">En proceso</div></div>
      <div class="mli-right" style="color:var(--amber)">${d.mant_en_proceso||0}</div>
    </div>
    <div class="mini-list-item">
      <div class="mli-icon" style="background:var(--violet-soft)">🔄</div>
      <div class="mli-body"><div class="mli-title">Revisiones vencidas</div><div class="mli-sub">Requieren atención</div></div>
      <div class="mli-right" style="color:var(--${d.preventivos_vencidos>0?'red':'green'})">${d.preventivos_vencidos||0}</div>
    </div>
    <div class="mini-list-item">
      <div class="mli-icon" style="background:var(--blue-soft)">🔁</div>
      <div class="mli-body"><div class="mli-title">Equipos prestados</div><div class="mli-sub">Actualmente en uso</div></div>
      <div class="mli-right" style="color:var(--blue)">${d.prestamos_activos||0}</div>
    </div>`;

  // ── Actividad reciente ─────────────────────────────────────────────
  const allEvents=[
    ...MANTS.map(m=>{const desc=m.descripcion||'';return{date:m.fecha||'2000-01-01',type:'mant',title:m.equipo_nombre,sub:desc.slice(0,55)+(desc.length>55?'…':''),estado:m.estado,tipoMant:m.tipo};}),
    ...LOANS.map(p=>({date:p.fecha_prestamo||'2000-01-01',type:'loan',title:p.equipo_nombre,sub:`${p.usuario_nombre} — ${p.departamento||''}`,estado:p.estado}))
  ];
  allEvents.sort((a,b)=>new Date(b.date)-new Date(a.date));
  $('recentActivity').innerHTML=allEvents.slice(0,6).map(ev=>{
    if(ev.type==='mant'){
      return`<div class="mini-list-item">
        <div class="mli-icon" style="background:${ev.tipoMant==='preventivo'?'var(--blue-soft)':'var(--orange-soft)'}">${ev.tipoMant==='preventivo'?'🛡️':'🔧'}</div>
        <div class="mli-body"><div class="mli-title">${ev.title}</div><div class="mli-sub">${ev.sub}</div></div>
        <span class="bs ${bsClass(ev.estado)}">${bsLabel(ev.estado)}</span>
      </div>`;
    }
    return`<div class="mini-list-item">
      <div class="mli-icon" style="background:var(--teal-soft)">🔁</div>
      <div class="mli-body"><div class="mli-title">${ev.title}</div><div class="mli-sub">${ev.sub}</div></div>
      <span class="bs ${bsClass(ev.estado)}">${bsLabel(ev.estado)}</span>
    </div>`;
  }).join('')||'<div class="empty"><div class="empty-icon">📋</div><h3>Sin actividad reciente</h3></div>';
}

/* ════════════════════════════════════════════════════
   BÚSQUEDA GLOBAL
════════════════════════════════════════════════════ */
async function gSearchFn(q){
  if(!q || q.length<2){
    $('gSearch').placeholder='Buscar equipos, usuarios…';
    close('ovSearchResults');
    return;
  }
  
  try{
    const res=await api(`/api/busqueda-global?q=${encodeURIComponent(q)}&limit=15`);
    if(res.error){
      close('ovSearchResults');
      return;
    }
    
    const {equipos=[],usuarios=[],prestamos=[],mantenimientos=[]}=res;
    const total=equipos.length+usuarios.length+prestamos.length;
    
    if(total===0){
      toast('No se encontraron resultados','info');
      return;
    }
    
    // Mostrar modal con resultados
    let html='';
    
    if(equipos.length>0){
      html+=`<div style="margin-bottom:16px">
        <div class="card-title" style="margin-bottom:10px">💻 Equipos (${equipos.length})</div>
        <div style="display:flex;flex-direction:column;gap:8px">`;
      equipos.forEach(e=>{
        html+=`<div style="padding:12px;background:var(--surface2);border-radius:8px;cursor:pointer;transition:all .2s;border:1px solid transparent" onclick="nav('equipos'); close('ovSearchResults')" onmouseover="this.style.background='var(--surface3)'" onmouseout="this.style.background='var(--surface2)'">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">
            <div style="flex:1">
              <div style="font-weight:600;color:var(--text)">${e.nombre}</div>
              <div style="font-size:11px;color:var(--text3);margin-top:2px">Serial: <strong>${e.serial||'—'}</strong> · Marca: <strong>${e.marca||'—'}</strong></div>
            </div>
            <span class="bs ${bsClass(e.estado)}">${bsLabel(e.estado)}</span>
          </div>
        </div>`;
      });
      html+='</div></div>';
    }
    
    if(usuarios.length>0){
      html+=`<div style="margin-bottom:16px">
        <div class="card-title" style="margin-bottom:10px">👥 Responsables (${usuarios.length})</div>
        <div style="display:flex;flex-direction:column;gap:8px">`;
      usuarios.forEach(u=>{
        html+=`<div style="padding:12px;background:var(--surface2);border-radius:8px;cursor:pointer;transition:all .2s;border:1px solid transparent" onclick="nav('usuarios'); close('ovSearchResults')" onmouseover="this.style.background='var(--surface3)'" onmouseout="this.style.background='var(--surface2)'">
          <div style="font-weight:600;color:var(--text)">${u.nombre}</div>
          <div style="font-size:11px;color:var(--text3);margin-top:2px">${u.email} · ${u.departamento||'Sin departamento'}</div>
        </div>`;
      });
      html+='</div></div>';
    }
    
    if(prestamos.length>0){
      html+=`<div style="margin-bottom:16px">
        <div class="card-title" style="margin-bottom:10px">🔁 Préstamos (${prestamos.length})</div>
        <div style="display:flex;flex-direction:column;gap:8px">`;
      prestamos.forEach(p=>{
        html+=`<div style="padding:12px;background:var(--surface2);border-radius:8px;cursor:pointer;transition:all .2s;border:1px solid transparent" onclick="nav('prestamos'); close('ovSearchResults')" onmouseover="this.style.background='var(--surface3)'" onmouseout="this.style.background='var(--surface2)'">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">
            <div style="flex:1">
              <div style="font-weight:600;color:var(--text)">${p.equipo}</div>
              <div style="font-size:11px;color:var(--text3);margin-top:2px">Responsable: <strong>${p.responsable}</strong></div>
            </div>
            <span class="bs ${bsClass(p.estado)}">${bsLabel(p.estado)}</span>
          </div>
        </div>`;
      });
      html+='</div></div>';
    }
    
    $('searchQueryDisplay').textContent=`Búsqueda: "${q}" • ${total} resultado(s)`;
    $('searchResultsEquipos').innerHTML=html;
    $('searchResultsUsuarios').innerHTML='';
    $('searchResultsPrestamos').innerHTML='';
    open('ovSearchResults');
  }catch(e){
    toast('Error en búsqueda: '+e.message,'err');
  }
}

/* ════════════════════════════════════════════════════
   HISTORIAL DE RESPONSABLES
════════════════════════════════════════════════════ */
async function showHistorialResponsables(eqId){
  try{
    const res=await api(`/api/equipos/${eqId}/historial-responsables`);
    if(res.error){
      toast('Error al cargar historial: '+res.error,'err');
      return;
    }
    
    const eq=EQ.find(e=>e.id===eqId);
    if(!eq) return;
    
    $('histResponsablesEquipo').textContent=`${eq.nombre} (${eq.serial})`;
    
    let html='';
    res.forEach((item,idx)=>{
      const isActual=item.estado==='actual';
      html+=`<div style="padding:14px;background:${isActual?'var(--surface2)':'var(--surface)'};border:1px solid ${isActual?'var(--blue)':'var(--border)'};border-radius:8px;border-left:3px solid ${isActual?'var(--blue)':'var(--text3)'};display:flex;gap:12px;position:relative">
        <div style="width:6px;height:6px;border-radius:50%;background:${isActual?'var(--green)':'var(--text3)'};margin-top:4px;flex-shrink:0"></div>
        <div style="flex:1">
          <div style="font-weight:600;color:var(--text)">${item.responsable}</div>
          <div style="font-size:12px;color:var(--text3);margin-top:3px;margin-bottom:6px">Desde: ${fmtDate(item.fecha)}</div>
          ${item.notas?`<div style="font-size:12px;background:var(--surface3);padding:6px 8px;border-radius:4px;color:var(--text2)">${item.notas}</div>`:''}
        </div>
        ${isActual?`<div style="background:var(--green-soft);color:var(--green);padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;white-space:nowrap;height:fit-content">ACTUAL</div>`:''}
      </div>`;
    });
    
    $('histResponsablesContent').innerHTML=html||'<div style="text-align:center;padding:20px;color:var(--text3)">Sin historial</div>';
    open('ovHistorialResponsables');
  }catch(e){
    toast('Error al cargar historial: '+e.message,'err');
  }
}

/* ════════════════════════════════════════════════════
   CAMBIAR RESPONSABLE
════════════════════════════════════════════════════ */
async function cambiarResponsable(eqId){
  const eq=EQ.find(e=>e.id===eqId);
  if(!eq) return;
  
  const nuevoUsrId=prompt(`Cambiar responsable de "${eq.nombre}" - Ingresa ID del nuevo usuario:`);
  if(!nuevoUsrId) return;
  
  const res=await api(`/api/equipos/${eqId}/cambiar-responsable`, 'POST', {
    nuevo_usuario_id: parseInt(nuevoUsrId),
    motivo: 'Cambio de asignación manual - Sistema'
  });
  
  if(res.error){
    toast('Error: '+res.error,'err');
  }else{
    toast(res.mensaje,'ok');
    await _refreshEq();DASH=computeDash();
    renderEq();renderDashboard();
  }
}

/* ════════════════════════════════════════════════════
   EQUIPOS
════════════════════════════════════════════════════ */
function renderEq(){
  updateTiposFilter();
  
  // Actualizar filtro de dueño
  const ftDueno = $('ftDueno');
  if(ftDueno && ftDueno.children.length <= 1){
    USR.forEach(u => {
      const opt = document.createElement('option');
      opt.value = u.id;
      opt.textContent = u.nombre;
      ftDueno.appendChild(opt);
    });
  }
  
  const q=($('srchEq')?.value||'');
  const tipo=$('ftTipo')?.value||'';
  const est=$('ftEst')?.value||'';
  const disp=$('ftEqDisp')?.value||'';
  const ordenSerial=$('ftSerial')?.value||'';
  const dueno=$('ftDueno')?.value||'';

  let rows=searchMultiField(EQ,q,SEARCH_FIELDS.eq);

  rows=rows.filter(e=>
    (!tipo||(e.tipo_nombre||e.tipo)===tipo)&&
    (!est||e.estado===est)&&
    (!disp||e.disponibilidad===disp)&&
    (!dueno||e.usuario_id==dueno));
  
  // Aplicar filtros avanzados anidables
  rows=applyAdvancedFilters('eq',rows);
  
  // Ordenar por serial si se seleccionó
  if(ordenSerial==='asc'){
    rows.sort((a,b)=>(a.serial||'').localeCompare(b.serial||''));
  }else if(ordenSerial==='desc'){
    rows.sort((a,b)=>(b.serial||'').localeCompare(a.serial||''));
  }
  
  $('eqCount').textContent=`${rows.length} de ${EQ.length} equipo(s)`;
  
  // Paginación
  const {data:pageData,totalPages,currentPage}=paginateArray(rows,'eq');
  
  const tb=$('eqTbody');
  if(!rows.length){
    tb.innerHTML=`<tr><td colspan="8"><div class="empty"><div class="empty-icon">💻</div><h3>Sin resultados</h3></div></td></tr>`;
    // Limpiar pagination
    const wrapper=tb.parentElement.parentElement;
    const oldPagination=wrapper.querySelector('[data-pagination="eq"]');
    if(oldPagination) oldPagination.remove();
    return;
  }
  
  tb.innerHTML=pageData.map(e=>{
    const responsable=e.usuario_id?USR.find(u=>u.id===e.usuario_id):null;
    const tipoNombre = e.tipo_nombre || e.tipo || 'Sin tipo';
    const isRetirado = e.disponibilidad === 'Retirado';
    const dispLabel = e.disponibilidad || 'Disponible';
    const dispClass = {Disponible:'bs-activo',Asignado:'bs-solicitado','En mantenimiento':'bs-en_proceso',Retirado:'bs-inactivo'}[dispLabel]||'bs-activo';
    return `
    <tr ${isRetirado ? 'style="opacity:0.55;background:rgba(0,0,0,0.3)"' : ''}>
      <td data-label="Equipo"><div class="av-cell">
        <div class="tipo-av">${TIPO_ICON[tipoNombre]||'📦'}</div>
        <div><div class="name">${e.nombre}</div><div class="sub">${[e.marca,e.modelo].filter(Boolean).join(' ')}</div></div>
      </div></td>
      <td data-label="Tipo"><span style="font-size:12px;color:var(--text3)">${tipoNombre}</span></td>
      <td data-label="Serial"><span class="mono">${e.serial||'—'}</span></td>
      <td data-label="Factura"><span style="font-size:12px">${e.num_factura||'—'}</span></td>
      <td data-label="Proveedor"><span style="font-size:12px">${e.nombre_proveedor||'—'}</span></td>
      <td data-label="Empresa"><span style="font-size:12px">${e.nombre_empresa||'—'}</span></td>
      <td data-label="Fecha Ingreso"><span style="font-size:12px">${e.fecha_ingreso||'—'}</span></td>
      <td data-label="Responsable"><span style="font-size:13px;color:var(--text)">${responsable?responsable.nombre:'—'}</span></td>
      <td data-label="Estado"><span class="bs ${bsClass(e.estado)}">${bsLabel(e.estado)}</span></td>
      <td data-label="Disponibilidad"><span class="bs ${dispClass}" style="font-size:11px;padding:4px 8px">${dispLabel}</span></td>
      <td data-label="Valor"><span class="mono" style="color:var(--text)">${fmt(e.valor)}</span></td>
      <td data-label="Acciones"><div class="act-cell">
        <button class="btn btn-ghost btn-icon btn-sm" title="Hoja de vida" onclick="openHV(${e.id})">📋</button>
        <button class="btn btn-ghost btn-icon btn-sm" title="Historial de responsables" onclick="showHistorialResponsables(${e.id})">📜</button>
        <button class="btn btn-ghost btn-icon btn-sm" title="Editar" onclick="editEq(${e.id})">✏️</button>
        <button class="btn btn-danger btn-icon btn-sm" title="Eliminar" onclick="delEq(${e.id})">🗑️</button>
      </div></td>
    </tr>
    `}).join('');
  
  // Agregar/actualizar controles de paginación si hay múltiples páginas
  if(totalPages>1){
    const wrapper=tb.parentElement.parentElement;
    let paginationContainer=wrapper.querySelector('[data-pagination="eq"]');
    if(!paginationContainer){
      paginationContainer=document.createElement('div');
      paginationContainer.setAttribute('data-pagination','eq');
      paginationContainer.className='pagination-wrap';
      wrapper.appendChild(paginationContainer);
    }
    paginationContainer.innerHTML=createPaginationControls(currentPage,totalPages,'eq');
  }else{
    // Remover pagination si no es necesaria
    const wrapper=tb.parentElement.parentElement;
    const paginationContainer=wrapper.querySelector('[data-pagination="eq"]');
    if(paginationContainer) paginationContainer.remove();
  }
}

function getNextSerialNumber(prefix){
  const re=new RegExp(`^${prefix}(\\d{4})$`,'i');
  const nums=EQ.reduce((acc,e)=>{const m=(e.serial||'').match(re);if(m)acc.push(parseInt(m[1]));return acc;},[]);
  return `${prefix}${String((nums.length?Math.max(...nums):0)+1).padStart(4,'0')}`;
}
function onTipoChange(){
  const nombre=$('eTipo').value;
  const tipo=TIPOS.find(t=>t.nombre===nombre);
  const prefix=tipo?.serial_prefix||'';
  const inp=$('eSerial');
  const cur=inp.value.trim();
  // Auto-rellena si el campo está vacío o si ya tiene un serial auto-generado (prefijo + dígitos)
  const isAutoGenerated=cur&&TIPOS.some(t=>t.serial_prefix&&new RegExp(`^${t.serial_prefix}\\d{4}$`,'i').test(cur));
  if(!prefix||(cur&&!isAutoGenerated)) return;
  inp.value=getNextSerialNumber(prefix);
}

function openEqModal(reset=true){
  if(reset){editEqId=null;$('eqModalTitle').textContent='Nuevo equipo';['eNom','eMarca','eModelo','eSerial','eFecha','eValor','eDesc','eNumFactura','eNombreProveedor','eFechaIngreso'].forEach(id=>$(id).value='');$('eTipo').value='';$('eEst').value='bueno';$('eDisp').value='Disponible';$('eResponsable').value='';$('eEmpresaPago').value=''}
  
  // Actualizar tipos
  updateTiposInModal();
  
  // Cargar usuarios activos en el select
  const selResp=$('eResponsable');
  if(selResp.options.length<=1){
    USR.filter(u=>u.estado==='activo').forEach(u=>{
      const opt=document.createElement('option');
      opt.value=u.id;
      opt.textContent=u.nombre;
      selResp.appendChild(opt);
    });
  }
  open('ovEq');
}
function editEq(id){
  const e=EQ.find(x=>x.id===id);if(!e)return;
  editEqId=id;$('eqModalTitle').textContent='Editar equipo';
  $('eNom').value=e.nombre;$('eEst').value=e.estado;$('eDisp').value=e.disponibilidad||'Disponible';
  $('eMarca').value=e.marca||'';$('eModelo').value=e.modelo||'';$('eSerial').value=e.serial||'';
  $('eFecha').value=e.fecha_adquisicion||'';
  $('eValor').value=e.valor||'';$('eDesc').value=e.descripcion||'';
  $('eNumFactura').value=e.num_factura||'';$('eNombreProveedor').value=e.nombre_proveedor||'';
  $('eEmpresaPago').value=e.nombre_empresa||'';$('eFechaIngreso').value=e.fecha_ingreso||'';
  
  // Reconstruir opciones de tipo y asignar el valor correcto
  updateTiposInModal();
  setTimeout(()=>{$('eTipo').value=e.tipo_nombre||e.tipo;},50);
  
  // Cargar usuarios activos en el select si no están ya cargados
  const selResp=$('eResponsable');
  if(selResp.options.length<=1){
    USR.filter(u=>u.estado==='activo').forEach(u=>{
      const opt=document.createElement('option');
      opt.value=u.id;
      opt.textContent=u.nombre;
      selResp.appendChild(opt);
    });
  }
  $('eResponsable').value=e.usuario_id||'';
  
  // Cargar licencias asignadas al equipo
  loadEqLicenses(id);
  
  open('ovEq');
}

// ═══════════════════════════════════════════════════════════
// FUNCIONES DE GESTIÓN DE LICENCIAS EN EQUIPOS
// ═══════════════════════════════════════════════════════════

async function loadEqLicenses(eqId){
  try{
    const result=await api(`/api/equipos/${eqId}/licencias`);
    const licenses=result instanceof Array?result:[];
    
    const container=$('eqLicensesContainer');
    const emptyMsg=$('eqLicensesEmpty');
    const list=$('eqLicensesList');
    
    if(licenses.length===0){
      container.style.display='none';
      emptyMsg.style.display='block';
    }else{
      container.style.display='block';
      emptyMsg.style.display='none';
      list.innerHTML=licenses.map(lic=>{
        const hoy=TODAY;
        const vencida=lic.fecha_caducidad<hoy;
        const color=vencida?'color:var(--red)':lic.fecha_caducidad<=new Date(new Date().setDate(new Date().getDate()+30)).toISOString().split('T')[0]?'color:var(--amber)':'';
        return`<tr style="border-bottom:1px solid var(--border)">
          <td style="padding:8px">${lic.nombre}</td>
          <td style="padding:8px;font-size:12px;color:var(--text3)">${lic.tipo}</td>
          <td style="padding:8px;${color}" class="mono">${fmtDate(lic.fecha_caducidad)}</td>
          <td style="text-align:center;padding:8px">
            <button class="btn btn-danger btn-icon btn-xs" onclick="removeEquipoLicense(${lic.asignacion_id},${eqId})" title="Remover">🗑️</button>
          </td>
        </tr>`;}).join('');
    }
  }catch(e){
    $('eqLicensesList').innerHTML='<tr><td colspan="4" style="padding:20px;text-align:center;color:var(--red)">Error cargando licencias</td></tr>';
  }
}

function openAssignLicenseModal(){
  if(!editEqId){
    toast('Por favor guarda el equipo primero','err');
    return;
  }
  
  // Limpiar modal
  $('licenseAssignDate').value=TODAY;
  $('licenseAssignNotes').value='';
  $('availableLicenseSelect').value='';
  $('assignLicenseSubtitle').textContent='Selecciona una licencia para asignar al equipo';
  
  // Obtener licencias ya asignadas
  const assignedIds=new Set();
  const eqLicRows=$('eqLicensesList')?.querySelectorAll('tr')||[];
  eqLicRows.forEach(row=>{
    const delBtn=row.querySelector('.btn-danger');
    if(delBtn){
      const onclick=delBtn.getAttribute('onclick');
      const match=onclick.match(/removeEquipoLicense\((\d+)/);
      if(match) assignedIds.add(parseInt(match[1]));
    }
  });
  
  // Poblar select con licencias disponibles
  const select=$('availableLicenseSelect');
  select.innerHTML='<option value="">Seleccionar licencia…</option>'+LICENCIAS.filter(lic=>lic.estado==='activa'||lic.estado==='por_vencer').map(lic=>`<option value="${lic.id}">${lic.nombre} (${lic.tipo}) - Vence: ${fmtDate(lic.fecha_caducidad)}</option>`).join('');
  
  open('ovAssignLicense');
}

async function confirmAssignLicense(){
  const licId=$('availableLicenseSelect').value;
  if(!licId){
    toast('Selecciona una licencia','err');
    return;
  }
  
  const btn=$('confirmAssignLicenseBtn');
  btn.disabled=true;
  btn.textContent='Asignando…';
  
  try{
    const data={
      licencia_id:parseInt(licId),
      fecha_asignacion:$('licenseAssignDate').value,
      notas:$('licenseAssignNotes').value
    };
    
    const res=await api(`/api/equipos/${editEqId}/licencias`,'POST',data);
    if(res.error){
      toast(res.error,'err');
      btn.disabled=false;
      btn.textContent='Asignar';
      return;
    }
    
    close('ovAssignLicense');
    await loadEqLicenses(editEqId);
    toast('Licencia asignada correctamente','ok');
    btn.disabled=false;
    btn.textContent='Asignar';
  }catch(e){
    toast('Error al asignar licencia','err');
    btn.disabled=false;
    btn.textContent='Asignar';
  }
}

async function removeEquipoLicense(asignacionId,eqId){
  if(!confirm('¿Remover esta licencia del equipo?'))return;
  
  try{
    const res=await api(`/api/equipos-licencias/${asignacionId}`,'DELETE');
    if(res.error){
      toast('Error al remover licencia: '+res.error,'err');
      return;
    }
    await loadEqLicenses(eqId);
    toast('Licencia removida','ok');
  }catch(e){
    toast('Error al remover licencia: '+e.message,'err');
  }
}

// Agregar nuevo tipo de equipo
function openAgregarTipo(){
  $('newTipoNombre').value='';
  $('newTipoDesc').value='';
  $('newTipoPrefix').value='';
  open('ovAgregarTipo');
}

async function saveNewTipo(){
  const nombre=$('newTipoNombre').value.trim();
  const descripcion=$('newTipoDesc').value.trim();
  
  if(!nombre){
    toast('El nombre del tipo no puede estar vacío','err');
    return;
  }
  
  if(TIPOS.some(t=>t.nombre.toLowerCase()===nombre.toLowerCase())){
    toast(`El tipo "${nombre}" ya existe`,'err');
    return;
  }
  
  try{
    const serial_prefix=$('newTipoPrefix').value||null;
    const res=await api('/api/tipos-equipos','POST',{nombre,descripcion,serial_prefix});
    
    if(res.nombre){
      TIPOS.push(res);
      TIPOS.sort((a,b)=>a.nombre.localeCompare(b.nombre));
      toast(`Tipo "${nombre}" agregado correctamente`,'ok');
      close('ovAgregarTipo');
      await _refreshEq();DASH=computeDash();
      renderTipos();
      updateTiposInModal();
      setTimeout(()=>{$('eTipo').value=nombre;},100);
    }else{
      toast(res.error||'Error al agregar tipo','err');
    }
  }catch(e){
    toast('Error al agregar tipo','err');
  }
}

async function saveEq(){
  // Prevenir múltiples clics
  if(isSubmitting){
    toast('Por favor espera a que termine el proceso','info');
    return;
  }
  
  const data={nombre:$('eNom').value.trim(),tipo:$('eTipo').value,estado:$('eEst').value,disponibilidad:$('eDisp').value,
    marca:$('eMarca').value,modelo:$('eModelo').value,serial:$('eSerial').value,
    usuario_id:parseInt($('eResponsable').value)||null,
    fecha_adquisicion:$('eFecha').value,
    valor:parseFloat($('eValor').value)||0,descripcion:$('eDesc').value,
    num_factura:$('eNumFactura').value.trim(),nombre_proveedor:$('eNombreProveedor').value.trim(),
    nombre_empresa:$('eEmpresaPago').value,fecha_ingreso:$('eFechaIngreso').value};
  if(!data.nombre||!data.tipo){toast('Nombre y tipo son requeridos','err');return}
  
  // Establecer flag y deshabilitar botón
  isSubmitting=true;
  const btn=$('saveEqBtn');
  btn.disabled=true;
  const btnText=editEqId?'Actualizando...':'Registrando...';
  btn.textContent=btnText;
  
  try{
    const res=editEqId?await api('/api/equipos/'+editEqId,'PUT',data):await api('/api/equipos','POST',data);
    if(res.error){toast(res.error,'err');throw new Error(res.error)}
    close('ovEq');await _refreshEq();DASH=computeDash();renderEq();renderDashboard();
    toast(editEqId?'Equipo actualizado':'Equipo registrado correctamente','ok');editEqId=null;
    isSubmitting=false;
    btn.disabled=false;
    btn.textContent='Guardar equipo';
  }catch(e){
    isSubmitting=false;
    btn.disabled=false;
    btn.textContent='Guardar equipo';
  }
}
async function delEq(id){
  if(!confirm('¿Eliminar este equipo? Esta acción no se puede deshacer.'))return;
  await api('/api/equipos/'+id,'DELETE');await _refreshEq();DASH=computeDash();renderEq();renderDashboard();toast('Equipo eliminado','info');
}

/* ════════════════════════════════════════════════════
   PAGINACIÓN
════════════════════════════════════════════════════ */
let currentPage={eq:1,usu:1,loan:1,asignaciones:1,mant:1,license:1,aplicativo:1,celular:1,simcard:1,tipos:1,roles:1};
let isSubmitting=false;
const ITEMS_PER_PAGE={eq:10,usu:15,loan:15,asignaciones:10,mant:10,license:15,aplicativo:15,celular:10,simcard:10,tipos:10,roles:10};

function updateItemsPerPage(entityType){
  try{
    const selectId=entityType==='usu'?'itemsPerPageUsr':'itemsPerPage'+entityType.charAt(0).toUpperCase()+entityType.slice(1);
    const select=document.getElementById(selectId);
    if(select){
      ITEMS_PER_PAGE[entityType]=parseInt(select.value)||10;
      currentPage[entityType]=1;
    }
  }catch(e){
  }
}

function createPaginationControls(currentP,totalPages,entityType){
  if(totalPages<=1)return'';
  const prev=Math.max(1,currentP-1);
  const next=Math.min(totalPages,currentP+1);
  const startPage=Math.max(1,currentP-2);
  const endPage=Math.min(totalPages,currentP+2);

  let nums='';
  if(startPage>1){
    nums+=`<button class="btn btn-ghost btn-sm pag-num" onclick="goToPage(1,'${entityType}')">1</button>`;
    if(startPage>2)nums+=`<span class="pag-dots pag-num">…</span>`;
  }
  for(let i=startPage;i<=endPage;i++){
    nums+=`<button class="btn ${i===currentP?'btn-primary':'btn-ghost'} btn-sm pag-num" onclick="goToPage(${i},'${entityType}')">${i}</button>`;
  }
  if(endPage<totalPages){
    if(endPage<totalPages-1)nums+=`<span class="pag-dots pag-num">…</span>`;
    nums+=`<button class="btn btn-ghost btn-sm pag-num" onclick="goToPage(${totalPages},'${entityType}')">${totalPages}</button>`;
  }

  return`<div class="pagination-bar">
    <button class="btn btn-ghost btn-sm" onclick="goToPage(${prev},'${entityType}')" ${currentP===1?'disabled':''}>← Ant.</button>
    ${nums}
    <span class="pag-info">Pág. ${currentP} / ${totalPages}</span>
    <button class="btn btn-ghost btn-sm" onclick="goToPage(${next},'${entityType}')" ${currentP===totalPages?'disabled':''}>Sig. →</button>
  </div>`;
}

function goToPage(page,entityType){
  currentPage[entityType]=page;
  if(entityType==='eq')renderEq();
  else if(entityType==='usu')renderUsr();
  else if(entityType==='loan')renderLoan();
  else if(entityType==='asignaciones')renderAsignaciones();
  else if(entityType==='mant')renderMant();
  else if(entityType==='celular')renderCelulares();
  else if(entityType==='simcard')renderSimcards();
  else if(entityType==='license')renderLicenses();
  else if(entityType==='aplicativo')renderAplicativos();
  else if(entityType==='tipos')renderTipos();
  else if(entityType==='roles')renderRoles();
}

function paginateArray(arr,entityType){
  if(!arr || arr.length===0) return {data:[],totalPages:0,currentPage:1};
  const pageSize=ITEMS_PER_PAGE[entityType]||10;
  const page=currentPage[entityType]||1;
  const start=(page-1)*pageSize;
  const end=start+pageSize;
  const totalPages=Math.ceil(arr.length/pageSize);
  // Validar que la página actual no exceda el total
  const validPage=Math.min(page,totalPages);
  if(validPage!==page) currentPage[entityType]=validPage;
  return {data:arr.slice((validPage-1)*pageSize,((validPage-1)*pageSize)+pageSize),totalPages:totalPages,currentPage:validPage};
}

/* ════════════════════════════════════════════════════
   ADMINISTRACIÓN DE TIPOS
════════════════════════════════════════════════════ */
let editTipoId=null;

function renderTipos(){
  const srch=$('srchTipo').value||'';
  let filtered=searchMultiField(TIPOS,srch,SEARCH_FIELDS.tipos);
  filtered=applyAdvancedFilters('tipos',filtered);
  
  $('tiposCount').textContent=`${filtered.length} tipo${filtered.length!==1?'s':''}`;
  
  const {data:pageData,totalPages,currentPage:cp}=paginateArray(filtered,'tipos');
  
  const tbody=$('tiposTbody');
  if(!filtered.length){
    tbody.innerHTML='<tr><td colspan="5"><div class="empty"><div class="empty-icon">📦</div><h3>Sin tipos</h3></div></td></tr>';
    const wrapper=tbody.parentElement.parentElement;
    const oldPagination=wrapper.querySelector('[data-pagination="tipos"]');
    if(oldPagination) oldPagination.remove();
    return;
  }
  
  tbody.innerHTML=pageData.map(t=>`
    <tr>
      <td>${t.nombre}</td>
      <td>${t.descripcion||'-'}</td>
      <td>${t.serial_prefix?`<span class="mono" style="font-size:12px;font-weight:600;color:var(--blue)">${t.serial_prefix}</span>`:'—'}</td>
      <td>${new Date(t.created_at).toLocaleDateString('es-CO')}</td>
      <td style="text-align:center">
        <button class="btn btn-sm btn-ghost" onclick="openEditarTipo(${t.id},'${t.nombre.replace(/'/g,"\\'")}')" title="Editar">✏️</button>
        <button class="btn btn-sm btn-ghost" onclick="deleteTipo(${t.id},'${t.nombre.replace(/'/g,"\\'")}')" title="Eliminar">🗑️</button>
      </td>
    </tr>
  `).join('');
  
  if(totalPages>1){
    const wrapper=tbody.parentElement.parentElement;
    let paginationContainer=wrapper.querySelector('[data-pagination="tipos"]');
    if(!paginationContainer){
      paginationContainer=document.createElement('div');
      paginationContainer.setAttribute('data-pagination','tipos');
      paginationContainer.className='pagination-wrap';
      wrapper.appendChild(paginationContainer);
    }
    paginationContainer.innerHTML=createPaginationControls(cp,totalPages,'tipos');
  }else{
    const wrapper=tbody.parentElement.parentElement;
    const paginationContainer=wrapper.querySelector('[data-pagination="tipos"]');
    if(paginationContainer) paginationContainer.remove();
  }
}

function openTipoModal(){
  editTipoId=null;
  $('newTipoNombre').value='';
  $('newTipoDesc').value='';
  $('newTipoPrefix').value='';
  open('ovAgregarTipo');
}

function openEditarTipo(id,nombre){
  editTipoId=id;
  $('editTipoNombre').value=nombre;
  const tipo=TIPOS.find(t=>t.id===id);
  $('editTipoDesc').value=tipo?.descripcion||'';
  $('editTipoPrefix').value=tipo?.serial_prefix||'';
  open('ovEditarTipo');
}

async function saveEditarTipo(){
  const nombre=$('editTipoNombre').value.trim();
  const descripcion=$('editTipoDesc').value.trim();
  
  if(!nombre){toast('El nombre no puede estar vacío','err');return;}
  
  try {
    const serial_prefix=$('editTipoPrefix').value||null;
    const res=await api(`/api/tipos-equipos/${editTipoId}`,'PUT',{nombre,descripcion,serial_prefix});

    // Si hay error explícito, mostrar
    if(res.error){
      toast(res.error,'err');
      return;
    }

    // Actualizar array local (usar respuesta o al menos actualizar propiedades básicas)
    const idx=TIPOS.findIndex(t=>t.id===editTipoId);
    if(idx>=0){
      TIPOS[idx]={
        ...TIPOS[idx],
        id: res.id || editTipoId,
        nombre: res.nombre || nombre,
        descripcion: res.descripcion !== undefined ? res.descripcion : descripcion,
        serial_prefix: res.serial_prefix !== undefined ? res.serial_prefix : serial_prefix
      };
    }
    
    TIPOS.sort((a,b)=>a.nombre.localeCompare(b.nombre));
    await _refreshEq();DASH=computeDash();
    renderTipos();
    updateTiposInModal();
    close('ovEditarTipo');
    toast(`Tipo "${nombre}" actualizado correctamente ✅`,'ok');
    editTipoId=null;
  } catch(e) {
    toast('Error al actualizar tipo: '+e.message,'err');
  }
}

async function deleteTipo(id,nombre){
  if(!confirm(`¿Eliminar tipo "${nombre}"? Esta acción no se puede deshacer.`))return;
  
  const res=await api(`/api/tipos-equipos/${id}`,'DELETE');
  
  if(res.ok){
    TIPOS=TIPOS.filter(t=>t.id!==id);
    await _refreshEq();DASH=computeDash();
    renderTipos();
    updateTiposInModal();
    toast(`Tipo "${nombre}" eliminado`,'info');
  }else{
    toast('Error al eliminar el tipo','err');
  }
}

/* ════════════════════════════════════════════════════
   ADMINISTRACIÓN DE ROLES
════════════════════════════════════════════════════ */
let editRolId=null;

function renderRoles(){
  const srch=$('srchRol').value||'';
  let filtered=searchMultiField(ROLES,srch,SEARCH_FIELDS.roles);
  filtered=applyAdvancedFilters('roles',filtered);
  
  $('rolesCount').textContent=`${filtered.length} rol${filtered.length!==1?'es':''}`;
  
  const {data:pageData,totalPages,currentPage:cp}=paginateArray(filtered,'roles');
  
  const deptColors={'Finanzas':'#4f8ef7','Plataformas':'#2dd4bf','Producción':'#a78bfa','Academia':'#fbbf24','Contenido':'#f87171','Gerencia':'#34d399'};
  
  const tbody=$('rolesTbody');
  if(!filtered.length){
    tbody.innerHTML='<tr><td colspan="5"><div class="empty"><div class="empty-icon">🔐</div><h3>Sin roles</h3></div></td></tr>';
    const wrapper=tbody.parentElement.parentElement;
    const oldPagination=wrapper.querySelector('[data-pagination="roles"]');
    if(oldPagination) oldPagination.remove();
    return;
  }
  
  tbody.innerHTML=pageData.map(r=>{
    const deptColor=deptColors[r.departamento]||'#6b7280';
    return `
      <tr>
        <td data-label="Nombre"><strong>${r.nombre}</strong></td>
        <td data-label="Descripción">${r.descripcion||'-'}</td>
        <td data-label="Departamento"><span style="font-size:11px;background:${deptColor}20;color:${deptColor};padding:4px 10px;border-radius:6px;display:inline-block;font-weight:600">${r.departamento||'Sin asignar'}</span></td>
        <td data-label="Creado">${new Date(r.created_at).toLocaleDateString('es-CO')}</td>
        <td data-label="Acciones" style="text-align:center">
          <button class="btn btn-sm btn-ghost" onclick="openEditarRol(${r.id},'${r.nombre.replace(/'/g,"\\'")}')" title="Editar">✏️</button>
          <button class="btn btn-sm btn-ghost" onclick="deleteRol(${r.id},'${r.nombre.replace(/'/g,"\\'")}')" title="Eliminar" ${['Administrador','Usuario'].includes(r.nombre)?'disabled title="No puedes eliminar roles del sistema"':''}>🗑️</button>
        </td>
      </tr>
    `;
  }).join('');
  
  if(totalPages>1){
    const wrapper=tbody.parentElement.parentElement;
    let paginationContainer=wrapper.querySelector('[data-pagination="roles"]');
    if(!paginationContainer){
      paginationContainer=document.createElement('div');
      paginationContainer.setAttribute('data-pagination','roles');
      paginationContainer.className='pagination-wrap';
      wrapper.appendChild(paginationContainer);
    }
    paginationContainer.innerHTML=createPaginationControls(cp,totalPages,'roles');
  }else{
    const wrapper=tbody.parentElement.parentElement;
    const paginationContainer=wrapper.querySelector('[data-pagination="roles"]');
    if(paginationContainer) paginationContainer.remove();
  }
}

function openRolModal(){
  editRolId=null;
  $('rolModalTitle').textContent='Nuevo rol';
  $('rolNombre').value='';
  $('rolDpto').value='';
  $('rolDesc').value='';
  open('ovTipoRol');
}

function openEditarRol(id,nombre){
  editRolId=id;
  const rol=ROLES.find(r=>r.id===id);
  $('rolModalTitle').textContent='Editar rol';
  $('rolNombre').value=nombre;
  $('rolDpto').value=rol?.departamento||'Gerencia';
  $('rolDesc').value=rol?.descripcion||'';
  open('ovTipoRol');
}

async function saveRol(){
  const nombre=$('rolNombre').value.trim();
  const departamento=$('rolDpto').value;
  const descripcion=$('rolDesc').value.trim();
  
  if(!nombre){toast('El nombre del rol no puede estar vacío','err');return;}
  if(!departamento){toast('El departamento es requerido','err');return;}
  
  const method=editRolId?'PUT':'POST';
  const endpoint=editRolId?`/api/roles/${editRolId}`:'/api/roles';
  
  try {
    const res=await api(endpoint,method,{nombre,descripcion,departamento});
    
    // Si hay error explícito, mostrar
    if(res.error){
      toast(res.error,'err');
      return;
    }
    
    // Actualizar array local
    if(editRolId){
      const idx=ROLES.findIndex(r=>r.id===editRolId);
      if(idx>=0){
        ROLES[idx]={
          ...ROLES[idx],
          id: res.id || editRolId,
          nombre: res.nombre || nombre,
          descripcion: res.descripcion !== undefined ? res.descripcion : descripcion,
          departamento: res.departamento || departamento
        };
      }
    }else{
      ROLES.push({
        id: res.id,
        nombre: res.nombre || nombre,
        descripcion: res.descripcion || descripcion,
        departamento: res.departamento || departamento
      });
    }
    
    ROLES.sort((a,b)=>a.nombre.localeCompare(b.nombre));
    renderRoles();
    close('ovTipoRol');
    toast(editRolId?'Rol actualizado correctamente ✅':'Rol creado correctamente ✅','ok');
    editRolId=null;
  } catch(e) {
    toast('Error al guardar rol: '+e.message,'err');
  }
}

async function deleteRol(id,nombre){
  if(!confirm(`¿Eliminar rol "${nombre}"? Esta acción no se puede deshacer.`))return;
  
  const res=await api(`/api/roles/${id}`,'DELETE');
  
  if(res.ok){
    ROLES=ROLES.filter(r=>r.id!==id);
    renderRoles();
    toast(`Rol "${nombre}" eliminado`,'info');
  }else{
    toast('Error al eliminar el rol','err');
  }
}

/* ════════════════════════════════════════════════════
   MANTENIMIENTOS
════════════════════════════════════════════════════ */
function clearEqFilters(){
  $('srchEq').value='';
  $('ftTipo').value='';
  $('ftEst').value='';
  $('ftEqDisp').value='';
  $('ftSerial').value='';
  $('ftDueno').value='';
  currentPage['eq']=1;
  renderEq();
}

function updateMantEquiposSelect(){
  const sel=$('ftMantEquipo');
  if(!sel) return;
  const current=sel.value;
  const equipos=[...new Map(MANTS.filter(m=>m.equipo_id).map(m=>[m.equipo_id,{id:m.equipo_id,nombre:m.equipo_nombre}])).values()]
    .sort((a,b)=>a.nombre.localeCompare(b.nombre));
  sel.innerHTML='<option value="">Todos los equipos</option>';
  equipos.forEach(e=>{
    const opt=document.createElement('option');
    opt.value=e.id;
    opt.textContent=e.nombre;
    sel.appendChild(opt);
  });
  sel.value=current;
}

function clearMantFilters(){
  $('srchMant').value='';
  $('ftMantEquipo').value='';
  $('ftMantTipo').value='';
  $('ftMantEst').value='';
  currentPage['mant']=1;
  renderMant();
}

function renderMant(){
  const q=($('srchMant')?.value||'');
  const equipo=$('ftMantEquipo')?.value||'';
  const tipo=$('ftMantTipo')?.value||'';
  const est=$('ftMantEst')?.value||'';

  let rows=searchMultiField(MANTS,q,SEARCH_FIELDS.mant);

  rows=rows.filter(m=>
    (!equipo||String(m.equipo_id)===equipo)&&
    (!tipo||m.tipo===tipo)&&
    (!est||m.estado===est));
  
  // Aplicar filtros avanzados anidables
  rows=applyAdvancedFilters('mant',rows);
  
  $('mantCount').textContent=`${rows.length} de ${MANTS.length} registro(s)`;
  
  // Paginación
  const {data:pageData,totalPages,currentPage:cp}=paginateArray(rows,'mant');
  
  const tb=$('mantTbody');
  if(!rows.length){
    tb.innerHTML=`<tr><td colspan="9"><div class="empty"><div class="empty-icon">🔧</div><h3>Sin registros</h3><p>Agrega mantenimientos desde aquí o desde la hoja de vida</p></div></td></tr>`;
    const wrapper=tb.parentElement.parentElement;
    const oldPagination=wrapper.querySelector('[data-pagination="mant"]');
    if(oldPagination) oldPagination.remove();
    return;
  }
  tb.innerHTML=pageData.map(m=>{
    const overdue=m.proxima_revision&&m.proxima_revision<TODAY&&m.estado==='completado';
    return`<tr>
      <td data-label="Equipo"><div class="av-cell">
        <div class="tipo-av">${TIPO_ICON[m.equipo_tipo]||'📦'}</div>
        <div class="name">${m.equipo_nombre}</div>
      </div></td>
      <td data-label="Tipo"><span class="bs ${bsClass(m.tipo)}">${bsLabel(m.tipo)}</span></td>
      <td data-label="Descripción" style="max-width:180px;font-size:12px;color:var(--text2)">${(m.descripcion||'').slice(0,70)}${(m.descripcion||'').length>70?'…':''}</td>
      <td data-label="Fecha" class="mono">${fmtDate(m.fecha)}</td>
      <td data-label="Técnico" style="color:var(--text3)">${m.tecnico||'—'}</td>
      <td data-label="Costo" class="mono">${m.costo?fmt(m.costo):'—'}</td>
      <td data-label="Estado"><span class="bs ${bsClass(m.estado)}">${bsLabel(m.estado)}</span></td>
      <td data-label="Próx. Revisión" class="mono" style="color:${overdue?'var(--red)':'var(--text3)'}">${fmtDate(m.proxima_revision)}${overdue?' ⚠':''}</td>
      <td data-label="Acciones"><div class="act-cell">
        <button class="btn btn-ghost btn-icon btn-sm" onclick="editMant(${m.id})">✏️</button>
        <button class="btn btn-danger btn-icon btn-sm" onclick="delMant(${m.id})">🗑️</button>
      </div></td>
    </tr>`;}).join('');
  
  // Agregar/actualizar controles de paginación si hay múltiples páginas
  if(totalPages>1){
    const wrapper=tb.parentElement.parentElement;
    let paginationContainer=wrapper.querySelector('[data-pagination="mant"]');
    if(!paginationContainer){
      paginationContainer=document.createElement('div');
      paginationContainer.setAttribute('data-pagination','mant');
      paginationContainer.className='pagination-wrap';
      wrapper.appendChild(paginationContainer);
    }
    paginationContainer.innerHTML=createPaginationControls(cp,totalPages,'mant');
  }else{
    const wrapper=tb.parentElement.parentElement;
    const paginationContainer=wrapper.querySelector('[data-pagination="mant"]');
    if(paginationContainer) paginationContainer.remove();
  }
}

function openMantModal(equipoId=null){
  editMantId=null;
  $('mantModalTitle').textContent='Nuevo mantenimiento';
  $('mantModalSub').textContent='Registrar mantenimiento vinculado al equipo';
  ['mDesc','mTec','mCosto','mProx'].forEach(id=>$(id).value='');
  $('mTipo').value='preventivo';$('mEst').value='completado';$('mFecha').value=TODAY;
  // Populate equipo select
  const sel=$('mEquipo');
  sel.innerHTML='<option value="">Seleccionar equipo…</option>'+EQ.map(e=>`<option value="${e.id}">${e.nombre} (${e.tipo_nombre||e.tipo})</option>`).join('');
  if(equipoId)sel.value=equipoId;
  open('ovMant');
}
function editMant(id){
  const m=MANTS.find(x=>x.id===id);if(!m)return;
  editMantId=id;$('mantModalTitle').textContent='Editar mantenimiento';$('mantModalSub').textContent=m.equipo_nombre;
  const sel=$('mEquipo');
  sel.innerHTML='<option value="">Seleccionar equipo…</option>'+EQ.map(e=>`<option value="${e.id}">${e.nombre} (${e.tipo_nombre||e.tipo})</option>`).join('');
  sel.value=m.equipo_id;$('mTipo').value=m.tipo;$('mEst').value=m.estado;
  $('mDesc').value=m.descripcion;$('mFecha').value=m.fecha;$('mTec').value=m.tecnico||'';
  $('mCosto').value=m.costo||'';$('mProx').value=m.proxima_revision||'';
  open('ovMant');
}
async function saveMant(){
  // Prevenir múltiples clics
  if(isSubmitting){
    toast('Por favor espera a que termine el proceso','info');
    return;
  }
  
  const data={equipo_id:parseInt($('mEquipo').value),tipo:$('mTipo').value,descripcion:$('mDesc').value.trim(),
    fecha:$('mFecha').value,tecnico:$('mTec').value,costo:parseFloat($('mCosto').value)||0,
    estado:$('mEst').value,proxima_revision:$('mProx').value||null};
  if(!data.equipo_id||!data.descripcion||!data.fecha){toast('Equipo, descripción y fecha son requeridos','err');return}
  
  // Establecer flag y deshabilitar botón
  isSubmitting=true;
  const btn=$('saveMantBtn');
  btn.disabled=true;
  const btnText=editMantId?'Actualizando...':'Registrando...';
  btn.textContent=btnText;
  
  try{
    const res=editMantId?await api('/api/mantenimientos/'+editMantId,'PUT',data):await api('/api/mantenimientos','POST',data);
    if(res.error){toast(res.error,'err');throw new Error(res.error)}
    close('ovMant');await _refreshMants();DASH=computeDash();renderMant();renderDashboard();
    toast(editMantId?'Mantenimiento actualizado':'Mantenimiento registrado','ok');editMantId=null;
    isSubmitting=false;
    btn.disabled=false;
    btn.textContent='Registrar mantenimiento';
  }catch(e){
    isSubmitting=false;
    btn.disabled=false;
    btn.textContent='Registrar mantenimiento';
  }
}
async function delMant(id){
  if(!confirm('¿Eliminar este mantenimiento?'))return;
  await api('/api/mantenimientos/'+id,'DELETE');await _refreshMants();DASH=computeDash();renderMant();renderDashboard();toast('Mantenimiento eliminado','info');
}

/* ════════════════════════════════════════════════════
   HOJA DE VIDA
════════════════════════════════════════════════════ */
async function openHV(equipoId){
  curHVId=equipoId;
  const e=EQ.find(x=>x.id===equipoId);
  $('hvTitle').textContent=e.nombre;
  $('hvSub').textContent=`${e.tipo_nombre||e.tipo} · ${[e.marca,e.modelo].filter(Boolean).join(' ')} · Serial: ${e.serial||'—'}`;
  $('hvEquipoMeta').innerHTML=`<div class="mant-info-cards">
    <div class="mant-info-card"><div class="mic-label">Estado</div><div class="mic-val"><span class="bs ${bsClass(e.estado)}">${bsLabel(e.estado)}</span></div></div>
    <div class="mant-info-card"><div class="mic-label">Valor</div><div class="mic-val mono">${fmt(e.valor)}</div></div>
    <div class="mant-info-card"><div class="mic-label">Adquisición</div><div class="mic-val">${fmtDate(e.fecha_adquisicion)}</div></div>
    <div class="mant-info-card"><div class="mic-label">Ubicación</div><div class="mic-val">${e.ubicacion||'—'}</div></div>
  </div>`;
  renderFacturaPreview(e.factura_url);
  $('hvFacturaInput').value='';
  _hvMantsOpen=true;
  await refreshHV();
  open('ovHV');
}
function renderFacturaPreview(url){
  const div=$('hvFacturaPreview');
  if(!url){div.innerHTML='<div style="font-size:12px;color:var(--text3);padding:6px 0">Sin factura adjunta</div>';return;}
  const isPdf=url.toLowerCase().includes('.pdf');
  const deleteBtn=`<button class="btn btn-danger btn-sm" style="margin-top:6px" onclick="deleteFactura()">🗑️ Eliminar factura</button>`;
  div.innerHTML=isPdf
    ?`<div style="display:flex;flex-direction:column;align-items:flex-start;gap:6px">
        <a href="${url}" target="_blank" class="btn btn-ghost btn-sm" style="text-decoration:none">📄 Ver factura PDF</a>
        ${deleteBtn}
      </div>`
    :`<div style="display:inline-block">
        <img src="${url}" alt="Factura" style="max-height:120px;max-width:100%;border-radius:8px;border:1px solid var(--border);cursor:pointer" onclick="window.open('${url}','_blank')">
        <div style="font-size:11px;color:var(--text3);margin-top:4px">Clic para ver en tamaño completo</div>
        ${deleteBtn}
      </div>`;
}
async function deleteFactura(){
  if(!confirm('¿Eliminar la factura adjunta? Esta acción no se puede deshacer.'))return;
  const r=await api('/api/equipos/'+curHVId+'/factura','DELETE');
  if(r.error){toast('Error: '+r.error,'err');return;}
  const eq=EQ.find(x=>x.id===curHVId);
  if(eq) eq.factura_url=null;
  renderFacturaPreview(null);
  toast('Factura eliminada','info');
}
async function uploadFactura(input){
  const file=input.files[0];
  if(!file)return;
  if(file.size>10*1024*1024){toast('Archivo muy grande (máx 10MB)','err');return;}
  const ext=file.name.split('.').pop().toLowerCase();
  const reader=new FileReader();
  reader.onload=async ev=>{
    const b64=ev.target.result.split(',')[1];
    toast('Subiendo factura…','info');
    const r=await api('/api/equipos/'+curHVId+'/factura','POST',{img:b64,ext});
    if(r.error){toast('Error: '+r.error,'err');return;}
    const eq=EQ.find(x=>x.id===curHVId);
    if(eq) eq.factura_url=r.url;
    renderFacturaPreview(r.url);
    toast('Factura guardada','ok');
  };
  reader.readAsDataURL(file);
}
let _hvMantsOpen=true;
function toggleHvMants(){
  _hvMantsOpen=!_hvMantsOpen;
  const el=$('hvMants');
  const tog=$('hvMantsToggle');
  el.style.display=_hvMantsOpen?'':'none';
  tog.textContent=_hvMantsOpen?'▼':'▶';
}
async function refreshHV(){
  const [hvs,mants]=await Promise.all([api('/api/equipos/'+curHVId+'/hoja_vida'),api('/api/equipos/'+curHVId+'/mantenimientos')]);
  // Mants section
  const hmDiv=$('hvMants');
  if(!mants.length){hmDiv.innerHTML='<div class="empty" style="padding:20px"><div class="empty-icon">🔧</div><h3>Sin mantenimientos registrados</h3></div>'}
  else{hmDiv.innerHTML='<div style="display:flex;flex-direction:column;gap:8px">'+mants.map(m=>`
    <div style="background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius-sm);padding:12px 14px;display:flex;align-items:flex-start;gap:12px">
      <div style="font-size:20px">${m.tipo==='preventivo'?'🛡️':'🔧'}</div>
      <div style="flex:1;min-width:0">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
          <span class="bs ${bsClass(m.tipo)}">${bsLabel(m.tipo)}</span>
          <span class="bs ${bsClass(m.estado)}">${bsLabel(m.estado)}</span>
        </div>
        <div style="font-size:13px;font-weight:600;color:var(--text)">${m.descripcion}</div>
        <div class="hv-meta">
          <span>📅 ${fmtDate(m.fecha)}</span>
          ${m.tecnico?`<span>👤 ${m.tecnico}</span>`:''}
          ${m.costo?`<span>💰 ${fmt(m.costo)}</span>`:''}
          ${m.proxima_revision?`<span style="color:${m.proxima_revision<TODAY?'var(--red)':'var(--teal)'}">🔄 Próx: ${fmtDate(m.proxima_revision)}</span>`:''}
        </div>
      </div>
      <button class="btn btn-danger btn-icon btn-sm" onclick="delMantFromHV(${m.id})">🗑️</button>
    </div>`).join('')+'</div>'}
  // Timeline
  const tlDiv=$('hvTimeline');
  const hvIcons={adquisicion:'🟢',mantenimiento:'🟡',reparacion:'🔴',proceso:'🔵',otro:'⚪'};
  if(!hvs.length){tlDiv.innerHTML='<div class="empty" style="padding:20px"><div class="empty-icon">📋</div><h3>Sin eventos registrados</h3></div>'}
  else{tlDiv.innerHTML='<div class="hv-tl">'+hvs.map(h=>`
    <div class="hv-item hv-${h.tipo}">
      <div class="hv-card">
        <div class="hv-card-top">
          <div>
            <h4>${hvIcons[h.tipo]||'⚪'} ${h.titulo}</h4>
            ${h.descripcion?`<p>${h.descripcion}</p>`:''}
          </div>
          <div style="display:flex;align-items:center;gap:6px;flex-shrink:0">
            <span class="bs ${bsClass(h.tipo)} bs-xs">${bsLabel(h.tipo)}</span>
            <button class="btn btn-danger btn-icon btn-sm" onclick="delHV(${h.id})">🗑️</button>
          </div>
        </div>
        <div class="hv-meta">
          <span>📅 ${fmtDate(h.fecha)}</span>
          ${h.responsable?`<span>👤 ${h.responsable}</span>`:''}
        </div>
      </div>
    </div>`).join('')+'</div>'}
}
function openMantFromHV(){
  close('ovHV');
  openMantModal(curHVId);
  // Hook: on save, also refresh HV
  const origSave=window._mantSaveHook;
  window._mantSaveHook=async()=>{await refreshHV();open('ovHV')};
}
async function delMantFromHV(id){
  if(!confirm('¿Eliminar este mantenimiento?'))return;
  await api('/api/mantenimientos/'+id,'DELETE');await _refreshMants();DASH=computeDash();await refreshHV();renderDashboard();toast('Mantenimiento eliminado','info');
}
async function delHV(id){
  if(!confirm('¿Eliminar este evento?'))return;
  await api('/api/hoja_vida/'+id,'DELETE');await refreshHV();toast('Evento eliminado','info');
}
function open_ovAddHV(){$('hvFechaEv').value=TODAY;open('ovAddHV')}
async function saveHVEvent(){
  const data={tipo:$('hvTipo').value,titulo:$('hvTit').value.trim(),descripcion:$('hvDescEv').value,fecha:$('hvFechaEv').value,responsable:$('hvResp').value};
  if(!data.titulo||!data.fecha){toast('Título y fecha requeridos','err');return}
  await api('/api/equipos/'+curHVId+'/hoja_vida','POST',data);
  close('ovAddHV');['hvTit','hvDescEv','hvResp'].forEach(id=>$(id).value='');
  await refreshHV();toast('Evento registrado','ok');
}

/* ════════════════════════════════════════════════════
   USUARIOS
════════════════════════════════════════════════════ */
function updateDptosSelect(){
  const dptos=[...new Set(USR.map(u=>u.departamento).filter(d=>d))].sort();
  const sel=$('ftUsrDpto');
  const current=sel.value;
  sel.innerHTML='<option value="">Todos los departamentos</option>';
  dptos.forEach(d=>{
    const opt=document.createElement('option');
    opt.value=d;
    opt.textContent=d;
    sel.appendChild(opt);
  });
  sel.value=current;
}
function clearUsrFilters(){
  $('srchUsr').value='';
  $('ftUsrDpto').value='';
  $('ftUsrEst').value='';
  currentPage['usu']=1;
  renderUsr();
}
function renderUsr(){
  const q=($('srchUsr')?.value||'');
  const dpto=$('ftUsrDpto')?.value||'';
  const est=$('ftUsrEst')?.value||'';
  
  // Búsqueda multi-campo en: nombre, email, departamento, telefono
  let rows=searchMultiField(USR,q,SEARCH_FIELDS.usu);
  
  // Aplicar filtros específicos
  rows=rows.filter(u=>(!dpto||u.departamento===dpto)&&(!est||u.estado===est));
  
  // Aplicar filtros avanzados anidables
  rows=applyAdvancedFilters('usu',rows);
  
  $('usrCount').textContent=`${rows.length} de ${USR.length} usuario(s)`;
  
  // Paginación
  const {data:pageData,totalPages,currentPage:cp}=paginateArray(rows,'usu');
  
  const tb=$('usrTbody');
  if(!rows.length){
    tb.innerHTML=`<tr><td colspan="8"><div class="empty"><div class="empty-icon">👥</div><h3>Sin resultados</h3></div></td></tr>`;
    const wrapper=tb.parentElement.parentElement;
    const oldPagination=wrapper.querySelector('[data-pagination="usu"]');
    if(oldPagination) oldPagination.remove();
    return;
  }
  tb.innerHTML=pageData.map((u,i)=>{
    const rol=ROLES.find(r=>r.id===u.rol_id);
    return `<tr>
      <td data-label="Nombre"><div class="av-cell">
        <div class="av" style="background:${AV_COLORS[i%AV_COLORS.length]}">${(u.nombre||'?').charAt(0)}</div>
        <div class="name">${u.nombre}</div>
      </div></td>
      <td data-label="Email" style="color:var(--text3)">${u.email}</td>
      <td data-label="Notif.Email" style="color:var(--text3);font-size:13px">${u.notification_email||'—'}</td>
      <td data-label="Cargo"><span style="font-size:11px;background:var(--blue-soft);color:var(--blue);padding:4px 8px;border-radius:6px;display:inline-block">${rol?.nombre||'—'}</span></td>
      <td data-label="Departamento">${u.departamento||'—'}</td>
      <td data-label="Teléfono" class="mono">${u.telefono||'—'}</td>
      <td data-label="Estado"><span class="bs ${bsClass(u.estado)}">${bsLabel(u.estado)}</span></td>
      <td data-label="Acciones"><div class="act-cell">
        <button class="btn btn-ghost btn-icon btn-sm" onclick="editUsr(${u.id})">✏️</button>
        <button class="btn btn-danger btn-icon btn-sm" onclick="delUsr(${u.id})">🗑️</button>
      </div></td>
    </tr>`;
  }).join('');
  
  // Agregar/actualizar controles de paginación si hay múltiples páginas
  if(totalPages>1){
    const wrapper=tb.parentElement.parentElement;
    let paginationContainer=wrapper.querySelector('[data-pagination="usu"]');
    if(!paginationContainer){
      paginationContainer=document.createElement('div');
      paginationContainer.setAttribute('data-pagination','usu');
      paginationContainer.className='pagination-wrap';
      wrapper.appendChild(paginationContainer);
    }
    paginationContainer.innerHTML=createPaginationControls(cp,totalPages,'usu');
  }else{
    const wrapper=tb.parentElement.parentElement;
    const paginationContainer=wrapper.querySelector('[data-pagination="usu"]');
    if(paginationContainer) paginationContainer.remove();
  }
}
function openUsrModal(){
  editUsrId=null;
  $('usrModalTitle').textContent='Nuevo responsable';
  
  // Limpiar TODOS los campos explícitamente
  const uNom = $('uNom');
  const uEmail = $('uEmail');
  const uPass = $('uPass');
  const uDpto = $('uDpto');
  const uTel = $('uTel');
  
  if(uNom) uNom.value='';
  if(uEmail) uEmail.value='';
  if(uPass) uPass.value='';
  if(uDpto) uDpto.value='';
  if(uTel) uTel.value='';
  const uNotifEmail=$('uNotifEmail');
  if(uNotifEmail) uNotifEmail.value='';
  
  $('uPassLabel').textContent='Contraseña * (min. 6 caracteres)';
  $('uPass').required=true;
  $('uEst').value='activo';
  $('uRol').value='';
  
  // Llenar select de roles
  const rolSel=$('uRol');
  rolSel.innerHTML='<option value="">Seleccionar cargo…</option>';
  ROLES.forEach(r=>{
    const opt=document.createElement('option');
    opt.value=r.id;
    opt.textContent=r.nombre;
    rolSel.appendChild(opt);
  });
  
  open('ovUsr');
}

function editUsr(id){
  const u=USR.find(x=>x.id===id);
  if(!u)return;
  editUsrId=id;
  $('usrModalTitle').textContent='Editar responsable';
  $('uNom').value=u.nombre;
  $('uEmail').value=u.email;
  $('uPass').value='';  // Empty password field - only update if provided
  $('uPassLabel').textContent='Contraseña (dejar vacío para no cambiar)';
  $('uPass').required=false;
  $('uDpto').value=u.departamento||'';
  $('uTel').value=u.telefono||'';
  $('uNotifEmail').value=u.notification_email||'';
  $('uEst').value=u.estado;
  
  // Llenar y seleccionar cargo
  const rolSel=$('uRol');
  rolSel.innerHTML='<option value="">Seleccionar cargo…</option>';
  ROLES.forEach(r=>{
    const opt=document.createElement('option');
    opt.value=r.id;
    opt.textContent=r.nombre;
    if(u.rol_id===r.id)opt.selected=true;
    rolSel.appendChild(opt);
  });
  
  // Actualizar departamento según rol seleccionado
  updateDptoFromRol();
  
  open('ovUsr');
}
function updateDptoFromRol(){
  const rolId=parseInt($('uRol').value);
  if(!rolId){$('uDpto').value='';return;}
  const rol=ROLES.find(r=>r.id===rolId);
  $('uDpto').value=rol?.departamento||'';
}

async function saveUsr(){
  if(isSubmitting) return;
  
  const emailInput = document.getElementById('uEmail');
  
  const nombre = document.getElementById('uNom')?.value.trim() || '';
  const email = document.getElementById('uEmail')?.value.trim() || '';
  const password = document.getElementById('uPass')?.value.trim() || '';
  const rolId = parseInt(document.getElementById('uRol')?.value || '0');
  const selectedRol = ROLES.find(r=>r.id===rolId);
  const departamento = selectedRol?.departamento || '';
  
  // Validaciones
  if(!nombre) { toast('❌ Falta: Nombre completo','err'); return; }
  if(!email) { toast('❌ Falta: Email','err'); return; }
  if(!editUsrId && !password) { toast('❌ Falta: Contraseña (mín 6 caracteres)','err'); return; }
  if(!rolId) { toast('❌ Falta: Cargo','err'); return; }
  if(!departamento) { toast('❌ El cargo no tiene departamento','err'); return; }
  
  const data = {
    nombre, email, password,
    departamento,
    telefono: document.getElementById('uTel')?.value.trim() || '',
    notification_email: document.getElementById('uNotifEmail')?.value.trim() || '',
    estado: document.getElementById('uEst')?.value || 'activo',
    rol_id: rolId
  };
  
  isSubmitting = true;
  const btn = document.getElementById('saveUsrBtn');
  btn.disabled = true;
  btn.textContent = editUsrId ? 'Actualizando...' : 'Guardando...';
  
  try {
    const res = editUsrId ? 
      await api('/api/usuarios/'+editUsrId, 'PUT', data) :
      await api('/api/usuarios', 'POST', data);
    
    if(res.error) {
      toast('❌ ' + res.error, 'err');
    } else {
      close('ovUsr');
      await _refreshUsr();DASH=computeDash();
      renderUsr();
      renderDashboard();
      toast(editUsrId ? '✅ Usuario actualizado' : '✅ Usuario creado', 'ok');
      editUsrId = null;
    }
  } catch(e) {
    toast('❌ Error: ' + e.message, 'err');
  } finally {
    isSubmitting = false;
    btn.disabled = false;
    btn.textContent = 'Guardar';
  }
}

async function delUsr(id){
  if(!confirm('¿Eliminar este responsable?'))return;
  await api('/api/usuarios/'+id,'DELETE');await _refreshUsr();DASH=computeDash();renderUsr();renderDashboard();toast('Usuario eliminado','info');
}

/* ════════════════════════════════════════════════════
   LICENCIAS
════════════════════════════════════════════════════ */
function updateLicenseProveedoresSelect(){
  const sel=$('ftLicenseProveedor');
  if(!sel) return;
  const current=sel.value;
  const proveedores=[...new Set(LICENCIAS.map(l=>l.proveedor).filter(Boolean))].sort();
  sel.innerHTML='<option value="">Todos los proveedores</option>';
  proveedores.forEach(p=>{
    const opt=document.createElement('option');
    opt.value=p;
    opt.textContent=p;
    sel.appendChild(opt);
  });
  sel.value=current;
}

function clearLicenseFilters(){
  $('srchLicense').value='';
  $('ftLicenseTipo').value='';
  $('ftLicenseProveedor').value='';
  $('ftLicenseEst').value='';
  currentPage['license']=1;
  renderLicenses();
}

function renderLicenses(){
  const q=($('srchLicense')?.value||'');
  const tipo=$('ftLicenseTipo')?.value||'';
  const proveedor=$('ftLicenseProveedor')?.value||'';
  const est=$('ftLicenseEst')?.value||'';

  let rows=searchMultiField(LICENCIAS,q,SEARCH_FIELDS.license);

  rows=rows.filter(l=>(!tipo||l.tipo===tipo)&&(!proveedor||l.proveedor===proveedor)&&(!est||l.estado===est));
  
  // Aplicar filtros avanzados anidables
  rows=applyAdvancedFilters('license',rows);
  
  $('licenseCount').textContent=`${rows.length} de ${LICENCIAS.length} licencia(s)`;
  
  // Paginación
  const {data:pageData,totalPages,currentPage:cp}=paginateArray(rows,'license');
  
  const tb=$('licenseTbody');
  if(!rows.length){
    tb.innerHTML=`<tr><td colspan="8"><div class="empty"><div class="empty-icon">📜</div><h3>Sin licencias</h3></div></td></tr>`;
    // Limpiar pagination
    const wrapper=tb.parentElement.parentElement;
    const oldPagination=wrapper.querySelector('[data-pagination="license"]');
    if(oldPagination) oldPagination.remove();
    return;
  }
  
  tb.innerHTML=pageData.map(l=>{
    const hoy=TODAY;
    const vencida=l.fecha_caducidad<hoy&&l.estado!=='inactiva';
    const porvencer=l.fecha_caducidad>=hoy&&l.fecha_caducidad<=new Date(new Date().setDate(new Date().getDate()+30)).toISOString().split('T')[0]&&l.estado!=='inactiva';
    return`<tr style="${vencida?'background:rgba(248,113,113,.04)':porvencer?'background:rgba(251,191,36,.04)':''}">
      <td data-label="Nombre"><strong>${l.nombre}</strong></td>
      <td data-label="Tipo"><span style="font-size:12px;background:var(--blue-soft);color:var(--blue);padding:4px 8px;border-radius:4px;display:inline-block">${l.tipo}</span></td>
      <td data-label="Inicio" class="mono">${fmtDate(l.fecha_inicio)}</td>
      <td data-label="Caducidad" class="mono" style="color:${vencida?'var(--red)':porvencer?'var(--amber)':'var(--text3)'}">
        ${fmtDate(l.fecha_caducidad)}
        ${vencida?'<div style="font-size:10px;color:var(--red);font-weight:700">VENCIDA</div>':''}
        ${porvencer?'<div style="font-size:10px;color:var(--amber);font-weight:700">Por vencer</div>':''}
      </td>
      <td data-label="Proveedor">${l.proveedor||'—'}</td>
      <td data-label="Costo" class="mono">${l.costo?fmt(l.costo):'—'}</td>
      <td data-label="Estado"><span class="bs ${bsClass(l.estado)}">${bsLabel(l.estado)}</span></td>
      <td data-label="Acciones"><div class="act-cell">
        <button class="btn btn-warning btn-sm" onclick="openLicenseModal(${l.id})">✏️ Editar</button>
        <button class="btn btn-danger btn-icon btn-sm" onclick="delLicense(${l.id})">🗑️</button>
      </div></td>
    </tr>`;}).join('');
  
  // Agregar/actualizar controles de paginación si hay múltiples páginas
  if(totalPages>1){
    const wrapper=tb.parentElement.parentElement;
    let paginationContainer=wrapper.querySelector('[data-pagination="license"]');
    if(!paginationContainer){
      paginationContainer=document.createElement('div');
      paginationContainer.setAttribute('data-pagination','license');
      paginationContainer.className='pagination-wrap';
      wrapper.appendChild(paginationContainer);
    }
    paginationContainer.innerHTML=createPaginationControls(cp,totalPages,'license');
  }else{
    // Remover pagination si no es necesaria
    const wrapper=tb.parentElement.parentElement;
    const paginationContainer=wrapper.querySelector('[data-pagination="license"]');
    if(paginationContainer) paginationContainer.remove();
  }
}

function openLicenseModal(license_id=null){
  editLicenseId=null;
  if(license_id){
    const lic=LICENCIAS.find(l=>l.id===license_id);
    if(!lic)return;
    editLicenseId=license_id;
    $('licenseModalTitle').textContent='Editar licencia';
    $('licenseModalSub').textContent=lic.nombre;
    $('lName').value=lic.nombre;
    $('lTipo').value=lic.tipo;
    $('lStart').value=lic.fecha_inicio;
    $('lExpiry').value=lic.fecha_caducidad;
    $('lProvider').value=lic.proveedor||'';
    $('lCost').value=lic.costo||'';
    $('lDesc').value=lic.descripcion||'';
    $('lNotes').value=lic.notas||'';
  }else{
    $('licenseModalTitle').textContent='Nueva licencia';
    $('licenseModalSub').textContent='Registrar nueva licencia';
    $('lName').value='';
    $('lTipo').value='Sist. Operativo';
    $('lStart').value=TODAY;
    $('lExpiry').value='';
    $('lProvider').value='';
    $('lCost').value='';
    $('lDesc').value='';
    $('lNotes').value='';
  }
  open('ovLicense');
}

async function saveLicense(){
  if(isSubmitting){
    toast('Por favor espera a que termine el proceso','info');
    return;
  }
  
  const nombre=$('lName').value.trim();
  const tipo=$('lTipo').value;
  const fecha_inicio=$('lStart').value;
  const fecha_caducidad=$('lExpiry').value;
  
  if(!nombre||!tipo||!fecha_inicio||!fecha_caducidad){
    toast('Nombre, tipo y fechas son requeridos','err');
    return;
  }
  
  const data={
    nombre:nombre,
    tipo:tipo,
    fecha_inicio:fecha_inicio,
    fecha_caducidad:fecha_caducidad,
    proveedor:$('lProvider').value||'',
    costo:parseFloat($('lCost').value)||0,
    descripcion:$('lDesc').value||'',
    notas:$('lNotes').value||''
  };
  
  isSubmitting=true;
  const btn=$('saveLicenseBtn');
  btn.disabled=true;
  const btnText=editLicenseId?'Actualizando...':'Registrando...';
  btn.textContent=btnText;
  
  try{
    const res=editLicenseId?await api('/api/licencias/'+editLicenseId,'PUT',data):await api('/api/licencias','POST',data);
    if(res.error){toast(res.error,'err');throw new Error(res.error)}
    close('ovLicense');await _refreshLics();renderLicenses();renderDashboard();
    toast(editLicenseId?'Licencia actualizada':'Licencia registrada','ok');editLicenseId=null;
    isSubmitting=false;
    btn.disabled=false;
    btn.textContent='Registrar licencia';
  }catch(e){
    isSubmitting=false;
    btn.disabled=false;
    btn.textContent='Registrar licencia';
  }
}

async function delLicense(id){
  if(!confirm('¿Eliminar esta licencia?'))return;
  await api('/api/licencias/'+id,'DELETE');await _refreshLics();renderLicenses();renderDashboard();toast('Licencia eliminada','info');
}

/* ════════════════════════════════════════════════════
   APLICATIVOS
════════════════════════════════════════════════════ */
let currentAppId=null;
let currentAppPagos=[];
let editAplicativoId=null;

function clearAplicativoFilters(){
  $('srchAplicativo').value='';
  $('ftAplicativoPeriodicidad').value='';
  $('ftAplicativoEst').value='';
  currentPage['aplicativo']=1;
  renderAplicativos();
}

function renderAplicativos(){
  const q=($('srchAplicativo')?.value||'');
  const periodicidad=$('ftAplicativoPeriodicidad')?.value||'';
  const est=$('ftAplicativoEst')?.value||'';
  
  let rows=searchMultiField(APLICATIVOS,q,SEARCH_FIELDS.aplicativo);
  
  rows=rows.filter(a=>{
    if(periodicidad&&a.periodicidad!==periodicidad)return false;
    if(est){
      const hoy=TODAY;
      const vencido=a.fecha_caducidad<hoy&&a.estado!=='inactivo';
      const porvencer=a.fecha_caducidad>=hoy&&a.fecha_caducidad<=new Date(new Date().setDate(new Date().getDate()+30)).toISOString().split('T')[0]&&a.estado!=='inactivo';
      if(est==='vencido'&&!vencido)return false;
      if(est==='por_vencer'&&!porvencer)return false;
      if(est!=='vencido'&&est!=='por_vencer'&&a.estado!==est)return false;
    }
    return true;
  });
  
  // Aplicar filtros avanzados anidables
  rows=applyAdvancedFilters('aplicativo',rows);
  
  $('aplicativoCount').textContent=`${rows.length} de ${APLICATIVOS.length} aplicativo(s)`;
  
  const {data:pageData,totalPages,currentPage:cp}=paginateArray(rows,'aplicativo');
  
  const tb=$('aplicativoTbody');
  if(!rows.length){
    tb.innerHTML=`<tr><td colspan="7"><div class="empty"><div class="empty-icon">📱</div><h3>Sin aplicativos</h3></div></td></tr>`;
    const wrapper=tb.parentElement.parentElement;
    const oldPagination=wrapper.querySelector('[data-pagination="aplicativo"]');
    if(oldPagination) oldPagination.remove();
    return;
  }
  
  tb.innerHTML=pageData.map(a=>{
    const hoy=TODAY;
    const vencido=a.fecha_caducidad<hoy&&a.estado!=='inactivo';
    const porvencer=a.fecha_caducidad>=hoy&&a.fecha_caducidad<=new Date(new Date().setDate(new Date().getDate()+30)).toISOString().split('T')[0]&&a.estado!=='inactivo';
    return`<tr style="${vencido?'background:rgba(248,113,113,.04)':porvencer?'background:rgba(251,191,36,.04)':''}">
      <td data-label="Nombre"><strong>${a.nombre}</strong></td>
      <td data-label="Próximo Pago" class="mono">${fmtDate(a.fecha_pago)}</td>
      <td data-label="Caducidad" class="mono" style="color:${vencido?'var(--red)':porvencer?'var(--amber)':'var(--text3)'}">
        ${fmtDate(a.fecha_caducidad)}
        ${vencido?'<div style="font-size:10px;color:var(--red);font-weight:700">VENCIDO</div>':''}
        ${porvencer?'<div style="font-size:10px;color:var(--amber);font-weight:700">Por vencer</div>':''}
      </td>
      <td data-label="Periodicidad"><span style="font-size:12px;background:var(--teal-soft);color:var(--teal);padding:4px 8px;border-radius:4px;display:inline-block">${a.periodicidad}</span></td>
      <td data-label="Tarjeta"><span style="font-size:12px;background:var(--violet-soft);color:var(--violet);padding:4px 8px;border-radius:4px;display:inline-block;font-family:var(--mono)">${a.tarjeta?'***'+(a.tarjeta+'').slice(-4):'—'}</span></td>
      <td data-label="Estado"><span class="bs ${bsClass(a.estado)}">${bsLabel(a.estado)}</span></td>
      <td data-label="Acciones"><div class="act-cell">
        <button class="btn btn-secondary btn-sm" onclick="showPagosDetalle(${a.id})">📋 Pagos</button>
        <button class="btn btn-warning btn-sm" onclick="openAplicativoModal(${a.id})">✏️ Editar</button>
        <button class="btn btn-danger btn-icon btn-sm" onclick="delAplicativo(${a.id})">🗑️</button>
      </div></td>
    </tr>`;}).join('');
  
  if(totalPages>1){
    const wrapper=tb.parentElement.parentElement;
    let paginationContainer=wrapper.querySelector('[data-pagination="aplicativo"]');
    if(!paginationContainer){
      paginationContainer=document.createElement('div');
      paginationContainer.setAttribute('data-pagination','aplicativo');
      paginationContainer.className='pagination-wrap';
      wrapper.appendChild(paginationContainer);
    }
    paginationContainer.innerHTML=createPaginationControls(cp,totalPages,'aplicativo');
  }else{
    const wrapper=tb.parentElement.parentElement;
    const paginationContainer=wrapper.querySelector('[data-pagination="aplicativo"]');
    if(paginationContainer) paginationContainer.remove();
  }
}

async function openAplicativoModal(app_id=null){
  editAplicativoId=null;
  currentAppId=app_id;
  currentAppPagos=[];
  
  if(app_id){
    const app=APLICATIVOS.find(a=>a.id===app_id);
    if(!app)return;
    editAplicativoId=app_id;
    $('aplicativoModalTitle').textContent='Editar Aplicativo';
    $('aplicativoModalSub').textContent=app.nombre;
    $('aName').value=app.nombre;
    $('aFechaPago').value=app.fecha_pago;
    $('aFechaCaducidad').value=app.fecha_caducidad||'';
    $('aPeriodicidad').value=app.periodicidad;
    $('aTarjeta').value=app.tarjeta;
    
    // Cargar pagos
    try{
      const pagos=await api(`/api/aplicativos/${app_id}/pagos`);
      currentAppPagos=Array.isArray(pagos)?pagos:[];
      renderAplicativoPagos();
    }catch(e){
      currentAppPagos=[];
    }
  }else{
    $('aplicativoModalTitle').textContent='Nuevo Aplicativo';
    $('aplicativoModalSub').textContent='Registrar nuevo aplicativo';
    $('aName').value='';
    $('aFechaPago').value=TODAY;
    $('aFechaCaducidad').value='';
    $('aPeriodicidad').value='Mensual';
    $('aTarjeta').value='4184';
    currentAppPagos=[];
    renderAplicativoPagos();
  }
  open('ovAplicativo');
}

function renderAplicativoPagos(){
  const container=$('aplicativoPagosContainer');
  if(!currentAppPagos.length){
    container.innerHTML=`<div style="text-align:center;color:var(--text3);padding:20px">No hay pagos registrados</div>`;
    return;
  }
  
  container.innerHTML=`<div style="background:var(--surface2);border-radius:var(--radius-sm);overflow:hidden">
    ${currentAppPagos.map((p,idx)=>`<div style="padding:12px;border-bottom:${idx<currentAppPagos.length-1?'1px solid var(--border)':'none'};display:flex;justify-content:space-between;align-items:center">
      <div>
        <div style="font-size:12px;color:var(--text3)">Pago #${idx+1}</div>
        <div style="font-size:13px;font-weight:600">${fmtDate(p.fecha_pago)} → ${fmtDate(p.fecha_caducidad)}</div>
      </div>
      <button class="btn btn-danger btn-icon btn-sm" onclick="delPago(${p.id})">🗑️</button>
    </div>`).join('')}
  </div>`;
}

async function showPagosDetalle(app_id){
  try{
    const app=APLICATIVOS.find(a=>a.id===app_id);
    if(!app)return;
    
    const pagos=await api(`/api/aplicativos/${app_id}/pagos`);
    const pagosList=Array.isArray(pagos)?pagos:[];
    
    $('pagosDetalleTitle').textContent=`Historial de pagos - ${app.nombre}`;
    const tb=$('pagosDetalleTbody');
    
    if(!pagosList.length){
      tb.innerHTML=`<tr><td colspan="5"><div class="empty" style="padding:30px"><div class="empty-icon">📋</div><h3>Sin pagos registrados</h3></div></td></tr>`;
    }else{
      tb.innerHTML=pagosList.map(p=>`<tr>
        <td data-label="Fecha Pago" class="mono">${fmtDate(p.fecha_pago)}</td>
        <td data-label="Caducidad" class="mono">${fmtDate(p.fecha_caducidad)}</td>
        <td data-label="Monto" class="mono">${p.monto?fmt(p.monto):'—'}</td>
        <td data-label="Método">${p.metodo_pago||'—'}</td>
        <td data-label="Acciones"><button class="btn btn-danger btn-icon btn-sm" onclick="delPago(${p.id});location.reload()">🗑️</button></td>
      </tr>`).join('');
    }
    
    open('ovPagosDetalle');
  }catch(e){
    toast('Error al cargar historial de pagos','err');
  }
}

async function saveAplicativo(){
  if(isSubmitting){
    toast('Por favor espera a que termine el proceso','info');
    return;
  }
  
  const nombre=$('aName').value.trim();
  const fecha_pago=$('aFechaPago').value;
  const fecha_caducidad=$('aFechaCaducidad').value;
  const periodicidad=$('aPeriodicidad').value;
  const tarjeta=$('aTarjeta').value;
  
  if(!nombre||!fecha_pago||!periodicidad||!tarjeta){
    toast('Nombre, fecha de pago, periodicidad y tarjeta son requeridos','err');
    return;
  }
  
  const data={
    nombre:nombre,
    fecha_pago:fecha_pago,
    fecha_caducidad:fecha_caducidad||null,
    periodicidad:periodicidad,
    tarjeta:tarjeta
  };
  
  isSubmitting=true;
  const btn=$('saveAplicativoBtn');
  btn.disabled=true;
  const btnText=editAplicativoId?'Actualizando...':'Registrando...';
  btn.textContent=btnText;
  
  try{
    const res=editAplicativoId?await api('/api/aplicativos/'+editAplicativoId,'PUT',data):await api('/api/aplicativos','POST',data);
    if(res.error){toast(res.error,'err');throw new Error(res.error)}
    close('ovAplicativo');await _refreshApps();renderAplicativos();renderDashboard();
    toast(editAplicativoId?'Aplicativo actualizado':'Aplicativo registrado','ok');editAplicativoId=null;
    isSubmitting=false;
    btn.disabled=false;
    btn.textContent='Registrar Aplicativo';
  }catch(e){
    isSubmitting=false;
    btn.disabled=false;
    btn.textContent='Registrar Aplicativo';
  }
}

async function delAplicativo(id){
  if(!confirm('¿Eliminar este aplicativo?'))return;
  await api('/api/aplicativos/'+id,'DELETE');await _refreshApps();renderAplicativos();renderDashboard();toast('Aplicativo eliminado','info');
}

function addPagoModal(){
  $('pFechaPago').value=TODAY;
  $('pFechaCaducidad').value='';
  $('pMonto').value='';
  open('ovAgregarPago');
}

async function savePago(){
  const fecha_pago=$('pFechaPago').value;
  const fecha_caducidad=$('pFechaCaducidad').value;
  const monto=$('pMonto').value||0;
  
  if(!fecha_pago||!fecha_caducidad){
    toast('Las fechas de pago y caducidad son requeridas','err');
    return;
  }
  
  if(!currentAppId){
    toast('Error: No se seleccionó aplicativo','err');
    return;
  }
  
  const data={
    fecha_pago:fecha_pago,
    fecha_caducidad:fecha_caducidad,
    monto:parseFloat(monto)
  };
  
  try{
    const res=await api(`/api/aplicativos/${currentAppId}/pagos`,'POST',data);
    if(res.error){toast(res.error,'err');throw new Error(res.error)}
    close('ovAgregarPago');
    
    // Recargar pagos del aplicativo actual
    try{
      const pagos=await api(`/api/aplicativos/${currentAppId}/pagos`);
      currentAppPagos=Array.isArray(pagos)?pagos:[];
      renderAplicativoPagos();
    }catch(e){}
    
    toast('Pago agregado correctamente','ok');
  }catch(e){
    toast('Error al guardar pago','err');
  }
}

async function delPago(pago_id){
  if(!confirm('¿Eliminar este pago?'))return;
  
  try{
    await api('/api/pagos-aplicativos/'+pago_id,'DELETE');
    toast('Pago eliminado','info');
    
    // Recargar si estamos en modal
    if(currentAppId){
      const pagos=await api(`/api/aplicativos/${currentAppId}/pagos`);
      currentAppPagos=Array.isArray(pagos)?pagos:[];
      renderAplicativoPagos();
    }
  }catch(e){
    toast('Error al eliminar pago','err');
  }
}

/* ════════════════════════════════════════════════════
   CELULARES
════════════════════════════════════════════════════ */
let editCelularId=null;

function updateCelularMarcasSelect(){
  const sel=$('ftCelularMarca');
  if(!sel) return;
  const current=sel.value;
  const marcas=[...new Set(CELULARES.map(c=>c.marca).filter(Boolean))].sort();
  sel.innerHTML='<option value="">Todas las marcas</option>';
  marcas.forEach(m=>{
    const opt=document.createElement('option');
    opt.value=m;
    opt.textContent=m;
    sel.appendChild(opt);
  });
  sel.value=current;
}

function clearCelularFilters(){
  $('srchCelular').value='';
  $('ftCelularMarca').value='';
  $('ftCelularEst').value='';
  currentPage['celular']=1;
  renderCelulares();
}

function renderCelulares(){
  const q=($('srchCelular')?.value||'');
  const marca=$('ftCelularMarca')?.value||'';
  const est=$('ftCelularEst')?.value||'';

  let rows=searchMultiField(CELULARES,q,SEARCH_FIELDS.celular);

  rows=rows.filter(c=>(!marca||c.marca===marca)&&(!est||c.estado===est));

  rows=applyAdvancedFilters('celular',rows);
  
  $('celularCount').textContent=`${rows.length} de ${CELULARES.length} celular(es)`;
  
  const {data:pageData,totalPages,currentPage:cp}=paginateArray(rows,'celular');
  
  const tb=$('celularTbody');
  if(!rows.length){
    tb.innerHTML=`<tr><td colspan="7"><div class="empty"><div class="empty-icon">📞</div><h3>Sin celulares</h3></div></td></tr>`;
    const wrapper=tb.parentElement.parentElement;
    const oldPagination=wrapper.querySelector('[data-pagination="celular"]');
    if(oldPagination) oldPagination.remove();
    return;
  }
  
  tb.innerHTML=pageData.map(c=>{
    const sims=Array.isArray(c.simcard)?c.simcard:[];
    const simsDisplay=sims.slice(0,3).map(s=>{
      const appLabel=s.app==='whatsapp_business'?'WA Business':'WA Messenger';
      const numColor=s.estado==='bloqueado'?'var(--red)':'var(--blue)';
      const bgColor=s.estado==='bloqueado'?'var(--red-soft)':'var(--blue-soft)';
      return `<div style="font-size:11px;padding:4px 6px;background:${bgColor};color:${numColor};border-radius:4px;margin-bottom:3px;font-weight:500"><div style="font-size:10px;opacity:0.8">${appLabel}</div>${s.numero}</div>`;
    }).join('');
    const masIndicador=sims.length>3?`<div style="font-size:10px;color:var(--text3);padding:4px 6px;font-weight:600">+${sims.length-3} más</div>`:'';
    return`<tr>
      <td data-label="Nombre"><strong>${c.nombre}</strong></td>
      <td data-label="Marca">${c.marca}</td>
      <td data-label="IMEI" class="mono">${c.imei}</td>
      <td data-label="IMEI 2" class="mono">${c.imei2?c.imei2:'—'}</td>
      <td data-label="Números SIM"><div style="max-width:180px">${simsDisplay?simsDisplay+masIndicador:'<span style="color:var(--text3)">—</span>'}</div></td>
      <td data-label="Estado"><span class="bs ${bsClass(c.estado)}">${bsLabel(c.estado)}</span></td>
      <td data-label="Acciones"><div class="act-cell">
        <button class="btn btn-secondary btn-sm" onclick="showSimsDelCelular(${c.id})" title="Ver todas las SIM">📋 SIM</button>
        <button class="btn btn-warning btn-sm" onclick="openCelularModal(${c.id})">✏️ Editar</button>
        <button class="btn btn-danger btn-icon btn-sm" onclick="delCelular(${c.id})">🗑️</button>
      </div></td>
    </tr>`;}).join('');
  
  if(totalPages>1){
    const wrapper=tb.parentElement.parentElement;
    let paginationContainer=wrapper.querySelector('[data-pagination="celular"]');
    if(!paginationContainer){
      paginationContainer=document.createElement('div');
      paginationContainer.setAttribute('data-pagination','celular');
      paginationContainer.className='pagination-wrap';
      wrapper.appendChild(paginationContainer);
    }
    paginationContainer.innerHTML=createPaginationControls(cp,totalPages,'celular');
  }else{
    const wrapper=tb.parentElement.parentElement;
    const paginationContainer=wrapper.querySelector('[data-pagination="celular"]');
    if(paginationContainer) paginationContainer.remove();
  }
}

function openCelularModal(cel_id=null){
  editCelularId=null;
  
  if(cel_id){
    const cel=CELULARES.find(c=>c.id===cel_id);
    if(!cel)return;
    editCelularId=cel_id;
    $('celularModalTitle').textContent='Editar Celular';
    $('celularModalSub').textContent=cel.nombre;
    $('cNombre').value=cel.nombre;
    $('cMarca').value=cel.marca;
    $('cImei').value=cel.imei;
    $('cImei2').value=cel.imei2||'';
    $('cWhatsapp').value=cel.whatsapp;
    $('cEstado').value=cel.estado||'bueno';
  }else{
    $('celularModalTitle').textContent='Nuevo Celular';
    $('celularModalSub').textContent='Registrar nuevo dispositivo';
    $('cNombre').value='';
    $('cMarca').value='';
    $('cImei').value='';
    $('cImei2').value='';
    $('cWhatsapp').value='activo';
    $('cEstado').value='bueno';
  }
  open('ovCelular');
}

async function saveCelular(){
  if(isSubmitting){
    toast('Por favor espera a que termine el proceso','info');
    return;
  }
  
  const nombre=$('cNombre').value.trim();
  const marca=$('cMarca').value.trim();
  const imei=$('cImei').value.trim();
  const imei2=$('cImei2').value.trim();
  const whatsapp=$('cWhatsapp').value;
  const estado=$('cEstado').value;
  
  if(!nombre||!marca||!imei){
    toast('Nombre, marca e IMEI son requeridos','err');
    return;
  }
  
  const data={nombre:nombre,marca:marca,imei:imei,imei2:imei2,whatsapp:whatsapp,estado:estado};
  
  isSubmitting=true;
  const btn=$('saveCelularBtn');
  btn.disabled=true;
  const btnText=editCelularId?'Actualizando...':'Registrando...';
  btn.textContent=btnText;
  
  try{
    const res=editCelularId?await api('/api/celulares/'+editCelularId,'PUT',data):await api('/api/celulares','POST',data);
    if(res.error){toast(res.error,'err');throw new Error(res.error)}
    close('ovCelular');await _refreshCels();renderCelulares();renderDashboard();
    toast(editCelularId?'Celular actualizado':'Celular registrado','ok');editCelularId=null;
    isSubmitting=false;
    btn.disabled=false;
    btn.textContent='Registrar Celular';
  }catch(e){
    isSubmitting=false;
    btn.disabled=false;
    btn.textContent='Registrar Celular';
  }
}

async function delCelular(id){
  if(!confirm('¿Eliminar este celular?'))return;
  await api('/api/celulares/'+id,'DELETE');await _refreshCels();renderCelulares();renderDashboard();toast('Celular eliminado','info');
}

async function showSimsDelCelular(celular_id){
  const celular=CELULARES.find(c=>c.id===celular_id);
  if(!celular)return;
  
  // Mapeo de colores para operadores
  const operadorColors={'Movistar':'var(--blue)','Claro':'var(--amber)','Tigo':'var(--red)','WOM':'var(--teal)'};
  const operadorColorsSoft={'Movistar':'var(--blue-soft)','Claro':'var(--amber-soft)','Tigo':'var(--red-soft)','WOM':'var(--teal-soft)'};
  
  // Obtener historial del servidor
  const historialRes=await api(`/api/celulares/${celular_id}/historial-sims`,'GET');
  const historial=Array.isArray(historialRes)?historialRes:[];
  
  const simsActuales=Array.isArray(celular.simcard)?celular.simcard:[];
  
  let html=`<div style="display:flex;gap:12px;margin-bottom:16px">
    <button class="btn btn-secondary" style="flex:1;border-bottom:3px solid var(--blue);cursor:pointer" onclick="switchSimTab('actual')">📱 SIM Actuales (${simsActuales.length})</button>
    <button class="btn btn-secondary" style="flex:1;cursor:pointer" onclick="switchSimTab('historial')">📋 Historial (${historial.length})</button>
  </div>`;
  
  // TAB 1: SIM Cards Actuales
  html+=`<div id="simTabActual">
    <table class="grid">
      <thead>
        <tr>
          <th>Número</th>
          <th>Operador</th>
          <th>Estado</th>
          <th>App</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody>`;
  
  if(simsActuales.length>0){
    simsActuales.forEach(s=>{
      const opColor=operadorColors[s.operador]||'var(--blue)';
      const opColorSoft=operadorColorsSoft[s.operador]||'var(--blue-soft)';
      html+=`<tr>
        <td data-label="Número" class="mono"><strong>${s.numero}</strong></td>
        <td data-label="Operador"><span class="bs" style="background:${opColorSoft};color:${opColor}">${s.operador}</span></td>
        <td data-label="Estado"><span class="bs ${bsClass(s.estado)}">${bsLabel(s.estado)}</span></td>
        <td data-label="App">${s.app==='whatsapp_business'?'WhatsApp Biz':'WhatsApp'}</td>
        <td data-label="Acciones"><div class="act-cell">
          <button class="btn btn-warning btn-sm" onclick="openSimcardModal(${s.id})">✏️ Editar</button>
          <button class="btn btn-danger btn-icon btn-sm" onclick="delSimcard(${s.id})">🗑️</button>
        </div></td>
      </tr>`;
    });
  }else{
    html+=`<tr><td colspan="5" style="text-align:center;color:var(--text3)">Sin SIM cards actualmente</td></tr>`;
  }
  
  html+=`</tbody></table></div>`;
  
  // TAB 2: Historial de Cambios
  html+=`<div id="simTabHistorial" style="display:none">
    <table class="grid">
      <thead>
        <tr>
          <th>Número</th>
          <th>Operador</th>
          <th>Fecha Agregada</th>
          <th>Fecha Removida</th>
          <th>Duración</th>
        </tr>
      </thead>
      <tbody>`;
  
  if(historial.length>0){
    historial.forEach(h=>{
      const sim=h.simcard;
      const fechaAg=new Date(h.fecha_agregada);
      const fechaRem=h.fecha_removida?new Date(h.fecha_removida):null;
      const duracion=fechaRem?Math.floor((fechaRem-fechaAg)/(1000*60*60*24))+' días':h.fecha_removida?'Removida':'Activa';
      const statusBg=h.fecha_removida?'background:var(--red-soft);color:var(--red)':'background:var(--green-soft);color:var(--green)';
      const opColor=sim?operadorColors[sim.operador]||'var(--blue)':'var(--text2)';
      const opColorSoft=sim?operadorColorsSoft[sim.operador]||'var(--blue-soft)':'var(--text2-soft)';
      
      html+=`<tr>
        <td data-label="Número" class="mono"><strong>${sim?sim.numero:'[Eliminada]'}</strong></td>
        <td data-label="Operador"><span class="bs" style="background:${opColorSoft};color:${opColor}">${sim?sim.operador:'N/A'}</span></td>
        <td data-label="Fecha Agregada">${fechaAg.toLocaleDateString('es-CO')}<br><small style="color:var(--text3)">${fechaAg.toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit'})}</small></td>
        <td data-label="Fecha Removida">${fechaRem?fechaRem.toLocaleDateString('es-CO')+'<br><small style="color:var(--text3)">'+fechaRem.toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit'})+'</small>':'<span style="color:var(--text3)">—</span>'}</td>
        <td data-label="Duración" style="${statusBg};border-radius:8px;padding:8px;text-align:center">${duracion}</td>
      </tr>`;
    });
  }else{
    html+=`<tr><td colspan="5" style="text-align:center;color:var(--text3)">Sin historial</td></tr>`;
  }
  
  html+=`</tbody></table></div>`;
  
  $('simsDelCelularContent').innerHTML=html;
  open('ovSimsDelCelular');
}

function switchSimTab(tab){
  const actual=$('simTabActual');
  const hist=$('simTabHistorial');
  const btns=document.querySelectorAll('#simsDelCelularContent~button');
  
  if(tab==='actual'){
    actual.style.display='block';
    hist.style.display='none';
  }else{
    actual.style.display='none';
    hist.style.display='block';
  }
}

/* ════════════════════════════════════════════════════
   SIM CARDS
════════════════════════════════════════════════════ */
let currentSimcardId=null;
let currentSimcardBloqueos=[];
let editSimcardId=null;

function clearSimcardFilters(){
  $('srchSimcard').value='';
  $('srchSimcardIMEI').value='';
  $('ftSimcardOperador').value='';
  $('ftSimcardEst').value='';
  currentPage['simcard']=1;
  renderSimcards();
}

function renderSimcards(){
  const q=($('srchSimcard')?.value||'');
  const qIMEI=($('srchSimcardIMEI')?.value||'').toLowerCase();
  const operador=$('ftSimcardOperador')?.value||'';
  const estado=$('ftSimcardEst')?.value||'';
  
  // Búsqueda multi-campo en: numero, operador
  let rows=searchMultiField(SIMCARDS,q,['numero','operador']);
  
  // Si hay búsqueda de IMEI, filtrar por IMEI o IMEI2 del celular asociado
  if(qIMEI){
    rows=rows.filter(s=>{
      if(!s.celular_id) return false; // Excluir SIM sin celular
      const cel=CELULARES.find(c=>c.id===s.celular_id);
      if(!cel) return false;
      const imei1=(cel.imei||'').toLowerCase();
      const imei2=(cel.imei2||'').toLowerCase();
      return imei1.includes(qIMEI) || imei2.includes(qIMEI);
    });
  }
  
  // Aplicar filtros específicos
  rows=rows.filter(s=>(!operador||s.operador===operador)&&(!estado||s.estado===estado));
  
  // Aplicar filtros avanzados anidables
  rows=applyAdvancedFilters('simcard',rows);
  
  $('simcardCount').textContent=`${rows.length} de ${SIMCARDS.length} SIM(s)`;
  
  const {data:pageData,totalPages,currentPage:cp}=paginateArray(rows,'simcard');
  
  const tb=$('simcardTbody');
  if(!rows.length){
    tb.innerHTML=`<tr><td colspan="8"><div class="empty"><div class="empty-icon">🆔</div><h3>Sin SIM cards</h3></div></td></tr>`;
    const wrapper=tb.parentElement.parentElement;
    const oldPagination=wrapper.querySelector('[data-pagination="simcard"]');
    if(oldPagination) oldPagination.remove();
    return;
  }
  
  tb.innerHTML=pageData.map(s=>{
    const cel=s.celular?s.celular:null;
    const numColor=s.estado==='bloqueado'?'var(--red)':'var(--text)';
    const appLabel=s.app==='whatsapp_business'?'📱 WA Business':'💬 WA Messenger';
    return`<tr>
      <td data-label="Número" class="mono"><strong style="color:${numColor}">${s.numero}</strong><br><small style="font-size:11px;opacity:0.7">${appLabel}</small></td>
      <td data-label="Operador"><span style="font-size:12px;background:var(--teal-soft);color:var(--teal);padding:4px 8px;border-radius:4px;display:inline-block">${s.operador}</span></td>
      <td data-label="Serial" class="mono">${s.serial||'—'}</td>
      <td data-label="Celular">${cel?cel.nombre:'—'}</td>
      <td data-label="Estado"><span class="bs ${bsClass(s.estado)}">${bsLabel(s.estado)}</span></td>
      <td data-label="Bloqueos"><button class="btn btn-secondary btn-sm" onclick="showBloqueoDetalle(${s.id})">📋</button></td>
      <td data-label="Acciones"><div class="act-cell">
        <button class="btn btn-warning btn-sm" onclick="openSimcardModal(${s.id})">✏️ Editar</button>
        <button class="btn btn-danger btn-icon btn-sm" onclick="delSimcard(${s.id})">🗑️</button>
      </div></td>
    </tr>`;}).join('');
  
  if(totalPages>1){
    const wrapper=tb.parentElement.parentElement;
    let paginationContainer=wrapper.querySelector('[data-pagination="simcard"]');
    if(!paginationContainer){
      paginationContainer=document.createElement('div');
      paginationContainer.setAttribute('data-pagination','simcard');
      paginationContainer.className='pagination-wrap';
      wrapper.appendChild(paginationContainer);
    }
    paginationContainer.innerHTML=createPaginationControls(cp,totalPages,'simcard');
  }else{
    const wrapper=tb.parentElement.parentElement;
    const paginationContainer=wrapper.querySelector('[data-pagination="simcard"]');
    if(paginationContainer) paginationContainer.remove();
  }
}

async function openSimcardModal(sim_id=null){
  editSimcardId=null;
  currentSimcardId=sim_id;
  currentSimcardBloqueos=[];
  
  // Cargar lista de celulares en el select
  const select=$('sCelularId');
  select.innerHTML='<option value="">Ninguno</option>'+CELULARES.map(c=>`<option value="${c.id}">${c.nombre}</option>`).join('');
  
  if(sim_id){
    const sim=SIMCARDS.find(s=>s.id===sim_id);
    if(!sim)return;
    editSimcardId=sim_id;
    $('simcardModalTitle').textContent='Editar SIM Card';
    $('simcardModalSub').textContent=sim.numero;
    $('sNumero').value=sim.numero;
    $('sSerial').value=sim.serial||'';
    $('sOperador').value=sim.operador;
    $('sEstado').value=sim.estado;
    $('sApp').value=sim.app;
    $('sSendflow').value=sim.sendflow||'no';
    $('sCelularId').value=sim.celular_id||'';
    
    // Cargar bloqueos
    try{
      const bloqueos=await api(`/api/simcards/${sim_id}/bloqueos`);
      currentSimcardBloqueos=Array.isArray(bloqueos)?bloqueos:[];
      renderSimcardBloqueos();
    }catch(e){
      currentSimcardBloqueos=[];
    }
  }else{
    $('simcardModalTitle').textContent='Nueva SIM Card';
    $('simcardModalSub').textContent='Registrar nuevatarjeta SIM';
    $('sNumero').value='';
    $('sSerial').value='';
    $('sOperador').value='Movistar';
    $('sEstado').value='activo';
    $('sApp').value='whatsapp';
    $('sSendflow').value='no';
    $('sCelularId').value='';
    currentSimcardBloqueos=[];
    renderSimcardBloqueos();
  }
  open('ovSimcard');
}

function renderSimcardBloqueos(){
  const container=$('simcardBloqueoContainer');
  if(!currentSimcardBloqueos.length){
    container.innerHTML=`<div style="text-align:center;color:var(--text3);padding:20px">Sin bloqueos registrados</div>`;
    return;
  }
  
  container.innerHTML=`<div style="background:var(--surface2);border-radius:var(--radius-sm);overflow:hidden">
    ${currentSimcardBloqueos.map((b,idx)=>`<div style="padding:12px;border-bottom:${idx<currentSimcardBloqueos.length-1?'1px solid var(--border)':'none'}">
      <div style="font-size:12px;color:var(--text3)">Bloqueo #${idx+1}</div>
      <div style="font-size:13px;font-weight:600">${fmtDate(b.fecha_bloqueo)}</div>
      ${b.razon?`<div style="font-size:12px;color:var(--text3)">Razón: ${b.razon}</div>`:''}
    </div>`).join('')}
  </div>`;
}

async function showBloqueoDetalle(sim_id){
  try{
    const sim=SIMCARDS.find(s=>s.id===sim_id);
    if(!sim)return;
    
    const bloqueos=await api(`/api/simcards/${sim_id}/bloqueos`);
    const bloqueosList=Array.isArray(bloqueos)?bloqueos:[];
    
    $('bloqueoDetalleTitle').textContent=`Bloqueos - ${sim.numero} (${sim.operador})`;
    const tb=$('bloqueoDetalleTbody');
    
    if(!bloqueosList.length){
      tb.innerHTML=`<tr><td colspan="4"><div class="empty" style="padding:30px"><div class="empty-icon">🚫</div><h3>Sin bloqueos</h3></div></td></tr>`;
    }else{
      tb.innerHTML=bloqueosList.map(b=>`<tr>
        <td data-label="Fecha Bloqueo" class="mono">${fmtDate(b.fecha_bloqueo)}</td>
        <td data-label="Razón">${b.razon||'—'}</td>
        <td data-label="Notas" style="font-size:12px;color:var(--text3)">${b.notas||'—'}</td>
        <td data-label="Acciones"><button class="btn btn-danger btn-icon btn-sm" onclick="delBloqueo(${b.id})">🗑️</button></td>
      </tr>`).join('');
    }
    
    open('ovBloqueoDetalle');
  }catch(e){
    toast('Error al cargar historial de bloqueos','err');
  }
}

async function saveSimcard(){
  if(isSubmitting){
    toast('Por favor espera a que termine el proceso','info');
    return;
  }
  
  const numero=$('sNumero').value.trim();
  const serial=$('sSerial').value.trim();
  const operador=$('sOperador').value;
  const estado=$('sEstado').value;
  const app=$('sApp').value;
  const sendflow=$('sSendflow').value;
  const celular_id=$('sCelularId').value||null;
  
  if(!numero||!operador){
    toast('Número y operador son requeridos','err');
    return;
  }
  
  const data={numero:numero,serial:serial,operador:operador,estado:estado,app:app,sendflow:sendflow,celular_id:celular_id?parseInt(celular_id):null};
  
  isSubmitting=true;
  const btn=$('saveSimcardBtn');
  btn.disabled=true;
  const btnText=editSimcardId?'Actualizando...':'Registrando...';
  btn.textContent=btnText;
  
  try{
    const res=editSimcardId?await api('/api/simcards/'+editSimcardId,'PUT',data):await api('/api/simcards','POST',data);
    if(res.error){toast(res.error,'err');throw new Error(res.error)}
    close('ovSimcard');await Promise.all([_refreshSims(),_refreshCels()]);renderSimcards();renderDashboard();
    toast(editSimcardId?'SIM Card actualizada':'SIM Card registrada','ok');editSimcardId=null;
    isSubmitting=false;
    btn.disabled=false;
    btn.textContent='Registrar SIM Card';
  }catch(e){
    isSubmitting=false;
    btn.disabled=false;
    btn.textContent='Registrar SIM Card';
  }
}

async function delSimcard(id){
  if(!confirm('¿Eliminar esta SIM Card?'))return;
  await api('/api/simcards/'+id,'DELETE');await Promise.all([_refreshSims(),_refreshCels()]);renderSimcards();renderDashboard();toast('SIM Card eliminada','info');
}

function addBloqueoModal(){
  $('bFecha').value=TODAY;
  $('bRazon').value='';
  $('bNotas').value='';
  open('ovAgregarBloqueo');
}

async function saveBloqueo(){
  const fecha_bloqueo=$('bFecha').value;
  const razon=$('bRazon').value||'';
  const notas=$('bNotas').value||'';
  
  if(!fecha_bloqueo){
    toast('La fecha del bloqueo es requerida','err');
    return;
  }
  
  if(!currentSimcardId){
    toast('Error: No se seleccionó SIM card','err');
    return;
  }
  
  const data={fecha_bloqueo:fecha_bloqueo,razon:razon,notas:notas};
  
  try{
    const res=await api(`/api/simcards/${currentSimcardId}/bloqueos`,'POST',data);
    if(res.error){toast(res.error,'err');throw new Error(res.error)}
    close('ovAgregarBloqueo');
    
    // Recargar bloqueos
    try{
      const bloqueos=await api(`/api/simcards/${currentSimcardId}/bloqueos`);
      currentSimcardBloqueos=Array.isArray(bloqueos)?bloqueos:[];
      renderSimcardBloqueos();
    }catch(e){}
    
    toast('Bloqueo registrado correctamente','ok');
  }catch(e){
    toast('Error al registrar bloqueo','err');
  }
}

async function delBloqueo(bloqueo_id){
  if(!confirm('¿Eliminar este bloqueo?'))return;
  
  try{
    await api('/api/bloqueos/'+bloqueo_id,'DELETE');
    toast('Bloqueo eliminado','info');
    
    // Recargar si estamos en modal
    if(currentSimcardId){
      const bloqueos=await api(`/api/simcards/${currentSimcardId}/bloqueos`);
      currentSimcardBloqueos=Array.isArray(bloqueos)?bloqueos:[];
      renderSimcardBloqueos();
    }
  }catch(e){
    toast('Error al eliminar bloqueo','err');
  }
}

/* ════════════════════════════════════════════════════
   PRÉSTAMOS
════════════════════════════════════════════════════ */
function renderLoan(){
  const q=($('srchLoan')?.value||'');
  const est=$('ftLoanEst')?.value||'';
  const dpto=$('ftLoanDpto')?.value||'';
  const vencido=$('ftLoanVencido')?.value||'';

  // ── Individuales: lógica original intacta ──────────────────────
  let individualRows=searchMultiField(LOANS,q,SEARCH_FIELDS.loan);
  individualRows=individualRows.filter(p=>{
    if(est&&p.estado!==est) return false;
    if(dpto&&p.departamento!==dpto) return false;
    if(vencido){
      const dl=daysLeft(p.fecha_devolucion_esperada);
      const isOverdue=p.estado==='activo'&&!p.fecha_devolucion_real&&p.fecha_devolucion_esperada&&p.fecha_devolucion_esperada<TODAY;
      const isNear=p.estado==='activo'&&!p.fecha_devolucion_real&&dl!==null&&dl>=0&&dl<=7;
      if(vencido==='vencido'&&!isOverdue) return false;
      if(vencido==='proximo'&&!isNear) return false;
    }
    return true;
  });
  individualRows=applyAdvancedFilters('loan',individualRows);

  // ── Masivos: filtros equivalentes ──────────────────────────────
  const masivosArr=Array.isArray(LOANS_MASIVOS)?LOANS_MASIVOS:[];
  let masivoRows=masivosArr.filter(p=>{
    if(q){
      const hay=(p.usuario_nombre+' '+(p.departamento||'')+' masivo').toLowerCase();
      if(!hay.includes(q.toLowerCase())) return false;
    }
    if(est&&p.estado!==est) return false;
    if(dpto&&p.departamento!==dpto) return false;
    if(vencido){
      const dl=daysLeft(p.fecha_devolucion_esperada);
      const isOverdue=p.estado==='activo'&&!p.fecha_devolucion_real&&p.fecha_devolucion_esperada&&p.fecha_devolucion_esperada<TODAY;
      const isNear=p.estado==='activo'&&!p.fecha_devolucion_real&&dl!==null&&dl>=0&&dl<=7;
      if(vencido==='vencido'&&!isOverdue) return false;
      if(vencido==='proximo'&&!isNear) return false;
    }
    return true;
  });

  // ── Combinar y ordenar por fecha de creación ───────────────────
  const allRows=[
    ...individualRows.map(r=>({...r,_tipo:'individual'})),
    ...masivoRows.map(r=>({...r,_tipo:'masivo'}))
  ].sort((a,b)=>(b.creado_en||'').localeCompare(a.creado_en||''));

  const total=LOANS.length+masivosArr.length;
  $('loanCount').textContent=`${allRows.length} de ${total} préstamo(s)`;

  const {data:pageData,totalPages,currentPage:cp}=paginateArray(allRows,'loan');

  const tb=$('loanTbody');
  if(!allRows.length){
    tb.innerHTML=`<tr><td colspan="9"><div class="empty"><div class="empty-icon">🔁</div><h3>Sin préstamos</h3></div></td></tr>`;
    $('loanPaginationContainer').innerHTML='';
    return;
  }

  tb.innerHTML=pageData.map(p=>{
    const overdue=p.estado==='activo'&&!p.fecha_devolucion_real&&p.fecha_devolucion_esperada&&p.fecha_devolucion_esperada<TODAY;
    const dl=daysLeft(p.fecha_devolucion_esperada);
    const near=p.estado==='activo'&&!p.fecha_devolucion_real&&dl!==null&&dl>=0&&dl<=7;
    const rowBg=overdue?'background:rgba(248,113,113,.04)':near?'background:rgba(251,191,36,.04)':'';

    if(p._tipo==='masivo'){
      return`<tr style="${rowBg}">
        <td data-label="Equipo"><div class="av-cell">
          <div class="tipo-av">📦</div>
          <div>
            <div class="name" style="font-weight:600">${p.num_equipos||0} equipo(s)</div>
            <span style="font-size:10px;font-weight:700;color:var(--blue);background:rgba(99,179,237,.15);padding:2px 6px;border-radius:4px">MASIVO</span>
          </div>
        </div></td>
        <td data-label="Responsable">${p.usuario_nombre}<div style="font-size:11px;color:var(--text3)">${p.departamento||''}</div></td>
        <td data-label="Fecha Préstamo" class="mono">${fmtDate(p.fecha_prestamo)}</td>
        <td data-label="Devolver Antes" class="mono" style="color:${overdue?'var(--red)':near?'var(--amber)':'var(--text3)'}">
          ${fmtDate(p.fecha_devolucion_esperada)}
          ${overdue?`<div style="font-size:10px;color:var(--red);font-weight:700">Venció hace ${Math.abs(dl)} día(s)</div>`:''}
          ${near&&!overdue?`<div style="font-size:10px;color:var(--amber);font-weight:700">En ${dl} día(s)</div>`:''}
        </td>
        <td data-label="Devuelto" class="mono">${fmtDate(p.fecha_devolucion_real)}</td>
        <td data-label="Estado"><span class="bs ${overdue?'bs-vencido':bsClass(p.estado)}">${overdue?'Vencido':bsLabel(p.estado)}</span></td>
        <td data-label="Términos"><span style="font-weight:600;color:${p.terminos_aceptados?'var(--green)':'var(--text3)'}">${p.terminos_aceptados?'✅ Aceptó':'⏳ Pendiente'}</span>${p.firma_url?'<br><span style="font-size:10px;color:var(--teal)">✍ Firmado</span>':''}</td>
        <td data-label="Notas" style="max-width:140px;font-size:12px;color:var(--text3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${p.notas||'—'}</td>
        <td data-label="Acciones"><div class="act-cell">
          <button class="btn btn-primary btn-sm" onclick="viewLoanMasivoItems(${p.id})">👁 Ver equipos</button>
          ${p.estado!=='devuelto'?`<button class="btn btn-success btn-sm" onclick="sendMasivoFirmaLink(${p.id})">🔗 Enlace Firma</button>`:''}
          ${p.estado!=='devuelto'?`<button class="btn btn-teal btn-sm" onclick="returnLoanMasivo(${p.id})">📤 Devolver</button>`:''}
          <button class="btn btn-danger btn-icon btn-sm" onclick="delLoanMasivo(${p.id})">🗑️ Eliminar</button>
        </div></td>
      </tr>`;
    }

    return`<tr style="${rowBg}">
      <td data-label="Equipo"><div class="av-cell">
        <div class="tipo-av">${TIPO_ICON[p.equipo_tipo]||'📦'}</div>
        <div class="name">${p.equipo_nombre}</div>
      </div></td>
      <td data-label="Responsable">${p.usuario_nombre}<div style="font-size:11px;color:var(--text3)">${p.departamento||''}</div></td>
      <td data-label="Fecha Préstamo" class="mono">${fmtDate(p.fecha_prestamo)}</td>
      <td data-label="Devolver Antes" class="mono" style="color:${overdue?'var(--red)':near?'var(--amber)':'var(--text3)'}">
        ${fmtDate(p.fecha_devolucion_esperada)}
        ${overdue?`<div style="font-size:10px;color:var(--red);font-weight:700">Venció hace ${Math.abs(dl)} día(s)</div>`:''}
        ${near&&!overdue?`<div style="font-size:10px;color:var(--amber);font-weight:700">En ${dl} día(s)</div>`:''}
      </td>
      <td data-label="Devuelto" class="mono">${fmtDate(p.fecha_devolucion_real)}</td>
      <td data-label="Estado"><span class="bs ${overdue?'bs-vencido':bsClass(p.estado)}">${overdue?'Vencido':bsLabel(p.estado)}</span></td>
      <td data-label="Términos"><span style="font-weight:600;color:${p.terminos_aceptados?'var(--green)':'var(--text3)'}">${p.terminos_aceptados?'✅ Aceptó':'⏳ Pendiente'}</span></td>
      <td data-label="Notas" style="max-width:140px;font-size:12px;color:var(--text3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${p.notas||'—'}</td>
      <td data-label="Acciones"><div class="act-cell">
        <button class="btn btn-info btn-sm" onclick="viewLoanDetails(${p.id})" title="Ver detalles">ℹ️ Detalles</button>
        ${p.estado==='solicitado'?`<button class="btn btn-warning btn-sm" onclick="openLoanModal(${p.id})">✏️ Editar</button>`:``}
        ${p.estado!=='devuelto'?`<button class="btn btn-success btn-sm" onclick="showSignatureLinkModal(${p.id})">🔗 Enviar Link</button>`:''}
        ${p.estado==='firmado'?`<button class="btn btn-teal btn-sm" onclick="returnLoan(${p.id})">📤 Devolver</button>`:''}
        <button class="btn btn-danger btn-icon btn-sm" onclick="delLoan(${p.id})">🗑️ Eliminar</button>
      </div></td>
    </tr>`;
  }).join('');

  $('loanPaginationContainer').innerHTML=createPaginationControls(cp,totalPages,'loan');
}
function updateLoanDptosSelect(){
  const dptos=[...new Set([...LOANS,...LOANS_MASIVOS].map(p=>p.departamento).filter(d=>d))].sort();
  const sel=$('ftLoanDpto');
  if(!sel) return;
  const current=sel.value;
  sel.innerHTML='<option value="">Todos los departamentos</option>';
  dptos.forEach(d=>{
    const opt=document.createElement('option');
    opt.value=d;
    opt.textContent=d;
    sel.appendChild(opt);
  });
  sel.value=current;
}

function clearLoanFilters(){
  $('srchLoan').value='';
  $('ftLoanEst').value='';
  $('ftLoanDpto').value='';
  $('ftLoanVencido').value='';
  currentPage['loan']=1;
  renderLoan();
}

/* ── PRÉSTAMOS MASIVOS ────────────────────────────────────────── */
let _lmSelectedIds=[];
let _lmScannerInstance=null;

async function toggleLmScanner(){
  if(_lmScannerInstance) await closeLmScanner();
  else await openLmScanner();
}

async function openLmScanner(){
  const area=$('lmScanArea'),label=$('lmScanLabel'),icon=$('lmScanIcon'),status=$('lmScanStatus');
  if(!area)return;
  area.style.display='block';
  if(label)label.textContent='Detener scanner';
  if(icon)icon.textContent='⏹';
  if(status)status.textContent='Iniciando cámara…';
  if(typeof Html5Qrcode==='undefined'){if(status)status.textContent='Librería no disponible';return;}
  await new Promise(r=>setTimeout(r,200));
  _lmScannerInstance=new Html5Qrcode('lmScannerRegion');
  const config={fps:25,qrbox:{width:260,height:80},experimentalFeatures:{useBarCodeDetectorIfSupported:true}};
  if(typeof Html5QrcodeSupportedFormats!=='undefined'){
    config.formatsToSupport=[Html5QrcodeSupportedFormats.CODE_128,Html5QrcodeSupportedFormats.QR_CODE];
  }
  try{
    await _lmScannerInstance.start({facingMode:'environment'},config,(text)=>_onLmScanSuccess(text),()=>{});
    if(status)status.textContent='Apunta al código de barras del equipo';
  }catch(err){
    if(status)status.textContent='Sin acceso a cámara: '+(err.message||err);
    _lmScannerInstance=null;
    if(area)area.style.display='none';
    if(label)label.textContent='Escanear código de barras';
    if(icon)icon.textContent='📷';
  }
}

async function closeLmScanner(){
  if(_lmScannerInstance){
    try{if(_lmScannerInstance.isScanning)await _lmScannerInstance.stop();_lmScannerInstance.clear();}catch{}
    _lmScannerInstance=null;
  }
  const region=$('lmScannerRegion');if(region)region.innerHTML='';
  const area=$('lmScanArea');if(area)area.style.display='none';
  const label=$('lmScanLabel');if(label)label.textContent='Escanear código de barras';
  const icon=$('lmScanIcon');if(icon)icon.textContent='📷';
  const status=$('lmScanStatus');if(status)status.textContent='';
}

function _onLmScanSuccess(text){
  let targetId=null;
  try{const url=new URL(text);const m=url.pathname.match(/\/equipo\/(\d+)/);if(m)targetId=parseInt(m[1]);}
  catch{if(/^\d+$/.test(text.trim()))targetId=parseInt(text.trim());}
  if(!targetId){toast('Código no reconocido','err');return;}
  if(_lmSelectedIds.includes(targetId)){toast('Este equipo ya fue agregado','info');return;}
  const eq=(window.equiposMasivoDisponibles||[]).find(e=>e.id===targetId);
  if(!eq){
    const inAll=EQ.find(e=>e.id===targetId);
    toast(inAll?`${inAll.nombre} no está disponible`:'Equipo no encontrado','err');
    return;
  }
  _lmSelectedIds.push(targetId);
  _lmRenderChips();
  toast(`${eq.nombre} agregado ✓`,'ok');
}

function openLoanMasivoModal(){
  closeLmScanner();
  _lmSelectedIds=[];
  const conPrestamo=new Set(
    LOANS.filter(l=>l.estado==='firmado'||l.estado==='activo').map(l=>l.equipo_id)
  );
  const enMasivo=new Set(
    (LOANS_MASIVOS||[]).filter(m=>m.estado!=='devuelto').flatMap(m=>m.equipo_ids||[])
  );
  window.equiposMasivoDisponibles=EQ.filter(e=>
    !conPrestamo.has(e.id)&&!enMasivo.has(e.id)&&e.disponibilidad!=='Retirado'
  );
  _lmRenderChips();
  $('lmEqSearch').value='';
  $('lmEqList').style.display='none';
  $('lmFecha').value=TODAY;
  $('lmDevol').value='';
  $('lmNotas').value='';
  $('lmUsr').innerHTML='<option value="">Seleccionar responsable…</option>'+
    USR.filter(u=>u.estado==='activo').map(u=>`<option value="${u.id}">${u.nombre} — ${u.departamento||''}</option>`).join('');
  open('ovLoanMasivo');
}

function _lmRenderChips(){
  const container=$('lmChips');
  container.innerHTML=_lmSelectedIds.map(id=>{
    const eq=EQ.find(e=>e.id===id)||{};
    return`<span style="display:inline-flex;align-items:center;gap:4px;padding:4px 8px;background:var(--surface3);border:1px solid var(--border);border-radius:20px;font-size:12px">
      ${eq.nombre||'Equipo '+id}
      <button onclick="_lmRemoveEquipo(${id})" style="background:none;border:none;cursor:pointer;color:var(--text3);font-size:14px;line-height:1;padding:0 2px">&times;</button>
    </span>`;
  }).join('');
  $('lmEqCount').textContent=`${_lmSelectedIds.length} equipo(s) seleccionado(s)`;
}

function _lmRemoveEquipo(id){
  _lmSelectedIds=_lmSelectedIds.filter(x=>x!==id);
  _lmRenderChips();
  filterEquiposMasivo();
}

function filterEquiposMasivo(){
  const q=$('lmEqSearch').value.toLowerCase();
  const list=$('lmEqList');
  // Usar la lista pre-calculada al abrir el modal, excluyendo los ya seleccionados
  const base=(window.equiposMasivoDisponibles||[]).filter(e=>!_lmSelectedIds.includes(e.id));
  const filtered=q?base.filter(e=>
    (e.nombre||'').toLowerCase().includes(q)||
    (e.serial||'').toLowerCase().includes(q)||
    (e.marca||'').toLowerCase().includes(q)||
    (e.tipo_nombre||e.tipo||'').toLowerCase().includes(q)
  ):base;

  if(!q){list.style.display='none';return;}
  list.style.display='block';
  if(!filtered.length){
    list.innerHTML='<div style="padding:12px;color:var(--text3);font-size:12px">No hay equipos disponibles</div>';
    return;
  }
  list.innerHTML=filtered.slice(0,30).map(e=>`
    <div style="padding:10px 12px;cursor:pointer;border-bottom:1px solid var(--border);transition:background 0.15s"
         onmouseover="this.style.background='var(--surface3)'"
         onmouseout="this.style.background='transparent'"
         onclick="_lmAddEquipo(${e.id})">
      <div style="font-size:13px;font-weight:600;color:var(--text)">${e.nombre}</div>
      <div style="font-size:11px;color:var(--text3)">${e.tipo_nombre||e.tipo||''} ${e.serial?'· Serial: '+e.serial:''}</div>
    </div>
  `).join('');
}

function _lmAddEquipo(id){
  if(!_lmSelectedIds.includes(id)) _lmSelectedIds.push(id);
  $('lmEqSearch').value='';
  $('lmEqList').style.display='none';
  _lmRenderChips();
}

document.addEventListener('click',function(e){
  if(e.target.id!=='lmEqSearch'&&!e.target.closest('#lmEqList')){
    const l=$('lmEqList');
    if(l) l.style.display='none';
  }
});

async function saveLoanMasivo(){
  if(!_lmSelectedIds.length){toast('Selecciona al menos 1 equipo','err');return;}
  const usuario_id=parseInt($('lmUsr').value);
  const fecha_prestamo=$('lmFecha').value;
  if(!usuario_id||!fecha_prestamo){toast('Responsable y fecha son requeridos','err');return;}

  const btn=$('saveLoanMasivoBtn');
  btn.disabled=true;btn.textContent='Registrando…';

  try{
    const res=await api('/api/prestamos/masivos','POST',{
      equipo_ids:_lmSelectedIds,
      usuario_id,
      fecha_prestamo,
      fecha_devolucion_esperada:$('lmDevol').value||null,
      notas:$('lmNotas').value
    });
    if(res.error){toast(res.error,'err');return;}
    await closeLmScanner();
    close('ovLoanMasivo');
    await Promise.all([_refreshLoans(),_refreshLoansMasivos()]);
    DASH=computeDash();renderLoan();renderDashboard();
    toast(`Préstamo masivo registrado con ${_lmSelectedIds.length} equipo(s) ✅`,'ok');
  }catch(e){
    toast('Error al registrar: '+e.message,'err');
  }finally{
    btn.disabled=false;btn.textContent='Registrar préstamo masivo';
  }
}

let _currentMasivoId=null;
function viewLoanMasivoItems(id){
  _currentMasivoId=id;
  const masivo=LOANS_MASIVOS.find(m=>m.id===id);
  if(!masivo){return;}
  $('lmItemsSub').textContent=`${masivo.usuario_nombre} · ${fmtDate(masivo.fecha_prestamo)}`;

  // Usar equipo_ids ya en memoria + EQ para evitar API call extra
  const equipoIds=masivo.equipo_ids||[];
  if(!equipoIds.length){
    $('lmItemsContent').innerHTML='<p style="color:var(--text3);padding:12px 0">Sin equipos registrados.</p>';
    document.getElementById('ovLoanMasivoItems').classList.add('open');
    return;
  }
  const rows=equipoIds.map((eqId,i)=>{
    const eq=EQ.find(e=>e.id===eqId)||{};
    return`<tr style="border-bottom:1px solid var(--border)">
      <td style="padding:8px 4px;color:var(--text3)">${i+1}</td>
      <td style="padding:8px 4px;font-weight:600">${eq.nombre||'Equipo '+eqId}</td>
      <td style="padding:8px 4px;color:var(--text3)">${eq.tipo_nombre||eq.tipo||'—'}</td>
      <td style="padding:8px 4px;color:var(--text3)">${eq.marca||'—'}</td>
      <td style="padding:8px 4px;color:var(--text3);font-family:monospace">${eq.serial||'—'}</td>
    </tr>`;
  }).join('');
  $('lmItemsContent').innerHTML=`
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead><tr style="border-bottom:2px solid var(--border)">
        <th style="padding:8px 4px;text-align:left">#</th>
        <th style="padding:8px 4px;text-align:left">Equipo</th>
        <th style="padding:8px 4px;text-align:left">Tipo</th>
        <th style="padding:8px 4px;text-align:left">Marca</th>
        <th style="padding:8px 4px;text-align:left">Serial</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;

  const firmaBtn=$('lmItemsFirmaBtn');
  if(firmaBtn) firmaBtn.style.display=masivo.estado==='devuelto'?'none':'';
  document.getElementById('ovLoanMasivoItems').classList.add('open');
}

function sendMasivoFirmaLink(id){
  const masivoId=id||_currentMasivoId;
  if(!masivoId) return;
  const masivo=LOANS_MASIVOS.find(m=>m.id===masivoId);
  if(!masivo) return;
  const url=`${window.location.origin}/firma/${masivoId}?doc=masivo`;
  // Reusar el modal de link de firma existente
  const inp=$('sigLinkUrl');
  if(inp){inp.value=url;}
  document.getElementById('ovLoanMasivoItems').classList.remove('open');
  open('ovSignLink');
}

async function returnLoanMasivo(id){
  if(!confirm('¿Marcar todos los equipos de este préstamo como devueltos?')) return;
  const res=await api(`/api/prestamos/masivos/${id}/devolver`,'PUT');
  if(res.error){toast(res.error,'err');return;}
  await _refreshLoansMasivos();
  DASH=computeDash();renderLoan();renderDashboard();
  toast('Préstamo masivo devuelto ✅','ok');
}

async function delLoanMasivo(id){
  if(!confirm('¿Eliminar este préstamo masivo? Esta acción no se puede deshacer.')) return;
  const res=await api(`/api/prestamos/masivos/${id}`,'DELETE');
  if(res.error){toast(res.error,'err');return;}
  await _refreshLoansMasivos();
  DASH=computeDash();renderLoan();renderDashboard();
  toast('Préstamo masivo eliminado','ok');
}

function openLoanModal(loan_id=null){
  editLoanId=null;

  // Excluir equipos que YA tienen préstamos NO devueltos (no solo 'activo')
  // Pero si estamos editando, excluir solo los demás préstamos activos
  const excludeLoanId=loan_id||null;
  const asignados=new Set(LOANS.filter(p=>p.estado!=='devuelto'&&p.id!==excludeLoanId).map(p=>p.equipo_id));
  const enMasivo=new Set((LOANS_MASIVOS||[]).filter(m=>m.estado!=='devuelto').flatMap(m=>m.equipo_ids||[]));
  window.equiposDisponibles=EQ.filter(e=>!asignados.has(e.id)&&!enMasivo.has(e.id)&&e.disponibilidad!=='Retirado');
  
  if(loan_id){
    // Modo edición
    const loan=LOANS.find(l=>l.id===loan_id);
    if(!loan)return;
    editLoanId=loan_id;
    $('loanModalTitle').textContent='Editar préstamo';
    $('loanModalSub').textContent=loan.equipo_nombre;
    
    // Llenar datos existentes
    $('lEq').value=loan.equipo_id;
    $('lUsr').value=loan.usuario_id;
    $('lFecha').value=loan.fecha_prestamo;
    $('lDevol').value=loan.fecha_devolucion_esperada||'';
    $('lNotas').value=loan.notas||'';
    $('lEqSearch').value=loan.equipo_nombre||'';  // Mostrar nombre del equipo
    $('lEqList').style.display='none';  // Ocultar lista
  }else{
    // Modo crear
    $('loanModalTitle').textContent='Nuevo préstamo';
    $('loanModalSub').textContent='Registrar préstamo vinculado a equipo';
    $('lEqSearch').value='';
    $('lEq').value='';
    $('lFecha').value=TODAY;
    $('lDevol').value='';
    $('lNotas').value='';
  }
  
  filterEquipos();
  $('lUsr').innerHTML='<option value="">Seleccionar responsable…</option>'+USR.filter(u=>u.estado==='activo').map(u=>`<option value="${u.id}">${u.nombre} — ${u.departamento||''}</option>`).join('');
  open('ovLoan');
}

function filterEquipos(){
  const q=$('lEqSearch').value.toLowerCase();
  const list=$('lEqList');
  const equipos=window.equiposDisponibles||[];
  
  const filtered=equipos.filter(e=>
    (e.nombre||'').toLowerCase().includes(q)||
    (e.serial||'').toLowerCase().includes(q)||
    (e.marca||'').toLowerCase().includes(q)||
    (e.tipo_nombre||e.tipo||'').toLowerCase().includes(q)
  );
  
  if(!q){
    list.style.display='none';
    return;
  }
  
  list.style.display='block';
  if(filtered.length===0){
    list.innerHTML='<div style="padding:12px;color:var(--text3);font-size:12px">No hay equipos disponibles</div>';
  }else{
    list.innerHTML=filtered.map(e=>`
      <div style="padding:10px 12px;cursor:pointer;border-bottom:1px solid var(--border);transition:background 0.15s" 
           onmouseover="this.style.background='var(--surface3)'" 
           onmouseout="this.style.background='transparent'" 
           onclick="selectEquipo(${e.id},'${e.nombre.replace(/'/g,"\\'")}')">
        <div style="font-size:13px;font-weight:600;color:var(--text)">${e.nombre}</div>
        <div style="font-size:11px;color:var(--text3)">${e.serial?'Serial: '+e.serial:''}</div>
      </div>
    `).join('');
  }
}

function selectEquipo(id,nombre){
  $('lEq').value=id;
  $('lEqSearch').value=nombre;
  $('lEqList').style.display='none';
}

// Cerrar dropdown de equipos al hacer click fuera
document.addEventListener('click',function(e){
  if(e.target.id!=='lEqSearch'&&!e.target.closest('#lEqList')){
    $('lEqList').style.display='none';
  }
});
async function saveLoan(){
  // Prevenir múltiples clics
  if(isSubmitting){
    toast('Por favor espera a que termine el proceso','info');
    return;
  }
  
  const equipo_id=parseInt($('lEq').value);
  const usuario_id=parseInt($('lUsr').value);
  const fecha_prestamo=$('lFecha').value;
  const fecha_devolucion_esperada=$('lDevol').value||null;
  const notas=$('lNotas').value;
  
  if(!equipo_id||!usuario_id||!fecha_prestamo){
    toast('Equipo, responsable y fecha son requeridos','err');
    return;
  }
  
  const data={
    equipo_id:equipo_id,
    usuario_id:usuario_id,
    fecha_prestamo:fecha_prestamo,
    fecha_devolucion_esperada:fecha_devolucion_esperada,
    notas:notas
  };
  
  // Establecer flag y deshabilitar botón
  isSubmitting=true;
  const btn=$('saveLoanBtn');
  btn.disabled=true;
  const btnText=editLoanId?'Actualizando...':'Registrando...';
  btn.textContent=btnText;
  
  try{
    const res=editLoanId?await api('/api/prestamos/'+editLoanId,'PUT',data):await api('/api/prestamos','POST',data);
    
    if(res.error){
      toast(res.error,'err');
      isSubmitting=false;
      btn.disabled=false;
      btn.textContent=editLoanId?'Actualizar':'Registrar préstamo';
      return;
    }
    
    // Obtener el ID del préstamo
    let loanId=res.id||editLoanId;
    
    if(!loanId){
      toast('Error: No se pudo obtener el ID del préstamo','err');
      isSubmitting=false;
      btn.disabled=false;
      btn.textContent=editLoanId?'Actualizar':'Registrar préstamo';
      return;
    }
    
    close('ovLoan');
    await _refreshLoans();DASH=computeDash();
    renderLoan();
    renderDashboard();
    toast(editLoanId?'Préstamo actualizado ✅':'Préstamo registrado ✅','ok');
    editLoanId=null;
    
    // Reiniciar estado
    isSubmitting=false;
    btn.disabled=false;
    btn.textContent='Registrar préstamo';
    
    // Mostrar modal para compartir link de firma solo si es nuevo préstamo
    if(!editLoanId){
      setTimeout(()=>{
        showSignatureLinkModal(loanId);
      },500);
    }
  }catch(e){
    toast('Error al registrar: '+e.message,'err');
    isSubmitting=false;
    btn.disabled=false;
    btn.textContent=editLoanId?'Actualizar':'Registrar préstamo';
  }
}
function viewLoanDocuments(id){
  const loan=LOANS.find(l=>l.id===id);
  if(!loan){toast('Préstamo no encontrado','err');return}
  
  let html=`<div style="margin-bottom:20px"><h3>${loan.equipo_nombre}</h3><p style="color:var(--text3);font-size:12px">${loan.usuario_nombre} — ${fmtDate(loan.fecha_prestamo)}</p></div>`;
  
  // ═══════════════════════════════════════════════════════════════
  // DOCUMENTOS DE FIRMA INICIAL
  // ═══════════════════════════════════════════════════════════════
  
  // Mostrar firma inicial
  if(loan.firma_url){
    html+=`<div style="margin-bottom:20px">
      <div class="card-title">✍️ Firma Digital (Préstamo)</div>
      <div style="border:1px solid var(--border);border-radius:8px;padding:12px;margin-top:8px;background:var(--surface2)">
        <img src="${loan.firma_url}" style="max-width:100%;height:auto;border-radius:6px;background:white;padding:8px" onerror="this.style.display='none';" onload="this.style.display='block'">
      </div>
    </div>`;
  }
  
  // Mostrar imágenes iniciales
  if(loan.imagen1_url||loan.imagen2_url){
    html+=`<div style="margin-bottom:20px"><div class="card-title">📷 Fotos (Recepción del Equipo)</div><div class="img-grid">`;
    
    if(loan.imagen1_url){
      html+=`<div style="border:1px solid var(--border);border-radius:8px;overflow:hidden;background:var(--surface2)">
        <img src="${loan.imagen1_url}" style="width:100%;height:150px;object-fit:cover" onerror="this.style.display='none';" onload="this.style.display='block'">
        <div style="padding:8px;background:var(--surface2);font-size:11px;color:var(--text3)">Foto 1: Recepción</div>
      </div>`;
    }
    
    if(loan.imagen2_url){
      html+=`<div style="border:1px solid var(--border);border-radius:8px;overflow:hidden;background:var(--surface2)">
        <img src="${loan.imagen2_url}" style="width:100%;height:150px;object-fit:cover" onerror="this.style.display='none';" onload="this.style.display='block'">
        <div style="padding:8px;background:var(--surface2);font-size:11px;color:var(--text3)">Foto 2: Verificación</div>
      </div>`;
    }
    
    html+=`</div></div>`;
  }
  
  // ═══════════════════════════════════════════════════════════════
  // DOCUMENTOS DE FIRMA DEVOLUCIÓN (si existen)
  // ═══════════════════════════════════════════════════════════════
  
  // Mostrar firma de devolución
  if(loan.firma_devolucion_url){
    html+=`<div style="margin-bottom:20px">
      <div class="card-title">✍️ Firma Digital (Devolución)</div>
      <div style="border:1px solid var(--border);border-radius:8px;padding:12px;margin-top:8px;background:var(--surface2)">
        <img src="${loan.firma_devolucion_url}" style="max-width:100%;height:auto;border-radius:6px;background:white;padding:8px" onerror="this.style.display='none';" onload="this.style.display='block'">
      </div>
    </div>`;
  }
  
  // Mostrar imágenes de devolución
  if(loan.imagen1_devolucion_url||loan.imagen2_devolucion_url){
    html+=`<div style="margin-bottom:20px"><div class="card-title">📷 Fotos (Devolución del Equipo)</div><div class="img-grid">`;
    
    if(loan.imagen1_devolucion_url){
      html+=`<div style="border:1px solid var(--border);border-radius:8px;overflow:hidden;background:var(--surface2)">
        <img src="${loan.imagen1_devolucion_url}" style="width:100%;height:150px;object-fit:cover" onerror="this.style.display='none';" onload="this.style.display='block'">
        <div style="padding:8px;background:var(--surface2);font-size:11px;color:var(--text3)">Foto 1: Estado devolución</div>
      </div>`;
    }
    
    if(loan.imagen2_devolucion_url){
      html+=`<div style="border:1px solid var(--border);border-radius:8px;overflow:hidden;background:var(--surface2)">
        <img src="${loan.imagen2_devolucion_url}" style="width:100%;height:150px;object-fit:cover" onerror="this.style.display='none';" onload="this.style.display='block'">
        <div style="padding:8px;background:var(--surface2);font-size:11px;color:var(--text3)">Foto 2: Confirmación</div>
      </div>`;
    }
    
    html+=`</div></div>`;
  }
  
  // Si no hay documentos
  if(!loan.firma_url&&!loan.imagen1_url&&!loan.imagen2_url&&!loan.firma_devolucion_url&&!loan.imagen1_devolucion_url&&!loan.imagen2_devolucion_url){
    html+=`<div style="padding:20px;text-align:center;color:var(--text3)"><p>Sin documentos registrados aún</p></div>`;
  }
  
  $('loanDocsContent').innerHTML=html;
  open('ovLoanDocs');
}

async function viewLoanDetails(id){
  try{
    const loan=await api(`/api/prestamos/${id}/detalle`);
    if(loan.error){toast(loan.error,'err');return}
    
    // Encabezado
    let html=`<div style="margin-bottom:24px">
      <h2 style="margin-bottom:8px">${loan.equipo?.nombre||loan.equipo_nombre||'Equipo'}</h2>
      <p style="color:var(--text3);font-size:13px">Responsable: ${loan.usuario?.nombre||loan.usuario_nombre||'Usuario'}</p>
    </div>`;
    
    // Timeline si existe
    if(loan.timeline && loan.timeline.length > 0){
      html+=`<div class="card" style="margin-bottom:16px">
        <div class="card-title">📅 Historial de Estados</div>
        <div style="margin-top:16px">`;
      
      loan.timeline.forEach((item,idx)=>{
        const isLast=idx===loan.timeline.length-1;
        const color=item.completado?'var(--green)':'var(--amber)';
        html+=`<div style="display:flex;position:relative;margin-bottom:24px">
          <div style="width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;background:${color};color:white">${item.icono}</div>
          <div style="margin-left:16px;flex:1">
            <div style="font-weight:600;color:var(--text);margin-bottom:4px">${item.titulo}</div>
            <div style="font-size:13px;color:var(--text2)">📅 ${item.fecha}</div>
            <div style="font-size:11px;color:${color};margin-top:4px;font-weight:600">${item.completado?'✅ Completado':'⏳ Pendiente'}</div>
          </div>
          ${!isLast?`<div style="position:absolute;left:19px;top:40px;width:2px;height:25px;background:var(--border)"></div>`:''}
        </div>`;
      });
      
      html+=`</div></div>`;
    }
    
    // Documentos firmados
    if(loan.firma_url || loan.imagen1_url || loan.imagen2_url){
      html+=`<div class="card" style="margin-bottom:16px">
        <div class="card-title">📄 Firma Inicial + Fotos</div>
        <div class="img-grid-3">`;
      
      if(loan.firma_url){
        html+=`<div style="border:1px solid var(--border);border-radius:6px;overflow:hidden">
          <img src="${loan.firma_url}" style="width:100%;height:80px;object-fit:cover;background:var(--surface2)">
          <div style="padding:8px;background:var(--surface2);text-align:center;font-weight:600">✍️ Firma</div>
        </div>`;
      }
      
      if(loan.imagen1_url){
        html+=`<div style="border:1px solid var(--border);border-radius:6px;overflow:hidden">
          <img src="${loan.imagen1_url}" style="width:100%;height:80px;object-fit:cover">
          <div style="padding:8px;background:var(--surface2);text-align:center;font-weight:600">📷 Foto 1</div>
        </div>`;
      }
      
      if(loan.imagen2_url){
        html+=`<div style="border:1px solid var(--border);border-radius:6px;overflow:hidden">
          <img src="${loan.imagen2_url}" style="width:100%;height:80px;object-fit:cover">
          <div style="padding:8px;background:var(--surface2);text-align:center;font-weight:600">📷 Foto 2</div>
        </div>`;
      }
      
      html+=`</div></div>`;
    }
    
    // Documentos de devolución
    if(loan.firma_devolucion_url || loan.imagen1_devolucion_url || loan.imagen2_devolucion_url){
      html+=`<div class="card">
        <div class="card-title">📄 Firma Devolución + Fotos</div>
        <div class="img-grid-3">`;
      
      if(loan.firma_devolucion_url){
        html+=`<div style="border:1px solid var(--border);border-radius:6px;overflow:hidden">
          <img src="${loan.firma_devolucion_url}" style="width:100%;height:80px;object-fit:cover;background:var(--surface2)">
          <div style="padding:8px;background:var(--surface2);text-align:center;font-weight:600">✍️ Firma Dev.</div>
        </div>`;
      }
      
      if(loan.imagen1_devolucion_url){
        html+=`<div style="border:1px solid var(--border);border-radius:6px;overflow:hidden">
          <img src="${loan.imagen1_devolucion_url}" style="width:100%;height:80px;object-fit:cover">
          <div style="padding:8px;background:var(--surface2);text-align:center;font-weight:600">📷 Foto 1 Dev.</div>
        </div>`;
      }
      
      if(loan.imagen2_devolucion_url){
        html+=`<div style="border:1px solid var(--border);border-radius:6px;overflow:hidden">
          <img src="${loan.imagen2_devolucion_url}" style="width:100%;height:80px;object-fit:cover">
          <div style="padding:8px;background:var(--surface2);text-align:center;font-weight:600">📷 Foto 2 Dev.</div>
        </div>`;
      }
      
      html+=`</div></div>`;
    }
    
    $('loanDetailsContent').innerHTML=html;
    open('ovLoanDetails');
  }catch(e){
    toast('Error al cargar detalles: '+e.message,'err');
  }
}

async function returnLoan(id){
  if(!confirm('¿Confirmar devolución del equipo?\n\nSe enviará un link al usuario para que firme la devolución'))return;
  showReturnLinkModal(id);
}
async function delLoan(id){
  if(!confirm('¿Eliminar este préstamo?'))return;
  await api('/api/prestamos/'+id,'DELETE');await _refreshLoans();DASH=computeDash();renderLoan();renderDashboard();toast('Préstamo eliminado','info');
}

/* ════════════════════════════════════════════════════
   CALENDARIO
════════════════════════════════════════════════════ */
function _computeCalEvents(){
  const events=[];
  for(const m of MANTS){
    if(!m.proxima_revision)continue;
    const tipo=m.tipo||'';
    events.push({date:m.proxima_revision,type:'mantenimiento',title:m.equipo_nombre||'Equipo desconocido',sub:`${tipo.charAt(0).toUpperCase()+tipo.slice(1)} · ${m.equipo_tipo||''}`,id:m.id,estado:m.estado,descripcion:m.descripcion||''});
  }
  for(const p of LOANS){
    let lbl='Para devolver';
    if(p.estado==='devuelto')lbl='Devuelto';
    else if(p.estado==='firmado')lbl='Pendiente firma';
    if(p.fecha_devolucion_esperada){
      events.push({date:p.fecha_devolucion_esperada,type:'prestamo',title:p.equipo_nombre||'Equipo desconocido',sub:`${lbl} · ${p.equipo_tipo||''}`,detail:`Responsable: ${p.usuario_nombre||'—'}`,id:p.id,estado:p.estado,notas:p.notas||''});
    }else if(p.fecha_prestamo){
      events.push({date:p.fecha_prestamo,type:'prestamo',title:p.equipo_nombre||'Equipo desconocido',sub:`Préstamo iniciado · ${p.equipo_tipo||''}`,detail:`Responsable: ${p.usuario_nombre||'—'}`,id:p.id,estado:p.estado,notas:p.notas||''});
    }
  }
  return events;
}

function renderCal(){
  const events=_computeCalEvents();
  const today=TODAY;
  const upcoming=events.filter(e=>e.date>=today);
  const overdue=events.filter(e=>e.date<today);

  function evHTML(e){
    const isOverdue=e.date<today;
    const cls=isOverdue?'cal-vencido':`cal-${e.type}`;
    const dl=daysLeft(e.date);
    return`<div class="cal-event ${cls}" onclick="nav('${e.type==='prestamo'?'prestamos':'mantenimientos'}')">
      <div class="cal-event-dot"></div>
      <div class="cal-event-body">
        <div class="cal-event-title">${e.type==='prestamo'?'🔁':'🔧'} ${e.title}</div>
        <div class="cal-event-sub">${e.sub}${e.detail?' · '+e.detail.slice(0,40):e.descripcion?' · '+e.descripcion.slice(0,40):e.notas?' · '+e.notas.slice(0,40):''}</div>
      </div>
      <div class="cal-event-date">${fmtDate(e.date)}${dl!==null&&!isOverdue?` (${dl}d)`:''}${isOverdue?' ⚠':''}</div>
    </div>`;
  }

  // Group by month
  function groupByMonth(evs){
    const months={};
    evs.forEach(e=>{const mo=e.date.slice(0,7);if(!months[mo])months[mo]=[];months[mo].push(e)});
    return months;
  }
  const monthNames=['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
  function renderMonths(evs){
    const g=groupByMonth(evs);
    return Object.keys(g).sort().map(mo=>{
      const[y,m]=mo.split('-');
      return`<div class="cal-month">${monthNames[parseInt(m)-1]} ${y}</div>`+g[mo].map(evHTML).join('');
    }).join('');
  }

  $('calUpcoming').innerHTML=upcoming.length?renderMonths(upcoming):'<div class="empty"><div class="empty-icon">✅</div><h3>Sin eventos próximos</h3><p>Todo al día</p></div>';
  $('calOverdue').innerHTML=overdue.length?overdue.map(evHTML).join(''):'<div class="empty"><div class="empty-icon">🎉</div><h3>Sin vencidos</h3><p>Excelente gestión</p></div>';
}

/* ════════════════════════════════════════════════════
   REPORTES
════════════════════════════════════════════════════ */
function renderReportes(){
  const totalValor=EQ.reduce((a,e)=>a+(e.valor||0),0);
  const byTipo={};EQ.forEach(e=>{const tipoName=e.tipo_nombre||e.tipo||'Sin tipo';byTipo[tipoName]=(byTipo[tipoName]||0)+1});
  const sorted=Object.entries(byTipo).sort((a,b)=>b[1]-a[1]);
  const totalMantCost=MANTS.reduce((a,m)=>a+(m.costo||0),0);

  $('reportesContent').innerHTML=`
    <div class="stats-row" style="margin-bottom:22px">
      <div class="stat-card" style="--accent-color:var(--blue)"><div class="glow-dot"></div>
        <div class="stat-label">Valor total inventario</div>
        <div class="stat-value" style="color:var(--blue);font-size:26px">$${(totalValor/1000000).toFixed(1)}M</div>
        <div class="stat-sub">${Number(totalValor).toLocaleString('es-CO')} COP</div>
      </div>
      <div class="stat-card" style="--accent-color:var(--green)"><div class="glow-dot" style="background:var(--green)"></div>
        <div class="stat-label">Equipos en buen estado</div>
        <div class="stat-value" style="color:var(--green)">${EQ.filter(e=>e.estado==='bueno').length}</div>
        <div class="stat-sub">${EQ.length?Math.round(EQ.filter(e=>e.estado==='bueno').length/EQ.length*100):0}% del total</div>
      </div>
      <div class="stat-card" style="--accent-color:var(--amber)"><div class="glow-dot" style="background:var(--amber)"></div>
        <div class="stat-label">Costo en mantenimientos</div>
        <div class="stat-value" style="color:var(--amber);font-size:26px">$${(totalMantCost/1000).toFixed(0)}K</div>
        <div class="stat-sub">${MANTS.length} mantenimiento(s) histórico(s)</div>
      </div>
      <div class="stat-card" style="--accent-color:var(--violet)"><div class="glow-dot" style="background:var(--violet)"></div>
        <div class="stat-label">Tipos de equipos</div>
        <div class="stat-value" style="color:var(--violet)">${Object.keys(byTipo).length}</div>
        <div class="stat-sub">Categorías diferentes</div>
      </div>
    </div>
    <div class="rep-grid">
      <div class="card">
        <div class="card-header"><div class="card-title">Distribución por tipo</div></div>
        <div class="card-body card-body-scrollable">${sorted.map(([t,c])=>`
          <div style="display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid var(--border)">
            <div style="display:flex;align-items:center;gap:8px">${TIPO_ICON[t]||'📦'} <span style="font-size:13px">${t}</span></div>
            <div style="display:flex;align-items:center;gap:10px">
              <div style="width:100px;height:5px;background:var(--surface3);border-radius:3px;overflow:hidden">
                <div style="width:${Math.round(c/EQ.length*100)}%;height:100%;background:var(--blue);border-radius:3px"></div>
              </div>
              <span style="font-family:var(--font-d);font-weight:700;color:var(--text);min-width:24px;text-align:right">${c}</span>
            </div>
          </div>`).join('')}
        </div>
      </div>
      <div class="card">
        <div class="card-header"><div class="card-title">Últimos préstamos</div></div>
        <div class="card-body">${LOANS.slice(0,8).map(p=>`
          <div style="display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid var(--border)">
            <div><div style="font-size:13px;font-weight:600;color:var(--text)">${p.equipo_nombre}</div>
            <div style="font-size:11px;color:var(--text3)">${p.usuario_nombre}</div></div>
            <span class="bs ${bsClass(p.estado)}">${bsLabel(p.estado)}</span>
          </div>`).join('')||'<div class="empty"><p>Sin préstamos</p></div>'}
        </div>
      </div>
    </div>`;
}

/* ════════════════════════════════════════════════════
   GLOBAL SEARCH
════════════════════════════════════════════════════ */
/* ════════════════════════════════════════════════════
   MODAL CLOSE ON BACKDROP
════════════════════════════════════════════════════ */
document.querySelectorAll('.overlay').forEach(ov=>{
  ov.addEventListener('click',e=>{if(e.target===ov)ov.classList.remove('open')});
});

// Attach close handlers to all close buttons
document.querySelectorAll('.m-close').forEach(btn=>{
  btn.addEventListener('click',e=>{
    e.preventDefault();
    e.stopPropagation();
    const overlay=btn.closest('.overlay');
    if(overlay)overlay.classList.remove('open');
  });
});

// Attach close handlers to all Cancelar buttons
document.querySelectorAll('.modal-body .btn-ghost').forEach(btn=>{
  if(btn.textContent.trim()==='Cancelar'){
    btn.addEventListener('click',e=>{
      e.preventDefault();
      e.stopPropagation();
      const overlay=btn.closest('.overlay');
      if(overlay)overlay.classList.remove('open');
    });
  }
});

// Attach close handlers to Listo buttons (ovSignLink, ovReturnLink)
// Bug: onclick="close(...)" en inline handlers resuelve document.close(), no la función custom.
// Los botones X y Cancelar tienen addEventListener como fallback; Listo no lo tenía.
document.querySelectorAll('.modal-body .btn-primary').forEach(btn=>{
  if(btn.textContent.trim().includes('Listo')){
    btn.addEventListener('click',e=>{
      e.preventDefault();
      e.stopPropagation();
      const overlay=btn.closest('.overlay');
      if(overlay)overlay.classList.remove('open');
    });
  }
});

// Override open for hoja de vida add event button
document.querySelectorAll('[onclick="open(\'ovAddHV\')"]').forEach(b=>{
  b.setAttribute('onclick','open_ovAddHV()');
});

/* ════════════════════════════════════════════════════
   GENERA LINKS PÚBLICOS PARA FIRMA
════════════════════════════════════════════════════ */

function showSignatureLinkModal(loanId){
  if(!loanId){
    toast('Error: ID de préstamo inválido','err');
    return;
  }
  
  try{
    const sigUrl=`${window.location.origin}/firma/${loanId}`;
    const urlInput=$('sigLinkUrl');
    if(urlInput){
      urlInput.value=sigUrl;
    }
    const qrDiv=$('sigLinkQR');
    if(qrDiv){
      qrDiv.innerHTML='';
    }
    open('ovSignLink');
  }catch(e){
    toast('Error al preparar link de firma: '+e.message,'err');
  }
}

function showReturnLinkModal(loanId){
  if(!loanId){
    toast('Error: ID de préstamo inválido','err');
    return;
  }
  
  try{
    const returnUrl=`${window.location.origin}/firma/${loanId}?tipo=devolucion`;
    const urlInput=$('returnLinkUrl');
    if(urlInput){
      urlInput.value=returnUrl;
    }
    open('ovReturnLink');
  }catch(e){
    toast('Error al preparar link de devolución: '+e.message,'err');
  }
}

function copySignatureLink(){
  const url=$('sigLinkUrl').value;
  navigator.clipboard.writeText(url).then(()=>{
    toast('Link copiado al portapapeles ✅','ok');
  }).catch(err=>{
    toast('Error al copiar','err');
  });
}

function copyReturnLink(){
  const url=$('returnLinkUrl').value;
  navigator.clipboard.writeText(url).then(()=>{
    toast('Link copiado al portapapeles ✅','ok');
  }).catch(err=>{
    toast('Error al copiar al portapapeles','err');
  });
}

function copyDesasignLink(){
  const url=$('desasignLink').value;
  navigator.clipboard.writeText(url).then(()=>{
    toast('Link copiado al portapapeles ✅','ok');
  }).catch(err=>{
    toast('Error al copiar al portapapeles','err');
  });
}

function toggleUserMenu(){
  const menu=$('userMenu');
  menu.style.display=menu.style.display==='none'?'block':'none';
  document.addEventListener('click',function closeUserMenu(e){
    if(!e.target.closest('.user-pill')){
      menu.style.display='none';
      document.removeEventListener('click',closeUserMenu);
    }
  });
}

/* ════════════════════════════════════════════════════
   ASIGNACIONES DE EQUIPOS
════════════════════════════════════════════════════ */
let selectedEquiposAsignacion={}; // {equipo_id: true, ...}

async function loadAsignaciones(){
  try{
    const res=await api('/api/asignaciones-equipos','GET');
    ASIGNACIONES=Array.isArray(res)?res:[];
    actualizarFiltrosAsignaciones();
    renderAsignaciones();
  }catch(err){
    ASIGNACIONES=[];
  }
}

function renderAsignaciones(){
  const search=$('srchAsig')?.value||'';
  const variable=$('ftAsigVariable')?.value||'';
  const responsableFilter=parseInt($('ftAsigResponsableValue')?.value)||0;
  const equipoFilter=parseInt($('ftAsigEquipoValue')?.value)||0;
  const firmaFilter=$('ftAsigFirmaValue')?.value||'';
  const estadoFilter=$('ftAsigEstadoValue')?.value||'';
  const politicaFilter=$('ftAsigPoliticaValue')?.value||'';
  const fechaFilter=$('ftAsigFechaValue')?.value||'';
  
  // Búsqueda multi-campo en: equipo.nombre, equipo.serial, usuario.nombre, usuario.departamento
  let filtered=searchMultiField(ASIGNACIONES,search,SEARCH_FIELDS.asignaciones);
  
  // Filtros específicos
  filtered=filtered.filter(a=>{
    let matchesSpecificFilter=true;
    
    if(variable==='responsable'&&responsableFilter){
      matchesSpecificFilter=a.usuario_id===responsableFilter;
    }else if(variable==='equipo'&&equipoFilter){
      matchesSpecificFilter=a.equipo_id===equipoFilter;
    }else if(variable==='firma'&&firmaFilter){
      const tieneEnt=!!a.firma_entrada_url;
      matchesSpecificFilter=(firmaFilter==='pendiente'&&!tieneEnt)||(firmaFilter==='firmado'&&tieneEnt);
    }else if(variable==='estado'&&estadoFilter){
      matchesSpecificFilter=a.estado===estadoFilter;
    }else if(variable==='politica'&&politicaFilter){
      matchesSpecificFilter=(politicaFilter==='si'&&a.politica_aceptada)||(politicaFilter==='no'&&!a.politica_aceptada);
    }else if(variable==='fecha'&&fechaFilter){
      const asigDate=a.fecha_asignacion?new Date(a.fecha_asignacion).toISOString().split('T')[0]:'';
      matchesSpecificFilter=asigDate===fechaFilter;
    }
    
    return matchesSpecificFilter;
  });
  
  // Aplicar filtros avanzados anidables
  filtered=applyAdvancedFilters('asignaciones',filtered);
  
  const {data:pageData,totalPages,currentPage:cp}=paginateArray(filtered,'asignaciones');
  
  // Renderizar tabla
  const tbody=$('asigTbody');
  tbody.innerHTML=pageData.map(a=>{
    const eq=a.equipo||{};
    const usr=a.usuario||{};
    const fechaAsig=a.fecha_asignacion?new Date(a.fecha_asignacion).toLocaleDateString('es-ES'):'—';
    const tieneEntrada=!!a.firma_entrada_url;
    const tieneSalida=!!a.firma_salida_url;
    
    return `<tr>
      <td><strong>${eq.nombre||'—'}</strong><br><small style="color:var(--text3)">${eq.serial||''}</small></td>
      <td>${usr.nombre||'—'}<br><small style="color:var(--text3)">${usr.departamento||''}</small></td>
      <td>${fechaAsig}</td>
      <td><span class="badge">${a.estado_equipo_entrada||'—'}</span></td>
      <td>${tieneEntrada?'✅ Firmada':'⏳ Pendiente'}</td>
      <td><span style="font-weight:600;color:${a.politica_aceptada?'var(--green)':'var(--text3)'}">${a.politica_aceptada?'✅ Aceptó':'⏳ Pendiente'}</span></td>
      <td><span class="badge ${a.estado==='abierta'?'badge-blue':'badge-green'}">${a.estado}</span></td>
      <td style="display:flex;gap:4px;flex-wrap:wrap">
        ${!tieneEntrada?`<button class="btn btn-primary btn-sm" onclick="generateSignLink(${a.id}, 'entrada')">Firmar Entrada</button>`:''}
        ${tieneEntrada?`<button class="btn btn-info btn-sm" onclick="viewSignature(${a.id}, 'entrada')">👁️ Ver Firma</button>`:''}
        ${tieneEntrada&&!tieneSalida?`<button class="btn btn-teal btn-sm" onclick="generateSignLink(${a.id}, 'salida')">Devolver</button>`:''}
        ${tieneSalida?`<button class="btn btn-secondary btn-sm" onclick="viewSignature(${a.id}, 'salida')">👁️ Ver Salida</button>`:''}
        ${a.estado!=='desasignada'?`<button class="btn btn-danger btn-sm" onclick="deleteAsignacion(${a.id})" style="background:var(--error);color:white">Eliminar</button>`:''}
      </td>

    </tr>`;
  }).join('');
  
  // Renderizar paginación
  $('asigPaginationContainer').innerHTML=createPaginationControls(cp,totalPages,'asignaciones');
  
  // Actualizar contador
  $('asigCount').textContent=`${filtered.length} de ${ASIGNACIONES.length} asignación(es)`;
}

function viewSignature(asigId, tipo){
  const asig = ASIGNACIONES.find(a => a.id === asigId);
  if (!asig) return;
  
  const firmaUrl = tipo === 'entrada' ? asig.firma_entrada_url : asig.firma_salida_url;
  if (!firmaUrl) {
    toast('No hay firma disponible', 'error');
    return;
  }
  
  const titulo = tipo === 'entrada' ? 'Firma de Entrada' : 'Firma de Salida';
  const container = document.createElement('div');
  container.id = 'firmaViewerContainer';
  container.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;display:flex;align-items:center;justify-content:center;z-index:9999;background:rgba(0,0,0,0.7)';
  container.innerHTML = `
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:0;max-width:600px;width:90%;max-height:80vh;display:flex;flex-direction:column">
      <div style="padding:16px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">
        <h3 style="margin:0">${titulo}</h3>
        <button onclick="document.getElementById('firmaViewerContainer').remove()" style="background:none;border:none;font-size:24px;cursor:pointer;padding:0">✕</button>
      </div>
      <div style="flex:1;overflow:auto;padding:16px;text-align:center">
        <img src="${firmaUrl}" style="max-width:100%;max-height:100%;object-fit:contain;border:1px solid var(--border);border-radius:4px">
      </div>
      <div style="padding:12px;border-top:1px solid var(--border);display:flex;gap:8px;justify-content:flex-end">
        <a href="${firmaUrl}" target="_blank" class="btn btn-primary btn-sm">📥 Descargar</a>
        <button class="btn btn-ghost btn-sm" onclick="document.getElementById('firmaViewerContainer').remove()">Cerrar</button>
      </div>
    </div>
  `;
  document.body.appendChild(container);
}

function actualizarFiltrosAsignaciones(){
  // Llenar filtro de responsables
  const ftRespValue=$('ftAsigResponsableValue');
  if(ftRespValue){
    while(ftRespValue.options.length>1) ftRespValue.removeChild(ftRespValue.lastChild);
    
    const responsablesIds=new Set(ASIGNACIONES.map(a=>a.usuario_id).filter(Boolean));
    const responsables=USR.filter(u=>responsablesIds.has(u.id)).sort((a,b)=>a.nombre.localeCompare(b.nombre));
    
    responsables.forEach(u=>{
      const opt=document.createElement('option');
      opt.value=u.id;
      opt.textContent=u.nombre;
      ftRespValue.appendChild(opt);
    });
  }
  
  // Llenar filtro de equipos
  const ftEqValue=$('ftAsigEquipoValue');
  if(ftEqValue){
    while(ftEqValue.options.length>1) ftEqValue.removeChild(ftEqValue.lastChild);
    
    const equiposIds=new Set(ASIGNACIONES.map(a=>a.equipo_id).filter(Boolean));
    const equipos=EQ.filter(e=>equiposIds.has(e.id)).sort((a,b)=>a.nombre.localeCompare(b.nombre));
    
    equipos.forEach(e=>{
      const opt=document.createElement('option');
      opt.value=e.id;
      opt.textContent=e.nombre+' ('+( e.serial||'—')+')';
      ftEqValue.appendChild(opt);
    });
  }
}

function updateAsigFilterUI(){
  const variable=$('ftAsigVariable').value;
  const container=$('asigFilterValueContainer');
  const btnClear=$('btClearAsigFilter');
  
  // Ocultar todos los inputs
  $('ftAsigResponsableValue').style.display='none';
  $('ftAsigEquipoValue').style.display='none';
  $('ftAsigFirmaValue').style.display='none';
  $('ftAsigEstadoValue').style.display='none';
  $('ftAsigPoliticaValue').style.display='none';
  $('ftAsigFechaValue').style.display='none';
  
  if(!variable){
    container.style.display='none';
    btnClear.style.display='none';
  }else{
    container.style.display='flex';
    btnClear.style.display='block';
    
    // Mostrar solo el input correspondiente
    if(variable==='responsable'){
      $('ftAsigResponsableValue').style.display='block';
    }else if(variable==='equipo'){
      $('ftAsigEquipoValue').style.display='block';
    }else if(variable==='firma'){
      $('ftAsigFirmaValue').style.display='block';
    }else if(variable==='estado'){
      $('ftAsigEstadoValue').style.display='block';
    }else if(variable==='politica'){
      $('ftAsigPoliticaValue').style.display='block';
    }else if(variable==='fecha'){
      $('ftAsigFechaValue').style.display='block';
    }
  }
}

function clearAsigFilters(){
  $('ftAsigVariable').value='';
  $('ftAsigResponsableValue').value='';
  $('ftAsigEquipoValue').value='';
  $('ftAsigFirmaValue').value='';
  $('ftAsigEstadoValue').value='';
  $('ftAsigPoliticaValue').value='';
  $('ftAsigFechaValue').value='';
  updateAsigFilterUI();
  currentPage['asignaciones']=1;
  renderAsignaciones();
}

function openAsignacionModal(){
  selectedEquiposAsignacion={};
  $('asigModalTitle').textContent='Nueva Asignación de Equipos';
  $('asigModalSub').textContent='Selecciona uno o varios equipos para asignar';
  
  // Llenar select de usuarios activos
  $('aUsr').innerHTML='<option value="">Seleccionar responsable…</option>'+USR.filter(u=>u.estado==='activo').map(u=>`<option value="${u.id}">${u.nombre} — ${u.departamento||''}</option>`).join('');
  
  // Limpiar búsqueda y campos
  $('aEqSearch').value='';
  $('aEstado').value='bueno';
  $('aNotas').value='';
  
  // Renderizar equipos disponibles
  filterEquiposAsignacion();
  updateAEqCount();
  
  open('ovAsignacion');
}

function updateAEqCount(){
  const count=Object.values(selectedEquiposAsignacion).filter(Boolean).length;
  $('aEqCount').textContent=count;
}

function toggleEquipoAsignacion(equipoId){
  selectedEquiposAsignacion[equipoId]=!selectedEquiposAsignacion[equipoId];
  const checkbox=document.querySelector(`input[data-eq-id="${equipoId}"]`);
  if(checkbox)checkbox.checked=selectedEquiposAsignacion[equipoId];
  updateAEqCount();
}

function filterEquiposAsignacion(){
  const q=$('aEqSearch').value.toLowerCase();
  const list=$('aEqList');
  
  // Excluir equipos que tienen asignación abierta Y responsable activo.
  // Si usuario_id es null, la asignación abierta es huérfana y el equipo debe poder reasignarse.
  const asignadosConResponsable=new Set(
    ASIGNACIONES.filter(a=>a.estado==='abierta').map(a=>a.equipo_id)
      .filter(eqId=>{const eq=EQ.find(e=>e.id===eqId);return eq&&eq.usuario_id;})
  );
  const equiposDisp=EQ.filter(e=>{
    const disp=(e.disponibilidad||'').toLowerCase();
    return !asignadosConResponsable.has(e.id)&&!disp.includes('retirado')&&!disp.includes('baja');
  });
  
  const filtered=equiposDisp.filter(e=>
    !q||e.nombre.toLowerCase().includes(q)||
    (e.marca||'').toLowerCase().includes(q)||
    (e.serial||'').toLowerCase().includes(q)||
    (e.tipo_nombre||'').toLowerCase().includes(q)
  );
  
  if(filtered.length===0){
    list.innerHTML='<div style="padding:12px;color:var(--text3);font-size:12px;text-align:center">No hay equipos disponibles</div>';
  }else{
    list.innerHTML=filtered.map(e=>`
      <div style="padding:6px 8px;border-bottom:1px solid var(--border);display:flex;gap:8px;align-items:center;cursor:pointer;transition:background 0.15s;background:${selectedEquiposAsignacion[e.id]?'var(--surface3)':'transparent'}" 
           onmouseover="this.style.background='var(--surface3)'" 
           onmouseout="this.style.background='${selectedEquiposAsignacion[e.id]?'var(--surface3)':'transparent'}'" 
           onclick="toggleEquipoAsignacion(${e.id})">
        <input type="checkbox" data-eq-id="${e.id}" ${selectedEquiposAsignacion[e.id]?'checked':''} style="cursor:pointer;margin:0;min-width:16px;width:16px;height:16px;flex-shrink:0">
        <div style="flex:1;min-width:0">
          <div style="font-size:12px;font-weight:600;color:var(--text);line-height:1.2">${e.nombre}</div>
          <div style="font-size:10px;color:var(--text3);line-height:1.2">${e.serial?'Serial: '+e.serial:''} • ${e.tipo_nombre||''}</div>
        </div>
      </div>
    `).join('');
  }
}

function selectEquipoAsignacion(id,nombre){
  // Esta función ya no se usa (reemplazada por toggleEquipoAsignacion)
}

async function saveAsignacion(){
  if(isSubmitting){
    toast('Por favor espera…','info');
    return;
  }
  
  const usuario_id_str=$('aUsr').value;
  const estado_equipo=$('aEstado').value||'bueno';
  const notas=$('aNotas').value||'';
  
  // Validar usuario
  const usuario_id=parseInt(usuario_id_str,10);
  if(!usuario_id||isNaN(usuario_id)){
    toast('Selecciona un responsable','err');
    return;
  }
  
  // Obtener equipos seleccionados
  const equiposSeleccionados=Object.keys(selectedEquiposAsignacion).filter(id=>selectedEquiposAsignacion[id]).map(id=>parseInt(id,10));
  
  if(equiposSeleccionados.length===0){
    toast('Selecciona al menos un equipo','err');
    return;
  }
  
  isSubmitting=true;
  $('saveAsigBtn').disabled=true;
  $('saveAsigBtn').textContent=`Creando ${equiposSeleccionados.length} asignación(nes)…`;
  
  try{
    let successCount=0;
    let errorCount=0;
    const createdAsignacionIds=[];
    
    // Crear una asignación por cada equipo
    for(const equipo_id of equiposSeleccionados){
      const payload={
        equipo_id:equipo_id,
        usuario_id:usuario_id,
        estado_equipo:estado_equipo,
        notas:notas
      };
      
      const res=await api('/api/asignaciones-equipos','POST',payload);
      
      if(res.id){
        successCount++;
        createdAsignacionIds.push(res.id);
      }else{
        errorCount++;
      }
    }
    
    // Mostrar resultado
    if(successCount>0){
      close('ovAsignacion');
      toast(`✅ ${successCount} asignación(nes) creada(s) exitosamente${errorCount>0?' - '+errorCount+' errores':''} - Próximo paso: firmar entrada ✍️`,'ok');
      await Promise.all([_refreshAsigs(),_refreshEq()]);DASH=computeDash();
      renderAsignaciones();
      renderDashboard();
    }else{
      toast(`❌ No se pudo crear ninguna asignación`,'err');
    }
  }catch(err){
    toast(err.message||'Error creando asignaciones','err');
  }finally{
    isSubmitting=false;
    $('saveAsigBtn').disabled=false;
    $('saveAsigBtn').textContent='Crear asignaciones';
  }
}



function generateSignLink(asigId, tipo){
  if(!asigId) return;
  
  // Construir URL: /firma/{id}?doc=asignacion&tipo=entrada|salida
  const url = `${window.location.origin}/firma/${asigId}?doc=asignacion&tipo=${tipo}`;
  
  // Copiar al portapapeles
  navigator.clipboard.writeText(url).then(() => {
    toast(`Link de firma copiado al portapapeles`, 'ok');
  }).catch(err => {
    toast('Error al copiar link', 'err');
  });
}

function viewAsignacionDetail(asigId){
  const asig=ASIGNACIONES.find(a=>a.id===asigId);
  if(!asig){
    toast('Asignación no encontrada','error');
    return;
  }
  
  const eq=asig.equipo||{};
  const usr=asig.usuario||{};
  
  // Formatear fechas
  const fecAsig = asig.fecha_asignacion ? new Date(asig.fecha_asignacion).toLocaleDateString('es-ES', {year:'numeric', month:'long', day:'numeric', hour:'2-digit', minute:'2-digit'}) : '—';
  const fecDesasig = asig.fecha_firma_desasignacion ? new Date(asig.fecha_firma_desasignacion).toLocaleDateString('es-ES', {year:'numeric', month:'long', day:'numeric', hour:'2-digit', minute:'2-digit'}) : '—';
  const fecFirmaEntrada = asig.fecha_firma_entrada ? new Date(asig.fecha_firma_entrada).toLocaleDateString('es-ES', {year:'numeric', month:'long', day:'numeric', hour:'2-digit', minute:'2-digit'}) : '—';
  const fecFirmaSalida = asig.fecha_firma_salida ? new Date(asig.fecha_firma_salida).toLocaleDateString('es-ES', {year:'numeric', month:'long', day:'numeric', hour:'2-digit', minute:'2-digit'}) : '—';
  
  let html = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
      <div>
        <strong style="color:var(--text3);font-size:11px;text-transform:uppercase">Equipo</strong>
        <div style="margin-top:4px;font-weight:600">${eq.nombre||'—'}</div>
      </div>
      <div>
        <strong style="color:var(--text3);font-size:11px;text-transform:uppercase">Responsable</strong>
        <div style="margin-top:4px;font-weight:600">${usr.nombre||'—'}</div>
      </div>
      <div>
        <strong style="color:var(--text3);font-size:11px;text-transform:uppercase">📅 Fecha Asignación</strong>
        <div style="margin-top:4px">${fecAsig}</div>
      </div>
      <div>
        <strong style="color:var(--text3);font-size:11px;text-transform:uppercase">✍️ Firma Entrada</strong>
        <div style="margin-top:4px;color:${asig.fecha_firma_entrada?'var(--green)':'var(--text3)'};">${fecFirmaEntrada}</div>
      </div>
      <div>
        <strong style="color:var(--text3);font-size:11px;text-transform:uppercase">📤 Firma Salida</strong>
        <div style="margin-top:4px;color:${asig.fecha_firma_salida?'var(--green)':'var(--text3)'};">${fecFirmaSalida}</div>
      </div>
      <div>
        <strong style="color:var(--text3);font-size:11px;text-transform:uppercase">🔄 Desasignada</strong>
        <div style="margin-top:4px;color:${asig.fecha_firma_desasignacion?'var(--green)':'var(--amber)'};">${fecDesasig}</div>
      </div>
    </div>
    
    <div style="background:var(--surface2);padding:12px;border-radius:6px;margin-top:12px">
      <strong style="color:var(--text3);font-size:11px;text-transform:uppercase">Estado</strong>
      <div style="margin-top:8px">
        <span class="badge" style="background:${asig.estado==='desasignada'?'var(--red)':asig.estado==='cerrada'?'var(--amber)':'var(--green)'};color:white;padding:4px 8px;border-radius:4px">
          ${asig.estado==='desasignada'?'Desasignada':asig.estado==='cerrada'?'Cerrada':'Abierta'}
        </span>
      </div>
    </div>
  `;
  
  $('asignacionDetContent').innerHTML = html;
  open('ovAsignacionDet');
}



async function deleteAsignacion(asigId){
  if(!confirm('¿Eliminar esta asignación permanentemente? Se borrará el registro completo y todo su historial.'))return;
  
  try{
    const res=await fetch(`/api/asignaciones-equipos/${asigId}`,{
      method:'DELETE',
      credentials:'include'
    });
    
    if(res.ok){
      toast('✅ Asignación eliminada permanentemente del sistema','ok');
      await Promise.all([_refreshAsigs(),_refreshEq()]);DASH=computeDash();
      renderEq();
      renderAsignaciones();
    }else{
      const err=await res.json();
      toast(err.error||'Error al eliminar la asignación','err');
    }
  }catch(err){
    toast(err.message||'Error en la eliminación','err');
  }
}


function generateSignLink(asigId, tipo) {
  // Get the base URL
  const baseUrl = window.location.origin;
  
  // Generate the signature link
  const signLink = `${baseUrl}/firma/${asigId}?doc=asignacion&tipo=${tipo}`;
  
  // Copy to clipboard
  navigator.clipboard.writeText(signLink).then(() => {
    toast(`Link copiado: ${signLink}`, 'ok');
    
    // Show a dialog with the link
    const msg = `
Enlace de firma generado:

${signLink}

Envíalo a la persona para que firme la ${tipo === 'entrada' ? 'recepción' : 'devolución'} del equipo.

El link ya está en tu portapapeles.
    `;
    toast(msg, 'ok');
  }).catch(err => {
    toast('Error al copiar al portapapeles', 'err');
  });
}

async function unassignAsignacion(asigId){
  if(!confirm('Desasignar este equipo del responsable? Se generará un enlace de firma para confirmar la desasignación.'))return;
  
  try{
    // Obtener datos de la asignación para saber el equipo
    const asig = ASIGNACIONES.find(a => a.id === asigId);
    if(!asig){
      toast('Asignación no encontrada','err');
      return;
    }
    
    // Guardar el equipo_id para usarlo después
    window.equipoDesasignadoId = asig.equipo_id;
    
    // Mostrar modal con enlace de firma para desasignación
    const desasigUrl=`${window.location.origin}/firma/${asigId}?doc=asignacion&tipo=desasignacion`;
    const urlInput=$('desasignLink');
    if(urlInput){
      urlInput.value=desasigUrl;
    }
    open('ovDesasignLink');
  }catch(err){
    toast(err.message||'Error generando enlace de desasignación','err');
  }
}

async function completeDesasignAndAssign(){
  close('ovDesasignLink');
  
  // Mostrar feedback mientras se refrescan datos
  try {
    toast('🔄 Refrescando datos...', 'info');
    await Promise.all([_refreshAsigs(),_refreshEq()]);DASH=computeDash();
    
    // Abrir modal de nueva asignación
    openAsignacionModal();
    
    // Pre-seleccionar el equipo que se acaba de desasignar
    if(window.equipoDesasignadoId){
      selectedEquiposAsignacion[window.equipoDesasignadoId] = true;
      
      // Actualizar UI
      const checkbox = document.querySelector(`input[data-eq-id="${window.equipoDesasignadoId}"]`);
      if(checkbox) checkbox.checked = true;
      updateAEqCount();
      
      // Scroll al equipo seleccionado
      const equipoEl = document.querySelector(`input[data-eq-id="${window.equipoDesasignadoId}"]`);
      if(equipoEl) equipoEl.scrollIntoView({behavior: 'smooth', block: 'nearest'});
      
      // Limpiar la variable
      window.equipoDesasignadoId = null;
      
      toast('✅ Equipo disponible para reasignar', 'ok');
    }
  } catch(err) {
    toast('❌ Error al refrescar datos: ' + err.message, 'err');
  }
}

/* ════════════════════════════════════════════════════
   SCANNER QR / BARCODE
════════════════════════════════════════════════════ */
let _html5Scanner=null;

async function openScanner(){
  open('ovScanner');
  $('scanStatus').textContent='Iniciando cámara…';
  if(typeof Html5Qrcode==='undefined'){
    $('scanStatus').textContent='Librería de escáner no disponible';
    return;
  }
  // Esperar a que el modal sea visible antes de iniciar la cámara
  await new Promise(r=>setTimeout(r,200));
  _html5Scanner=new Html5Qrcode('scannerRegion');
  const _scanConfig={fps:25,qrbox:{width:240,height:90},experimentalFeatures:{useBarCodeDetectorIfSupported:true}};
  if(typeof Html5QrcodeSupportedFormats!=='undefined'){
    _scanConfig.formatsToSupport=[Html5QrcodeSupportedFormats.CODE_128,Html5QrcodeSupportedFormats.QR_CODE];
  }
  try{
    await _html5Scanner.start(
      {facingMode:'environment'},
      _scanConfig,
      (text)=>_onScanSuccess(text),
      ()=>{}
    );
    $('scanStatus').textContent='Apunta al código del equipo';
  }catch(err){
    $('scanStatus').textContent='Sin acceso a cámara: '+(err.message||err);
    _html5Scanner=null;
  }
}

async function closeScanner(){
  if(_html5Scanner){
    try{
      if(_html5Scanner.isScanning)await _html5Scanner.stop();
      _html5Scanner.clear();
    }catch{}
    _html5Scanner=null;
  }
  const region=$('scannerRegion');
  if(region)region.innerHTML='';
  $('scanStatus').textContent='';
  close('ovScanner');
}

function _onScanSuccess(text){
  closeScanner();
  try{
    let targetId=null;
    try{
      const url=new URL(text);
      const m=url.pathname.match(/\/equipo\/(\d+)/);
      if(m)targetId=parseInt(m[1]);
    }catch{
      if(/^\d+$/.test(text.trim()))targetId=parseInt(text.trim());
    }
    if(!targetId){toast('Código no reconocido como equipo','err');return;}
    nav('equipos');
    const eq=EQ.find(e=>e.id===targetId);
    if(eq){toast(`Equipo encontrado: ${eq.nombre}`,'ok');editEq(targetId);}
    else toast('Equipo no encontrado en inventario','err');
  }catch{
    toast('Error al procesar el código','err');
  }
}

/* ════════════════════════════════════════════════════
   ETIQUETAS
════════════════════════════════════════════════════ */
const LABELS_PER_PAGE=60;
let _labelsPage=0;

function getLabelLogoUrl(){return localStorage.getItem('label_logo_url')||'';}

function saveLabelLogo(){
  const url=($('labelLogoUrl').value||'').trim();
  if(url)localStorage.setItem('label_logo_url',url);
  else localStorage.removeItem('label_logo_url');
  renderEtiquetas();
  toast('Logo actualizado','ok');
}

function clearLabelLogo(){
  localStorage.removeItem('label_logo_url');
  const inp=$('labelLogoUrl');if(inp)inp.value='';
  const prev=$('labelLogoPreview');if(prev){prev.style.display='none';prev.src='';}
  renderEtiquetas();
}

function updateLabelLogoPreview(){
  const url=($('labelLogoUrl').value||'').trim();
  const prev=$('labelLogoPreview');
  if(!prev)return;
  if(url){prev.src=url;prev.style.display='block';}
  else{prev.style.display='none';prev.src='';}
}

function _labelCardHtml(eq,logoUrl){
  const serial=eq.serial||eq.serialno||'—';
  const logoHtml=logoUrl
    ?`<img src="${logoUrl}" class="label-logo-img" alt="" onerror="this.style.display='none'">`
    :`<div class="label-logo-empty"></div>`;
  return`<div class="label-card">
    <div class="label-left">${logoHtml}</div>
    <div class="label-right"><svg id="lqr-${eq.id}" class="label-bc"></svg><div class="label-serial">${serial}</div></div>
  </div>`;
}

function renderEtiquetas(){
  const grid=$('etiquetasGrid');
  const pag=$('etiquetasPagination');
  if(!grid)return;

  // Sincronizar campo de URL con localStorage
  const storedLogo=getLabelLogoUrl();
  const inp=$('labelLogoUrl');
  if(inp&&!inp.value&&storedLogo){inp.value=storedLogo;updateLabelLogoPreview();}

  if(!EQ.length){
    grid.innerHTML='<p style="color:var(--text3);text-align:center;padding:40px 0;grid-column:1/-1">No hay equipos cargados.</p>';
    if(pag)pag.innerHTML='';
    return;
  }
  const total=EQ.length;
  const totalPages=Math.ceil(total/LABELS_PER_PAGE);
  if(_labelsPage>=totalPages)_labelsPage=totalPages-1;
  if(_labelsPage<0)_labelsPage=0;
  const start=_labelsPage*LABELS_PER_PAGE;
  const pageEqs=EQ.slice(start,start+LABELS_PER_PAGE);

  grid.innerHTML=pageEqs.map(eq=>_labelCardHtml(eq,storedLogo)).join('');

  if(pag){
    pag.innerHTML=`
      <button class="btn btn-ghost btn-sm" onclick="_labelsNav(-1)" ${_labelsPage===0?'disabled':''}>← Anterior</button>
      <span style="font-size:13px;color:var(--text3)">Pág. ${_labelsPage+1}/${totalPages} &nbsp;·&nbsp; ${start+1}–${Math.min(start+LABELS_PER_PAGE,total)} de ${total}</span>
      <button class="btn btn-ghost btn-sm" onclick="_labelsNav(1)" ${_labelsPage>=totalPages-1?'disabled':''}>Siguiente →</button>`;
  }

  if(typeof JsBarcode==='undefined')return;
  pageEqs.forEach(eq=>{
    const el=$(`lqr-${eq.id}`);
    if(!el)return;
    try{JsBarcode(el,String(eq.id),{format:'CODE128',width:1.2,height:24,displayValue:false,margin:1});}catch{}
  });
}

function _labelsNav(dir){
  _labelsPage+=dir;
  renderEtiquetas();
  window.scrollTo(0,0);
}

function printEtiquetas(){
  if(typeof JsBarcode==='undefined'){toast('Librería barcode no disponible','err');return;}
  const start=_labelsPage*LABELS_PER_PAGE;
  const eqs=EQ.slice(start,start+LABELS_PER_PAGE);
  if(!eqs.length){toast('Sin etiquetas en esta página','err');return;}
  _printLabelPage(eqs);
}

const _LABEL_PRINT_CSS=`*{box-sizing:border-box;margin:0;padding:0}body{font-family:Arial,sans-serif;background:#fff}.pg{width:216mm;height:279mm;padding:5mm;display:grid;grid-template-columns:repeat(6,1fr);gap:1.5mm;align-content:space-between;page-break-after:always}.pg:last-child{page-break-after:avoid}.lc{border:1px solid #ccc;border-radius:2px;padding:1.5mm;display:flex;flex-direction:row;align-items:center;gap:1.5mm;overflow:hidden}.lft{flex-shrink:0;width:20%;display:flex;align-items:center;justify-content:center}.ll{max-width:100%;max-height:20px;object-fit:contain;display:block}.le{width:16px;height:16px;border:1px dashed #bbb;border-radius:2px}.lrt{flex:1;min-width:0;display:flex;flex-direction:column;gap:1px}.lb svg{width:100%!important;height:auto!important;display:block}.ls{font-size:9px;font-family:monospace;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#222}@page{size:letter;margin:0}`;

function _buildLabelPageHTML(eqs){
  const logoUrl=getLabelLogoUrl();
  const logoHtml=logoUrl?`<img src="${logoUrl}" class="ll" alt="">`:`<div class="le"></div>`;
  const getBC=(id)=>{
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.style.cssText='position:absolute;left:-9999px;top:-9999px';
    document.body.appendChild(svg);
    try{JsBarcode(svg,String(id),{format:'CODE128',width:1.0,height:22,displayValue:false,margin:1});}catch{}
    const xml=new XMLSerializer().serializeToString(svg);
    document.body.removeChild(svg);
    return xml;
  };
  return`<div class="pg">${eqs.map(eq=>`<div class="lc"><div class="lft">${logoHtml}</div><div class="lrt"><div class="lb">${getBC(eq.id)}</div><div class="ls">${eq.serial||eq.serialno||'—'}</div></div></div>`).join('')}</div>`;
}

function _openPrintWindow(bodyHTML){
  const iframe=document.createElement('iframe');
  iframe.style.cssText='position:absolute;left:-9999px;top:-9999px;width:0;height:0;border:none';
  document.body.appendChild(iframe);
  const doc=iframe.contentDocument||iframe.contentWindow.document;
  doc.open();
  doc.write(`<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Etiquetas</title><style>${_LABEL_PRINT_CSS}</style></head><body>${bodyHTML}</body></html>`);
  doc.close();
  setTimeout(()=>{
    iframe.contentWindow.focus();
    iframe.contentWindow.print();
    setTimeout(()=>document.body.removeChild(iframe),2000);
  },400);
}

function printEtiquetas(){
  if(typeof JsBarcode==='undefined'){toast('Librería barcode no disponible','err');return;}
  const start=_labelsPage*LABELS_PER_PAGE;
  const eqs=EQ.slice(start,start+LABELS_PER_PAGE);
  if(!eqs.length){toast('Sin etiquetas en esta página','err');return;}
  _openPrintWindow(_buildLabelPageHTML(eqs));
}

function printAllEtiquetas(){
  if(typeof JsBarcode==='undefined'){toast('Librería barcode no disponible','err');return;}
  const PER=60;
  toast('Generando etiquetas…','info');
  const body=Array.from({length:Math.ceil(EQ.length/PER)},(_,pi)=>
    _buildLabelPageHTML(EQ.slice(pi*PER,(pi+1)*PER))
  ).join('');
  _openPrintWindow(body);
}

/* ════════════════════════════════════════════════════
   BOOT
════════════════════════════════════════════════════ */
init();