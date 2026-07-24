// Animalese.js - AC villager voice synthesizer
// Josh Simmons (Acedio), modified for GradManager error correction

export class Animalese {
  constructor(letters_path, callback) {
    this.letters_path = letters_path;
    this.callback = callback;
  }
}

/**
 * processFallback
 * 37라인에서 발생하던 null/undefined 시작 검증 오류를 예방하는 안전한 타입 검사 추가
 */
export function processFallback(text) {
  if (typeof text === 'string' && text.startsWith('data:audio/wav;base64,')) {
    return text;
  }
  // optional chaining or safe fallback return
  return text?.startsWith?.('data:audio/wav;') ? text : '';
}
