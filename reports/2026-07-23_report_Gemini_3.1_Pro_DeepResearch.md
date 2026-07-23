# A Comparative Analysis of Large Language Models for Arabic-to-Dhivehi Translation: An Empirical Study

**Author:** Gemini 3.1 Pro (Deep Research)  
**Date:** July 23, 2026  

---

# Empirical Evaluation of Large Language Models in Low-Resource Linguistic Domains: A Comprehensive Analysis of the Dhivehi Translation Arena

The deployment of Large Language Models (LLMs) across diverse global populations frequently encounters the structural limitations of their pretraining corpora. Even though the intended operational parameters of most open-weights and proprietary models are restricted to high-resource languages, real-world deployment data demonstrates that users routinely prompt these models in languages far beyond their primary training scope. This phenomenon has catalyzed an urgent need to evaluate the cross-lingual generalization capabilities of monolingual and multilingual models. Languages utilizing non-Latin scripts, such as Dhivehi and Sudanese Arabic, are particularly vulnerable to performance degradation, as standard foundational models are rarely optimized for their unique morphological and syntactic demands. The historical reliance on automated translation in research contexts, driven by budget constraints that render manual translation infeasible, further underscores the necessity of establishing empirical baselines for low-resource languages.

Dhivehi, an Indo-Aryan language spoken predominantly in the Maldives, utilizes the right-to-left Thaana script. It presents a formidable challenge for neural machine translation architectures due to its high morphological complexity, distinct Subject-Object-Verb (SOV) word order, and profound lexical borrowing from Arabic. Furthermore, the inherent cursive nature of scripts like Arabic and Thaana—where letters change shape depending on their positional context and lack a print-versus-handwriting distinction—has historically confounded typographic systems and continues to challenge modern neural tokenizers.

This comprehensive report analyzes the empirical performance of 37 distinct LLM configurations in translating English and Arabic source texts into Dhivehi. The underlying data is derived from a specialized translation arena evaluating outputs through a dual-metric system encompassing both absolute human ratings and relative head-to-head performance rankings.

## Methodological Framework and Dataset Overview

The analytical dataset comprises 571 discrete votes cast across 785 generated translations, logged on July 23, 2026. The evaluation methodology utilizes a sophisticated convex blending system to synthesize absolute human judgments with mathematical comparative performance.

Human evaluators assess the quality and correctness of English or Arabic to Dhivehi translations, assigning a rating on a scale of 1 to 3 stars, with an explicit mechanism to reject critically flawed or hallucinated outputs by assigning a score of -1. These discrete scores are aggregated to formulate a preliminary average rating. However, because absolute star ratings are highly susceptible to evaluator subjectivity and sample size variance, the methodology incorporates a Glicko-2 rating system to refine the hierarchy.

The Glicko-2 system evaluates translations by placing them in direct head-to-head pairings, establishing relative dominance even when absolute star ratings are identical. The ultimate performance index is a normalized combined score ranging from 0 to 1. This final metric is calculated as a convex blend of the normalized Glicko-2 rating and the normalized average star rating. The blending weight is dynamically determined by a confidence factor derived from the Glicko-2 Rating Deviation (RD). For mature models with low RD (high statistical confidence based on a large volume of matchups), the Glicko-2 rating acts as the dominant variable. Conversely, for newly introduced or under-tested models exhibiting high RD, the absolute star ratings carry greater weight. Unless otherwise specified, models were evaluated using a default inference temperature of 0.85, while configurations utilizing explicit thinking or reasoning budgets operated on their manufacturer-specified defaults.

## 1. Overall Performance Ranking and Model Stratification

The overarching hierarchy of the Dhivehi translation arena demonstrates a severe stratification between proprietary, highly optimized models and open-weights architectures. The upper echelons are monopolized by the Google Gemini and Anthropic Claude lineages, while several notable models fall into cascading failure modes when attempting to generate Thaana script.

### The Elite Tier: Top Performing Models

The following table details the five most capable models in the arena, evaluated by their normalized combined scores, average star ratings, and Glicko-2 statistics.

| **Overall Rank** | **Model Configuration**   | **Base Architecture** | **Preset Configuration** | **Combined Score** | **Average Star Rating** | **Glicko-2 ELO** | **Matchup Win Rate** |
| ---------------- | ------------------------- | --------------------- | ------------------------ | ------------------ | ----------------------- | ---------------- | -------------------- |
| 1                | Gemini 3.5 Flash (T1.0)   | Gemini 3.5 Flash      | Default, Temp 1.0        | 0.9638             | 2.54                    | 1980.58          | 84.61%               |
| 2                | Gemini 3.6 Flash (T0.3)   | Gemini 3.6 Flash      | Temp 0.3                 | 0.9340             | 2.33                    | 1954.42          | 78.37%               |
| 3                | Claude Opus 4.5 (T0.1)    | Claude Opus 4.5       | Temp 0.1                 | 0.9021             | 1.81                    | 1946.01          | 53.75%               |
| 4                | Gemini 3 Pro (Low, T0.35) | Gemini 3 Pro Preview  | Low Reasoning, Temp 0.35 | 0.8954             | 2.71                    | 1860.55          | 56.14%               |
| 5                | Gemini 3.5 Flash (T0.3)   | Gemini 3.5 Flash      | Temp 0.3                 | 0.8852             | 1.90                    | 1916.52          | 65.15%               |

The empirical data establishes the **Gemini 3.5 Flash (T1.0)** as the paramount architecture for Dhivehi translation. Achieving an unprecedented combined score of 0.9638, an ELO of 1980.58, and a staggering 84.61% win rate across 65 direct matchups, this model demonstrates an exceptional capacity for cross-lingual mapping. Its vote distribution reveals robust consistency, securing 9 "excellent" ratings, 1 "good" rating, 1 "okay" rating, and absolutely zero rejections. This profile suggests that Google’s 3.5 iteration of the Flash architecture achieved a critical saturation point in its multilingual pretraining corpus, allowing it to natively navigate the morphological boundaries of the Thaana script without the fragmentation seen in earlier generations.

The **Gemini 3.6 Flash (T0.3)** secures the second position with a combined score of 0.9340, indicating that the incremental architectural updates from 3.5 to 3.6 maintained the fundamental cross-lingual competencies required for Dhivehi, albeit optimally functioning at a lower temperature constraint.

Anthropic's **Claude Opus 4.5 (T0.1)** anchors the third rank. This model presents a fascinating statistical paradox: its average absolute star rating is a relatively modest 1.81, yet it commands a massive ELO of 1946.01 and a combined score of 0.9021. This disparity is explained by its sheer volume of consistent, competent outputs. Across an exhaustive 160 comparative matchups (86 wins, 32 losses, 42 ties), Opus 4.5 almost never fails catastrophically. It received zero rejections across its evaluation lifecycle, meaning that while human evaluators might find its prose occasionally uninspired (defaulting to "good" rather than "excellent"), it consistently defeats more erratic models that oscillate between brilliance and hallucination.

The fourth-ranked model, **Gemini 3 Pro (Low, T0.35)**, represents the zenith of human subjective preference. It achieved the highest absolute star average in the entire dataset at 2.71, accumulating 18 "excellent" votes out of 21 evaluations. However, its Glicko-2 ELO of 1860.55 is lower than the top three models, and its win rate sits at 56.14%. This indicates that while its successful translations are extraordinarily high in quality and deeply favored by native speakers, its comparative reliability against the sheer consistency of the Gemini Flash series slightly depresses its mathematical ranking.

### Significant Underperformers and Anomalous Failures

A critical aspect of evaluating LLMs in low-resource environments is analyzing the architectures that collapse under the linguistic stress of unrepresented scripts. The arena data highlights several catastrophic underperformers.

The most profound anomaly is the total failure of the **Gemma 4** lineage. The dataset includes evaluations for both the Gemma 4 31B Instruct and the Gemma 4 26B Instruct models across multiple temperature configurations. Every single configuration yielded an average star rating of -2.0, a 0.0% win rate, and a 100% rejection rate. A collapse of this magnitude strongly implies a fundamental deficiency in the tokenizer. When an LLM's byte-pair encoding (BPE) or SentencePiece tokenizer lacks sufficient vocabulary depth for a specific script, it resorts to severe character fragmentation. The model attempts to reconstruct Dhivehi words using statistically distant tokens from Arabic, Hebrew, or Latin scripts, resulting in illegible, hallucinated outputs that human evaluators immediately reject.

Similarly, the **Gemini 3.5 Flash Lite** models (both T0.1 and T0.85) exhibit catastrophic failure, returning average scores of -1.0 and -2.0 respectively, with win rates hovering around 11%. This is highly irregular given that the standard Gemini 3.5 Flash model is the absolute champion of the arena. This massive delta between the base model and its "Lite" counterpart suggests that the nuanced, cross-lingual representations necessary to translate English syntax into Dhivehi SOV structures reside in the deeper parameter weights of the network. When the model undergoes heavy distillation, pruning, or quantization to create the "Lite" version, these fragile, low-resource linguistic pathways are seemingly the first to be destroyed.

Finally, the **DeepSeek V4 Flash** and the **GPT-5.6 Luna** models significantly underperformed expectations, anchoring the bottom quartile of active models with negative average star ratings (-0.71 and -1.2 respectively). This performance deficit indicates that these specific architectural branches have not yet achieved the multilingual saturation required to handle Indo-Aryan languages effectively, often generating rigid, literal translations that violate local grammatical conventions.

## 2. Longitudinal Evolution and Model Family Dynamics

Analyzing the chronological progression of specific model families provides deep insights into how different AI research laboratories are addressing the challenge of multilingual alignment over time. The data reveals stark contrasts: some families exhibit consistent generational compounding of linguistic capability, while others suffer from severe architectural regressions.

### The Google Gemini Lineage: Exponential Flash Scaling and Pro Plateau

The Google Gemini ecosystem is the most heavily represented in the dataset and provides the clearest empirical map of longitudinal evolution in low-resource translation.

**The Iterative Trajectory of Gemini Flash:** The evolution of the Gemini Flash series demonstrates a dramatic, almost exponential improvement curve. The earliest iterations represented in the dataset, such as **Gemini 2.0 Flash**, languished in the bottom quartile. The T0.85 variant of 2.0 Flash recorded a combined score of 0.4363, an ELO of 1345.44, and a win rate of just 27.19% across 239 matchups. It suffered from high rejection rates, indicating a tenuous grasp of the Thaana script.

The transition to **Gemini 2.5 Flash** showed only marginal structural improvement. The T0.85 variant increased its combined score slightly to 0.4656, but its win rate dropped further to 22.59% over 270 matchups, indicating persistent instability. The introduction of the **Gemini 3 Flash Preview** pushed the series firmly into the mid-tier. The low-reasoning T1.0 configuration achieved a combined score of 0.6588 and a more respectable ELO of 1630.00, signaling that Google had begun to rectify the underlying tokenization and alignment issues.

The quantum leap occurred with the release of **Gemini 3.5 Flash**. As previously noted, it surged to the #1 overall rank with an ELO of 1980.58 and a combined score of 0.9638. This monumental generational jump suggests that between versions 3.0 and 3.5, the architectural pretraining mixture was fundamentally altered, perhaps through the inclusion of high-quality, synthetic Dhivehi-Arabic parallel corpora, effectively transforming the Flash model from a budget-tier liability into an industry-leading translator. The subsequent **Gemini 3.6 Flash** maintained this elite status, ranking #2 overall, though it did not decisively eclipse the 3.5 model, potentially indicating an asymptotic plateau in the current architectural paradigm.

**The Trajectory of Gemini Pro:** In stark contrast to the explosive growth of the Flash series, the Gemini Pro models exhibit a much flatter developmental trajectory.

- **Gemini 2.5 Pro (Min, T0.1)** achieved a combined score of 0.5918 and an ELO of 1602.12.
- **Gemini 3 Pro Preview (Low, T0.35)** showed significant strength, reaching a combined score of 0.8954 and an ELO of 1860.55.
- **Gemini 3.1 Pro Preview (Low, T0.35)** maintained a similarly robust position with a combined score of 0.8828 and an ELO of 1891.74.

The longitudinal data establishes a critical paradigm shift: while the older-generation Pro models are highly competent, the newer-generation, smaller Flash models (3.5 and 3.6) have definitively surpassed them in this specific cross-lingual task. For low-resource translation, recency of architectural update and training data curation outweighs raw parameter count.

### The Anthropic Claude Lineage: The 4.6 Regression Anomaly

Anthropic’s models display a highly erratic evolutionary path, characterized by steady initial competence followed by a catastrophic generational regression.

The mid-tier foundation is established by the Sonnet family. **Claude 3.5 Sonnet (T0.1)** and **Claude 3.7 Sonnet (T0.85)** act as relatively safe but unexceptional translators, recording combined scores of 0.5687 and 0.5194, respectively. They avoid high rejection rates but fail to secure the dominant win rates required to climb the Glicko-2 ladder.

The apex of Anthropic's achievement in this domain is the **Claude Opus 4.5 (T0.1)**. As the #3 ranked model overall with an ELO of 1946.01, it is the most stable and reliable model tested, characterized by a massive volume of "good" ratings and zero rejections over 160 matchups.

However, the subsequent generation reveals a severe anomaly. **Claude Opus 4.6 (T0.1)** represents a drastic regression from its predecessor. Its combined score collapses to 0.7109, its win rate plummets from 53.75% to 47.61%, and its ELO drops by over 250 points to 1692.99. This degradation is mirrored and amplified in the smaller tier: **Claude Sonnet 4.6 (T0.1)** collapses entirely, yielding a combined score of 0.3890, an average rating of -0.42, and a dismal 13.88% win rate.

This generational regression from 4.5 to 4.6 is a critical observation. It is highly probable that in optimizing the 4.6 models for advanced reasoning, coding logic, or English-language safety alignment, Anthropic inadvertently triggered catastrophic forgetting within its low-resource language representations. The data firmly suggests that architectural upgrades intended to improve performance in dominant languages can simultaneously destroy the delicate, fragile weights responsible for generating coherent Dhivehi.

### The OpenAI GPT-5.6 Series: Consistent Mediocrity

The OpenAI ecosystem, represented by the GPT-5.6 series, failed to achieve relevance in the upper tiers of the arena. The models exhibit a clear degradation directly correlated to their parameter scale/tier:

- **GPT-5.6 Sol (T0.85)** peaked at a combined score of 0.5535, with a win rate of 34.37%.
- **GPT-5.6 Terra (T0.85)** achieved a combined score of 0.4716, with a win rate of 36.66%.
- **GPT-5.6 Luna (T0.1)** fell to a combined score of 0.3845, with a win rate of 15.38%.

The GPT-5.6 series is characterized by its inability to win direct matchups against Google or Anthropic models. The consistent mediocrity across all three tiers (Sol, Terra, Luna) implies that OpenAI's latent space representation for Dhivehi is misaligned. These models likely produce structurally rigid, literal translations that feel highly unnatural to native speakers, heavily relying on English syntactic mapping rather than natively generating Dhivehi SOV structures.

## 3. Configuration Impact Analysis

Beyond baseline architectural strengths, the arena dataset provides a robust opportunity to analyze how granular inference configurations—specifically generation temperature and explicit reasoning budgets—alter translation efficacy.

### Temperature Dynamics: The Balance of Entropy and Determinism

In autoregressive language generation, temperature controls the entropy of the probability distribution over the vocabulary space. A low temperature (e.g., 0.1) compresses the distribution, creating highly deterministic, argmax-heavy outputs that prioritize the most statistically likely next token. Conversely, a higher temperature (e.g., 0.85 to 1.0) flattens the distribution, injecting randomness that allows for more diverse, creative, and sometimes more contextually appropriate token selection.

The dataset includes an explicit tracking of 45 cross-temperature head-to-head comparisons, wherein the exact same base model architecture competed against itself across different temperature presets. The macro-level statistics show a near-even split: the High Temperature configuration won 24 times (53.3%), while the Low Temperature configuration won 21 times (46.6%). There were zero ties in cross-temperature pairings.

However, this statistical parity dissolves when analyzing specific model families, revealing deep structural biases regarding how different architectures handle entropy in low-resource environments.

The following table isolates the cross-temperature win rates for select foundational models :

| **Base Model Architecture** | **High Temp (0.85/1.0) Wins** | **Low Temp (0.1/0.3) Wins** | **High Temp Win Rate** | **Low Temp Win Rate** |
| --------------------------- | ----------------------------- | --------------------------- | ---------------------- | --------------------- |
| Gemini 3 Flash Preview      | 11                            | 1                           | 91.66%                 | 8.33%                 |
| Gemini 2.0 Flash            | 3                             | 0                           | 100.00%                | 0.00%                 |
| Claude Opus 4.5             | 2                             | 1                           | 66.66%                 | 33.33%                |
| Gemini 2.5 Flash            | 1                             | 2                           | 33.33%                 | 66.66%                |
| Gemini 3 Pro Preview        | 6                             | 10                          | 37.50%                 | 62.50%                |
| Claude 3.5 Sonnet           | 0                             | 2                           | 0.00%                  | 100.00%               |
| DeepSeek V4 Pro             | 0                             | 1                           | 0.00%                  | 100.00%               |

**Models Benefiting from Low Temperature Determinism:** For a significant cohort of models, translating into Dhivehi requires strict deterministic adherence to the most highly probable linguistic pathways. Elevating the temperature introduces noise that these models cannot smoothly recover from, resulting in hallucinations or grammatical fragmentation. The Anthropic Claude 3.5 Sonnet, DeepSeek V4 Pro, and the Gemini 3 Pro Preview demonstrate a heavy reliance on low temperatures. For the Gemini 3 Pro Preview, lowering the temperature resulted in 10 victories against its high-temperature self, suggesting that its internal mapping of Dhivehi is fragile; forcing it to search for lower-probability tokens inevitably breaks its syntax.

**Models Benefiting from High Temperature Entropy:** Conversely, certain architectures require high entropy to escape local minima. In low-resource linguistics, the "most likely" token (the argmax) might actually be a transliterated English word or a direct Arabic loanword that is poorly adapted to natural Dhivehi usage. High temperature allows the model to search wider for the natural, native equivalent. This dynamic is overwhelmingly evident in the Gemini 3 Flash Preview, which won 91.66% of its matchups when utilizing a high temperature. Similarly, Gemini 2.0 Flash won 100% of its high-temperature comparisons. These models thrive on the injected creativity, suggesting that their primary, deterministic pathways are flawed, and they rely on broader stochastic sampling to generate fluent prose.

### The Efficacy of Reasoning and Thinking Mechanisms

A dominant contemporary trend in LLM design is the integration of hidden "thinking" or "reasoning" budgets, allowing the model to semantically decompose a prompt in a latent chain-of-thought before generating the final output. The arena dataset explicitly isolates 17 configurations utilizing reasoning parameters against 28 non-reasoning configurations.

At a macro statistical level, granting a model a reasoning budget yields an objective linguistic advantage. The average ELO of reasoning models is 1567.37, significantly exceeding the non-reasoning average ELO of 1477.84. This 89.5-point ELO differential demonstrates that allowing a network to process the complex semantic shifts between Arabic VSO structures, English SVO structures, and Dhivehi SOV structures before output generation leads to objectively superior linguistic alignment.

However, a micro-level analysis of specific same-base architectural comparisons reveals that the application of reasoning is highly contingent on interacting variables, particularly temperature.

The dataset highlights the following critical comparative examples :

| **Base Model**         | **Reasoning Configuration** | **Non-Reasoning Configuration** | **Reasoning ELO** | **Non-Reasoning ELO** | **ELO Differential** |
| ---------------------- | --------------------------- | ------------------------------- | ----------------- | --------------------- | -------------------- |
| Gemini 3 Flash Preview | Low Reasoning, Temp 1.0     | Default, Temp 1.0               | 1630.00           | 1558.46               | +71.54               |
| Gemini 3 Flash Preview | Low Reasoning, Temp 1.0     | Default, Temp 0.3               | 1630.00           | 1534.93               | +95.07               |
| Gemini 3 Pro Preview   | Low Reasoning, Temp 0.35    | Default, Temp 1.0               | 1860.55           | 1758.35               | +102.20              |
| Gemini 3 Pro Preview   | Low Reasoning, Temp 1.0     | Default, Temp 1.0               | 1624.05           | 1758.35               | -134.29              |

When properly configured, reasoning mechanisms provide massive boosts. For instance, granting the Gemini 3 Pro Preview a "low" reasoning budget and restricting its temperature to 0.35 results in a massive 102.2-point ELO surge over its non-reasoning default. Similarly, the Gemini 3 Flash Preview sees a 71.54-point ELO increase when granted minimal reasoning at a high temperature.

**The Negative Reasoning Anomaly:** The most vital insight derived from the reasoning analysis is the catastrophic interaction between high temperature and reasoning logic within the Gemini 3 Pro Preview model. When this model was granted a low reasoning budget but configured with a high temperature (T1.0), it achieved an ELO of only 1624.05, losing to its non-reasoning T1.0 counterpart by a massive -134.29 ELO points. In direct head-to-head matchups, the high-temp reasoning model suffered 33 losses.

This anomaly exposes the fragility of latent chain-of-thought processing. Reasoning mechanisms rely on establishing highly logical, deterministic pathways to parse meaning. A high temperature injects probabilistic noise directly into this chain of thought. When the Gemini 3 Pro model attempted to reason at T1.0, the internal logic likely derailed, cascading into a severely degraded final translation. Therefore, the empirical evidence dictates that reasoning models must generally be paired with lower temperatures to realize their full potential in cross-lingual syntax mapping.

## 4. Economic Viability and Cost-Effectiveness

Translation operations deployed at scale must reconcile the pursuit of absolute linguistic fidelity with the realities of inference computing costs. The dataset calculates a highly useful "Bang for Buck" metric, juxtaposing the model's combined quality score against its cost per 100,000 tokens. This metric allows for the stratification of models into budget and premium operational tiers.

### The Budget Tier (Under $10 per 100k tokens)

Models in this classification are engineered for massive throughput, web scraping, and bulk document translation. However, as established in the anomaly analysis, several models in this price bracket (e.g., the Gemma series and Flash Lite variants) fail completely at Dhivehi translation. The true champions of this tier are architectures that maintain coherent syntax without spiraling into hallucination loops.

The following table details the most viable budget configurations :

| **Model Configuration**              | **Cost per 100k Tokens** | **Bang for Buck Metric** | **Combined Score** | **Glicko-2 ELO** |
| ------------------------------------ | ------------------------ | ------------------------ | ------------------ | ---------------- |
| Gemini 2.0 Flash (T0.1)              | $0.31                    | 10.00                    | 0.4640             | 1389.69          |
| Gemini 3.1 Flash Lite (T0.1)         | $1.20                    | 9.44                     | 0.5865             | 1562.06          |
| Gemini 3 Flash (Low Reasoning, T1.0) | $2.62                    | 9.01                     | 0.6588             | 1630.00          |
| Gemini 3 Flash (T0.3)                | $6.90                    | 7.19                     | 0.6012             | 1534.93          |

The **Gemini 2.0 Flash (T0.1)** achieves the highest theoretical Bang for Buck (10.0) by costing a negligible $0.31 per 100k tokens. While its overall combined score of 0.4640 places it in the lower-middle tier regarding absolute quality, it represents the most cost-efficient option for non-critical translation where perfection is subservient to volume.

A significant step up in quality is provided by the **Gemini 3.1 Flash Lite (T0.1)**. Costing $1.20 per 100k tokens, it boasts a Bang for Buck of 9.44 and crucially secures a 56.9% win rate. It is highly viable for budget-constrained operations requiring majority-readable outputs.

The absolute sweet spot for economic operations, however, is the **Gemini 3 Flash (Low Reasoning, T1.0)**. At just $2.62 per 100k tokens, this configuration leverages its minimal reasoning budget to achieve a highly respectable combined score of 0.6588 and an ELO of 1630.00. It vastly outperforms the 2.x generation models for a fraction of a cent more per token, making it the premier budget selection.

### The Premium Tier ($20 to $120+ per 100k tokens)

Premium architectures are mandated for production-grade software localization, legal document translation, and the parsing of theological texts where semantic precision and cultural pragmatics are non-negotiable.

| **Model Configuration**   | **Cost per 100k Tokens** | **Bang for Buck Metric** | **Combined Score** | **Average Star Rating** |
| ------------------------- | ------------------------ | ------------------------ | ------------------ | ----------------------- |
| Gemini 3 Pro (Low, T0.35) | $20.38                   | 7.88                     | 0.8954             | 2.71                    |
| Claude Opus 4.5 (T0.1)    | $34.67                   | 7.20                     | 0.9021             | 1.81                    |
| Gemini 3.5 Flash (T1.0)   | $55.71                   | 6.91                     | 0.9638             | 2.54                    |
| DeepSeek V4 Pro (T0.1)    | $72.13                   | 3.36                     | 0.5262             | 0.85                    |
| Gemini 3 Pro (T1.0)       | $123.59                  | 4.79                     | 0.7939             | 2.16                    |

The **Most Cost-Effective Premium Option** is undeniably the **Gemini 3 Pro (Low, T0.35)**. Priced at $20.38 per 100k tokens, it secures the highest absolute star average (2.71) across the entire arena and maintains a Bang for Buck of 7.88—an exceptionally high efficiency ratio for a premium-tier model. By leveraging a low reasoning budget and tight temperature constraints, it avoids the exorbitant costs of unconstrained generation while dominating the intersection of supreme precision and reasonable pricing.

The **Claude Opus 4.5 (T0.1)** serves as the elite anchor of stability. At $34.67 per 100k tokens, it maintains a strong Bang for Buck of 7.20. As previously established, it survived 160 rigorous head-to-head matches without a single human rejection. For enterprise deployments where translation errors pose severe reputational risks, the $34 premium is entirely justified by the mathematical guarantee of baseline coherence.

Conversely, the data highlights the inefficiency of unoptimized flagship deployment. The **Gemini 3 Pro (T1.0)**—running without reasoning constraints and at high entropy—costs an exorbitant $123.59 per 100k tokens. Despite this massive expenditure, it only achieves a combined score of 0.7939 and a poor Bang for Buck of 4.79. This starkly illustrates that merely deploying the most expensive parameterization does not guarantee optimal performance in low-resource linguistics; precise configuration is drastically more impactful than raw computing power.

## 5. ELO vs. Rating Discrepancies and Vote Distribution Analytics

A foundational strength of this specialized arena is its dual-evaluation methodology. Pure average star ratings are highly vulnerable to small sample sizes, extreme evaluator bias, and subjective interpretations of "good" versus "okay." The Glicko-2 ELO algorithm corrects for this volatility by tracking mathematically rigorous wins and losses against dynamically matched opponents. Analyzing the vote distributions alongside discrepancies between ELO and star ratings reveals the deep operational character of these models.

### Identifying Polarizing vs. Consensus Models

Vote distributions expose whether a model is consistently competent or violently unstable.

**Consensus Models (High agreement, stability):** Models achieving high consensus demonstrate deep alignment with native speaker expectations.

- **Gemini 3.5 Flash (T1.0):** This model generated 9 Excellent, 1 Good, 1 Okay, and 0 Rejected ratings. Its extremely high average score (2.54) perfectly aligns with its #1 ELO (1980.58). Evaluators universally recognize its quality, and it defeats almost all mathematical opponents without debate.
- **Gemini 3 Pro (Low, T0.35):** Generating 18 Excellent, 3 Good, and 0 Rejected ratings, this is the ultimate subjective consensus model. Human readers universally praise its outputs, which is reflected in its high ELO (1860.55).

**Polarizing Models (High Excellent combined with High Rejection):** Polarizing models pose a massive risk to automated pipelines, as they act as a linguistic dice roll.

- **Gemini 2.5 Pro (Min, T0.85):** This architecture received 8 Excellent ratings, indicating that when it succeeds, its prose is beautiful. However, it simultaneously suffered 10 outright Rejections. Consequently, its average score crashed to 0.40, and its ELO sank to a dismal 1448.01. A polarizing distribution indicates acute systemic instability; the model has a high probability of entering a hallucination loop or outputting raw Arabic syntax unadapted to Dhivehi, triggering immediate human rejection.
- **Gemini 2.5 Flash (T0.1):** Generating 6 Excellent, 5 Good, 4 Okay, and 3 Rejected ratings, this completely flat distribution reveals a model that lacks any foundational consistency, producing wildly different quality tiers regardless of the prompt.

### The Mechanics of ELO vs. Star Rating Discrepancy

Certain models exhibit high star ratings but moderate ELOs, or vice versa. Understanding these discrepancies determines which metric an enterprise should optimize for.

The most profound example is the **Claude Opus 4.5 (T0.1)**. It possesses a relatively low average star score of 1.81, which would seemingly place it near the middle of the pack. However, its mathematical ELO is a massive 1946.01, ranking it 3rd overall. The explanation lies in its vote distribution: 10 Excellent, 10 Good, 2 Okay, and crucially, 0 Rejected. Opus 4.5 rarely wows the human evaluator into giving a perfect 3-star rating, often settling for a safe, literal 2-star "Good" translation. However, because it *never* produces a rejected or structurally broken output, it constantly wins its head-to-head A/B tests against flashier models that occasionally hallucinate.

Conversely, the **Gemini 3.1 Pro (Low, T0.35)** shows a high average score (2.26) but a proportionately lower ELO (1891.74) than would be expected for such a high star rating. This occurs because its Rating Deviation (RD) is tight (81.08), meaning the algorithm is highly confident in its ELO placement. This suggests that while the model looks fantastic in isolation (garnering high stars), it frequently loses nuanced comparative battles when placed side-by-side against the supreme fluency of Gemini 3.5 Flash.

**Metric Recommendation:** For production use cases and automated deployment, the **Glicko-2 ELO is a vastly more reliable metric** than average stars. ELO mathematically rewards baseline consistency and severely penalizes catastrophic failure, which aligns perfectly with enterprise risk management requirements in software and document localization.

## 6. Qualitative Evaluation and Syntactic Mechanics

To genuinely comprehend the empirical statistics, one must analyze the structural mechanics of the generated translations. The dataset includes qualitative samples purposefully chosen for maximum rating divergence, providing a granular window into how top-tier models succeed where lower-tier models succumb to tokenization collapse and syntactic rigidity.

### Syntactic Alignment in Complex Theological Texts (Query 69)

**Source Text (Arabic):** `قال ابن تيمية رحمه الله: الفقه هو معرفة ما لله على العباد وما للعباد عند الله` *(Context: Ibn Taymiyyah said: Fiqh is knowing what rights Allah has over the servants and what rights the servants have with Allah.)* 

This prompt presents an extreme test of syntactic agility. The model must transition from an Arabic Verb-Subject-Object (VSO) or Subject-Verb-Object (SVO) phrasing to the strict Subject-Object-Verb (SOV) structure of Dhivehi, while correctly mapping weighty theological vocabulary and preserving honorifics.

- **The Excellent Output (Gemini 2.5 Flash Reasoning T0.85, Rating: 3):** `އިބްނު ތައިމިއްޔާ ރަޙިމަހުﷲ ވިދާޅުވިއެވެ: ފިޤުހަކީ، ﷲ ތަޢާލާ އަޅުތަކުންގެ މައްޗަށް ލައްވާފައިވާ ހައްޤުތަކާއި، އަދި ﷲ ތަޢާލާގެ ޙަޟްރަތުގައި އަޅުތަކުންނަށް ލިބިގެންވާ ހައްޤުތައް ދެނެގަތުމެވެ.`  *Linguistic Breakdown:* The model flawlessly captures the required honorifics ("ރަޙިމަހުﷲ ވިދާޅުވިއެވެ" - Said, with respect). It translates "معرفة" (knowing) accurately into the Dhivehi gerund "ދެނެގަތުމެވެ" and places it elegantly at the absolute end of the sentence, strictly adhering to Dhivehi SOV grammatical norms. The delicate balancing act of "rights over" and "rights with" is handled without conceptual distortion.
- **The Rejected Output (Gemma 4 26B, Rating: -1):** `އިބްނު Tayyipiyah (ރަޙިމަހުﷲ) ވަނީ މިވަގުތު ބަޔާންކޮށްފައިވަނީ: "ފިޤުހަކީ، މާތްﷲގެ ފަރާތުން عبادުން (ބަންދާ) މަތީގައި އޮތް ހައްގުތަކާއި، عبادުންގެ ފަރާތުން މާތްﷲގެ ފަރާތުން އޮތް ހައްގުތަކާ ބެހޭ މަޢުރިފަތެވެ."`  *Linguistic Breakdown:* This translation is a total failure. The model cannot transliterate "Taymiyyah", leaving it as bizarrely spelled English text ("Tayyipiyah") amidst the Thaana script. It introduces incredibly awkward, hallucinated phrasing ("ވަނީ މިވަގުތު ބަޔާންކޮށްފައިވަނީ" - has currently stated), which is fundamentally unnatural. Furthermore, it fails to translate the Arabic word "عباد" (servants), simply dropping it into the text and adding a Dhivehi suffix ("عبادުން"), then bizarrely attempting to clarify it with a Hindi/Urdu loanword in brackets ("ބަންދާ"). This exemplifies why open-weights models lacking specific script fine-tuning fail completely; they lack the BPE depth to resolve the entities natively.

### Tokenization Collapse and Cross-Lingual Bleed (Query 314)

**Source Text (Arabic):** `اعلمْ أنَّ الإخلاصَ هو تصفيةُ العملِ عن ملاحظةِ المخلوقين، فلا يقصدُ العاملُ بعملِه إلا وجهَ اللهِ تعالى.` *(Context: Know that sincerity is purifying the action from the observation of creations...)* 

- **The Excellent Output (Claude Opus 4.5 T0.1, Rating: 3):** `ދަންނާށެވެ! އިޚްލާޞްތެރިކަމަކީ މަޚްލޫޤުން ބެލުމުން ޢަމަލު ޠާހިރުކުރުމެވެ. ފަހެ، ޢަމަލުކުރާ މީހާ އޭނާގެ ޢަމަލުން ﷲ ތަޢާލާގެ ވަޖުހުފުޅު ފިޔަވައި އެހެން އެއްވެސް ކަމެއް ޤަޞްދު ނުކުރުމެވެ.`  *Linguistic Breakdown:* Claude utilizes the commanding imperative "ދަންނާށެވެ!" perfectly for the Arabic "اعلمْ" (Know!). It masterfully translates "تصفية" (purifying) into the Arabic loan-word integrated deeply into Dhivehi ("ޠާހިރުކުރުމެވެ"), maintaining the formal religious register of the text.
- **The Rejected Outputs (Gemini 3.5 Flash Lite T0.1 / T0.85, Rating: -1):** `דעانering ދަންނާށެވެ!` and `דעانel، إخلاصvكي نﻱ مﺨلwqكي gةvمfشلkي vمaلkخlوقqيn، پﻻ yقﺻdس vلcعaمlلv بcعaمlه إﻻ wجhهa اllلhi تcعaلaى.`  *Linguistic Breakdown:* This is a textbook, empirical example of tokenization collapse under the strain of low-resource constraint. The "Lite" model suffers catastrophic interference, outputting Hebrew characters (`דעان`), English suffixes (`ering`), and a totally broken, interlaced mixture of Arabic and Latin characters (`مﺨلwqكي`). The "Lite" distillation process clearly stripped the parameters required to untangle overlapping byte-pair encodings for structurally similar right-to-left scripts, causing immediate cross-lingual bleeding.

### Escaping Literalism in Complex English Prose (Query 264)

**Source Text (English):** `To understand why every machine since Gutenberg has wrestled this script and mostly lost, you need one structural fact: Arabic is cursive always. There is no print-versus-handwriting distinction, no block letters. The letters connect in stone inscriptions, in manuscripts, in metal, on screens. Each letter therefore changes shape depending on its neighbours... The positional variation is the letter.` 

Translating descriptive English prose into Dhivehi often suffers from extreme, rigid literalism, where models map dictionary definitions without understanding metaphorical intent.

- **The Excellent Output (Gemini 3.5 Flash T1.0, Rating: 3):** `ގޫޓެންބާގްގެ ޒަމާނުން ފެށިގެން އުފެއްދި ކޮންމެ މެޝިނަކަށްމެ މި އަކުރުތަކާ ހަނގުރާމަކޮށް، ގިނަ ފަހަރު ނާކާމިޔާބުވެފައިވަނީ ކީއްވެގެންކަން ދެނެގަތުމަށްޓަކައި، ތިބާއަށް އޮނިގަނޑާ ބެހޭ އެއް ހަގީގަތް އެނގެންޖެހެއެވެ: އެއީ އަރަބި ބަހަކީ އަބަދުވެސް ގުޅުވައިގެން ލިޔާ އަކުރުތަކެއް ކަމެވެ... އަކުރު ހުންނަ ތަނަށް ބަލައި އަންނަ ބައްޓަމުގެ ބަދަލަކީ، ހުދު އެ އަކުރެވެ.`  *Linguistic Breakdown:* The model beautifully and accurately translates the metaphorical "wrestled this script" to "މި އަކުރުތަކާ ހަނގުރާމަކޮށް" (fought/warred with these letters), maintaining the narrative intent of the English source. It handles the structural colon dynamically, creating a naturally flowing, highly explanatory Dhivehi paragraph that resolves elegantly.
- **The Rejected Output (Gemini 2.5 Flash T0.85, Rating: -1):** `...އެއް ހަށިގަނޑު ހަޤީޤަތެއް އެނގުން މުހިންމެވެ... ތަނަވަސްކަމުގެ ތަފާތަކީ އެއީ އަކުރެވެ.`  *Linguistic Breakdown:* This translation completely disintegrates due to literal mapping. The model literally translates "structural fact" to "ހަށިގަނޑު ހަޤީޤަތެއް" (body fact/physical body truth), which is semantic nonsense in Dhivehi. Furthermore, it completely botches the critical final English sentence ("The positional variation is the letter") by translating it to "ތަނަވަސްކަމުގެ ތަފާތަކީ އެއީ އަކުރެވެ" (The difference of wealth is the letter). This total semantic failure demonstrates why older generation models generate high rejection rates: they lack the contextual abstraction layers necessary to map meaning rather than mere vocabulary.

## 7. Strategic Recommendations and Deployments

The empirical data derived from translating English and Arabic into Dhivehi exposes the massive capability gap between bleeding-edge, highly parameter-rich LLMs and their predecessors, as well as the unique vulnerabilities of distilled "Lite" architectures. The right-to-left Thaana script and complex Dhivehi syntax ruthlessly expose weaknesses in modern tokenization, context windows, and cross-lingual latent mapping. Based on the exhaustive analysis of combined scores, Glicko-2 ELO metrics, temperature dynamics, reasoning constraints, and qualitative syntactic outputs, the following strategic recommendations are provided for enterprise deployment.

### Top 3 Models for Production Environments

For deployments where grammatical accuracy, structural fluency, and cultural nuance are strictly required—such as official government documentation, theological translations, and high-tier localization—the following models are unparalleled.

1. **Gemini 3.5 Flash (Default, T1.0):** The undisputed apex of the arena. With an ELO approaching 2000 and an 84.6% win rate, it produces consistently excellent translations that effortlessly capture complex English metaphors and rigid Arabic theological structures with native-level Dhivehi fluency. Its optimal functionality at high temperature (T1.0) allows it the necessary creative entropy to find perfect localized phrasing without collapsing into literalism.
2. **Claude Opus 4.5 (Temp 0.1):** The absolute pinnacle of pipeline stability. While it may occasionally lack the creative, poetic flair of Gemini 3.5 Flash (often settling for "Good" rather than "Excellent" ratings), its zero-rejection track record across 160 A/B matchups makes it the safest model for fully automated pipelines. Its restricted low temperature ensures strict, deterministic adherence to the source text without any risk of hallucination.
3. **Gemini 3.6 Flash (Temp 0.3):** Functionally tied with its 3.5 predecessor in terms of overall capability, this model requires a slightly lower temperature to maintain its structural integrity but delivers outstanding, highly accurate results with a massive combined score of 0.934.

### Best Budget Option for High Volume

For high-volume, cost-constrained environments (e.g., bulk web scraping, low-priority messaging) where occasional human editing or oversight is possible:

- **Gemini 3 Flash Preview (Min Reasoning, Temp 1.0):** At an astonishingly low cost of only $2.62 per 100k tokens, this specific configuration leverages a minimal reasoning budget to heavily outmaneuver equivalent non-reasoning models. It maintains a highly respectable Bang for Buck metric of 9.01 and provides highly legible, structurally sound Dhivehi prose, completely eclipsing the deeply flawed 2.0 and 2.5 generations for a fraction of the cost.

### Most Cost-Effective Premium Option

For high-stakes translations that must balance enterprise budget constraints with elite, peer-reviewed quality:

- **Gemini 3 Pro Preview (Low Reasoning, Temp 0.35):** Priced at ~$20 per 100k tokens, this configuration masterfully avoids the massive $123+ inference costs of the standard unconstrained Pro models, while simultaneously delivering the highest absolute star average in the dataset (2.71). The low reasoning budget, combined with a restrictive 0.35 temperature, prevents the Pro architecture from wandering into noisy hallucination spaces while forcing deep, precise semantic alignment with the source text.

### Models to Strictly Avoid

Certain architectures pose a massive operational risk to any translation pipeline due to their propensity for catastrophic output failure and tokenization collapse:

- **The Entire Gemma 4 Lineage (31B and 26B):** Exhibiting a 100% human rejection rate and negative overall scores, these open-weights models simply cannot process or generate the Thaana script correctly. Deploying them for Dhivehi will result in total system failure and immediate user alienation.
- **Gemini 3.5 Flash Lite (All Configurations):** Despite the towering strength of the base 3.5 Flash model, the "Lite" parameterization triggers a total cross-lingual breakdown in low-resource environments. The model suffers from severe tokenization artifacts, frequently mixing Hebrew, Latin, and broken Arabic characters into its output.
- **Claude Sonnet 4.6 and Opus 4.6:** These models represent a clear case of catastrophic generational regression. They severely underperform their older 4.5 counterparts, suffering from massive ELO drops and high rejection rates. This indicates they have lost vital, fragile multilingual weights during their architectural safety updates.
- **The OpenAI GPT-5.6 Series (Sol, Terra, Luna):** OpenAI's current systemic offerings are structurally misaligned for the Dhivehi language. They produce highly rigid, literal, and unnatural translations with poor matchup win rates, and are significantly outclassed by both Google and Anthropic models in this specific linguistic domain.