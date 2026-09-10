"use strict";

/**
 * Todo el estado real vive en el backend (run.status). Este archivo NO
 * revalida transiciones ni decide qué es válido: solo clasifica, para la
 * UI, si un estado "sigue en progreso" (para saber si seguir haciendo
 * polling) o no. La máquina de estados de verdad vive únicamente en
 * backend/services/workflow.py.
 */
const API = "/api";

const ESTADOS_EN_PROGRESO = new Set([
  "CREATED",
  "OPTIMIZING",
  "AUDITING",
  "GATING",
  "ITERATING",
  "EXECUTING",
]);

const ORDEN_PIPELINE = ["prompt", "optimizer", "auditor", "gates", "human", "executor"];

const NODO_POR_ESTADO = {
  CREATED: "prompt",
  OPTIMIZING: "optimizer",
  ITERATING: "optimizer",
  AUDITING: "auditor",
  GATING: "gates",
  WAITING_HUMAN: "human",
  APPROVED: "human",
  REJECTED: "human",
  EXECUTING: "executor",
  COMPLETED: "executor",
};

const ETIQUETA_GATE = {
  gate_1_estructura_instruccion: "Gate 1 — Estructura e Instrucción",
  gate_2_cognicion: "Gate 2 — Razonamiento y Cognición",
  gate_3_seguridad_veracidad: "Gate 3 — Seguridad y Veracidad",
  gate_4_eficiencia_foco: "Gate 4 — Eficiencia y Foco",
};

const ETIQUETA_DECISION = {
  approve: "Aprobó el prompt",
  iterate: "Pidió nueva iteración",
  edit: "Editó el prompt a mano",
  reject: "Rechazó el prompt",
};

const POLL_MS = 3000;

let runId = null;
let pollTimer = null;
let ultimoPayloadSerializado = null;

// Mientras auto-iterar está activo, hay que seguir sondeando aunque el
// estado pase brevemente por WAITING_HUMAN entre una vuelta automática y
// la siguiente (no hay round-trip HTTP entre vueltas: el backend las
// encadena solo). Esto es una condición de parada de la UI, no una
// revalidación de la máquina de estados real.
let autoIterando = null; // { targetScore, maxAttempts, iteracionesAlInicio } | null

function debeSeguirSondeando(run) {
  if (ESTADOS_EN_PROGRESO.has(run.status)) return true;
  if (!autoIterando) return false;
  if (run.status === "ERROR") {
    autoIterando = null;
    return false;
  }
  const nuevasIteraciones = run.iterations.length - autoIterando.iteracionesAlInicio;
  const ultimoScore = ultimaAuditoria(run)?.total_score ?? 0;
  const alcanzoMeta = ultimoScore >= autoIterando.targetScore;
  const agotoIntentos = nuevasIteraciones >= autoIterando.maxAttempts;
  if (alcanzoMeta || agotoIntentos) {
    autoIterando = null;
    return false;
  }
  return true;
}

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

function mostrarErrorGlobal(msg) {
  document.getElementById("panel-pipeline").hidden = false;
  const banner = document.getElementById("error-run");
  banner.hidden = false;
  banner.textContent = msg;
}

function detenerPolling() {
  if (pollTimer) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
  // fuerza el próximo render (evita comparar contra datos de un run distinto)
  ultimoPayloadSerializado = null;
  autoIterando = null;
}

// ---------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------

function renderPipeline(run) {
  document.getElementById("panel-pipeline").hidden = false;
  const nodoActual = NODO_POR_ESTADO[run.status] || null;
  const idxActual = ORDEN_PIPELINE.indexOf(nodoActual);

  document.querySelectorAll(".pipeline-nodo").forEach((el) => {
    const idx = ORDEN_PIPELINE.indexOf(el.dataset.nodo);
    el.classList.remove("activo", "hecho", "error");
    if (run.status === "ERROR") {
      if (idx === idxActual) el.classList.add("error");
      else if (idx < idxActual) el.classList.add("hecho");
      return;
    }
    if (idx === idxActual) {
      el.classList.add(ESTADOS_EN_PROGRESO.has(run.status) ? "activo" : "hecho");
    } else if (idx < idxActual) {
      el.classList.add("hecho");
    }
  });

  let textoEstado = `Estado: ${run.status}`;
  if (autoIterando) {
    const hechas = run.iterations.length - autoIterando.iteracionesAlInicio;
    const mejorScore = ultimaAuditoria(run)?.total_score ?? "—";
    textoEstado += ` — auto-mejorando: intento ${Math.min(hechas + 1, autoIterando.maxAttempts)}/${
      autoIterando.maxAttempts
    }, último score: ${mejorScore}/${autoIterando.targetScore}`;
  }
  document.getElementById("estado-run").textContent = textoEstado;
  document.getElementById(
    "prompt-original-run"
  ).innerHTML = `<strong>Prompt original:</strong> ${escapeHtml(run.original_prompt)}`;

  const banner = document.getElementById("error-run");
  if (run.status === "ERROR" && run.error_message) {
    banner.hidden = false;
    banner.textContent = run.error_message;
  } else {
    banner.hidden = true;
  }
}

function renderTimeline(events) {
  const panel = document.getElementById("panel-timeline");
  const lista = document.getElementById("lista-timeline");
  if (!events || !events.length) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  lista.innerHTML = events
    .map((e) => {
      const hora = new Date(e.timestamp).toLocaleTimeString("es-ES");
      return `<li><span class="ts">[${hora}]</span>${escapeHtml(e.description)}</li>`;
    })
    .join("");
}

function renderIteraciones(run) {
  const panel = document.getElementById("panel-iteraciones");
  const contenedor = document.getElementById("lista-iteraciones");
  if (!run.iterations.length) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  contenedor.innerHTML = run.iterations
    .map((it) => {
      const fuente = it.source === "optimizer" ? "Optimizer" : "Edición manual";
      const salida = it.output_prompt ?? "(el Optimizer no devolvió un prompt válido)";
      const auditoria = it.audits[0];
      let badge = "";
      if (auditoria) {
        badge = auditoria.parse_ok
          ? ` — score ${auditoria.total_score}/100, ${auditoria.gates_passed}/${
              auditoria.gates_passed + auditoria.gates_failed
            } Gates`
          : " — auditoría falló (parse_ok=false)";
      }
      const decisiones = it.human_decisions
        .map((hd) => {
          const detalle = hd.feedback || hd.edited_prompt;
          return `<div class="decision">
            <span class="decision-tipo">${ETIQUETA_DECISION[hd.decision] || hd.decision}</span>
            ${detalle ? `: ${escapeHtml(detalle)}` : ""}
          </div>`;
        })
        .join("");

      return `
      <div class="iteracion">
        <div class="iteracion-titulo">Iteración ${it.iteration_number} (${fuente})${badge}</div>
        <div class="iteracion-comparacion">
          <div><span class="etiqueta">ENTRADA</span>${escapeHtml(it.input_prompt)}</div>
          <div><span class="etiqueta">SALIDA</span>${escapeHtml(salida)}</div>
        </div>
        ${decisiones ? `<div class="decisiones-humanas">${decisiones}</div>` : ""}
      </div>`;
    })
    .join("");
}

function ultimaAuditoria(run) {
  if (!run.iterations.length) return null;
  const ultimaIteracion = run.iterations[run.iterations.length - 1];
  return ultimaIteracion.audits[0] || null;
}

function renderGates(gates) {
  const contenedor = document.getElementById("gates-auditoria");
  contenedor.innerHTML = gates
    .map((g) => {
      const clase = g.status === "PASS" ? "pass" : g.status === "FAIL" ? "fail" : "na";
      const simbolo = g.status === "PASS" ? "✓" : g.status === "FAIL" ? "✗" : "N/A";
      return `
      <div class="gate-card ${clase}">
        <div class="gate-nombre">${ETIQUETA_GATE[g.gate] || g.gate}</div>
        <div class="gate-estado">${simbolo} ${g.status}</div>
        <div class="gate-justificacion">${escapeHtml(g.justification)}</div>
      </div>`;
    })
    .join("");
}

function renderPropiedades(properties) {
  const contenedor = document.getElementById("propiedades-auditoria");
  const porGate = {};
  for (const p of properties) {
    (porGate[p.gate] = porGate[p.gate] || []).push(p);
  }
  contenedor.innerHTML = Object.entries(porGate)
    .map(
      ([gate, props]) => `
    <div class="propiedad-grupo">
      <h3>${ETIQUETA_GATE[gate] || gate}</h3>
      ${props
        .map(
          (p) => `
        <div class="propiedad-fila">
          <span>${p.property_id} — ${escapeHtml(p.property_name)}</span>
          <span class="propiedad-score">${p.score}/10</span>
          <span>${escapeHtml(p.observation)}</span>
        </div>`
        )
        .join("")}
    </div>`
    )
    .join("");
}

function renderAuditoria(run) {
  const panel = document.getElementById("panel-auditoria");
  const audit = ultimaAuditoria(run);
  if (!audit) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;

  const resumen = document.getElementById("resumen-auditoria");
  if (!audit.parse_ok) {
    resumen.innerHTML = "<strong>La auditoría no pudo interpretarse (parse_ok=false).</strong>";
    document.getElementById("gates-auditoria").innerHTML = "";
    document.getElementById("propiedades-auditoria").innerHTML = "";
    document.getElementById("recomendaciones-auditoria").innerHTML = "";
    return;
  }

  const gatesScore = audit.gates_score !== null && audit.gates_score !== undefined
    ? audit.gates_score.toFixed(2)
    : "—";
  resumen.innerHTML =
    `Score total: <strong>${audit.total_score}/100</strong> — ` +
    `${audit.gates_passed} PASS / ${audit.gates_failed} FAIL / ${audit.gates_not_applicable} N/A ` +
    `(gates_score: ${gatesScore})`;

  renderGates(audit.gates);
  renderPropiedades(audit.properties);

  const rec = document.getElementById("recomendaciones-auditoria");
  rec.innerHTML = audit.recommendations.length
    ? `<strong>Recomendaciones:</strong><ul>${audit.recommendations
        .map((r) => `<li>${escapeHtml(r)}</li>`)
        .join("")}</ul>`
    : "";
}

function renderHumano(run) {
  document.getElementById("panel-humano").hidden = run.status !== "WAITING_HUMAN";
}

function renderEjecucion(run) {
  document.getElementById("panel-ejecucion").hidden = run.status !== "APPROVED";
}

function renderRespuesta(run) {
  const panel = document.getElementById("panel-respuesta");
  if (!run.result) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  document.getElementById(
    "prompt-aprobado-respuesta"
  ).innerHTML = `<strong>Prompt aprobado:</strong> ${escapeHtml(run.result.approved_prompt)}`;
  document.getElementById("texto-respuesta").textContent = run.result.final_response;
}

function render(run, events) {
  renderPipeline(run);
  renderTimeline(events);
  renderIteraciones(run);
  renderAuditoria(run);
  renderHumano(run);
  renderEjecucion(run);
  renderRespuesta(run);
}

// ---------------------------------------------------------------------------
// Carga + polling
// ---------------------------------------------------------------------------

async function cargarYQuizasSeguirSondeando(id) {
  let run;
  let events;
  try {
    [run, events] = await Promise.all([apiFetch(`/runs/${id}`), apiFetch(`/runs/${id}/events`)]);
  } catch (err) {
    mostrarErrorGlobal(err.message);
    return;
  }

  // Si nada cambió desde el último poll, no se vuelve a pintar: reconstruir
  // el innerHTML de un panel resetea el scroll de cualquier caja que el
  // usuario haya desplazado (p. ej. la SALIDA de una iteración), aunque el
  // contenido sea idéntico. Repintar solo cuando hay algo nuevo evita eso.
  const serializado = JSON.stringify({ run, events });
  if (serializado !== ultimoPayloadSerializado) {
    ultimoPayloadSerializado = serializado;
    render(run, events);
  }

  if (debeSeguirSondeando(run)) {
    pollTimer = setTimeout(() => cargarYQuizasSeguirSondeando(id), POLL_MS);
  }
}

// ---------------------------------------------------------------------------
// Acciones
// ---------------------------------------------------------------------------

async function iniciarRun() {
  const campo = document.getElementById("input-prompt");
  const prompt = campo.value.trim();
  if (!prompt) return;

  const boton = document.getElementById("btn-iniciar");
  boton.disabled = true;
  try {
    const run = await apiFetch("/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    runId = run.id;
    detenerPolling();
    cargarYQuizasSeguirSondeando(runId);
  } catch (err) {
    mostrarErrorGlobal(err.message);
  } finally {
    boton.disabled = false;
  }
}

async function cargarHistorial() {
  const runs = await apiFetch("/runs");
  const contenedor = document.getElementById("lista-historial");
  if (!runs.length) {
    contenedor.innerHTML = '<p class="nota">Sin ejecuciones todavía.</p>';
    return;
  }
  contenedor.innerHTML = runs
    .map(
      (r) => `
    <div class="item-historial" data-id="${r.id}">
      <div class="estado">${r.status}</div>
      <div>${escapeHtml(r.original_prompt.slice(0, 80))}</div>
      <div class="nota">${new Date(r.created_at).toLocaleString("es-ES")}</div>
    </div>`
    )
    .join("");
  contenedor.querySelectorAll(".item-historial").forEach((el) => {
    el.addEventListener("click", () => {
      runId = el.dataset.id;
      document.getElementById("panel-historial").hidden = true;
      detenerPolling();
      cargarYQuizasSeguirSondeando(runId);
    });
  });
}

function conectarBotones() {
  document.getElementById("btn-iniciar").addEventListener("click", iniciarRun);

  document.getElementById("btn-historial-toggle").addEventListener("click", async () => {
    const panel = document.getElementById("panel-historial");
    panel.hidden = !panel.hidden;
    if (!panel.hidden) await cargarHistorial();
  });

  document.getElementById("btn-aprobar").addEventListener("click", async () => {
    try {
      await apiFetch(`/runs/${runId}/approve`, { method: "POST" });
      detenerPolling();
      cargarYQuizasSeguirSondeando(runId);
    } catch (err) {
      mostrarErrorGlobal(err.message);
    }
  });

  document.getElementById("btn-iterar").addEventListener("click", async () => {
    const campo = document.getElementById("input-feedback");
    const feedback = campo.value.trim();
    if (!feedback) {
      mostrarErrorGlobal("Escribe el feedback antes de pedir una nueva iteración.");
      return;
    }
    try {
      await apiFetch(`/runs/${runId}/iterate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ feedback }),
      });
      campo.value = "";
      detenerPolling();
      cargarYQuizasSeguirSondeando(runId);
    } catch (err) {
      mostrarErrorGlobal(err.message);
    }
  });

  document.getElementById("btn-editar-toggle").addEventListener("click", () => {
    const campo = document.getElementById("input-edicion");
    campo.hidden = !campo.hidden;
    document.getElementById("btn-editar-enviar").hidden = campo.hidden;
  });

  document.getElementById("btn-editar-enviar").addEventListener("click", async () => {
    const campo = document.getElementById("input-edicion");
    const prompt = campo.value.trim();
    if (!prompt) return;
    try {
      await apiFetch(`/runs/${runId}/edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      campo.value = "";
      campo.hidden = true;
      document.getElementById("btn-editar-enviar").hidden = true;
      detenerPolling();
      cargarYQuizasSeguirSondeando(runId);
    } catch (err) {
      mostrarErrorGlobal(err.message);
    }
  });

  document.getElementById("btn-rechazar").addEventListener("click", async () => {
    const feedback = document.getElementById("input-feedback").value.trim() || null;
    try {
      await apiFetch(`/runs/${runId}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ feedback }),
      });
      detenerPolling();
      cargarYQuizasSeguirSondeando(runId);
    } catch (err) {
      mostrarErrorGlobal(err.message);
    }
  });

  document.getElementById("btn-auto-iterar").addEventListener("click", async () => {
    const targetScore = 90;
    const maxAttempts = 5;
    try {
      const runActual = await apiFetch(`/runs/${runId}`);
      await apiFetch(`/runs/${runId}/auto-iterate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_score: targetScore, max_attempts: maxAttempts }),
      });
      detenerPolling();
      autoIterando = {
        targetScore,
        maxAttempts,
        iteracionesAlInicio: runActual.iterations.length,
      };
      cargarYQuizasSeguirSondeando(runId);
    } catch (err) {
      mostrarErrorGlobal(err.message);
    }
  });

  document.getElementById("btn-copiar-respuesta").addEventListener("click", async () => {
    const boton = document.getElementById("btn-copiar-respuesta");
    const texto = document.getElementById("texto-respuesta").textContent;
    try {
      await navigator.clipboard.writeText(texto);
      boton.textContent = "✓ Copiado";
      boton.classList.add("copiado");
      setTimeout(() => {
        boton.textContent = "⧉ Copiar";
        boton.classList.remove("copiado");
      }, 1500);
    } catch (err) {
      mostrarErrorGlobal("No se pudo copiar al portapapeles: " + err.message);
    }
  });

  document.getElementById("btn-ejecutar").addEventListener("click", async () => {
    try {
      await apiFetch(`/runs/${runId}/execute`, { method: "POST" });
      detenerPolling();
      cargarYQuizasSeguirSondeando(runId);
    } catch (err) {
      mostrarErrorGlobal(err.message);
    }
  });
}

document.addEventListener("DOMContentLoaded", conectarBotones);
