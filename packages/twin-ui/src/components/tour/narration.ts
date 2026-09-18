// The narration channel. Tier 0 (captions) is rendered by the player and is
// always on; this is tier 1, the browser's own speech synthesis. No audio
// files, no network. Tier 2 (a step's pre-rendered audioUrl) is not used by
// the pilot.

export function speechSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window &&
    typeof window.SpeechSynthesisUtterance !== "undefined";
}

/**
 * Speak `text` at `rate`, replacing anything already being said. Calls
 * `onDone` exactly once, whether the utterance ends, errors, or is cancelled.
 */
export function speak(text: string, rate: number, onDone: () => void): () => void {
  if (!speechSupported()) {
    onDone();
    return () => {};
  }
  let finished = false;
  const finish = () => {
    if (finished) return;
    finished = true;
    onDone();
  };
  const synth = window.speechSynthesis;
  synth.cancel();
  // One utterance per sentence: Chrome silently drops a long utterance after
  // about fifteen seconds without firing onend, which would hang the tour.
  const sentences = text.split(/(?<=[.!?])\s+/).filter((t) => t.trim());
  const queue = sentences.map((sentence, i) => {
    const u = new SpeechSynthesisUtterance(sentence);
    u.rate = Math.min(2, Math.max(0.5, rate));
    u.onerror = finish;
    if (i === sentences.length - 1) u.onend = finish;
    return u;
  });
  if (queue.length === 0) finish();
  queue.forEach((u) => synth.speak(u));
  return () => {
    queue.forEach((u) => {
      u.onend = null;
      u.onerror = null;
    });
    synth.cancel();
    finish();
  };
}

export function silence(): void {
  if (speechSupported()) window.speechSynthesis.cancel();
}
