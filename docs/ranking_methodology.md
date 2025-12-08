# Ranking and Voting Methodology

This document outlines the methodology used in the Dhivehi Translation Arena for evaluating and ranking translation models. The system employs a hybrid approach that combines qualitative star ratings with a comparative ELO ranking system, along with cost-effectiveness metrics.

## 1. Voting Mechanisms

The platform supports two primary methods for users to evaluate translations:

### A. Star Ratings (Qualitative)
Users rate individual translations on a fixed scale. These ratings provide an absolute measure of quality and are mapped to a point system for scoring:

| Rating | Label | Description | Score Contribution |
| :--- | :--- | :--- | :--- |
| **3 Stars** | Excellent | The translation is perfect or near-perfect. | **+3** |
| **2 Stars** | Good | The meaning is correct, but the wording or grammar might not be. | **+1** |
| **1 Star** | Understandable | The meaning is not fully correct, but it's understandable. | **0** |
| **-1** | Trash | It hallucinates, has glitch tokens, or the translation is inaccurate, or fails to follow instructions, or it doesn't make sense. | **-2** |

### B. Quick Compare (Relative)
In "Quick Compare" mode, users are presented with two blind translations side-by-side and asked to select the better one. This generates explicit pairwise comparison data (Winner vs. Loser).

## 2. Hybrid Methodology: Derived Comparisons

To maximize the utility of the data, the system unifies these two voting methods into a single dataset for ranking.

- **Explicit Comparisons**: Results from the "Quick Compare" mode are used directly.
- **Derived Comparisons**: Star ratings are converted into pairwise comparisons.
    - If a user rates Model A as **3 Stars** and Model B as **1 Star** for the same query, the system infers a "Win" for Model A over Model B.
    - If ratings are equal, it is recorded as a "Tie".

This hybrid approach allows the system to build a robust ranking even when users primarily engage with the star rating interface.

## 3. ELO Ranking Algorithm

The core ranking algorithm is based on the **ELO rating system**, commonly used in chess and competitive games. It calculates the relative skill levels of the models based on the pairwise comparisons described above.

### Parameters
- **Initial Rating**: `1500.0`
- **K-Factor**: `32`
  - The K-factor determines the sensitivity of the rating to recent results. A K-factor of 32 allows ratings to adjust reasonably quickly to new performance data.

### Formulas

#### Expected Score
The expected score ($E_A$) for Model A against Model B is calculated as:

$$E_A = \frac{1}{1 + 10^{(R_B - R_A) / 400}}$$

Where:
- $R_A$ is the current rating of Model A.
- $R_B$ is the current rating of Model B.

The expected score for Model B ($E_B$) is $1 - E_A$.

#### Rating Update
After a match, the new rating ($R'_A$) is updated based on the actual result ($S_A$):

$$R'_A = R_A + K \cdot (S_A - E_A)$$

Where $S_A$ is the actual score:
- **Win**: $1.0$
- **Loss**: $0.0$
- **Tie**: $0.5$

## 4. Scoring & Metrics

In addition to the raw ELO rating, the system calculates several derived metrics to provide a comprehensive view of model performance.

### A. Normalized Scores
To combine different metrics, we normalize them to a 0-1 scale:

1.  **Normalized Average Score**:
    - Based on the "Score Contribution" described in section 1A.
    - Range: $[-2, 3]$ (from all "Rejected" to all "Excellent").
    - Formula: `(Average Score + 2) / 5`
    - This maps the range $[-2, 3]$ to $[0, 1]$.

2.  **Normalized ELO**:
    - ELO ratings are normalized assuming a practical range of [1000, 2000].
    - Formula: `(ELO - 1000) / 1000`
    - Clamped between 0 and 1.

### B. Combined Score
The Combined Score represents the overall quality of the model, giving equal weight to the absolute quality (stars) and relative quality (ELO).

$$Combined Score = 0.5 \times Normalized Avg Score + 0.5 \times Normalized ELO$$

### C. "Bang for Buck" (Value Metric)
This metric identifies models that provide high quality at a low cost. It is designed to heavily reward high-quality models while penalizing expensive ones.

$$Bang For Buck = \frac{(10 \times Combined Score)^4}{Projected Cost Per 100k Words}$$

**Rationale**:
- **Power of 4**: The combined score is raised to the 4th power to make the metric highly sensitive to quality. A slightly better model receives a significantly higher value score.
- **Cost Divisor**: Dividing by the cost per 100k words ensures that among models of similar quality, the cheaper one is favored.

### D. Projected Cost
- Calculated as the average cost per word multiplied by 100,000.
- For free or zero-cost models, a nominal cost of $0.01 is used to prevent division by zero.
