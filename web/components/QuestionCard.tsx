"use client";
import { useState } from "react";
import type { Question, SavedAnswer } from "@/lib/types";

interface QuestionCardProps {
  question: Question;
  index: number;
  savedAnswer?: SavedAnswer;
  onAnswer: (id: string, letter: string, correct: boolean) => void;
  onClear: (id: string) => void;
}

const TYPE_LABELS: Record<string, string> = {
  MULTIPLE_CHOICE: "Multipla Escolha",
  MULTIPLE_CHOICE_FOUR: "Multipla Escolha (4)",
  TRUE_OR_FALSE: "Certo/Errado",
  DISCURSIVE: "Discursiva",
};

export function QuestionCard({
  question: q,
  index,
  savedAnswer,
  onAnswer,
  onClear,
}: QuestionCardProps) {
  const [selected, setSelected] = useState<string | null>(
    savedAnswer?.s || null
  );
  const [revealed, setRevealed] = useState(!!savedAnswer);
  const [showSolution, setShowSolution] = useState(false);

  const locked = revealed;
  const isCorrectAnswer = savedAnswer?.c;

  const topicStr =
    q.topics.map((t) => t.n).join(", ") || "Sem especialidade";

  const handleSelect = (letter: string) => {
    if (locked) return;
    setSelected(letter);
  };

  const handleConfirm = () => {
    if (!selected) return;
    const correct = q.alternatives.find((a) => a.letter === selected)?.correct;
    setRevealed(true);
    onAnswer(q.id, selected, !!correct);
  };

  const handleReset = () => {
    setSelected(null);
    setRevealed(false);
    setShowSolution(false);
    onClear(q.id);
  };

  // Video embed
  let videoEmbed = "";
  if (q.video_url) {
    const v = q.video_url;
    if (v.includes("youtube.com/watch"))
      videoEmbed = `https://www.youtube.com/embed/${v.split("v=")[1]?.split("&")[0]}`;
    else if (v.includes("youtu.be/"))
      videoEmbed = `https://www.youtube.com/embed/${v.split("youtu.be/")[1]?.split("?")[0]}`;
  }

  const meta = [q.institution, q.year ? String(q.year) : ""].filter(Boolean).join(" · ");

  const badgeYear = meta ? <span className="badge badge-year">{meta}</span> : null;
  const badgeType = (
    <span className="badge badge-type">
      {TYPE_LABELS[q.answer_type] || q.answer_type}
    </span>
  );
  const badgeTopic = <span className="badge badge-topic">{topicStr}</span>;
  const badgeBanca = q.banca ? (
    <span className="badge badge-specialty">{q.banca}</span>
  ) : null;

  return (
    <div
      className={[
        "question-card",
        "question",
        locked ? (isCorrectAnswer ? "answered-correct" : "answered-wrong") : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="question-header">
        <span className="question-number">#{index + 1}</span>
        <div className="question-meta">
          {badgeYear}
          {badgeType}
          {badgeTopic}
          {badgeBanca}
          {q.labels.map((l) => {
            const up = l.toUpperCase();
            if (up.includes("CANCEL"))
              return (
                <span key={l} className="badge badge-anulada">
                  Anulada
                </span>
              );
            if (up.includes("OUTDAT"))
              return (
                <span key={l} className="badge badge-outdated">
                  Desatualizada
                </span>
              );
            return null;
          })}
        </div>
      </div>

      <div className="enunciado question-html" dangerouslySetInnerHTML={{ __html: q.statement }} />

      <div className="alternativas">
        {q.alternatives.map((alt) => {
          const isSelected = selected === alt.letter;
          const isWrongSelected = locked && isSelected && !alt.correct;

          const altClasses = [
            "alternativa",
            "alt",
            !locked && isSelected ? "selected" : "",
            locked && alt.correct ? "correct-reveal" : "",
            isWrongSelected ? "wrong-reveal" : "",
            locked && !isSelected && !alt.correct ? "dimmed" : "",
            locked ? "locked" : "",
          ]
            .filter(Boolean)
            .join(" ");

          return (
            <div
              key={alt.letter}
              className={altClasses}
              onClick={() => handleSelect(alt.letter)}
            >
              <div className="letra">{alt.letter}</div>
              <div
                className="texto-alt question-html"
                dangerouslySetInnerHTML={{ __html: alt.body }}
              />
            </div>
          );
        })}
      </div>

      {locked && (
        <div
          className={[
            "result-banner",
            "show",
            isCorrectAnswer ? "correct" : "wrong",
          ].join(" ")}
        >
          {isCorrectAnswer
            ? "Voce acertou!"
            : `Voce errou. Gabarito: ${q.correct_letter}`}
        </div>
      )}

      <div className="q-actions">
        {!locked && (
          <button
            type="button"
            className="btn btn-confirm"
            onClick={handleConfirm}
            disabled={!selected}
          >
            Confirmar resposta
          </button>
        )}
        <button
          type="button"
          className="btn btn-show"
          onClick={() => setShowSolution(!showSolution)}
        >
          {showSolution ? "Ocultar gabarito" : "Ver gabarito"}
        </button>
        {locked && (
          <button
            type="button"
            className="btn btn-reset"
            onClick={handleReset}
          >
            Refazer
          </button>
        )}
      </div>

      {showSolution && (
        <div className="answer-section comentario">
          <div className="gabarito">
            <strong>Gabarito:</strong> {q.correct_letter}
          </div>

          {q.solution && (
            <div
              className="solution-text-content question-html"
              dangerouslySetInnerHTML={{ __html: q.solution }}
            />
          )}

          {(videoEmbed || q.video_url) && (
            <div className="video-solution">
              <strong>Correcao em Video:</strong>
              {videoEmbed ? (
                <iframe src={videoEmbed} allowFullScreen loading="lazy" />
              ) : (
                <a href={q.video_url} target="_blank" rel="noopener">
                  Assistir video
                </a>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
