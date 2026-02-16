/** Adaptive question selection with multi-level curriculum and uncertainty sampling. */

export class Sampler {
  selectNext(questions, estimates, viewport, answeredIds) {
    throw new Error('Not implemented: Sampler.selectNext');
  }

  selectByMode(mode, questions, estimates, viewport, answeredIds) {
    throw new Error('Not implemented: Sampler.selectByMode');
  }

  scoreAll(questions, estimates, viewport, answeredIds) {
    throw new Error('Not implemented: Sampler.scoreAll');
  }
}
