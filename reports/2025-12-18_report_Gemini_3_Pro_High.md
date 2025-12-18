---
title: "Qualitative and Quantitative Analysis of Large Language Models in Dhivehi Translation"
author: "Gemini 3 Pro (High)"
date: "2025-12-18"
---

# Qualitative and Quantitative Analysis of Large Language Models in Dhivehi Translation

**Author:** Gemini 3 Pro (High)  
**Date:** December 18, 2025

## Abstract

This report presents a comprehensive analysis of the performance of various Large Language Models (LLMs) in translating text from Arabic/English to Dhivehi. Utilizing a pairwise comparison methodology and ELO rating system, we evaluate models based on accuracy, fluency, and theological nuance. Our findings indicate a significant performance advantage for models with "reasoning" capabilities (System 2 thinking) and lower temperature settings. The **Gemini 3 Pro (Low Reasoning)** variants currently dominate the leaderboard, demonstrating superior handling of complex grammatical structures and context.

## 1. Methodology

The analysis is based on data collected through the Dhivehi Translation Arena, a platform enabling blind pairwise comparisons.
*   **Metric:** ELO Rating System (Starting 1500).
*   **Comparisons:** 330 cross-temperature comparisons and hundreds of intra-model comparisons.
*   **Variables:** Model Family (Gemini, Claude), Temperature (0.1 vs 0.85+), and Reasoning Effort (None vs Low vs High).

## 2. Quantitative Analysis

### 2.1 ELO Leaderboard Overview

The ELO ratings reveal a clear hierarchy, with Gemini 3 Pro models occupying the top tier.

| Rank | Model | ELO Rating | Win Rate |
| :--- | :--- | :--- | :--- |
| **1** | **Gemini 3 Pro (Low Reasoning, T0.35)** | **1755** | **56.0%** |
| 2 | Gemini 3 Pro (Low Reasoning, T1.0) | 1725 | 53.4% |
| 3 | Gemini 3 Pro (Standard, T1.0) | 1679 | 50.0% |
| 4 | Claude Opus 4.5 (T0.1) | 1590 | 54.6% |
| 5 | Gemini 2.5 Flash (Reasoning, T0.85) | 1570 | 34.1%* |

*(Note: Win rate depends on the difficulty of opponents faced. ELO is the more robust metric.)*

**Key Observation:** The top 3 positions are held by Gemini 3 Pro variants. The "Low Reasoning" capability (a specific inference-time compute step) provides a tangible boost over the standard model (+46 to +76 ELO points).

### 2.2 The Impact of Temperature

A stark contrast exists between low-temperature (deterministic) and high-temperature (creative) configurations.

*   **Low Temperature (0.1 - 0.35) Wins:** 213
*   **High Temperature (0.85 - 1.0) Wins:** 117
*   **Win Rate for High Temp:** 35.4%

**Analysis:** For translation tasks, specifically into a low-resource language like Dhivehi, precision is paramount. High temperature settings often introduce hallucinations or unnatural phrasing ("creative liberties") that native speakers penalize. Low temperature ensures adherence to grammatical rules and dictionary definitions.

### 2.3 The Impact of Reasoning Models

We compared models with explicit "thinking/reasoning" capabilities against standard models.

*   **Average ELO (Reasoning Models):** 1600
*   **Average ELO (Standard Models):** 1438

**Reasoning Delta:** +162 Points.
Models that "think" before generating output are significantly better at resolving ambiguity in the source text, particularly for religious texts (Quran/Hadith) where theological precision is required.

## 3. Qualitative Analysis & Model Quirks

### 3.1 Case Study: Theological Nuance (Hadith)
*Source: "لا يؤمن أحدكم حتى يحب لأخيه ما يحب لنفسه" (None of you [truly] believes until he loves for his brother what he loves for himself).*

*   **Gemini 3 Pro (Reasoning):**
    > "ތިބާގެ އަމިއްލަ ނަފްސަށް އެދޭ ހެޔޮކަންތައް، ތިބާގެ އަޚާއަށްވެސް އެދިއްޖައުމަށް ދާންދެން، ތިޔަބައިމީހުންގެ ތެރެއިން އެކަކުވެސް **(ފުރިހަމަ ގޮތުގައި)** އީމާނެއް ނުވާނެއެވެ."
    *   *Analysis:* The model inserted "(ފުރިހަމަ ގޮތުގައި)" (in a perfect way) in parentheses. This is a sophisticated understanding of Islamic theology—the Hadith negates the *perfection* of faith, not the *existence* of faith. This demonstrates "world knowledge" applied correctly.

*   **Gemini 2.5 Flash Lite (T0.85):**
    > "ތަ ކަލާގެ ޤާނޫނަކީ..."
    *   *Analysis:* Complete hallucination. The model misinterpreted the Arabic entirely, likely due to low parameter count and high temperature noise.

### 3.2 Comparison of Honorifics (Quran 58:11)
*Source: "يرفع الله الذين آمنوا منكم..." (Allah will raise those who have believed among you...)*

*   **Gemini 3 Pro / Gemini 2.0 Flash:** Accurately used "ﷲ ތަޢާލާ" or "މާތް ﷲ" (Allah the Exalted / Noble Allah), adhering to Dhivehi cultural norms for addressing the Divine.
*   **Claude Opus (T0.85):**
    > "اللهُ ތަޢާލާ..."
    *   *Quirk:* Claude sometimes mixes Arabic script for specific religious terms within the Dhivehi text. While respectful, it breaks orthographic consistency.

### 3.3 Model Characteristics

*   **Gemini 3 Pro (Reasoning):** The "Scholar". Very precise, explains itself implicitly through bracketed clarifications. Highly stable at low temperatures.
*   **Claude Opus 4.5:** The "Classicist". High quality, but occasionally reverts to source-language scripts for proper nouns. Good structure but slower.
*   **Gemini 2.5 Flash Lite:** "Unstable". Not recommended for Dhivehi. Frequently hallucinates at high temperatures.

## 4. Discussion: High vs. Low Reasoning

The data suggests that **Reasoning is the single biggest differentiator** for Dhivehi translation quality, surpassing model size in some instances (Gemini 2.5 Flash Reasoning beats Standard Claude Sonnet 3.5).

*   **High Reasoning (Gemini 3 Pro):** Handles long-distance dependencies in sentences and infers implicit context (e.g., gender, pluralization, theological implication).
*   **Low/No Reasoning:** Tends to translate word-for-word, missing the "spirit" of the sentence, or failing to restructure the sentence for natural Dhivehi flow (SOV structure).

## 5. Conclusion

For the highest quality Dhivehi translations, we recommend **Gemini 3 Pro (Low Reasoning)** with a **Temperature of 0.35**. This configuration offers the best balance of creative fluidity and grammatical precision, backed by the highest ELO rating in our arena. High temperature settings should be avoided for translation tasks in this linguistic context.
