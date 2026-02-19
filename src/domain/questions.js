/** Question filtering and retrieval by domain and answer history. */

const questionIndex = new Map();

export function indexQuestions(questions) {
  for (const q of questions) {
    if (!questionIndex.has(q.id)) {
      questionIndex.set(q.id, q);
    }
  }
}

export function getAvailableQuestions(domainBundle, answeredIds) {
  return domainBundle.questions.filter((q) => !answeredIds.has(q.id));
}

export function getQuestionById(id) {
  return questionIndex.get(id);
}

export function getOverlappingQuestions(domainId, questions) {
  return questions.filter(
    (q) => q.domain_ids.length > 1 && q.domain_ids.includes(domainId)
  );
}

export function clearIndex() {
  questionIndex.clear();
}
