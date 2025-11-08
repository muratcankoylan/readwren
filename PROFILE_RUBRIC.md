# Literary Profile Metrics Rubric

This document defines the scoring system and meaning of all metrics in user literary profiles.

## Style Signature Metrics

All style metrics are scored 0-100.

### Prose Density (0-100)

How much the reader tolerates or prefers compressed, layered prose.

- **0-20**: Prefers sparse, minimalist prose (Hemingway, Carver)
- **21-40**: Likes clean, direct writing with occasional flourishes
- **41-60**: Balanced - appreciates both clarity and complexity
- **61-80**: Enjoys dense, literary prose that rewards close reading
- **81-100**: Craves maximum density (Pynchon, Joyce, difficult modernists)

**Example 75**: "Enjoys prose dense enough to require active reading, not passive consumption. Tolerates complexity when it serves meaning."

### Pacing (0-100)

Speed preference from contemplative to rapid.

- **0-20**: Extremely slow, meditative, philosophical
- **21-40**: Slow burn, character-focused, gradual development
- **41-60**: Moderate pacing with mix of action and reflection
- **61-80**: Brisk pacing, plot-driven with momentum
- **81-100**: Rapid, thriller-pace, constant movement

**Example 35**: "Prefers slow-burn narratives that allow for reflection and character depth over plot velocity."

### Tone (0-100)

From dark/serious to light/humorous.

- **0-20**: Unrelentingly dark, tragic, pessimistic
- **21-40**: Serious, melancholic, bittersweet
- **41-60**: Balanced tone with light and shadow
- **61-80**: Generally optimistic with moments of conflict
- **81-100**: Light, comedic, satirical, humorous

**Example 30**: "Gravitates toward serious, contemplative tones. Comfortable with melancholy and ambiguity."

### Worldbuilding (0-100)

How much systematic world construction the reader values.

- **0-20**: Minimal worldbuilding, focuses on character/emotion
- **21-40**: Light worldbuilding as backdrop
- **41-60**: Moderate worldbuilding that serves story
- **61-80**: Rich, detailed worlds that feel lived-in
- **81-100**: Intricate systems, encyclopedic detail (Tolkien, Herbert)

**Example 70**: "Values detailed, thought-through worlds. Appreciates when speculative elements follow internal logic."

### Character Focus (0-100)

How much the reader prioritizes character depth.

- **0-20**: Plot/ideas over character (hard SF, thriller)
- **21-40**: Character serves plot
- **41-60**: Balanced character and plot
- **61-80**: Character-driven with strong interiority
- **81-100**: Deeply psychological, all about inner life

**Example 85**: "Strongly character-driven reader. Needs rich interiority and psychological depth. Plot serves character."

## Implicit Signals

### Vocabulary Richness (0.0-1.0)

Measured from user responses during interview.

- **0.0-0.3**: Basic vocabulary, simple constructions
- **0.31-0.5**: Standard vocabulary, clear expression
- **0.51-0.7**: Above-average vocabulary, varied syntax
- **0.71-0.85**: Rich vocabulary, complex sentences
- **0.86-1.0**: Highly sophisticated, literary vocabulary

**Example 0.85**: "Uses phrases like 'refracted through a prism,' 'absurdist grief,' 'weaponize normalcy' - indicates comfort with abstract, literary language."

### Response Brevity Score (0.0-1.0)

Average length/detail of interview responses.

- **0.0-0.2**: Very long, detailed, essay-like responses
- **0.21-0.4**: Moderate-length, thoughtful responses
- **0.41-0.6**: Balanced brevity and detail
- **0.61-0.8**: Concise, to-the-point responses
- **0.81-1.0**: Extremely brief, minimal elaboration

**Example 0.35**: "Provides detailed, thoughtful responses with examples and metaphors. Not rushed in expression."

### Engagement Index (0.0-1.0)

How actively engaged the user is with the interview.

- **0.0-0.3**: Minimal engagement, short answers, low investment
- **0.31-0.5**: Basic engagement, answers questions adequately
- **0.51-0.7**: Good engagement, thoughtful responses
- **0.71-0.85**: High engagement, insightful, self-reflective
- **0.86-1.0**: Maximum engagement, deeply analytical, meta-commentary

**Example 0.9**: "Highly engaged. Uses metaphors ('lectured by a statue'), self-reflection, and shows awareness of own preferences."

## Consumption Habits

### Daily Time Minutes (15-180)

Estimated daily reading time based on engagement signals.

- **15-30**: Casual reader, occasional reading
- **31-45**: Regular reader, consistent habit
- **46-60**: Dedicated reader, daily priority
- **61-90**: Serious reader, significant time commitment
- **91-180**: Intensive reader, reading is lifestyle

**Example 45**: "Likely dedicates 45 minutes daily - consistent reading habit without being obsessive."

### Delivery Frequency

How often user wants story content.

- **"daily"**: Regular reading habit
- **"every_few_days"**: Periodic reader
- **"weekly"**: Weekend/batched reading
- **"binge"**: Irregular, intensive sessions

### Pages Per Delivery (5-50)

How much content per session.

- **5-10**: Short bursts, attention-constrained
- **11-20**: Standard reading session
- **21-35**: Solid reading session
- **36-50**: Extended, immersive sessions

**Example 20**: "Comfortable with 20-page sessions - substantial but not marathon reading."

## Narrative Desires

### Wish

A one-sentence synthesis of the reader's ideal story, written in their voice and capturing their specific intersection of interests.

**Good Example**: 
"A speculative fiction that uses philosophical premises to explore profound human loneliness and cultural disconnection, where the intellectual framework serves as a prism for emotional truth rather than mere escapism."

**Why it works**: Specific genre + philosophical bent + emotional core + explicit rejection of surface-level entertainment.

### Preferred Ending

- **"happy"**: Optimistic resolution, conflicts resolved
- **"bittersweet"**: Mixed emotions, pyrrhic victory, growth through loss
- **"ambiguous"**: Open-ended, unresolved, interpretive
- **"tragic"**: Dark ending, failure, loss
- **"transcendent"**: Goes beyond traditional categories

### Themes (3-8 themes)

Key thematic interests identified from conversation.

Should be specific enough to be actionable:
- Good: "loneliness and cultural fracture"
- Too vague: "relationships"
- Good: "memory and identity"
- Too vague: "psychology"

## Metadata

### Interview Turns

Number of questions answered before profile generation.

- **1-3**: Very limited data, extrapolation heavy
- **4-7**: Partial interview, reasonable confidence
- **8-10**: Substantial data, high confidence
- **11-12**: Complete interview, maximum confidence

### Completion Status

- **"complete"**: Full 12-turn interview
- **"early_exit"**: User quit via command
- **"interrupted"**: Ctrl+C or error

### Early Termination

Boolean indicating if interview ended before 12 turns. Affects confidence in extrapolated data.

## Using This Rubric

### For Profile Interpretation

When reading a profile, cross-reference metrics with this rubric:

```json
"prose_density": 75,
"pacing": 35,
"character_focus": 85
```

**Interpretation**: Dense literary prose + slow burn + deeply psychological = literary fiction reader who values interiority and complex language over plot velocity.

### For Profile Generation

The ProfileGeneratorAgent uses this rubric to:
1. Score metrics consistently across users
2. Generate explanations that reference these scales
3. Ensure scores align with conversation evidence

### For Recommendation Systems

Metrics can be used to:
- Match readers with similar preferences
- Find books that fit specific metric profiles
- Identify anti-patterns (avoid books with opposite metrics)

## Score Consistency Guidelines

### Internal Coherence

Certain metric combinations are more coherent:

**Coherent**:
- High prose_density (75) + High character_focus (85) = Literary fiction
- Low pacing (25) + High worldbuilding (80) = Epic fantasy
- High tone (75) + Medium pacing (50) = Contemporary rom-com

**Incoherent** (flag for review):
- High prose_density (85) + High pacing (90) = Rare, possibly thriller with literary prose
- Low character_focus (20) + High tone (80) = Unusual, maybe satire

### Evidence Requirements

Each score should be supportable from interview:

- **Strong evidence** (2+ clear examples): High confidence score
- **Moderate evidence** (1 example + inference): Medium confidence
- **Weak evidence** (inference only): Note in `_metadata` that score is extrapolated

## Future Enhancements

### Confidence Scores

Add confidence to each metric:

```json
"style_signature": {
  "prose_density": 75,
  "prose_density_confidence": 0.85,
  "pacing": 35,
  "pacing_confidence": 0.6
}
```

### Comparative Metrics

"Your prose_density (75) is higher than 78% of readers" - percentile rankings.

### Evolution Tracking

Track how profiles change over time as users read more and preferences shift.

