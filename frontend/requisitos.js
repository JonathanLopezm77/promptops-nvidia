"use strict";

/**
 * Pantalla de Ingeniería de Requisitos. Igual que app.js, el estado real
 * vive en el backend (analysis.status, en requirements_workflow.py); aquí
 * solo se decide qué pintar y si seguir haciendo polling.
 */
const API = "/api";
const POLL_MS = 3000;

const ESTADOS_EN_PROGRESO = new Set(["CREATED", "EVALUATING", "IMPROVING", "REEVALUATING"]);
const ORDEN_PIPELINE = ["entrada", "evaluacion", "mejora", "reevaluacion", "resultado"];
const NODO_POR_ESTADO = {
  CREATED: "entrada",
  EVALUATING: "evaluacion",
  IMPROVING: "mejora",
  REEVALUATING: "reevaluacion",
  COMPLETED: "resultado",
};
const ETIQUETA_ESTADO = {
  CREATED: "Creado",
  EVALUATING: "Evaluando el requisito original (10 criterios)…",
  IMPROVING: "Generando la versión mejorada…",
  REEVALUATING: "Reevaluando el requisito mejorado…",
  COMPLETED: "Completado",
  ERROR: "Error",
};

// Mismo orden y nombres que REQUIREMENT_CRITERIA en backend/schemas/requirements.py.
const CRITERIOS = {
  claridad: "Claridad",
  especificidad: "Especificidad",
  atomicidad: "Atomicidad",
  completitud: "Completitud",
  consistencia: "Consistencia",
  factibilidad: "Factibilidad",
  verificabilidad: "Verificabilidad",
  trazabilidad: "Trazabilidad",
  ausencia_ambiguedad: "Ausencia de ambigüedad",
  criterios_aceptacion: "Criterios de aceptación",
};

let analisisId = null;
let pollTimer = null;
let ultimoPayloadSerializado = null;
let ultimoAnalisis = null;

// Último dictado aceptado ({texto, metadata}); se envía como input_mode
// "voice" en el próximo ANALIZAR y luego se descarta.
let ultimoDictado = null;
let dictando = false;
// Id del análisis iniciado por voz: al terminar se lee en voz alta solo,
// porque el flujo del enunciado (4.1) cierra con retroalimentación hablada.
let hablarAlTerminar = null;

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

async function apiFetch(path, options) {
  const res = await fetch(API + path, options);
  let body = null;
  try {
    body = await res.json();
  } catch (e) {
    body = null;
  }
  if (!res.ok) {
    const detail = body && body.detail ? body.detail : `Error HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body;
}

function mostrarError(msg) {
  document.getElementById("panel-pipeline").hidden = false;
  const banner = document.getElementById("error-analisis");
  banner.hidden = false;
  banner.textContent = msg;
}

function detenerPolling() {
  if (pollTimer) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
  ultimoPayloadSerializado = null;
}

function evaluacion(analisis, stage) {
  return analisis.evaluations.find((e) => e.stage === stage && e.parse_ok) || null;
}

function listaHtml(items) {
  return items.map((i) => `<li>${escapeHtml(i)}</li>`).join("");
}

// ---------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------

function nodoConError(a) {
  if (!evaluacion(a, "original")) return "evaluacion";
  if (!a.improved_requirement) return "mejora";
  return "reevaluacion";
}

function renderPipeline(a) {
  document.getElementById("panel-pipeline").hidden = false;
  const actual = a.status === "ERROR" ? nodoConError(a) : NODO_POR_ESTADO[a.status];
  const idxActual = ORDEN_PIPELINE.indexOf(actual);

  document.querySelectorAll("#panel-pipeline .pipeline-nodo").forEach((el) => {
    const nodo = el.dataset.nodo;
    const idx = ORDEN_PIPELINE.indexOf(nodo);
    el.classList.remove("activo", "hecho", "error", "omitido");
    if (a.improvement_skipped && (nodo === "mejora" || nodo === "reevaluacion")) {
      el.classList.add("omitido");
    } else if (a.status === "ERROR" && nodo === actual) {
      el.classList.add("error");
    } else if (idx < idxActual || a.status === "COMPLETED") {
      el.classList.add("hecho");
    } else if (idx === idxActual) {
      el.classList.add("activo");
    }
  });

  let estado = `Estado: ${ETIQUETA_ESTADO[a.status] || a.status}`;
  if (a.improvement_skipped) estado += " — el requisito ya era de alta calidad, no se modificó.";
  else if (a.recommended_version === "improved") estado += " — se recomienda la versión mejorada.";
  else if (a.recommended_version === "original") estado += " — se recomienda conservar el original.";
  document.getElementById("estado-analisis").textContent = estado;

  const banner = document.getElementById("error-analisis");
  banner.hidden = !a.error_message;
  banner.textContent = a.error_message || "";
}

function claseScore(score) {
  if (score == null) return "";
  if (score >= 8) return "score-alto";
  if (score >= 6) return "score-medio";
  return "score-bajo";
}

function renderPuntajes(a) {
  const orig = evaluacion(a, "original");
  const mej = evaluacion(a, "improved");
  const cont = document.getElementById("resumen-puntajes");
  const tarjeta = (titulo, ev) =>
    ev
      ? `<div class="tarjeta-puntaje ${ev.is_high_quality ? "alta" : "baja"}">
           <div class="nota">${titulo}</div>
           <div class="puntaje-grande">${ev.global_score}<span>/100</span></div>
           <div class="nota">${ev.is_high_quality ? "Alta calidad" : "No alcanza alta calidad"}</div>
         </div>`
      : "";
  let delta = "";
  if (a.score_delta != null) {
    const signo = a.score_delta > 0 ? "+" : "";
    delta = `<div class="tarjeta-puntaje delta">
               <div class="nota">DELTA</div>
               <div class="puntaje-grande ${a.score_delta >= 0 ? "score-alto" : "score-bajo"}">${signo}${a.score_delta}</div>
               <div class="nota">antes → después</div>
             </div>`;
  }
  cont.innerHTML = tarjeta("ORIGINAL", orig) + tarjeta("MEJORADO", mej) + delta;
  cont.insertAdjacentHTML(
    "beforeend",
    '<p class="nota formula">Requirements Quality Score = promedio de los 10 criterios (1-10) × 10. ' +
      "Alta calidad: ≥ 80 y ningún criterio por debajo de 6.</p>"
  );
}

function renderCriterios(a) {
  const orig = evaluacion(a, "original");
  const mej = evaluacion(a, "improved");
  const porClave = (ev) => Object.fromEntries((ev?.criteria || []).map((c) => [c.criterion, c]));
  const o = porClave(orig);
  const m = porClave(mej);

  const filas = Object.entries(CRITERIOS)
    .map(([clave, nombre]) => {
      const co = o[clave];
      const cm = m[clave];
      const ultimo = cm || co;
      const delta = co && cm ? cm.score - co.score : null;
      return `<tr>
        <td>${nombre}</td>
        <td class="num ${claseScore(co?.score)}">${co ? co.score : "—"}</td>
        ${mej ? `<td class="num ${claseScore(cm?.score)}">${cm ? cm.score : "—"}</td>` : ""}
        ${mej ? `<td class="num">${delta == null ? "—" : (delta > 0 ? "+" : "") + delta}</td>` : ""}
        <td>${escapeHtml(ultimo?.finding)}${
          ultimo?.recommendation
            ? `<div class="recomendacion">→ ${escapeHtml(ultimo.recommendation)}</div>`
            : ""
        }</td>
      </tr>`;
    })
    .join("");

  document.getElementById("tabla-criterios").innerHTML = `
    <table class="tabla-criterios">
      <thead><tr>
        <th>Criterio</th><th>Antes</th>${mej ? "<th>Después</th><th>Δ</th>" : ""}
        <th>Hallazgo${mej ? " (versión mejorada)" : ""} / recomendación</th>
      </tr></thead>
      <tbody>${filas}</tbody>
    </table>`;
}

function resaltarTerminos(texto, terminos) {
  let html = escapeHtml(texto);
  for (const t of terminos) {
    const termino = escapeHtml(t.term).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    if (!termino) continue;
    const motivo = escapeHtml(t.reason).replace(/"/g, "&quot;");
    html = html.replace(new RegExp(termino, "gi"), (m) => `<mark title="${motivo}">${m}</mark>`);
  }
  return html;
}

function renderDiagnostico(a) {
  const orig = evaluacion(a, "original");
  document.getElementById("panel-resultado").hidden = !orig;
  if (!orig) return;

  const terminos = orig.ambiguous_terms || [];
  let texto = `<strong>Requisito:</strong> ${resaltarTerminos(a.original_requirement, terminos)}`;
  texto += `<br /><strong>Diagnóstico:</strong> ${escapeHtml(orig.summary)}`;
  if (orig.is_compound) texto += "<br /><strong>Compuesto:</strong> mezcla varios requisitos independientes.";
  if (orig.missing_information?.length) {
    texto += `<br /><strong>Falta:</strong> ${escapeHtml(orig.missing_information.join("; "))}`;
  }
  document.getElementById("diagnostico-texto").innerHTML = texto;

  renderPuntajes(a);
  renderCriterios(a);

  document.getElementById("terminos-ambiguos").innerHTML = terminos.length
    ? `<h3 class="subtitulo">Términos ambiguos detectados</h3>
       <ul class="lista-simple">${terminos
         .map((t) => `<li><mark>${escapeHtml(t.term)}</mark> — ${escapeHtml(t.reason)}</li>`)
         .join("")}</ul>`
    : "";
}

function renderPreguntas(a) {
  const orig = evaluacion(a, "original");
  const preguntas = orig?.clarification_questions || [];
  const panel = document.getElementById("panel-preguntas");
  panel.hidden = !(a.status === "COMPLETED" && preguntas.length);
  document.getElementById("lista-preguntas").innerHTML = listaHtml(preguntas);
}

function renderMejorado(a) {
  const panel = document.getElementById("panel-mejorado");
  panel.hidden = !a.improved_requirement;
  if (!a.improved_requirement) return;
  const imp = a.improvement || {};

  document.getElementById("texto-original").textContent = a.original_requirement;
  document.getElementById("texto-mejorado").innerHTML = escapeHtml(a.improved_requirement).replace(
    /\[POR DEFINIR:[^\]]*\]/g,
    (m) => `<mark class="por-definir">${m}</mark>`
  );
  document.getElementById("lista-criterios-aceptacion").innerHTML = listaHtml(imp.acceptance_criteria || []);
  const pendientes = imp.pending_items || [];
  document.getElementById("bloque-pendientes").hidden = !pendientes.length;
  document.getElementById("lista-pendientes").innerHTML = listaHtml(pendientes);
  const recomendacion = document.getElementById("aviso-recomendacion");
  recomendacion.hidden = a.recommended_version !== "original";
  recomendacion.textContent =
    a.recommended_version === "original"
      ? `La versión mejorada no subió el puntaje (delta ${a.score_delta ?? "—"}). ` +
        "Se recomienda conservar el requisito original y revisar los hallazgos a mano."
      : "";

  const sinRespaldo = imp.unsupported_values || [];
  const aviso = document.getElementById("aviso-no-sustentados");
  aviso.hidden = !sinRespaldo.length;
  aviso.textContent = sinRespaldo.length
    ? `Atención: el requisito mejorado contiene valores que nadie proporcionó (${sinRespaldo.join(", ")}). ` +
      "Pueden ser datos inventados por el modelo: confírmalos con el stakeholder antes de aceptarlos."
    : "";
  document.getElementById("lista-cambios").innerHTML = listaHtml(imp.changes || []);
  document.getElementById("texto-intencion").textContent = imp.intent_preservation
    ? `Intención original: ${imp.intent_preservation}`
    : "";
}

function describirStt(m) {
  const partes = [
    `${escapeHtml(m.engine)} · ${escapeHtml(m.provider)}`,
    `procesamiento ${m.processing === "remote" ? "REMOTO" : escapeHtml(m.processing)}`,
    `idioma ${escapeHtml(m.language)}`,
    escapeHtml(m.browser),
  ];
  if (m.recording_ms != null) partes.push(`grabación ${(m.recording_ms / 1000).toFixed(1)} s`);
  if (m.transcription_ms != null) partes.push(`transcripción ${(m.transcription_ms / 1000).toFixed(2)} s`);
  if (m.confidence != null) partes.push(`confianza ${m.confidence}`);
  let html = partes.join(" · ");
  if (m.edited) {
    html += `<br />Transcripción corregida a mano. Original: «${escapeHtml(m.original_transcript)}»`;
  }
  return html;
}

function renderTrazabilidad(a) {
  document.getElementById("panel-trazabilidad").hidden = false;
  const fila = (k, v) => (v == null || v === "" ? "" : `<div><span>${k}</span>${v}</div>`);
  const evs = a.evaluations
    .map(
      (e) =>
        `${e.stage === "original" ? "Evaluación original" : "Reevaluación"}: ${escapeHtml(e.model)}` +
        ` · ${e.latency_ms != null ? (e.latency_ms / 1000).toFixed(1) + " s" : "—"}` +
        ` · tokens ${e.prompt_tokens ?? "?"}/${e.completion_tokens ?? "?"}` +
        (e.parse_ok ? "" : " · <strong>JSON inválido (respuesta cruda guardada)</strong>")
    )
    .join("<br />");
  const mejora = a.improved_requirement
    ? `${escapeHtml(a.improver_model)} · ${(a.improvement_latency_ms / 1000).toFixed(1)} s · tokens ${a.improvement_tokens ?? "?"}`
    : a.improvement_skipped
      ? "Omitida (el original ya era de alta calidad)"
      : null;

  document.getElementById("datos-trazabilidad").innerHTML = [
    fila("ID", `<code>${a.id}</code>`),
    fila(
      "Análisis anterior",
      a.parent_id ? `<a href="#" data-id="${a.parent_id}" class="link-analisis"><code>${a.parent_id}</code></a>` : null
    ),
    fila("Entrada", a.input_mode === "voice" ? "Voz (STT)" : "Texto"),
    fila("Motor STT", a.stt_metadata ? describirStt(a.stt_metadata) : null),
    fila("Creado", new Date(a.created_at).toLocaleString("es-ES")),
    fila("Terminado", a.finished_at ? new Date(a.finished_at).toLocaleString("es-ES") : null),
    fila("Contexto", a.project_context ? escapeHtml(a.project_context) : null),
    fila("Aclaraciones", a.clarifications ? escapeHtml(a.clarifications) : null),
    fila("Evaluador", evs || escapeHtml(a.evaluator_model)),
    fila("Mejorador", mejora),
  ].join("");

  document.querySelectorAll(".link-analisis").forEach((el) =>
    el.addEventListener("click", (ev) => {
      ev.preventDefault();
      abrirAnalisis(el.dataset.id);
    })
  );
}

function renderBotonesVoz(a) {
  const terminado = a.status === "COMPLETED" || a.status === "ERROR";
  document.getElementById("btn-escuchar").hidden = !(terminado && Voz.soportaSintesis);
}

function render(a) {
  ultimoAnalisis = a;
  renderBotonesVoz(a);
  renderPipeline(a);
  renderDiagnostico(a);
  renderPreguntas(a);
  renderMejorado(a);
  renderTrazabilidad(a);
}

// ---------------------------------------------------------------------------
// Carga + polling
// ---------------------------------------------------------------------------

async function cargarYQuizasSeguirSondeando(id) {
  let analisis;
  try {
    analisis = await apiFetch(`/requirements/${id}`);
  } catch (err) {
    mostrarError(err.message);
    return;
  }
  const serializado = JSON.stringify(analisis);
  if (serializado !== ultimoPayloadSerializado) {
    ultimoPayloadSerializado = serializado;
    render(analisis);
  }
  if (ESTADOS_EN_PROGRESO.has(analisis.status)) {
    pollTimer = setTimeout(() => cargarYQuizasSeguirSondeando(id), POLL_MS);
  } else if (hablarAlTerminar === analisis.id) {
    hablarAlTerminar = null;
    leerResultado(analisis);
  }
}

// ---------------------------------------------------------------------------
// Voz
// ---------------------------------------------------------------------------

function textoParaVoz(texto) {
  return (texto || "").replace(/\[POR DEFINIR:?\s*([^\]]*)\]/gi, " (por definir: $1) ").replace(/\s+/g, " ");
}

/** Guion de la retroalimentación hablada, derivado solo de la respuesta de la API. */
function guionResultado(a) {
  if (a.status === "ERROR") {
    // Solo la causa general: el detalle técnico (validación, cuerpo HTTP) no
    // se entiende hablado y ya está completo en pantalla.
    const causa = (a.error_message || "").split(":")[0].trim();
    return `El análisis terminó con un error. ${causa}. El detalle está en la pantalla.`;
  }
  const orig = evaluacion(a, "original");
  if (!orig) return "El análisis todavía no tiene resultados.";

  const partes = [`Análisis completado. El requisito original obtuvo ${orig.global_score} de 100 puntos.`];
  if (a.improvement_skipped) {
    partes.push("Es un requisito de alta calidad, así que no se modificó.");
  } else {
    const mej = evaluacion(a, "improved");
    if (mej) {
      partes.push(`La versión mejorada obtuvo ${mej.global_score} de 100, una diferencia de ${a.score_delta} puntos.`);
    }
    partes.push(
      a.recommended_version === "improved"
        ? "Se recomienda usar la versión mejorada."
        : "Se recomienda conservar el requisito original y revisarlo a mano."
    );
  }

  const debiles = [...orig.criteria].sort((x, y) => x.score - y.score).filter((c) => c.score < 6).slice(0, 3);
  if (debiles.length) {
    partes.push("Los criterios más débiles son:");
    debiles.forEach((c) => partes.push(`${CRITERIOS[c.criterion]}, con ${c.score} de 10. ${c.finding}`));
  }
  if (orig.ambiguous_terms?.length) {
    partes.push(`Términos ambiguos: ${orig.ambiguous_terms.map((t) => t.term).join(", ")}.`);
  }
  const preguntas = orig.clarification_questions || [];
  if (preguntas.length) {
    partes.push(`Tengo ${preguntas.length} ${preguntas.length === 1 ? "pregunta" : "preguntas"} de aclaración.`);
    preguntas.forEach((p, i) => partes.push(`Pregunta ${i + 1}: ${p}`));
  }
  if (a.improved_requirement && a.recommended_version === "improved") {
    partes.push(`Requisito mejorado: ${textoParaVoz(a.improved_requirement)}`);
  }
  return partes.join("\n");
}

function leerResultado(a) {
  const estado = document.getElementById("estado-tts");
  const detener = document.getElementById("btn-detener-voz");
  const info = Voz.hablar(guionResultado(a), {
    alTerminar: () => {
      detener.hidden = true;
    },
  });
  if (!info) {
    estado.textContent = "Este navegador no soporta lectura en voz alta.";
    return;
  }
  detener.hidden = false;
  estado.textContent =
    `Voz: ${info.voice} (${info.language}) · ${info.engine} · ` +
    `procesamiento ${info.processing === "local" ? "LOCAL" : info.processing === "remote" ? "REMOTO" : "desconocido"}`;
}

function actualizarBotonDictar() {
  const boton = document.getElementById("btn-dictar");
  boton.textContent = dictando ? "⏹ TERMINAR DICTADO" : "🎤 DICTAR";
  boton.classList.toggle("grabando", dictando);
}

function alternarDictado() {
  const estado = document.getElementById("estado-voz");
  const campo = document.getElementById("input-requisito");
  if (dictando) {
    Voz.detenerDictado();
    estado.textContent = "Procesando la transcripción…";
    return;
  }
  Voz.detenerHabla();
  dictando = true;
  ultimoDictado = null;
  actualizarBotonDictar();
  estado.textContent = "Escuchando… habla y pulsa TERMINAR DICTADO al acabar.";
  Voz.iniciarDictado({
    alParcial: (texto) => {
      campo.value = texto;
    },
    alTerminar: (resultado, error) => {
      dictando = false;
      actualizarBotonDictar();
      if (error) {
        estado.textContent = error;
        return;
      }
      campo.value = resultado.texto;
      ultimoDictado = resultado;
      const m = resultado.metadata;
      estado.textContent =
        `Transcrito con ${m.provider} (remoto)` +
        (m.transcription_ms != null ? ` en ${(m.transcription_ms / 1000).toFixed(2)} s` : "") +
        ". Revisa el texto y pulsa ANALIZAR.";
    },
  });
}

function abrirAnalisis(id) {
  analisisId = id;
  detenerPolling();
  cargarYQuizasSeguirSondeando(id);
}

// ---------------------------------------------------------------------------
// Acciones
// ---------------------------------------------------------------------------

async function analizar() {
  const requirement = document.getElementById("input-requisito").value.trim();
  if (!requirement) return;
  const contexto = document.getElementById("input-contexto").value.trim();

  const cuerpo = { requirement, project_context: contexto || null, input_mode: "text" };
  if (ultimoDictado) {
    cuerpo.input_mode = "voice";
    cuerpo.stt_metadata = {
      ...ultimoDictado.metadata,
      edited: requirement !== ultimoDictado.texto,
      original_transcript: ultimoDictado.texto,
    };
  }

  const boton = document.getElementById("btn-analizar");
  boton.disabled = true;
  try {
    const a = await apiFetch("/requirements", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo),
    });
    ultimoDictado = null;
    document.getElementById("estado-voz").textContent = "";
    if (cuerpo.input_mode === "voice") hablarAlTerminar = a.id;
    abrirAnalisis(a.id);
  } catch (err) {
    mostrarError(err.message);
  } finally {
    boton.disabled = false;
  }
}

async function responderPreguntas() {
  const campo = document.getElementById("input-respuestas");
  const answers = campo.value.trim();
  if (!answers) {
    mostrarError("Escribe tus respuestas antes de reanalizar.");
    return;
  }
  const boton = document.getElementById("btn-responder");
  boton.disabled = true;
  try {
    const nuevo = await apiFetch(`/requirements/${analisisId}/clarify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers }),
    });
    campo.value = "";
    if (nuevo.input_mode === "voice") hablarAlTerminar = nuevo.id;
    abrirAnalisis(nuevo.id);
  } catch (err) {
    mostrarError(err.message);
  } finally {
    boton.disabled = false;
  }
}

async function cargarHistorial() {
  const lista = await apiFetch("/requirements");
  const contenedor = document.getElementById("lista-historial");
  if (!lista.length) {
    contenedor.innerHTML = '<p class="nota">Sin análisis todavía.</p>';
    return;
  }
  contenedor.innerHTML = lista
    .map(
      (a) => `
    <div class="item-historial" data-id="${a.id}">
      <div class="estado">${a.status}${a.parent_id ? " · aclaración" : ""}${a.input_mode === "voice" ? " · voz" : ""}</div>
      <div>${escapeHtml(a.original_requirement.slice(0, 80))}</div>
      <div class="nota">${new Date(a.created_at).toLocaleString("es-ES")}</div>
    </div>`
    )
    .join("");
  contenedor.querySelectorAll(".item-historial").forEach((el) => {
    el.addEventListener("click", () => {
      document.getElementById("panel-historial").hidden = true;
      abrirAnalisis(el.dataset.id);
    });
  });
}

document.getElementById("btn-analizar").addEventListener("click", analizar);

const botonDictar = document.getElementById("btn-dictar");
if (Voz.soportaDictado) {
  botonDictar.addEventListener("click", alternarDictado);
} else {
  botonDictar.disabled = true;
  document.getElementById("estado-voz").textContent =
    "Este navegador no soporta dictado por voz. Usa Chrome o Edge.";
}
document.getElementById("btn-escuchar").addEventListener("click", () => {
  if (ultimoAnalisis) leerResultado(ultimoAnalisis);
});
document.getElementById("btn-detener-voz").addEventListener("click", () => {
  Voz.detenerHabla();
  document.getElementById("btn-detener-voz").hidden = true;
});
document.getElementById("btn-responder").addEventListener("click", responderPreguntas);
document.getElementById("btn-historial-toggle").addEventListener("click", async () => {
  const panel = document.getElementById("panel-historial");
  panel.hidden = !panel.hidden;
  if (!panel.hidden) {
    try {
      await cargarHistorial();
    } catch (err) {
      mostrarError(err.message);
    }
  }
});
