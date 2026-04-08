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

  const borderClass = locked
    ? isCorrectAnswer
      ? "border-correct/50"
      : "border-incorrect/50"
    : "border-border hover:border-accent";

  // Video embed
  let videoEmbed = "";
  if (q.video_url) {
    const v = q.video_url;
    if (v.includes("youtube.com/watch"))
      videoEmbed = `https://www.youtube.com/embed/${v.split("v=")[1]?.split("&")[0]}`;
    else if (v.includes("youtu.be/"))
      videoEmbed = `https://www.youtube.com/embed/${v.split("youtu.be/")[1]?.split("?")[0]}`;
  }

  return (
    <div
      className={`bg-card rounded-2xl p-7 mb-5 border-2 transition-all ${borderClass}`}
    >
      {/* Header */}
      <div className="flex justify-between items-center mb-4 pb-3 border-b border-border flex-wrap gap-2">
        <span className="font-bold text-accent">#{index + 1}</span>
        <div className="flex gap-1.5">
          <span className="badge-type">
            {TYPE_LABELS[q.answer_type] || q.answer_type}
          </span>
          {q.labels.map((l) =>
            l.toUpperCase().includes("CANCEL") ? (
              <span key={l} className="badge-cancel">
                Anulada
              </span>
            ) : l.toUpperCase().includes("OUTDAT") ? (
              <span key={l} className="badge-outdat">
                Desatualizada
              </span>
            ) : null
          )}
        </div>
      </div>

      {/* Meta */}
      <div className="text-sm text-muted mb-2">
        {q.institution} {q.year || ""} | {q.banca}
      </div>
      <div className="text-sm text-accent font-semibold mb-3">{topicStr}</div>

      {/* Statement */}
      <div
        className="leading-relaxed mb-5 text-[15px] question-html"
        dangerouslySetInnerHTML={{ __html: q.statement }}
      />

      {/* Alternatives */}
      <div className="flex flex-col gap-3 mb-4">
        {q.alternatives.map((alt) => {
          let altClass =
            "flex items-start gap-3 p-4 rounded-xl cursor-pointer transition-all border-2 text-sm leading-relaxed";

          if (locked) {
            altClass += " pointer-events-none";
            if (alt.correct) altClass += " border-correct/80 bg-correct/10";
            else if (alt.letter === selected && !alt.correct)
              altClass += " border-incorrect/80 bg-incorrect/10";
            else altClass += " border-transparent opacity-40";
          } else if (selected === alt.letter) {
            altClass += " border-accent bg-accent/10";
          } else {
            altClass +=
              " border-transparent bg-hover hover:bg-[#2a2a2a] hover:translate-x-1";
          }

          let letterClass =
            "w-9 h-9 flex items-center justify-center rounded-lg font-bold text-sm flex-shrink-0 transition-all";
          if (locked && alt.correct)
            letterClass += " bg-correct text-white";
          else if (locked && alt.letter === selected && !alt.correct)
            letterClass += " bg-incorrect text-white";
          else if (selected === alt.letter)
            letterClass += " bg-accent text-dark";
          else letterClass += " bg-border text-white";

          return (
            <div
              key={alt.letter}
              className={altClass}
              onClick={() => handleSelect(alt.letter)}
            >
              <div className={letterClass}>{alt.letter}</div>
              <div
                className="flex-1 pt-1 question-html"
                dangerouslySetInnerHTML={{ __html: alt.body }}
              />
            </div>
          );
        })}
      </div>

      {/* Result banner */}
      {locked && (
        <div
          className={`p-3 rounded-xl font-semibold text-sm mb-3 ${
            isCorrectAnswer
              ? "bg-correct/10 text-correct"
              : "bg-incorrect/10 text-incorrect"
          }`}
        >
          {isCorrectAnswer
            ? "Voce acertou!"
            : `Voce errou. Gabarito: ${q.correct_letter}`}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 flex-wrap">
        {!locked && (
          <button
            onClick={handleConfirm}
            disabled={!selected}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-accent text-dark disabled:bg-border disabled:text-muted transition-colors"
          >
            Confirmar
          </button>
        )}
        <button
          onClick={() => setShowSolution(!showSolution)}
          className="px-4 py-2 rounded-xl text-xs font-semibold bg-hover text-white hover:bg-[#2a2a2a] transition-colors"
        >
          {showSolution ? "Ocultar" : "Ver Gabarito"}
        </button>
        {locked && (
          <button
            onClick={handleReset}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-yellow-400/20 text-yellow-400 hover:bg-yellow-400/30 transition-colors"
          >
            Refazer
          </button>
        )}
      </div>

      {/* Solution */}
      {showSolution && (
        <div className="mt-4 p-4 bg-dark rounded-2xl border border-border">
          <h4 className="text-correct font-semibold mb-2">
            Gabarito: {q.correct_letter}
          </h4>
          {q.solution && (
            <div
              className="leading-relaxed text-sm text-muted question-html"
              dangerouslySetInnerHTML={{ __html: q.solution }}
            />
          )}
          {videoEmbed && (
            <div className="mt-3">
              <iframe
                src={videoEmbed}
                className="w-full h-[340px] rounded-xl"
                allowFullScreen
                loading="lazy"
              />
            </div>
          )}
          {q.video_url && !videoEmbed && (
            <a
              href={q.video_url}
              target="_blank"
              rel="noopener"
              className="text-accent text-sm font-semibold hover:underline"
            >
              Assistir video
            </a>
          )}
        </div>
      )}
    </div>
  );
}
