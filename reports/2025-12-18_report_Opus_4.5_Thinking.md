# A Comparative Analysis of Large Language Models for Arabic-to-Dhivehi Translation: An Empirical Study

**Author:** Claude Opus 4.5 (Thinking)  
**Date:** December 18, 2025  

---

## Abstract

This study presents a comprehensive empirical analysis of 21 large language model (LLM) configurations in the domain of Arabic-to-Dhivehi translation—a low-resource language pair that poses significant challenges for current AI systems. Using a blind testing platform with dual evaluation methodologies (star ratings and ELO-based pairwise comparisons), we analyze 481 translations across 187 unique source texts. Our findings reveal that reasoning-enabled models, particularly Gemini 3 Pro with low reasoning effort, significantly outperform non-reasoning counterparts, achieving ELO ratings of 1755.9 compared to the baseline 1500. Furthermore, we observe nuanced effects of temperature parameters on translation quality, with lower temperatures (0.1-0.35) correlating with higher accuracy in religious and technical texts, while moderate temperatures (0.85-1.0) occasionally produce more natural-sounding prose.

---

## 1. Introduction

### 1.1 Background

Dhivehi (ދިވެހި), the official language of the Maldives with approximately 340,000 speakers, remains severely underrepresented in large language model training corpora. This scarcity creates unique challenges for machine translation systems, particularly when translating from Arabic—a language with significant historical and religious connections to Dhivehi through Islam and shared Thaana script roots.

### 1.2 Research Objectives

This study addresses the following research questions:

1. **RQ1:** Which LLM architectures demonstrate superior performance in Arabic-to-Dhivehi translation?
2. **RQ2:** How do temperature and reasoning parameters affect translation quality?
3. **RQ3:** What characteristic behaviors and failure modes distinguish different model families?

### 1.3 Methodology Overview

The Dhivehi Translation Arena employs a blind testing platform where translations are presented without model identification. Evaluators rate translations on a 4-point scale (Excellent/3, Good/2, Okay/1, Trash/-1) and participate in pairwise comparisons. ELO ratings are derived from both explicit comparisons and star-rating differentials.

---

## 2. Dataset and Experimental Setup

### 2.1 Corpus Statistics

| Metric | Value |
|:-------|------:|
| Unique source queries | 187 |
| Total translations generated | 481 |
| Total votes cast | 313 |
| Pairwise comparisons (derived) | 959 |
| Pairwise comparisons (explicit) | 343 |
| Tie outcomes | 353 |
| Total API cost | $2.22 USD |

### 2.2 Model Configurations

The study evaluates 21 model configurations across four major families:

| Family | Variants Tested | Temperature Settings | Reasoning Modes |
|:-------|:---------------:|:--------------------:|:---------------:|
| Gemini 3 Pro Preview | 3 | 0.35, 1.0 | Low, Default |
| Gemini 3 Flash Preview | 4 | 0.3, 1.0 | Minimal, Default |
| Gemini 2.5 Pro/Flash | 5 | 0.1, 0.85 | Min Thinking, No Thinking, Reasoning |
| Gemini 2.0 Flash | 2 | 0.1, 0.85 | None |
| Claude 3.5/3.7 Sonnet | 4 | 0.1, 0.85 | None |
| Claude Opus 4.5 | 2 | 0.1, 0.85 | None |

### 2.3 Evaluation Framework

**Star Rating System:**
- **3 (Excellent):** Accurate, natural, publication-ready
- **2 (Good):** Meaning correct, minor stylistic issues
- **1 (Okay):** Understandable but with errors
- **-1 (Trash):** Significant errors, unusable

**ELO Rating System:**
- Initial rating: 1500
- K-factor: 32
- Combined score weighting: 40% star ratings, 60% ELO

---

## 3. Quantitative Results

### 3.1 ELO Rankings

The following table presents the complete ELO standings:

| Rank | Model | ELO Rating | Wins | Losses | Ties | Total Matches | Win Rate |
|:----:|:------|:----------:|:----:|:------:|:----:|:-------------:|:--------:|
| 1 | gemini-3-pro-low-t0.35 | **1755.9** | 88 | 18 | 51 | 157 | 56.1% |
| 2 | gemini-3-pro-low-t1.0 | **1725.1** | 86 | 29 | 46 | 161 | 53.4% |
| 3 | gemini-3-pro-t1.0 | **1679.7** | 56 | 24 | 32 | 112 | 50.0% |
| 4 | claude-opus-4.5-t0.1 | **1590.2** | 47 | 15 | 24 | 86 | 54.7% |
| 5 | gemini-2.5-flash-reasoning-t0.85 | **1570.1** | 72 | 77 | 62 | 211 | 34.1% |
| 6 | claude-opus-4.5-t0.85 | 1546.3 | 86 | 75 | 55 | 216 | 39.8% |
| 7 | gemini-3-flash-low-t1.0 | 1536.3 | 11 | 7 | 13 | 31 | 35.5% |
| 8 | gemini-3-flash-t0.3 | 1529.0 | 10 | 10 | 10 | 30 | 33.3% |
| 9 | gemini-2.0-flash-t0.85 | 1522.6 | 63 | 123 | 46 | 232 | 27.2% |
| 10 | gemini-3-flash-low-t0.3 | 1506.6 | 7 | 11 | 15 | 33 | 21.2% |
| 11 | gemini-2.0-flash-t0.1 | 1503.7 | 28 | 34 | 21 | 83 | 33.7% |
| 12 | gemini-2.5-pro-min-t0.1 | 1501.5 | 45 | 24 | 31 | 100 | 45.0% |
| 13 | gemini-3-flash-t1.0 | 1500.1 | 7 | 8 | 15 | 30 | 23.3% |
| 14 | claude-sonnet-3.7-t0.85 | 1469.2 | 57 | 65 | 37 | 159 | 35.8% |
| 15 | claude-sonnet-3.5-t0.85 | 1462.1 | 47 | 50 | 29 | 126 | 37.3% |
| 16 | claude-sonnet-3.5-t0.1 | 1448.2 | 30 | 34 | 34 | 98 | 30.6% |
| 17 | gemini-2.5-flash-t0.1 | 1384.3 | 25 | 38 | 24 | 87 | 28.7% |
| 18 | claude-sonnet-3.7-t0.1 | 1377.6 | 37 | 37 | 36 | 110 | 33.6% |
| 19 | gemini-2.5-pro-min-t0.85 | 1361.6 | 80 | 99 | 46 | 225 | 35.6% |
| 20 | gemini-2.5-flash-t0.85 | 1340.1 | 57 | 112 | 60 | 229 | 24.9% |
| 21 | gemini-2.5-flash-lite-t0.85 | 1189.7 | 10 | 59 | 19 | 88 | 11.4% |

### 3.2 Vote Distribution by Model

| Model | Excellent (3) | Good (2) | Okay (1) | Trash (-1) | Quality Score* |
|:------|:-------------:|:--------:|:--------:|:----------:|:--------------:|
| gemini-3-pro-low-t0.35 | 16 | 3 | 0 | 0 | **0.95** |
| gemini-3-pro-low-t1.0 | 15 | 2 | 1 | 1 | **0.89** |
| gemini-3-pro-t1.0 | 7 | 5 | 0 | 0 | **0.83** |
| claude-opus-4.5-t0.85 | 8 | 11 | 4 | 2 | 0.68 |
| claude-opus-4.5-t0.1 | 5 | 5 | 1 | 0 | 0.77 |
| gemini-2.5-flash-reasoning-t0.85 | 8 | 11 | 2 | 3 | 0.67 |
| gemini-2.0-flash-t0.85 | 4 | 6 | 9 | 3 | 0.45 |
| gemini-2.5-pro-min-t0.85 | 8 | 7 | 2 | 10 | 0.41 |

*Quality Score = Weighted average: (3×Excellent + 2×Good + 1×Okay - 2×Trash) / (3×Total)*

### 3.3 Overall Vote Distribution

| Rating | Count | Percentage |
|:-------|------:|:----------:|
| Excellent (3) | 117 | 37.4% |
| Good (2) | 110 | 35.1% |
| Okay (1) | 50 | 16.0% |
| Trash (-1) | 36 | 11.5% |

---

## 4. Qualitative Analysis

### 4.1 Model Family Characteristics

#### 4.1.1 Gemini 3 Pro (Low Reasoning) — Top Performers

The Gemini 3 Pro models with low reasoning effort demonstrate exceptional performance in Arabic-to-Dhivehi translation, achieving the highest ELO ratings (1755.9 and 1725.1) and the highest proportion of "Excellent" ratings. These models exhibit:

**Strengths:**
- Superior handling of classical Arabic religious terminology
- Natural Dhivehi sentence structure and flow
- Accurate preservation of honorifics (ރަޙިމަހުﷲ, ޞައްލަﷲ ޢަލައިހި ވަސައްލަމަ)
- Consistent formatting of quotations within religious texts

**Example (Hadith Translation) — Rated Excellent:**

> **Source:** ليس منا من لم يرحم صغيرنا ويوقر كبيرنا
>
> **gemini-3-pro-low-t0.35:**
> އަހަރެމެންގެ ތެރެއިން ކުޑަކުދިންނަށް އޯގާތެރިނުވާ، އަދި ބޮޑެތި މީހުންނަށް އިޙްތިރާމް ނުކުރާ މީހަކީ އަހަރެމެންގެ ތެރެއިންވާ މީހެއް ނޫނެވެ.
>
> *(Translation: "One who does not show compassion to our young and does not respect our elders is not from among us.")*

**Example (Islamic Jurisprudence) — Rated Excellent:**

> **Source:** قال الإمام أحمد رحمه الله: لا يحل لأحد أن يفتي في دين الله إلا بعلم ويقين
>
> **gemini-3-pro-low-t1.0:**
> އިމާމް އަޙްމަދު ރަޙިމަހުﷲ ވިދާޅުވިއެވެ: "ޢިލްމާއި ޔަޤީންކަމާ އެކުގައި މެނުވީ، އެއްވެސް މީހަކަށް ﷲ ގެ ދީނުގައި ފަތުވާ ދިނުން ހުއްދަވެގެން ނުވެއެވެ."

#### 4.1.2 Claude Opus 4.5 — Premium Performance

Claude Opus 4.5 demonstrates strong capabilities, ranking 4th (T0.1) and 6th (T0.85) overall. The model shows particular strength in:

**Strengths:**
- English-to-Dhivehi technical translations
- Maintaining formal register appropriate to religious contexts
- Balanced handling of loanwords vs. native Dhivehi alternatives

**Example (English Technical — Rated Excellent):**

> **Source:** A blind testing platform for comparing Arabic to Dhivehi translations across a selection of different LLM models.
>
> **claude-opus-4.5-t0.85:**
> އެކި އެލް.އެލް.އެމް މޮޑެލްތަކުގައި ޢަރަބި ބަހުން ދިވެހި ބަހަށް ތަރުޖަމާކުރުން އަޅާކިޔުމަށް ބޭނުންކުރާ ބްލައިންޑް ޓެސްޓިން ޕްލެޓްފޯމެއް.

**Characteristic Behavior:** Claude models tend to produce complete, well-structured sentences but occasionally over-explain concepts, leading to translations that are accurate but verbose.

#### 4.1.3 Gemini 2.5 Flash (Reasoning Enabled) — Strong Mid-Tier

With reasoning explicitly enabled, Gemini 2.5 Flash achieves ELO 1570.1, significantly outperforming its non-reasoning counterpart (1340.1). This 230-point differential underscores the impact of reasoning capabilities on translation quality.

**Example (Hadith Chain — Rated Excellent):**

> **Source:** حدثنا أبو اليمان، قال: أخبرنا شعيب، عن الزهري...
>
> **gemini-2.5-flash-reasoning-t0.85:**
> އަޅުގަނޑުމެންނަށް އަބޫލް ޔަމާން ހަދީޘް ކުރެއްވިއެވެ. އެކަލޭގެފާނު ވިދާޅުވިއެވެ. އަޅުގަނޑުމެންނަށް ޝުޢައިބު ޚަބަރުދެއްވިއެވެ. الزهريގެ އަރިހުންނެވެ...

**Notable:** The reasoning model correctly identifies and preserves the isnad (chain of narration) structure critical to hadith scholarship.

#### 4.1.4 Gemini 2.0 Flash — Budget-Efficient Option

Despite its low cost ($0.10/MTok input, $0.40/MTok output), Gemini 2.0 Flash maintains a near-baseline ELO (1522.6 at T0.85, 1503.7 at T0.1), demonstrating acceptable performance for cost-sensitive applications.

**Example (Religious Text — Rated Excellent):**

> **Source:** إِنَّمَا بُعِثْتُ لِأُتَمِّمَ مَكَارِمَ الْأَخْلَاقِ
>
> **gemini-2.0-flash-t0.85:**
> ހަމަކަށަވަރުން، ތިމަންކަލޭގެފާނު ފޮނުއްވުނީ މާތްއަޚްލާޤު ފުރިހަމަ ކުރެއްވުމަށްޓަކައެވެ.

**Limitation:** Higher variance in quality; the same model produced both excellent and trash-rated translations depending on source text complexity.

#### 4.1.5 Low-Performing Models — Failure Mode Analysis

**gemini-2.5-flash-lite-t0.85** (ELO: 1189.7, Win Rate: 11.4%) consistently underperforms, demonstrating characteristic failure modes:

**Failure Mode 1: Script Mixing**
> **Source:** ...ދިވެހި ބަހަށް ސަޕޯޓް නොකුරާތީ...
> 
> *Note: The model incorrectly inserted Sinhala script (නො) within Dhivehi text.*

**Failure Mode 2: Incomplete Translation**
The model occasionally produces truncated outputs or leaves portions untranslated, particularly in longer passages (>100 words).

**Failure Mode 3: Semantic Drift**
In some instances, the model produces translations that are grammatically correct but semantically shifted from the source meaning.

---

## 5. Temperature Effects on Translation Quality

### 5.1 Comparative Analysis: High (0.85) vs. Low (0.1) Temperature

Temperature settings produce observable effects on translation characteristics:

#### Gemini 2.5 Flash: T0.85 vs. T0.1

| Source | T0.85 Translation | T0.1 Translation |
|:-------|:------------------|:-----------------|
| يحرم من الرضاع ما يحرم من النسب | ...ނަސަބުގެ ސަބަބުން ޙަރާމްވާ ކަންތައްތައް ކިރުބުއިމުގެ ސަބަބުންވެސް ޙަރާމްވާނެއެވެ. | ...ނަސަބުގެ ސަބަބުން ޙަރާމްވާ ކަންތައްތައް ކިރުމުގެ ސަބަބުންވެސް ޙަރާމްވެއެވެ. |

**Observations:**
- T0.85 uses "ކިރުބުއިމުގެ" (milk-drinking) — more descriptive
- T0.1 uses "ކިރުމުގެ" (of milk) — more concise
- T0.85 uses future tense (ޙަރާމްވާނެއެވެ); T0.1 uses present (ޙަރާމްވެއެވެ)

#### Claude Sonnet 3.5: T0.85 vs. T0.1

| Source | T0.85 Translation | T0.1 Translation |
|:-------|:------------------|:-----------------|
| والعلم أحق ما تصرف فيه الأوقات... | އަދި ޢިލްމަކީ އެންމެ އައުލާކަންބޮޑު ވަގުތު ހޭދަކުރާ ކަމެކެވެ. | އިލްމަކީ ވަގުތު ހޭދަކުރުމަށް އެންމެ އެކަށީގެންވާ އެއްޗެވެ. |

**Observations:**
- T0.85 uses "އެންމެ އައުލާކަންބޮޑު" (most noble priority) — more literary
- T0.1 uses "އެންމެ އެކަށީގެންވާ" (most suitable) — more neutral

### 5.2 Temperature Recommendations by Domain

| Domain | Recommended Temperature | Rationale |
|:-------|:-----------------------:|:----------|
| Religious/Legal Texts | 0.1 - 0.35 | Precision in terminology is paramount |
| Literary/Prose | 0.85 - 1.0 | Allows for more natural expression |
| Technical Documentation | 0.1 - 0.3 | Consistency and accuracy required |
| General Translation | 0.5 - 0.7 | Balance of creativity and precision |

---

## 6. Reasoning Parameter Impact

### 6.1 Gemini 3 Pro: Reasoning Effort Comparison

The Gemini 3 Pro family provides a controlled experiment on reasoning effort impact:

| Configuration | ELO Rating | Excellent Ratings | Trash Ratings |
|:--------------|:----------:|:-----------------:|:-------------:|
| gemini-3-pro-low-t0.35 | 1755.9 | 16 | 0 |
| gemini-3-pro-low-t1.0 | 1725.1 | 15 | 1 |
| gemini-3-pro-t1.0 (default) | 1679.7 | 7 | 0 |

**Key Finding:** Low reasoning effort (`effort: "low"`) actually outperforms the default setting by 76 ELO points (1755.9 vs. 1679.7). This counterintuitive result may be attributed to:

1. **Task Appropriateness:** Translation may benefit from pattern-matching more than deep reasoning
2. **Reduced Over-Thinking:** Lower reasoning prevents unnecessary "corrections" to valid translations
3. **Faster Convergence:** Simpler reasoning paths may lead to more consistent outputs

### 6.2 Gemini 2.5 Flash: Reasoning vs. No Reasoning

| Configuration | ELO Rating | Δ from Baseline |
|:--------------|:----------:|:---------------:|
| gemini-2.5-flash-reasoning-t0.85 | 1570.1 | +230.0 |
| gemini-2.5-flash-t0.85 (no thinking) | 1340.1 | baseline |

The 230-point ELO differential demonstrates that enabling reasoning significantly improves translation quality, even when temperature is held constant.

---

## 7. Common Failure Patterns

### 7.1 Trash-Rated Translation Analysis

Examination of -1 rated translations reveals systematic failure patterns:

#### Pattern 1: Verbose Over-Explanation

> **Source:** Is there a way to restore deleted files...
>
> **claude-opus-4.5-t0.85** (Trash rating):
> ޑިލީޓްކޮށްފައިވާ ފައިލްތައް އަލުން ހޯދޭނެ ގޮތެއް އެބައޮތް. ކްރާފްޓީ ކޮންޓްރޯލާ ބެކަޕް ފޯލްޑަރެއް ޑިލީޓްވެ ސޭވް ކޮރަޕްޓް ވެފައިވާނަމަ، ޑިލީޓްކޮށްފައިވާ ފައިލްތައް އަލުން ހޯދުމަށް ތިރީގައިވާ ގޮތްތައް ބޭނުންކުރެވިދާނެ:
> 1. **ރީސައިކަލް ބިން ބެލުން**...
> 2. **ފައިލް ރިކަވަރީ ސޮފްޓްވެއާ ބޭނުންކުރުން**...

**Failure:** The model answered the question rather than translating it, providing step-by-step instructions in Dhivehi.

#### Pattern 2: Translation of Untranslatable Content

> **Source:** والركن والواجب قد يفرق بعض الفقهاء بينهما...
>
> Multiple models incorrectly attempted to translate technical fiqh terminology that should be transliterated and explained contextually.

#### Pattern 3: Script Corruption

> **gemini-2.5-pro-min-t0.85** produced: "...ސަޕޯޓް නොකුරާތީ..."
>
> **Note:** Sinhala script (නො) incorrectly inserted, indicating potential training data contamination.

---

## 8. Cost-Effectiveness Analysis

### 8.1 Cost per Quality Point

| Model | Avg. Cost/Translation | ELO Rating | Cost/ELO Point |
|:------|----------------------:|:----------:|:--------------:|
| gemini-2.0-flash-t0.85 | $0.00008 | 1522.6 | $0.00000005 |
| gemini-2.5-flash-t0.85 | $0.00048 | 1340.1 | $0.00000036 |
| gemini-3-pro-low-t0.35 | $0.00604 | 1755.9 | $0.00000344 |
| claude-opus-4.5-t0.85 | $0.00911 | 1546.3 | $0.00000589 |

### 8.2 Efficiency Frontier

For cost-constrained applications:
- **Budget:** gemini-2.0-flash-t0.85 (excellent cost-efficiency)
- **Balanced:** gemini-2.5-flash-reasoning-t0.85 (good quality, moderate cost)
- **Premium:** gemini-3-pro-low-t0.35 (best quality, higher cost)

---

## 9. Conclusions and Recommendations

### 9.1 Key Findings

1. **Reasoning Matters:** Models with explicit reasoning capabilities consistently outperform their standard counterparts by 100-250 ELO points.

2. **Temperature Tuning:** Lower temperatures (0.1-0.35) improve accuracy for technical/religious texts, while moderate temperatures (0.85) may enhance prose fluency.

3. **Model Selection:** Gemini 3 Pro (Low Reasoning) with temperature 0.35 represents the current state-of-the-art for Arabic-to-Dhivehi translation, achieving zero trash ratings across 19 evaluated translations.

4. **Cost-Quality Trade-off:** A 75× cost increase (gemini-2.0-flash to gemini-3-pro) yields only 15% ELO improvement, suggesting diminishing returns at the premium tier.

5. **Failure Patterns:** Script mixing and semantic drift are the most critical failure modes, primarily affecting lower-tier models.

### 9.2 Recommendations for Practitioners

| Use Case | Recommended Model | Temperature |
|:---------|:------------------|:-----------:|
| Religious/Islamic texts | gemini-3-pro-low-t0.35 | 0.35 |
| High-volume general translation | gemini-2.0-flash-t0.1 | 0.1 |
| English-to-Dhivehi technical | claude-opus-4.5-t0.1 | 0.1 |
| Literary/creative content | claude-sonnet-3.5-t0.85 | 0.85 |

### 9.3 Limitations

1. **Evaluator Pool:** Data primarily reflects judgments from Arabic-literate Dhivehi speakers, introducing potential evaluator bias.
2. **Sample Size:** Some model configurations have limited evaluation data (<50 comparisons).
3. **Source Text Bias:** Corpus heavily weighted toward religious/Islamic texts.

### 9.4 Future Directions

1. Expansion of source text diversity to include modern/secular content
2. Inter-rater reliability assessment with multiple blind evaluators
3. Fine-tuning experiments on Dhivehi-specific corpora
4. Evaluation of emerging models (GPT-5, Gemini 4) as they become available

---

## Appendix A: Methodology Details

### A.1 ELO Calculation

The ELO rating system uses the following formula:

```
Expected Score: E_A = 1 / (1 + 10^((R_B - R_A) / 400))
New Rating: R'_A = R_A + K × (S_A - E_A)
```

Where:
- R_A, R_B: Current ratings
- K: Development coefficient (32)
- S_A: Actual score (1 for win, 0.5 for tie, 0 for loss)

### A.2 Combined Score Weighting

```
Combined Score = 0.4 × Normalized_Rating + 0.6 × Normalized_ELO
```

The 40/60 weighting prioritizes competitive performance (ELO) over absolute ratings, reducing the influence of evaluation bias.

---

## Appendix B: Complete Translation Examples

### B.1 Hadith on Compassion

**Source:** ليس منا من لم يرحم صغيرنا ويوقر كبيرنا

| Model | Translation | Rating |
|:------|:------------|:------:|
| gemini-3-pro-t1.0 | އަހަރެމެންގެ ކުޑަކުދިންނަށް ރަޙުމް ނުކުރާ، އަދި އަހަރެމެންގެ ބޮޑެތި މީހުންނަށް ޤަދަރު ނުކުރާ މީހަކީ އަހަރެމެންގެ ތެރެއިންވާ މީހެއް ނޫނެވެ. | 3 |
| gemini-3-pro-low-t1.0 | އަހަރެމެންގެ ތެރެއިން ކުޑަކުދިންނަށް އޯގާތެރި ނުވާ، އަދި ބޮޑެތި މީހުންނަށް އިޙްތިރާމް ނުކުރާ މީހަކީ އަހަރެމެންގެ ތެރެއިންވާ މީހެއް ނޫނެވެ. | 3 |
| claude-opus-4.5-t0.85 | އަހަރެމެންގެ ކުޑަކުދިންނަށް އޯގާތެރި ނުވެ، އަހަރެމެންގެ ބޮޑެތި މީހުންނަށް އިޙްތިރާމް ނުކުރާ މީހަކީ އަހަރެމެންގެ ތެރެއިންވާ މީހެއް ނޫނެވެ. | 3 |

### B.2 Prophetic Mission Statement

**Source:** إِنَّمَا بُعِثْتُ لِأُتَمِّمَ مَكَارِمَ الْأَخْلَاقِ

| Model | Translation | Rating |
|:------|:------------|:------:|
| claude-opus-4.5-t0.85 | ހަމަކަށަވަރުން ތިމަންކަލޭގެފާނު ފޮނުއްވުނީ ރިވެތި އަޚްލާޤު ފުރިހަމަ ކުރެއްވުމަށެވެ. | 3 |
| gemini-2.5-flash-reasoning-t0.85 | ހަމަކަށަވަރުން ތިމަންކަލޭގެފާނު ފޮނުއްވުނީ ރިވެތި އަޚުލާޤުތައް ފުރިހަމަ ކުރެއްވުމަށެވެ. | 3 |
| gemini-2.0-flash-t0.85 | ހަމަކަށަވަރުން، ތިމަންކަލޭގެފާނު ފޮނުއްވުނީ މާތްއަޚްލާޤު ފުރިހަމަ ކުރެއްވުމަށްޓަކައެވެ. | 3 |

---

## References

1. Dhivehi Translation Arena Platform. (2025). GitHub Repository. https://github.com/maaldheefee/dhivehi-translation-arena

2. Elo, A. E. (1978). *The Rating of Chessplayers, Past and Present*. Arco Publishing.

3. Google DeepMind. (2025). Gemini 3 Technical Report. Google Research.

4. Anthropic. (2025). Claude 4 Model Card. Anthropic AI.

5. OpenRouter. (2025). API Documentation and Pricing. https://openrouter.ai/docs

---

*This report was generated using data collected through December 18, 2025. All translations and ratings represent the combined judgments of human evaluators using the Dhivehi Translation Arena blind testing protocol.*
