import { useEffect, useRef, useState } from "react";

import Icon from "../../components/Icon.jsx";
import LojistaSidebar from "../../components/LojistaSidebar.jsx";
import { backendGet, orchestrate, unwrap } from "../../lib/http.js";
import { readActor } from "../../lib/session.js";

const TEXTO_PROMPT = "Descreva com suas palavras o principal desafio no dia a dia:";
const AVISOS_KEY = "orvyn-ultimos-avisos";

export default function App() {
  const [actor, setActor] = useState(readActor);
  const [profileName, setProfileName] = useState(actor?.nome || "Lojista");
  const [questions, setQuestions] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState({});
  const [messages, setMessages] = useState([]);
  const [selecionados, setSelecionados] = useState([]);
  const [freeText, setFreeText] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const conversationRef = useRef(null);

  useEffect(() => {
    if (!actor || actor.perfil !== "lojista" || !Number.isInteger(actor.id)) {
      window.location.replace("/");
    }
  }, [actor]);

  useEffect(() => {
    if (!actor || actor.perfil !== "lojista" || !Number.isInteger(actor.id)) return;
    let ativo = true;

    async function carregar() {
      try {
        const [lojista, roteiro] = await Promise.all([
          backendGet(`/api/lojistas/${actor.id}`, actor),
          backendGet("/api/chat/roteiro", actor),
        ]);
        if (!ativo) return;
        setProfileName(lojista?.nome || actor.nome || "Lojista");
        const perguntas = Array.isArray(roteiro?.perguntas) ? roteiro.perguntas : [];
        setQuestions(perguntas);
        setMessages(
          perguntas.length
            ? [{ role: "assistant", text: perguntas[0].pergunta }]
            : [{ role: "assistant", text: TEXTO_PROMPT }],
        );
      } catch (falha) {
        if (!ativo) return;
        setError(falha.message || String(falha));
      } finally {
        if (ativo) setLoading(false);
      }
    }

    carregar();
    return () => {
      ativo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [actor?.perfil, actor?.id]);

  useEffect(() => {
    const last = conversationRef.current?.lastElementChild;
    last?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    setSelecionados([]);
  }, [currentQuestion]);

  const question = questions[currentQuestion];
  const noTexto = !loading && currentQuestion >= questions.length;
  const total = questions.length;
  const etapaAtual = Math.min(currentQuestion + 1, total);
  const progresso = total ? (etapaAtual / total) * 100 : 0;
  const badge = noTexto ? "Última etapa" : loading ? "Preparando perguntas" : "Passo a passo";

  function alternarOpcao(valor) {
    setSelecionados((atual) => {
      if (!question?.multipla) return [valor];
      return atual.includes(valor) ? atual.filter((item) => item !== valor) : [...atual, valor];
    });
  }

  function responder(event) {
    event.preventDefault();
    setError("");
    if (!question) return;
    if (selecionados.length === 0) {
      setError("Selecione uma resposta antes de continuar.");
      return;
    }

    const rotulos = question.opcoes
      .filter((opcao) => selecionados.includes(opcao.valor))
      .map((opcao) => opcao.rotulo);
    const valor = question.multipla ? [...selecionados] : selecionados[0];
    setAnswers((atual) => ({ ...atual, [question.id]: valor }));

    const proxima = currentQuestion + 1;
    setMessages((atual) => {
      const novas = [...atual, { role: "user", text: rotulos.join(", ") }];
      if (proxima < questions.length) {
        novas.push({ role: "assistant", text: questions[proxima].pergunta });
      } else {
        novas.push({ role: "assistant", text: TEXTO_PROMPT });
      }
      return novas;
    });
    setCurrentQuestion(proxima);
  }

  async function enviarTexto(event) {
    event.preventDefault();
    setError("");
    const texto = freeText.trim();

    if (!texto || texto.length > 500) {
      setError("Descreva sua necessidade com até 500 caracteres.");
      return;
    }

    setSubmitting(true);
    try {
      const envelope = await orchestrate("/demandas", {
        method: "POST",
        actor,
        body: { lojista_id: actor.id, respostas: answers, texto_livre: texto },
      });
      const resultado = unwrap(envelope);
      const avisos = envelope?.orquestracao?.avisos || [];
      if (avisos.length) {
        sessionStorage.setItem(AVISOS_KEY, JSON.stringify(avisos));
      } else {
        sessionStorage.removeItem(AVISOS_KEY);
      }
      if (!Number.isInteger(resultado?.demanda_id)) {
        throw new Error("Não foi possível registrar seu pedido. Tente novamente.");
      }
      window.location.assign(
        `/resultados.html?demanda_id=${encodeURIComponent(resultado.demanda_id)}`,
      );
    } catch (falha) {
      setError(falha.message || String(falha));
    } finally {
      setSubmitting(false);
    }
  }

  if (!actor || actor.perfil !== "lojista") return null;

  return (
    <>
      <LojistaSidebar active="chat" name={profileName} />

      <div className="app-area">
        <header className="topbar">
          <nav className="breadcrumbs" aria-label="Breadcrumb">
            <a href="/" aria-label="Início">
              <Icon name="home" />
            </a>
            <span aria-hidden="true">›</span>
            <span>Encontrar soluções</span>
            <span aria-hidden="true">›</span>
            <strong>Passo a passo</strong>
          </nav>
        </header>

        <main className="page-content">
          <div className="page-heading">
            <h1>Vamos entender seu negócio</h1>
            <p>Responda algumas perguntas para encontrar soluções compatíveis</p>
          </div>

          <section className="chat-card" aria-label="Perguntas sobre seu negócio">
            <header className="chat-header">
              <div className="chat-title">
                <span className="chat-status-dot" aria-hidden="true" />
                <strong>Perguntas sobre seu negócio</strong>
              </div>
              <div className="progress-area">
                <span id="progress-label">
                  {loading ? "Preparando diagnóstico..." : `Etapa ${etapaAtual} de ${total}`}
                </span>
                <span className="progress-track" aria-hidden="true">
                  <span className="progress-value" style={{ width: `${progresso}%` }} />
                </span>
                <span className="progress-badge">{badge}</span>
              </div>
            </header>

            <div className="chat-body">
              <div className="conversation" ref={conversationRef} aria-live="polite">
                {messages.map((message, index) => (
                  <div className={`message-row ${message.role}`} key={`${message.role}-${index}`}>
                    <div className="message-bubble">{message.text}</div>
                  </div>
                ))}
              </div>

              {error ? (
                <div className="chat-error" role="alert">
                  {error}
                </div>
              ) : null}

              {!loading && question ? (
                <form className="answer-form" onSubmit={responder}>
                  <fieldset className="answer-fieldset">
                    <legend>{question.pergunta}</legend>
                    <div className="answer-options">
                      {question.opcoes.map((opcao) => (
                        <label className="answer-option" key={opcao.valor}>
                          <input
                            type={question.multipla ? "checkbox" : "radio"}
                            name="chat-answer"
                            value={opcao.valor}
                            checked={selecionados.includes(opcao.valor)}
                            onChange={() => alternarOpcao(opcao.valor)}
                          />
                          <span>{opcao.rotulo}</span>
                        </label>
                      ))}
                    </div>
                  </fieldset>
                  <div className="form-actions">
                    <span className="form-hint">
                      {question.multipla
                        ? "Selecione uma ou mais opções."
                        : "Selecione uma opção para continuar."}
                    </span>
                    <button className="primary-button" type="submit">
                      Enviar resposta
                    </button>
                  </div>
                </form>
              ) : null}

              {noTexto ? (
                <form className="text-form" onSubmit={enviarTexto}>
                  <label className="text-prompt" htmlFor="free-text">
                    <span className="prompt-icon" aria-hidden="true">
                      ✦
                    </span>
                    {TEXTO_PROMPT}
                  </label>
                  <textarea
                    id="free-text"
                    name="texto_livre"
                    rows="4"
                    maxLength="500"
                    required
                    placeholder="Descreva detalhadamente..."
                    value={freeText}
                    onChange={(event) => setFreeText(event.target.value)}
                  />
                  <div className="form-actions text-actions">
                    <span className="form-hint">
                      <span>{freeText.length}</span>/500 caracteres
                    </span>
                    <button className="primary-button" type="submit" disabled={submitting}>
                      {submitting ? "Analisando..." : "Analisar necessidade"}
                    </button>
                  </div>
                </form>
              ) : null}
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
