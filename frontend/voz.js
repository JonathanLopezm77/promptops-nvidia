"use strict";

/**
 * Subsistema de voz de la pantalla de requisitos (Parcial 1, sección 4.5).
 * Se mantiene separado de la lógica del análisis, como pide el enunciado.
 *
 * - STT: Web Speech API (SpeechRecognition). NO es local: Chrome envía el
 *   audio a los servidores de Google y Edge a los de Microsoft. Por eso
 *   cada dictado guarda en stt_metadata qué motor/proveedor se usó.
 * - TTS: speechSynthesis del navegador. En Windows las voces "Microsoft ..."
 *   del sistema son locales (voice.localService = true); las "Google ..."
 *   de Chrome son remotas. Se informa cuál se usó.
 */
const Voz = (() => {
  const Reconocimiento = window.SpeechRecognition || window.webkitSpeechRecognition || null;
  const IDIOMA = "es-CO";

  const MENSAJES_ERROR = {
    "not-allowed": "El navegador no tiene permiso para usar el micrófono.",
    "service-not-allowed": "El navegador bloqueó el servicio de reconocimiento de voz.",
    "no-speech": "No se detectó voz. Intenta de nuevo hablando más cerca del micrófono.",
    "audio-capture": "No se encontró un micrófono.",
    network: "El reconocimiento de voz necesita conexión a internet (usa un servicio remoto).",
    aborted: "Dictado cancelado.",
    "language-not-supported": `El navegador no reconoce el idioma ${IDIOMA}.`,
  };

  function proveedorStt() {
    const ua = navigator.userAgent;
    if (/Edg\//.test(ua)) return "Microsoft (servicio en la nube de Edge)";
    if (/Chrome\//.test(ua)) return "Google (servicio en la nube de Chrome)";
    return "servicio del navegador (desconocido)";
  }

  function navegador() {
    const m = navigator.userAgent.match(/(Edg|Chrome|Firefox|Safari)\/([\d.]+)/);
    return m ? `${m[1] === "Edg" ? "Edge" : m[1]} ${m[2]}` : navigator.userAgent;
  }

  // -------------------------------------------------------------------------
  // STT
  // -------------------------------------------------------------------------

  let rec = null;

  /**
   * Empieza a dictar. `alParcial(texto)` recibe la transcripción en vivo;
   * `alTerminar({texto, metadata} | null, error | null)` se llama una vez.
   */
  function iniciarDictado({ alParcial, alTerminar }) {
    if (!Reconocimiento) {
      alTerminar(null, "Este navegador no soporta dictado por voz. Usa Chrome o Edge.");
      return;
    }
    rec = new Reconocimiento();
    rec.lang = IDIOMA;
    rec.continuous = true;
    rec.interimResults = true;

    const inicio = performance.now();
    let finDeHabla = null;
    let finales = [];
    let confianzas = [];
    let error = null;

    rec.onresult = (ev) => {
      let parcial = "";
      finales = [];
      confianzas = [];
      for (const r of ev.results) {
        if (r.isFinal) {
          finales.push(r[0].transcript.trim());
          confianzas.push(r[0].confidence);
        } else {
          parcial += r[0].transcript;
        }
      }
      alParcial([...finales, parcial.trim()].filter(Boolean).join(" "));
    };
    rec.onspeechend = () => {
      finDeHabla = performance.now();
    };
    rec.onerror = (ev) => {
      error = MENSAJES_ERROR[ev.error] || `Error de reconocimiento de voz: ${ev.error}`;
    };
    rec.onend = () => {
      const fin = performance.now();
      rec = null;
      const texto = finales.join(" ").trim();
      if (!texto) {
        alTerminar(null, error || MENSAJES_ERROR["no-speech"]);
        return;
      }
      const confianzaValida = confianzas.filter((c) => c > 0);
      alTerminar(
        {
          texto,
          metadata: {
            engine: "Web Speech API (SpeechRecognition)",
            provider: proveedorStt(),
            processing: "remote",
            language: IDIOMA,
            browser: navegador(),
            recording_ms: Math.round((finDeHabla ?? fin) - inicio),
            // Desde que se dejó de hablar hasta tener el texto final.
            transcription_ms: finDeHabla ? Math.round(fin - finDeHabla) : null,
            confidence: confianzaValida.length
              ? Number((confianzaValida.reduce((a, b) => a + b, 0) / confianzaValida.length).toFixed(3))
              : null,
            recorded_at: new Date().toISOString(),
          },
        },
        null
      );
    };
    rec.start();
  }

  function detenerDictado() {
    if (rec) rec.stop();
  }

  // -------------------------------------------------------------------------
  // TTS
  // -------------------------------------------------------------------------

  function elegirVoz() {
    const voces = window.speechSynthesis ? speechSynthesis.getVoices() : [];
    const espanol = voces.filter((v) => v.lang.toLowerCase().startsWith("es"));
    return (
      espanol.find((v) => v.localService && /co|419|mx|us/i.test(v.lang)) ||
      espanol.find((v) => v.localService) ||
      espanol[0] ||
      null
    );
  }

  /**
   * Lee `texto` en voz alta. Chrome corta las locuciones largas (~15 s), así
   * que se divide en frases y se encolan. Devuelve la descripción de la voz
   * usada, o null si el navegador no soporta síntesis.
   */
  function hablar(texto, { alTerminar } = {}) {
    if (!window.speechSynthesis) return null;
    speechSynthesis.cancel();
    const voz = elegirVoz();
    const frases = texto.match(/[^.!?:\n]+[.!?:]?/g)?.map((f) => f.trim()).filter(Boolean) || [];
    frases.forEach((frase, i) => {
      const u = new SpeechSynthesisUtterance(frase);
      u.lang = voz?.lang || IDIOMA;
      if (voz) u.voice = voz;
      if (i === frases.length - 1 && alTerminar) {
        u.onend = alTerminar;
        u.onerror = alTerminar;
      }
      speechSynthesis.speak(u);
    });
    return {
      engine: "speechSynthesis (navegador)",
      voice: voz ? voz.name : "voz por defecto del navegador",
      language: voz?.lang || IDIOMA,
      processing: voz ? (voz.localService ? "local" : "remote") : "desconocido",
    };
  }

  function detenerHabla() {
    if (window.speechSynthesis) speechSynthesis.cancel();
  }

  // Las voces se cargan de forma asíncrona en Chrome.
  if (window.speechSynthesis) speechSynthesis.getVoices();

  return {
    soportaDictado: Boolean(Reconocimiento),
    soportaSintesis: Boolean(window.speechSynthesis),
    iniciarDictado,
    detenerDictado,
    hablar,
    detenerHabla,
  };
})();
