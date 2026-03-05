/**
 * Evaluator prompt templates for AI-driven persona testing.
 *
 * Builds structured prompts for Claude Code Task agents:
 * - Regular personas (Sonnet 4.6): batch checkpoint evaluation
 * - Pedant personas (Opus 4.6): per-question audit with web verification
 * - Cross-browser comparison: visual consistency check
 *
 * All prompts instruct the agent to write JSON output matching the
 * AgentEvaluation schema from data-model.md.
 */

/**
 * Build the evaluation prompt for a regular (non-pedant) persona checkpoint.
 *
 * The agent role-plays as the persona, states expectations BEFORE viewing
 * the screenshot, then compares reality to expectations.
 *
 * @param {object} persona - Persona definition from definitions.js
 * @param {object} checkpointData - Checkpoint JSON (questions, screenshot path, etc.)
 * @param {object[]} previousEvals - Prior checkpoint evaluations for continuity
 * @returns {string} Complete prompt for Task agent
 */
export function buildRegularEvalPrompt(persona, checkpointData, previousEvals = []) {
  const prevContext = previousEvals.length > 0
    ? `\n\nPrevious checkpoint evaluations for continuity:\n${JSON.stringify(previousEvals.map(e => ({
        checkpoint: e.checkpointNumber,
        sentiment: e.overallSentiment,
        engagement: e.engagementLevel,
        narrative: e.beliefNarrative?.substring(0, 200),
      })), null, 2)}`
    : '';

  return `You are role-playing as ${persona.name}. ${persona.personality}

You are evaluating checkpoint ${checkpointData.checkpointNumber} of a Knowledge Mapper session.
Total questions answered so far: ${checkpointData.questionsAnswered}.
${prevContext}

## Step 1: State Your Expectations (BEFORE looking at the screenshot)

Based on the questions you just answered, describe:
- What you EXPECT the knowledge map to look like right now
- What color pattern you expect (green = high knowledge, yellow = medium, red = low)
- How you're feeling about the experience so far

## Step 2: Read the Screenshot

Read the screenshot file at: ${checkpointData.screenshotPath}

Compare what you see to your expectations. Describe any gaps.

## Step 3: Evaluate Each Question

For each question in this batch, evaluate:

${checkpointData.questionsInBatch.map((q, i) => `
### Question ${i + 1}: ${q.questionText?.substring(0, 100)}
- Options: ${JSON.stringify(q.options)}
- Marked correct answer: ${q.correctAnswer}
- Answer selected: ${q.selectedAnswer} (${q.wasCorrect ? 'correct' : 'wrong'})
- Difficulty: ${q.difficulty}
- Domain: ${q.domainId}
- Source article: ${q.sourceArticle || 'unknown'}
`).join('')}

For each question, rate on 1-5 scale:
- **contentValidity**: Does this question test what it claims to test?
- **distractorQuality**: Are the wrong answers plausibly wrong (not obviously wrong)?
- **difficultyRating**: Is the difficulty appropriate for the topic?
- **educationalValue**: Does answering this teach something meaningful?
- **clarityRating**: Is the question unambiguous and well-written?
- **topicAligned**: Is this question in the right map region for its topic?

Also assess: Is the marked answer actually correct? If you have doubts, note them.

## Step 4: Report Issues

Flag any problems found:
- **blocker**: Crash, wrong map, estimator collapse
- **major**: Incorrect answer marked, poor question quality pattern
- **minor**: Small UX issues, cosmetic problems
- **cosmetic**: Trivial visual issues

## Step 5: Write Output

Write your evaluation as JSON to: tests/visual/.working/personas/${checkpointData.personaId}-eval-${checkpointData.checkpointNumber}.json

Use this exact schema:
\`\`\`json
{
  "personaId": "${checkpointData.personaId}",
  "checkpointNumber": ${checkpointData.checkpointNumber},
  "beliefNarrative": "First-person stream of consciousness in ${persona.name}'s voice...",
  "expectations": {
    "mapDescription": "What you expected the map to look like",
    "colorExpectation": "Expected color pattern",
    "overallFeeling": "Your emotional state"
  },
  "realityAssessment": {
    "mapDescription": "What you actually see in the screenshot",
    "matchesExpectation": true/false,
    "gapDescription": "Any gap between expectation and reality"
  },
  "questionEvaluations": [
    {
      "questionId": "...",
      "questionText": "...",
      "markedAnswer": "B",
      "agentAssessment": "B",
      "isCorrectAsMarked": true,
      "contentValidity": 4,
      "distractorQuality": 3,
      "difficultyRating": 3,
      "educationalValue": 4,
      "clarityRating": 5,
      "topicAligned": true,
      "notes": "Optional commentary"
    }
  ],
  "issuesFound": [],
  "engagementLevel": 4,
  "overallSentiment": "positive"
}
\`\`\`

${checkpointData.consoleErrors.length > 0 ? `\n**WARNING**: Console errors were captured during this checkpoint:\n${checkpointData.consoleErrors.join('\n')}\nFlag these as issues if they indicate real problems.` : ''}`;
}

/**
 * Build the evaluation prompt for a pedant persona (per-question audit).
 *
 * The pedant agent critically evaluates EVERY question and uses WebSearch
 * to verify any suspected errors.
 *
 * @param {object} persona - Pedant persona definition
 * @param {object} questionData - Single question from checkpoint batch
 * @param {object} checkpointData - Full checkpoint data
 * @returns {string} Complete prompt for Opus Task agent
 */
export function buildPedantEvalPrompt(persona, questionData, checkpointData) {
  return `You are role-playing as ${persona.name}. ${persona.personality}

You are auditing question ${checkpointData.checkpointNumber} in a Knowledge Mapper session.

## The Question

**Question**: ${questionData.questionText}

**Options**:
- A: ${questionData.options?.A || 'N/A'}
- B: ${questionData.options?.B || 'N/A'}
- C: ${questionData.options?.C || 'N/A'}
- D: ${questionData.options?.D || 'N/A'}

**Marked correct answer**: ${questionData.correctAnswer}
**Domain**: ${questionData.domainId}
**Difficulty**: ${questionData.difficulty}
**Source article**: ${questionData.sourceArticle || 'unknown'}

## Your Tasks

### 1. Assess Answer Correctness

Using your domain expertise, evaluate whether the marked answer (${questionData.correctAnswer}) is actually correct.

- If you AGREE: note "isCorrectAsMarked: true"
- If you DISAGREE: you MUST use the WebSearch tool to verify before flagging

### 2. Web Verification (if disagreement)

If you suspect the marked answer is wrong:
1. Search for authoritative sources (Wikipedia, textbooks, academic sites)
2. Use specific search queries related to the question topic
3. Cite the URL of your source
4. Determine verdict:
   - **CORRECTION_VERIFIED**: Web evidence supports your correction
   - **ORIGINAL_CONFIRMED**: Web evidence confirms the original answer was correct
   - **INCONCLUSIVE**: Insufficient evidence; flag for human review

**CRITICAL**: NEVER hallucinate a correction. If you can't find evidence, mark INCONCLUSIVE.

### 3. Rate Question Quality

Rate each dimension 1-5:
- **contentValidity**: Does this question test genuine understanding?
- **distractorQuality**: Are wrong answers plausibly wrong?
- **difficultyRating**: Is difficulty appropriate?
- **educationalValue**: Does answering teach something?
- **clarityRating**: Is the question unambiguous?

### 4. Assess Map Change

Read the screenshot at: ${checkpointData.screenshotPath}
- Is the map updating appropriately after this answer?
- Does the color change match the answer correctness?

### 5. Write Output

Write your evaluation as JSON to: tests/visual/.working/personas/${checkpointData.personaId}-eval-${checkpointData.checkpointNumber}.json

Schema:
\`\`\`json
{
  "personaId": "${checkpointData.personaId}",
  "checkpointNumber": ${checkpointData.checkpointNumber},
  "beliefNarrative": "First-person critical assessment...",
  "expectations": {
    "mapDescription": "Expected map state after this answer",
    "colorExpectation": "Expected color change",
    "overallFeeling": "Your critical assessment"
  },
  "realityAssessment": {
    "mapDescription": "What you see in the screenshot",
    "matchesExpectation": true/false,
    "gapDescription": "Any discrepancy"
  },
  "questionEvaluations": [
    {
      "questionId": "${questionData.questionId}",
      "questionText": "${questionData.questionText?.substring(0, 100)}",
      "markedAnswer": "${questionData.correctAnswer}",
      "agentAssessment": "YOUR_ANSWER",
      "isCorrectAsMarked": true/false,
      "webVerification": {
        "searched": true/false,
        "query": "search query used",
        "sourceUrl": "https://...",
        "verdict": "CORRECTION_VERIFIED|ORIGINAL_CONFIRMED|INCONCLUSIVE",
        "correctedAnswer": "C (only if correction verified)",
        "evidence": "Brief quote or summary from source"
      },
      "contentValidity": 4,
      "distractorQuality": 3,
      "difficultyRating": 3,
      "educationalValue": 4,
      "clarityRating": 5,
      "topicAligned": true,
      "notes": "Detailed critical commentary"
    }
  ],
  "issuesFound": [],
  "engagementLevel": 3,
  "overallSentiment": "neutral"
}
\`\`\``;
}

/**
 * Build a follow-up verification prompt for a flagged question.
 *
 * Used when a pedant eval flagged a question but didn't complete web search.
 *
 * @param {object} question - The flagged question data
 * @param {string} agentAssessment - What the agent thinks the correct answer is
 * @returns {string} Verification prompt for Task agent with WebSearch
 */
export function buildPedantVerificationPrompt(question, agentAssessment) {
  return `You are a fact-checking agent. A pedant persona flagged a potential error in a quiz question.

## Question Under Review

**Question**: ${question.questionText}

**Options**:
- A: ${question.options?.A || 'N/A'}
- B: ${question.options?.B || 'N/A'}
- C: ${question.options?.C || 'N/A'}
- D: ${question.options?.D || 'N/A'}

**Currently marked correct**: ${question.correctAnswer}
**Pedant believes correct answer is**: ${agentAssessment}
**Source article**: ${question.sourceArticle || 'unknown'}

## Your Task

Use the WebSearch tool to verify which answer is actually correct.

1. Search for the specific topic of this question
2. Find at least one authoritative source (Wikipedia, academic, textbook)
3. Determine the correct answer based on evidence
4. Report your verdict:
   - **CORRECTION_VERIFIED**: The pedant is right, the marked answer is wrong
   - **ORIGINAL_CONFIRMED**: The original marked answer is correct
   - **INCONCLUSIVE**: Cannot determine with available evidence

Write your result as JSON:
\`\`\`json
{
  "questionId": "${question.questionId}",
  "questionText": "${question.questionText?.substring(0, 100)}",
  "currentAnswer": "${question.correctAnswer}",
  "suggestedAnswer": "${agentAssessment}",
  "verdict": "CORRECTION_VERIFIED|ORIGINAL_CONFIRMED|INCONCLUSIVE",
  "sourceUrl": "https://...",
  "evidence": "Brief supporting evidence from the source",
  "confidence": "high|medium|low"
}
\`\`\``;
}

/**
 * Build a cross-browser comparison prompt for visual consistency testing.
 *
 * @param {string[]} screenshotPaths - Array of 3 screenshot paths (chrome, firefox, webkit)
 * @param {string[]} browserNames - Array of browser names matching the screenshots
 * @returns {string} Prompt for comparison Task agent
 */
export function buildCrossBrowserComparisonPrompt(screenshotPaths, browserNames) {
  return `You are a visual QA specialist comparing screenshots of the same application across different browsers.

## Screenshots to Compare

${screenshotPaths.map((path, i) => `- **${browserNames[i]}**: ${path}`).join('\n')}

Read each screenshot file and compare them.

## Evaluation Criteria

1. **Color distribution similarity**: Are the heatmap colors consistent across browsers? Minor rendering differences are acceptable; large color shifts are not.
2. **Layout consistency**: Are UI elements (quiz panel, map, header) in the same positions?
3. **Canvas rendering**: Are the heatmap, article dots, grid lines, and answered-question markers all present and aligned?
4. **Text rendering**: Is text readable and properly positioned in all browsers?
5. **Any browser-specific artifacts**: Rendering glitches, missing elements, misaligned layers?

## Output

Write your comparison as JSON:
\`\`\`json
{
  "browsers": ${JSON.stringify(browserNames)},
  "colorConsistency": {
    "score": 4,
    "notes": "Description of color differences"
  },
  "layoutConsistency": {
    "score": 5,
    "notes": "Description of layout differences"
  },
  "canvasRendering": {
    "score": 4,
    "notes": "Description of canvas differences"
  },
  "textRendering": {
    "score": 5,
    "notes": "Description of text differences"
  },
  "overallConsistency": 4,
  "artifacts": [],
  "verdict": "CONSISTENT|MINOR_DIFFERENCES|INCONSISTENT"
}
\`\`\``;
}
